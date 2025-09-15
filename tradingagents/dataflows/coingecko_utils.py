#!/usr/bin/env python3
"""
CoinGecko加密货币数据获取工具
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


class CoinGeckoAPI:
    """CoinGecko API客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化CoinGecko API客户端
        
        Args:
            api_key: CoinGecko API密钥（可选，用于提高请求限制）
        """
        self.api_key = api_key or os.getenv('COINGECKO_API_KEY')
        self.base_url = "https://api.coingecko.com/api/v3"
        self.session = requests.Session()
        
        # 设置请求头
        if self.api_key:
            self.session.headers.update({
                'x-cg-demo-api-key': self.api_key
            })
        
        # 请求限制控制
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 免费API限制：每秒1个请求
        
        logger.info(f"🪙 CoinGecko API客户端初始化完成")
        logger.info(f"   API密钥: {'已配置' if self.api_key else '未配置（使用免费限制）'}")
    
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
            logger.debug(f"🪙 CoinGecko API请求成功: {endpoint}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ CoinGecko API请求失败: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ CoinGecko API响应解析失败: {e}")
            raise
    
    def get_coin_list(self) -> List[Dict]:
        """
        获取所有支持的加密货币列表
        
        Returns:
            加密货币列表
        """
        try:
            data = self._make_request("coins/list")
            logger.info(f"📋 获取到 {len(data)} 个加密货币")
            return data
        except Exception as e:
            logger.error(f"❌ 获取加密货币列表失败: {e}")
            return []
    
    def get_coin_market_data(self, coin_id: str, vs_currency: str = "usd", 
                           days: int = 30) -> Dict:
        """
        获取加密货币市场数据
        
        Args:
            coin_id: 加密货币ID（如 'bitcoin', 'ethereum'）
            vs_currency: 计价货币（默认USD）
            days: 数据天数（1, 7, 14, 30, 90, 180, 365, max）
            
        Returns:
            市场数据字典
        """
        try:
            params = {
                'vs_currency': vs_currency,
                'days': days
                # 注意：interval参数需要付费API，免费版不支持
            }
            
            data = self._make_request(f"coins/{coin_id}/market_chart", params)
            
            # 处理价格数据
            prices = data.get('prices', [])
            volumes = data.get('total_volumes', [])
            market_caps = data.get('market_caps', [])
            
            # 转换为DataFrame格式
            price_data = []
            for i, price_point in enumerate(prices):
                price_data.append({
                    'timestamp': price_point[0],
                    'datetime': datetime.fromtimestamp(price_point[0] / 1000),
                    'price': price_point[1],
                    'volume': volumes[i][1] if i < len(volumes) else 0,
                    'market_cap': market_caps[i][1] if i < len(market_caps) else 0
                })
            
            df = pd.DataFrame(price_data)
            
            logger.info(f"📊 获取 {coin_id} 市场数据: {len(df)} 条记录")
            return {
                'coin_id': coin_id,
                'vs_currency': vs_currency,
                'data': df,
                'raw_data': data
            }
            
        except Exception as e:
            logger.error(f"❌ 获取 {coin_id} 市场数据失败: {e}")
            return {}
    
    def get_coin_info(self, coin_id: str) -> Dict:
        """
        获取加密货币详细信息
        
        Args:
            coin_id: 加密货币ID
            
        Returns:
            详细信息字典
        """
        try:
            params = {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'true',
                'developer_data': 'true',
                'sparkline': 'false'
            }
            
            data = self._make_request(f"coins/{coin_id}", params)
            
            # 提取关键信息
            coin_info = {
                'id': data.get('id'),
                'symbol': data.get('symbol', '').upper(),
                'name': data.get('name'),
                'description': data.get('description', {}).get('en', ''),
                'homepage': data.get('links', {}).get('homepage', [''])[0],
                'genesis_date': data.get('genesis_date'),
                'market_data': data.get('market_data', {}),
                'community_data': data.get('community_data', {}),
                'developer_data': data.get('developer_data', {}),
                'categories': data.get('categories', []),
                'platforms': data.get('platforms', {}),
                'raw_data': data
            }
            
            logger.info(f"ℹ️ 获取 {coin_id} 详细信息成功")
            return coin_info
            
        except Exception as e:
            logger.error(f"❌ 获取 {coin_id} 详细信息失败: {e}")
            return {}
    
    def search_coins(self, query: str) -> List[Dict]:
        """
        搜索加密货币
        
        Args:
            query: 搜索关键词
            
        Returns:
            搜索结果列表
        """
        try:
            data = self._make_request("search", {'query': query})
            coins = data.get('coins', [])
            
            logger.info(f"🔍 搜索 '{query}' 找到 {len(coins)} 个结果")
            return coins
            
        except Exception as e:
            logger.error(f"❌ 搜索加密货币失败: {e}")
            return []
    
    def get_trending_coins(self) -> List[Dict]:
        """
        获取热门加密货币
        
        Returns:
            热门加密货币列表
        """
        try:
            data = self._make_request("search/trending")
            trending = data.get('coins', [])
            
            logger.info(f"🔥 获取到 {len(trending)} 个热门加密货币")
            return trending
            
        except Exception as e:
            logger.error(f"❌ 获取热门加密货币失败: {e}")
            return []


def get_crypto_data(coin_id: str, vs_currency: str = "usd", 
                   days: int = 30, data_type: str = "market") -> Dict:
    """
    获取加密货币数据的便捷函数
    
    Args:
        coin_id: 加密货币ID
        vs_currency: 计价货币
        days: 数据天数
        data_type: 数据类型 ('market', 'info', 'search')
        
    Returns:
        数据字典
    """
    api = CoinGeckoAPI()
    
    if data_type == "market":
        return api.get_coin_market_data(coin_id, vs_currency, days)
    elif data_type == "info":
        return api.get_coin_info(coin_id)
    elif data_type == "search":
        return api.search_coins(coin_id)
    else:
        logger.error(f"❌ 不支持的数据类型: {data_type}")
        return {}


def format_crypto_data_for_analysis(crypto_data: Dict) -> str:
    """
    将加密货币数据格式化为分析报告
    
    Args:
        crypto_data: 加密货币数据
        
    Returns:
        格式化的分析报告字符串
    """
    if not crypto_data:
        return "❌ 无法获取加密货币数据"
    
    try:
        coin_id = crypto_data.get('coin_id', 'Unknown')
        df = crypto_data.get('data')
        
        if df is None or df.empty:
            return f"❌ {coin_id} 数据为空"
        
        # 基本统计信息
        latest_price = df['price'].iloc[-1]
        price_change_24h = ((df['price'].iloc[-1] - df['price'].iloc[-2]) / df['price'].iloc[-2] * 100) if len(df) > 1 else 0
        avg_volume = df['volume'].mean()
        avg_market_cap = df['market_cap'].mean()
        
        # 价格趋势分析
        price_trend = "上涨" if price_change_24h > 0 else "下跌"
        
        report = f"""
