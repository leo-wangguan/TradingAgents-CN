#!/usr/bin/env python3
"""
CoinMarketCap加密货币数据获取工具
提供加密货币价格、市场数据、项目信息等数据获取功能
"""

import os
import time
import requests
import pandas as pd
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')

# 导入统一日志系统
from tradingagents.utils.logging_init import setup_dataflow_logging
logger = setup_dataflow_logging()


class CoinMarketCapAPI:
    """CoinMarketCap API客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化CoinMarketCap API客户端
        
        Args:
            api_key: CoinMarketCap API密钥（必需）
        """
        self.api_key = api_key or os.getenv('COINMARKETCAP_API_KEY')
        if not self.api_key:
            raise ValueError("CoinMarketCap API密钥未设置，请设置COINMARKETCAP_API_KEY环境变量")
        
        self.base_url = "https://pro-api.coinmarketcap.com/v1"
        self.session = requests.Session()
        
        # 设置请求头
        self.session.headers.update({
            'X-CMC_PRO_API_KEY': self.api_key,
            'Accept': 'application/json'
        })
        
        # 请求限制控制
        self.last_request_time = 0
        self.min_request_interval = 2.0  # Free用户限制：每分钟30次请求，即每2秒1次
        
        logger.info(f"🪙 CoinMarketCap API客户端初始化完成")
        logger.info(f"   API密钥: {'已配置' if self.api_key else '未配置'}")
    
    def _rate_limit(self):
        """控制请求频率"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        发送API请求
        
        Args:
            endpoint: API端点
            params: 请求参数
            
        Returns:
            API响应数据
        """
        self._rate_limit()
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"🪙 CoinMarketCap API请求成功: {endpoint}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ CoinMarketCap API请求失败: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ CoinMarketCap API响应解析失败: {e}")
            raise
    
    def get_crypto_listings(self, limit: int = 100, start: int = 1) -> List[Dict]:
        """
        获取加密货币列表（Free用户限制前100名）
        
        Args:
            limit: 返回数量限制（最大100）
            start: 起始位置
            
        Returns:
            加密货币列表
        """
        try:
            params = {
                'start': start,
                'limit': min(limit, 100),  # Free用户限制
                'convert': 'USD'
            }
            
            data = self._make_request("cryptocurrency/listings/latest", params)
            listings = data.get('data', [])
            
            logger.info(f"📋 获取到 {len(listings)} 个加密货币")
            return listings
            
        except Exception as e:
            logger.error(f"❌ 获取加密货币列表失败: {e}")
            return []
    
    def get_crypto_quotes(self, symbol: str, convert: str = "USD") -> Dict:
        """
        获取加密货币最新报价
        
        Args:
            symbol: 加密货币符号（如 'BTC', 'ETH'）
            convert: 转换货币（默认USD）
            
        Returns:
            报价数据
        """
        try:
            params = {
                'symbol': symbol.upper(),
                'convert': convert
            }
            
            data = self._make_request("cryptocurrency/quotes/latest", params)
            quotes = data.get('data', {})
            
            if symbol.upper() in quotes:
                logger.info(f"📊 获取 {symbol} 报价成功")
                return quotes[symbol.upper()]
            else:
                logger.warning(f"⚠️ 未找到 {symbol} 的报价数据")
                return {}
                
        except Exception as e:
            logger.error(f"❌ 获取 {symbol} 报价失败: {e}")
            return {}
    
    def get_crypto_info(self, symbol: str) -> Dict:
        """
        获取加密货币详细信息
        
        Args:
            symbol: 加密货币符号
            
        Returns:
            详细信息字典
        """
        try:
            params = {
                'symbol': symbol.upper()
            }
            
            data = self._make_request("cryptocurrency/info", params)
            info = data.get('data', {})
            
            if symbol.upper() in info:
                logger.info(f"ℹ️ 获取 {symbol} 详细信息成功")
                return info[symbol.upper()]
            else:
                logger.warning(f"⚠️ 未找到 {symbol} 的详细信息")
                return {}
                
        except Exception as e:
            logger.error(f"❌ 获取 {symbol} 详细信息失败: {e}")
            return {}
    
    def get_historical_quotes(self, symbol: str, count: int = 30, 
                            interval: str = "daily", convert: str = "USD") -> List[Dict]:
        """
        获取历史报价数据
        
        Args:
            symbol: 加密货币符号
            count: 数据点数量（Free用户限制）
            interval: 时间间隔（daily, hourly）
            convert: 转换货币
            
        Returns:
            历史数据列表
        """
        try:
            params = {
                'symbol': symbol.upper(),
                'count': min(count, 100),  # Free用户限制
                'interval': interval,
                'convert': convert
            }
            
            data = self._make_request("cryptocurrency/quotes/historical", params)
            historical = data.get('data', [])
            
            logger.info(f"📈 获取 {symbol} 历史数据: {len(historical)} 条记录")
            return historical
            
        except Exception as e:
            logger.error(f"❌ 获取 {symbol} 历史数据失败: {e}")
            return []
    
    def search_crypto(self, query: str) -> List[Dict]:
        """
        搜索加密货币（通过列表API实现）
        
        Args:
            query: 搜索关键词
            
        Returns:
            搜索结果列表
        """
        try:
            # 获取前100名加密货币列表
            listings = self.get_crypto_listings(limit=100)
            
            # 在列表中搜索匹配的加密货币
            results = []
            query_lower = query.lower()
            
            for crypto in listings:
                name = crypto.get('name', '').lower()
                symbol = crypto.get('symbol', '').lower()
                
                if query_lower in name or query_lower in symbol:
                    results.append(crypto)
            
            logger.info(f"🔍 搜索 '{query}' 找到 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"❌ 搜索加密货币失败: {e}")
            return []


def get_crypto_data_cmc(symbol: str, data_type: str = "quotes", 
                       convert: str = "USD", count: int = 30) -> Dict:
    """
    获取加密货币数据的便捷函数
    
    Args:
        symbol: 加密货币符号
        data_type: 数据类型 ('quotes', 'info', 'historical', 'search')
        convert: 转换货币
        count: 历史数据数量
        
    Returns:
        数据字典
    """
    try:
        api = CoinMarketCapAPI()
        
        if data_type == "quotes":
            return api.get_crypto_quotes(symbol, convert)
        elif data_type == "info":
            return api.get_crypto_info(symbol)
        elif data_type == "historical":
            return api.get_historical_quotes(symbol, count, convert=convert)
        elif data_type == "search":
            return api.search_crypto(symbol)
        else:
            logger.error(f"❌ 不支持的数据类型: {data_type}")
            return {}
            
    except Exception as e:
        logger.error(f"❌ 获取加密货币数据失败: {e}")
        return {}


def format_crypto_data_for_analysis_cmc(crypto_data: Dict, symbol: str) -> str:
    """
    将CoinMarketCap加密货币数据格式化为分析报告
    
    Args:
        crypto_data: 加密货币数据
        symbol: 加密货币符号
        
    Returns:
        格式化的分析报告字符串
    """
    if not crypto_data:
        return f"❌ 无法获取 {symbol} 的加密货币数据"
    
    try:
        # 处理报价数据
        if 'quote' in crypto_data:
            quote = crypto_data['quote'].get('USD', {})
            
            current_price = quote.get('price', 0)
            change_24h = quote.get('percent_change_24h', 0)
            volume_24h = quote.get('volume_24h', 0)
            market_cap = quote.get('market_cap', 0)
            
            price_trend = "上涨" if change_24h > 0 else "下跌"
            
            report = f"""
🪙 加密货币分析报告: {symbol.upper()}

📊 基本数据:
- 当前价格: ${current_price:,.2f}
- 24小时变化: {change_24h:+.2f}% ({price_trend})
- 24小时交易量: ${volume_24h:,.0f}
- 市值: ${market_cap:,.0f}

📈 市场表现:
- 价格趋势: {price_trend}趋势明显
- 交易活跃度: {'高' if volume_24h > 1000000000 else '中等' if volume_24h > 100000000 else '低'}
- 市场表现: {'强势' if change_24h > 5 else '稳定' if abs(change_24h) < 5 else '弱势'}

💡 分析建议:
- 基于CoinMarketCap数据的最新市场分析
- 建议结合技术指标进行进一步分析
"""
            
            return report
        
        # 处理项目信息数据
        elif 'name' in crypto_data:
            name = crypto_data.get('name', 'Unknown')
            description = crypto_data.get('description', '')
            website = crypto_data.get('urls', {}).get('website', [''])[0] if crypto_data.get('urls', {}).get('website') else ''
            
            report = f"""
🪙 加密货币项目信息: {name} ({symbol.upper()})

📊 基本信息:
- 名称: {name}
- 符号: {symbol.upper()}
- 官网: {website}

📝 项目描述:
{description[:500]}{'...' if len(description) > 500 else ''}

💡 分析建议:
- 基于CoinMarketCap项目信息
- 建议进一步分析技术文档和社区活跃度
"""
            
            return report
        
        else:
            return f"❌ 未知的数据格式: {symbol}"
        
    except Exception as e:
        logger.error(f"❌ 格式化加密货币数据失败: {e}")
        return f"❌ 数据处理错误: {str(e)}"


def test_coinmarketcap_connection() -> bool:
    """
    测试CoinMarketCap API连接
    
    Returns:
        连接是否成功
    """
    try:
        logger.info("🧪 测试CoinMarketCap API连接...")
        
        api = CoinMarketCapAPI()
        
        # 测试获取比特币报价
        btc_quote = api.get_crypto_quotes('BTC')
        
        if btc_quote and 'quote' in btc_quote:
            logger.info("✅ CoinMarketCap API连接成功")
            return True
        else:
            logger.error("❌ CoinMarketCap API连接失败：数据为空")
            return False
            
    except Exception as e:
        logger.error(f"❌ CoinMarketCap API连接测试失败: {e}")
        return False


if __name__ == "__main__":
    """测试脚本"""
    logger.info("🧪 CoinMarketCap工具测试")
    logger.info("=" * 50)
    
    # 测试连接
    if test_coinmarketcap_connection():
        # 测试获取比特币数据
        btc_data = get_crypto_data_cmc('BTC', 'quotes')
        if btc_data:
            report = format_crypto_data_for_analysis_cmc(btc_data, 'BTC')
            print(report)
        
        logger.info("🎉 CoinMarketCap工具测试完成")
    else:
        logger.error("❌ CoinMarketCap工具测试失败")
