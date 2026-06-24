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


def _is_financial_company(info: dict) -> bool:
    sector = (info.get("sector") or "").lower()
    industry = (info.get("industry") or "").lower()
    return any(term in f"{sector} {industry}" for term in ("financial", "bank", "insurance", "capital markets"))


def _rating_from_score(pct: float) -> str:
    if pct >= 85:
        return "Excellent"
    if pct >= 70:
        return "Strong"
    if pct >= 55:
        return "Average"
    if pct >= 40:
        return "Weak"
    return "Poor"


def _score_from_components(scores: dict, max_points: dict) -> dict:
    available = {k: v for k, v in scores.items() if v is not None}
    total_possible = sum(max_points[k] for k in available)
    total_earned = sum(available.values())
    pct = round((total_earned / total_possible) * 100, 1) if total_possible > 0 else 0

    return {
        "totalScore": pct,
        "rating": _rating_from_score(pct),
        "componentScores": scores,
        "metricsAvailable": len(available),
        "metricsTotal": len(max_points),
    }


def calculate_financial_fundamental_score(info: dict) -> dict:
    """Bank/financial-sector score. Avoids industrial metrics that do not apply to banks."""
    max_points = {
        "revenueGrowth": 10,
        "earningsGrowth": 10,
        "profitMargin": 15,
        "roe": 25,
        "roa": 15,
        "priceToBook": 15,
        "peRatio": 10,
    }
    scores = {}

    rg = info.get("revenueGrowth")
    if rg is not None:
        if rg > 0.15:
            scores["revenueGrowth"] = 10
        elif rg > 0.05:
            scores["revenueGrowth"] = 7
        elif rg >= 0:
            scores["revenueGrowth"] = 4
        elif rg > -0.15:
            scores["revenueGrowth"] = 2
        else:
            scores["revenueGrowth"] = 1
    else:
        scores["revenueGrowth"] = None

    eg = info.get("earningsGrowth")
    if eg is not None:
        if eg > 0.20:
            scores["earningsGrowth"] = 10
        elif eg > 0.10:
            scores["earningsGrowth"] = 8
        elif eg > 0:
            scores["earningsGrowth"] = 6
        elif eg > -0.15:
            scores["earningsGrowth"] = 3
        else:
            scores["earningsGrowth"] = 1
    else:
        scores["earningsGrowth"] = None

    pm = info.get("profitMargins")
    if pm is not None:
        if pm > 0.30:
            scores["profitMargin"] = 15
        elif pm > 0.20:
            scores["profitMargin"] = 11
        elif pm > 0.10:
            scores["profitMargin"] = 7
        elif pm > 0:
            scores["profitMargin"] = 3
        else:
            scores["profitMargin"] = 0
    else:
        scores["profitMargin"] = None

    roe = info.get("returnOnEquity")
    if roe is not None:
        if roe > 0.18:
            scores["roe"] = 25
        elif roe > 0.15:
            scores["roe"] = 21
        elif roe > 0.12:
            scores["roe"] = 17
        elif roe > 0.08:
            scores["roe"] = 10
        elif roe > 0.04:
            scores["roe"] = 5
        else:
            scores["roe"] = 0
    else:
        scores["roe"] = None

    roa = info.get("returnOnAssets")
    if roa is not None:
        if roa > 0.015:
            scores["roa"] = 15
        elif roa > 0.010:
            scores["roa"] = 12
        elif roa > 0.0075:
            scores["roa"] = 9
        elif roa > 0.005:
            scores["roa"] = 5
        else:
            scores["roa"] = 1
    else:
        scores["roa"] = None

    pb = info.get("priceToBook")
    if pb is not None:
        if pb <= 1.0:
            scores["priceToBook"] = 15
        elif pb <= 1.5:
            scores["priceToBook"] = 12
        elif pb <= 2.0:
            scores["priceToBook"] = 8
        elif pb <= 3.0:
            scores["priceToBook"] = 4
        else:
            scores["priceToBook"] = 1
    else:
        scores["priceToBook"] = None

    pe = info.get("trailingPE")
    if pe is not None and pe > 0:
        if pe <= 8:
            scores["peRatio"] = 10
        elif pe <= 12:
            scores["peRatio"] = 8
        elif pe <= 18:
            scores["peRatio"] = 5
        elif pe <= 25:
            scores["peRatio"] = 3
        else:
            scores["peRatio"] = 1
    else:
        scores["peRatio"] = None

    result = _score_from_components(scores, max_points)
    result["sectorModel"] = "financial"
    return result


