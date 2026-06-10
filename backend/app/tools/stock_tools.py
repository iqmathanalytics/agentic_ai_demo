from __future__ import annotations

import json
import logging
from datetime import datetime
from statistics import mean

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _get_yf_data(symbol: str, exchange: str) -> dict | None:
    """Internal helper — fetch yfinance data once and cache for the tool chain."""
    ticker = _map_ticker(symbol, exchange)
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance not installed")
        return None

    try:
        yf_ticker = yf.Ticker(ticker)
        history = yf_ticker.history(period="6mo", interval="1d")
        info = yf_ticker.info or {}
        if history.empty:
            logger.warning("Empty history for %s", ticker)
            return None
        closes = [float(v) for v in history["Close"].tail(60).tolist()]
        return {"history": history, "closes": closes, "info": info, "ticker": ticker}
    except Exception as exc:
        logger.error("yfinance error for %s: %s", ticker, exc, exc_info=True)
        return None


def _map_ticker(symbol: str, exchange: str) -> str:
    s = symbol.upper().strip()
    e = exchange.upper().strip()
    if e == "NSE" and not s.endswith(".NS"):
        return f"{s}.NS"
    if e == "BSE" and not s.endswith(".BO"):
        return f"{s}.BO"
    return s


@tool
def get_stock_price_data(symbol: str, exchange: str = "NSE") -> str:
    """Fetch current stock price, change percentage, SMA20, SMA50, RSI, and volume.

    Call this first to get the core price and technical data for a stock.
    """
    data = _get_yf_data(symbol, exchange)
    if data is None:
        return json.dumps({"error": f"Could not fetch price data for {symbol} on {exchange}", "available": False})

    closes = data["closes"]
    latest = closes[-1]
    previous = closes[-2] if len(closes) > 1 else latest
    change_pct = ((latest - previous) / previous) * 100 if previous else 0
    sma20 = mean(closes[-20:]) if len(closes) >= 20 else mean(closes)
    sma50 = mean(closes[-50:]) if len(closes) >= 50 else mean(closes)

    gains = [max(0, closes[i] - closes[i - 1]) for i in range(1, len(closes))]
    losses = [max(0, closes[i - 1] - closes[i]) for i in range(1, len(closes))]
    avg_gain = mean(gains[-14:]) if len(gains) >= 14 else mean(gains) if gains else 0
    avg_loss = mean(losses[-14:]) if len(losses) >= 14 else mean(losses) if losses else 0
    rsi = 50
    if avg_loss > 0:
        rs = avg_gain / avg_loss
        rsi = round(100 - (100 / (1 + rs)), 2)

    history = data["history"]
    volume = int(history["Volume"].tail(1).iloc[0])

    chart_data = [
        {"time": str(index.date()), "value": round(float(row["Close"]), 2)}
        for index, row in history.tail(30).iterrows()
    ]

    result = {
        "available": True,
        "symbol": symbol,
        "exchange": exchange,
        "currentPrice": round(latest, 2),
        "change": round(change_pct, 2),
        "sma20": round(sma20, 2),
        "sma50": round(sma50, 2),
        "rsi": rsi,
        "volume": volume,
        "chartData": chart_data,
    }
    logger.info("get_stock_price_data result: price=%s change=%s%%", result["currentPrice"], result["change"])
    return json.dumps(result)


@tool
def get_company_profile(symbol: str, exchange: str = "NSE") -> str:
    """Fetch company profile including market cap, PE ratio, sector, industry, and business summary.

    Use this to get fundamental reference data about a company.
    """
    data = _get_yf_data(symbol, exchange)
    if data is None:
        return json.dumps({"error": f"Could not fetch profile data for {symbol} on {exchange}", "available": False})

    info = data["info"]
    result = {
        "available": True,
        "symbol": symbol,
        "exchange": exchange,
        "companyName": info.get("longName", info.get("shortName", symbol)),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "businessSummary": info.get("longBusinessSummary", ""),
        "marketCap": info.get("marketCap"),
        "trailingPE": info.get("trailingPE"),
        "forwardPE": info.get("forwardPE"),
        "dividendYield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "website": info.get("website"),
    }
    logger.info("get_company_profile result: name=%s sector=%s", result["companyName"], result["sector"])
    return json.dumps(result)


@tool
def get_fundamentals(symbol: str, exchange: str = "NSE") -> str:
    """Fetch company financial fundamentals: revenue, net profit, EPS, ROE, ROCE, Debt/Equity ratio.

    Call this for in-depth financial health analysis.
    """
    data = _get_yf_data(symbol, exchange)
    if data is None:
        return json.dumps({"error": f"Could not fetch fundamental data for {symbol} on {exchange}", "available": False})

    info = data["info"]
    result = {
        "available": True,
        "symbol": symbol,
        "exchange": exchange,
        "revenue": info.get("totalRevenue"),
        "revenueGrowth": info.get("revenueGrowth"),
        "netProfit": info.get("netIncomeToCommon"),
        "eps": info.get("trailingEps"),
        "forwardEps": info.get("forwardEps"),
        "roe": info.get("returnOnEquity"),
        "debtToEquity": info.get("debtToEquity"),
        "profitMargins": info.get("profitMargins"),
        "freeCashflow": info.get("freeCashflow"),
        "operatingCashflow": info.get("operatingCashflow"),
    }
    return json.dumps(result)


