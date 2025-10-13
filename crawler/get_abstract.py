import re
import bs4
from playwright.sync_api import sync_playwright
from semanticscholar import SemanticScholar

abs_len = 30

def get_abstract_from_semanticscholar(title):
    sch = SemanticScholar(timeout=10, retry=False)
    results = sch.search_paper(title, fields=["title", "abstract"], limit=1)
    if results[0]["abstract"]:
        return re.sub(r"\s+", " ", results[0]["abstract"].strip())
    else:
        return None


def abstract_scraper(url):
    with sync_playwright() as p:
        browser = p.firefox.launch()
        page = browser.new_page()
        page.goto(url, timeout=300000)
        html = page.content()
    html = re.sub("<br>", "\n", html)
    soup = convert_html2soup(html)
    res = find_abstract_from_soup(soup)
    return res


def detect_abstract(abstract):
    if len(abstract.text) > abs_len:
        res_abs = abstract
    else:
        next_element = abstract.find_next()
        if next_element and len(next_element.text) > abs_len:
            res_abs = next_element
        else:
            return find_abstract_from_soup(next_element)
    res_abs = re.sub('\s+', ' ', res_abs.text.strip())
    if res_abs[0:8].lower() == 'abstract':
        res_abs = res_abs[8:].strip()
        if res_abs.startswith(':'):
            res_abs = res_abs[1:].strip()
    return res_abs


def convert_html2soup(html):
    soup = bs4.BeautifulSoup(html, 'html.parser').body
    aria_hidden_elements = soup.find_all(attrs={"aria-hidden": "true"})
    for element in aria_hidden_elements:
        element.decompose()
    return soup


def find_abstract_from_soup(soup):
    origin_abstract = soup.find_all(class_='abstract')
    if not origin_abstract:
        origin_abstract = soup.find_all(string=lambda text: 'abstract' in text.lower())
    maybe_abstract = []
    for abstract in origin_abstract:
        if type(abstract) == bs4.element.NavigableString or type(abstract) == bs4.element.Tag:
            maybe_abstract.append(detect_abstract(abstract))
    abstract = max(maybe_abstract, key=len, default='')
    return abstract

def crawl_all_abstract(title, url):
    abstract = None
    try:
        abstract = get_abstract_from_semanticscholar(title)
    except:
        pass
    if not abstract or len(abstract) < abs_len:
        try:
            if url.endswith('.pdf'):
                url = url[:-4]
            abstract = abstract_scraper(url)
        except:
            pass
    return abstract



if __name__ == '__main__':
    ab = crawl_all_abstract("Attention Is All You Need", "https://arxiv.org/abs/1706.03762")
    print(ab)
