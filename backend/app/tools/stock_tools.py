import logging
from statistics import mean
import os

from langchain_core.tools import tool
from .search_tools import perform_search
from .quantitative_tools import (
    calculate_fundamental_score as _calc_score,
    revenue_analysis as _rev_analysis,
    calculate_fair_value as _calc_fv,
    generate_bullish_factors as _gen_bull,
    generate_bearish_factors as _gen_bear,
    investment_recommendation as _inv_rec,
    get_analyst_consensus as _analyst_consensus,
    discover_peers as _discover_peers,
    build_analysis_context as _build_context,
)

logger = logging.getLogger(__name__)

def _map_ticker(symbol: str, exchange: str) -> str:
    s = symbol.upper().strip()
    e = exchange.upper().strip()
    if e == "NSE" and not s.endswith(".NS"):
        return f"{s}.NS"
    if e == "BSE" and not s.endswith(".BO"):
        return f"{s}.BO"
    return s

@tool
def resolve_ticker(company_name: str) -> str:
    """Resolves a company name to its primary stock ticker symbol.
    Returns a JSON string with the ticker and exchange, or an error.
    """
    logger.info(f"Resolving ticker for {company_name}")
    query = f"{company_name} stock ticker symbol primary exchange"
    search_res = perform_search(query)
    
    # We'll use a simple heuristic or a small LLM call if needed, 
    # but for now let's just return the search result for the agent to parse.
    return search_res

@tool
def search_company_profile(company_name: str) -> str:
    """Searches for comprehensive company description, management updates, product launches, and strategic developments.
    Priority: Firecrawl -> Tavily -> Serper -> Brave Search.
    """
    logger.info(f"Searching company profile for {company_name}")
    query = f"{company_name} company overview, management, strategic developments, product launches"
    return perform_search(query)

@tool
def search_latest_news(company_name: str) -> str:
    """Searches for the latest news, earnings reports, analyst upgrades/downgrades, and revenue guidance.
    Returns headlines, sources, dates, and summaries.
    """
    logger.info(f"Searching latest news for {company_name}")
    query = f"{company_name} latest news, earnings report, analyst rating"
    return perform_search(query, search_type="news")

def _get_yfinance_data(ticker: str) -> dict:
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        history = t.history(period="1y")
        info = t.info
        return {"history": history, "info": info}
    except Exception as e:
        logger.error(f"yfinance error for {ticker}: {e}")
        return None

from .market_data import collect_market_data

@tool
def get_market_metrics(symbol: str, exchange: str) -> str:
    """Fetches real-time market data including Price, Market Cap, Enterprise Value, Revenue, EPS, EBITDA, PE Ratio, Forward PE, PEG, Dividend Yield, Beta, 52W High/Low, Avg Volume.
    Uses Finnhub -> Alpha Vantage -> Yahoo Finance.
    """
    logger.info(f"Fetching market metrics for {symbol} on {exchange}")
    
    fallback_data = collect_market_data(symbol, exchange)
    
    ticker = _map_ticker(symbol, exchange)
    data = _get_yfinance_data(ticker)
    
    if not data or not data.get("info"):
        if fallback_data.get("available"):
            return {
                "Current Price": fallback_data.get("currentPrice"),
                "Market Cap": fallback_data.get("marketCap"),
                "Average Volume": fallback_data.get("volume"),
                "Source": fallback_data.get("provider")
            }
        return {"error": "Market data unavailable for this symbol."}
        
    info = data["info"]
    history = data["history"]
    
    current_price = history["Close"].iloc[-1] if not history.empty else info.get("currentPrice")
    
    metrics = {
        "Current Price": current_price or fallback_data.get("currentPrice"),
        "Market Cap": info.get("marketCap") or fallback_data.get("marketCap"),
        "Enterprise Value": info.get("enterpriseValue"),
        "Revenue": info.get("totalRevenue"),
        "EPS": info.get("trailingEps"),
        "EBITDA": info.get("ebitda"),
        "PE Ratio": info.get("trailingPE"),
        "Forward PE": info.get("forwardPE"),
        "PEG Ratio": info.get("pegRatio"),
        "Dividend Yield": info.get("dividendYield"),
        "Beta": info.get("beta"),
        "52 Week High": info.get("fiftyTwoWeekHigh"),
        "52 Week Low": info.get("fiftyTwoWeekLow"),
        "Average Volume": info.get("averageVolume") or fallback_data.get("volume"),
        "Source": "yfinance"
    }
    return metrics

