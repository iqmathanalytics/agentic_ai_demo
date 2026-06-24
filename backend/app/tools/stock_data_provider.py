"""Unified stock data access with Yahoo Finance + FMP fallbacks for cloud deployments."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

_BUNDLE_CACHE: dict[tuple[str, str, str], tuple[dict[str, Any], float]] = {}
_BUNDLE_CACHE_TTL_SECONDS = 60 * 10
_FMP_COOLDOWN_UNTIL = 0.0


def map_ticker(symbol: str, exchange: str) -> str:
    s = symbol.upper().strip()
    e = exchange.upper().strip()
    if e == "NSE" and not s.endswith(".NS"):
        return f"{s}.NS"
    if e == "BSE" and not s.endswith(".BO"):
        return f"{s}.BO"
    return s


def fmp_symbol(symbol: str, exchange: str) -> str:
    ticker = map_ticker(symbol, exchange)
    if ticker.endswith((".NS", ".BO")):
        return ticker
    clean = symbol.upper().strip()
    if exchange.upper() == "NSE":
        return f"{clean}.NS"
    if exchange.upper() == "BSE":
        return f"{clean}.BO"
    return clean


def _info_is_usable(info: dict | None) -> bool:
    if not info:
        return False
    keys = (
        "currentPrice",
        "regularMarketPrice",
        "marketCap",
        "trailingPE",
        "totalRevenue",
        "sector",
    )
    return any(info.get(k) not in (None, 0, "") for k in keys)


def _fetch_yfinance_bundle(ticker: str, period: str = "1y") -> dict[str, Any] | None:
    try:
        import yfinance as yf

        t = yf.Ticker(ticker)
        history = t.history(period=period)
        info = t.info or {}
        if history.empty and not _info_is_usable(info):
            return None
        return {
            "info": info,
            "history": history,
            "source": "Yahoo Finance",
            "ticker": ticker,
            "currency": info.get("currency") or info.get("financialCurrency"),
        }
    except Exception as exc:
        logger.warning("[Yahoo Finance] bundle failed for %s: %s", ticker, exc)
        return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


def _fetch_fmp_bundle(symbol: str, exchange: str, period: str = "1y") -> dict[str, Any] | None:
    global _FMP_COOLDOWN_UNTIL

    if time.time() < _FMP_COOLDOWN_UNTIL:
        logger.info("[FMP] Skipping request during short rate-limit cooldown")
        return None

    api_key = os.getenv("FMP_KEY")
    if not api_key:
        logger.info("[FMP] No API key — set FMP_KEY to enable cloud fallback")
        return None

    fmp_sym = fmp_symbol(symbol, exchange)
    ticker = map_ticker(symbol, exchange)

    try:
        import httpx
        import pandas as pd
    except ImportError as exc:
        logger.warning("[FMP] missing dependency: %s", exc)
        return None

    base = "https://financialmodelingprep.com/stable"

    def _get(client: httpx.Client, path: str, **params: Any) -> Any:
        global _FMP_COOLDOWN_UNTIL

        if time.time() < _FMP_COOLDOWN_UNTIL:
            return None
        params["apikey"] = api_key
        resp = client.get(f"{base}/{path}", params=params, timeout=25)
        if resp.status_code != 200:
            logger.warning("[FMP] %s returned HTTP %s", path, resp.status_code)
            if resp.status_code == 429:
                _FMP_COOLDOWN_UNTIL = time.time() + 60
            return None
        try:
            return resp.json()
        except Exception:
            return None

    def _first(payload: Any) -> dict:
        if isinstance(payload, list) and payload:
            return payload[0] if isinstance(payload[0], dict) else {}
        if isinstance(payload, dict):
            return payload
        return {}

    try:
        with httpx.Client(timeout=25) as client:
            profile = _first(_get(client, "profile", symbol=fmp_sym))
            quote = _first(_get(client, "quote", symbol=fmp_sym))
            metrics = _first(_get(client, "key-metrics-ttm", symbol=fmp_sym))
            ratios = _first(_get(client, "ratios-ttm", symbol=fmp_sym))
            growth = _first(_get(client, "income-statement-growth", symbol=fmp_sym, limit=1))
            cashflow = _first(_get(client, "cash-flow-statement", symbol=fmp_sym, limit=1))
            income = _first(_get(client, "income-statement", symbol=fmp_sym, limit=1))
            targets = _first(_get(client, "price-target-consensus", symbol=fmp_sym))
            grades = _first(_get(client, "grades-consensus", symbol=fmp_sym))
            history_raw = _get(client, "historical-price-eod/full", symbol=fmp_sym)
    except Exception as exc:
        logger.error("[FMP] HTTP error for %s: %s", fmp_sym, exc)
        return None

    p = profile or {}
    q = quote or {}

    current_price = _safe_float(q.get("price")) or _safe_float(p.get("price"))
    if not current_price:
        logger.warning("[FMP] No price for %s", fmp_sym)
        return None

    revenue = _safe_float(income.get("revenue"))
    growth_rev = _safe_float(growth.get("growthRevenue"))
    if growth_rev is not None and abs(growth_rev) > 1:
        growth_rev = growth_rev / 100.0
    growth_earn = _safe_float(growth.get("growthNetIncome"))
    if growth_earn is not None and abs(growth_earn) > 1:
        growth_earn = growth_earn / 100.0

    consensus = (grades.get("consensus") or "hold").lower().replace(" ", "_")
    analyst_count = sum(
        int(grades.get(k) or 0)
        for k in ("strongBuy", "buy", "hold", "sell", "strongSell")
    )

    info = {
        "shortName": p.get("companyName") or symbol,
        "longName": p.get("companyName") or symbol,
        "symbol": p.get("symbol") or fmp_sym,
        "sector": p.get("sector"),
        "industry": p.get("industry"),
        "country": p.get("country"),
        "currency": p.get("currency"),
        "website": p.get("website"),
        "longBusinessSummary": p.get("description"),
        "description": p.get("description"),
        "currentPrice": current_price,
        "regularMarketPrice": current_price,
        "marketCap": _safe_float(q.get("marketCap")) or _safe_float(p.get("marketCap")),
        "enterpriseValue": _safe_float(metrics.get("enterpriseValueTTM")),
        "totalRevenue": revenue,
        "trailingEps": _safe_float(p.get("eps")) or _safe_float(q.get("eps")),
        "ebitda": _safe_float(income.get("ebitda")),
        "trailingPE": _safe_float(metrics.get("peRatioTTM")) or _safe_float(p.get("pe")),
        "forwardPE": _safe_float(metrics.get("forwardPE")),
        "pegRatio": _safe_float(metrics.get("pegRatioTTM")),
        "dividendYield": _safe_float(ratios.get("dividendYieldTTM")),
        "beta": _safe_float(p.get("beta")) or _safe_float(q.get("beta")),
        "fiftyTwoWeekHigh": _safe_float(q.get("yearHigh")) or (
            _safe_float(str(p.get("range", "")).split("-")[-1].strip()) if p.get("range") else None
        ),
        "fiftyTwoWeekLow": _safe_float(q.get("yearLow")) or (
            _safe_float(str(p.get("range", "")).split("-")[0].strip()) if p.get("range") else None
        ),
        "averageVolume": _safe_float(q.get("avgVolume")) or _safe_float(p.get("averageVolume")),
        "revenueGrowth": growth_rev,
        "earningsGrowth": growth_earn,
        "grossMargins": _safe_float(ratios.get("grossProfitMarginTTM")),
        "operatingMargins": _safe_float(ratios.get("operatingProfitMarginTTM")),
        "profitMargins": _safe_float(ratios.get("netProfitMarginTTM")),
        "returnOnEquity": _safe_float(metrics.get("roeTTM")),
        "returnOnAssets": _safe_float(metrics.get("returnOnAssetsTTM")),
        "debtToEquity": _safe_float(metrics.get("debtToEquityTTM")),
        "currentRatio": _safe_float(metrics.get("currentRatioTTM")),
        "freeCashflow": _safe_float(cashflow.get("freeCashFlow")),
        "enterpriseToEbitda": _safe_float(metrics.get("enterpriseValueOverEBITDATTM")),
        "recommendationKey": consensus,
        "targetMeanPrice": _safe_float(targets.get("targetConsensus")) or _safe_float(targets.get("targetMedian")),
        "targetHighPrice": _safe_float(targets.get("targetHigh")),
        "targetLowPrice": _safe_float(targets.get("targetLow")),
        "numberOfAnalystOpinions": analyst_count or None,
    }

    history = pd.DataFrame()
    rows = history_raw if isinstance(history_raw, list) else (history_raw or {}).get("historical", [])
    if rows:
        df = pd.DataFrame(rows)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").set_index("date")
        col_map = {"close": "Close", "volume": "Volume"}
        df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}, inplace=True)
        if "Close" in df.columns:
            if period == "5y":
                df = df.tail(252 * 5)
            elif period == "1y":
                df = df.tail(252)
            history = df

    logger.info(
        "[FMP] bundle ready for %s | price=%s marketCap=%s history=%d rows",
        fmp_sym,
        current_price,
        info.get("marketCap"),
        len(history),
    )
    return {
        "info": info,
        "history": history,
        "source": "Financial Modeling Prep",
        "ticker": ticker,
        "currency": info.get("currency"),
    }


def _enrich_history_from_alpha_vantage(symbol: str, exchange: str) -> Any:
    api_key = os.getenv("ALPHA_VANTAGE_KEY")
    if not api_key:
        return None
    clean = symbol.upper().strip()
    try:
        import httpx
        import pandas as pd

        resp = httpx.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": clean,
                "outputsize": "full",
                "apikey": api_key,
            },
            timeout=30,
        )
        data = resp.json()
        series = data.get("Time Series (Daily)")
        if not series:
            return None
        rows = []
        for dt, vals in series.items():
            rows.append({"date": dt, "Close": float(vals["4. close"]), "Volume": int(vals["5. volume"])})
        if not rows:
            return None
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").set_index("date")
    except Exception as exc:
        logger.warning("[Alpha Vantage] history fallback failed for %s: %s", clean, exc)
        return None


def get_stock_bundle(symbol: str, exchange: str, period: str = "1y") -> dict[str, Any] | None:
    """Return stock info + price history, preferring Yahoo Finance with FMP fallback."""
    ticker = map_ticker(symbol, exchange)
    cache_key = (symbol.upper().strip(), exchange.upper().strip(), period)
    cached = _BUNDLE_CACHE.get(cache_key)
    if cached and time.time() - cached[1] < _BUNDLE_CACHE_TTL_SECONDS:
        return cached[0]

    yahoo = _fetch_yfinance_bundle(ticker, period=period)
    if yahoo and _info_is_usable(yahoo.get("info")):
        _BUNDLE_CACHE[cache_key] = (yahoo, time.time())
        return yahoo

    fmp = _fetch_fmp_bundle(symbol, exchange, period=period)
    if fmp:
        _maybe_enrich_history(fmp, symbol, exchange, period)
        _BUNDLE_CACHE[cache_key] = (fmp, time.time())
        return fmp

    return None


def _maybe_enrich_history(bundle: dict[str, Any], symbol: str, exchange: str, period: str) -> None:
    history = bundle.get("history")
    if history is not None and not history.empty:
        return
    av_hist = _enrich_history_from_alpha_vantage(symbol, exchange)
    if av_hist is not None and not av_hist.empty:
        bundle["history"] = av_hist.tail(252 * 5 if period == "5y" else 252)


def fetch_analyst_consensus(ticker: str) -> dict[str, Any]:
    """Analyst ratings via FMP stable API (cloud-safe; avoids Yahoo rate limits)."""
    global _FMP_COOLDOWN_UNTIL

    if time.time() < _FMP_COOLDOWN_UNTIL:
        return {}

    api_key = os.getenv("FMP_KEY")
    if not api_key:
        return {}

    fmp_sym = ticker.upper().strip()
    try:
        import httpx
    except ImportError:
        return {}

    base = "https://financialmodelingprep.com/stable"

    try:
        with httpx.Client(timeout=20) as client:
            grades_resp = client.get(
                f"{base}/grades-consensus",
                params={"symbol": fmp_sym, "apikey": api_key},
            )
            targets_resp = client.get(
                f"{base}/price-target-consensus",
                params={"symbol": fmp_sym, "apikey": api_key},
            )
    except Exception as exc:
        logger.warning("[FMP] analyst fetch failed for %s: %s", fmp_sym, exc)
        return {}

    if grades_resp.status_code == 429 or targets_resp.status_code == 429:
        _FMP_COOLDOWN_UNTIL = time.time() + 60
        return {}

    grades = grades_resp.json() if grades_resp.status_code == 200 else []
    targets = targets_resp.json() if targets_resp.status_code == 200 else []
    g = grades[0] if isinstance(grades, list) and grades else {}
    t = targets[0] if isinstance(targets, list) and targets else {}

    if not g and not t:
        return {}

    strong_buy = int(g.get("strongBuy") or 0)
    buy = int(g.get("buy") or 0)
    hold = int(g.get("hold") or 0)
    sell = int(g.get("sell") or 0)
    strong_sell = int(g.get("strongSell") or 0)
    total = strong_buy + buy + hold + sell + strong_sell

    grade_map = {
        "buy": strong_buy + buy,
        "hold": hold,
        "sell": sell + strong_sell,
    }
    grade_map = {k: v for k, v in grade_map.items() if v > 0}

    consensus_raw = (g.get("consensus") or "").strip()
    consensus_rating = consensus_raw.title() if consensus_raw else "N/A"

    result: dict[str, Any] = {
        "Consensus Rating": consensus_rating,
        "Target Mean Price": _safe_float(t.get("targetConsensus")) or _safe_float(t.get("targetMedian")),
        "Target High Price": _safe_float(t.get("targetHigh")),
        "Target Low Price": _safe_float(t.get("targetLow")),
        "Number of Analyst Opinions": total or None,
    }
    if grade_map:
        result["Analyst Counts"] = grade_map
        if total > 0:
            result["Buy Ratio"] = round(grade_map.get("buy", 0) / total * 100, 1)
    return result


def get_stock_info(symbol: str, exchange: str) -> tuple[dict | None, str | None]:
    bundle = get_stock_bundle(symbol, exchange, period="1y")
    if not bundle:
        return None, None
    return bundle.get("info"), bundle.get("source")
