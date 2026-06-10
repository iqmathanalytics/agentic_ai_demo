from __future__ import annotations

import logging
import os
from statistics import mean
from typing import Any

logger = logging.getLogger(__name__)


def _ticker_for_exchange(symbol: str, exchange: str) -> str:
    exchange_upper = exchange.upper()
    symbol_upper = symbol.upper().strip()
    if exchange_upper == "NSE" and not symbol_upper.endswith(".NS"):
        result = f"{symbol_upper}.NS"
        logger.info("Symbol mapping: %s (exchange=%s) -> %s", symbol, exchange, result)
        return result
    if exchange_upper == "BSE" and not symbol_upper.endswith(".BO"):
        result = f"{symbol_upper}.BO"
        logger.info("Symbol mapping: %s (exchange=%s) -> %s", symbol, exchange, result)
        return result
    logger.info("Symbol mapping: %s (exchange=%s) -> %s (no change)", symbol, exchange, symbol_upper)
    return symbol_upper


def _fetch_yahoo(symbol: str, exchange: str) -> dict[str, Any] | None:
    ticker = _ticker_for_exchange(symbol, exchange)
    logger.info("[Yahoo Finance] Fetching ticker=%s | original_symbol=%s | exchange=%s", ticker, symbol, exchange)

    try:
        import yfinance as yf
    except ImportError as exc:
        logger.warning("[Yahoo Finance] yfinance package not installed: %s", exc)
        return None
    except Exception as exc:
        logger.warning("[Yahoo Finance] yfinance import error: %s", exc)
        return None

    try:
        yf_ticker = yf.Ticker(ticker)
        history = yf_ticker.history(period="6mo", interval="1d")
        info = yf_ticker.info or {}
        news_raw = getattr(yf_ticker, "news", [])

        logger.info(
            "[Yahoo Finance] API response for %s: history.shape=%s, info.keys=%d, news=%d items",
            ticker,
            history.shape if hasattr(history, "shape") else "N/A",
            len(info),
            len(news_raw),
        )

        if history.empty:
            logger.warning("[Yahoo Finance] Empty history for %s", ticker)
            return None

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

        volume = int(history["Volume"].tail(1).iloc[0])
        market_cap = info.get("marketCap")
        trailing_pe = info.get("trailingPE")
        sector = info.get("sector")

        logger.info(
            "[Yahoo Finance] Parsed values for %s: price=%s, change=%s%%, sma20=%s, sma50=%s, volume=%s, marketCap=%s, trailingPE=%s, sector=%s",
            ticker,
            round(latest, 2),
            round(change_pct, 2),
            round(sma20, 2),
            round(sma50, 2),
            volume,
            market_cap,
            trailing_pe,
            sector,
        )

        news_titles = [item.get("title") for item in news_raw[:5] if item.get("title")]

        return {
            "available": True,
            "provider": "Yahoo Finance",
            "ticker": ticker,
            "currentPrice": round(latest, 2),
            "change": round(change_pct, 2),
            "sma20": round(sma20, 2),
            "sma50": round(sma50, 2),
            "volume": volume,
            "marketCap": market_cap,
            "trailingPE": trailing_pe,
            "sector": sector,
            "chartData": chart_data,
            "news": news_titles,
        }
    except Exception as exc:
        logger.error("[Yahoo Finance] Exception for %s: %s", ticker, exc, exc_info=True)
        return None


def _fetch_alpha_vantage(symbol: str, exchange: str) -> dict[str, Any] | None:
    api_key = os.getenv("ALPHA_VANTAGE_KEY")
    if not api_key:
        logger.info("[Alpha Vantage] No API key — set ALPHA_VANTAGE_KEY env var to enable")
        return None

    ticker = _ticker_for_exchange(symbol, exchange)
    clean = symbol.upper().strip()
    logger.info("[Alpha Vantage] Fetching ticker=%s | clean_symbol=%s", ticker, clean)

    try:
        import httpx
    except ImportError:
        logger.warning("[Alpha Vantage] httpx not installed")
        return None

    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": clean,
            "outputsize": "compact",
            "apikey": api_key,
        }
        resp = httpx.get(url, params=params, timeout=30)
        data = resp.json()
        logger.info("[Alpha Vantage] HTTP %s | keys=%s", resp.status_code, list(data.keys()))

        if "Error Message" in data:
            logger.error("[Alpha Vantage] API error: %s", data["Error Message"])
            return None
        if "Note" in data:
            logger.warning("[Alpha Vantage] Rate limited: %s", data["Note"][:120])
            return None

        time_series = data.get("Time Series (Daily)")
        if not time_series:
            logger.warning("[Alpha Vantage] No 'Time Series (Daily)' in response")
            return None

        dates = sorted(time_series.keys(), reverse=True)[:60]
        logger.info("[Alpha Vantage] Got %d days of data for %s", len(dates), clean)

        closes = []
        chart_data = []
        for dt in dates:
            close_val = float(time_series[dt]["4. close"])
            closes.append(close_val)
            if len(chart_data) < 30:
                chart_data.append({"time": dt, "value": round(close_val, 2)})

        chart_data.reverse()
        latest = closes[0]
        previous = closes[1] if len(closes) > 1 else latest
        change_pct = ((latest - previous) / previous) * 100 if previous else 0
        sma20 = mean(closes[:20]) if len(closes) >= 20 else mean(closes)
        sma50 = mean(closes[:50]) if len(closes) >= 50 else mean(closes)
        volume = int(time_series[dates[0]]["5. volume"])

        logger.info(
            "[Alpha Vantage] Parsed values: price=%s, change=%s%%, sma20=%s, sma50=%s, volume=%s",
            round(latest, 2),
            round(change_pct, 2),
            round(sma20, 2),
            round(sma50, 2),
            volume,
        )

        return {
            "available": True,
            "provider": "Alpha Vantage",
            "ticker": ticker,
            "currentPrice": round(latest, 2),
            "change": round(change_pct, 2),
            "sma20": round(sma20, 2),
            "sma50": round(sma50, 2),
            "volume": volume,
            "marketCap": None,
            "trailingPE": None,
            "sector": None,
            "chartData": chart_data,
            "news": [],
        }
    except Exception as exc:
        logger.error("[Alpha Vantage] Exception: %s", exc, exc_info=True)
        return None