@tool
def calculate_fundamentals(symbol: str, exchange: str) -> str:
    """Calculates Revenue Growth, Earnings Growth, Gross Margin, Operating Margin, Net Margin, ROE, ROA, Debt to Equity, Current Ratio, Free Cash Flow.
    Classifies each as Strong, Neutral, or Weak.
    """
    ticker = _map_ticker(symbol, exchange)
    logger.info(f"Calculating fundamentals for {ticker}")
    
    data = _get_yfinance_data(ticker)
    if not data or not data.get("info"):
        return {"error": "Fundamental data unavailable."}
        
    info = data["info"]
    
    def classify(val, lower, upper):
        if val is None: return "Data Not Available"
        if val > upper: return "Strong"
        if val < lower: return "Weak"
        return "Neutral"

    def classify_inv(val, lower, upper): # For things where lower is better, like Debt/Equity
        if val is None: return "Data Not Available"
        if val < lower: return "Strong"
        if val > upper: return "Weak"
        return "Neutral"

    fundamentals = {
        "Revenue Growth": {
            "Value": info.get("revenueGrowth"),
            "Classification": classify(info.get("revenueGrowth"), 0.05, 0.15)
        },
        "Earnings Growth": {
            "Value": info.get("earningsGrowth"),
            "Classification": classify(info.get("earningsGrowth"), 0.05, 0.15)
        },
        "Gross Margin": {
            "Value": info.get("grossMargins"),
            "Classification": classify(info.get("grossMargins"), 0.20, 0.40)
        },
        "Operating Margin": {
            "Value": info.get("operatingMargins"),
            "Classification": classify(info.get("operatingMargins"), 0.10, 0.20)
        },
        "Net Margin": {
            "Value": info.get("profitMargins"),
            "Classification": classify(info.get("profitMargins"), 0.05, 0.15)
        },
        "ROE": {
            "Value": info.get("returnOnEquity"),
            "Classification": classify(info.get("returnOnEquity"), 0.10, 0.20)
        },
        "ROA": {
            "Value": info.get("returnOnAssets"),
            "Classification": classify(info.get("returnOnAssets"), 0.05, 0.10)
        },
        "Debt to Equity": {
            "Value": info.get("debtToEquity"),
            "Classification": classify_inv(info.get("debtToEquity", 100), 50, 150)
        },
        "Current Ratio": {
            "Value": info.get("currentRatio"),
            "Classification": classify(info.get("currentRatio"), 1.0, 2.0)
        },
        "Free Cash Flow": {
            "Value": info.get("freeCashflow"),
            "Classification": "Strong" if info.get("freeCashflow", 0) > 0 else "Weak"
        }
    }
    score = _calc_score(info)
    rev = _rev_analysis(info, ticker)
    fundamentals["_quantScore"] = score
    fundamentals["_revenueAnalysis"] = rev
    return fundamentals

@tool
def calculate_valuation(symbol: str, exchange: str) -> str:
    """Performs PE Comparison, Sector PE Comparison, EV/EBITDA Comparison.
    Returns Undervalued, Fairly Valued, or Overvalued with explanation.
    """
    ticker = _map_ticker(symbol, exchange)
    logger.info(f"Calculating valuation for {ticker}")
    
    data = _get_yfinance_data(ticker)
    if not data or not data.get("info"):
        return {"error": "Valuation data unavailable."}
        
    info = data["info"]
    pe = info.get("trailingPE")
    forward_pe = info.get("forwardPE")
    ev_ebitda = info.get("enterpriseToEbitda")
    
    assessment = "Fairly Valued"
    if pe and forward_pe:
        if pe < 15 and forward_pe < 15:
            assessment = "Undervalued"
        elif pe > 25 or forward_pe > 25:
            assessment = "Overvalued"
            
    result = {
        "Trailing PE": pe,
        "Forward PE": forward_pe,
        "EV/EBITDA": ev_ebitda,
        "Assessment": assessment,
        "Explanation": f"Based on a Trailing PE of {pe} and Forward PE of {forward_pe}, the stock appears {assessment} relative to typical market averages."
    }
    fv = _calc_fv(info)
    result["_fairValue"] = fv
    return result

