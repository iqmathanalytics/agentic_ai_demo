import json
import logging
import operator
from typing import Annotated, Sequence, TypedDict, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from app.models.schemas import AgentEvent, AgentRunRequest, EquityReport
from app.services.llm_factory import create_chat_model
from app.utils.events import SendEvent, emit

from app.tools.stock_tools import (
    resolve_ticker,
    search_company_profile,
    search_latest_news,
    get_market_metrics,
    calculate_fundamentals,
    calculate_valuation,
    calculate_risk,
    get_analyst_ratings
)

logger = logging.getLogger(__name__)

class TickerInfo(BaseModel):
    symbol: str = Field(description="Stock ticker symbol")
    exchange: str = Field(description="Primary stock exchange")
    found: bool = Field(description="Whether the ticker was successfully resolved")

class EquityResearchState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    symbol: str
    exchange: str
    company_name: str

    # LLM-generated summaries
    company_report: str
    news_report: str

    # Structured tool data (deterministic)
    market_data: dict
    fundamental_data: dict
    valuation_data: dict
    risk_data: dict
    analyst_data: dict

    # Final output
    final_report: str
    structured_data: Optional[EquityReport]

    # Resilience flags
    ticker_resolved: bool
    error_message: Optional[str]

async def run_stock_agent(request: AgentRunRequest, send: SendEvent) -> dict:
    payload = request.input
    symbol = payload.get("symbol", "").upper().strip()
    exchange = payload.get("exchange", "NSE")
    name = payload.get("name", symbol)

    llm = create_chat_model(request.credentials)

    async def _emit_agent_start(agent_id, agent_name, progress):
        await emit(send, "agent_started", f"Starting {agent_name}...", progress,
                   agent_id=agent_id, agent_name=agent_name, status="running")

    async def _emit_agent_end(agent_id, agent_name, progress, success=True):
        status = "completed" if success else "failed"
        msg = f"{agent_name} complete." if success else f"{agent_name} failed."
        await emit(send, "agent_completed", msg, progress,
                   agent_id=agent_id, agent_name=agent_name, status=status)

    async def ticker_resolution_node(state: EquityResearchState):
        await _emit_agent_start("ticker", "Ticker Resolution Agent", 5)

        prompt = f"""You are a Ticker Resolution Agent.
Find the correct stock ticker symbol and exchange for '{state['company_name']}' or verify '{state['symbol']}'.
Primary Exchange requested: {state['exchange']}.
Use the resolve_ticker tool."""
        bound_llm = llm.bind_tools([resolve_ticker])
        try:
            msg = await bound_llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content="Resolve ticker.")])
            found_symbol = state['symbol']
            found_exchange = state['exchange']
            found = False

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    res = resolve_ticker.invoke(tc["args"])
                    extraction_prompt = f"Extract the stock ticker and exchange from these search results for {state['company_name']}. Results: {res}"
                    ticker_llm = llm.with_structured_output(TickerInfo)
                    ticker_result = await ticker_llm.ainvoke([SystemMessage(content=extraction_prompt)])
                    found_symbol = ticker_result.symbol.upper()
                    found_exchange = ticker_result.exchange.upper()
                    found = ticker_result.found

            if not found and state['symbol']:
                found = True

            await _emit_agent_end("ticker", "Ticker Resolution Agent", 8, success=found)
            return {
                "symbol": found_symbol,
                "exchange": found_exchange,
                "ticker_resolved": found,
                "error_message": None if found else f"Could not resolve ticker for {state['company_name']}"
            }
        except Exception as e:
            logger.error(f"Ticker resolution failed: {e}")
            await _emit_agent_end("ticker", "Ticker Resolution Agent", 8, success=False)
            return {"ticker_resolved": False, "error_message": str(e)}

    async def company_node(state: EquityResearchState):
        if not state.get("ticker_resolved"): return {}
        await _emit_agent_start("company", "Company Intelligence Agent", 10)
        tool = search_company_profile
        bound_llm = llm.bind_tools([tool])
        prompt = f"You are a Company Intelligence Agent. Use the tool to find information about {state['company_name']} ({state['symbol']}). Write a brief executive summary."
        try:
            msg = await bound_llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content="Start research.")])
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    res = tool.invoke(tc["args"])
                    msg = await llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content=f"Tool result: {res}\n\nWrite the executive summary.")])
            await _emit_agent_end("company", "Company Intelligence Agent", 15)
            return {"company_report": msg.content}
        except Exception as e:
            logger.error(f"Company node failed: {e}")
            await _emit_agent_end("company", "Company Intelligence Agent", 15, success=False)
            return {"company_report": "Data Not Available"}

    async def news_node(state: EquityResearchState):
        if not state.get("ticker_resolved"): return {}
        await _emit_agent_start("news", "News Research Agent", 20)
        tool = search_latest_news
        bound_llm = llm.bind_tools([tool])
        prompt = f"You are a News Research Agent. Use the tool to find latest news about {state['company_name']}. Write a summary of most important developments and state the sentiment (Bullish / Neutral / Bearish)."
        try:
            msg = await bound_llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content="Start news research.")])
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    res = tool.invoke(tc["args"])
                    msg = await llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content=f"Tool result: {res}\n\nWrite the news summary.")])
            await _emit_agent_end("news", "News Research Agent", 30)
            return {"news_report": msg.content}
        except Exception as e:
            logger.error(f"News node failed: {e}")
            await _emit_agent_end("news", "News Research Agent", 30, success=False)
            return {"news_report": "Data Not Available"}

    async def market_node(state: EquityResearchState):
        if not state.get("ticker_resolved"): return {}
        await _emit_agent_start("market", "Market Data Agent", 35)
        try:
            data = get_market_metrics.invoke({"symbol": state["symbol"], "exchange": state["exchange"]})
            await _emit_agent_end("market", "Market Data Agent", 45)
            return {"market_data": data}
        except Exception as e:
            logger.error(f"Market node failed: {e}")
            await _emit_agent_end("market", "Market Data Agent", 45, success=False)
            return {"market_data": {}}

    async def fundamental_node(state: EquityResearchState):
        if not state.get("ticker_resolved"): return {}
        await _emit_agent_start("fundamental", "Fundamental Analysis Agent", 50)
        try:
            data = calculate_fundamentals.invoke({"symbol": state["symbol"], "exchange": state["exchange"]})
            await _emit_agent_end("fundamental", "Fundamental Analysis Agent", 55)
            return {"fundamental_data": data}
        except Exception as e:
            logger.error(f"Fundamental node failed: {e}")
            await _emit_agent_end("fundamental", "Fundamental Analysis Agent", 55, success=False)
            return {"fundamental_data": {}}

    async def valuation_node(state: EquityResearchState):
        if not state.get("ticker_resolved"): return {}
        await _emit_agent_start("valuation", "Valuation Agent", 60)
        try:
            data = calculate_valuation.invoke({"symbol": state["symbol"], "exchange": state["exchange"]})
            await _emit_agent_end("valuation", "Valuation Agent", 65)
            return {"valuation_data": data}
        except Exception as e:
            logger.error(f"Valuation node failed: {e}")
            await _emit_agent_end("valuation", "Valuation Agent", 65, success=False)
            return {"valuation_data": {}}

    async def risk_node(state: EquityResearchState):
        if not state.get("ticker_resolved"): return {}
        await _emit_agent_start("risk", "Risk Analysis Agent", 70)
        try:
            data = calculate_risk.invoke({"symbol": state["symbol"], "exchange": state["exchange"]})
            await _emit_agent_end("risk", "Risk Analysis Agent", 75)
            return {"risk_data": data}
        except Exception as e:
            logger.error(f"Risk node failed: {e}")
            await _emit_agent_end("risk", "Risk Analysis Agent", 75, success=False)
            return {"risk_data": {}}

    async def analyst_node(state: EquityResearchState):
        if not state.get("ticker_resolved"): return {}
        await _emit_agent_start("analyst", "Analyst Consensus Agent", 80)
        try:
            data = get_analyst_ratings.invoke({"symbol": state["symbol"], "exchange": state["exchange"]})
            await _emit_agent_end("analyst", "Analyst Consensus Agent", 85)
            return {"analyst_data": data}
        except Exception as e:
            logger.error(f"Analyst node failed: {e}")
            await _emit_agent_end("analyst", "Analyst Consensus Agent", 85, success=False)
            return {"analyst_data": {}}

    async def decision_node(state: EquityResearchState):
        await _emit_agent_start("decision", "Investment Decision Agent", 90)

        def _fmt(val, default="Data Not Available"):
            if val is None or val == "None":
                return default
            if isinstance(val, dict):
                if not val or "error" in val:
                    return default
                return json.dumps(val, indent=2)
            if isinstance(val, list):
                if not val:
                    return default
                return json.dumps(val, indent=2)
            return str(val)

        comp = _fmt(state.get('company_report'))
        news = _fmt(state.get('news_report'))
        market = state.get('market_data', {}) or {}
        fund = state.get('fundamental_data', {}) or {}
        val = state.get('valuation_data', {}) or {}
        risk = state.get('risk_data', {}) or {}
        analyst = state.get('analyst_data', {}) or {}

        prompt = f"""You are the Investment Decision Agent.
Compile a comprehensive equity research report using the gathered data.

Company Info:
{comp}

News:
{news}

Market Metrics:
{json.dumps(market, indent=2)}

Fundamentals:
{json.dumps(fund, indent=2)}

Valuation:
{json.dumps(val, indent=2)}

Risk Analysis:
{json.dumps(risk, indent=2)}

Analyst Consensus:
{json.dumps(analyst, indent=2)}

Generate a complete structured equity research report with all required fields."""

        try:
            structured_llm = llm.with_structured_output(EquityReport)
            logger.info("=== DECISION NODE: Invoking structured LLM ===")
            logger.info(f"Prompt:\n{prompt}")

            result = await structured_llm.ainvoke([SystemMessage(content=prompt)])

            logger.info("=== DECISION NODE: Structured output received ===")
            logger.info(f"Recommendation: {result.recommendation}")
        except Exception as e:
            logger.error("=== DECISION NODE: Structured output failed ===")
            logger.error(f"Error: {e}", exc_info=True)

            result = EquityReport(
                companyOverview=comp,
                latestNews=[],
                valuation=dict(market),
                fundamentals=dict(fund),
                bullishFactors=[],
                bearishFactors=[],
                riskAnalysis=dict(risk),
                analystRatings=dict(analyst),
                recommendation={
                    "action": "INSUFFICIENT DATA",
                    "confidence": 0,
                    "reasoning": f"Analysis could not be completed. Error: {str(e)}"
                },
                outlook12Month={},
                report=f"# Analysis Incomplete\n\n**Error:** {str(e)}\n\n## Available Data\n\n{comp}\n\n{news}"
            )

        # Ensure Current Price and Market Cap from raw market data are in valuation
        current_price = market.get("Current Price")
        market_cap = market.get("Market Cap")
        if current_price is not None:
            result.valuation["Current Price"] = current_price
        if market_cap is not None:
            result.valuation["Market Cap"] = market_cap

        await _emit_agent_end("decision", "Investment Decision Agent", 98)
        return {"structured_data": result}

    graph = StateGraph(EquityResearchState)
    graph.add_node("ticker_resolution", ticker_resolution_node)
    graph.add_node("company_node", company_node)
    graph.add_node("news_node", news_node)
    graph.add_node("market_node", market_node)
    graph.add_node("fundamental_node", fundamental_node)
    graph.add_node("valuation_node", valuation_node)
    graph.add_node("risk_node", risk_node)
    graph.add_node("analyst_node", analyst_node)
    graph.add_node("decision_node", decision_node)

    graph.set_entry_point("ticker_resolution")
    graph.add_edge("ticker_resolution", "company_node")
    graph.add_edge("company_node", "news_node")
    graph.add_edge("news_node", "market_node")
    graph.add_edge("market_node", "fundamental_node")
    graph.add_edge("fundamental_node", "valuation_node")
    graph.add_edge("valuation_node", "risk_node")
    graph.add_edge("risk_node", "analyst_node")
    graph.add_edge("analyst_node", "decision_node")
    graph.add_edge("decision_node", END)

    app = graph.compile()

    nodes_list = ["Ticker Resolution Agent", "Company Intelligence Agent", "News Research Agent", "Market Data Agent",
                  "Fundamental Analysis Agent", "Valuation Agent", "Risk Analysis Agent",
                  "Analyst Consensus Agent", "Investment Decision Agent"]

    await send(AgentEvent(
        type="run_started",
        message=f"Multi-Agent Equity Research started for {name}.",
        progress=2,
        payload={"workflow": {"engine": "langgraph", "nodes": nodes_list}, "tools": []},
    ))

    try:
        final_state = await app.ainvoke({
            "messages": [],
            "symbol": symbol,
            "exchange": exchange,
            "company_name": name,
            "company_report": "",
            "news_report": "",
            "market_data": {},
            "fundamental_data": {},
            "valuation_data": {},
            "risk_data": {},
            "analyst_data": {},
            "final_report": "",
            "structured_data": None,
            "ticker_resolved": False,
            "error_message": None
        })

        if not final_state.get("ticker_resolved"):
            error_msg = final_state.get("error_message") or "Ticker not found."
            await send(AgentEvent(
                type="run_failed",
                message=error_msg,
                progress=100,
                status="failed"
            ))
            return {"error": error_msg}

        structured_data = final_state.get("structured_data")
        if structured_data and isinstance(structured_data, EquityReport):
            report_data = structured_data.model_dump()
        else:
            report_data = {
                "stockName": name,
                "symbol": final_state.get("symbol", symbol),
                "exchange": final_state.get("exchange", exchange),
                "report": "Report generation failed.",
                "chartData": []
            }

        logger.info("FINAL RESPONSE")
        logger.info(json.dumps(report_data, indent=2))

        await send(AgentEvent(
            type="final",
            message="Multi-Agent Equity Research complete.",
            progress=100,
            payload={"result": report_data, "toolCalls": []},
        ))
        return report_data

    except Exception as exc:
        logger.error("LangGraph execution failed: %s", exc, exc_info=True)
        report_data = {"error": str(exc), "report": f"## Error\n\n{exc}"}
        await send(AgentEvent(
            type="agent_failed",
            message=f"[Error] {exc}",
            progress=100,
            status="failed",
            payload={"result": report_data},
        ))
        return report_data