def _fetch_finnhub(symbol: str, exchange: str) -> dict[str, Any] | None:
    api_key = os.getenv("FINNHUB_KEY")
    if not api_key:
        logger.info("[Finnhub] No API key — set FINNHUB_KEY env var to enable")
        return None

    ticker = _ticker_for_exchange(symbol, exchange)
    clean = symbol.upper().strip()
    logger.info("[Finnhub] Fetching ticker=%s | clean_symbol=%s", ticker, clean)

    try:
        import httpx
    except ImportError:
        logger.warning("[Finnhub] httpx not installed")
        return None

    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={clean}&token={api_key}"
        resp = httpx.get(url, timeout=30)
        data = resp.json()
        logger.info("[Finnhub] Response: %s", data)

        if "c" not in data or data["c"] is None or data["c"] == 0:
            logger.warning("[Finnhub] No valid quote for %s — response: %s", clean, data)
            return None

        latest = float(data["c"])
        previous = float(data.get("pc", latest))
        change_pct = float(data.get("dp", 0))

        logger.info(
            "[Finnhub] Parsed values: price=%s, change=%s%%, high=%s, low=%s",
            round(latest, 2),
            round(change_pct, 2),
            round(float(data.get("h", 0)), 2),
            round(float(data.get("l", 0)), 2),
        )

        return {
            "available": True,
            "provider": "Finnhub",
            "ticker": ticker,
            "currentPrice": round(latest, 2),
            "change": round(change_pct, 2),
            "sma20": None,
            "sma50": None,
            "volume": None,
            "marketCap": None,
            "trailingPE": None,
            "sector": None,
            "chartData": [],
            "news": [],
        }
    except Exception as exc:
        logger.error("[Finnhub] Exception: %s", exc, exc_info=True)
        return None


_PROVIDERS: list[tuple[str, Any]] = [
    ("Yahoo Finance", _fetch_yahoo),
    ("Alpha Vantage", _fetch_alpha_vantage),
    ("Finnhub", _fetch_finnhub),
]


def collect_market_data(symbol: str, exchange: str) -> dict[str, Any]:
    logger.info("=" * 60)
    logger.info("collect_market_data CALLED: symbol=%r | exchange=%r", symbol, exchange)
    logger.info("=" * 60)

    if not symbol or not symbol.strip():
        logger.error("VALIDATION FAILED: empty symbol")
        return {"available": False, "error": "Stock symbol is required."}

    if not exchange or not exchange.strip():
        logger.error("VALIDATION FAILED: empty exchange")
        return {"available": False, "error": "Exchange is required."}

    errors: list[str] = []
    for name, fetch_fn in _PROVIDERS:
        logger.info("--- Trying provider: %s ---", name)
        try:
            result = fetch_fn(symbol, exchange)
            if result is not None and result.get("available") is True:
                logger.info(
                    ">>> Provider %s SUCCEEDED for %s on %s <<<",
                    name,
                    symbol,
                    exchange,
                )
                return result
            msg = result.get("error", "returned no data") if result else "returned None"
            errors.append(f"{name}: {msg}")
            logger.warning(">>> Provider %s FAILED for %s on %s: %s <<<", name, symbol, exchange, msg)
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            logger.error(">>> Provider %s EXCEPTION for %s on %s: %s <<<", name, symbol, exchange, exc, exc_info=True)

    logger.error("ALL PROVIDERS EXHAUSTED for symbol=%s exchange=%s", symbol, exchange)
    return {
        "available": False,
        "error": f"Could not fetch market data for {symbol} on {exchange}. Tried: {'; '.join(errors)}",
    }
