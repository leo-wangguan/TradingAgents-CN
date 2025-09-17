from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from typing import List
from typing import Annotated
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import RemoveMessage
from langchain_core.tools import tool
from datetime import date, timedelta, datetime
import time
import functools
import pandas as pd
import os
from pathlib import Path
from dateutil.relativedelta import relativedelta
from langchain_openai import ChatOpenAI
import tradingagents.dataflows.interface as interface
from tradingagents.default_config import DEFAULT_CONFIG
from langchain_core.messages import HumanMessage
import re

# 导入统一日志系统和工具日志装饰器
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_tool_call, log_analysis_step

import asyncio
from typing import Dict, Optional, List
from tradingagents.dataflows.whitepaper_parser import WhitepaperParser
from tradingagents.dataflows import crypto_project_repository
from .gitbook_downloader import GitbookDownloader

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]
        
        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]
        
        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")
        
        return {"messages": removal_operations + [placeholder]}
    
    return delete_messages


class Toolkit:
    _config = DEFAULT_CONFIG.copy()

    @classmethod
    def update_config(cls, config):
        """Update the class-level configuration."""
        cls._config.update(config)

    @property
    def config(self):
        """Access the configuration."""
        return self._config

    def __init__(self, config=None):
        if config:
            self.update_config(config)
        # 本轮调用级的轻量缓存（避免重复请求 CoinGecko）
        if not hasattr(self, "_crypto_ctx"):
            self._crypto_ctx = {}

    @staticmethod
    @tool
    def get_reddit_news(
        curr_date: Annotated[str, "Date you want to get news for in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve global news from Reddit within a specified time frame.
        Args:
            curr_date (str): Date you want to get news for in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the latest global news from Reddit in the specified time frame.
        """
        
        global_news_result = interface.get_reddit_global_news(curr_date, 7, 5)

        return global_news_result

    @staticmethod
    @tool
    def get_finnhub_news(
        ticker: Annotated[
            str,
            "Search query of a company, e.g. 'AAPL, TSM, etc.",
        ],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news about a given stock from Finnhub within a date range
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing news about the company within the date range from start_date to end_date
        """

        end_date_str = end_date

        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        look_back_days = (end_date - start_date).days

        finnhub_news_result = interface.get_finnhub_news(
            ticker, end_date_str, look_back_days
        )

        return finnhub_news_result

    @staticmethod
    @tool
    def get_reddit_stock_info(
        ticker: Annotated[
            str,
            "Ticker of a company. e.g. AAPL, TSM",
        ],
        curr_date: Annotated[str, "Current date you want to get news for"],
    ) -> str:
        """
        Retrieve the latest news about a given stock from Reddit, given the current date.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): current date in yyyy-mm-dd format to get news for
        Returns:
            str: A formatted dataframe containing the latest news about the company on the given date
        """

        stock_news_results = interface.get_reddit_company_news(ticker, curr_date, 7, 5)

        return stock_news_results

    @staticmethod
    @tool
    def get_chinese_social_sentiment(
        ticker: Annotated[str, "Ticker of a company. e.g. AAPL, TSM"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ) -> str:
        """
        获取中国社交媒体和财经平台上关于特定股票的情绪分析和讨论热度。
        整合雪球、东方财富股吧、新浪财经等中国本土平台的数据。
        Args:
            ticker (str): 股票代码，如 AAPL, TSM
            curr_date (str): 当前日期，格式为 yyyy-mm-dd
        Returns:
            str: 包含中国投资者情绪分析、讨论热度、关键观点的格式化报告
        """
        try:
            # 这里可以集成多个中国平台的数据
            chinese_sentiment_results = interface.get_chinese_social_sentiment(ticker, curr_date)
            return chinese_sentiment_results
        except Exception as e:
            # 如果中国平台数据获取失败，回退到原有的Reddit数据
            return interface.get_reddit_company_news(ticker, curr_date, 7, 5)

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified 或 get_stock_market_data_unified
    def get_china_stock_data(
        stock_code: Annotated[str, "中国股票代码，如 000001(平安银行), 600519(贵州茅台)"],
        start_date: Annotated[str, "开始日期，格式 yyyy-mm-dd"],
        end_date: Annotated[str, "结束日期，格式 yyyy-mm-dd"],
    ) -> str:
        """
        获取中国A股实时和历史数据，通过Tushare等高质量数据源提供专业的股票数据。
        支持实时行情、历史K线、技术指标等全面数据，自动使用最佳数据源。
        Args:
            stock_code (str): 中国股票代码，如 000001(平安银行), 600519(贵州茅台)
            start_date (str): 开始日期，格式 yyyy-mm-dd
            end_date (str): 结束日期，格式 yyyy-mm-dd
        Returns:
            str: 包含实时行情、历史数据、技术指标的完整股票分析报告
        """
        try:
            logger.debug(f"📊 [DEBUG] ===== agent_utils.get_china_stock_data 开始调用 =====")
            logger.debug(f"📊 [DEBUG] 参数: stock_code={stock_code}, start_date={start_date}, end_date={end_date}")

            from tradingagents.dataflows.interface import get_china_stock_data_unified
            logger.debug(f"📊 [DEBUG] 成功导入统一数据源接口")

            logger.debug(f"📊 [DEBUG] 正在调用统一数据源接口...")
            result = get_china_stock_data_unified(stock_code, start_date, end_date)

            logger.debug(f"📊 [DEBUG] 统一数据源接口调用完成")
            logger.debug(f"📊 [DEBUG] 返回结果类型: {type(result)}")
            logger.debug(f"📊 [DEBUG] 返回结果长度: {len(result) if result else 0}")
            logger.debug(f"📊 [DEBUG] 返回结果前200字符: {str(result)[:200]}...")
            logger.debug(f"📊 [DEBUG] ===== agent_utils.get_china_stock_data 调用结束 =====")

            return result
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"❌ [DEBUG] ===== agent_utils.get_china_stock_data 异常 =====")
            logger.error(f"❌ [DEBUG] 错误类型: {type(e).__name__}")
            logger.error(f"❌ [DEBUG] 错误信息: {str(e)}")
            logger.error(f"❌ [DEBUG] 详细堆栈:")
            print(error_details)
            logger.error(f"❌ [DEBUG] ===== 异常处理结束 =====")
            return f"中国股票数据获取失败: {str(e)}。建议安装pytdx库: pip install pytdx"

    @staticmethod
    @tool
    def get_china_market_overview(
        curr_date: Annotated[str, "当前日期，格式 yyyy-mm-dd"],
    ) -> str:
        """
        获取中国股市整体概览，包括主要指数的实时行情。
        涵盖上证指数、深证成指、创业板指、科创50等主要指数。
        Args:
            curr_date (str): 当前日期，格式 yyyy-mm-dd
        Returns:
            str: 包含主要指数实时行情的市场概览报告
        """
        try:
            # 使用Tushare获取主要指数数据
            from tradingagents.dataflows.tushare_adapter import get_tushare_adapter

            adapter = get_tushare_adapter()
            if not adapter.provider or not adapter.provider.connected:
                # 如果Tushare不可用，回退到TDX
                logger.warning(f"⚠️ Tushare不可用，回退到TDX获取市场概览")
                from tradingagents.dataflows.tdx_utils import get_china_market_overview
                return get_china_market_overview()

            # 使用Tushare获取主要指数信息
            # 这里可以扩展为获取具体的指数数据
            return f"""# 中国股市概览 - {curr_date}

## 📊 主要指数
- 上证指数: 数据获取中...
- 深证成指: 数据获取中...
- 创业板指: 数据获取中...
- 科创50: 数据获取中...

## 💡 说明
市场概览功能正在从TDX迁移到Tushare，完整功能即将推出。
当前可以使用股票数据获取功能分析个股。

数据来源: Tushare专业数据源
更新时间: {curr_date}
"""

        except Exception as e:
            return f"中国市场概览获取失败: {str(e)}。正在从TDX迁移到Tushare数据源。"

    @staticmethod
    @tool
    def get_YFin_data(
        symbol: Annotated[str, "ticker symbol of the company"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve the stock price data for a given ticker symbol from Yahoo Finance.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.
        """

        result_data = interface.get_YFin_data(symbol, start_date, end_date)

        return result_data

    @staticmethod
    @tool
    def get_YFin_data_online(
        symbol: Annotated[str, "ticker symbol of the company"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve the stock price data for a given ticker symbol from Yahoo Finance.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.
        """

        result_data = interface.get_YFin_data_online(symbol, start_date, end_date)

        return result_data

    @staticmethod
    @tool
    def get_stockstats_indicators_report(
        symbol: Annotated[str, "ticker symbol of the company"],
        indicator: Annotated[
            str, "technical indicator to get the analysis and report of"
        ],
        curr_date: Annotated[
            str, "The current trading date you are trading on, YYYY-mm-dd"
        ],
        look_back_days: Annotated[int, "how many days to look back"] = 30,
    ) -> str:
        """
        Retrieve stock stats indicators for a given ticker symbol and indicator.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            indicator (str): Technical indicator to get the analysis and report of
            curr_date (str): The current trading date you are trading on, YYYY-mm-dd
            look_back_days (int): How many days to look back, default is 30
        Returns:
            str: A formatted dataframe containing the stock stats indicators for the specified ticker symbol and indicator.
        """

        result_stockstats = interface.get_stock_stats_indicators_window(
            symbol, indicator, curr_date, look_back_days, False
        )

        return result_stockstats

    @staticmethod
    @tool
    def get_stockstats_indicators_report_online(
        symbol: Annotated[str, "ticker symbol of the company"],
        indicator: Annotated[
            str, "technical indicator to get the analysis and report of"
        ],
        curr_date: Annotated[
            str, "The current trading date you are trading on, YYYY-mm-dd"
        ],
        look_back_days: Annotated[int, "how many days to look back"] = 30,
    ) -> str:
        """
        Retrieve stock stats indicators for a given ticker symbol and indicator.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            indicator (str): Technical indicator to get the analysis and report of
            curr_date (str): The current trading date you are trading on, YYYY-mm-dd
            look_back_days (int): How many days to look back, default is 30
        Returns:
            str: A formatted dataframe containing the stock stats indicators for the specified ticker symbol and indicator.
        """

        result_stockstats = interface.get_stock_stats_indicators_window(
            symbol, indicator, curr_date, look_back_days, True
        )

        return result_stockstats

    @staticmethod
    @tool
    def get_finnhub_company_insider_sentiment(
        ticker: Annotated[str, "ticker symbol for the company"],
        curr_date: Annotated[
            str,
            "current date of you are trading at, yyyy-mm-dd",
        ],
    ):
        """
        Retrieve insider sentiment information about a company (retrieved from public SEC information) for the past 30 days
        Args:
            ticker (str): ticker symbol of the company
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the sentiment in the past 30 days starting at curr_date
        """

        data_sentiment = interface.get_finnhub_company_insider_sentiment(
            ticker, curr_date, 30
        )

        return data_sentiment

    @staticmethod
    @tool
    def get_finnhub_company_insider_transactions(
        ticker: Annotated[str, "ticker symbol"],
        curr_date: Annotated[
            str,
            "current date you are trading at, yyyy-mm-dd",
        ],
    ):
        """
        Retrieve insider transaction information about a company (retrieved from public SEC information) for the past 30 days
        Args:
            ticker (str): ticker symbol of the company
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the company's insider transactions/trading information in the past 30 days
        """

        data_trans = interface.get_finnhub_company_insider_transactions(
            ticker, curr_date, 30
        )

        return data_trans

    @staticmethod
    @tool
    def get_simfin_balance_sheet(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        Retrieve the most recent balance sheet of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the company's most recent balance sheet
        """

        data_balance_sheet = interface.get_simfin_balance_sheet(ticker, freq, curr_date)

        return data_balance_sheet

    @staticmethod
    @tool
    def get_simfin_cashflow(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        Retrieve the most recent cash flow statement of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
                str: a report of the company's most recent cash flow statement
        """

        data_cashflow = interface.get_simfin_cashflow(ticker, freq, curr_date)

        return data_cashflow

    @staticmethod
    @tool
    def get_simfin_income_stmt(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        Retrieve the most recent income statement of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
                str: a report of the company's most recent income statement
        """

        data_income_stmt = interface.get_simfin_income_statements(
            ticker, freq, curr_date
        )

        return data_income_stmt

    @staticmethod
    @tool
    def get_google_news(
        query: Annotated[str, "Query to search with"],
        curr_date: Annotated[str, "Curr date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news from Google News based on a query and date range.
        Args:
            query (str): Query to search with
            curr_date (str): Current date in yyyy-mm-dd format
            look_back_days (int): How many days to look back
        Returns:
            str: A formatted string containing the latest news from Google News based on the query and date range.
        """

        google_news_results = interface.get_google_news(query, curr_date, 7)

        return google_news_results

    @staticmethod
    @tool
    def get_realtime_stock_news(
        ticker: Annotated[str, "Ticker of a company. e.g. AAPL, TSM"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ) -> str:
        """
        获取股票的实时新闻分析，解决传统新闻源的滞后性问题。
        整合多个专业财经API，提供15-30分钟内的最新新闻。
        支持多种新闻源轮询机制，优先使用实时新闻聚合器，失败时自动尝试备用新闻源。
        对于A股和港股，会优先使用中文财经新闻源（如东方财富）。
        
        Args:
            ticker (str): 股票代码，如 AAPL, TSM, 600036.SH
            curr_date (str): 当前日期，格式为 yyyy-mm-dd
        Returns:
            str: 包含实时新闻分析、紧急程度评估、时效性说明的格式化报告
        """
        from tradingagents.dataflows.realtime_news_utils import get_realtime_stock_news
        return get_realtime_stock_news(ticker, curr_date, hours_back=6)

    @staticmethod
    @tool
    def get_stock_news_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news about a given stock by using OpenAI's news API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest news about the company on the given date.
        """

        openai_news_results = interface.get_stock_news_openai(ticker, curr_date)

        return openai_news_results

    @staticmethod
    @tool
    def get_global_news_openai(
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest macroeconomics news on a given date using OpenAI's macroeconomics news API.
        Args:
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest macroeconomic news on the given date.
        """

        openai_news_results = interface.get_global_news_openai(curr_date)

        return openai_news_results

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified
    def get_fundamentals_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest fundamental information about a given stock on a given date by using OpenAI's news API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest fundamental information about the company on the given date.
        """
        logger.debug(f"📊 [DEBUG] get_fundamentals_openai 被调用: ticker={ticker}, date={curr_date}")

        # 检查是否为中国股票
        import re
        if re.match(r'^\d{6}$', str(ticker)):
            logger.debug(f"📊 [DEBUG] 检测到中国A股代码: {ticker}")
            # 使用统一接口获取中国股票名称
            try:
                from tradingagents.dataflows.interface import get_china_stock_info_unified
                stock_info = get_china_stock_info_unified(ticker)

                # 解析股票名称
                if "股票名称:" in stock_info:
                    company_name = stock_info.split("股票名称:")[1].split("\n")[0].strip()
                else:
                    company_name = f"股票代码{ticker}"

                logger.debug(f"📊 [DEBUG] 中国股票名称映射: {ticker} -> {company_name}")
            except Exception as e:
                logger.error(f"⚠️ [DEBUG] 从统一接口获取股票名称失败: {e}")
                company_name = f"股票代码{ticker}"

            # 修改查询以包含正确的公司名称
            modified_query = f"{company_name}({ticker})"
            logger.debug(f"📊 [DEBUG] 修改后的查询: {modified_query}")
        else:
            logger.debug(f"📊 [DEBUG] 检测到非中国股票: {ticker}")
            modified_query = ticker

        try:
            openai_fundamentals_results = interface.get_fundamentals_openai(
                modified_query, curr_date
            )
            logger.debug(f"📊 [DEBUG] OpenAI基本面分析结果长度: {len(openai_fundamentals_results) if openai_fundamentals_results else 0}")
            return openai_fundamentals_results
        except Exception as e:
            logger.error(f"❌ [DEBUG] OpenAI基本面分析失败: {str(e)}")
            return f"基本面分析失败: {str(e)}"

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified
    def get_china_fundamentals(
        ticker: Annotated[str, "中国A股股票代码，如600036"],
        curr_date: Annotated[str, "当前日期，格式为yyyy-mm-dd"],
    ):
        """
        获取中国A股股票的基本面信息，使用中国股票数据源。
        Args:
            ticker (str): 中国A股股票代码，如600036, 000001
            curr_date (str): 当前日期，格式为yyyy-mm-dd
        Returns:
            str: 包含股票基本面信息的格式化字符串
        """
        logger.debug(f"📊 [DEBUG] get_china_fundamentals 被调用: ticker={ticker}, date={curr_date}")

        # 检查是否为中国股票
        import re
        if not re.match(r'^\d{6}$', str(ticker)):
            return f"错误：{ticker} 不是有效的中国A股代码格式"

        try:
            # 使用统一数据源接口获取股票数据（默认Tushare，支持备用数据源）
            from tradingagents.dataflows.interface import get_china_stock_data_unified
            logger.debug(f"📊 [DEBUG] 正在获取 {ticker} 的股票数据...")

            # 获取最近30天的数据用于基本面分析
            from datetime import datetime, timedelta
            end_date = datetime.strptime(curr_date, '%Y-%m-%d')
            start_date = end_date - timedelta(days=30)

            stock_data = get_china_stock_data_unified(
                ticker,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )

            logger.debug(f"📊 [DEBUG] 股票数据获取完成，长度: {len(stock_data) if stock_data else 0}")

            if not stock_data or "获取失败" in stock_data or "❌" in stock_data:
                return f"无法获取股票 {ticker} 的基本面数据：{stock_data}"

            # 调用真正的基本面分析
            from tradingagents.dataflows.optimized_china_data import OptimizedChinaDataProvider

            # 创建分析器实例
            analyzer = OptimizedChinaDataProvider()

            # 生成真正的基本面分析报告
            fundamentals_report = analyzer._generate_fundamentals_report(ticker, stock_data)

            logger.debug(f"📊 [DEBUG] 中国基本面分析报告生成完成")
            logger.debug(f"📊 [DEBUG] get_china_fundamentals 结果长度: {len(fundamentals_report)}")

            return fundamentals_report

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"❌ [DEBUG] get_china_fundamentals 失败:")
            logger.error(f"❌ [DEBUG] 错误: {str(e)}")
            logger.error(f"❌ [DEBUG] 堆栈: {error_details}")
            return f"中国股票基本面分析失败: {str(e)}"

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified 或 get_stock_market_data_unified
    def get_hk_stock_data_unified(
        symbol: Annotated[str, "港股代码，如：0700.HK、9988.HK等"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"]
    ) -> str:
        """
        获取港股数据的统一接口，优先使用AKShare数据源，备用Yahoo Finance

        Args:
            symbol: 港股代码 (如: 0700.HK)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            str: 格式化的港股数据
        """
        logger.debug(f"🇭🇰 [DEBUG] get_hk_stock_data_unified 被调用: symbol={symbol}, start_date={start_date}, end_date={end_date}")

        try:
            from tradingagents.dataflows.interface import get_hk_stock_data_unified

            result = get_hk_stock_data_unified(symbol, start_date, end_date)

            logger.debug(f"🇭🇰 [DEBUG] 港股数据获取完成，长度: {len(result) if result else 0}")

            return result

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"❌ [DEBUG] get_hk_stock_data_unified 失败:")
            logger.error(f"❌ [DEBUG] 错误: {str(e)}")
            logger.error(f"❌ [DEBUG] 堆栈: {error_details}")
            return f"港股数据获取失败: {str(e)}"

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_fundamentals_unified", log_args=True)
    def get_stock_fundamentals_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"] = None,
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"] = None,
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"] = None
    ) -> str:
        """
        统一的股票基本面分析工具
        自动识别股票类型（A股、港股、美股）并调用相应的数据源

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            start_date: 开始日期（可选，格式：YYYY-MM-DD）
            end_date: 结束日期（可选，格式：YYYY-MM-DD）
            curr_date: 当前日期（可选，格式：YYYY-MM-DD）

        Returns:
            str: 基本面分析数据和报告
        """
        logger.info(f"📊 [统一基本面工具] 分析股票: {ticker}")

        # 添加详细的股票代码追踪日志
        logger.info(f"🔍 [股票代码追踪] 统一基本面工具接收到的原始股票代码: '{ticker}' (类型: {type(ticker)})")
        logger.info(f"🔍 [股票代码追踪] 股票代码长度: {len(str(ticker))}")
        logger.info(f"🔍 [股票代码追踪] 股票代码字符: {list(str(ticker))}")

        # 保存原始ticker用于对比
        original_ticker = ticker

        try:
            from tradingagents.utils.stock_utils import StockUtils
            from datetime import datetime, timedelta

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info['is_china']
            is_hk = market_info['is_hk']
            is_us = market_info['is_us']

            logger.info(f"🔍 [股票代码追踪] StockUtils.get_market_info 返回的市场信息: {market_info}")
            logger.info(f"📊 [统一基本面工具] 股票类型: {market_info['market_name']}")
            logger.info(f"📊 [统一基本面工具] 货币: {market_info['currency_name']} ({market_info['currency_symbol']})")

            # 检查ticker是否在处理过程中发生了变化
            if str(ticker) != str(original_ticker):
                logger.warning(f"🔍 [股票代码追踪] 警告：股票代码发生了变化！原始: '{original_ticker}' -> 当前: '{ticker}'")

            # 设置默认日期
            if not curr_date:
                curr_date = datetime.now().strftime('%Y-%m-%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = curr_date

            result_data = []

            if is_china:
                # 中国A股：获取股票数据 + 基本面数据
                logger.info(f"🇨🇳 [统一基本面工具] 处理A股数据...")
                logger.info(f"🔍 [股票代码追踪] 进入A股处理分支，ticker: '{ticker}'")

                try:
                    # 获取股票价格数据
                    from tradingagents.dataflows.interface import get_china_stock_data_unified
                    logger.info(f"🔍 [股票代码追踪] 调用 get_china_stock_data_unified，传入参数: ticker='{ticker}', start_date='{start_date}', end_date='{end_date}'")
                    stock_data = get_china_stock_data_unified(ticker, start_date, end_date)
                    logger.info(f"🔍 [股票代码追踪] get_china_stock_data_unified 返回结果前200字符: {stock_data[:200] if stock_data else 'None'}")
                    result_data.append(f"## A股价格数据\n{stock_data}")
                except Exception as e:
                    logger.error(f"🔍 [股票代码追踪] get_china_stock_data_unified 调用失败: {e}")
                    result_data.append(f"## A股价格数据\n获取失败: {e}")

                try:
                    # 获取基本面数据
                    from tradingagents.dataflows.optimized_china_data import OptimizedChinaDataProvider
                    analyzer = OptimizedChinaDataProvider()
                    logger.info(f"🔍 [股票代码追踪] 调用 OptimizedChinaDataProvider._generate_fundamentals_report，传入参数: ticker='{ticker}'")
                    fundamentals_data = analyzer._generate_fundamentals_report(ticker, stock_data if 'stock_data' in locals() else "")
                    logger.info(f"🔍 [股票代码追踪] _generate_fundamentals_report 返回结果前200字符: {fundamentals_data[:200] if fundamentals_data else 'None'}")
                    result_data.append(f"## A股基本面数据\n{fundamentals_data}")
                except Exception as e:
                    logger.error(f"🔍 [股票代码追踪] _generate_fundamentals_report 调用失败: {e}")
                    result_data.append(f"## A股基本面数据\n获取失败: {e}")

            elif is_hk:
                # 港股：使用AKShare数据源，支持多重备用方案
                logger.info(f"🇭🇰 [统一基本面工具] 处理港股数据...")

                hk_data_success = False

                # 主要数据源：AKShare
                try:
                    from tradingagents.dataflows.interface import get_hk_stock_data_unified
                    hk_data = get_hk_stock_data_unified(ticker, start_date, end_date)

                    # 检查数据质量
                    if hk_data and len(hk_data) > 100 and "❌" not in hk_data:
                        result_data.append(f"## 港股数据\n{hk_data}")
                        hk_data_success = True
                        logger.info(f"✅ [统一基本面工具] 港股主要数据源成功")
                    else:
                        logger.warning(f"⚠️ [统一基本面工具] 港股主要数据源质量不佳")

                except Exception as e:
                    logger.error(f"⚠️ [统一基本面工具] 港股主要数据源失败: {e}")

                # 备用方案：基础港股信息
                if not hk_data_success:
                    try:
                        from tradingagents.dataflows.interface import get_hk_stock_info_unified
                        hk_info = get_hk_stock_info_unified(ticker)

                        basic_info = f"""## 港股基础信息

**股票代码**: {ticker}
**股票名称**: {hk_info.get('name', f'港股{ticker}')}
**交易货币**: 港币 (HK$)
**交易所**: 香港交易所 (HKG)
**数据源**: {hk_info.get('source', '基础信息')}

⚠️ 注意：详细的价格和财务数据暂时无法获取，建议稍后重试或使用其他数据源。

**基本面分析建议**：
- 建议查看公司最新财报
- 关注港股市场整体走势
- 考虑汇率因素对投资的影响
"""
                        result_data.append(basic_info)
                        logger.info(f"✅ [统一基本面工具] 港股备用信息成功")

                    except Exception as e2:
                        # 最终备用方案
                        fallback_info = f"""## 港股信息（备用）

**股票代码**: {ticker}
**股票类型**: 港股
**交易货币**: 港币 (HK$)
**交易所**: 香港交易所 (HKG)

❌ 数据获取遇到问题: {str(e2)}

**建议**：
1. 检查网络连接
2. 稍后重试分析
3. 使用其他港股数据源
4. 查看公司官方财报
"""
                        result_data.append(fallback_info)
                        logger.warning(f"⚠️ [统一基本面工具] 港股使用最终备用方案")

            else:
                # 美股：使用OpenAI/Finnhub数据源
                logger.info(f"🇺🇸 [统一基本面工具] 处理美股数据...")

                try:
                    from tradingagents.dataflows.interface import get_fundamentals_openai
                    us_data = get_fundamentals_openai(ticker, curr_date)
                    result_data.append(f"## 美股基本面数据\n{us_data}")
                except Exception as e:
                    result_data.append(f"## 美股基本面数据\n获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 基本面分析数据

**股票类型**: {market_info['market_name']}
**货币**: {market_info['currency_name']} ({market_info['currency_symbol']})
**分析日期**: {curr_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的数据源*
"""

            logger.info(f"📊 [统一基本面工具] 数据获取完成，总长度: {len(combined_result)}")
            return combined_result

        except Exception as e:
            error_msg = f"统一基本面分析工具执行失败: {str(e)}"
            logger.error(f"❌ [统一基本面工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_market_data_unified", log_args=True)
    def get_stock_market_data_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"]
    ) -> str:
        """
        统一的股票市场数据工具
        自动识别股票类型（A股、港股、美股）并调用相应的数据源获取价格和技术指标数据

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            start_date: 开始日期（格式：YYYY-MM-DD）
            end_date: 结束日期（格式：YYYY-MM-DD）

        Returns:
            str: 市场数据和技术分析报告
        """
        logger.info(f"📈 [统一市场工具] 分析股票: {ticker}")

        try:
            from tradingagents.utils.stock_utils import StockUtils

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info['is_china']
            is_hk = market_info['is_hk']
            is_us = market_info['is_us']
            is_crypto = market_info['is_crypto']

            logger.info(f"📈 [统一市场工具] 股票类型: {market_info['market_name']}")
            logger.info(f"📈 [统一市场工具] 货币: {market_info['currency_name']} ({market_info['currency_symbol']}")

            result_data = []

            if is_china:
                # 中国A股：使用中国股票数据源
                logger.info(f"🇨🇳 [统一市场工具] 处理A股市场数据...")

                try:
                    from tradingagents.dataflows.interface import get_china_stock_data_unified
                    stock_data = get_china_stock_data_unified(ticker, start_date, end_date)
                    result_data.append(f"## A股市场数据\n{stock_data}")
                except Exception as e:
                    result_data.append(f"## A股市场数据\n获取失败: {e}")

            elif is_hk:
                # 港股：使用AKShare数据源
                logger.info(f"🇭🇰 [统一市场工具] 处理港股市场数据...")

                try:
                    from tradingagents.dataflows.interface import get_hk_stock_data_unified
                    hk_data = get_hk_stock_data_unified(ticker, start_date, end_date)
                    result_data.append(f"## 港股市场数据\n{hk_data}")
                except Exception as e:
                    result_data.append(f"## 港股市场数据\n获取失败: {e}")

            elif is_crypto:
                # 加密货币：使用加密货币数据源
                logger.info(f"🪙 [统一市场工具] 处理加密货币市场数据...")

                try:
                    from tradingagents.dataflows.crypto_data_source_manager import get_crypto_data_unified
                    from datetime import datetime
                    
                    # 将日期范围转换为天数
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    days = (end_dt - start_dt).days + 1
                    
                    # 将加密货币符号转换为CoinGecko ID
                    coin_id = ticker.lower()  # 大多数情况下，符号就是ID
                    if coin_id == 'btc':
                        coin_id = 'bitcoin'
                    elif coin_id == 'eth':
                        coin_id = 'ethereum'
                    elif coin_id == 'ada':
                        coin_id = 'cardano'
                    
                    crypto_data = get_crypto_data_unified(coin_id, 'usd', days, 'market')
                    result_data.append(f"## 加密货币市场数据\n{crypto_data}")
                except Exception as e:
                    result_data.append(f"## 加密货币市场数据\n获取失败: {e}")

            else:
                # 美股：使用Yahoo Finance数据源
                logger.info(f"🇺🇸 [统一市场工具] 处理美股市场数据...")

                try:
                    from tradingagents.dataflows.interface import get_YFin_data_online
                    us_data = get_YFin_data_online(ticker, start_date, end_date)
                    result_data.append(f"## 美股市场数据\n{us_data}")
                except Exception as e:
                    result_data.append(f"## 美股市场数据\n获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 市场数据分析

**股票类型**: {market_info['market_name']}
**货币**: {market_info['currency_name']} ({market_info['currency_symbol']})
**分析期间**: {start_date} 至 {end_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的数据源*
"""

            logger.info(f"📈 [统一市场工具] 数据获取完成，总长度: {len(combined_result)}")
            return combined_result

        except Exception as e:
            error_msg = f"统一市场数据工具执行失败: {str(e)}"
            logger.error(f"❌ [统一市场工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_news_unified", log_args=True)
    def get_stock_news_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"]
    ) -> str:
        """
        统一的股票新闻工具
        自动识别股票类型（A股、港股、美股）并调用相应的新闻数据源

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            curr_date: 当前日期（格式：YYYY-MM-DD）

        Returns:
            str: 新闻分析报告
        """
        logger.info(f"📰 [统一新闻工具] 分析股票: {ticker}")

        try:
            from tradingagents.utils.stock_utils import StockUtils
            from datetime import datetime, timedelta

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info['is_china']
            is_hk = market_info['is_hk']
            is_us = market_info['is_us']

            logger.info(f"📰 [统一新闻工具] 股票类型: {market_info['market_name']}")

            # 计算新闻查询的日期范围
            end_date = datetime.strptime(curr_date, '%Y-%m-%d')
            start_date = end_date - timedelta(days=7)
            start_date_str = start_date.strftime('%Y-%m-%d')

            result_data = []

            if is_china or is_hk:
                # 中国A股和港股：使用AKShare东方财富新闻和Google新闻（中文搜索）
                logger.info(f"🇨🇳🇭🇰 [统一新闻工具] 处理中文新闻...")

                # 1. 尝试获取AKShare东方财富新闻
                try:
                    # 处理股票代码
                    clean_ticker = ticker.replace('.SH', '').replace('.SZ', '').replace('.SS', '').replace('.HK', '').replace('.XSHE', '').replace('.XSHG', '')
                    
                    logger.info(f"🇨🇳🇭🇰 [统一新闻工具] 尝试获取东方财富新闻: {clean_ticker}")
                    
                    # 导入AKShare新闻获取函数
                    from tradingagents.dataflows.akshare_utils import get_stock_news_em
                    
                    # 获取东方财富新闻
                    news_df = get_stock_news_em(clean_ticker)
                    
                    if not news_df.empty:
                        # 格式化东方财富新闻
                        em_news_items = []
                        for _, row in news_df.iterrows():
                            news_title = row.get('标题', '')
                            news_time = row.get('时间', '')
                            news_url = row.get('链接', '')
                            
                            news_item = f"- **{news_title}** [{news_time}]({news_url})"
                            em_news_items.append(news_item)
                        
                        # 添加到结果中
                        if em_news_items:
                            em_news_text = "\n".join(em_news_items)
                            result_data.append(f"## 东方财富新闻\n{em_news_text}")
                            logger.info(f"🇨🇳🇭🇰 [统一新闻工具] 成功获取{len(em_news_items)}条东方财富新闻")
                except Exception as em_e:
                    logger.error(f"❌ [统一新闻工具] 东方财富新闻获取失败: {em_e}")
                    result_data.append(f"## 东方财富新闻\n获取失败: {em_e}")

                # 2. 获取Google新闻作为补充
                try:
                    # 获取公司中文名称用于搜索
                    if is_china:
                        # A股使用股票代码搜索，添加更多中文关键词
                        clean_ticker = ticker.replace('.SH', '').replace('.SZ', '').replace('.SS', '').replace('.XSHE', '').replace('.XSHG', '')
                        search_query = f"{clean_ticker} 股票 公司 财报 新闻"
                        logger.info(f"🇨🇳 [统一新闻工具] A股Google新闻搜索关键词: {search_query}")
                    else:
                        # 港股使用代码搜索
                        search_query = f"{ticker} 港股"
                        logger.info(f"🇭🇰 [统一新闻工具] 港股Google新闻搜索关键词: {search_query}")

                    from tradingagents.dataflows.interface import get_google_news
                    news_data = get_google_news(search_query, curr_date)
                    result_data.append(f"## Google新闻\n{news_data}")
                    logger.info(f"🇨🇳🇭🇰 [统一新闻工具] 成功获取Google新闻")
                except Exception as google_e:
                    logger.error(f"❌ [统一新闻工具] Google新闻获取失败: {google_e}")
                    result_data.append(f"## Google新闻\n获取失败: {google_e}")

            else:
                # 美股：使用Finnhub新闻
                logger.info(f"🇺🇸 [统一新闻工具] 处理美股新闻...")

                try:
                    from tradingagents.dataflows.interface import get_finnhub_news
                    news_data = get_finnhub_news(ticker, start_date_str, curr_date)
                    result_data.append(f"## 美股新闻\n{news_data}")
                except Exception as e:
                    result_data.append(f"## 美股新闻\n获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 新闻分析

**股票类型**: {market_info['market_name']}
**分析日期**: {curr_date}
**新闻时间范围**: {start_date_str} 至 {curr_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的新闻源*
"""

            logger.info(f"📰 [统一新闻工具] 数据获取完成，总长度: {len(combined_result)}")
            return combined_result

        except Exception as e:
            error_msg = f"统一新闻工具执行失败: {str(e)}"
            logger.error(f"❌ [统一新闻工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_sentiment_unified", log_args=True)
    def get_stock_sentiment_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"]
    ) -> str:
        """
        统一的股票情绪分析工具
        自动识别股票类型（A股、港股、美股）并调用相应的情绪数据源

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            curr_date: 当前日期（格式：YYYY-MM-DD）

        Returns:
            str: 情绪分析报告
        """
        logger.info(f"😊 [统一情绪工具] 分析股票: {ticker}")

        try:
            from tradingagents.utils.stock_utils import StockUtils

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info['is_china']
            is_hk = market_info['is_hk']
            is_us = market_info['is_us']

            logger.info(f"😊 [统一情绪工具] 股票类型: {market_info['market_name']}")

            result_data = []

            if is_china or is_hk:
                # 中国A股和港股：使用社交媒体情绪分析
                logger.info(f"🇨🇳🇭🇰 [统一情绪工具] 处理中文市场情绪...")

                try:
                    # 可以集成微博、雪球、东方财富等中文社交媒体情绪
                    # 目前使用基础的情绪分析
                    sentiment_summary = f"""
## 中文市场情绪分析

**股票**: {ticker} ({market_info['market_name']})
**分析日期**: {curr_date}

### 市场情绪概况
- 由于中文社交媒体情绪数据源暂未完全集成，当前提供基础分析
- 建议关注雪球、东方财富、同花顺等平台的讨论热度
- 港股市场还需关注香港本地财经媒体情绪

### 情绪指标
- 整体情绪: 中性
- 讨论热度: 待分析
- 投资者信心: 待评估

*注：完整的中文社交媒体情绪分析功能正在开发中*
"""
                    result_data.append(sentiment_summary)
                except Exception as e:
                    result_data.append(f"## 中文市场情绪\n获取失败: {e}")

            else:
                # 美股：使用Reddit情绪分析
                logger.info(f"🇺🇸 [统一情绪工具] 处理美股情绪...")

                try:
                    from tradingagents.dataflows.interface import get_reddit_sentiment

                    sentiment_data = get_reddit_sentiment(ticker, curr_date)
                    result_data.append(f"## 美股Reddit情绪\n{sentiment_data}")
                except Exception as e:
                    result_data.append(f"## 美股Reddit情绪\n获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 情绪分析

**股票类型**: {market_info['market_name']}
**分析日期**: {curr_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的情绪数据源*
"""

            logger.info(f"😊 [统一情绪工具] 数据获取完成，总长度: {len(combined_result)}")
            return combined_result

        except Exception as e:
            error_msg = f"统一情绪分析工具执行失败: {str(e)}"
            logger.error(f"❌ [统一情绪工具] {error_msg}")
            return error_msg

    # ==================== 加密货币项目分析工具 ====================
    
    @staticmethod
    def _get_crypto_project_base_data(coin_id: str) -> dict:
        """
        获取加密货币项目的基础数据（内部方法，供其他工具调用）
        
        Args:
            coin_id (str): CoinGecko格式的币种ID
            
        Returns:
            dict: 包含项目信息、市场数据、链接等的基础数据
        """
        try:
            from tradingagents.dataflows.crypto_project_repository import (
                get_project_bundle,
                render_project_info,
            )
            
            # 命中请求级缓存（120秒内有效）
            try:
                self_ref = Toolkit
                # 静态方法内无法直接访问实例缓存；改用类属性作为轻量全局缓存
                if not hasattr(self_ref, "__crypto_ctx_cache__"):
                    self_ref.__crypto_ctx_cache__ = {}
                cache_entry = self_ref.__crypto_ctx_cache__.get(coin_id)
                if cache_entry and (time.time() - cache_entry.get("ts", 0) < 120):
                    return cache_entry["data"]
            except Exception:
                pass

            # 通过 repository 统一获取结构化数据并渲染文本视图
            bundle = get_project_bundle(coin_id)
            coin_data = bundle.get('coin_data')
            project_info = render_project_info(coin_data) if coin_data else f"❌ 无法获取 {coin_id} 的项目信息"
            
            data = {
                'project_info': project_info,
                'coin_data': coin_data,
                'coin_id': coin_id
            }

            # 写入请求级缓存
            try:
                Toolkit.__crypto_ctx_cache__[coin_id] = {"data": data, "ts": time.time()}
            except Exception:
                pass
            return data
        except Exception as e:
            logger.error(f"获取项目基础数据失败: {e}")
            return {
                'project_info': None,
                'coin_data': None,
                'coin_id': coin_id,
                'error': str(e)
            }
    
    @staticmethod
    @tool
    def get_crypto_whitepaper_analysis(coin_id: str) -> str:
        """
        获取并分析加密货币项目的白皮书内容。
        该工具会首先尝试查找并解析PDF格式的白皮书。如果失败，它将尝试抓取并解析在线HTML文档网站。
        """
        try:
            base_data = Toolkit._get_crypto_project_base_data(coin_id)
            project_info_text = base_data.get('project_info')
            coin_dict = base_data.get('coin_data')
            
            if not project_info_text or not coin_dict:
                return f"❌ 无法获取 {coin_id} 的基础项目信息，白皮书分析中止。"

            project_slug = Toolkit._slugify_project_name(coin_id, coin_dict)
            Toolkit._ensure_dir(f"data/crypto/whitepapers/{project_slug}")

            all_links_groups = Toolkit._collect_whitepaper_links(project_info_text, coin_dict)
            
            # 策略1：尝试解析PDF
            pdf_urls = list(dict.fromkeys(all_links_groups.get('pdf', [])))
            if pdf_urls:
                pdf_summary, parsed_url = Toolkit._try_parse_pdf(coin_id, pdf_urls)
                if pdf_summary and parsed_url:
                    local_pdf_path = Toolkit._save_whitepaper_pdf(coin_id, parsed_url, project_slug)
                    logger.info(f"✅ 成功从PDF获取白皮书摘要: {local_pdf_path}")
                    return Toolkit._render_whitepaper_report(coin_id, coin_dict, project_info_text, pdf_summary=pdf_summary, local_pdf_path=local_pdf_path)

            # 策略2：如果PDF失败，尝试从HTML文档网站抓取
            html_candidates_urls = Toolkit._discover_html_candidates(all_links_groups, project_info_text, coin_dict)
            if html_candidates_urls:
                logger.info(f"🔍 未找到可用PDF, 尝试从 {html_candidates_urls[0]} 开始抓取HTML文档...")
                docs_url = html_candidates_urls[0]
                try:
                    downloader = GitbookDownloader(base_url=docs_url)
                    full_markdown_content = asyncio.run(downloader.download())

                    if full_markdown_content and len(full_markdown_content) > 100:
                        local_md_path = Toolkit._save_html_markdown(coin_id, full_markdown_content, project_slug)
                        logger.info(f"✅ 成功抓取并转换HTML文档为Markdown: {local_md_path}")
                        return Toolkit._render_whitepaper_report(coin_id, coin_dict, project_info_text, html_summary=full_markdown_content, local_html_path=local_md_path)
                    else:
                        logger.warning(f"抓取HTML文档失败或内容过短: {docs_url}")
                except Exception as e:
                    logger.error(f"执行Gitbook下载器时出错: {docs_url}, 错误: {e}")

            logger.warning(f"所有白皮书自动提取策略均失败({coin_id})。")
            return Toolkit._render_whitepaper_report(coin_id, coin_dict, project_info_text)
        except Exception as e:
            logger.error(f"白皮书分析失败: {e}")
            return f"❌ 白皮书分析过程中发生错误: {e}"

    @staticmethod
    def _slugify_project_name(coin_id, coin_dict):
        name = coin_dict.get('name') if isinstance(coin_dict, dict) else None
        if not name:
            name = coin_id
        s = str(name).strip().lower()
        s = re.sub(r"\s+", "-", s)
        s = re.sub(r"[^a-z0-9\-_]", "", s)
        return s or coin_id

    @staticmethod
    def _ensure_dir(path: str):
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            pass

    @staticmethod
    def _save_whitepaper_pdf(coin_id, pdf_url: str, project_slug: str):
        try:
            from urllib.parse import urlparse
            import requests
            
            base_dir = os.path.join("data", "crypto", "whitepapers", project_slug)
            Toolkit._ensure_dir(base_dir)
            fn = f"{project_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            out_path = os.path.join(base_dir, fn)

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            with requests.get(pdf_url, stream=True, timeout=30, headers=headers) as r:
                r.raise_for_status()
                with open(out_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return out_path
        except Exception as e:
            logger.debug(f"保存白皮书PDF失败: {e}")
            return None

    @staticmethod
    def _save_html_markdown(coin_id, md_text: str, project_slug: str) -> str:
        try:
            base_dir = os.path.join("data", "crypto", "whitepapers", project_slug)
            Toolkit._ensure_dir(base_dir)
            fn = f"{project_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            out_path = os.path.join(base_dir, fn)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(md_text)
            return out_path
        except Exception as e:
            logger.debug(f"保存白皮书Markdown失败: {e}")
            return ""

    @staticmethod
    def _collect_whitepaper_links(project_info_text, coin_dict):
        groups = {'pdf': [], 'github': [], 'website': [], 'docs': []}
        
        # From project_info text (less reliable, but good for PDFs)
        if isinstance(project_info_text, str):
            pdf_patterns = [
                r'https?://[^\s<>"{}|\\^`\[\]]+\.pdf'
            ]
            for pat in pdf_patterns:
                groups['pdf'].extend(re.findall(pat, project_info_text, re.IGNORECASE))
        
        # From coin_data (source of truth for official links)
        if isinstance(coin_dict, dict):
            # The 'links' object might be missing, so we check top-level keys directly.
            
            # Website/Homepage links
            homepage_val = coin_dict.get('homepage')
            if isinstance(homepage_val, str) and homepage_val:
                groups['website'].append(homepage_val)
            
            # Attempt to find documentation links from raw_data if available
            raw_data = coin_dict.get('raw_data', {})
            if isinstance(raw_data, dict):
                raw_links = raw_data.get('links', {})
                if isinstance(raw_links, dict):
                    # Official Documentation links (high priority)
                    for key in ['documentation', 'docs', 'technical_doc', 'whitepaper']:
                        value = raw_links.get(key)
                        if isinstance(value, list):
                            groups['docs'].extend(filter(None, value))
                        elif isinstance(value, str) and value:
                            groups['docs'].append(value)

                    # Github links from raw data for robustness
                    repos = raw_links.get('repos_url', {}).get('github', [])
                    groups['github'].extend(repos if isinstance(repos, list) else [repos] if repos else [])

        # Clean up duplicates
        for key in groups:
            groups[key] = list(dict.fromkeys(filter(None, groups[key])))
            
        logger.info(f"🔗 链接收集结果: { {k: v for k, v in groups.items() if v} }")
        return groups

    @staticmethod
    def _try_parse_pdf(coin_id, pdf_urls):
        if not pdf_urls:
            return None, None
        try:
            parser = get_whitepaper_parser()
            for url in pdf_urls[:3]:
                logger.info(f"正在解析白皮书: {url}")
                content = parser.parse_whitepaper(url, coin_id)
                if content and 'error' not in content:
                    return content, url
        except Exception as e:
            logger.warning(f"白皮书解析失败: {e}")
        return None, None

    @staticmethod
    def _discover_html_candidates(groups, project_info_text, coin_dict):
        from urllib.parse import urlparse
        
        # --- Priority 1: Explicit documentation links from coin_data ---
        doc_urls = groups.get('docs', [])
        if doc_urls:
            logger.info(f"发现 {len(doc_urls)} 个官方文档链接，将优先使用: {doc_urls[:3]}")
            return doc_urls[:5] # Return up to 5 official doc URLs

        # --- Priority 2: Guess from website/homepage ---
        logger.info("未找到官方文档链接，尝试从官网猜测...")
        
        # Gather base domains from official websites
        base_domains = set()
        website_urls = groups.get('website', [])
        for url in website_urls:
            try:
                host = urlparse(url).netloc
                if host: base_domains.add(host.replace('www.', ''))
            except: continue
        
        # Generate candidate URLs with common doc subdomains
        candidates = set(website_urls) # Start with the original websites
        for domain in base_domains:
            for sub in ['docs', 'documentation', 'help', 'developers', 'wiki', 'blog']:
                candidates.add(f"https://{sub}.{domain}")
                
        final_list = list(dict.fromkeys(filter(None, candidates)))
        
        logger.info(f"构建了 {len(final_list)} 个HTML候选页面: {final_list[:3]}")
        return final_list[:5]

    @staticmethod
    def _render_whitepaper_report(
        coin_id: str,
        coin_dict: dict,
        project_info_text: str,
        pdf_summary: Optional[dict] = None,
        html_summary: Optional[str] = None,
        local_pdf_path: Optional[str] = None,
        local_html_path: Optional[str] = None
    ) -> str:
        lines = [f"📄 **{coin_dict.get('name', coin_id.upper())} 白皮书与文档分析**\n"]
        
        if local_pdf_path or local_html_path:
            lines.append("\n**📦 本地资产**")
            if local_pdf_path: lines.append(f"- 已保存PDF: `{local_pdf_path}`")
            if local_html_path: lines.append(f"- 已保存Markdown副本: `{local_html_path}`")
        
        if pdf_summary: lines.extend(Toolkit._lines_pdf_summary(pdf_summary, local_pdf_path))
        if html_summary: lines.extend(Toolkit._lines_html_summary(html_summary, local_html_path))

        if not pdf_summary and not html_summary:
            lines.append("\n**⚠️ 未能自动提取白皮书或文档内容。**\n请参考下面的资源链接进行手动分析。")

        all_links = Toolkit._collect_whitepaper_links(project_info_text, coin_dict)
        lines.append("\n**🔗 相关资源链接**")
        for link_type, urls in all_links.items():
            if urls:
                unique_urls = list(dict.fromkeys(filter(None, urls)))
                if unique_urls: lines.append(f"- **{link_type.replace('_', ' ').title()}**: {unique_urls[0]}")

        lines.extend(Toolkit._lines_recommendations())
        return "\n".join(lines)

    @staticmethod
    def _lines_pdf_summary(summary: dict, local_path: Optional[str]) -> List[str]:
        lines = ["\n**📄 PDF白皮书摘要**"]
        sections = summary.get('sections', {})
        if sections:
             for section, content_list in sections.items():
                 if content_list: lines.append(f"  - **{section.replace('_', ' ').title()}**: {content_list[0][:150]}...")
        else:
            lines.append(f"  - 提取文本预览: {summary.get('text', '')[:200]}...")
        return lines

    @staticmethod
    def _lines_html_summary(summary: str, local_path: Optional[str]) -> List[str]:
        lines = ["\n**🌐 HTML文档摘要**"]
        summary_preview = (summary[:1500] + '\n...') if len(summary) > 1500 else summary
        lines.append(f"```markdown\n{summary_preview}\n```")
        return lines

    @staticmethod
    def _lines_recommendations() -> List[str]:
        return [
            "\n**💡 分析建议**",
            "- **技术深度**: 审查GitHub仓库以评估开发活动的真实性。",
            "- **经济模型**: 仔细分析Tokenomics，特别是代币分配和释放计划。",
            "- **团队背景**: 深入调查核心团队成员的背景和过往项目经验。",
            "- **路线图**: 对比路线图承诺和实际开发进展。"
        ]

    @staticmethod
    @tool
    def get_crypto_team_governance(coin_id: str) -> str:
        """
        获取项目团队和治理结构信息（白皮书分析的深化）
        
        Args:
            coin_id (str): CoinGecko格式的币种ID
            
        Returns:
            str: 团队和治理分析结果
        """
        try:
            # 获取项目基础数据
            base_data = Toolkit._get_crypto_project_base_data(coin_id)
            
            if base_data.get('error'):
                return f"❌ 无法获取 {coin_id} 的项目信息: {base_data['error']}"
            
            project_info = base_data['project_info']
            coin_data = base_data['coin_data']
            
            if not project_info or isinstance(project_info, str) and project_info.strip().startswith("❌"):
                return f"❌ 无法获取 {coin_id} 的项目信息"
            
            analysis = f"👥 {coin_id.upper()} 团队与治理分析\n\n"
            
            # 1. 尝试从白皮书缓存中获取团队信息
            team_info_sections = []
            whitepaper_team_info = None
            
            try:
                from tradingagents.dataflows.whitepaper_parser import get_whitepaper_parser
                parser = get_whitepaper_parser()
                
                # 查找缓存的白皮书文件
                cache_dir = Path("./cache/whitepapers")
                if cache_dir.exists():
                    cached_files = list(cache_dir.glob(f"{coin_id}_*.pdf"))
                    if cached_files:
                        # 使用最新的缓存文件
                        latest_file = max(cached_files, key=os.path.getctime)
                        logger.info(f"发现缓存的白皮书: {latest_file}")
                        
                        # 直接解析本地PDF文件
                        whitepaper_content = parser.parse_pdf(str(latest_file))
                        if "error" not in whitepaper_content:
                            sections = whitepaper_content.get('sections', {})
                            whitepaper_team_info = sections.get('team_info', [])
                            
                            if whitepaper_team_info:
                                team_info_sections.append("📄 白皮书中的团队信息:")
                                for info in whitepaper_team_info[:5]:
                                    team_info_sections.append(f"- {info}")
            except Exception as e:
                logger.debug(f"白皮书团队信息获取失败: {e}")
            
            # 2. 从项目描述信息中提取团队相关信息（备用方案）
            if not whitepaper_team_info:
                if isinstance(project_info, str):
                    # 查找团队相关关键词（注意：这是项目描述，不是完整白皮书）
                    team_keywords = ['team', 'founder', 'developer', 'core team', 'advisors', 'governance', 'leadership', 'creator']
                    found_info = []
                    
                    lines = project_info.split('\n')
                    for line in lines:
                        if any(keyword.lower() in line.lower() for keyword in team_keywords):
                            found_info.append(line.strip())
                    
                    if found_info:
                        team_info_sections.append("🔍 项目描述中的团队信息:")
                        for info in found_info[:5]:  # 最多显示5条
                            team_info_sections.append(f"- {info}")
                    else:
                        team_info_sections.append("❌ 未在项目描述中找到明确的团队信息")
                        team_info_sections.append("💡 建议查看白皮书分析工具获取更详细的团队信息")
            
            # 2. 从CoinGecko结构化数据中提取团队信息
            if isinstance(coin_data, dict):
                # 提取创始人信息
                if 'name' in coin_data:
                    team_info_sections.append(f"\n📋 项目基本信息:")
                    team_info_sections.append(f"- 项目名称: {coin_data.get('name', 'N/A')}")
                    team_info_sections.append(f"- 符号: {coin_data.get('symbol', 'N/A')}")
                    description = coin_data.get('description', {})
                    if isinstance(description, dict):
                        desc_text = description.get('en', 'N/A')
                    else:
                        desc_text = str(description)
                    team_info_sections.append(f"- 描述: {desc_text[:200]}...")
                
                # 提取链接信息中的团队相关链接
                links = coin_data.get('links', {})
                if links:
                    team_info_sections.append(f"\n🔗 相关链接:")
                    
                    # GitHub链接（开发团队）
                    github_repos = links.get('repos_url', {}).get('github', [])
                    if github_repos:
                        team_info_sections.append(f"- GitHub仓库: {github_repos[0]}")
                        team_info_sections.append(f"  - 建议查看Contributors页面了解开发团队")
                    
                    # 官网链接
                    if links.get('homepage'):
                        team_info_sections.append(f"- 项目官网: {links['homepage']}")
                        team_info_sections.append(f"  - 建议查看About/Team页面")
                    
                    # 社交媒体链接
                    social_links = []
                    for key, value in links.items():
                        if key in ['twitter_screen_name', 'telegram_channel_identifier', 'reddit_url']:
                            if value:
                                social_links.append(f"- {key.replace('_', ' ').title()}: {value}")
                    
                    if social_links:
                        team_info_sections.append(f"\n📱 社交媒体渠道:")
                        team_info_sections.extend(social_links)
            else:
                team_info_sections.append(f"\n❌ 无法获取CoinGecko结构化数据")
            
            # 3. 添加团队分析框架
            team_info_sections.append(f"\n📊 团队分析框架:")
            team_info_sections.append(f"1. 核心团队:")
            team_info_sections.append(f"   - 创始人背景和经验")
            team_info_sections.append(f"   - 核心开发团队规模")
            team_info_sections.append(f"   - 技术顾问和专家")
            team_info_sections.append(f"   - 行业经验和声誉")
            
            team_info_sections.append(f"\n2. 治理结构:")
            team_info_sections.append(f"   - 决策机制和投票权")
            team_info_sections.append(f"   - 去中心化程度")
            team_info_sections.append(f"   - 社区参与度")
            team_info_sections.append(f"   - 透明度水平")
            
            team_info_sections.append(f"\n3. 开发活跃度:")
            team_info_sections.append(f"   - 代码提交频率")
            team_info_sections.append(f"   - 版本发布节奏")
            team_info_sections.append(f"   - 社区贡献度")
            team_info_sections.append(f"   - 技术更新频率")
            
            # 4. 添加评估要点
            team_info_sections.append(f"\n💡 关键评估指标:")
            team_info_sections.append(f"- 团队背景的匹配度（技术vs商业）")
            team_info_sections.append(f"- 长期承诺和稳定性")
            team_info_sections.append(f"- 社区治理的参与度")
            team_info_sections.append(f"- 技术创新的前瞻性")
            
            # 组合所有信息
            analysis += "\n".join(team_info_sections)
            
            # 尝试获取GitHub信息
            try:
                if isinstance(coin_data, dict):
                    links = coin_data.get('links', {})
                    github_url = links.get('repos_url', {}).get('github', [])
                    
                    if github_url:
                        analysis += f"\n🔗 GitHub仓库: {github_url[0] if github_url else 'N/A'}\n"
                        analysis += f"- 建议查看GitHub的Contributors页面了解开发团队\n"
                        analysis += f"- 关注代码提交频率和活跃度\n"
            except Exception as e:
                logger.warning(f"获取GitHub信息失败: {e}")
            
            analysis += f"\n📊 治理结构分析:\n"
            analysis += f"- 治理代币: 需要查看项目文档确认\n"
            analysis += f"- 投票机制: 需要了解具体的治理流程\n"
            analysis += f"- 去中心化程度: 基于团队透明度评估\n"
            
            analysis += f"\n💡 评估要点:\n"
            analysis += f"- 团队背景和经验\n"
            analysis += f"- 开发活跃度和代码质量\n"
            analysis += f"- 社区参与度和治理透明度\n"
            analysis += f"- 长期承诺和路线图执行能力\n"
            
            return analysis
            
        except Exception as e:
            logger.error(f"团队信息获取失败: {e}")
            return f"❌ 团队信息获取过程中发生错误: {e}"

    @staticmethod
    @tool
    def get_crypto_detailed_tokenomics(coin_id: str) -> str:
        """
        获取详细的Tokenomics分析
        
        Args:
            coin_id (str): CoinGecko格式的币种ID
            
        Returns:
            str: 详细的Tokenomics分析结果
        """
        try:
            # 获取项目基础数据
            base_data = Toolkit._get_crypto_project_base_data(coin_id)
            
            if base_data.get('error'):
                return f"❌ 无法获取 {coin_id} 的项目信息: {base_data['error']}"
            
            project_info = base_data['project_info']
            coin_data = base_data['coin_data']
            
            analysis = f"💰 {coin_id.upper()} Tokenomics 深度分析\n\n"
            
            # 1. 尝试从白皮书缓存中获取Tokenomics信息
            tokenomics_sections = []
            whitepaper_tokenomics_info = None
            
            try:
                from tradingagents.dataflows.whitepaper_parser import get_whitepaper_parser
                parser = get_whitepaper_parser()
                
                # 查找缓存的白皮书文件
                cache_dir = Path("./cache/whitepapers")
                if cache_dir.exists():
                    cached_files = list(cache_dir.glob(f"{coin_id}_*.pdf"))
                    if cached_files:
                        # 使用最新的缓存文件
                        latest_file = max(cached_files, key=os.path.getctime)
                        logger.info(f"发现缓存的白皮书: {latest_file}")
                        
                        # 直接解析本地PDF文件
                        whitepaper_content = parser.parse_pdf(str(latest_file))
                        if "error" not in whitepaper_content:
                            sections = whitepaper_content.get('sections', {})
                            whitepaper_tokenomics_info = sections.get('tokenomics', [])
                            
                            if whitepaper_tokenomics_info:
                                tokenomics_sections.append("📄 白皮书中的Tokenomics信息:")
                                for info in whitepaper_tokenomics_info[:5]:
                                    tokenomics_sections.append(f"- {info}")
            except Exception as e:
                logger.debug(f"白皮书Tokenomics信息获取失败: {e}")
            
            # 2. 从项目描述中提取Tokenomics信息（备用方案）
            if not whitepaper_tokenomics_info:
                if isinstance(project_info, str):
                    # 查找Tokenomics相关关键词（注意：这是项目描述，不是完整白皮书）
                    tokenomics_keywords = ['supply', 'circulating', 'total', 'max', 'inflation', 'deflation', 'token', 'economy', 'distribution', 'allocation', 'vesting', 'burn', 'mint']
                    found_info = []
                    
                    lines = project_info.split('\n')
                    for line in lines:
                        if any(keyword.lower() in line.lower() for keyword in tokenomics_keywords):
                            found_info.append(line.strip())
                    
                    if found_info:
                        tokenomics_sections.append("🔍 项目描述中的Tokenomics信息:")
                        for info in found_info[:5]:  # 最多显示5条
                            tokenomics_sections.append(f"- {info}")
                    else:
                        tokenomics_sections.append("❌ 未在项目描述中找到明确的Tokenomics信息")
                        tokenomics_sections.append("💡 建议查看白皮书分析工具获取更详细的Tokenomics信息")
            
            # 2. 从CoinGecko市场数据中提取Tokenomics信息
            if isinstance(coin_data, dict):
                market_data_info = coin_data.get('market_data', {})
                if market_data_info:
                    tokenomics_sections.append(f"\n📊 市场数据中的Tokenomics信息:")
                    
                    # 供应量信息
                    if 'total_supply' in market_data_info and market_data_info['total_supply'] is not None:
                        tokenomics_sections.append(f"- 总供应量: {market_data_info['total_supply']:,}")
                    if 'circulating_supply' in market_data_info and market_data_info['circulating_supply'] is not None:
                        tokenomics_sections.append(f"- 流通供应量: {market_data_info['circulating_supply']:,}")
                    if 'max_supply' in market_data_info and market_data_info['max_supply'] is not None:
                        tokenomics_sections.append(f"- 最大供应量: {market_data_info['max_supply']:,}")
                    
                    # 市值信息
                    if 'market_cap' in market_data_info and market_data_info['market_cap'] and 'usd' in market_data_info['market_cap']:
                        tokenomics_sections.append(f"- 市值: ${market_data_info['market_cap']['usd']:,}")
                    if 'fully_diluted_valuation' in market_data_info and market_data_info['fully_diluted_valuation'] and 'usd' in market_data_info['fully_diluted_valuation']:
                        tokenomics_sections.append(f"- 完全稀释估值: ${market_data_info['fully_diluted_valuation']['usd']:,}")
                    
                    # 价格信息
                    if 'current_price' in market_data_info and market_data_info['current_price'] and 'usd' in market_data_info['current_price']:
                        tokenomics_sections.append(f"- 当前价格: ${market_data_info['current_price']['usd']:,.2f}")
                    if 'price_change_percentage_24h' in market_data_info and market_data_info['price_change_percentage_24h'] is not None:
                        tokenomics_sections.append(f"- 24小时价格变化: {market_data_info['price_change_percentage_24h']:.2f}%")
            
            
            # 组合所有信息
            analysis += "\n".join(tokenomics_sections)
            
            # 添加Tokenomics分析框架
            analysis += f"\n📋 Tokenomics 分析框架:\n"
            analysis += f"1. 供应机制:\n"
            analysis += f"   - 总供应量: 需要查看项目文档\n"
            analysis += f"   - 流通供应量: 基于市场数据\n"
            analysis += f"   - 通胀/通缩机制: 需要分析代币释放计划\n"
            
            analysis += f"\n2. 分配结构:\n"
            analysis += f"   - 团队分配: 通常10-20%\n"
            analysis += f"   - 投资者分配: 通常20-40%\n"
            analysis += f"   - 社区/生态: 通常30-50%\n"
            analysis += f"   - 储备金: 通常5-15%\n"
            
            analysis += f"\n3. 释放机制:\n"
            analysis += f"   - 线性释放: 稳定但可能影响价格\n"
            analysis += f"   - 阶段性释放: 可能造成价格波动\n"
            analysis += f"   - 条件释放: 基于里程碑或业绩\n"
            
            analysis += f"\n4. 用途和价值捕获:\n"
            analysis += f"   - 治理权利: 投票权重和决策权\n"
            analysis += f"   - 费用支付: 网络使用费用\n"
            analysis += f"   - 质押奖励: 网络安全和参与激励\n"
            analysis += f"   - 生态激励: 开发者奖励和用户激励\n"
            
            analysis += f"\n💡 关键评估指标:\n"
            analysis += f"- 代币分配公平性\n"
            analysis += f"- 释放机制合理性\n"
            analysis += f"- 价值捕获能力\n"
            analysis += f"- 长期可持续性\n"
            
            return analysis
            
        except Exception as e:
            logger.error(f"Tokenomics分析失败: {e}")
            return f"❌ Tokenomics分析过程中发生错误: {e}"

    @staticmethod
    @tool
    def get_crypto_roadmap_development(coin_id: str) -> str:
        """
        获取项目路线图和开发进展信息（白皮书分析的深化）
        
        Args:
            coin_id (str): CoinGecko格式的币种ID
            
        Returns:
            str: 路线图和开发进展分析结果
        """
        try:
            # 获取项目基础数据
            base_data = Toolkit._get_crypto_project_base_data(coin_id)
            
            if base_data.get('error'):
                return f"❌ 无法获取 {coin_id} 的项目信息: {base_data['error']}"
            
            project_info = base_data['project_info']
            coin_data = base_data['coin_data']
            
            analysis = f"🗺️ {coin_id.upper()} 路线图与开发进展\n\n"
            
            # 使用已获取的结构化数据中的GitHub开发信息（避免重复请求）
            if isinstance(coin_data, dict):
                links = coin_data.get('links', {})
                github_urls = links.get('repos_url', {}).get('github', [])
                if github_urls:
                    analysis += f"🔗 主要代码仓库:\n"
                    for i, url in enumerate(github_urls[:3], 1):
                        analysis += f"  {i}. {url}\n"
                    analysis += f"\n💡 建议查看GitHub了解:\n"
                    analysis += f"- 最新提交和开发活跃度\n"
                    analysis += f"- 里程碑和版本发布\n"
                    analysis += f"- 社区贡献和协作情况\n"
            
            # 1. 尝试从白皮书缓存中获取路线图信息
            whitepaper_roadmap_info = None
            
            try:
                from tradingagents.dataflows.whitepaper_parser import get_whitepaper_parser
                parser = get_whitepaper_parser()
                
                # 查找缓存的白皮书文件
                cache_dir = Path("./cache/whitepapers")
                if cache_dir.exists():
                    cached_files = list(cache_dir.glob(f"{coin_id}_*.pdf"))
                    if cached_files:
                        # 使用最新的缓存文件
                        latest_file = max(cached_files, key=os.path.getctime)
                        logger.info(f"发现缓存的白皮书: {latest_file}")
                        
                        # 直接解析本地PDF文件
                        whitepaper_content = parser.parse_pdf(str(latest_file))
                        if "error" not in whitepaper_content:
                            sections = whitepaper_content.get('sections', {})
                            whitepaper_roadmap_info = sections.get('roadmap', [])
                            
                            if whitepaper_roadmap_info:
                                analysis += f"\n📄 白皮书中的路线图信息:\n"
                                for info in whitepaper_roadmap_info[:5]:
                                    analysis += f"- {info}\n"
            except Exception as e:
                logger.debug(f"白皮书路线图信息获取失败: {e}")
            
            # 2. 从项目信息中提取路线图信息（备用方案）
            if not whitepaper_roadmap_info:
                if project_info and not (isinstance(project_info, str) and project_info.strip().startswith("❌")):
                    analysis += f"\n📋 项目信息中的路线图线索:\n"
                    
                    roadmap_keywords = ['roadmap', 'milestone', 'phase', 'upgrade', 'launch', 'release']
                    if isinstance(project_info, str):
                        lines = project_info.split('\n')
                        roadmap_info = []
                        for line in lines:
                            if any(keyword.lower() in line.lower() for keyword in roadmap_keywords):
                                roadmap_info.append(line.strip())
                        
                        if roadmap_info:
                            for info in roadmap_info[:5]:
                                analysis += f"- {info}\n"
                        else:
                            analysis += f"- 未在项目信息中找到明确的路线图信息\n"
            
            # 添加路线图分析框架
            analysis += f"\n📊 路线图分析框架:\n"
            analysis += f"1. 技术路线图:\n"
            analysis += f"   - 核心功能开发\n"
            analysis += f"   - 性能优化升级\n"
            analysis += f"   - 安全性和稳定性改进\n"
            analysis += f"   - 跨链和互操作性\n"
            
            analysis += f"\n2. 生态建设:\n"
            analysis += f"   - 开发者工具和SDK\n"
            analysis += f"   - 合作伙伴和集成\n"
            analysis += f"   - 社区建设和治理\n"
            analysis += f"   - 应用和用例扩展\n"
            
            analysis += f"\n3. 市场推广:\n"
            analysis += f"   - 交易所上线计划\n"
            analysis += f"   - 机构合作和采用\n"
            analysis += f"   - 营销和品牌建设\n"
            analysis += f"   - 合规和监管适应\n"
            
            analysis += f"\n💡 关键评估指标:\n"
            analysis += f"- 开发进度与承诺的一致性\n"
            analysis += f"- 技术创新的前瞻性\n"
            analysis += f"- 生态建设的可持续性\n"
            analysis += f"- 市场时机的把握能力\n"
            
            return analysis
            
        except Exception as e:
            logger.error(f"路线图分析失败: {e}")
            return f"❌ 路线图分析过程中发生错误: {e}"

    @staticmethod
    @tool
    def get_crypto_community_activity(coin_id: str) -> str:
        """
        获取社区活跃度和社交媒体分析
        
        Args:
            coin_id (str): CoinGecko格式的币种ID
            
        Returns:
            str: 社区活跃度分析结果
        """
        try:
            # 获取项目基础数据
            base_data = Toolkit._get_crypto_project_base_data(coin_id)
            
            if base_data.get('error'):
                return f"❌ 无法获取 {coin_id} 的项目信息: {base_data['error']}"
            
            project_info = base_data['project_info']
            coin_data = base_data['coin_data']
            
            analysis = f"👥 {coin_id.upper()} 社区活跃度分析\n\n"
            
            # 从项目信息中提取社交媒体信息
            if project_info and not (isinstance(project_info, str) and project_info.strip().startswith("❌")):
                analysis += f"📱 社交媒体渠道:\n"
                
                social_keywords = ['twitter', 'telegram', 'discord', 'reddit', 'youtube', 'medium', 'github']
                social_info = []
                
                if isinstance(project_info, str):
                    lines = project_info.split('\n')
                    for line in lines:
                        if any(keyword.lower() in line.lower() for keyword in social_keywords):
                            social_info.append(line.strip())
                    
                    if social_info:
                        for info in social_info[:8]:  # 最多显示8条
                            analysis += f"- {info}\n"
                    else:
                        analysis += f"- 未在项目信息中找到社交媒体链接\n"
            
            # 使用已获取的结构化数据中的社区信息（避免重复请求）
            if isinstance(coin_data, dict):
                community_data = coin_data.get('community_data', {})
                if community_data:
                    analysis += f"\n📊 社区数据统计:\n"
                    for key, value in community_data.items():
                        if value and value != 0:
                            analysis += f"- {key.replace('_', ' ').title()}: {value:,}\n"
            
            # 添加社区分析框架
            analysis += f"\n📈 社区活跃度评估框架:\n"
            analysis += f"1. 社交媒体指标:\n"
            analysis += f"   - 关注者数量和增长趋势\n"
            analysis += f"   - 内容发布频率和质量\n"
            analysis += f"   - 用户互动和参与度\n"
            analysis += f"   - 社区讨论热度\n"
            
            analysis += f"\n2. 开发者社区:\n"
            analysis += f"   - GitHub星标和Fork数量\n"
            analysis += f"   - 代码提交频率\n"
            analysis += f"   - 贡献者数量和多样性\n"
            analysis += f"   - 文档完整性和更新频率\n"
            
            analysis += f"\n3. 用户社区:\n"
            analysis += f"   - 论坛和聊天群活跃度\n"
            analysis += f"   - 用户反馈和问题解决\n"
            analysis += f"   - 社区治理参与度\n"
            analysis += f"   - 线下活动和会议参与\n"
            
            analysis += f"\n💡 关键评估指标:\n"
            analysis += f"- 社区增长速度和健康度\n"
            analysis += f"- 用户粘性和忠诚度\n"
            analysis += f"- 开发者生态的繁荣程度\n"
            analysis += f"- 社区治理的有效性\n"
            
            return analysis
            
        except Exception as e:
            logger.error(f"社区活跃度分析失败: {e}")
            return f"❌ 社区活跃度分析过程中发生错误: {e}"

    @staticmethod
    @tool
    def get_crypto_comprehensive_analysis(coin_id: str) -> str:
        """
        获取加密货币项目的综合分析报告（整合所有分析工具）
        
        Args:
            coin_id (str): CoinGecko格式的币种ID
            
        Returns:
            str: 包含白皮书、团队、Tokenomics、路线图、社区等全面分析的综合报告
        """
        try:
            analysis_sections = []
            
            # 1. 白皮书分析（主要信息源）
            analysis_sections.append("## 📄 白皮书与核心信息")
            whitepaper_analysis = Toolkit.get_crypto_whitepaper_analysis.invoke({"coin_id": coin_id})
            analysis_sections.append(whitepaper_analysis)
            
            # 2. 团队治理分析
            analysis_sections.append("\n## 👥 团队与治理")
            team_analysis = Toolkit.get_crypto_team_governance.invoke({"coin_id": coin_id})
            analysis_sections.append(team_analysis)
            
            # 3. Tokenomics分析
            analysis_sections.append("\n## 💰 Tokenomics")
            tokenomics_analysis = Toolkit.get_crypto_detailed_tokenomics.invoke({"coin_id": coin_id})
            analysis_sections.append(tokenomics_analysis)
            
            # 4. 路线图分析
            analysis_sections.append("\n## 🗺️ 路线图与开发")
            roadmap_analysis = Toolkit.get_crypto_roadmap_development.invoke({"coin_id": coin_id})
            analysis_sections.append(roadmap_analysis)
            
            # 5. 社区活跃度分析
            analysis_sections.append("\n## 👥 社区活跃度")
            community_analysis = Toolkit.get_crypto_community_activity.invoke({"coin_id": coin_id})
            analysis_sections.append(community_analysis)
            
            # 6. 综合分析总结
            analysis_sections.append(f"\n## 🎯 综合分析总结")
            analysis_sections.append(f"""
**项目**: {coin_id.upper()}
**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### 分析框架
本报告基于以下五个维度的深度分析：
1. **白皮书与核心信息** - 技术架构、共识机制、核心概念
2. **团队与治理** - 团队背景、治理结构、决策机制
3. **Tokenomics** - 代币经济模型、分配机制、价值捕获
4. **路线图与开发** - 技术路线图、开发进展、里程碑
5. **社区活跃度** - 社区规模、参与度、治理参与

### 投资建议框架
- **技术评估**: 基于白皮书和路线图分析
- **团队评估**: 基于团队背景和治理结构分析
- **经济评估**: 基于Tokenomics和代币分配分析
- **社区评估**: 基于社区活跃度和参与度分析
- **风险评估**: 综合以上四个维度的风险因素

### 下一步行动
1. 深入阅读白皮书PDF文档
2. 关注GitHub仓库的开发进展
3. 跟踪社区讨论和治理投票
4. 监控市场表现和技术指标
""")
            
            # 组合所有分析
            comprehensive_analysis = f"# {coin_id.upper()} 加密货币项目综合分析报告\n\n" + "\n".join(analysis_sections)
            
            return comprehensive_analysis
            
        except Exception as e:
            logger.error(f"综合分析失败: {e}")
            return f"❌ 综合分析过程中发生错误: {e}"
