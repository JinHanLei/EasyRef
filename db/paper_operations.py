from typing import List, Dict, Optional, Any
import logging
import hashlib
import uuid

from config import SUPABASE_CONFIG
from crawler.get_pdf import download_single_pdf_content
from schemas import SearchTask, SearchResult

logger = logging.getLogger(__name__)


def _calculate_file_hash(pdf_bytes: bytes) -> str:
    """计算文件SHA256哈希值"""
    return hashlib.sha256(pdf_bytes).hexdigest()


class PDFStorage:
    """PDF文件存储到Supabase"""

    def __init__(self, supabase):
        self.supabase = supabase
        self.paper_ops = PaperOperations(supabase)

    def upload_pdf_from_bytes(
            self,
            pdf_bytes: bytes,
    ) -> Optional[Dict[str, Any]]:
        """将PDF字节流上传到Supabase存储，支持文件去重"""
        try:
            file_size = len(pdf_bytes)
            file_hash = _calculate_file_hash(pdf_bytes)

            # 检查是否已存在相同文件
            existing = self.supabase.table('papers').select('pdf_url').eq('file_hash', file_hash).execute()

            if existing.data:
                # 文件已存在，直接返回已存在的文件信息，不创建新的关联记录
                existing_file = existing.data[0]
                
                return {
                    'pdf_url': existing_file['pdf_url'],
                    'file_size': file_size,
                    'success': True,
                    'message': '文件已存在，使用现有文件',
                    'existing': True
                }

            # 生成存储路径
            file_name = f"{file_hash}.pdf"

            # 上传到Supabase存储
            self.supabase.storage.from_(SUPABASE_CONFIG['papers_bucket_name']).upload(
                path=file_name,
                file=pdf_bytes,
                file_options={'content-type': 'application/pdf'}
            )
            public_url = self.supabase.storage.from_(SUPABASE_CONFIG['papers_bucket_name']).get_public_url(file_name)
            # 保存文件信息到数据库
            file_record = {
                'pdf_url': public_url,
                'file_hash':file_hash,
                'file_size': file_size,
                'success': True,
            }
            return file_record

        except Exception as e:
            logger.error(f"上传PDF文件时出错: {e}")
            return {
                'success': False,
                'message': f'上传文件时出错: {str(e)}'
            }


