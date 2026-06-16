import logging
from statistics import mean
from typing import Optional

logger = logging.getLogger(__name__)


def _get_info(ticker: str) -> Optional[dict]:
    from .stock_data_provider import get_stock_bundle

    symbol = ticker.replace(".NS", "").replace(".BO", "")
    exchange = "NSE" if ticker.endswith(".NS") else "BSE" if ticker.endswith(".BO") else "NASDAQ"
    bundle = get_stock_bundle(symbol, exchange, period="1y")
    if bundle:
        return bundle.get("info")
    return None


def get_revenue_history(ticker: str) -> list:
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        q_fin = t.quarterly_financials
        if q_fin is not None and not q_fin.empty and "Total Revenue" in q_fin.index:
            rev = q_fin.loc["Total Revenue"]
            result = []
            for date, val in rev.items():
                result.append({
                    "quarter": str(date.date()),
                    "revenue": int(val) if val == val else 0
                })
            return result
        return []
    except Exception as e:
        logger.error(f"get_revenue_history error: {e}")
        return []


def revenue_analysis(info: dict, ticker: str = "") -> dict:
    rev_growth = info.get("revenueGrowth")
    rev_ttm = info.get("totalRevenue")
    quarterly = get_revenue_history(ticker) if ticker else []

    growth_rates = []
    if len(quarterly) >= 2:
        for i in range(1, len(quarterly)):
            prev = quarterly[i - 1]["revenue"]
            curr = quarterly[i]["revenue"]
            if prev and prev > 0:
                growth_rates.append(round((curr - prev) / prev * 100, 2))

    avg_growth = round(mean(growth_rates), 2) if growth_rates else None

    if rev_growth is not None:
        if rev_growth > 0.20:
            trend = "Strong Growth"
        elif rev_growth > 0.10:
            trend = "Moderate Growth"
        elif rev_growth > 0:
            trend = "Slow Growth"
        elif rev_growth > -0.10:
            trend = "Declining"
        else:
            trend = "Sharp Decline"
    else:
        trend = "Data Not Available"

    consecutive_growth = 0
    for g in growth_rates:
        if g > 0:
            consecutive_growth += 1
        else:
            break

    return {
        "revenueGrowth": rev_growth,
        "totalRevenue": rev_ttm,
        "quarterlyRevenue": quarterly,
        "quarterlyGrowthRates": growth_rates,
        "averageQuarterlyGrowth": avg_growth,
        "trend": trend,
        "consecutiveGrowthQuarters": consecutive_growth
    }


def calculate_fundamental_score(info: dict) -> dict:
    scores = {}
    max_points = {"revenueGrowth": 15, "grossMargin": 15, "operatingMargin": 10,
                  "roe": 15, "debtToEquity": 20, "currentRatio": 10, "freeCashFlow": 15}

    rg = info.get("revenueGrowth")
    if rg is not None:
        if rg > 0.25: scores["revenueGrowth"] = 15
        elif rg > 0.15: scores["revenueGrowth"] = 12
        elif rg > 0.05: scores["revenueGrowth"] = 8
        elif rg > 0: scores["revenueGrowth"] = 4
        else: scores["revenueGrowth"] = 0
    else:
        scores["revenueGrowth"] = None

    gm = info.get("grossMargins")
    if gm is not None:
        if gm > 0.60: scores["grossMargin"] = 15
        elif gm > 0.45: scores["grossMargin"] = 13
        elif gm > 0.30: scores["grossMargin"] = 10
        elif gm > 0.15: scores["grossMargin"] = 6
        else: scores["grossMargin"] = 2
    else:
        scores["grossMargin"] = None

    om = info.get("operatingMargins")
    if om is not None:
        if om > 0.30: scores["operatingMargin"] = 10
        elif om > 0.20: scores["operatingMargin"] = 8
        elif om > 0.10: scores["operatingMargin"] = 6
        elif om > 0.05: scores["operatingMargin"] = 4
        elif om > 0: scores["operatingMargin"] = 2
        else: scores["operatingMargin"] = 0
    else:
        scores["operatingMargin"] = None

    roe = info.get("returnOnEquity")
    if roe is not None:
        if roe > 0.30: scores["roe"] = 15
        elif roe > 0.20: scores["roe"] = 13
        elif roe > 0.15: scores["roe"] = 10
        elif roe > 0.10: scores["roe"] = 7
        elif roe > 0.05: scores["roe"] = 4
        else: scores["roe"] = 0
    else:
        scores["roe"] = None

    dte = info.get("debtToEquity")
    if dte is not None:
        if dte < 30: scores["debtToEquity"] = 20
        elif dte < 50: scores["debtToEquity"] = 18
        elif dte < 100: scores["debtToEquity"] = 14
        elif dte < 200: scores["debtToEquity"] = 8
        elif dte < 300: scores["debtToEquity"] = 4
        else: scores["debtToEquity"] = 0
    else:
        scores["debtToEquity"] = None

    cr = info.get("currentRatio")
    if cr is not None:
        if cr > 2.5: scores["currentRatio"] = 10
        elif cr > 2.0: scores["currentRatio"] = 9
        elif cr > 1.5: scores["currentRatio"] = 7
        elif cr > 1.0: scores["currentRatio"] = 5
        elif cr > 0.5: scores["currentRatio"] = 2
        else: scores["currentRatio"] = 0
    else:
        scores["currentRatio"] = None

    fcf = info.get("freeCashflow")
    if fcf is not None:
        if fcf > 0: scores["freeCashFlow"] = 15
        else: scores["freeCashFlow"] = 0
    else:
        scores["freeCashFlow"] = None

    available = {k: v for k, v in scores.items() if v is not None}
    total_possible = sum(max_points[k] for k in available)
    total_earned = sum(available.values())
    pct = round((total_earned / total_possible) * 100, 1) if total_possible > 0 else 0

    if pct >= 85: rating = "Excellent"
    elif pct >= 70: rating = "Strong"
    elif pct >= 55: rating = "Average"
    elif pct >= 40: rating = "Weak"
    else: rating = "Poor"

    return {
        "totalScore": pct,
        "rating": rating,
        "componentScores": scores,
        "metricsAvailable": len(available),
        "metricsTotal": len(max_points)
    }


