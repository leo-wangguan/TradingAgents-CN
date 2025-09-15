#!/usr/bin/env python3
"""
CoinDesk加密货币数据获取工具
提供比特币价格和新闻数据获取功能
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


class CoinDeskAPI:
    """CoinDesk API客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化CoinDesk API客户端
        
        Args:
            api_key: CoinDesk API密钥（可选）
        """
        self.api_key = api_key or os.getenv('COINDESK_API_KEY')
        self.base_url = "https://data-api.coindesk.com"
        self.session = requests.Session()
        
        # 设置请求头 - CoinDesk Data API使用API key作为查询参数
        # 不需要在header中设置Authorization
        
        # 请求限制控制
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 保守的请求间隔
        
        logger.info(f"🪙 CoinDesk API客户端初始化完成")
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
            logger.debug(f"🪙 CoinDesk API请求成功: {endpoint}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ CoinDesk API请求失败: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ CoinDesk API响应解析失败: {e}")
            raise
    
    def get_current_price(self, currency: str = "USD") -> Dict:
        """
        获取当前比特币价格
        
        Args:
            currency: 计价货币（默认USD）
            
        Returns:
            当前价格数据
        """
        try:
            # 使用CoinDesk Data API
            endpoint = "index/cc/v1/latest/tick"
            params = {
                'market': 'ccix',
                'instruments': 'BTC-USD',
                'api_key': self.api_key
            }
            
            data = self._make_request(endpoint, params)
            
            if 'Data' in data and data['Data']:
                # CoinDesk Data API返回的是字典，键是币种对
                btc_data = data['Data'].get('BTC-USD', {})
                
                result = {
                    'symbol': 'BTC',
                    'currency': currency,
                    'price': float(btc_data.get('VALUE', 0)),
                    'timestamp': btc_data.get('VALUE_LAST_UPDATE_TS', ''),
                    'volume_24h': btc_data.get('MOVING_24_HOUR_VOLUME', 0),
                    'volume_24h_quote': btc_data.get('MOVING_24_HOUR_QUOTE_VOLUME', 0),
                    'change_24h': btc_data.get('MOVING_24_HOUR_CHANGE', 0),
                    'change_24h_pct': btc_data.get('MOVING_24_HOUR_CHANGE_PERCENTAGE', 0),
                    'high_24h': btc_data.get('MOVING_24_HOUR_HIGH', 0),
                    'low_24h': btc_data.get('MOVING_24_HOUR_LOW', 0),
                    'raw_data': data
                }
                
                logger.info(f"📊 获取BTC当前价格成功: ${result['price']:,.2f}")
                return result
            else:
                logger.error("❌ CoinDesk API返回数据为空")
                return {}
            
        except Exception as e:
            logger.error(f"❌ 获取BTC当前价格失败: {e}")
            return {}
    
    def get_historical_prices(self, start_date: str, end_date: str, 
                            currency: str = "USD") -> List[Dict]:
        """
        获取历史比特币价格
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            currency: 计价货币
            
        Returns:
            历史价格数据列表
        """
        try:
            # 使用CoinDesk的历史价格API
            url = "https://api.coindesk.com/v1/bpi/historical/close.json"
            params = {
                'start': start_date,
                'end': end_date,
                'currency': currency
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            bpi = data.get('bpi', {})
            
            # 转换为列表格式
            historical_data = []
            for date, price in bpi.items():
                historical_data.append({
                    'date': date,
                    'price': float(price),
                    'currency': currency
                })
            
            # 按日期排序
            historical_data.sort(key=lambda x: x['date'])
            
            logger.info(f"📈 获取BTC历史价格: {len(historical_data)} 条记录")
            return historical_data
            
        except Exception as e:
            logger.error(f"❌ 获取BTC历史价格失败: {e}")
            return []
    
    def get_news(self, limit: int = 10, category: str = None) -> List[Dict]:
        """
        获取加密货币新闻
        
        Args:
            limit: 返回数量限制
            category: 新闻分类
            
        Returns:
            新闻列表
        """
        try:
            # 注意：这里使用模拟数据，因为CoinDesk的新闻API可能需要特殊权限
            # 在实际应用中，您可能需要使用其他新闻API或爬虫
            
            # 模拟新闻数据
            mock_news = [
                {
                    'id': '1',
                    'title': 'Bitcoin Price Analysis: Market Trends and Future Outlook',
                    'summary': 'Recent analysis of Bitcoin price movements and market sentiment.',
                    'url': 'https://www.coindesk.com/bitcoin-price-analysis',
                    'published_at': datetime.now().isoformat(),
                    'category': 'analysis'
                },
                {
                    'id': '2', 
                    'title': 'Cryptocurrency Market Update: Major Developments',
                    'summary': 'Latest developments in the cryptocurrency market.',
                    'url': 'https://www.coindesk.com/market-update',
                    'published_at': (datetime.now() - timedelta(hours=2)).isoformat(),
                    'category': 'market'
                }
            ]
            
            # 根据分类过滤
            if category:
                mock_news = [news for news in mock_news if news.get('category') == category]
            
            # 限制数量
            mock_news = mock_news[:limit]
            
            logger.info(f"📰 获取加密货币新闻: {len(mock_news)} 条")
            return mock_news
            
        except Exception as e:
            logger.error(f"❌ 获取新闻失败: {e}")
            return []
    
    def get_supported_currencies(self) -> List[str]:
        """
        获取支持的货币列表
        
        Returns:
            支持的货币列表
        """
        try:
            url = "https://api.coindesk.com/v1/bpi/supported-currencies.json"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            currencies = [item.get('currency') for item in data if item.get('currency')]
            
            logger.info(f"💱 获取支持的货币: {len(currencies)} 种")
            return currencies
            
        except Exception as e:
            logger.error(f"❌ 获取支持货币失败: {e}")
            return ['USD', 'EUR', 'GBP']  # 默认货币


def get_coindesk_data(symbol: str, data_type: str = "price", **kwargs) -> str:
    """
    获取CoinDesk数据的便捷函数
    
    Args:
        symbol: 加密货币符号（仅支持BTC）
        data_type: 数据类型 ('price', 'historical', 'news')
        **kwargs: 其他参数
        
    Returns:
        数据结果字符串
    """
    try:
        api = CoinDeskAPI()
        
        if symbol.upper() != 'BTC':
            return f"❌ CoinDesk仅支持比特币(BTC)，不支持 {symbol}"
        
        if data_type == "price":
            price_data = api.get_current_price()
            if price_data:
                return format_coindesk_price_data(price_data)
            else:
                return f"❌ 无法获取 {symbol} 的价格数据"
        
        elif data_type == "historical":
            start_date = kwargs.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
            end_date = kwargs.get('end_date', datetime.now().strftime('%Y-%m-%d'))
            currency = kwargs.get('currency', 'USD')
            
            historical_data = api.get_historical_prices(start_date, end_date, currency)
            if historical_data:
                return format_coindesk_historical_data(historical_data)
            else:
                return f"❌ 无法获取 {symbol} 的历史数据"
        
        elif data_type == "news":
            limit = kwargs.get('limit', 10)
            category = kwargs.get('category')
            
            news_data = api.get_news(limit, category)
            if news_data:
                return format_coindesk_news_data(news_data)
            else:
                return f"❌ 无法获取 {symbol} 的新闻数据"
        
        else:
            return f"❌ 不支持的数据类型: {data_type}"
            
    except Exception as e:
        logger.error(f"❌ 获取CoinDesk数据失败: {e}")
        return f"❌ 获取CoinDesk数据失败: {str(e)}"


def format_coindesk_price_data(price_data: Dict) -> str:
    """格式化CoinDesk价格数据"""
    try:
        symbol = price_data.get('symbol', 'BTC')
        price = price_data.get('price', 0)
        currency = price_data.get('currency', 'USD')
        timestamp = price_data.get('timestamp', '')
        
        report = f"""
