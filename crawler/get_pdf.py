import requests
from playwright.sync_api import sync_playwright
import ssl
from typing import Dict, List, Optional, Tuple

from paper_utils.pdf_fast_reader import PDFFastReader

ssl._create_default_https_context = ssl._create_unverified_context


def convert_to_pdf_url(url: str) -> str | None:
    """
    将论文链接转换为可以直接下载PDF的链接

    Args:
        url: 原始论文链接

    Returns:
        可以直接下载PDF的链接
    """
    # 处理arxiv链接: https://arxiv.org/abs/1706.03762 -> https://arxiv.org/pdf/1706.03762.pdf
    if 'arxiv' in url and '/abs/' in url:
        url = url.replace("/abs/", "/pdf/")
        if not url.endswith('.pdf'):
            url += ".pdf"
        return url

    # 处理acl链接
    if 'aclanthology.org' in url:
        if url.endswith("/"):
            url = url[:-1]
        if not url.endswith('.pdf'):
            url += ".pdf"
        return url

    # 如果已经是PDF链接则直接返回
    if url.endswith('.pdf'):
        return url

    return None


def download_single_pdf_content(url: str) -> Optional[bytes]:
    """下载单个PDF文件内容并返回字节数据
    
    Args:
        url: PDF文件的URL
        
    Returns:
        bytes: PDF文件的字节内容，下载失败时返回None
    """
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200 and is_pdf_response(response):
            content = response.content
            # 双重检查确保内容确实是PDF格式
            if is_pdf_content(content):
                return content
            else:
                return None
        else:
            return None
    except Exception:
        return None
    

def download_from_weburl_content(url: str) -> Optional[bytes]:
    """
    在网页中查找PDF链接并下载内容，返回PDF字节数据，找不到则返回None。
    """
    pdf_url = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, timeout=15000)
            links = page.query_selector_all('a')
            for link in links:
                href = link.get_attribute('href')
                if href and '.pdf' in href.lower():
                    if not href.startswith('http'):
                        from urllib.parse import urljoin
                        href = urljoin(url, href)
                    pdf_url = href
                    break
        except Exception:
            pass
        browser.close()
    if pdf_url:
        return download_single_pdf_content(pdf_url)
    return None


def get_bing_search_results(question: str) -> List[dict]:
    """获取Bing搜索结果"""
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(10000)
            try:
                page.goto(f"https://www.bing.com/search?q={question}")
            except:
                page.goto("https://www.bing.com")
                page.fill('input[name="q"]', question)
                page.press('input[name="q"]', 'Enter')
            try:
                page.wait_for_load_state('networkidle', timeout=5000)
            except:
                pass
            search_results = page.query_selector_all('.b_algo h2')
            for result in search_results:
                title = result.inner_text()
                a_tag = result.query_selector('a')
                if not a_tag:
                    continue
                url = a_tag.get_attribute('href')
                if not url:
                    continue
                results.append({'title': title, 'url': url})
            browser.close()
    except Exception:
        pass
    return results

def download_from_bing_single_content(title: str) -> Optional[bytes]:
    """通过Bing搜索，根据标题下载PDF内容

    Args:
        title: 论文标题

    Returns:
        bytes: PDF文件的字节内容，下载失败时返回None
    """
    search_queries = [
        f"{title} filetype:pdf",
        f"{title} pdf",
        f"{title} download pdf"
    ]

    for query in search_queries:
        search_results = get_bing_search_results(query)
        if search_results:
            for result in search_results:
                if '.pdf' in result['url'].lower():
                    content = download_single_pdf_content(result['url'])
                    if content:
                        return content
    return None


def is_pdf_content(content: bytes) -> bool:
    """
    检查字节内容是否为PDF格式

    Args:
        content: 文件的字节内容

    Returns:
        bool: 如果是PDF格式返回True，否则返回False
    """
    # 检查PDF文件的魔数（Magic Number）
    # PDF文件以'%PDF-'开头
    if content and len(content) > 4:
        return content.startswith(b'%PDF-')
    return False


def is_pdf_response(response) -> bool:
    """
    检查HTTP响应是否为PDF格式

    Args:
        response: requests的响应对象

    Returns:
        bool: 如果是PDF格式返回True，否则返回False
    """
    content_type = response.headers.get('content-type', '').lower()
    return 'application/pdf' in content_type


def main_download_pdf_contents(
    title: str,
    url: str,
) -> Optional[bytes]:
    """下载单个PDF内容
    
    Args:
        title: 论文标题
        url: 论文链接

    Returns:
        bytes: PDF文件的字节内容，下载失败时返回None
    """
    # 转换链接为PDF下载链接
    pdf_url = convert_to_pdf_url(url)
    if pdf_url:
        # 直接尝试下载PDF
        content = download_single_pdf_content(pdf_url)
    elif url:
        content = download_from_weburl_content(url)
    else:
        content = download_from_bing_single_content(title)
    return content


if __name__ == '__main__':
    content = main_download_pdf_contents("Attention Is All You Need", "https://arxiv.org/abs/1706.03762")
    abs = PDFFastReader(content=content).forward(abstract_only=True)
    print(abs)