def calculate_fundamental_score(info: dict) -> dict:
    if _is_financial_company(info):
        return calculate_financial_fundamental_score(info)

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

    result = _score_from_components(scores, max_points)
    result["sectorModel"] = "standard"
    return result


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


def bank_price_to_book_valuation(info: dict) -> Optional[dict]:
    book_value = info.get("bookValue")
    pb = info.get("priceToBook")
    roe = info.get("returnOnEquity")
    if not book_value or book_value <= 0:
        return None

    if roe is not None:
        if roe >= 0.18:
            fair_pb = 1.45
        elif roe >= 0.15:
            fair_pb = 1.25
        elif roe >= 0.12:
            fair_pb = 1.05
        elif roe >= 0.08:
            fair_pb = 0.85
        else:
            fair_pb = 0.70
    elif pb:
        fair_pb = min(max(pb, 0.8), 1.2)
    else:
        fair_pb = 1.0

    return {
        "fairValue": round(book_value * fair_pb, 2),
        "method": "Bank Price/Book",
        "appliedPB": round(fair_pb, 2),
    }


def bank_pe_valuation(info: dict) -> Optional[dict]:
    pe = info.get("trailingPE")
    eps = info.get("trailingEps")
    roe = info.get("returnOnEquity")
    if not pe or not eps or pe <= 0 or eps <= 0:
        return None

    if roe is not None and roe >= 0.15:
        fair_pe = 8.0
    elif roe is not None and roe >= 0.10:
        fair_pe = 7.0
    else:
        fair_pe = 6.0
    fair_pe = max(fair_pe, min(pe * 1.10, 10.0))

    return {
        "fairValue": round(eps * fair_pe, 2),
        "method": "Bank PE",
        "appliedPE": round(fair_pe, 2),
    }


