#!/usr/bin/env python3
"""
加密货币数据源智能选择器
根据数据需求和币种自动选择最佳数据源
"""

import os
from typing import Dict, List, Optional, Any
from enum import Enum

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')

# 导入统一日志系统
from tradingagents.utils.logging_init import setup_dataflow_logging
logger = setup_dataflow_logging()


class CryptoDataSource(Enum):
    """加密货币数据源枚举"""
    COINMARKETCAP = "coinmarketcap"
    COINGECKO = "coingecko"
    COINDESK = "coindesk"


class DataType(Enum):
    """数据类型枚举"""
    PRICE = "price"
    MARKET = "market"
    INFO = "info"
    NEWS = "news"
    SEARCH = "search"


class CryptoDataSourceSelector:
    """加密货币数据源智能选择器"""
    
    def __init__(self):
        """初始化数据源选择器"""
        self.available_sources = self._check_available_sources()
        self.source_priorities = self._get_source_priorities()
        
        logger.info(f"🪙 加密货币数据源选择器初始化完成")
        logger.info(f"   可用数据源: {[s.value for s in self.available_sources]}")
    
    def _check_available_sources(self) -> List[CryptoDataSource]:
        """检查可用的数据源"""
        available = []
        
        # 检查CoinMarketCap
        try:
            from .coinmarketcap_utils import CoinMarketCapAPI
            api = CoinMarketCapAPI()
            test_data = api.get_crypto_quotes('BTC')
            if test_data:
                available.append(CryptoDataSource.COINMARKETCAP)
                logger.info("✅ CoinMarketCap数据源可用")
        except Exception as e:
            logger.warning(f"⚠️ CoinMarketCap数据源不可用: {e}")
        
        # 检查CoinGecko
        try:
            from .coingecko_utils import CoinGeckoAPI
            api = CoinGeckoAPI()
            test_data = api.get_coin_list()
            if test_data:
                available.append(CryptoDataSource.COINGECKO)
                logger.info("✅ CoinGecko数据源可用")
        except Exception as e:
            logger.warning(f"⚠️ CoinGecko数据源不可用: {e}")
        
        # 检查CoinDesk
        try:
            from .coindesk_utils import CoinDeskAPI
            api = CoinDeskAPI()
            test_data = api.get_current_price()
            if test_data:
                available.append(CryptoDataSource.COINDESK)
                logger.info("✅ CoinDesk数据源可用")
        except Exception as e:
            logger.warning(f"⚠️ CoinDesk数据源不可用: {e}")
        
        return available
    
    def _get_source_priorities(self) -> Dict[DataType, List[CryptoDataSource]]:
        """获取不同数据类型的源优先级"""
        return {
            DataType.PRICE: [
                CryptoDataSource.COINMARKETCAP,  # 优先：数据质量高
                CryptoDataSource.COINGECKO,      # 备用：支持更多币种
                CryptoDataSource.COINDESK        # 最后：仅BTC
            ],
            DataType.MARKET: [
                CryptoDataSource.COINMARKETCAP,  # 优先：市场数据完整
                CryptoDataSource.COINGECKO       # 备用：市场数据详细
            ],
            DataType.INFO: [
                CryptoDataSource.COINGECKO,      # 优先：项目信息最详细
                CryptoDataSource.COINMARKETCAP   # 备用：基础项目信息
            ],
            DataType.NEWS: [
                CryptoDataSource.COINDESK,       # 优先：专业新闻
                CryptoDataSource.COINGECKO       # 备用：社区新闻
            ],
            DataType.SEARCH: [
                CryptoDataSource.COINGECKO,      # 优先：支持最多币种
                CryptoDataSource.COINMARKETCAP   # 备用：前100名币种
            ]
        }
    
    def select_best_source(self, data_type: DataType, symbol: str = None) -> Optional[CryptoDataSource]:
        """
        选择最佳数据源
        
        Args:
            data_type: 数据类型
            symbol: 加密货币符号（可选）
            
        Returns:
            最佳数据源
        """
        try:
            priorities = self.source_priorities.get(data_type, [])
            
            for source in priorities:
                if source in self.available_sources:
                    # 特殊处理：CoinDesk仅支持BTC
                    if source == CryptoDataSource.COINDESK and symbol and symbol.upper() != 'BTC':
                        continue
                    
                    logger.debug(f"🪙 选择数据源: {source.value} for {data_type.value}")
                    return source
            
            logger.warning(f"⚠️ 没有可用的数据源 for {data_type.value}")
            return None
            
        except Exception as e:
            logger.error(f"❌ 选择数据源失败: {e}")
            return None
    
    def get_data(self, symbol: str, data_type: str, **kwargs) -> str:
        """
        获取数据（自动选择最佳数据源）
        
        Args:
            symbol: 加密货币符号
            data_type: 数据类型
            **kwargs: 其他参数
            
        Returns:
            数据结果
        """
        try:
            # 转换数据类型
            try:
                data_type_enum = DataType(data_type.lower())
            except ValueError:
                logger.error(f"❌ 不支持的数据类型: {data_type}")
                return f"❌ 不支持的数据类型: {data_type}"
            
            # 选择最佳数据源
            best_source = self.select_best_source(data_type_enum, symbol)
            if not best_source:
                return f"❌ 没有可用的数据源获取 {data_type} 数据"
            
            # 调用对应的数据源
            if best_source == CryptoDataSource.COINMARKETCAP:
                from .crypto_data_source_manager import get_crypto_data_source_manager
                manager = get_crypto_data_source_manager()
                manager.set_current_source(manager.CryptoDataSource.COINMARKETCAP)
                return manager.get_crypto_data(symbol, **kwargs)
            
            elif best_source == CryptoDataSource.COINGECKO:
                from .crypto_data_source_manager import get_crypto_data_source_manager
                manager = get_crypto_data_source_manager()
                manager.set_current_source(manager.CryptoDataSource.COINGECKO)
                return manager.get_crypto_data(symbol, **kwargs)
            
            elif best_source == CryptoDataSource.COINDESK:
                from .coindesk_utils import get_coindesk_data
                return get_coindesk_data(symbol, data_type, **kwargs)
            
            else:
                return f"❌ 不支持的数据源: {best_source.value}"
                
        except Exception as e:
            logger.error(f"❌ 获取数据失败: {e}")
            return f"❌ 获取数据失败: {str(e)}"
    
    def get_source_recommendations(self) -> Dict[str, Any]:
        """获取数据源推荐信息"""
        return {
            "recommended_strategy": "混合数据源策略",
            "primary_source": "CoinMarketCap (价格、市场数据)",
            "secondary_source": "CoinGecko (项目信息、小众币种)",
            "news_source": "CoinDesk (专业新闻)",
            "coverage": {
                "top_100_crypto": "CoinMarketCap",
                "all_crypto": "CoinGecko", 
                "bitcoin_only": "CoinDesk",
                "news_analysis": "CoinDesk"
            },
            "api_limits": {
                "coinmarketcap": "10,000 calls/month (Free)",
                "coingecko": "Strict rate limits",
                "coindesk": "Relatively lenient"
            }
        }


