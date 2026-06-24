"""Deterministic assembly of equity research reports from graph state."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.schemas import EquityReport, NewsItem, Recommendation
from app.tools.currency_utils import TARGET_CURRENCY, convert_to_myr, get_fx_rate_to_myr, normalize_currency

logger = logging.getLogger(__name__)

_MONEY_KEYS = {
    "Current Price",
    "currentPrice",
    "regularMarketPrice",
    "Market Cap",
    "marketCap",
    "Enterprise Value",
    "Revenue",
    "totalRevenue",
    "EPS",
    "EBITDA",
    "Target Mean Price",
    "Target High Price",
    "Target Low Price",
    "targetMeanPrice",
    "targetHighPrice",
    "targetLowPrice",
    "Fair Value Estimate",
    "fairValue",
    "freeCashflow",
}

_FUNDAMENTAL_MONEY_KEYS = {"Free Cash Flow"}

_NAV_JUNK_PATTERNS = re.compile(
    r"(?i)(who we are|what we do|overview\s+our culture|history and timeline|"
    r"headquarters\s*&\s*contact|fact sheet|leadership|innovation labs|"
    r"broadband\s*&\s*fiber|internet of thing|about us overview|"
    r"community\s*&\s*more|contact info|skip to|cookie policy|privacy policy)",
)
_BIO_PATTERN = re.compile(r"(?i)mr\.|mrs\.|ms\.|dr\.\s+[a-z]\.{2,}")
_REPEAT_HEADING = re.compile(r"(?i)(overview\s*){2,}")


def _has_value(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, str) and val.strip().lower() in {"", "n/a", "na", "none", "data not available"}:
        return False
    if isinstance(val, dict) and (not val or "error" in val):
        return False
    if isinstance(val, list) and not val:
        return False
    return True


def _detect_source_currency(state: dict) -> str:
    market = state.get("market_data") or {}
    quant = state.get("quantitative_data") or {}
    market_metrics = quant.get("marketMetrics") or {}
    return normalize_currency(
        market.get("Currency")
        or market.get("currency")
        or market_metrics.get("currency")
        or quant.get("currency"),
        state.get("exchange", ""),
    )


def _convert_money_dict(value: Any, source_currency: str) -> Any:
    if isinstance(value, list):
        converted = []
        for item in value:
            if isinstance(item, dict) and "value" in item:
                converted.append({**item, "value": convert_to_myr(item["value"], source_currency)})
            else:
                converted.append(_convert_money_dict(item, source_currency))
        return converted

    if not isinstance(value, dict):
        return value

    converted = {}
    for key, item in value.items():
        if key in _MONEY_KEYS:
            converted[key] = convert_to_myr(item, source_currency)
        elif isinstance(item, dict):
            converted[key] = _convert_money_dict(item, source_currency)
        elif isinstance(item, list):
            converted[key] = _convert_money_dict(item, source_currency)
        else:
            converted[key] = item
    return converted


def _convert_fundamentals(fundamentals: dict, source_currency: str) -> dict:
    converted = {}
    for key, item in fundamentals.items():
        if isinstance(item, dict):
            item = dict(item)
            if key in _FUNDAMENTAL_MONEY_KEYS and "Value" in item:
                item["Value"] = convert_to_myr(item["Value"], source_currency)
        converted[key] = item
    return converted


def _format_myr(value: Any) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return str(value)
    amount = float(value)
    if abs(amount) >= 1e12:
        return f"RM {amount / 1e12:.2f}T"
    if abs(amount) >= 1e9:
        return f"RM {amount / 1e9:.2f}B"
    if abs(amount) >= 1e6:
        return f"RM {amount / 1e6:.2f}M"
    return f"RM {amount:,.2f}"


def normalize_state_money_to_myr(state: dict) -> tuple[dict, str, float]:
    source_currency = _detect_source_currency(state)
    fx_rate = get_fx_rate_to_myr(source_currency)

    normalized = dict(state)
    normalized["market_data"] = _convert_money_dict(state.get("market_data") or {}, source_currency)
    normalized["valuation_data"] = _convert_money_dict(state.get("valuation_data") or {}, source_currency)
    normalized["risk_data"] = _convert_money_dict(state.get("risk_data") or {}, source_currency)
    normalized["analyst_data"] = _convert_money_dict(state.get("analyst_data") or {}, source_currency)
    normalized["quantitative_data"] = _convert_money_dict(state.get("quantitative_data") or {}, source_currency)
    normalized["fundamental_data"] = _convert_fundamentals(state.get("fundamental_data") or {}, source_currency)
    return normalized, source_currency, fx_rate


def _parse_search_results(raw: str) -> list[dict]:
    if not raw:
        return []
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return [{"snippet": str(raw)[:500]}]
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def _clean_snippet(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    text = _REPEAT_HEADING.sub(" ", text)
    if _NAV_JUNK_PATTERNS.search(text):
        return ""
    if _BIO_PATTERN.search(text) and len(text) < 400:
        return ""
    if len(text) > 80 and text.count("Overview") > 2:
        return ""
    return text


def _relevance_score(item: dict, company_name: str, symbol: str) -> int:
    title = (item.get("title") or "").lower()
    snippet = (item.get("snippet") or item.get("content") or "").lower()
    combined = f"{title} {snippet}"
    score = 0
    name_parts = [p.lower() for p in company_name.split() if len(p) > 2]
    for part in name_parts[:3]:
        if part in combined:
            score += 3
    if symbol.lower() in combined:
        score += 4
    if _NAV_JUNK_PATTERNS.search(combined):
        score -= 10
    if _BIO_PATTERN.search(combined) and symbol.lower() not in combined:
        score -= 5
    if item.get("url") and any(x in item["url"].lower() for x in ("about-us", "/careers", "/leadership")):
        score -= 3
    return score


def _filter_relevant_items(items: list[dict], company_name: str, symbol: str) -> list[dict]:
    scored = []
    for item in items:
        snippet = _clean_snippet(item.get("snippet") or item.get("content") or "")
        title = _clean_snippet(item.get("title") or item.get("name") or "")
        if not snippet and not title:
            continue
        item = {**item, "snippet": snippet or item.get("snippet", ""), "title": title or item.get("title", "")}
        score = _relevance_score(item, company_name, symbol)
        if score >= 2:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored]


def extract_company_overview(
    search_raw: str,
    company_name: str,
    symbol: str = "",
    market_data: dict | None = None,
) -> str:
    market_data = market_data or {}
    yf_summary = market_data.get("longBusinessSummary") or ""
    sector = market_data.get("sector") or ""
    industry = market_data.get("industry") or ""

    paragraphs: list[str] = []

    if _has_value(yf_summary) and len(yf_summary) > 80:
        clean = _clean_snippet(yf_summary) or yf_summary[:1200]
        paragraphs.append(clean)

    if sector or industry:
        meta = []
        if sector:
            meta.append(f"**Sector:** {sector}")
        if industry:
            meta.append(f"**Industry:** {industry}")
        paragraphs.append(" | ".join(meta))

    items = _filter_relevant_items(_parse_search_results(search_raw), company_name, symbol)
    for item in items[:3]:
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        if snippet and len(snippet) > 60:
            if title and title.lower() not in snippet.lower()[:50]:
                paragraphs.append(f"**{title}** — {snippet[:400]}")
            else:
                paragraphs.append(snippet[:400])

    if not paragraphs:
        return f"{company_name} ({symbol}) — limited public profile data available. Review market metrics and fundamentals below."

    return "\n\n".join(paragraphs)


def extract_news_items(search_raw: str, company_name: str = "", symbol: str = "") -> list[NewsItem]:
    items = _parse_search_results(search_raw)
    if company_name or symbol:
        items = _filter_relevant_items(items, company_name, symbol) or items

    news: list[NewsItem] = []
    for item in items[:10]:
        title = (item.get("title") or item.get("name") or "").strip()
        snippet = (item.get("snippet") or item.get("content") or "").strip()
        if not title and not snippet:
            continue
        if not title:
            title = snippet[:80] + ("..." if len(snippet) > 80 else "")
        news.append(NewsItem(
            title=title,
            snippet=snippet or title,
            url=item.get("url", ""),
            source=item.get("source", ""),
            date=item.get("date") or item.get("published", ""),
        ))
    return news


def extract_news_headlines(search_raw: str) -> list[str]:
    return [n.title for n in extract_news_items(search_raw)]


def build_reasoning_bullets(state: dict, recommendation: Recommendation) -> list[str]:
    """Plain-English reasoning from quantitative data."""
    bullets: list[str] = []
    quant = state.get("quantitative_data") or {}
    market = state.get("market_data") or {}
    val_data = state.get("valuation_data") or {}
    risk = state.get("risk_data") or {}
    analyst = state.get("analyst_data") or {}
    rec_data = quant.get("recommendation") or {}
    action = recommendation.recommendation

    score = rec_data.get("score") or quant.get("fundamentalScore", {}).get("totalScore")
    rating = rec_data.get("rating") or quant.get("fundamentalScore", {}).get("rating", "")
    upside = rec_data.get("upside")
    fv = quant.get("fairValue") or val_data.get("_fairValue") or {}

    if score is not None:
        if action == "BUY":
            score_phrase = "supports"
        elif action == "SELL":
            score_phrase = "supports reducing exposure through"
        else:
            score_phrase = "suggests caution on"
        bullets.append(
            f"The company scores {score:.0f}/100 on fundamentals ({rating}), "
            f"which {score_phrase} a {action} stance."
        )

    price = market.get("Current Price")
    if upside is not None and price:
        fair = fv.get("fairValue")
        if fair:
            bullets.append(
                f"At {_format_myr(price)}, the stock looks {'undervalued' if upside > 5 else 'overvalued' if upside < -5 else 'fairly priced'} "
                f"vs an estimated fair value of {_format_myr(fair)} ({upside:+.1f}% upside)."
            )
        else:
            bullets.append(f"Valuation upside is estimated at {upside:+.1f}% based on available metrics.")

    bullish = quant.get("bullishFactors") or []
    bearish = quant.get("bearishFactors") or []
    if action == "BUY" and bullish:
        bullets.append(f"Key strength: {bullish[0]}")
    elif action == "SELL" and bearish:
        bullets.append(f"Key concern: {bearish[0]}")
    elif bullish and bearish:
        bullets.append(f"Balanced view — positive: {bullish[0][:100]}; risk: {bearish[0][:100]}")

    risk_level = risk.get("Classification")
    beta = risk.get("Beta") or market.get("Beta")
    if risk_level:
        beta_str = f" (beta {beta:.2f})" if isinstance(beta, (int, float)) else ""
        bullets.append(f"Risk is rated {risk_level}{beta_str}, factored into the confidence score.")

    consensus = analyst.get("Consensus Rating")
    target = analyst.get("Target Mean Price")
    if consensus and consensus != "N/A":
        target_str = f" with analyst target near {_format_myr(target)}" if _has_value(target) else ""
        bullets.append(f"Wall Street consensus is '{consensus}'{target_str}.")

    if not bullets:
        bullets.append(recommendation.reason1)
        if recommendation.reason2:
            bullets.append(recommendation.reason2)

    return bullets[:5]


def build_recommendation_summary(action: str, confidence: float, bullets: list[str]) -> str:
    if not bullets:
        return f"We recommend {action} with {confidence:.0f}% confidence based on available market data."
    lead = bullets[0]
    return f"{action} ({confidence:.0f}% confidence) — {lead}"


def collect_data_sources(state: dict) -> list[str]:
    sources: list[str] = []
    market = state.get("market_data") or {}
    if market.get("Source"):
        sources.append(str(market["Source"]))
    elif _has_value(market.get("Current Price")):
        sources.append("Yahoo Finance")

    for key in ("fundamental_data", "valuation_data", "risk_data", "analyst_data"):
        if _has_value(state.get(key)):
            if "Yahoo Finance" not in sources:
                sources.append("Yahoo Finance")

    quant = state.get("quantitative_data") or {}
    if quant.get("dataSources"):
        for s in quant["dataSources"]:
            if s not in sources:
                sources.append(s)

    if state.get("company_report") and "Data Not Available" not in str(state.get("company_report")):
        for s in ("Tavily", "Serper", "Web Search"):
            if s not in sources:
                sources.append(s)
                break

    if not sources:
        sources.append("Public market data APIs")
    return sources


def compute_data_completeness(state: dict) -> int:
    market = state.get("market_data") or {}
    quant = state.get("quantitative_data") or {}

    checks = [
        (20, _has_value(market.get("Current Price"))),
        (15, bool(market.get("chartData"))),
        (15, _has_value(quant.get("recommendation"))),
        (10, _has_value(state.get("risk_data"))),
        (10, _has_value(state.get("fundamental_data"))),
        (10, _has_value(state.get("valuation_data"))),
        (5, _has_value(market.get("Market Cap"))),
        (5, _has_value(state.get("analyst_data"))),
        (4, bool(quant.get("bullishFactors"))),
        (4, bool(quant.get("bearishFactors"))),
        (1, bool(state.get("company_report") and "Data Not Available" not in str(state.get("company_report")))),
        (1, bool(state.get("news_items") or state.get("news_headlines"))),
    ]
    total = sum(weight for weight, _ in checks)
    earned = sum(weight for weight, ok in checks if ok)
    return round(earned / total * 100) if total else 0


def _merge_valuation(market: dict, valuation: dict) -> dict:
    merged = {}
    if valuation and "error" not in valuation:
        merged["Trailing PE"] = valuation.get("Trailing PE") or market.get("PE Ratio")
        merged["Forward PE"] = valuation.get("Forward PE") or market.get("Forward PE")
        merged["EV/EBITDA"] = valuation.get("EV/EBITDA")
        merged["Assessment"] = valuation.get("Assessment")
        merged["Explanation"] = valuation.get("Explanation")
        fv = valuation.get("_fairValue") or {}
        if fv.get("fairValue"):
            merged["Fair Value Estimate"] = fv.get("fairValue")
            merged["Upside %"] = fv.get("upside")

    merged["Current Price"] = market.get("Current Price")
    merged["Market Cap"] = market.get("Market Cap")
    merged["PEG Ratio"] = market.get("PEG Ratio")
    merged["Dividend Yield"] = market.get("Dividend Yield")
    merged["Beta"] = market.get("Beta")
    return {k: v for k, v in merged.items() if _has_value(v)}


def _build_recommendation(quant: dict, state: dict) -> Recommendation:
    rec = quant.get("recommendation") or {}
    base = Recommendation(
        recommendation=rec.get("recommendation", "HOLD"),
        confidence=float(rec.get("confidence", 50)),
        reason1=rec.get("reason1", "Analysis based on available fundamental and valuation metrics."),
        reason2=rec.get("reason2", "Review data completeness score before acting on this recommendation."),
    )
    bullets = build_reasoning_bullets(state, base)
    summary = build_recommendation_summary(base.recommendation, base.confidence, bullets)
    return base.model_copy(update={
        "summary": summary,
        "reasoning": bullets,
        "reason1": bullets[0] if bullets else base.reason1,
        "reason2": bullets[1] if len(bullets) > 1 else base.reason2,
    })


def build_deterministic_markdown(
    state: dict,
    recommendation: Recommendation,
    valuation: dict,
    fundamentals: dict,
    risk: dict,
    analyst: dict,
    bullish: list,
    bearish: list,
    data_sources: list[str],
    completeness: int,
) -> str:
    name = state.get("company_name", "")
    symbol = state.get("symbol", "")
    exchange = state.get("exchange", "")

    lines = [
        f"# Equity Research: {name} ({symbol}.{exchange})",
        "",
        f"**Recommendation:** {recommendation.recommendation} | **Confidence:** {recommendation.confidence:.0f}%",
        f"**Data Completeness:** {completeness}% | **Sources:** {', '.join(data_sources)}",
        "",
        "> This analysis uses publicly available market data. Not financial advice.",
        "",
        "## Why This Recommendation",
    ]
    for b in recommendation.reasoning or [recommendation.reason1, recommendation.reason2]:
        if b:
            lines.append(f"- {b}")

    if valuation.get("Assessment"):
        lines.extend(["", "## Valuation", f"- **Assessment:** {valuation['Assessment']}"])
        for key in ("Trailing PE", "Forward PE", "EV/EBITDA", "Fair Value Estimate", "Upside %"):
            if _has_value(valuation.get(key)):
                value = _format_myr(valuation[key]) if key in {"Fair Value Estimate"} else valuation[key]
                lines.append(f"- **{key}:** {value}")

    if bullish:
        lines.extend(["", "## Bullish Factors"])
        for f in bullish[:6]:
            lines.append(f"- {f}")

    if bearish:
        lines.extend(["", "## Bearish Factors"])
        for f in bearish[:6]:
            lines.append(f"- {f}")

    return "\n".join(lines)


def build_equity_report(state: dict) -> EquityReport:
    state, source_currency, fx_rate = normalize_state_money_to_myr(state)
    market = state.get("market_data") or {}
    fund = state.get("fundamental_data") or {}
    val_data = state.get("valuation_data") or {}
    risk = state.get("risk_data") or {}
    analyst = state.get("analyst_data") or {}
    quant = state.get("quantitative_data") or {}

    valuation = _merge_valuation(market, val_data)
    recommendation = _build_recommendation(quant, state)
    bullish = quant.get("bullishFactors") or []
    bearish = quant.get("bearishFactors") or []
    data_sources = collect_data_sources(state)
    completeness = compute_data_completeness(state)

    company_name = state.get("company_name", "")
    symbol = state.get("symbol", "")

    company_overview = extract_company_overview(
        state.get("company_search_raw", ""),
        company_name,
        symbol,
        market,
    )

    news_items_raw = state.get("news_items") or []
    news_items: list[NewsItem] = []
    for item in news_items_raw:
        if isinstance(item, NewsItem):
            news_items.append(item)
        elif isinstance(item, dict):
            news_items.append(NewsItem(**item))
    if not news_items:
        raw_items = extract_news_items(
            state.get("news_search_raw", state.get("news_report", "")),
            company_name,
            symbol,
        )
        news_items = raw_items

    news_headlines = [n.title for n in news_items] if news_items else state.get("news_headlines") or []

    clean_fund = {k: v for k, v in fund.items() if not str(k).startswith("_") and _has_value(v)}

    report_md = build_deterministic_markdown(
        state, recommendation, valuation, clean_fund, risk, analyst,
        bullish, bearish, data_sources, completeness,
    )

    current_price = valuation.get("Current Price")
    market_cap = valuation.get("Market Cap")

    chart_data = list(market.get("chartData") or [])
    if chart_data and current_price is not None:
        from datetime import date
        today = str(date.today())
        if chart_data[-1]["time"] != today:
            chart_data = chart_data + [{"time": today, "value": round(float(current_price), 2)}]
        else:
            chart_data[-1]["value"] = round(float(current_price), 2)

    outlook = {}
    fv = quant.get("fairValue") or val_data.get("_fairValue") or {}
    if fv.get("upside") is not None:
        upside = fv["upside"]
        outlook = {
            "Base Case": f"Fair value assessment: {fv.get('assessment', 'N/A')}",
            "Bull Case": f"Upside scenario: +{upside:.1f}%" if upside and upside > 0 else "Limited upside",
            "Bear Case": f"Downside scenario: {upside:.1f}%" if upside and upside < 0 else "Moderate downside risk",
        }

    return EquityReport(
        stockName=company_name,
        symbol=symbol,
        exchange=state.get("exchange", ""),
        companyOverview=company_overview,
        latestNews=news_headlines,
        newsItems=news_items,
        valuation=valuation,
        fundamentals=clean_fund,
        bullishFactors=bullish,
        bearishFactors=bearish,
        riskAnalysis=risk if "error" not in risk else {},
        analystRatings=analyst if "error" not in analyst else {},
        recommendation=recommendation,
        outlook12Month=outlook,
        chartData=chart_data,
        report=report_md,
        currentPrice=float(current_price) if isinstance(current_price, (int, float)) else None,
        marketCap=float(market_cap) if isinstance(market_cap, (int, float)) else None,
        displayCurrency=TARGET_CURRENCY,
        sourceCurrency=source_currency,
        fxRateToDisplayCurrency=fx_rate,
        dataSources=data_sources,
        dataCompleteness=completeness,
    )


async def build_recommendation_reasoning_with_llm(llm, state: dict, report: EquityReport) -> Recommendation:
    """Use LLM to rewrite reasoning in simpler plain English."""
    rec = report.recommendation
    context = {
        "action": rec.recommendation,
        "confidence": rec.confidence,
        "price": report.currentPrice,
        "bullets": rec.reasoning,
        "bullish": report.bullishFactors[:2],
        "bearish": report.bearishFactors[:2],
    }
    prompt = (
        f"Rewrite this stock recommendation reasoning for {state.get('company_name')} in simple, clear English "
        f"that a beginner investor can understand. Keep {rec.recommendation} and confidence {rec.confidence}% unchanged. "
        f"Return exactly 3-4 short bullet points (one sentence each). No jargon. JSON format: "
        f'{{"summary": "one line", "bullets": ["...", "..."]}}\n\nData: {json.dumps(context)}'
    )
    try:
        response = await llm.ainvoke([
            SystemMessage(content="You explain investments simply. Output valid JSON only."),
            HumanMessage(content=prompt),
        ])
        content = getattr(response, "content", str(response))
        if isinstance(content, list):
            content = " ".join(str(p) for p in content)
        match = re.search(r"\{.*\}", str(content), re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            bullets = parsed.get("bullets") or rec.reasoning
            summary = parsed.get("summary") or rec.summary
            return rec.model_copy(update={
                "summary": summary,
                "reasoning": bullets,
                "reason1": bullets[0] if bullets else rec.reason1,
                "reason2": bullets[1] if len(bullets) > 1 else rec.reason2,
            })
    except Exception as exc:
        logger.warning("LLM reasoning enhancement skipped: %s", exc)
    return rec


async def build_company_overview_with_llm(llm, state: dict, overview: str) -> str:
    """Polish company overview — remove nav junk, write 2-3 clear paragraphs."""
    if not overview or len(overview) < 50:
        return overview
    prompt = (
        f"Write a clean 2-3 paragraph company overview for {state.get('company_name')} ({state.get('symbol')}). "
        f"Use ONLY facts from the source text below. No website navigation text, no leadership bios, "
        f"no duplicate headings. Plain English. Max 200 words.\n\nSource:\n{overview[:2000]}"
    )
    try:
        response = await llm.ainvoke([
            SystemMessage(content="You write concise investor-friendly company summaries."),
            HumanMessage(content=prompt),
        ])
        content = getattr(response, "content", str(response))
        if isinstance(content, list):
            content = " ".join(str(p) for p in content)
        if content and len(content) > 80:
            return str(content).strip()
    except Exception as exc:
        logger.warning("LLM company overview enhancement skipped: %s", exc)
    return overview


async def build_narrative_with_llm(llm, state: dict, base_report: EquityReport) -> str:
    """Optional LLM enhancement for full report markdown."""
    prompt = (
        f"Improve this equity research summary for {state.get('company_name')} "
        f"({state.get('symbol')}). Keep ALL facts, numbers, and the {base_report.recommendation.recommendation} "
        f"recommendation unchanged. Output markdown bullet points only. Max 400 words.\n\n"
        f"{base_report.report[:3000]}"
    )
    try:
        response = await llm.ainvoke([
            SystemMessage(content="You are a concise equity analyst. Never change BUY/HOLD/SELL or numeric facts."),
            HumanMessage(content=prompt),
        ])
        content = getattr(response, "content", str(response))
        if isinstance(content, list):
            content = " ".join(str(p) for p in content)
        if content and len(content) > 100:
            return str(content)
    except Exception as exc:
        logger.warning("LLM narrative enhancement skipped: %s", exc)
    return base_report.report
