#!/usr/bin/env python3
"""
测试增强后的CryptoProjectAnalyst（带工具集）
"""

import sys
import os
sys.path.append('/app')

from web.utils.analysis_runner import run_stock_analysis

def test_enhanced_crypto_analyst():
    """测试增强后的加密货币分析师"""
    print("🧪 测试增强后的CryptoProjectAnalyst")
    print("=" * 60)
    
    def nop(*args, **kwargs): 
        pass
    
    # 测试BTC分析
    print("📊 开始分析BTC（使用增强工具集）...")
    
    try:
        res = run_stock_analysis(
            stock_symbol='BTC',
            analysis_date='2025-01-15',
            analysts=['fundamentals'],  # 只测试fundamentals分析师
            research_depth=1,
            llm_provider='deepseek',
            llm_model='deepseek-chat',
            market_type='加密货币',
            progress_callback=nop
        )
        
        print(f"✅ 分析完成")
        print(f"success: {res.get('success')}")
        
        state = res.get('state', {})
        fundamentals_report = state.get('fundamentals_report', '')
        print(f"fundamentals_report_len: {len(fundamentals_report)}")
        
        if fundamentals_report:
            print("\n📋 增强后的分析报告预览:")
            print("=" * 60)
            print(fundamentals_report[:1000])
            if len(fundamentals_report) > 1000:
                print("...")
                print(f"(报告总长度: {len(fundamentals_report)} 字符)")
        else:
            print("❌ 未生成分析报告")
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_crypto_analyst()