@tool
def calculate_risk(symbol: str, exchange: str) -> str:
    """Calculates Annual Volatility, Beta, Drawdown. Classifies Risk as Low, Medium, High."""
    ticker = _map_ticker(symbol, exchange)
    logger.info(f"Calculating risk for {ticker}")
    
    data = _get_yfinance_data(ticker)
    if not data or not data.get("info") or data["history"].empty:
        return {"error": "Risk data unavailable."}
        
    history = data["history"]
    closes = history["Close"].tolist()
    
    import numpy as np
    returns = np.diff(closes) / closes[:-1]
    volatility = np.std(returns) * np.sqrt(252) * 100 # Annualized volatility in %
    
    peak = closes[0]
    max_drawdown = 0
    for price in closes:
        if price > peak: peak = price
        dd = (peak - price) / peak * 100
        if dd > max_drawdown: max_drawdown = dd
        
    beta = data["info"].get("beta")
    
    risk_level = "Medium"
    if volatility > 40 or (beta and beta > 1.5) or max_drawdown > 30:
        risk_level = "High"
    elif volatility < 20 and (beta and beta < 0.8) and max_drawdown < 15:
        risk_level = "Low"

    result = {
        "Annual Volatility": round(volatility, 2) if not np.isnan(volatility) else None,
        "Beta": beta,
        "Maximum Drawdown": round(max_drawdown, 2),
        "Classification": risk_level
    }
    return result

@tool
def get_analyst_ratings(symbol: str, exchange: str) -> str:
    """Collects Buy, Hold, Sell Ratings, Average Target Price, and Consensus Rating."""
    ticker = _map_ticker(symbol, exchange)
    logger.info(f"Getting analyst ratings for {ticker}")
    
    data = _get_yfinance_data(ticker)
    if not data or not data.get("info"):
        return {"error": "Analyst ratings unavailable."}
        
    info = data["info"]
    
    result = {
        "Consensus Rating": info.get("recommendationKey", "N/A").replace("_", " ").title(),
        "Target Mean Price": info.get("targetMeanPrice"),
        "Target High Price": info.get("targetHighPrice"),
        "Target Low Price": info.get("targetLowPrice"),
        "Number of Analyst Opinions": info.get("numberOfAnalystOpinions")
    }
    enhanced = _analyst_consensus(ticker)
    if enhanced.get("Analyst Counts"):
        result["_analystCounts"] = enhanced["Analyst Counts"]
        result["_buyRatio"] = enhanced.get("Buy Ratio")
    return result


@tool
def generate_trading_factors(symbol: str, exchange: str) -> str:
    """Generates data-driven bullish and bearish investment factors based on fundamental analysis.
    Returns a dict with 'bullishFactors' and 'bearishFactors' lists.
    """
    ticker = _map_ticker(symbol, exchange)
    logger.info(f"Generating trading factors for {ticker}")

    data = _get_yfinance_data(ticker)
    if not data or not data.get("info"):
        return {"error": "Factor generation unavailable."}

    info = data["info"]
    score = _calc_score(info)
    fv = _calc_fv(info)

    bull = _gen_bull(info, score, fv)
    bear = _gen_bear(info, score, fv)

    return {"bullishFactors": bull, "bearishFactors": bear}


@tool
def get_investment_verdict(symbol: str, exchange: str) -> str:
    """Calculates a rule-based investment recommendation (BUY/HOLD/SELL) with confidence score and reasoning.
    Uses fundamental score, fair value upside, and analyst consensus.
    """
    ticker = _map_ticker(symbol, exchange)
    logger.info(f"Computing investment verdict for {ticker}")

    data = _get_yfinance_data(ticker)
    if not data or not data.get("info"):
        return {"error": "Verdict unavailable."}

    info = data["info"]
    score = _calc_score(info)
    fv = _calc_fv(info)
    analyst = _analyst_consensus(ticker)

    rec = _inv_rec(score, fv, analyst)
    return rec


@tool
def discover_peer_companies(symbol: str, exchange: str) -> str:
    """Discovers peer companies in the same sector/industry, ranked by market cap proximity.
    Returns a list of peer company details including symbol, name, PE ratio, and growth.
    """
    ticker = _map_ticker(symbol, exchange)
    logger.info(f"Discovering peers for {ticker}")

    data = _get_yfinance_data(ticker)
    if not data or not data.get("info"):
        return {"error": "Peer discovery unavailable."}

    info = data["info"]
    peers = _discover_peers(info)
    return {"peers": peers, "count": len(peers)}


@tool
def get_comprehensive_analysis(symbol: str, exchange: str) -> str:
    """Runs the full quantitative analysis pipeline and returns a comprehensive context dict.
    Includes: fundamental score, fair value, bullish/bearish factors, analyst consensus,
    investment verdict, peer comparison, and revenue analysis.
    This is the primary tool for the Investment Decision Agent.
    """
    context = _build_context(symbol, exchange)
    return context