def pe_valuation(info: dict) -> Optional[dict]:
    pe = info.get("trailingPE")
    eps = info.get("trailingEps")
    if pe and eps and pe > 0:
        sector_pe = info.get("sectorPE") or 20
        fair_pe = min(pe * 1.2, sector_pe * 1.1)
        fair_val = round(fair_pe * eps, 2)
        return {"fairValue": fair_val, "method": "PE Ratio", "appliedPE": round(fair_pe, 2)}
    return None


def forward_pe_valuation(info: dict) -> Optional[dict]:
    fpe = info.get("forwardPE")
    eps = info.get("trailingEps")
    if fpe and eps and fpe > 0:
        sector_pe = info.get("sectorPE") or 20
        fair_fpe = min(fpe * 1.15, sector_pe * 1.1)
        forward_eps = eps * (1 + (info.get("earningsGrowth") or 0.10))
        fair_val = round(fair_fpe * forward_eps, 2)
        return {"fairValue": fair_val, "method": "Forward PE", "appliedPE": round(fair_fpe, 2)}
    return None


def growth_valuation(info: dict) -> Optional[dict]:
    peg = info.get("pegRatio")
    eps = info.get("trailingEps")
    if peg and eps and peg > 0:
        fair_peg = min(peg, 1.5)
        fair_val = round(fair_peg * eps * (1 + (info.get("earningsGrowth") or 0.10)), 2)
        return {"fairValue": fair_val, "method": "PEG Ratio", "appliedPEG": round(fair_peg, 2)}
    return None


def calculate_fair_value(info: dict) -> dict:
    methods = []
    for fn in [pe_valuation, forward_pe_valuation, growth_valuation]:
        try:
            r = fn(info)
            if r:
                methods.append(r)
        except Exception as e:
            logger.warning(f"Valuation method failed: {e}")

    current_price = info.get("currentPrice") if info.get("currentPrice") is not None else info.get("regularMarketPrice")

    if methods:
        fair_vals = [m["fairValue"] for m in methods if m.get("fairValue")]
        composite = round(mean(fair_vals), 2) if fair_vals else None
    else:
        composite = None

    upside = None
    if composite and current_price and current_price > 0:
        upside = round((composite - current_price) / current_price * 100, 1)

    assessed = "Not Available"
    if upside is not None:
        if upside > 25: assessed = "Strong Buy Opportunity"
        elif upside > 10: assessed = "Undervalued"
        elif upside > -5: assessed = "Fairly Valued"
        elif upside > -15: assessed = "Overvalued"
        else: assessed = "Strongly Overvalued"

    return {
        "currentPrice": current_price,
        "fairValue": composite,
        "upside": upside,
        "assessment": assessed,
        "methods": methods
    }


