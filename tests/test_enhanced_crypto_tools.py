#!/usr/bin/env python3
"""
测试增强后的加密货币分析工具
验证工具是否真正利用了白皮书内容
"""

import sys
import os
sys.path.append('/app')

from tradingagents.agents.utils.agent_utils import Toolkit

def test_enhanced_crypto_tools():
    """测试增强后的加密货币分析工具"""
    print("🧪 测试增强后的加密货币分析工具")
    print("=" * 60)
    
    toolkit = Toolkit()
    
    # 测试币种
    test_coin = "ethereum"
    
    print(f"\n📊 测试币种: {test_coin.upper()}")
    print("-" * 40)
    
    try:
        # 测试团队治理分析
        print("👥 测试团队治理分析...")
        team_result = toolkit.get_crypto_team_governance.invoke({"coin_id": test_coin})
        print(f"✅ 团队治理分析完成，长度: {len(team_result)}")
        print(f"预览: {team_result[:300]}...")
        
        # 测试Tokenomics分析
        print("\n💰 测试Tokenomics分析...")
        tokenomics_result = toolkit.get_crypto_detailed_tokenomics.invoke({"coin_id": test_coin})
        print(f"✅ Tokenomics分析完成，长度: {len(tokenomics_result)}")
        print(f"预览: {tokenomics_result[:300]}...")
        
        # 测试路线图分析
        print("\n🗺️ 测试路线图分析...")
        roadmap_result = toolkit.get_crypto_roadmap_development.invoke({"coin_id": test_coin})
        print(f"✅ 路线图分析完成，长度: {len(roadmap_result)}")
        print(f"预览: {roadmap_result[:300]}...")
        
        # 测试社区活跃度分析
        print("\n👥 测试社区活跃度分析...")
        community_result = toolkit.get_crypto_community_activity.invoke({"coin_id": test_coin})
        print(f"✅ 社区活跃度分析完成，长度: {len(community_result)}")
        print(f"预览: {community_result[:300]}...")
        
        print("\n🎉 所有工具测试完成！")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_crypto_tools()
