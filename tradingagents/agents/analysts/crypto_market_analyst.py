from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 日志
from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")


def create_crypto_market_analyst(llm, toolkit):

    def crypto_market_analyst_node(state):
        logger.debug(f"🪙 [DEBUG] ===== 加密市场分析师节点开始 =====")

        current_date = state["trade_date"]
        ticker = state["company_of_interest"]  # 对于加密，这里通常是符号或CoinGecko ID

        logger.info(f"🪙 [加密市场分析师] 分析目标: {ticker}，日期: {current_date}")

        # 仅使用统一市场数据工具，内部已支持is_crypto分支
        tools = [toolkit.get_stock_market_data_unified]

        system_message = (
            f"""你是一位专业的加密货币市场分析师。你必须对{ticker}进行详细的市场技术分析。

请务必先调用 get_stock_market_data_unified 工具获取真实的市场数据（工具会自动识别是否为加密货币并选择数据源），然后基于返回的真实数据进行分析。

分析要求：
1. 结合价格趋势（高/低、波动率）、成交量变化、短中长期动量进行判断
2. 使用常见技术指标（MA/EMA、MACD、RSI、布林带）进行解释
3. 描述关键支撑/阻力位与潜在突破位
4. 给出短期/中期的交易思路与风险提示
5. 全程使用中文，引用到的价格或市值单位统一为美元（$）

输出格式：
## 📊 资产基本信息
## 📈 技术指标分析
## 📉 价格趋势与区间
## 🔎 成交量与动能
## ⚠️ 风险与注意事项
## 💭 交易思路与建议
"""
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一位专业的加密货币市场分析师，与其他分析师协作。"
                    "使用提供的工具来获取和分析市场数据。"
                    "如果你无法完全回答，没关系；其他分析师会从不同角度继续分析。"
                    "请先调用工具，然后基于工具返回的真实数据给出分析。\n{system_message}\n当前日期是{current_date}，分析对象是{ticker}。",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        # 标准处理：如果有工具调用，按框架执行；否则直接返回模型内容
        if len(result.tool_calls) == 0:
            report = result.content
            logger.info(f"🪙 [加密市场分析师] 直接回复，长度: {len(report)}")
            return {
                "messages": [result],
                "market_report": report,
            }

        # 有工具调用时，执行工具并生成分析
        try:
            from langchain_core.messages import ToolMessage, HumanMessage

            tool_messages = []
            for tool_call in result.tool_calls:
                tool_name = tool_call.get('name')
                tool_args = tool_call.get('args', {})
                tool_id = tool_call.get('id')

                tool_result = None
                for tool in tools:
                    current_tool_name = getattr(tool, 'name', getattr(tool, '__name__', str(tool)))
                    if current_tool_name == tool_name:
                        try:
                            tool_result = tool.invoke(tool_args)
                        except Exception as tool_error:
                            tool_result = f"工具执行失败: {str(tool_error)}"
                        break

                if tool_result is None:
                    tool_result = f"未找到工具: {tool_name}"

                tool_messages.append(
                    ToolMessage(content=str(tool_result), tool_call_id=tool_id)
                )

            # 让模型基于工具结果生成最终报告
            analysis_prompt = (
                "现在请基于上述工具返回的真实市场数据，完成加密货币的技术分析报告。"
                "必须包含具体的指标数值和区间判断，并给出明确的交易建议与风险提示。"
            )

            messages = state["messages"] + [result] + tool_messages + [HumanMessage(content=analysis_prompt)]
            final_result = llm.invoke(messages)
            report = final_result.content

            logger.info(f"🪙 [加密市场分析师] 生成完整分析报告，长度: {len(report)}")
            return {
                "messages": [result] + tool_messages + [final_result],
                "market_report": report,
            }

        except Exception as e:
            logger.error(f"❌ [加密市场分析师] 工具执行或分析生成失败: {e}")
            return {
                "messages": [result],
                "market_report": "加密市场分析失败：工具执行或报告生成失败",
            }

    return crypto_market_analyst_node


