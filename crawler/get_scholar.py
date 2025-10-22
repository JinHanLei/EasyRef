import time
import uuid
import re
import bibtexparser
from apiModels import DBLPBibTeX
from bibtexparser.bparser import BibTexParser
from scholarly import scholarly, ProxyGenerator
from config import PROXY_CONFIG
from schemas import Paper
import logging
logger = logging.getLogger(__name__)

if PROXY_CONFIG['enabled']:
    pg = ProxyGenerator()
    success = pg.SingleProxy(PROXY_CONFIG['http'])

    # 第二个参数ProxyGenerator()代表强制使用代理
    scholarly.use_proxy(pg, ProxyGenerator())

def check_scholar_availability():
    """
    测试谷歌学术的可达性
    Returns:
        bool: 是否可达
    """
    try:
        # 尝试一个简单的查询
        next(scholarly.search_pubs('test', year_low=2023, year_high=2023))
        return True
    except Exception as e:
        logger.warning(f"谷歌学术不可达: {e}")
        return False


def get_google_scholar(keyword, year_low=None, year_high=None, limit_num=5):
    """
    使用scholarly查询论文
    
    Args:
        keyword (str): 搜索关键词
        year_low (int, optional): 最早年份
        year_high (int, optional): 最晚年份
        limit (int, optional): 爬取到的论文数量限制
    Yields:
        dict: 每篇论文的基础信息或最终结果
    """
    # 先检查谷歌学术是否可达
    if not check_scholar_availability():
        yield {
            'success': False,
            'message': '谷歌学术不可达，无法获取论文',
            'data': None,
            'completed': True
        }
        return

    papers = []
    scholarly.set_timeout(100)
    searched_scholar = scholarly.search_pubs(query=keyword, year_low=year_low, year_high=year_high)
    count = 0
    fetcher = DBLPBibTeX()

    try:
        for pub in searched_scholar:
            filled_pub = pub
            if count >= limit_num:
                break
            count += 1
            title = filled_pub['bib']['title']
            if title.startswith("\"") and title.endswith("\""):
                title = title[1:-1]
            title = title.strip()
            if papers and any(p['title'].lower() == title.lower() for p in papers):
                continue
            # 构建基础论文信息，使用Paper schema约束数据结构
            paper_id = str(uuid.uuid4())

            # dblp获取bib
            bibtex = fetcher.get_bibtex(f"title:{title} year:{filled_pub['bib'].get('pub_year')}")
            real_bibtex = None
            if bibtex:
                bib_db = bibtexparser.loads(bibtex, parser=BibTexParser())
                bib_title = bib_db.entries[0].get('title')
                # 只有标题存在且两个标题相同才赋值
                if bib_title:
                    if re.sub("\s", "", bib_title.lower()) == re.sub("\s", "", title.lower()):
                        real_bibtex = bibtex

            paper_info = Paper(
                id=paper_id,
                title=title,
                pub_year=filled_pub['bib'].get('pub_year'),
                num_citations=filled_pub.get('num_citations', 0),
                bib=real_bibtex,
                pub_url=filled_pub.get('pub_url', None),
                bib_url=filled_pub.get('url_scholarbib', None),
                citedby_url=filled_pub.get('citedby_url', None),
                authors=filled_pub['bib'].get('author', None)
            )

            papers.append(paper_info.__dict__)
            # 实时返回每篇论文的信息
            yield {
                'success': True,
                'message': f'已获取第 {count} 篇论文',
                'data': paper_info.__dict__,  # 转换为字典以便序列化
                'completed': False,
                'progress': count
            }
            
            if count % 10 == 0:
                time.sleep(0.08)
                
        # 完成所有爬取
        yield {
            'success': True,
            'message': f'成功获取 {count} 篇论文',
            'data':papers,
            'completed': True,
            'total': count
        }
        
    except Exception as e:
        logger.error(f"爬取过程中断: {e}")
        yield {
            'success': False,
            'message': f'爬取过程中断: {str(e)}',
            'completed': True
        }
    
if __name__ == '__main__':
    keyword = "summarization llm"
    year_low = 2024
    year_high = None
    limit_num = 5
    save_dir = "data"

    result_generator = get_google_scholar(keyword, year_low, year_high, limit_num)
    papers_data = []
    count = 0
    for result in result_generator:
        if count > 1:
            papers_data.append(result['data'])
            break
        count += 1
    print(papers_data)
