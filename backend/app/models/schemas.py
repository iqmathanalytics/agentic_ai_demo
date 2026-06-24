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
    # Website audits do not require an LLM API key. Keep this optional at the schema level
    # and enforce it only when an LLM is actually invoked.
    api_key: str = ""


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
    summary: str = Field(default="", description="One-line plain-English summary")
    reasoning: List[str] = Field(default_factory=list, description="Simple reasoning bullet points")


class NewsItem(BaseModel):
    title: str = ""
    snippet: str = ""
    url: str = ""
    source: str = ""
    date: str = ""


class EquityReport(BaseModel):
    stockName: str = Field(default="", description="Company display name")
    symbol: str = Field(default="", description="Stock ticker symbol")
    exchange: str = Field(default="", description="Stock exchange")
    companyOverview: str = Field(description="Executive summary of business")
    latestNews: List[str] = Field(description="List of most important developments")
    newsItems: List[NewsItem] = Field(default_factory=list, description="Structured news articles")
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
    displayCurrency: str = Field(default="MYR", description="Currency used for all displayed money values")
    sourceCurrency: str = Field(default="", description="Original market data currency")
    fxRateToDisplayCurrency: float | None = Field(None, description="FX rate used to convert source currency to display currency")
    dataSources: List[str] = Field(default_factory=list, description="Data providers used in analysis")
    dataCompleteness: int = Field(default=0, description="Percentage of expected data fields populated")