🪙 加密货币分析报告: {coin_id.upper()}

📊 基本数据:
- 当前价格: ${latest_price:,.2f}
- 24小时变化: {price_change_24h:+.2f}% ({price_trend})
- 平均交易量: ${avg_volume:,.0f}
- 平均市值: ${avg_market_cap:,.0f}

📈 价格趋势:
- 最高价: ${df['price'].max():,.2f}
- 最低价: ${df['price'].min():,.2f}
- 价格波动: {((df['price'].max() - df['price'].min()) / df['price'].mean() * 100):.2f}%

📅 数据时间范围:
- 开始时间: {df['datetime'].iloc[0].strftime('%Y-%m-%d %H:%M:%S')}
- 结束时间: {df['datetime'].iloc[-1].strftime('%Y-%m-%d %H:%M:%S')}
- 数据点数: {len(df)}

💡 分析建议:
- 价格趋势: {price_trend}趋势明显
- 交易活跃度: {'高' if avg_volume > df['volume'].quantile(0.7) else '中等' if avg_volume > df['volume'].quantile(0.3) else '低'}
- 市场表现: {'强势' if price_change_24h > 5 else '稳定' if abs(price_change_24h) < 5 else '弱势'}
"""
        
        return report
        
    except Exception as e:
        logger.error(f"❌ 格式化加密货币数据失败: {e}")
        return f"❌ 数据处理错误: {str(e)}"


def test_coingecko_connection() -> bool:
    """
    测试CoinGecko API连接
    
    Returns:
        连接是否成功
    """
    try:
        logger.info("🧪 测试CoinGecko API连接...")
        
        api = CoinGeckoAPI()
        
        # 测试获取比特币数据
        btc_data = api.get_coin_market_data('bitcoin', days=1)
        
        if btc_data and 'data' in btc_data and not btc_data['data'].empty:
            logger.info("✅ CoinGecko API连接成功")
            return True
        else:
            logger.error("❌ CoinGecko API连接失败：数据为空")
            return False
            
    except Exception as e:
        logger.error(f"❌ CoinGecko API连接测试失败: {e}")
        return False


if __name__ == "__main__":
    """测试脚本"""
    logger.info("🧪 CoinGecko工具测试")
    logger.info("=" * 50)
    
    # 测试连接
    if test_coingecko_connection():
        # 测试获取比特币数据
        btc_data = get_crypto_data('bitcoin', days=7)
        if btc_data:
            report = format_crypto_data_for_analysis(btc_data)
            print(report)
        
        logger.info("🎉 CoinGecko工具测试完成")
    else:
        logger.error("❌ CoinGecko工具测试失败")
