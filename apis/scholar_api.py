from flask import Blueprint, jsonify, request
import uuid
import logging

from apis.auth_api import get_authenticated_client
from crawler.get_scholar import get_google_scholar
from crawler.enhance_paper_info import enhance_paper_info
from db.paper_operations import PaperOperations, PDFStorage
from db.supabase_client import SupabaseInitializer
from schemas import SearchTask, SearchResult
from crawler.bib2text import bibtex_to_text

logger = logging.getLogger(__name__)

# 创建蓝图
scholar = Blueprint('scholar', __name__, url_prefix='/api')

# 默认用户凭据（用于无登录访问）
DEFAULT_USER_EMAIL = "jinhanlei@mail.easyref.tech"
DEFAULT_USER_PASSWORD = "2GHLMCL"

def get_default_user_client():
    """
    获取默认用户的Supabase客户端
    
    Returns:
        tuple: (用户ID, Supabase客户端实例)
    """
    try:
        # 初始化Supabase客户端
        supabase_init = SupabaseInitializer()
        supabase_client = supabase_init.supabase
        
        # 使用默认凭据登录
        response = supabase_client.auth.sign_in_with_password({
            "email": DEFAULT_USER_EMAIL,
            "password": DEFAULT_USER_PASSWORD
        })
        
        if response and response.session:
            user_id = str(response.user.id)
            access_token = response.session.access_token
            
            # 更新客户端的认证头
            supabase_client.options.headers.update({
                "Authorization": f"Bearer {access_token}"
            })
            
            return user_id, supabase_client
        else:
            logger.error("默认用户登录失败")
            return None, None
    except Exception as e:
        logger.error(f"获取默认用户客户端时出错: {e}")
        return None, None

@scholar.route('/scholar_real', methods=['POST'])
def search_scholar():
    """
    处理用户搜索请求的主要API端点
    
    1. 接收用户输入的关键词和约束条件
    2. 创建搜索任务并生成session_id
    3. 调用get_scholar爬取论文
    4. 对每篇论文进行信息增强处理
    5. 将论文信息存入数据库
    6. 将搜索结果分页存入user_search_results表
    7. 返回session_id给前端
    """
    try:
        # 获取请求数据
        data = request.get_json()
        keyword = data.get('keyword')
        year_low = data.get('year_low')
        year_high = data.get('year_high')
        limit_num = data.get('limit_num', 50)
        
        # 尝试获取认证用户，如果没有则使用默认用户
        user_id, supabase_client = get_authenticated_client()
        if not user_id or not supabase_client:
            logger.info("未检测到认证用户，使用默认用户")
            user_id, supabase_client = get_default_user_client()
        
        if not keyword:
            return jsonify({'error': '缺少关键词参数'}), 400
            
        if not user_id:
            return jsonify({'error': '用户认证失败'}), 401
        
        # 创建session_id
        session_id = str(uuid.uuid4())
        paper_ops = PaperOperations(supabase_client)
        pdf_storage = PDFStorage(supabase_client)

        # 创建搜索任务并保存到数据库
        task = SearchTask(
            session_id=session_id,
            user_id=user_id,
            keyword=keyword,
            year_low=year_low,
            year_high=year_high,
            limit_num=limit_num,
            status='running',
        )
        paper_ops.save_task_to_db(task)
        
        # 调用get_scholar爬取论文
        papers_data = []
        search_generator = get_google_scholar(
            keyword=keyword,
            year_low=year_low,
            year_high=year_high,
            limit_num=limit_num
        )
        
        for item in search_generator:
            if item.get('completed'):
                # 搜索完成，更新任务状态
                task.status = 'completed'
                paper_ops.save_task_to_db(task)
                # 得到所有论文
                papers_data = item.get('data', [])
                break
            if not item.get('success'):
                # 搜索出错，更新任务状态
                task.status = 'error'
                paper_ops.save_task_to_db(task)
                logger.error(f"搜索过程中发生错误: {item.get('message', None)}")
                return jsonify({'error': item.get('message', None)}), 500
        
        # 处理每篇论文：增强信息并保存到数据库
        enhanced_papers = []
        search_results = []
        for i, paper_data in enumerate(papers_data):
            # 检查数据库中是否已存在相同标题和年份的论文
            existing_paper = paper_ops.get_paper_by_title_year(
                paper_data['title'], 
                paper_data['pub_year']
            )
            
            # 如果论文不存在，则调用enhance_paper_info获取更多信息
            if not existing_paper:
                enhanced_paper = enhance_paper_info(paper_data)
                if 'pdf_content' in enhanced_paper:
                    pdf_content = enhanced_paper.pop('pdf_content')
                    # 存在pdf则上传到bucket
                    if pdf_content:
                        pdf_result = pdf_storage.upload_pdf_from_bytes(pdf_content)
                        if pdf_result and pdf_result.get('success'):
                            enhanced_paper['pdf_url'] = pdf_result.get('pdf_url')
                            enhanced_paper['file_size'] = pdf_result.get('file_size', 0)
                            enhanced_paper['file_hash'] = pdf_result.get('file_hash', 0)

                enhanced_papers.append(enhanced_paper)
                search_results.append(enhanced_paper['id'])
            else:
                search_results.append(existing_paper['id'])

        title_and_abstracts = ""
        titles = ""
        if enhanced_papers:
            paper_ops.batch_insert_papers(enhanced_papers)
            title_and_abstracts = "\n\n".join(["标题：" + paper['title'] + "\n" + "摘要：" + paper['abstract']
                                             for paper in enhanced_papers])
        else:
            titles = "\n".join(["标题：" + paper['title'] for paper in papers_data])

        paper_ops.insert_search_results(
            papers_id=search_results,
            session_id=session_id,
        )

        # 返回session_id
        return jsonify({
            'session_id': session_id,
            'data': title_and_abstracts if title_and_abstracts else titles,
            'message': f'搜索完成，共处理{len(search_results)}篇论文'
        }), 200
        
    except Exception as e:
        logger.error(f"搜索过程中发生错误: {e}", exc_info=True)
        return jsonify({'error': f'服务器内部错误: {str(e)}'}), 500