class PaperOperations:
    """论文数据库操作类"""
    
    def __init__(self, supabase):
        self.supabase = supabase

    def get_paper_by_title_year(self, title: str, pub_year: int) -> Optional[Dict]:
        """根据标题和年份获取论文信息，用于检查重复
        
        Args:
            title: 论文标题
            pub_year: 发表年份
            
        Returns:
            dict: 论文信息，如果不存在则返回None
        """
        try:
            logger.info(f"检查论文是否存在: {title}, 年份: {pub_year}")
            # 使用ILIKE进行不区分大小写的匹配，并去除标题两端空格
            result = self.supabase.table('papers') \
                .select('*') \
                .ilike('title', title.strip()) \
                .eq('pub_year', pub_year) \
                .limit(1) \
                .execute()
            logger.info(f"查询结果: {result.data}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"根据标题和年份获取论文信息失败: {e}")
            return None

    def batch_insert_papers(self, papers_data: List[Dict[str, Any]]):
        """储存论文
        
        Args:
            papers_data: 论文数据列表
            
        Returns:
            List[Dict]: 插入的论文数据（包含数据库生成的ID等字段）
        """
        try:
            result = self.supabase.table('papers').insert(papers_data).execute()
            # 返回插入的论文数据，包含数据库生成的ID等字段
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"批量插入论文失败: {e}")
            return []

    def update_paper(self, paper_id: str, update_data: Dict[str, Any]) -> bool:
        """更新单篇论文信息
        
        Args:
            paper_id: 论文ID
            update_data: 更新数据
            
        Returns:
            bool: 是否更新成功
        """
        try:
            self.supabase.table('papers').update(update_data).eq('id', paper_id).execute()
            return True
        except Exception as e:
            logger.error(f"更新论文失败: {e}")
            return False

    def get_paper_by_id(self, paper_id: str) -> Optional[Dict]:
        """根据ID获取论文信息
        
        Args:
            paper_id: 论文ID
            
        Returns:
            dict: 论文信息
        """
        try:
            result = self.supabase.table('papers').select('*').eq('id', paper_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"获取论文信息失败: {e}")
            return None

    def insert_search_results(
            self,
            papers_id: List,
            session_id: str,
    ) -> List[Dict]:
        """将搜索结果插入数据库并建立索引
        
        Args:
            papers_id: 论文id列表
            session_id: 搜索会话ID
            
        Returns:
            List[Dict]: 插入的论文数据
        """
        try:
            logger.info(f"开始插入 {len(papers_id)} 条搜索结果记录")
            # 为每个论文创建搜索结果索引
            search_results = []
            for i, paper_id in enumerate(papers_id):
                search_result = SearchResult(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    paper_id=paper_id,
                    result_index=i
                )

                search_results.append(search_result.__dict__)
            
            # 批量插入搜索结果
            if search_results:
                logger.info(f"正在执行数据库插入操作，共 {len(search_results)} 条记录")
                result = self.supabase.table('search_results').insert(search_results).execute()
                logger.info(f"数据库插入操作完成")
            
            return search_results
        except Exception as e:
            logger.error(f"插入搜索结果失败: {e}")
            raise e

    def get_papers_by_session(
            self,
            session_id: str,
            page: int = 1,
            page_size: int = 20
    ) -> tuple[List[Dict], Dict]:
        """根据搜索会话ID获取论文列表
        
        Args:
            session_id: 搜索会话ID
            page: 页码
            page_size: 每页数量
            
        Returns:
            tuple: (论文列表, 分页信息)
        """
        try:
            # 计算偏移量
            offset = (page - 1) * page_size
            
            # 查询搜索结果总数
            count_result = self.supabase.table('search_results') \
                .select('count', count='exact') \
                .eq('session_id', session_id) \
                .execute()
            
            total_count = count_result.count if hasattr(count_result, 'count') else 0
            
            # 查询论文数据
            result = self.supabase.table('search_results') \
                .select('paper_id,result_index') \
                .eq('session_id', session_id) \
                .order('result_index') \
                .range(offset, offset + page_size - 1) \
                .execute()
            
            # 获取论文ID列表
            paper_ids = [item['paper_id'] for item in result.data] if result.data else []
            
            # 查询论文详细信息
            papers_data = []
            if paper_ids:
                papers_result = self.supabase.table('papers') \
                    .select('*') \
                    .in_('id', paper_ids) \
                    .execute()
                papers_data = papers_result.data
            
            # 构建分页信息
            total_pages = (total_count + page_size - 1) // page_size
            pagination = {
                'current_page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
            
            return papers_data, pagination
        except Exception as e:
            logger.error(f"获取论文列表时出错: {e}")
            raise e

    def save_task_to_db(self, task):
        """
        将任务信息保存到数据库
        
        Args:
            task: 搜索任务对象
        """
        try:
            # 检查任务是否已存在
            result = self.supabase.table('search_tasks').select('*').eq('session_id', task.session_id).execute()
            user_id_str = str(task.user_id) if task.user_id else None
            task_data = task.__dict__
            if result.data:
                # 更新现有任务
                self.supabase.table('search_tasks').update(task_data).eq('session_id', task.session_id).execute()
            else:
                # 插入新任务
                if user_id_str is None:
                    raise ValueError("用户ID不能为空，无法创建搜索任务")
                self.supabase.table('search_tasks').insert(task_data).execute()
        except Exception as e:
            logger.error(f"保存任务到数据库失败: {e}")
            raise e

    def load_task_from_db(self, session_id: str):
        """
        从数据库加载任务信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            SearchTask: 搜索任务对象或None
        """
        try:
            result = self.supabase.table('search_tasks').select('*').eq('session_id', session_id).execute()
            if result.data:
                task_data = result.data[0]
                task = SearchTask(
                    session_id=task_data['session_id'],
                    keyword=task_data['keyword'],
                    year_low=task_data['year_low'],
                    year_high=task_data['year_high'],
                    limit_num=task_data['limit_num'],
                    user_id=task_data['user_id'],
                    status=task_data['status'],
                )
                return task
        except Exception as e:
            logger.error(f"从数据库加载任务失败: {e}")
        return None
