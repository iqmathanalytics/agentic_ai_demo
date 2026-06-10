from __future__ import annotations

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
    middleware = ToolEventMiddleware(send, "stock_analyst", "Stock Analysis Agent")

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
        result = await agent.ainvoke({"messages": [("human", user_query)]})
        messages = result.get("messages", [])
        output_text = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content and hasattr(msg, "type") and msg.type == "ai":
                output_text = msg.content
                break
    except Exception as exc:
        logger.error("Stock agent execution failed: %s", exc, exc_info=True)
        error_result = {
            "stockName": name,
            "symbol": symbol,
            "exchange": exchange,
            "error": str(exc),
            "report": f"## Stock Analysis Failed\n\n**Error:** {exc}\n\nTool-based analysis could not complete.",
            "toolCalls": middleware.tool_history,
        }
        await send(AgentEvent(
            type="agent_failed",
            message=f"[Error] {exc}",
            progress=100,
            agent_id="stock_analyst",
            agent_name="Stock Analysis Agent",
            status="failed",
            payload={"error": str(exc), "toolCalls": middleware.tool_history},
        ))
        return error_result

    report_data = {
        "stockName": name,
        "symbol": symbol,
        "exchange": exchange,
        "report": output_text,
        "toolCalls": middleware.tool_history,
    }

    await send(AgentEvent(
        type="final",
        message="Investment report generated from real tool data.",
        progress=100,
        payload={"result": report_data, "toolCalls": middleware.tool_history},
    ))

    return report_data
