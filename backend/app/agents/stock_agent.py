import json
import logging
import math
import operator
from typing import Annotated, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph

from app.agents.stock_report_builder import (
    build_equity_report,
    build_company_overview_with_llm,
    build_narrative_with_llm,
    build_recommendation_reasoning_with_llm,
    extract_company_overview,
    extract_news_items,
)
from app.models.schemas import AgentEvent, AgentRunRequest, EquityReport
from app.services.llm_factory import create_chat_model
from app.tools.search_tools import get_search_sources_used, perform_search
from app.tools.stock_tools import (
    calculate_fundamentals,
    calculate_risk,
    calculate_valuation,
    get_analyst_ratings,
    get_comprehensive_analysis,
    get_market_metrics,
)
from app.utils.events import SendEvent, emit

logger = logging.getLogger(__name__)


class EquityResearchState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    symbol: str
    exchange: str
    company_name: str
    company_report: str
    company_search_raw: str
    news_report: str
    news_search_raw: str
    news_headlines: list
    news_items: list
    market_data: dict
    fundamental_data: dict
    valuation_data: dict
    risk_data: dict
    analyst_data: dict
    quantitative_data: dict
    final_report: str
    structured_data: Optional[EquityReport]
    ticker_resolved: bool
    error_message: Optional[str]


