#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试爬虫功能的脚本
调用get_google_scholar获取论文，然后对每篇论文调用enhance_paper_info增强信息
测试3篇论文的完整流程
"""

import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.get_scholar import get_google_scholar
from crawler.enhance_paper_info import enhance_paper_info

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_crawlers():
    """
    测试爬虫功能
    """
    # 搜索关键词
    keyword = "attention is all you need"
    year_low = 2016
    year_high = 2024
    limit_num = 1
    
    logger.info(f"开始测试爬虫功能，关键词: {keyword}，年份: {year_low}-{year_high}，数量: {limit_num}")
    
    # 调用get_google_scholar获取论文
    papers_generator = get_google_scholar(
        keyword=keyword,
        year_low=year_low,
        year_high=year_high,
        limit_num=limit_num
    )
    
    count = 0
    for item in papers_generator:
        if item.get('completed', False):
            logger.info(f"爬取完成: {item['message']}")
            if item.get('data') and isinstance(item['data'], list):
                logger.info(f"总共获取到 {len(item['data'])} 篇论文")
            continue
            
        if item.get('data') and not item.get('completed'):
            count += 1
            paper_info = item['data']
            logger.info(f"正在处理第 {count} 篇论文: {paper_info['title']}")
            
            # 调用enhance_paper_info增强论文信息
            enhanced_paper = enhance_paper_info(paper_info)
            
            # 输出增强后的信息
            logger.info(f"论文标题: {enhanced_paper['title']}")
            logger.info(f"发表年份: {enhanced_paper.get('pub_year', 'N/A')}")
            logger.info(f"引用次数: {enhanced_paper.get('num_citations', 'N/A')}")
            
            # 检查是否有PDF内容
            if enhanced_paper.get('pdf_content'):
                pdf_size = len(enhanced_paper['pdf_content'])
                logger.info(f"PDF内容已获取，大小: {pdf_size} 字节")
            else:
                logger.info("未获取到PDF内容")
                
            # 检查摘要
            abstract = enhanced_paper.get('abstract')
            if abstract:
                # 只显示摘要的前200个字符
                preview = abstract[:200] + "..." if len(abstract) > 200 else abstract
                logger.info(f"摘要预览: {preview}")
            else:
                logger.info("未获取到摘要")
                
            logger.info("-" * 50)

    logger.info("爬虫功能测试完成")


if __name__ == "__main__":
    test_crawlers()