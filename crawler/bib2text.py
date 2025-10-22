import bibtexparser
from apiModels import DBLPBibTeX
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

def clean_bib(bib):
    """
    清理并规范化BibTeX条目，去除重复项并修复格式问题
    
    Args:
        bib (str): 原始BibTeX字符串
        
    Returns:
        str: 清理后的BibTeX字符串
    """
    if not bib or not isinstance(bib, str):
        return ""
    
    # 使用bibtexparser解析BibTeX，这比手动解析更健壮
    try:
        parser = BibTexParser()
        parser.customization = convert_to_unicode
        bib_database = bibtexparser.loads(bib, parser=parser)
        # 跟踪已处理的标题以避免重复
        processed_titles = set()
        cleaned_entries = []
        # 处理每个条目
        for entry in bib_database.entries:
            # 获取标题并标准化
            title = entry.get('title', '').strip().lower()
            # 如果标题已存在，则跳过该条目
            if title and title in processed_titles:
                continue
            # 添加标题到已处理集合
            if title:
                processed_titles.add(title)
            # 将条目添加到清理后的列表中
            cleaned_entries.append(entry)
        # 创建新的BibDatabase并写回字符串
        cleaned_database = bibtexparser.bibdatabase.BibDatabase()
        cleaned_database.entries = cleaned_entries
        return bibtexparser.dumps(cleaned_database)
    except Exception:
        print(f"处理BibTeX条目时出错：{bib}")


def format_author(authors, style):
    """根据引用格式要求格式化作者列表"""
    if not authors:
        return ""

    names = authors.replace('\n', ' ').split(' and ')

    # 处理每个作者的名字格式
    formatted_names = []
    for name in names:
        # 处理"姓, 名"格式
        if ',' in name:
            parts = [p.strip() for p in name.split(',', 1)]
            if style == 'mla':
                formatted_names.append(f"{parts[0]}, {parts[1]}")
            else:
                # APA和GB/T使用名缩写
                initials = '. '.join([n[0] for n in parts[1].split() if n]) + '.'
                formatted_names.append(f"{parts[0]}, {initials}")
        else:
            # 处理"名 姓"格式
            parts = name.split()
            if len(parts) > 1:
                surname = parts[-1]
                given_names = ' '.join(parts[:-1])
                if style == 'mla':
                    formatted_names.append(f"{surname}, {given_names}")
                else:
                    initials = '. '.join([n[0] for n in given_names.split() if n]) + '.'
                    formatted_names.append(f"{surname}, {initials}")
            else:
                formatted_names.append(name)

    # 根据格式要求组合作者列表
    if style == 'gb7714':
        if len(formatted_names) > 3:
            return f"{', '.join(formatted_names[:3])}, 等"
        return ', '.join(formatted_names)

    if len(formatted_names) == 1:
        return formatted_names[0]

    if len(formatted_names) == 2:
        return f"{formatted_names[0]} and {formatted_names[1]}"

    return f"{', '.join(formatted_names[:-1])}, and {formatted_names[-1]}"


def format_title(title, style):
    """根据引用格式要求格式化标题"""
    title = title.strip('{}')

    if style == 'mla':
        # MLA格式标题：首字母大写（除冠词、介词等）
        words = title.split()
        capitalized = []
        for i, word in enumerate(words):
            if i == 0 or word.lower() not in ['a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 'on', 'at', 'to',
                                              'by', 'in', 'of']:
                capitalized.append(word.capitalize())
            else:
                capitalized.append(word.lower())
        return ' '.join(capitalized)

    # APA和GB/T格式标题：仅首单词首字母大写
    return title[0].upper() + title[1:]


