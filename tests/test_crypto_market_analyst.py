#!/usr/bin/env python3
"""
测试Market Analyst的加密货币支持
"""

import sys
import os
sys.path.append('.')

def test_crypto_market_analyst():
    """测试Market Analyst对加密货币的支持"""
    print("🧪 测试Market Analyst的加密货币支持")
    print("=" * 60)
    
    try:
        from tradingagents.agents.analysts.market_analyst import create_market_analyst
        from tradingagents.agents.utils.agent_utils import Toolkit
        from tradingagents.default_config import DEFAULT_CONFIG
        from tradingagents.llm_adapters.deepseek_adapter import ChatDeepSeek
        
        # 创建配置
        config = DEFAULT_CONFIG.copy()
        config['online_tools'] = True
        
        # 创建工具包
        toolkit = Toolkit(config)
        print("✅ 工具包初始化完成")
        
        # 创建DeepSeek LLM
        llm = ChatDeepSeek(
            model='deepseek-chat',
            temperature=0.1,
            max_tokens=2000
        )
        print("✅ DeepSeek LLM初始化完成")
        
        # 创建市场分析师
        market_analyst = create_market_analyst(llm, toolkit)
        print("✅ Market Analyst创建完成")
        
        # 测试加密货币分析
        test_state = {
            'trade_date': '2025-01-15',
            'company_of_interest': 'BTC',
            'messages': []
        }
        
        print(f"\n📊 开始分析加密货币: {test_state['company_of_interest']}")
        print("=" * 60)
        
        result = market_analyst(test_state)
        
        print("✅ Market Analyst分析完成")
        print(f"消息数量: {len(result.get('messages', []))}")
        
        market_report = result.get('market_report', '')
        print(f"市场报告长度: {len(market_report)} 字符")
        
        if len(market_report) > 100:
            print("\n📈 市场报告内容:")
            print("-" * 50)
            print(market_report[:800])
            print("-" * 50)
            
            # 检查报告质量
            has_crypto_keywords = any(keyword in market_report for keyword in ['BTC', 'Bitcoin', '加密货币', '价格', '技术指标'])
            has_analysis = len(market_report) > 500
            
            print(f"\n📊 报告质量检查:")
            print(f"包含加密货币关键词: {has_crypto_keywords}")
            print(f"分析内容充分: {has_analysis}")
            
            if has_crypto_keywords and has_analysis:
                print("🎉 Market Analyst加密货币分析测试成功！")
                return True
            else:
                print("⚠️ 报告质量需要改进")
                return False
        else:
            print("❌ 市场报告内容异常:")
            print(market_report)
            return False
            
    except Exception as e:
        print(f"❌ Market Analyst测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_crypto_market_analyst()
    if success:
        print("\n🎉 所有测试通过！")
    else:
        print("\n❌ 测试失败！")
