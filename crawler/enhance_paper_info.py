import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from crawler.get_abstract import crawl_all_abstract
from crawler.get_pdf import main_download_pdf_contents
from paper_utils.pdf_fast_reader import PDFFastReader

logger = logging.getLogger(__name__)


def enhance_paper_info(paper_info):
    """
    为单篇论文增强信息，获取摘要和PDF内容
    
    Args:
        paper_info (dict): 论文基础信息
        
    Returns:
        dict: 增强后的论文信息
    """
    # 创建增强信息的副本
    enhanced_info = paper_info.copy()
    
    # 先尝试下载PDF内容
    if paper_info.get('pub_url'):
        try:
            pdf_content = main_download_pdf_contents(
                paper_info['title'],
                paper_info['pub_url']
            )
            enhanced_info['pdf_content'] = pdf_content
        except Exception as e:
            logger.warning(f"下载PDF失败: {paper_info['title']}, 错误: {e}")
            enhanced_info['pdf_content'] = None
    
    # 从PDF中提取摘要
    abstract = None
    
    # 如果PDF中没有提取到摘要或摘要为空，则调用crawl_all_abstract
    if not abstract:
        try:
            abstract = crawl_all_abstract(
                paper_info['title'], 
                paper_info['pub_url']
            )
        except Exception as e:
            logger.warning(f"获取摘要失败: {paper_info['title']}, 错误: {e}")

    if not abstract and enhanced_info.get('pdf_content'):
        try:
            pdf_reader = PDFFastReader(content=enhanced_info.get('pdf_content'))
            abstract = pdf_reader.forward(abstract_only=True)
            # 清理摘要内容
            if abstract:
                abstract = abstract.strip()
        except Exception as e:
            logger.warning(f"从PDF提取摘要失败: {paper_info['title']}, 错误: {e}")
            abstract = None
    
    enhanced_info['abstract'] = abstract
    return enhanced_info


def enhance_papers_generator(papers_generator):
    """
    增强论文信息生成器，为每篇论文获取摘要和PDF
    
    Args:
        papers_generator: 论文信息生成器
        
    Yields:
        dict: 增强后的论文信息或状态信息
    """
    for item in papers_generator:
        if item.get('completed', False) and not item.get('progress'):
            yield item
            continue
            
        if item.get('data') and not item.get('completed'):
            # 增强单篇论文信息
            enhanced_data = enhance_paper_info(item['data'])
            item['data'] = enhanced_data
            yield item
        else:
            # 其他情况直接yield
            yield item


def enhance_papers_batch(papers_list, max_workers=5):
    """
    使用多线程批量增强论文信息
    
    Args:
        papers_list (list): 论文信息列表
        max_workers (int): 最大线程数，默认为5
        
    Returns:
        list: 增强后的论文信息列表
    """
    enhanced_papers = []
    
    # 使用线程池处理论文信息增强
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_paper = {
            executor.submit(enhance_paper_info, paper): paper 
            for paper in papers_list
        }
        
        # 收集结果
        for future in as_completed(future_to_paper):
            paper = future_to_paper[future]
            try:
                enhanced_paper = future.result()
                enhanced_papers.append(enhanced_paper)
            except Exception as e:
                logger.error(f"处理论文时出错: {paper.get('title', 'Unknown')}, 错误: {e}")
                # 出错时保留原始论文信息
                enhanced_papers.append(paper)
    
    return enhanced_papers