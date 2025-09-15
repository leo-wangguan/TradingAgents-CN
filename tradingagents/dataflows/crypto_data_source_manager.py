#!/usr/bin/env python3
"""
加密货币数据源管理器
统一管理加密货币数据源的选择和切换，支持CoinGecko、Binance、Coinbase等
"""

import os
import time
from typing import Dict, List, Optional, Any
from enum import Enum
import warnings

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')
warnings.filterwarnings('ignore')

# 导入统一日志系统
from tradingagents.utils.logging_init import setup_dataflow_logging
logger = setup_dataflow_logging()


class CryptoDataSource(Enum):
    """加密货币数据源枚举"""
    COINGECKO = "coingecko"
    COINMARKETCAP = "coinmarketcap"
    BINANCE = "binance"
    COINBASE = "coinbase"
    CRYPTOCOMPARE = "cryptocompare"


class CryptoDataSourceManager:
    """加密货币数据源管理器"""

    def __init__(self):
        """初始化加密货币数据源管理器"""
        self.default_source = self._get_default_source()
        self.available_sources = self._check_available_sources()
        self.current_source = self.default_source

        logger.info(f"🪙 加密货币数据源管理器初始化完成")
        logger.info(f"   默认数据源: {self.default_source.value}")
        logger.info(f"   可用数据源: {[s.value for s in self.available_sources]}")

    def _get_default_source(self) -> CryptoDataSource:
        """获取默认加密货币数据源"""
        env_source = os.getenv('DEFAULT_CRYPTO_DATA_SOURCE', 'coingecko').lower()
        
        source_mapping = {
            'coingecko': CryptoDataSource.COINGECKO,
            'coinmarketcap': CryptoDataSource.COINMARKETCAP,
            'binance': CryptoDataSource.BINANCE,
            'coinbase': CryptoDataSource.COINBASE,
            'cryptocompare': CryptoDataSource.CRYPTOCOMPARE
        }
        
        return source_mapping.get(env_source, CryptoDataSource.COINGECKO)
    
    def _check_available_sources(self) -> List[CryptoDataSource]:
        """检查可用的加密货币数据源"""
        available = []
        
        # 检查CoinMarketCap
        try:
            from .coinmarketcap_utils import CoinMarketCapAPI
            api = CoinMarketCapAPI()
            # 简单测试连接
            test_data = api.get_crypto_quotes('BTC')
            if test_data:
                available.append(CryptoDataSource.COINMARKETCAP)
                logger.info("✅ CoinMarketCap数据源可用")
            else:
                logger.warning("⚠️ CoinMarketCap数据源不可用: API连接失败")
        except ImportError:
            logger.warning("⚠️ CoinMarketCap数据源不可用: 依赖库未安装")
        except Exception as e:
            logger.warning(f"⚠️ CoinMarketCap数据源不可用: {e}")
        
        # 检查CoinGecko
        try:
            from .coingecko_utils import CoinGeckoAPI
            api = CoinGeckoAPI()
            # 简单测试连接
            test_data = api.get_coin_list()
            if test_data:
                available.append(CryptoDataSource.COINGECKO)
                logger.info("✅ CoinGecko数据源可用")
            else:
                logger.warning("⚠️ CoinGecko数据源不可用: API连接失败")
        except ImportError:
            logger.warning("⚠️ CoinGecko数据源不可用: 依赖库未安装")
        except Exception as e:
            logger.warning(f"⚠️ CoinGecko数据源不可用: {e}")
        
        # 检查Binance (预留)
        try:
            # 这里可以添加Binance API检查
            # available.append(CryptoDataSource.BINANCE)
            pass
        except Exception as e:
            logger.debug(f"Binance数据源检查跳过: {e}")
        
        # 检查Coinbase (预留)
        try:
            # 这里可以添加Coinbase API检查
            # available.append(CryptoDataSource.COINBASE)
            pass
        except Exception as e:
            logger.debug(f"Coinbase数据源检查跳过: {e}")
        
        # 检查CryptoCompare (预留)
        try:
            # 这里可以添加CryptoCompare API检查
            # available.append(CryptoDataSource.CRYPTOCOMPARE)
            pass
        except Exception as e:
            logger.debug(f"CryptoCompare数据源检查跳过: {e}")
        
        return available
    
    def get_current_source(self) -> CryptoDataSource:
        """获取当前数据源"""
        return self.current_source
    
    def set_current_source(self, source: CryptoDataSource) -> bool:
        """设置当前数据源"""
        if source in self.available_sources:
            self.current_source = source
            logger.info(f"✅ 加密货币数据源已切换到: {source.value}")
            return True
        else:
            logger.error(f"❌ 加密货币数据源不可用: {source.value}")
            return False
    
    def get_crypto_data(self, coin_id: str, vs_currency: str = "usd", 
                       days: int = 30, data_type: str = "market") -> str:
        """
        获取加密货币数据
        
        Args:
            coin_id: 加密货币ID (如 'bitcoin', 'ethereum')
            vs_currency: 计价货币 (默认USD)
            days: 数据天数
            data_type: 数据类型 ('market', 'info', 'search')
            
        Returns:
            str: 格式化的加密货币数据报告
        """
        logger.info(f"🪙 [加密货币数据获取] 开始获取数据",
                   extra={
                       'coin_id': coin_id,
                       'vs_currency': vs_currency,
                       'days': days,
                       'data_type': data_type,
                       'data_source': self.current_source.value,
                       'event_type': 'crypto_data_fetch_start'
                   })

        start_time = time.time()

        try:
            if self.current_source == CryptoDataSource.COINMARKETCAP:
                result = self._get_coinmarketcap_data(coin_id, vs_currency, days, data_type)
            elif self.current_source == CryptoDataSource.COINGECKO:
                result = self._get_coingecko_data(coin_id, vs_currency, days, data_type)
            elif self.current_source == CryptoDataSource.BINANCE:
                result = self._get_binance_data(coin_id, vs_currency, days, data_type)
            elif self.current_source == CryptoDataSource.COINBASE:
                result = self._get_coinbase_data(coin_id, vs_currency, days, data_type)
            elif self.current_source == CryptoDataSource.CRYPTOCOMPARE:
                result = self._get_cryptocompare_data(coin_id, vs_currency, days, data_type)
            else:
                result = f"❌ 不支持的加密货币数据源: {self.current_source.value}"

            # 记录结果
            duration = time.time() - start_time
            result_length = len(result) if result else 0
            is_success = result and "❌" not in result and "错误" not in result

            if is_success:
                logger.info(f"✅ [加密货币数据获取] 成功获取数据",
                           extra={
                               'coin_id': coin_id,
                               'data_source': self.current_source.value,
                               'duration': duration,
                               'result_length': result_length,
                               'event_type': 'crypto_data_fetch_success'
                           })
            else:
                logger.warning(f"⚠️ [加密货币数据获取] 数据获取失败",
                              extra={
                                  'coin_id': coin_id,
                                  'data_source': self.current_source.value,
                                  'duration': duration,
                                  'result_length': result_length,
                                  'event_type': 'crypto_data_fetch_warning'
                              })

            return result

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ [加密货币数据获取] 异常失败: {e}",
                        extra={
                            'coin_id': coin_id,
                            'data_source': self.current_source.value,
                            'duration': duration,
                            'error': str(e),
                            'event_type': 'crypto_data_fetch_exception'
                        }, exc_info=True)
            return f"❌ 获取加密货币数据失败: {str(e)}"
    
    def search_crypto(self, query: str) -> str:
        """
        搜索加密货币
        
        Args:
            query: 搜索关键词
            
        Returns:
            str: 搜索结果
        """
        try:
            if self.current_source == CryptoDataSource.COINMARKETCAP:
                return self._search_coinmarketcap(query)
            elif self.current_source == CryptoDataSource.COINGECKO:
                return self._search_coingecko(query)
            elif self.current_source == CryptoDataSource.BINANCE:
                return self._search_binance(query)
            elif self.current_source == CryptoDataSource.COINBASE:
                return self._search_coinbase(query)
            elif self.current_source == CryptoDataSource.CRYPTOCOMPARE:
                return self._search_cryptocompare(query)
            else:
                return f"❌ 不支持的加密货币数据源: {self.current_source.value}"
                
        except Exception as e:
            logger.error(f"❌ 搜索加密货币失败: {e}")
            return f"❌ 搜索加密货币失败: {str(e)}"
    
    # ==================== CoinMarketCap数据接口 ====================
    
    def _get_coinmarketcap_data(self, coin_id: str, vs_currency: str, 
                               days: int, data_type: str) -> str:
        """使用CoinMarketCap获取加密货币数据"""
        try:
            from .coinmarketcap_utils import get_crypto_data_cmc, format_crypto_data_for_analysis_cmc
            
            # 将coin_id转换为符号格式（CoinMarketCap使用符号而不是ID）
            symbol = coin_id.upper()
            
            if data_type == "market":
                crypto_data = get_crypto_data_cmc(symbol, "quotes", vs_currency.upper())
                if crypto_data:
                    return format_crypto_data_for_analysis_cmc(crypto_data, symbol)
                else:
                    return f"❌ 无法获取 {symbol} 的市场数据"
            elif data_type == "info":
                crypto_info = get_crypto_data_cmc(symbol, "info")
                if crypto_info:
                    return format_crypto_data_for_analysis_cmc(crypto_info, symbol)
                else:
                    return f"❌ 无法获取 {symbol} 的详细信息"
            elif data_type == "search":
                search_results = get_crypto_data_cmc(symbol, "search")
                if search_results:
                    return self._format_crypto_search_results(search_results)
                else:
                    return f"❌ 搜索 '{symbol}' 无结果"
            else:
                return f"❌ 不支持的数据类型: {data_type}"
                
        except Exception as e:
            logger.error(f"❌ CoinMarketCap数据获取失败: {e}")
            return f"❌ CoinMarketCap数据获取失败: {str(e)}"
    
    def _search_coinmarketcap(self, query: str) -> str:
        """使用CoinMarketCap搜索加密货币"""
        try:
            from .coinmarketcap_utils import CoinMarketCapAPI
            api = CoinMarketCapAPI()
            results = api.search_crypto(query)
            return self._format_crypto_search_results(results)
        except Exception as e:
            logger.error(f"❌ CoinMarketCap搜索失败: {e}")
            return f"❌ CoinMarketCap搜索失败: {str(e)}"
    
    # ==================== CoinGecko数据接口 ====================
    
    def _convert_symbol_to_coingecko_id(self, symbol: str) -> str:
        """将符号转换为CoinGecko的币种ID"""
        # CoinGecko使用小写的币种ID，而不是符号
        symbol_to_id = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum', 
            'ADA': 'cardano',
            'DOT': 'polkadot',
            'LINK': 'chainlink',
            'MATIC': 'matic-network',
            'AVAX': 'avalanche-2',
            'SOL': 'solana',
            'ATOM': 'cosmos',
            'NEAR': 'near',
            'FTM': 'fantom',
            'ALGO': 'algorand',
            'VET': 'vechain',
            'ICP': 'internet-computer',
            'FIL': 'filecoin',
            'TRX': 'tron',
            'XRP': 'ripple',
            'LTC': 'litecoin',
            'BCH': 'bitcoin-cash',
            'EOS': 'eos',
            'XLM': 'stellar',
            'XTZ': 'tezos',
            'ZEC': 'zcash',
            'DASH': 'dash',
            'NEO': 'neo',
            'IOTA': 'iota',
            'ONT': 'ontology',
            'QTUM': 'qtum',
            'ZIL': 'zilliqa',
            'ICX': 'icon',
            'WAVES': 'waves',
            'KMD': 'komodo',
            'SC': 'siacoin',
            'DCR': 'decred',
            'LSK': 'lisk',
            'ARK': 'ark',
            'REP': 'augur',
            'GNT': 'golem',
            'BAT': 'basic-attention-token',
            'ZRX': '0x',
            'KNC': 'kyber-network-crystal',
            'LRC': 'loopring',
            'OMG': 'omg',
            'SNT': 'status',
            'MKR': 'maker',
            'DAI': 'dai',
            'USDC': 'usd-coin',
            'USDT': 'tether',
            'BUSD': 'binance-usd',
            'TUSD': 'true-usd',
            'PAX': 'paxos-standard',
            'GUSD': 'gemini-dollar',
            'SUSD': 'nusd',
            'FRAX': 'frax',
            'LUSD': 'liquity-usd',
            'DUSD': 'defidollar',
            'CUSD': 'celo-dollar',
            'MUSD': 'musd',
            'RSV': 'reserve',
            'USDK': 'usdk',
            'USDN': 'neutrino-usd',
            'USDP': 'paxos-standard',
            'USDS': 'stableusd',
            'USDT': 'tether',
            'USDC': 'usd-coin',
            'BUSD': 'binance-usd',
            'TUSD': 'true-usd',
            'PAX': 'paxos-standard',
            'GUSD': 'gemini-dollar',
            'SUSD': 'nusd',
            'FRAX': 'frax',
            'LUSD': 'liquity-usd',
            'DUSD': 'defidollar',
            'CUSD': 'celo-dollar',
            'MUSD': 'musd',
            'RSV': 'reserve',
            'USDK': 'usdk',
            'USDN': 'neutrino-usd',
            'USDP': 'paxos-standard',
            'USDS': 'stableusd'
        }
        
        # 如果已经是小写，可能是ID，直接返回
        if symbol.islower():
            return symbol
            
        # 转换为大写后查找映射
        symbol_upper = symbol.upper()
        return symbol_to_id.get(symbol_upper, symbol.lower())
    
    def _get_coingecko_data(self, coin_id: str, vs_currency: str, 
                           days: int, data_type: str) -> str:
        """使用CoinGecko获取加密货币数据"""
        try:
            from .coingecko_utils import get_crypto_data, format_crypto_data_for_analysis
            
            # 将符号转换为CoinGecko的币种ID
            coin_id = self._convert_symbol_to_coingecko_id(coin_id)
            
            if data_type == "market":
                crypto_data = get_crypto_data(coin_id, vs_currency, days, "market")
                if crypto_data:
                    return format_crypto_data_for_analysis(crypto_data)
                else:
                    return f"❌ 无法获取 {coin_id} 的市场数据"
            elif data_type == "info":
                crypto_info = get_crypto_data(coin_id, vs_currency, days, "info")
                if crypto_info:
                    return self._format_crypto_info(crypto_info)
                else:
                    return f"❌ 无法获取 {coin_id} 的详细信息"
            elif data_type == "search":
                search_results = get_crypto_data(coin_id, vs_currency, days, "search")
                if search_results:
                    return self._format_crypto_search_results(search_results)
                else:
                    return f"❌ 搜索 '{coin_id}' 无结果"
            else:
                return f"❌ 不支持的数据类型: {data_type}"
                
        except Exception as e:
            logger.error(f"❌ CoinGecko数据获取失败: {e}")
            return f"❌ CoinGecko数据获取失败: {str(e)}"
    
    def _search_coingecko(self, query: str) -> str:
        """使用CoinGecko搜索加密货币"""
        try:
            from .coingecko_utils import CoinGeckoAPI
            api = CoinGeckoAPI()
            results = api.search_coins(query)
            return self._format_crypto_search_results(results)
        except Exception as e:
            logger.error(f"❌ CoinGecko搜索失败: {e}")
            return f"❌ CoinGecko搜索失败: {str(e)}"
    
    # ==================== Binance数据接口 (预留) ====================
    
    def _get_binance_data(self, coin_id: str, vs_currency: str, 
                         days: int, data_type: str) -> str:
        """使用Binance获取加密货币数据 (预留)"""
        return f"❌ Binance数据源暂未实现"
    
    def _search_binance(self, query: str) -> str:
        """使用Binance搜索加密货币 (预留)"""
        return f"❌ Binance搜索暂未实现"
    
    # ==================== Coinbase数据接口 (预留) ====================
    
    def _get_coinbase_data(self, coin_id: str, vs_currency: str, 
                          days: int, data_type: str) -> str:
        """使用Coinbase获取加密货币数据 (预留)"""
        return f"❌ Coinbase数据源暂未实现"
    
    def _search_coinbase(self, query: str) -> str:
        """使用Coinbase搜索加密货币 (预留)"""
        return f"❌ Coinbase搜索暂未实现"
    
    # ==================== CryptoCompare数据接口 (预留) ====================
    
    def _get_cryptocompare_data(self, coin_id: str, vs_currency: str, 
                               days: int, data_type: str) -> str:
        """使用CryptoCompare获取加密货币数据 (预留)"""
        return f"❌ CryptoCompare数据源暂未实现"
    
    def _search_cryptocompare(self, query: str) -> str:
        """使用CryptoCompare搜索加密货币 (预留)"""
        return f"❌ CryptoCompare搜索暂未实现"
    
    # ==================== 数据格式化方法 ====================
    
    def _format_crypto_info(self, crypto_info: Dict) -> str:
        """格式化加密货币详细信息"""
        try:
            name = crypto_info.get('name', 'Unknown')
            symbol = crypto_info.get('symbol', '').upper()
            description = crypto_info.get('description', '')
            homepage = crypto_info.get('homepage', '')
            categories = crypto_info.get('categories', [])
            market_data = crypto_info.get('market_data', {})
            
            current_price = market_data.get('current_price', {}).get('usd', 0)
            market_cap = market_data.get('market_cap', {}).get('usd', 0)
            total_volume = market_data.get('total_volume', {}).get('usd', 0)
            
            report = f"""
🪙 加密货币详细信息: {name} ({symbol})

📊 基本信息:
- 名称: {name}
- 符号: {symbol}
- 官网: {homepage}
- 分类: {', '.join(categories[:5])}

💰 市场数据:
- 当前价格: ${current_price:,.2f}
- 市值: ${market_cap:,.0f}
- 24小时交易量: ${total_volume:,.0f}

📝 项目描述:
{description[:500]}{'...' if len(description) > 500 else ''}
"""
            return report
            
        except Exception as e:
            logger.error(f"❌ 格式化加密货币信息失败: {e}")
            return f"❌ 格式化加密货币信息失败: {str(e)}"
    
    def _format_crypto_search_results(self, results: List[Dict]) -> str:
        """格式化加密货币搜索结果"""
        try:
            if not results:
                return "❌ 未找到匹配的加密货币"
            
            report = f"🔍 加密货币搜索结果 (共{len(results)}个):\n\n"
            
            for i, coin in enumerate(results[:10], 1):  # 只显示前10个结果
                coin_id = coin.get('id', 'Unknown')
                name = coin.get('name', 'Unknown')
                symbol = coin.get('symbol', '').upper()
                market_cap_rank = coin.get('market_cap_rank', 'N/A')
                
                report += f"{i}. {name} ({symbol})\n"
                report += f"   ID: {coin_id}\n"
                report += f"   市值排名: {market_cap_rank}\n\n"
            
            if len(results) > 10:
                report += f"... 还有 {len(results) - 10} 个结果\n"
            
            return report
            
        except Exception as e:
            logger.error(f"❌ 格式化搜索结果失败: {e}")
            return f"❌ 格式化搜索结果失败: {str(e)}"