def generate_bullish_factors(info: dict, score_data: dict, fair_value_data: dict) -> list:
    factors = []
    score = score_data.get("totalScore", 0)

    rg = info.get("revenueGrowth")
    if rg is not None and rg > 0.15:
        factors.append(f"Strong revenue growth of {rg*100:.0f}% indicates robust business momentum")

    gm = info.get("grossMargins")
    if gm is not None and gm > 0.50:
        factors.append(f"Healthy gross margin of {gm*100:.0f}% shows strong pricing power")

    roe = info.get("returnOnEquity")
    if roe is not None and roe > 0.20:
        factors.append(f"Strong ROE of {roe*100:.0f}% reflects efficient capital utilization")

    dte = info.get("debtToEquity")
    if dte is not None and dte < 50:
        factors.append(f"Conservative debt profile with Debt/Equity of {dte:.1f}%")

    fcf = info.get("freeCashflow")
    if fcf is not None and fcf > 0:
        factors.append(f"Positive free cash flow of ${fcf:,.0f} provides financial flexibility")

    upside = fair_value_data.get("upside")
    if upside is not None and upside > 10:
        factors.append(f"Estimated upside of {upside:.1f}% suggests attractive entry point")

    peg = info.get("pegRatio")
    if peg is not None and peg < 1.0:
        factors.append(f"PEG ratio of {peg:.2f} suggests undervaluation relative to growth")

    if score >= 80:
        factors.append("Strong overall fundamental score indicates high-quality business")

    return factors if factors else ["No significant bullish factors identified"]


def generate_bearish_factors(info: dict, score_data: dict, fair_value_data: dict) -> list:
    factors = []
    score = score_data.get("totalScore", 0)

    rg = info.get("revenueGrowth")
    if rg is not None and rg < 0.02:
        factors.append(f"Stagnant revenue growth of {rg*100:.0f}% raises demand concerns")

    gm = info.get("grossMargins")
    if gm is not None and gm < 0.20:
        factors.append(f"Low gross margin of {gm*100:.0f}% indicates weak pricing power")

    om = info.get("operatingMargins")
    if om is not None and om < 0.05:
        factors.append(f"Thin operating margin of {om*100:.0f}% signals cost inefficiency")

    dte = info.get("debtToEquity")
    if dte is not None and dte > 150:
        factors.append(f"Elevated debt-to-equity of {dte:.1f}% increases financial risk")

    cr = info.get("currentRatio")
    if cr is not None and cr < 1.0:
        factors.append(f"Current ratio of {cr:.2f} indicates potential liquidity concerns")

    fcf = info.get("freeCashflow")
    if fcf is not None and fcf < 0:
        factors.append(f"Negative free cash flow of ${abs(fcf):,.0f} raises sustainability questions")

    eps = info.get("earningsGrowth")
    if eps is not None and eps < 0:
        factors.append(f"Declining earnings ({eps*100:.0f}%) signals deteriorating profitability")

    beta = info.get("beta")
    if beta is not None and beta > 1.5:
        factors.append(f"High beta of {beta:.2f} indicates above-market volatility risk")

    upside = fair_value_data.get("upside")
    if upside is not None and upside < -15:
        factors.append(f"Estimated downside of {abs(upside):.1f}% suggests the stock is overvalued")

    if score < 40:
        factors.append("Weak overall fundamental score highlights significant business risks")

    return factors if factors else ["No significant bearish factors identified"]


def calculate_confidence(info: dict, score_data: dict) -> int:
    score = score_data.get("totalScore", 0)
    if score == 0:
        return 0

    confidence = int(score * 0.60)

    metrics_available = score_data.get("metricsAvailable", 0)
    metrics_total = score_data.get("metricsTotal", 7)
    data_completeness = metrics_available / metrics_total
    confidence += int(data_completeness * 20)

    current_price = info.get("currentPrice") if info.get("currentPrice") is not None else info.get("regularMarketPrice")
    if info.get("targetMeanPrice") and current_price:
        analyst_range = info.get("targetHighPrice", current_price) - info.get("targetLowPrice", current_price)
        if analyst_range > 0 and current_price > 0:
            spread = analyst_range / current_price
            if spread < 0.15:
                confidence += 10
            elif spread < 0.30:
                confidence += 5

    volume = info.get("averageVolume")
    if volume and volume > 1000000:
        confidence += 10

    return min(confidence, 100)


