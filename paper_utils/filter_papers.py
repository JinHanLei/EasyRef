import pandas as pd
import os


def filter_papers_by_keyword(input_file, keyword, output_file=None):
    """
    从CSV文件中过滤出标题包含特定关键词的记录
    
    参数:
        input_file: 输入CSV文件路径
        keyword: 需要包含的关键词，不区分大小写
        output_file: 输出CSV文件路径，默认为None时自动生成
    
    返回:
        输出文件路径
    """
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误：文件 {input_file} 不存在")
        return None
    
    # 读取CSV文件
    try:
        data = pd.read_csv(input_file)
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return None
        
    # 检查是否包含title列
    if "title" not in data.columns:
        print("错误：输入文件必须包含title列")
        return None
    
    # 按标题关键词过滤
    print(f"原始数据记录数: {len(data)}")
    
    # 将关键词转为小写进行不区分大小写的匹配
    keyword_lower = keyword.lower()
    
    # 过滤掉不包含关键词的记录
    filtered_data = data[data["title"].str.lower().str.contains(keyword_lower, na=False)]
    
    print(f"过滤后记录数: {len(filtered_data)}")
    print(f"删除了 {len(data) - len(filtered_data)} 条不包含关键词 '{keyword}' 的记录")
    
    # 如果没有指定输出文件，则生成默认输出文件名
    if output_file is None:
        file_name, file_ext = os.path.splitext(input_file)
        output_file = f"{file_name}_with_{keyword}{file_ext}"
    
    # 保存过滤后的数据
    filtered_data.to_csv(output_file, index=False)
    print(f"过滤后的数据已保存到 {output_file}")
    
    return output_file


if __name__ == "__main__":
    # 设置默认关键词
    keyword = "summar"
    
    input_file = 'data/summarization_llm_new_20250512.csv'
    # 执行过滤
    result_file = filter_papers_by_keyword(input_file, keyword)
    