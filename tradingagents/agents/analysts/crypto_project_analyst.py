#!/usr/bin/env python3
"""
CryptoProjectAnalyst 加密项目分析师
- 负责基于项目元数据（Tokenomics/白皮书/团队/路线图等）生成项目层分析报告
- 面向加密货币场景，用于替代股票场景中的 Fundamentals Analyst
"""

from typing import Dict

from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")


def _symbol_to_coingecko_id(symbol: str) -> str:
    """将常见加密货币交易符号映射为 CoinGecko ID（最小可用集）。"""
    if not symbol:
        return symbol
    s = str(symbol).strip().lower()
    mapping = {
        "btc": "bitcoin",
        "eth": "ethereum",
        "ada": "cardano",
        "sol": "solana",
        "dot": "polkadot",
        "xrp": "ripple",
        "ltc": "litecoin",
        "bch": "bitcoin-cash",
        "doge": "dogecoin",
        "matic": "matic-network",
        "atom": "cosmos",
        "avax": "avalanche-2",
        "near": "near",
    }
    return mapping.get(s, s)


def create_crypto_project_analyst(llm):
    """创建加密项目分析师智能体。

    说明：此分析师直接从数据流管理器获取项目信息，不依赖工具调用，
    以保证在无工具环境下也可工作。输出写入 fundamentals_report，
    以与既有下游流程保持兼容。
    """

    def crypto_project_analyst_node(state: Dict) -> Dict:
        logger.debug("🪙 [DEBUG] ===== 加密项目分析师节点开始 =====")

        ticker = state.get("company_of_interest", "").strip()
        trade_date = state.get("trade_date", "")

        try:
            # 检测是否为加密货币
            from tradingagents.utils.stock_utils import StockUtils
            market_info = StockUtils.get_market_info(ticker)
            if not market_info.get("is_crypto", False):
                logger.info("🪙 [加密项目分析师] 目标非加密资产，跳过")
                return state

            # 获取项目元数据（通过统一加密数据源管理器）
            from tradingagents.dataflows.crypto_data_source_manager import (
                get_crypto_data_unified,
            )

            coin_id = _symbol_to_coingecko_id(ticker)
            logger.info(f"🪙 [加密项目分析师] 获取项目元数据: symbol={ticker}, id={coin_id}")

            # data_type='info' 表示拉取项目信息/元数据；days 对 info 无实际意义，传 0 占位
            project_info = get_crypto_data_unified(coin_id, "usd", 0, "info")

            if not project_info or isinstance(project_info, str) and project_info.strip().startswith("❌"):
                # 兜底：如果 info 拉取失败，输出最小提示，避免中断流程
                logger.warning("🪙 [加密项目分析师] 未获取到有效项目信息，返回占位分析")
                fallback_report = (
                    f"## 加密项目分析（{ticker}）\n\n"
                    f"- 日期: {trade_date}\n"
                    f"- 提示: 未能获取到完整的项目信息（可能是免费额度或ID映射问题）\n"
                    f"- 建议: 稍后重试，或在设置中填写更高权限的API Key\n"
                )
                new_state = dict(state)
                new_state["fundamentals_report"] = fallback_report
                return new_state

            # 交给 LLM 进行结构化的项目层分析
            system_prompt = (
                "你是一位专业的加密货币项目研究分析师。请基于提供的项目元数据，"
                "撰写结构化、可执行的分析报告，内容需覆盖：\n"
                "1) 项目概览（愿景/价值主张/生态定位）\n"
                "2) Tokenomics（供应、分配、释放、通胀/通缩机制、用途）\n"
                "3) 团队与社区（核心成员、治理结构、社区活跃度）\n"
                "4) 路线图与进展（里程碑、开发活跃度、代码仓库动态可简述）\n"
                "5) 竞争格局与差异化（同类项目对比）\n"
                "6) 合规与风险（政策、技术、资金、托管流动性等）\n"
                "7) 投资要点与结论（适合的持仓逻辑/时段、关键观察指标）\n\n"
                "要求：\n- 使用中文撰写；\n- 结合元数据中的事实给出具体要点；\n- 结尾提供3-5条可操作建议；\n- 严禁编造未在数据中体现的具体数值。"
            )

            messages = [
                ("system", system_prompt),
                ("human", f"分析对象: {ticker}\n\n项目元数据如下（原始文本）：\n\n{project_info}"),
            ]

            logger.info("🪙 [加密项目分析师] 调用LLM生成项目层分析报告…")
            result = llm.invoke(messages)
            content = getattr(result, "content", "") or (result if isinstance(result, str) else "")

            if not content:
                content = "⚠️ 模型未返回内容，请稍后重试或检查LLM配置。"

            new_state = dict(state)
            new_state["fundamentals_report"] = content
            logger.info(f"🪙 [加密项目分析师] 生成项目报告，长度: {len(content)}")
            return new_state

        except Exception as e:
            logger.error(f"❌ [加密项目分析师] 执行失败: {e}")
            return state

    return crypto_project_analyst_node