def format_reference(entry, style='apa'):
    """根据条目类型和引用格式生成格式化引用"""
    entry_type = entry['ENTRYTYPE'].lower()
    author = format_author(entry.get('author', ''), style)
    year = entry.get('year', 'n.d.')
    title = format_title(entry.get('title', ''), style)

    # APA格式
    if style == 'apa':
        if entry_type == 'article':
            journal = entry.get('journal', '')
            volume = entry.get('volume', '')
            number = f"({entry['number']})" if 'number' in entry else ''
            pages = entry.get('pages', '')
            return f"{author} ({year}). {title}. {journal}, {volume}{number}, {pages}"

        elif entry_type == 'book':
            publisher = entry.get('publisher', '')
            return f"{author} ({year}). {title}. {publisher}."

        elif entry_type == 'inproceedings':
            booktitle = entry.get('booktitle', '')
            pages = entry.get('pages', '')
            res = f"{author} ({year}). {title}. In {booktitle}"
            if pages:
                res += f" (pp. {pages})"
            return res

        # 默认格式
        return f"{author} ({year}). {title}"

    # MLA格式
    elif style == 'mla':
        if entry_type == 'article':
            journal = entry.get('journal', '')
            volume = entry.get('volume', '')
            number = entry.get('number', '')
            pages = entry.get('pages', '')
            date = entry.get('date', year)
            res = f"{author}. \"{title}.\" {journal}"
            if volume:
                res += f", vol. {volume}"
            if number:
                res += f", no. {number}"
            if date:
                res += f", {date}"
            if pages:
                res += f", pp. {pages}"
            return res

        elif entry_type == 'book':
            publisher = entry.get('publisher', '')
            return f"{author}. {title}. {publisher}, {year}"

        elif entry_type == 'inproceedings':
            booktitle = entry.get('booktitle', '')
            pages = entry.get('pages', '')
            res = f"{author}. \"{title}.\" {booktitle}, {year}"
            if pages:
                res += f", pp. {pages}"
            return res
        # 默认格式
        return f"{author}. \"{title}.\" {year}"

    # GB/T 7714格式
    elif style == 'gb7714':
        if entry_type == 'article':
            journal = entry.get('journal', '')
            volume = entry.get('volume', '')
            number = entry.get('number', '')
            pages = entry.get('pages', '')
            res = f"{author}. {title}[J]. {journal}, {year}, {volume}"
            if number:
                res += f"({number})"
            if pages:
                res += f": {pages}"
            return res

        elif entry_type == 'book':
            publisher = entry.get('publisher', '')
            return f"{author}. {title}[M]. {publisher}, {year}"

        elif entry_type == 'inproceedings':
            booktitle = entry.get('booktitle', '')
            pages = entry.get('pages', '')
            return f"{author}. {title}[C]// {booktitle}. {year}: {pages}"

        # 默认格式
        return f"{author}. {title}[Z]. {year}"
    # 未知格式默认使用APA
    return format_reference(entry, 'apa')


def remove_trailing_punctuation(text):
    """
    去除字符串末尾的逗号和冒号
    
    Args:
        text (str): 输入字符串
        
    Returns:
        str: 去除末尾逗号和冒号后的字符串
    """
    if not text or not isinstance(text, str):
        return text
    text = text.strip()
    # 去除末尾的逗号和冒号
    while text and text[-1] in [',', ':']:
        text = text[:-1]
    
    return text.strip()


def bibtex_to_text(bibtex_str, style='apa'):
    """主函数：将BibTeX字符串转换为格式化文本"""
    # 先清理BibTeX数据
    cleaned_bibtex = clean_bib(bibtex_str)
    
    parser = BibTexParser()
    parser.customization = convert_to_unicode  # 处理特殊字符
    bib_db = bibtexparser.loads(cleaned_bibtex, parser=parser)

    output = []
    for entry in bib_db.entries:
        real_ref = format_reference(entry, style)
        # 去除末尾的逗号和冒号
        real_ref = remove_trailing_punctuation(real_ref)

        output.append(real_ref.strip() + '.')

    return '\n'.join(output)

if __name__ == '__main__':
    fetcher = DBLPBibTeX()
    bibtex_data = fetcher.get_bibtex("title:Attention is all you need year:2017")
    print(bibtex_data)

    print("APA格式:")
    bibtex_data = clean_bib(bibtex_data)
    print(bibtex_to_text(bibtex_data, 'apa'))

    print("\nMLA格式:")
    print(bibtex_to_text(bibtex_data, 'mla'))

    print("\nGB/T 7714格式:")
    print(bibtex_to_text(bibtex_data, 'gb7714'))