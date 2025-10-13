import os
import pandas as pd
import arxiv
import requests
import uuid
from playwright.sync_api import sync_playwright
import ssl
import zipfile
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
ssl._create_default_https_context = ssl._create_unverified_context


# ==================== 通用方法 ====================
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


# def extract_and_categorize_links(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
#     """
#     读取DataFrame并进行链接提取，分类为arxiv、pdf、acl和其他
#
#     Args:
#         df: 包含论文信息的DataFrame
#
#     Returns:
#         包含分类结果的字典
#     """
#     # 提取包含arxiv的行
#     arxiv_rows = df[df['pub_url'].str.contains('arxiv', na=False)]
#
#     # 提取直接包含PDF链接的行
#     pdf_rows = df[df['pub_url'].str.contains('.pdf', na=False)]
#
#     # 提取包含acl但不包含pdf的行
#     acl_rows = df[
#         df['pub_url'].str.contains('acl', na=False) &
#         ~df['pub_url'].str.contains('.pdf', na=False)
#     ]
#
#     # 其他行（不包含arxiv、pdf、acl）
#     others = df[
#         ~df.index.isin(arxiv_rows.index) &
#         ~df.index.isin(pdf_rows.index) &
#         ~df.index.isin(acl_rows.index)
#     ]
#
#     return {
#         'arxiv': arxiv_rows,
#         'pdf': pdf_rows,
#         'acl': acl_rows,
#         'others': others
#     }


# def preprocess_pdf_links(arxiv_df: pd.DataFrame, pdf_df: pd.DataFrame, acl_df: pd.DataFrame) -> List[Tuple[str, str]]:
#     url_title_list = []
#     # arxiv
#     for _, row in arxiv_df.iterrows():
#         url = row["pub_url"].replace("/abs/", "/pdf/")
#         if not url.endswith('.pdf'):
#             url += ".pdf"
#         url_title_list.append((url, row["title"]))
#     # pdf
#     for _, row in pdf_df.iterrows():
#         url_title_list.append((row["pub_url"], row["title"]))
#     # acl
#     for _, row in acl_df.iterrows():
#         acl_url = row["pub_url"]
#         if acl_url.endswith("/"):
#             acl_url = acl_url[:-1]
#         acl_url += ".pdf"
#         url_title_list.append((acl_url, row["title"]))
#     return url_title_list


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


# ==================== 返回PDF内容的方法（用于云端存储）====================
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


def batch_download_pdf_contents(
    title_url_list: List[Tuple[str, str]],
    max_workers: int = 8
) -> List[Optional[bytes]]:
    """批量下载PDF内容
    
    Args:
        title_url_list: 论文标题和链接的元组列表
        max_workers: 最大工作线程数
        
    Returns:
        List[Optional[bytes]]: PDF内容列表，下载失败的为None
    """
    def download_single(args):
        title, url = args
        return main_download_pdf_contents(title, url)
    
    contents = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_single, item) for item in title_url_list]
        for future in as_completed(futures):
            contents.append(future.result())
    
    # 保持与输入列表相同的顺序
    result_dict = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(download_single, title_url_list[i]): i 
            for i in range(len(title_url_list))
        }
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            result_dict[index] = future.result()
    
    # 按顺序返回结果
    contents = [result_dict[i] for i in range(len(title_url_list))]
    return contents




