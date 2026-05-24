"""
能源可信数据空间 - 完整技术方案报告
最终组装脚本：整合所有章节，生成约50000字、100页的完整Word文档
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from report_utils import *
from generate_ch2 import write_ch2
from generate_ch3_5 import write_ch3, write_ch4, write_ch5
from generate_ch6_9 import write_ch6, write_ch7, write_ch8, write_ch9, write_references, write_appendix

TOTAL_WORDS_EST = 0

def count_section(name, words):
    global TOTAL_WORDS_EST
    TOTAL_WORDS_EST += words
    print(f"  [OK] {name} (约{words}字)")

def build_report():
    print("="*60)
    print("  能源可信数据空间 - 完整技术方案报告生成器")
    print("="*60)
    
    doc = init_document()
    print("\n[1/11] 生成封面...")
    write_cover(doc)
    count_section("封面", 500)
    
    print("[2/11] 生成摘要...")
    write_abstract(doc)
    count_section("摘要", 500)
    
    print("[3/11] 生成第一章：项目背景...")
    write_ch1(doc)
    count_section("第一章", 6000)
    
    print("[4/11] 生成第二章：技术需求分析...")
    write_ch2(doc)
    count_section("第二章", 8000)
    
    print("[5/11] 生成第三章：总体架构设计...")
    write_ch3(doc)
    count_section("第三章", 6000)
    
    print("[6/11] 生成第四章：核心技术创新点...")
    write_ch4(doc)
    count_section("第四章", 10000)
    
    print("[7/11] 生成第五章：关键技术实现细节...")
    write_ch5(doc)
    count_section("第五章", 8000)
    
    print("[8/11] 生成第六章：实验验证方案...")
    write_ch6(doc)
    count_section("第六章", 4500)
    
    print("[9/11] 生成第七章：性能测试结果与分析...")
    write_ch7(doc)
    count_section("第七章", 4000)
    
    print("[10/11] 生成第八章：应用价值分析...")
    write_ch8(doc)
    count_section("第八章", 3500)
    
    print("[11/11] 生成第九章+参考文献+附录...")
    write_ch9(doc)
    count_section("第九章", 4000)
    write_references(doc)
    count_section("参考文献", 600)
    write_appendix(doc)
    count_section("附录", 800)
    
    # 保存文件
    output_path = os.path.join(os.path.dirname(__file__), '能源可信数据空间_技术方案报告.docx')
    doc.save(output_path)
    
    print("\n" + "="*60)
    print(f"  报告生成完成！")
    print(f"  文件：{output_path}")
    print(f"  预估总字数：约{TOTAL_WORDS_EST}字")
    print(f"  预估页数：约{TOTAL_WORDS_EST//500}页 (按500字/页估算)")
    print("="*60)
    return output_path


if __name__=='__main__':
    output = build_report()
    print(f"\n最终文件: {output}")
