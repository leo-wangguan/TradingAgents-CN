#!/usr/bin/env python3
"""
测试PDF解析功能
验证白皮书下载和解析的完整流程
"""

import sys
import os
sys.path.append('/app')

from tradingagents.dataflows.whitepaper_parser import get_whitepaper_parser

def test_pdf_parsing():
    """测试PDF解析功能"""
    print("🧪 测试PDF解析功能")
    print("=" * 60)
    
    parser = get_whitepaper_parser()
    
    # 测试已知的PDF白皮书链接
    test_cases = [
        {
            "coin_id": "bitcoin",
            "url": "https://bitcoin.org/bitcoin.pdf",
            "description": "Bitcoin原始白皮书"
        },
        {
            "coin_id": "ethereum", 
            "url": "https://ethereum.org/en/whitepaper/",
            "description": "Ethereum白皮书页面"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📄 测试: {test_case['description']}")
        print(f"币种: {test_case['coin_id']}")
        print(f"URL: {test_case['url']}")
        print("-" * 40)
        
        try:
            # 解析白皮书
            result = parser.parse_whitepaper(test_case['url'], test_case['coin_id'])
            
            if "error" in result:
                print(f"❌ 解析失败: {result['error']}")
            else:
                print(f"✅ 解析成功!")
                print(f"- 页数: {result.get('pages', 'N/A')}")
                print(f"- 文本长度: {len(result.get('text', ''))} 字符")
                
                # 显示结构化信息
                sections = result.get('sections', {})
                if sections:
                    print(f"- 结构化信息:")
                    for section_name, content_list in sections.items():
                        if content_list:
                            section_display = {
                                'team_info': '👥 团队信息',
                                'tokenomics': '💰 代币经济学',
                                'technology': '🔧 技术架构',
                                'roadmap': '🗺️ 路线图',
                                'governance': '🏛️ 治理结构',
                                'economics': '💼 经济模型',
                                'security': '🔒 安全机制',
                                'use_cases': '📱 应用场景'
                            }.get(section_name, section_name)
                            
                            print(f"  {section_display}: {len(content_list)} 条")
                            # 显示前2条内容
                            for i, item in enumerate(content_list[:2]):
                                print(f"    {i+1}. {item[:80]}...")
                
                # 显示文本预览
                text = result.get('text', '')
                if text:
                    print(f"- 文本预览:")
                    print(f"  {text[:200]}...")
                    
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🎉 PDF解析功能测试完成!")

if __name__ == "__main__":
    test_pdf_parsing()
