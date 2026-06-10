from __future__ import annotations

from statistics import mean
from typing import Any


def _ticker_for_exchange(symbol: str, exchange: str) -> str:
    exchange = exchange.upper()
    symbol = symbol.upper().strip()
    if exchange == "NSE" and not symbol.endswith(".NS"):
        return f"{symbol}.NS"
    if exchange == "BSE" and not symbol.endswith(".BO"):
        return f"{symbol}.BO"
    return symbol


def collect_market_data(symbol: str, exchange: str) -> dict[str, Any]:
    try:
        import yfinance as yf
    except Exception as exc:
        return {"available": False, "error": f"yfinance unavailable: {exc}"}

    ticker = _ticker_for_exchange(symbol, exchange)
    try:
        yf_ticker = yf.Ticker(ticker)
        history = yf_ticker.history(period="6mo", interval="1d")
        info = yf_ticker.info or {}
        if history.empty:
            return {"available": False, "ticker": ticker, "error": "No historical prices returned."}

        closes = [float(v) for v in history["Close"].tail(60).tolist()]
        latest = closes[-1]
        previous = closes[-2] if len(closes) > 1 else latest
        change_pct = ((latest - previous) / previous) * 100 if previous else 0
        sma20 = mean(closes[-20:]) if len(closes) >= 20 else mean(closes)
        sma50 = mean(closes[-50:]) if len(closes) >= 50 else mean(closes)
        chart_data = [
            {"time": str(index.date()), "value": round(float(row["Close"]), 2)}
            for index, row in history.tail(30).iterrows()
        ]
        return {
            "available": True,
            "ticker": ticker,
            "currentPrice": round(latest, 2),
            "change": round(change_pct, 2),
            "sma20": round(sma20, 2),
            "sma50": round(sma50, 2),
            "volume": int(history["Volume"].tail(1).iloc[0]),
            "marketCap": info.get("marketCap"),
            "trailingPE": info.get("trailingPE"),
            "sector": info.get("sector"),
            "chartData": chart_data,
            "news": [item.get("title") for item in getattr(yf_ticker, "news", [])[:5] if item.get("title")],
        }
    except Exception as exc:
        return {"available": False, "ticker": ticker, "error": str(exc)}