def calculate_fair_value(info: dict) -> dict:
    methods = []
    valuation_methods = (
        [bank_price_to_book_valuation, bank_pe_valuation]
        if _is_financial_company(info)
        else [pe_valuation, forward_pe_valuation, growth_valuation]
    )
    for fn in valuation_methods:
        try:
            r = fn(info)
            if r:
                methods.append(r)
        except Exception as e:
            logger.warning(f"Valuation method failed: {e}")

    current_price = info.get("currentPrice") if info.get("currentPrice") is not None else info.get("regularMarketPrice")

    target_price = info.get("targetMeanPrice")
    if target_price and current_price and target_price > 0:
        methods.append({
            "fairValue": round(float(target_price), 2),
            "method": "Analyst Target",
        })

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
        factors.append("Positive free cash flow provides financial flexibility")

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
        factors.append("Negative free cash flow raises sustainability questions")

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
    """Signal-based BUY/HOLD/SELL decision.

    This deliberately separates business quality, valuation, and analyst view so a
    sector-specific stock (especially banks) is not downgraded just because
    industrial metrics are unavailable.
    """
    score = float(score_data.get("totalScore") or 0)
    rating = score_data.get("rating", "Average")
    upside = fair_value_data.get("upside")
    current = fair_value_data.get("currentPrice")

    analyst_rec = (analyst_data or {}).get("Consensus Rating", "").lower()
    analyst_bullish = any(w in analyst_rec for w in ["buy", "strong", "outperform", "overweight"])
    analyst_bearish = any(w in analyst_rec for w in ["sell", "underperform", "reduce", "underweight"])
    target = (analyst_data or {}).get("Target Mean Price")
    target_upside = None
    if isinstance(target, (int, float)) and isinstance(current, (int, float)) and current > 0:
        target_upside = round((target - current) / current * 100, 1)

    buy_points = 0
    sell_points = 0
    reasons: list[str] = []
    risks: list[str] = []

    if score >= 75:
        buy_points += 3
        reasons.append(f"Business quality is strong ({rating}, {score:.0f}/100).")
    elif score >= 60:
        buy_points += 2
        reasons.append(f"Business quality is investable ({rating}, {score:.0f}/100).")
    elif score >= 45:
        buy_points += 1
        risks.append(f"Business quality is mixed ({rating}, {score:.0f}/100).")
    else:
        sell_points += 2
        risks.append(f"Business quality is weak ({rating}, {score:.0f}/100).")

    if upside is not None:
        if upside >= 20:
            buy_points += 3
            reasons.append(f"Fair-value model indicates meaningful upside of {upside:.1f}%.")
        elif upside >= 8:
            buy_points += 2
            reasons.append(f"Fair-value model indicates upside of {upside:.1f}%.")
        elif upside >= 0:
            buy_points += 1
            reasons.append(f"Fair-value model shows modest upside of {upside:.1f}%.")
        elif upside <= -20:
            sell_points += 3
            risks.append(f"Fair-value model indicates downside of {upside:.1f}%.")
        elif upside <= -8:
            sell_points += 1
            risks.append(f"Fair-value model indicates limited downside of {upside:.1f}%.")

    if target_upside is not None:
        if target_upside >= 12:
            buy_points += 2
            reasons.append(f"Analyst target implies about {target_upside:.1f}% upside.")
        elif target_upside >= 5:
            buy_points += 1
            reasons.append(f"Analyst target implies about {target_upside:.1f}% upside.")
        elif target_upside <= -10:
            sell_points += 2
            risks.append(f"Analyst target implies about {abs(target_upside):.1f}% downside.")

    if analyst_bullish:
        buy_points += 2
        reasons.append("Analyst consensus is positive.")
    elif analyst_bearish:
        sell_points += 2
        risks.append("Analyst consensus is negative.")

    net_score = buy_points - sell_points

    if buy_points >= 5 and net_score >= 3 and score >= 55 and not (analyst_bearish and (target_upside or 0) < 0):
        action = "BUY"
    elif sell_points >= 5 and net_score <= -2:
        action = "SELL"
    else:
        action = "HOLD"

    if action == "BUY" and upside is not None and upside <= -25 and (target_upside is None or target_upside < 10):
        action = "HOLD"
        risks.append("Fair-value downside is too large to justify a BUY despite quality and analyst support.")

    conviction = abs(net_score)
    confidence_score = min(92, max(45, 48 + conviction * 7 + min(score, 90) * 0.25))
    if action == "HOLD":
        confidence_score = min(confidence_score, 72)
    confidence_score = round(confidence_score)

    if action == "BUY":
        reason1 = reasons[0] if reasons else f"The stock has a positive combined score ({rating}, {score:.0f}/100)."
        reason2 = next((r for r in reasons[1:] if "upside" in r.lower() or "consensus" in r.lower()), reasons[1] if len(reasons) > 1 else "Multiple signals support accumulation.")
    elif action == "SELL":
        reason1 = risks[0] if risks else f"The stock has a negative combined score ({rating}, {score:.0f}/100)."
        reason2 = next((r for r in risks[1:] if "downside" in r.lower() or "consensus" in r.lower()), risks[1] if len(risks) > 1 else "Risk/reward is unfavorable.")
    else:
        reason1 = risks[0] if risks else f"Signals are balanced ({rating}, {score:.0f}/100)."
        reason2 = reasons[0] if reasons else "Wait for a clearer valuation or quality signal before changing stance."

    return {
        "recommendation": action,
        "confidence": confidence_score,
        "score": score,
        "upside": upside,
        "targetUpside": target_upside,
        "rating": rating,
        "buySignals": buy_points,
        "sellSignals": sell_points,
        "reason1": reason1,
        "reason2": reason2,
    }


def get_analyst_consensus(ticker: str) -> dict:
    from .stock_data_provider import fetch_analyst_consensus

    fmp_result = fetch_analyst_consensus(ticker)
    if fmp_result:
        return fmp_result

    def _from_info() -> dict:
        info = _get_info(ticker) or {}
        if not info:
            return {}
        result = {
            "Consensus Rating": (info.get("recommendationKey") or "N/A").replace("_", " ").title(),
            "Target Mean Price": info.get("targetMeanPrice"),
            "Target High Price": info.get("targetHighPrice"),
            "Target Low Price": info.get("targetLowPrice"),
            "Number of Analyst Opinions": info.get("numberOfAnalystOpinions"),
        }
        counts = info.get("analystCounts") or {}
        counts = {k: v for k, v in counts.items() if v}
        if counts:
            result["Analyst Counts"] = counts
            total = sum(counts.values())
            result["Buy Ratio"] = round(counts.get("buy", 0) / total * 100, 1) if total > 0 else 0
        if (
            result["Consensus Rating"] != "N/A"
            or result.get("Target Mean Price") is not None
            or result.get("Analyst Counts")
        ):
            return result
        return {}

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
        return _from_info()

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

    return result if result.get("Consensus Rating") != "N/A" or result.get("Target Mean Price") is not None else _from_info()


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
            "currency": info.get("currency") or info.get("financialCurrency"),
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