def investment_recommendation(score_data: dict, fair_value_data: dict, analyst_data: dict) -> dict:
    score = score_data.get("totalScore", 0)
    upside = fair_value_data.get("upside")
    rating = score_data.get("rating", "Average")

    analyst_rec = (analyst_data or {}).get("Consensus Rating", "").lower()
    analyst_bullish = any(w in analyst_rec for w in ["buy", "strong"])

    upside_str = f"{upside:.1f}%" if upside is not None else "N/A"

    # Default values
    action = "HOLD"
    reason1 = ""
    reason2 = ""

    if score >= 70 and upside is not None and upside > 5:
        action = "BUY"
        confidence_score = calculate_confidence({"targetMeanPrice": 1, "targetHighPrice": 2,
                                                  "targetLowPrice": 0.5, "averageVolume": 2000000,
                                                  "currentPrice": 1}, score_data)
        reason1 = f"The business looks financially strong ({rating}, {score:.0f}/100 score)."
        reason2 = f"The stock appears undervalued with about {upside_str} upside to fair value."
    elif score >= 55 and upside is not None and upside > 0:
        action = "BUY"
        confidence_score = calculate_confidence({"targetMeanPrice": 1, "targetHighPrice": 1.5,
                                                  "targetLowPrice": 0.8, "averageVolume": 1000000,
                                                  "currentPrice": 1}, score_data)
        reason1 = f"Fundamentals are solid ({rating}, {score:.0f}/100) with room to grow."
        reason2 = f"Modest upside of {upside_str} makes this a reasonable entry for long-term holders."
    elif upside is not None and upside > -10 and score >= 40:
        action = "HOLD"
        confidence_score = calculate_confidence(info={"averageVolume": 500000, "currentPrice": 1}, score_data=score_data)
        reason1 = f"Results are mixed ({rating}, {score:.0f}/100) — neither strongly cheap nor expensive."
        reason2 = f"With only {upside_str} upside, wait for a better price or clearer catalyst."
    elif upside is not None and upside <= -10:
        action = "SELL"
        confidence_score = calculate_confidence(info={"averageVolume": 500000, "currentPrice": 1}, score_data=score_data)
        reason1 = f"Fundamentals are weak ({rating}, {score:.0f}/100) and growth looks limited."
        reason2 = f"The stock may be overpriced with {upside_str} downside vs fair value — consider reducing exposure."
    else:
        action = "HOLD"
        confidence_score = calculate_confidence(info={"averageVolume": 500000, "currentPrice": 1}, score_data=score_data)
        reason1 = f"Not enough clear signals ({rating}, {score:.0f}/100) to call a strong move."
        reason2 = "Hold and watch for better data before making a bigger decision."

    if analyst_data and analyst_data.get("Consensus Rating"):
        divergence = 0 if analyst_bullish and action == "BUY" else (20 if analyst_bullish else 10)
        confidence_score = max(confidence_score - divergence, 0)

    return {
        "recommendation": action,
        "confidence": confidence_score,
        "score": score,
        "upside": upside,
        "rating": rating,
        "reason1": reason1,
        "reason2": reason2
    }


def get_analyst_consensus(ticker: str) -> dict:
    from .stock_data_provider import fetch_analyst_consensus

    fmp_result = fetch_analyst_consensus(ticker)
    if fmp_result:
        return fmp_result

    try:
        import yfinance as yf

        t = yf.Ticker(ticker)
        recs = t.recommendations
        info = t.info or {}
    except Exception as e:
        msg = str(e).lower()
        if "rate" in msg or "too many" in msg:
            logger.info("Yahoo analyst data rate-limited for %s — using available profile data only", ticker)
        else:
            logger.warning("Yahoo analyst data unavailable for %s: %s", ticker, e)
        return {}

    result = {
        "Consensus Rating": info.get("recommendationKey", "N/A").replace("_", " ").title(),
        "Target Mean Price": info.get("targetMeanPrice"),
        "Target High Price": info.get("targetHighPrice"),
        "Target Low Price": info.get("targetLowPrice"),
        "Number of Analyst Opinions": info.get("numberOfAnalystOpinions"),
    }

    if recs is not None and not recs.empty:
        try:
            grade_col = None
            for col in ["To Grade", "Action", "Grade", "Rating"]:
                if col in recs.columns:
                    grade_col = col
                    break

            if grade_col:
                recent = recs.tail(20)
                counts = recent[grade_col].value_counts()

                grade_map = {}
                for g in counts.index:
                    gs = str(g).lower()
                    if any(w in gs for w in ["buy", "outperform", "overweight", "add"]):
                        grade_map["buy"] = grade_map.get("buy", 0) + counts[g]
                    elif any(w in gs for w in ["hold", "neutral", "equal-weight", "market perform"]):
                        grade_map["hold"] = grade_map.get("hold", 0) + counts[g]
                    elif any(w in gs for w in ["sell", "underperform", "underweight", "reduce"]):
                        grade_map["sell"] = grade_map.get("sell", 0) + counts[g]

                result["Analyst Counts"] = grade_map
                if grade_map:
                    total = sum(grade_map.values())
                    result["Buy Ratio"] = round(grade_map.get("buy", 0) / total * 100, 1) if total > 0 else 0
        except Exception as e:
            logger.warning("Failed to parse Yahoo recommendations for %s: %s", ticker, e)

    return result