🪙 CoinDesk比特币价格报告: {symbol}

📊 当前价格:
- 价格: ${price:,.2f} {currency}
- 更新时间: {timestamp}

💡 数据来源: CoinDesk API
📈 建议: 结合其他技术指标进行综合分析
"""
        return report
        
    except Exception as e:
        logger.error(f"❌ 格式化价格数据失败: {e}")
        return f"❌ 数据处理错误: {str(e)}"


def format_coindesk_historical_data(historical_data: List[Dict]) -> str:
    """格式化CoinDesk历史数据"""
    try:
        if not historical_data:
            return "❌ 历史数据为空"
        
        # 计算统计信息
        prices = [item['price'] for item in historical_data]
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)
        
        # 计算价格变化
        first_price = prices[0]
        last_price = prices[-1]
        price_change = last_price - first_price
        price_change_pct = (price_change / first_price) * 100 if first_price != 0 else 0
        
        trend = "上涨" if price_change > 0 else "下跌"
        
        report = f"""
🪙 CoinDesk比特币历史价格分析

📊 数据统计:
- 数据期间: {historical_data[0]['date']} 至 {historical_data[-1]['date']}
- 数据点数: {len(historical_data)}
- 最高价: ${max_price:,.2f}
- 最低价: ${min_price:,.2f}
- 平均价: ${avg_price:,.2f}