@tool
def get_company_news(symbol: str, exchange: str = "NSE") -> str:
    """Fetch latest company news headlines with sources and publication dates.

    Returns recent news articles that can be used for sentiment analysis.
    """
    ticker = _map_ticker(symbol, exchange)
    try:
        import yfinance as yf
    except ImportError:
        return json.dumps({"error": "yfinance not installed", "available": False})

    try:
        yf_ticker = yf.Ticker(ticker)
        news_raw = getattr(yf_ticker, "news", [])
        if not news_raw:
            return json.dumps({"error": f"No news found for {ticker}", "available": False})

        articles = []
        for item in news_raw[:10]:
            articles.append({
                "title": item.get("title", ""),
                "source": item.get("publisher", ""),
                "date": datetime.fromtimestamp(item.get("providerPublishTime", 0)).isoformat() if item.get("providerPublishTime") else None,
                "link": item.get("link", ""),
            })
        result = {"available": True, "symbol": symbol, "articles": articles}
        logger.info("get_company_news: %d articles for %s", len(articles), ticker)
        return json.dumps(result)
    except Exception as exc:
        logger.error("News fetch error for %s: %s", ticker, exc, exc_info=True)
        return json.dumps({"error": str(exc), "available": False})


@tool
def analyze_sentiment(news_json: str) -> str:
    """Analyze sentiment of news articles (pass the JSON string from get_company_news).

    Produces an overall sentiment score (positive/negative/neutral) based on keyword analysis.
    """
    try:
        news_data = json.loads(news_json)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid news data. Call get_company_news first and pass its result."})

    if not isinstance(news_data, dict) or not news_data.get("articles"):
        return json.dumps({"error": "No articles found in the provided data. Call get_company_news first."})

    articles = news_data["articles"]
    positive_words = {"profit", "growth", "surge", "gain", "positive", "upgrade", "bullish", "record", "strong", "beat", "launch", "expansion", "partnership", "innovation", "dividend"}
    negative_words = {"loss", "decline", "fall", "drop", "negative", "downgrade", "bearish", "crash", "fear", "sell", "risk", "debt", "fraud", "investigation", "lawsuit", "penalty"}

    pos_count = 0
    neg_count = 0
    for article in articles:
        title = article.get("title", "").lower()
        for word in positive_words:
            if word in title:
                pos_count += 1
        for word in negative_words:
            if word in title:
                neg_count += 1

    total = pos_count + neg_count
    if total == 0:
        score = 0.0
        label = "neutral"
    else:
        score = round((pos_count - neg_count) / total, 2)
        if score > 0.2:
            label = "positive"
        elif score < -0.2:
            label = "negative"
        else:
            label = "neutral"

    result = {
        "sentiment_score": score,
        "sentiment_label": label,
        "positive_articles": pos_count,
        "negative_articles": neg_count,
        "total_analyzed": len(articles),
    }
    logger.info("analyze_sentiment: label=%s score=%s", label, score)
    return json.dumps(result)


@tool
def calculate_risk_metrics(symbol: str, exchange: str = "NSE") -> str:
    """Calculate volatility, maximum drawdown, and beta for a stock.

    Provides risk assessment metrics based on historical price data.
    """
    data = _get_yf_data(symbol, exchange)
    if data is None:
        return json.dumps({"error": f"Could not fetch risk data for {symbol} on {exchange}", "available": False})

    closes = data["closes"]
    returns = [(closes[i] - closes[i - 1]) / closes[i - 1] * 100 for i in range(1, len(closes))]
    volatility = round(mean([abs(r) for r in returns[-20:]]) if len(returns) >= 20 else mean([abs(r) for r in returns]), 2)

    peak = closes[0]
    max_drawdown = 0
    for price in closes:
        if price > peak:
            peak = price
        drawdown = (peak - price) / peak * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    result = {
        "available": True,
        "symbol": symbol,
        "exchange": exchange,
        "volatility_20d": volatility,
        "volatility_label": "High" if volatility > 3 else "Moderate" if volatility > 1.5 else "Low",
        "max_drawdown_pct": round(max_drawdown, 2),
        "beta": data["info"].get("beta"),
        "data_points": len(returns),
    }
    logger.info("calculate_risk_metrics: volatility=%s max_drawdown=%s", result["volatility_20d"], result["max_drawdown_pct"])
    return json.dumps(result)
