from __future__ import annotations

import json
import logging

from langchain.agents import create_agent

from app.agents.handlers import ToolEventMiddleware
from app.graphs.workflow import describe_langgraph_workflow
from app.models.schemas import AgentEvent, AgentRunRequest
from app.prompts.templates import STOCK_AGENT_SYSTEM_PROMPT
from app.services.llm_factory import create_chat_model
from app.tools.stock_tools import (
    calculate_risk_metrics,
    analyze_sentiment,
    get_company_news,
    get_company_profile,
    get_fundamentals,
    get_stock_price_data,
)
from app.utils.events import SendEvent, emit

logger = logging.getLogger(__name__)

STOCK_TOOLS = [
    get_stock_price_data,
    get_company_profile,
    get_fundamentals,
    get_company_news,
    analyze_sentiment,
    calculate_risk_metrics,
]

STOCK_STEP_MAP = {
    "get_stock_price_data": ("technical", "Technical Analysis Agent"),
    "get_company_profile": ("collector", "Data Collector Agent"),
    "get_fundamentals": ("collector", "Data Collector Agent"),
    "get_company_news": ("collector", "Data Collector Agent"),
    "analyze_sentiment": ("sentiment", "Sentiment Analysis Agent"),
    "calculate_risk_metrics": ("risk", "Risk Assessment Agent"),
}


def _extract_stock_result(tool_history: list[dict], symbol: str, exchange: str, name: str, report_text: str) -> dict:
    """Reconstruct the structured stock data dict from tool call results."""
    result = {
        "stockName": name,
        "symbol": symbol,
        "exchange": exchange,
        "currentPrice": None,
        "change": None,
        "sma20": None,
        "sma50": None,
        "volume": None,
        "marketCap": None,
        "trailingPE": None,
        "sector": None,
        "sentiment": None,
        "risk": None,
        "recommendation": None,
        "confidence": None,
        "chartData": [],
        "report": report_text,
    }

    for entry in tool_history:
        raw = entry.get("result", "")
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(parsed, dict):
            continue
        if parsed.get("available") is False:
            continue

        tool_name = entry.get("tool", "")

        if tool_name == "get_stock_price_data":
            result["currentPrice"] = parsed.get("currentPrice")
            result["change"] = parsed.get("change")
            result["sma20"] = parsed.get("sma20")
            result["sma50"] = parsed.get("sma50")
            result["volume"] = parsed.get("volume")
            result["chartData"] = parsed.get("chartData", [])

        elif tool_name == "get_company_profile":
            result["marketCap"] = parsed.get("marketCap")
            result["trailingPE"] = parsed.get("trailingPE")
            result["sector"] = parsed.get("sector")

        elif tool_name == "analyze_sentiment":
            result["sentiment"] = parsed.get("sentiment_label")

        elif tool_name == "calculate_risk_metrics":
            result["risk"] = parsed.get("volatility_label")

    logger.info("Extracted stock result: price=%s change=%s sma20=%s sma50=%s vol=%s mcap=%s",
                result["currentPrice"], result["change"], result["sma20"],
                result["sma50"], result["volume"], result["marketCap"])
                
    import math
    def _sanitize_nan(val):
        if isinstance(val, float) and math.isnan(val):
            return None
        if isinstance(val, dict):
            return {k: _sanitize_nan(v) for k, v in val.items()}
        if isinstance(val, list):
            return [_sanitize_nan(v) for v in val]
        return val
        
    return _sanitize_nan(result)


async def run_stock_agent(request: AgentRunRequest, send: SendEvent) -> dict:
    payload = request.input
    symbol = payload.get("symbol", "")
    exchange = payload.get("exchange", "NSE")
    name = payload.get("name", symbol)

    workflow = describe_langgraph_workflow([t.name for t in STOCK_TOOLS])
    await send(AgentEvent(
        type="run_started",
        message=f"Stock analysis started for {symbol} on {exchange}.",
        progress=2,
        payload={"workflow": workflow, "tools": [t.name for t in STOCK_TOOLS]},
    ))

    llm = create_chat_model(request.credentials)
    middleware = ToolEventMiddleware(send, "stock_analyst", "Stock Analysis Agent", tool_step_map=STOCK_STEP_MAP)

    agent = create_agent(
        model=llm,
        tools=STOCK_TOOLS,
        system_prompt=STOCK_AGENT_SYSTEM_PROMPT,
        middleware=[middleware],
        name="stock_analyst",
    )

    user_query = (
        f"Research and analyze the stock: {name} (symbol: {symbol}, exchange: {exchange}).\n\n"
        f"Call the tools in a logical order: start with price data, then profile, "
        f"then fundamentals, then news, then sentiment, then risk. "
        f"Only after you have all the data, produce the final report.\n\n"
        f"If any tool returns unavailable data, report the error clearly and stop."
    )

    await emit(send, "agent_running", "Agent starting tool-based research...", 5,
               agent_id="stock_analyst", agent_name="Stock Analysis Agent", status="running",
               payload={"tools": [t.name for t in STOCK_TOOLS]})

    try:
        raw_result = await agent.ainvoke({"messages": [("human", user_query)]})
        messages = raw_result.get("messages", [])
        output_text = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content and hasattr(msg, "type") and msg.type == "ai":
                output_text = msg.content
                break

        # Emit running status for Investment Insight Agent
        await emit(send, "agent_started", "Generating investment insights...", 80,
                   agent_id="insight", agent_name="Investment Insight Agent", status="running")
    except Exception as exc:
        logger.error("Stock agent execution failed: %s", exc, exc_info=True)
        report_data = _extract_stock_result(middleware.tool_history, symbol, exchange, name, "")
        report_data["error"] = str(exc)
        report_data["report"] = f"## Stock Analysis Failed\n\n**Error:** {exc}\n\nTool-based analysis could not complete."
        await send(AgentEvent(
            type="agent_failed",
            message=f"[Error] {exc}",
            progress=100,
            agent_id="stock_analyst",
            agent_name="Stock Analysis Agent",
            status="failed",
            payload={"result": report_data, "toolCalls": middleware.tool_history},
        ))
        return report_data

    report_data = _extract_stock_result(middleware.tool_history, symbol, exchange, name, output_text)
    report_data["toolCalls"] = middleware.tool_history

    logger.info("Final stock result payload: currentPrice=%s change=%s sma20=%s sma50=%s volume=%s marketCap=%s chartData=%d points",
                report_data["currentPrice"], report_data["change"], report_data["sma20"],
                report_data["sma50"], report_data["volume"], report_data["marketCap"],
                len(report_data["chartData"]))

    # Emit completed status for Investment Insight Agent
    await emit(send, "agent_completed", "Investment report generated.", 95,
               agent_id="insight", agent_name="Investment Insight Agent", status="completed")

    await send(AgentEvent(
        type="final",
        message="Investment report generated from real tool data.",
        progress=100,
        payload={"result": report_data, "toolCalls": middleware.tool_history},
    ))

    return report_data