@scholar.route('/scholar', methods=['POST'])
def search_scholar_fake():
    # 获取请求数据
    data = request.get_json()
    keyword = data.get('keyword')
    year_low = data.get('year_low')
    year_high = data.get('year_high')
    limit_num = data.get('limit_num', 50)
    style = data.get('style', 'apa')

    # 尝试获取认证用户，如果没有则使用默认用户
    user_id, supabase_client = get_authenticated_client()
    if not user_id or not supabase_client:
        logger.info("未检测到认证用户，使用默认用户")
        user_id, supabase_client = get_default_user_client()

    if not keyword:
        return jsonify({'error': '缺少关键词参数'}), 400

    if not user_id:
        return jsonify({'error': '用户认证失败'}), 401

    paper_ops = PaperOperations(supabase_client)
    papers = paper_ops.search_papers_by_keyword(keyword=keyword)
    res_text = ""
    for i, paper_data in enumerate(papers):
        bib = bibtex_to_text(paper_data['bib'], style)
        res_text += f"{i+1}. {paper_data['title']} \n  摘要：{paper_data['abstract']} \n 引用格式：{bib} \n "

    return jsonify({
        'session_id': str(uuid.uuid4()),
        'data': res_text,
        'message': f'搜索完成，共处理{len(papers)}篇论文'
    }), 200

@scholar.route('/bib2text', methods=['POST'])
def convert_bib2text():
    """
    将BibTeX格式转换为指定格式的文本引用
    
    请求参数:
        bib_str (str): BibTeX字符串
        style (str): 转换格式，可选值: 'apa'(默认), 'mla', 'gb7714'
    
    返回:
        JSON: 包含转换后的文本引用
    """
    try:
        # 获取请求数据
        data = request.get_json()
        bib_str = data.get('bib_str')
        style = data.get('style', 'apa')  # 默认使用APA格式
        
        # 参数验证
        if not bib_str:
            return jsonify({'error': '缺少bib_str参数'}), 400
            
        if style not in ['apa', 'mla', 'gb7714']:
            return jsonify({'error': '不支持的格式，支持的格式: apa, mla, gb7714'}), 400
        
        # 调用bibtex_to_text函数进行转换
        converted_text = bibtex_to_text(bib_str, style)
        
        # 返回结果
        return jsonify({
            'success': True,
            'data': converted_text,
            'style': style
        }), 200
        
    except Exception as e:
        logger.error(f"BibTeX转换过程中发生错误: {e}", exc_info=True)
        return jsonify({'error': f'服务器内部错误: {str(e)}'}), 500