# ==================== 保存到本地文件的方法（向后兼容，暂时注释）====================
'''
def download_single_pdf(url: str, output_dir: str) -> Optional[str]:
    """下载单个PDF文件"""
    try:
        file_extension = '.pdf'
        unique_filename = str(uuid.uuid4()) + file_extension
        local_filename = os.path.join(output_dir, unique_filename)
        
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            with open(local_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return local_filename
        else:
            return None
    except Exception:
        return None
    

def download_from_weburl(url: str, output_dir: str) -> Optional[str]:
    """
    在网页中查找PDF链接并下载，返回本地文件路径，找不到则返回None。
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
        return download_single_pdf(pdf_url, output_dir)
    return None


def download_direct_pdfs(
    url_title_list: List[Tuple[str, str]],
    output_dir: str,
    max_workers: int = 8
) -> Tuple[List[str], List[Tuple[str, str]]]:
    downloaded_files = []
    failed_list = []
    def download_single_pdf_task(url):
        return download_single_pdf(url, output_dir)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_single_pdf_task, url) for url in url_title_list]
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            if result:
                downloaded_files.append(result)
            else:
                failed_list.append(url_title_list[i])
    return downloaded_files, failed_list


def download_from_weburls(
    others_df: pd.DataFrame,
    output_dir: str,
    max_workers: int = 8
) -> Tuple[List[str], List[dict]]:
    def weburl_task(row):
        file_path = download_from_weburl(row["pub_url"], output_dir)
        if file_path:
            return file_path, None
        else:
            return None, {'title': row['title'], 'pub_url': row['pub_url']}
    tasks = [row for _, row in others_df.iterrows()]
    downloaded_files = []
    failed_list = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(weburl_task, row) for row in tasks]
        for i, future in enumerate(as_completed(futures)):
            file_path, fail_info = future.result()
            if file_path:
                downloaded_files.append(file_path)
            elif fail_info:
                failed_list.append(fail_info)
    return downloaded_files, failed_list


def download_from_bing(
    others_df: pd.DataFrame,
    output_dir: str,
    max_workers: int = 8,
    max_tries: int = 3
) -> Tuple[List[str], List[dict]]:
    def bing_task(row):
        search_queries = [
            f"{row['title']} filetype:pdf",
            f"{row['title']} pdf",
            f"{row['title']} download pdf"
        ]
        for query in search_queries:
            for _ in range(max_tries):
                search_results = get_bing_search_results(query)
                if search_results:
                    for result in search_results:
                        if '.pdf' in result['url'].lower():
                            file_path = download_single_pdf(result['url'], output_dir)
                            if file_path:
                                return file_path, None
        return None, {'title': row['title'], 'pub_url': row['pub_url']}
    tasks = [row for _, row in others_df.iterrows()]
    downloaded_files = []
    failed_list = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(bing_task, row) for row in tasks]
        for i, future in enumerate(as_completed(futures)):
            file_path, fail_info = future.result()
            if file_path:
                downloaded_files.append(file_path)
            elif fail_info:
                failed_list.append(fail_info)
    return downloaded_files, failed_list


def main_download_pdfs(
    df: pd.DataFrame, 
    output_dir: str,
    download_direct: bool = True,
    download_weburl: bool = True,
    download_bing: bool = True,
    max_workers: int = 8
) -> Tuple[str, pd.DataFrame]:
    """主函数：下载PDF到本地目录（向后兼容）"""
    os.makedirs(output_dir, exist_ok=True)
    categorized = extract_and_categorize_links(df)
    downloaded_files = []
    not_found_rows = []
    # 2. 统一处理arxiv/pdf/acl
    if download_direct and (not categorized['arxiv'].empty or not categorized['pdf'].empty or not categorized['acl'].empty):
        url_title_list = preprocess_pdf_links(categorized['arxiv'], categorized['pdf'], categorized['acl'])
        direct_files, failed_direct = download_direct_pdfs(url_title_list, output_dir, max_workers=max_workers)
        downloaded_files.extend(direct_files)
        for url, title in failed_direct:
            not_found_rows.append({'title': title, 'pub_url': url})
    # 3. 从链接下载
    failed_weburl_df = None
    if download_weburl and not categorized['others'].empty:
        weburl_files, failed_weburl = download_from_weburls(categorized['others'], output_dir, max_workers=max_workers)
        downloaded_files.extend(weburl_files)
        failed_weburl_df = pd.DataFrame(failed_weburl)
        not_found_rows.extend(failed_weburl)
    # 4. 从Bing搜索下载
    if download_bing and failed_weburl_df is not None and not failed_weburl_df.empty:
        bing_files, failed_bing = download_from_bing(failed_weburl_df, output_dir, max_workers=max_workers)
        downloaded_files.extend(bing_files)
        not_found_rows.extend(failed_bing)
    return output_dir, pd.DataFrame(not_found_rows)


# 示例使用
if __name__ == "__main__":
    keywords = "eval_sum_llm_final"
    df = pd.read_excel(f"data/{keywords}.xlsx")
    output_path, not_found_df = main_download_pdfs(
        df=df,
        output_dir=f"data/{keywords}_pdfs",
        download_direct=True,
        download_weburl=True,
        download_bing=True,
        max_workers=8
    )
    print(f"下载完成，输出路径: {output_path}")
    if not_found_df.empty:
        print(f"未能下载的条目数量: {len(not_found_df)}")
        print("未能下载的条目详情:")
        print(not_found_df)
'''