async def run_stock_agent(request: AgentRunRequest, send: SendEvent) -> dict:
    payload = request.input
    symbol = payload.get("symbol", "").upper().strip()
    exchange = payload.get("exchange", "NSE")
    name = payload.get("name", symbol)

    llm = create_chat_model(request.credentials, streaming=False)

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

        if state["symbol"]:
            await _emit_agent_end("ticker", "Ticker Resolution Agent", 8, success=True)
            return {
                "symbol": state["symbol"].upper(),
                "exchange": state["exchange"].upper(),
                "ticker_resolved": True,
                "error_message": None,
            }

        query_name = state["company_name"]
        search_res = perform_search(f"{query_name} stock ticker symbol {state['exchange']}")
        await _emit_agent_end("ticker", "Ticker Resolution Agent", 8, success=bool(search_res))
        return {
            "symbol": state["symbol"] or query_name[:10].upper(),
            "exchange": state["exchange"],
            "ticker_resolved": bool(state["symbol"] or query_name),
            "error_message": None if query_name else "Could not resolve ticker.",
        }

    async def company_node(state: EquityResearchState):
        if not state.get("ticker_resolved"):
            return {}
        await _emit_agent_start("company", "Company Intelligence Agent", 10)
        try:
            search_raw = perform_search(
                f'"{state["company_name"]}" {state["symbol"]} stock company business profile what does the company do'
            )
            overview = extract_company_overview(
                search_raw,
                state["company_name"],
                state["symbol"],
                state.get("market_data") or {},
            )
            await _emit_agent_end("company", "Company Intelligence Agent", 15)
            return {"company_report": overview, "company_search_raw": search_raw}
        except Exception as e:
            logger.error("Company node failed: %s", e)
            await _emit_agent_end("company", "Company Intelligence Agent", 15, success=False)
            return {"company_report": "Data Not Available", "company_search_raw": ""}

    async def news_node(state: EquityResearchState):
        if not state.get("ticker_resolved"):
            return {}
        await _emit_agent_start("news", "News Research Agent", 20)
        try:
            search_raw = perform_search(
                f'"{state["company_name"]}" {state["symbol"]} stock latest news earnings',
                search_type="news",
            )
            news_items = extract_news_items(search_raw, state["company_name"], state["symbol"])
            headlines = [n.title for n in news_items]
            summary = "\n".join(f"- {h}" for h in headlines[:5]) if headlines else "No recent news found."
            await _emit_agent_end("news", "News Research Agent", 30)
            return {
                "news_report": summary,
                "news_search_raw": search_raw,
                "news_headlines": headlines,
                "news_items": [n.model_dump() for n in news_items],
            }
        except Exception as e:
            logger.error("News node failed: %s", e)
            await _emit_agent_end("news", "News Research Agent", 30, success=False)
            return {"news_report": "Data Not Available", "news_search_raw": "", "news_headlines": [], "news_items": []}

    async def market_node(state: EquityResearchState):
        if not state.get("ticker_resolved"):
            return {}
        await _emit_agent_start("market", "Market Data Agent", 35)
        try:
            data = get_market_metrics.invoke({"symbol": state["symbol"], "exchange": state["exchange"]})
            await _emit_agent_end("market", "Market Data Agent", 45)
            return {"market_data": data}
        except Exception as e:
            logger.error("Market node failed: %s", e)
            await _emit_agent_end("market", "Market Data Agent", 45, success=False)
            return {"market_data": {}}

    async def fundamental_node(state: EquityResearchState):
        if not state.get("ticker_resolved"):
            return {}
        await _emit_agent_start("fundamental", "Fundamental Analysis Agent", 50)
        try:
            data = calculate_fundamentals.invoke({"symbol": state["symbol"], "exchange": state["exchange"]})
            await _emit_agent_end("fundamental", "Fundamental Analysis Agent", 55)
            return {"fundamental_data": data}
        except Exception as e:
            logger.error("Fundamental node failed: %s", e)
            await _emit_agent_end("fundamental", "Fundamental Analysis Agent", 55, success=False)
            return {"fundamental_data": {}}

    async def valuation_node(state: EquityResearchState):
        if not state.get("ticker_resolved"):
            return {}
        await _emit_agent_start("valuation", "Valuation Agent", 60)
        try:
            data = calculate_valuation.invoke({"symbol": state["symbol"], "exchange": state["exchange"]})
            await _emit_agent_end("valuation", "Valuation Agent", 65)
            return {"valuation_data": data}
        except Exception as e:
            logger.error("Valuation node failed: %s", e)
            await _emit_agent_end("valuation", "Valuation Agent", 65, success=False)
            return {"valuation_data": {}}

    async def risk_node(state: EquityResearchState):
        if not state.get("ticker_resolved"):
            return {}
        await _emit_agent_start("risk", "Risk Analysis Agent", 70)
        try:
            data = calculate_risk.invoke({"symbol": state["symbol"], "exchange": state["exchange"]})
            await _emit_agent_end("risk", "Risk Analysis Agent", 75)
            return {"risk_data": data}
        except Exception as e:
            logger.error("Risk node failed: %s", e)
            await _emit_agent_end("risk", "Risk Analysis Agent", 75, success=False)
            return {"risk_data": {}}

    async def analyst_node(state: EquityResearchState):
        if not state.get("ticker_resolved"):
            return {}
        await _emit_agent_start("analyst", "Analyst Consensus Agent", 80)
        try:
            data = get_analyst_ratings.invoke({"symbol": state["symbol"], "exchange": state["exchange"]})
            await _emit_agent_end("analyst", "Analyst Consensus Agent", 85)
            return {"analyst_data": data}
        except Exception as e:
            logger.error("Analyst node failed: %s", e)
            await _emit_agent_end("analyst", "Analyst Consensus Agent", 85, success=False)
            return {"analyst_data": {}}

    async def quantitative_node(state: EquityResearchState):
        if not state.get("ticker_resolved"):
            return {}
        await _emit_agent_start("quantitative", "Quantitative Analysis Agent", 86)
        try:
            data = get_comprehensive_analysis.invoke({"symbol": state["symbol"], "exchange": state["exchange"]})
            search_sources = get_search_sources_used()
            existing = data.get("dataSources") or []
            for s in search_sources:
                if s not in existing:
                    existing.append(s)
            market_src = (state.get("market_data") or {}).get("Source")
            if market_src and market_src not in existing:
                existing.append(market_src)
            data["dataSources"] = existing
            await _emit_agent_end("quantitative", "Quantitative Analysis Agent", 90)
            return {"quantitative_data": data}
        except Exception as e:
            logger.error("Quantitative node failed: %s", e)
            await _emit_agent_end("quantitative", "Quantitative Analysis Agent", 90, success=False)
            return {"quantitative_data": {}}

    async def decision_node(state: EquityResearchState):
        await _emit_agent_start("decision", "Investment Decision Agent", 92)

        result = build_equity_report(state)

        try:
            enhanced_rec = await build_recommendation_reasoning_with_llm(llm, state, result)
            clean_overview = await build_company_overview_with_llm(llm, state, result.companyOverview)
            enhanced_report = await build_narrative_with_llm(llm, state, result)
            result = result.model_copy(update={
                "recommendation": enhanced_rec,
                "companyOverview": clean_overview,
                "report": enhanced_report,
            })
        except Exception as e:
            logger.warning("LLM enhancement skipped: %s", e)

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
    graph.add_node("quantitative_node", quantitative_node)
    graph.add_node("decision_node", decision_node)

    graph.set_entry_point("ticker_resolution")
    graph.add_edge("ticker_resolution", "company_node")
    graph.add_edge("company_node", "news_node")
    graph.add_edge("news_node", "market_node")
    graph.add_edge("market_node", "fundamental_node")
    graph.add_edge("fundamental_node", "valuation_node")
    graph.add_edge("valuation_node", "risk_node")
    graph.add_edge("risk_node", "analyst_node")
    graph.add_edge("analyst_node", "quantitative_node")
    graph.add_edge("quantitative_node", "decision_node")
    graph.add_edge("decision_node", END)

    app = graph.compile()

    nodes_list = [
        "Ticker Resolution Agent", "Company Intelligence Agent", "News Research Agent",
        "Market Data Agent", "Fundamental Analysis Agent", "Valuation Agent",
        "Risk Analysis Agent", "Analyst Consensus Agent", "Quantitative Analysis Agent",
        "Investment Decision Agent",
    ]

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
            "company_search_raw": "",
            "news_report": "",
            "news_search_raw": "",
            "news_headlines": [],
            "news_items": [],
            "market_data": {},
            "fundamental_data": {},
            "valuation_data": {},
            "risk_data": {},
            "analyst_data": {},
            "quantitative_data": {},
            "final_report": "",
            "structured_data": None,
            "ticker_resolved": False,
            "error_message": None,
        })

        if not final_state.get("ticker_resolved"):
            error_msg = final_state.get("error_message") or "Ticker not found."
            await send(AgentEvent(type="run_failed", message=error_msg, progress=100, status="failed"))
            return {"error": error_msg}

        structured_data = final_state.get("structured_data")
        if structured_data and isinstance(structured_data, EquityReport):
            report_data = structured_data.model_dump()
        else:
            report_data = build_equity_report(final_state).model_dump()

        def clean_floats(obj):
            if isinstance(obj, dict):
                return {k: clean_floats(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [clean_floats(v) for v in obj]
            if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                return None
            return obj

        report_data = clean_floats(report_data)
        logger.info("FINAL RESPONSE: recommendation=%s confidence=%s completeness=%s",
                    report_data.get("recommendation", {}).get("recommendation"),
                    report_data.get("recommendation", {}).get("confidence"),
                    report_data.get("dataCompleteness"))

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