def discover_peers(info: dict) -> list:
    sector = info.get("sector")
    industry = info.get("industry")
    ticker = info.get("symbol")

    if not sector and not industry:
        return []

    peers = []
    try:
        import yfinance as yf
        if industry:
            t = yf.Ticker(industry)
        elif sector:
            t = yf.Ticker(sector)
    except Exception:
        pass

    market_cap = info.get("marketCap")
    peers_data = []
    try:
        import yfinance as yf
        if sector:
            try:
                sector_tickers = _get_sector_etf_holdings(sector)
                for sym in sector_tickers[:15]:
                    if sym.upper() == (ticker or "").upper():
                        continue
                    try:
                        p = yf.Ticker(sym)
                        p_info = p.info
                        p_mcap = p_info.get("marketCap")
                        if p_mcap and market_cap:
                            ratio = p_mcap / market_cap
                            if 0.1 <= ratio <= 10:
                                peers_data.append({
                                    "symbol": sym,
                                    "name": p_info.get("shortName") or p_info.get("longName") or sym,
                                    "marketCap": p_mcap,
                                    "pe": p_info.get("trailingPE"),
                                    "revenueGrowth": p_info.get("revenueGrowth"),
                                    "rating": p_info.get("recommendationKey", "").title()
                                })
                    except Exception:
                        continue
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Peer discovery failed: {e}")

    peers_data.sort(key=lambda x: x.get("marketCap") or 0, reverse=True)
    return peers_data[:8]


def _get_sector_etf_holdings(sector: str) -> list:
    sector_map = {
        "Technology": "XLK", "Healthcare": "XLV", "Financial Services": "XLF",
        "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP", "Energy": "XLE",
        "Industrials": "XLI", "Basic Materials": "XLB", "Utilities": "XLU",
        "Real Estate": "XLRE", "Communication Services": "XLC"
    }
    etf = sector_map.get(sector)
    if not etf:
        return []
    try:
        import yfinance as yf
        etf_ticker = yf.Ticker(etf)
        holdings = etf_ticker.info.get("holdings", [])
        if holdings:
            return [h.get("symbol") for h in holdings if h.get("symbol")]
    except Exception:
        pass
    return []


def build_analysis_context(symbol: str, exchange: str) -> dict:
    from .stock_data_provider import get_stock_bundle, map_ticker

    ticker = map_ticker(symbol, exchange)
    bundle = get_stock_bundle(symbol, exchange, period="1y")
    if not bundle or not bundle.get("info"):
        return {"error": "Stock data unavailable", "ticker": ticker}

    info = bundle["info"]
    history = bundle.get("history")
    data_source = bundle.get("source") or "Yahoo Finance"

    score_data = calculate_fundamental_score(info)
    rev_analysis = revenue_analysis(info, ticker)
    fv_data = calculate_fair_value(info)
    bullish = generate_bullish_factors(info, score_data, fv_data)
    bearish = generate_bearish_factors(info, score_data, fv_data)
    analyst_data = get_analyst_consensus(ticker)
    rec = investment_recommendation(score_data, fv_data, analyst_data)
    peers = discover_peers(info)

    current_price = info.get("currentPrice") if info.get("currentPrice") is not None else info.get("regularMarketPrice")
    market_cap = info.get("marketCap")
    pe_ratio = info.get("trailingPE")
    eps = info.get("trailingEps")

    context = {
        "ticker": ticker,
        "companyName": info.get("shortName") or info.get("longName") or symbol,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "dataSources": [data_source],
        "marketMetrics": {
            "currentPrice": current_price,
            "marketCap": market_cap,
            "peRatio": pe_ratio,
            "forwardPE": info.get("forwardPE"),
            "eps": eps,
            "dividendYield": info.get("dividendYield"),
            "beta": info.get("beta")
        },
        "fundamentalScore": score_data,
        "revenueAnalysis": rev_analysis,
        "fairValue": fv_data,
        "bullishFactors": bullish,
        "bearishFactors": bearish,
        "analystConsensus": analyst_data,
        "recommendation": rec,
        "peers": peers
    }
    return context