# 全局数据源选择器实例
_data_source_selector = None

def get_crypto_data_source_selector() -> CryptoDataSourceSelector:
    """获取全局数据源选择器实例"""
    global _data_source_selector
    if _data_source_selector is None:
        _data_source_selector = CryptoDataSourceSelector()
    return _data_source_selector


def get_crypto_data_smart(symbol: str, data_type: str = "market", **kwargs) -> str:
    """
    智能获取加密货币数据（自动选择最佳数据源）
    
    Args:
        symbol: 加密货币符号
        data_type: 数据类型
        **kwargs: 其他参数
        
    Returns:
        数据结果
    """
    selector = get_crypto_data_source_selector()
    return selector.get_data(symbol, data_type, **kwargs)


if __name__ == "__main__":
    """测试脚本"""
    logger.info("🧪 加密货币数据源选择器测试")
    logger.info("=" * 50)
    
    selector = get_crypto_data_source_selector()
    
    # 测试数据源推荐
    recommendations = selector.get_source_recommendations()
    print("📋 数据源推荐:")
    for key, value in recommendations.items():
        print(f"  {key}: {value}")
    
    # 测试智能数据获取
    test_cases = [
        ("BTC", "price"),
        ("ETH", "market"),
        ("ADA", "info"),
        ("BTC", "news")
    ]
    
    for symbol, data_type in test_cases:
        print(f"\n🔍 测试获取 {symbol} 的 {data_type} 数据...")
        result = get_crypto_data_smart(symbol, data_type)
        print(f"结果长度: {len(result)}")
        print(f"结果预览: {result[:200]}...")
    
    logger.info("🎉 数据源选择器测试完成")
