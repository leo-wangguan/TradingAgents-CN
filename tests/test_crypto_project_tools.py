#!/usr/bin/env python3
"""
测试CryptoProjectAnalyst的专用工具集
"""

import sys
import os
sys.path.append('/app')

from tradingagents.agents.utils.agent_utils import Toolkit

def test_crypto_project_tools():
    """测试加密货币项目工具集"""
    print("🧪 测试CryptoProjectAnalyst专用工具集")
    print("=" * 60)
    
    # 创建Toolkit实例
    toolkit = Toolkit()
    
    # 测试币种
    test_coins = ["bitcoin", "ethereum", "cardano"]
    
    for coin_id in test_coins:
        print(f"\n📊 测试币种: {coin_id.upper()}")
        print("-" * 40)
        
        try:
            # 测试白皮书分析
            print("📄 测试白皮书分析...")
            whitepaper_result = toolkit.get_crypto_whitepaper_analysis.invoke({"coin_id": coin_id})
            print(f"✅ 白皮书分析完成，长度: {len(whitepaper_result)}")
            print(f"预览: {whitepaper_result[:200]}...")
            
            # 测试团队和治理信息
            print("\n👥 测试团队和治理信息...")
            team_result = toolkit.get_crypto_team_governance.invoke({"coin_id": coin_id})
            print(f"✅ 团队信息获取完成，长度: {len(team_result)}")
            print(f"预览: {team_result[:200]}...")
            
            # 测试Tokenomics分析
            print("\n💰 测试Tokenomics分析...")
            tokenomics_result = toolkit.get_crypto_detailed_tokenomics.invoke({"coin_id": coin_id})
            print(f"✅ Tokenomics分析完成，长度: {len(tokenomics_result)}")
            print(f"预览: {tokenomics_result[:200]}...")
            
            # 测试路线图分析
            print("\n🗺️ 测试路线图分析...")
            roadmap_result = toolkit.get_crypto_roadmap_development.invoke({"coin_id": coin_id})
            print(f"✅ 路线图分析完成，长度: {len(roadmap_result)}")
            print(f"预览: {roadmap_result[:200]}...")
            
            # 测试社区活跃度
            print("\n👥 测试社区活跃度...")
            community_result = toolkit.get_crypto_community_activity.invoke({"coin_id": coin_id})
            print(f"✅ 社区活跃度分析完成，长度: {len(community_result)}")
            print(f"预览: {community_result[:200]}...")
            
        except Exception as e:
            print(f"❌ 测试 {coin_id} 时发生错误: {e}")
            continue
    
    print("\n🎉 工具集测试完成！")

if __name__ == "__main__":
    test_crypto_project_tools()
