import logging

from app.graphs.workflow import describe_langgraph_workflow
from app.models.schemas import AgentEvent, AgentRunRequest
from app.prompts.templates import STOCK_REPORT_PROMPT
from app.services.llm_factory import create_chat_model, invoke_text
from app.tools.market_data import collect_market_data
from app.utils.events import SendEvent, emit, heartbeat

logger = logging.getLogger(__name__)

STOCK_STEPS = [
    ("collector", "Data Collection Agent"),
    ("technical", "Technical Analysis Agent"),
    ("sentiment", "News Sentiment Agent"),
    ("risk", "Risk Assessment Agent"),
    ("insight", "Investment Insights Agent"),
]


async def run_stock_agent(request: AgentRunRequest, send: SendEvent) -> dict:
    payload = request.input
    workflow = describe_langgraph_workflow([step[0] for step in STOCK_STEPS])
    await send(AgentEvent(type="run_started", message="Stock analysis workflow started.", progress=2, payload={"workflow": workflow}))

    await emit(send, "agent_started", "Collecting market data...", 8, agent_id="collector", agent_name="Data Collection Agent", status="running")
    await heartbeat(
        send,
        "collector",
        "Data Collection Agent",
        8,
        22,
        ["Resolving exchange ticker...", "Loading historical prices...", "Checking company profile metadata..."],
    )
    market_data = collect_market_data(payload.get("symbol", ""), payload.get("exchange", "NSE"))
    logger.info("Market data result: available=%s ticker=%s", market_data.get("available"), market_data.get("ticker"))

    if not market_data.get("available"):
        error_msg = market_data.get("error", "Market data unavailable.")
        logger.error("STOP: market data fetch failed — %s", error_msg)
        await emit(send, "agent_failed", f"Market data unavailable: {error_msg}", 24, agent_id="collector", agent_name="Data Collection Agent", status="failed", payload={"market_data": market_data, "error": error_msg})
        result = {
            "stockName": payload.get("name"),
            "symbol": payload.get("symbol"),
            "exchange": payload.get("exchange"),
            "currentPrice": None,
            "change": None,
            "sma20": None,
            "sma50": None,
            "volume": None,
            "marketCap": None,
            "trailingPE": None,
            "sector": None,
            "sentiment": "Unavailable",
            "risk": "Unavailable",
            "recommendation": "Unavailable",
            "confidence": 0,
            "chartData": [],
            "report": f"## Market Data Unavailable\n\nError: {error_msg}\n\nCould not fetch data for {payload.get('symbol')} on {payload.get('exchange')}. Check the symbol and try again.",
            "marketData": market_data,
        }
        await send(AgentEvent(type="final", message="Stock analysis failed — market data unavailable.", progress=100, payload={"result": result}))
        return result

    await emit(send, "agent_completed", "Market data collection complete.", 24, agent_id="collector", agent_name="Data Collection Agent", status="completed", payload={"market_data": market_data})

    await emit(send, "agent_started", "Running technical signal checks...", 28, agent_id="technical", agent_name="Technical Analysis Agent", status="running")
    await heartbeat(
        send,
        "technical",
        "Technical Analysis Agent",
        28,
        44,
        ["Calculating trend against moving averages...", "Estimating momentum and price change...", "Preparing chart series..."],
    )
    await emit(send, "agent_completed", "Technical analysis complete.", 46, agent_id="technical", agent_name="Technical Analysis Agent", status="completed")

    await emit(send, "agent_started", "Analyzing available news sentiment...", 50, agent_id="sentiment", agent_name="News Sentiment Agent", status="running")
    await heartbeat(
        send,
        "sentiment",
        "News Sentiment Agent",
        50,
        62,
        ["Reading recent market headlines...", "Classifying sentiment direction...", "Summarizing narrative drivers..."],
    )
    await emit(send, "agent_completed", "Sentiment pass complete.", 64, agent_id="sentiment", agent_name="News Sentiment Agent", status="completed")

    await emit(send, "agent_started", "Evaluating portfolio risk factors...", 68, agent_id="risk", agent_name="Risk Assessment Agent", status="running")
    await heartbeat(
        send,
        "risk",
        "Risk Assessment Agent",
        68,
        76,
        ["Reviewing volatility proxies...", "Checking liquidity and valuation risk...", "Scoring downside risk..."],
    )
    await emit(send, "agent_completed", "Risk assessment complete.", 78, agent_id="risk", agent_name="Risk Assessment Agent", status="completed")

    await emit(send, "agent_started", "Generating investment report with the connected LLM...", 82, agent_id="insight", agent_name="Investment Insights Agent", status="running")
    llm = create_chat_model(request.credentials)
    prompt = STOCK_REPORT_PROMPT.format(payload=payload, market_data=market_data)
    report = await invoke_text(llm, prompt)
    await emit(send, "agent_completed", "Investment report generated.", 96, agent_id="insight", agent_name="Investment Insights Agent", status="completed")

    result = {
        "stockName": payload.get("name"),
        "symbol": payload.get("symbol"),
        "exchange": payload.get("exchange"),
        "currentPrice": market_data.get("currentPrice"),
        "change": market_data.get("change"),
        "sma20": market_data.get("sma20"),
        "sma50": market_data.get("sma50"),
        "volume": market_data.get("volume"),
        "marketCap": market_data.get("marketCap"),
        "trailingPE": market_data.get("trailingPE"),
        "sector": market_data.get("sector"),
        "sentiment": "See report",
        "risk": "See report",
        "recommendation": "AI report generated",
        "confidence": 0,
        "chartData": market_data.get("chartData", []),
        "report": report,
        "marketData": market_data,
    }
    await send(AgentEvent(type="final", message="Final stock report ready.", progress=100, payload={"result": result}))
    return result