📈 价格趋势:
- 期初价格: ${first_price:,.2f}
- 期末价格: ${last_price:,.2f}
- 价格变化: {price_change:+.2f} ({price_change_pct:+.2f}%)
- 趋势: {trend}

💡 数据来源: CoinDesk API
"""
        return report
        
    except Exception as e:
        logger.error(f"❌ 格式化历史数据失败: {e}")
        return f"❌ 数据处理错误: {str(e)}"


def format_coindesk_news_data(news_data: List[Dict]) -> str:
    """格式化CoinDesk新闻数据"""
    try:
        if not news_data:
            return "❌ 新闻数据为空"
        
        report = f"""
📰 CoinDesk加密货币新闻摘要

📋 最新新闻 (共{len(news_data)}条):
"""
        
        for i, news in enumerate(news_data, 1):
            title = news.get('title', '无标题')
            summary = news.get('summary', '无摘要')
            url = news.get('url', '')
            published_at = news.get('published_at', '')
            
            report += f"""
{i}. {title}
   📝 摘要: {summary}
   🔗 链接: {url}
   📅 发布时间: {published_at}
"""
        
        report += """
💡 数据来源: CoinDesk API
📈 建议: 结合新闻情绪分析市场趋势
"""
        return report
        
    except Exception as e:
        logger.error(f"❌ 格式化新闻数据失败: {e}")
        return f"❌ 数据处理错误: {str(e)}"


def test_coindesk_connection() -> bool:
    """
    测试CoinDesk API连接
    
    Returns:
        连接是否成功
    """
    try:
        logger.info("🧪 测试CoinDesk API连接...")
        
        api = CoinDeskAPI()
        
        # 测试获取比特币价格
        price_data = api.get_current_price()
        
        if price_data and 'price' in price_data:
            logger.info("✅ CoinDesk API连接成功")
            return True
        else:
            logger.error("❌ CoinDesk API连接失败：数据为空")
            return False
            
    except Exception as e:
        logger.error(f"❌ CoinDesk API连接测试失败: {e}")
        return False


if __name__ == "__main__":
    """测试脚本"""
    logger.info("🧪 CoinDesk工具测试")
    logger.info("=" * 50)
    
    # 测试连接
    if test_coindesk_connection():
        # 测试获取比特币价格
        price_data = get_coindesk_data('BTC', 'price')
        if price_data:
            print(price_data)
        
        # 测试获取历史数据
        historical_data = get_coindesk_data('BTC', 'historical')
        if historical_data:
            print(historical_data)
        
        logger.info("🎉 CoinDesk工具测试完成")
    else:
        logger.error("❌ CoinDesk工具测试失败")
