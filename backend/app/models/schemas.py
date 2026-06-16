from typing import Any, List, Literal

from pydantic import BaseModel, Field

Provider = Literal["openai", "gemini", "claude", "openrouter", "groq"]
AgentKind = Literal["stock", "resume", "website_audit"]
EventType = Literal[
    "run_started",
    "agent_started",
    "agent_running",
    "agent_completed",
    "agent_failed",
    "tool_start",
    "tool_end",
    "tool_error",
    "llm_start",
    "llm_end",
    "log",
    "token",
    "metric",
    "final",
    "preview",
    "run_failed",
    "run_completed",
]


class Credentials(BaseModel):
    provider: Provider
    model: str
    api_key: str = Field(min_length=6)


class AgentRunRequest(BaseModel):
    agent: AgentKind
    credentials: Credentials
    input: dict[str, Any]


class AgentEvent(BaseModel):
    type: EventType
    agent_id: str | None = None
    agent_name: str | None = None
    status: str | None = None
    message: str | None = None
    progress: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)


class Recommendation(BaseModel):
    recommendation: str = Field(description="One of: BUY, HOLD, SELL")
    confidence: float = Field(description="Confidence score 0-100")
    reason1: str = Field(description="Primary reason for the recommendation")
    reason2: str = Field(description="Secondary reason for the recommendation")


class EquityReport(BaseModel):
    companyOverview: str = Field(description="Executive summary of business")
    latestNews: List[str] = Field(description="List of most important developments")
    valuation: dict = Field(description="Current Price, Market Cap, PE, Sector Avg PE, etc.")
    fundamentals: dict = Field(description="Revenue Growth, Margins, ROE, Debt/Equity, etc.")
    bullishFactors: List[str] = Field(description="List of positive catalysts")
    bearishFactors: List[str] = Field(description="List of negative risks")
    riskAnalysis: dict = Field(description="Market Risk, Financial Risk, Business Risk scores")
    analystRatings: dict = Field(description="Buy/Hold/Sell counts, Consensus, Target Price")
    recommendation: Recommendation = Field(description="Action (BUY/HOLD/SELL), Confidence (0-100), Two concise reasons")
    outlook12Month: dict = Field(description="Base/Bull/Bear scenarios")
    chartData: list = Field(default_factory=list, description="Time-series price chart data")
    report: str = Field(description="The full detailed markdown report")
    currentPrice: float | None = Field(None, description="Current stock price")
    marketCap: float | None = Field(None, description="Market capitalization")

