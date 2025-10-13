from flask import Blueprint, jsonify, request
import uuid
import logging

from apis.auth_api import get_authenticated_client
from crawler.get_scholar import get_google_scholar
from crawler.enhance_paper_info import enhance_paper_info
from db.paper_operations import PaperOperations, PDFStorage
from schemas import SearchTask, SearchResult

logger = logging.getLogger(__name__)

# 创建蓝图
scholar = Blueprint('scholar', __name__, url_prefix='/api')

@scholar.route('/scholar', methods=['POST'])
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
        user_id, supabase_client = get_authenticated_client()
        
        if not keyword:
            return jsonify({'error': '缺少关键词参数'}), 400
            
        if not user_id:
            return jsonify({'error': '缺少用户ID参数'}), 400
        
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
        if enhanced_papers:
            paper_ops.batch_insert_papers(enhanced_papers)

        paper_ops.insert_search_results(
            papers_id=search_results,
            session_id=session_id,
        )

        # 返回session_id
        return jsonify({
            'session_id': session_id,
            'message': f'搜索完成，共处理{len(search_results)}篇论文'
        }), 200
        
    except Exception as e:
        logger.error(f"搜索过程中发生错误: {e}", exc_info=True)
        return jsonify({'error': f'服务器内部错误: {str(e)}'}), 500