# 全局加密货币数据源管理器实例
_crypto_data_source_manager = None

def get_crypto_data_source_manager() -> CryptoDataSourceManager:
    """获取全局加密货币数据源管理器实例"""
    global _crypto_data_source_manager
    if _crypto_data_source_manager is None:
        _crypto_data_source_manager = CryptoDataSourceManager()
    return _crypto_data_source_manager


# ==================== 统一接口函数 ====================

def get_crypto_data_unified(coin_id: str, vs_currency: str = "usd", 
                           days: int = 30, data_type: str = "market") -> str:
    """
    统一的加密货币数据获取接口
    自动使用配置的加密货币数据源

    Args:
        coin_id: 加密货币ID (如 'bitcoin', 'ethereum')
        vs_currency: 计价货币 (默认USD)
        days: 数据天数
        data_type: 数据类型 ('market', 'info', 'search')

    Returns:
        str: 格式化的加密货币数据报告
    """
    manager = get_crypto_data_source_manager()
    return manager.get_crypto_data(coin_id, vs_currency, days, data_type)


def search_crypto_unified(query: str) -> str:
    """
    统一的加密货币搜索接口

    Args:
        query: 搜索关键词

    Returns:
        str: 搜索结果
    """
    manager = get_crypto_data_source_manager()
    return manager.search_crypto(query)
