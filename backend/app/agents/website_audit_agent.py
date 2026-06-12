import logging

from app.models.schemas import AgentEvent, AgentRunRequest
from app.tools.website_audit_tools import run_website_audit
from app.utils.events import SendEvent, emit

logger = logging.getLogger(__name__)


async def run_website_audit_agent(request: AgentRunRequest, send: SendEvent) -> dict:
    payload = request.input
    url = payload.get("url", "").strip()

    workflow = {
        "engine": "direct",
        "nodes": ["URL Validator", "Fetcher Agent", "Screenshot Agent", "Parser Agent", "SEO Analyst", "Performance Analyst", "Accessibility Analyst", "Best Practices Analyst", "Report Generator"],
    }
    await send(AgentEvent(
        type="run_started",
        message=f"Website audit started for {url}.",
        progress=2,
        payload={"workflow": workflow, "tools": ["validate_url", "fetch_website", "parse_html", "score"]},
    ))

    await emit(send, "agent_started", "Validating URL...", 8,
               agent_id="validator", agent_name="URL Validator", status="running")

    from app.tools.website_audit_tools import validate_url
    validation = validate_url(url)
    if not validation["valid"]:
        await emit(send, "agent_failed", f"URL validation failed: {validation['error']}", 12,
                   agent_id="validator", agent_name="URL Validator", status="failed")
        error_result = _error_result(url, [validation["error"]])
        await send(AgentEvent(
            type="final", message="Website audit failed - invalid URL.",
            progress=100, payload={"result": error_result},
        ))
        return error_result

    target_url = validation["url"]
    await emit(send, "agent_completed", f"URL validated: {target_url}", 12,
               agent_id="validator", agent_name="URL Validator", status="completed")

    await emit(send, "agent_started", "Fetching website...", 15,
               agent_id="fetcher", agent_name="Fetcher Agent", status="running")

    from app.tools.website_audit_tools import fetch_website
    fetch_result = await fetch_website(target_url)
    if not fetch_result["success"]:
        await emit(send, "agent_failed", f"Fetch failed: {fetch_result['error']}", 25,
                   agent_id="fetcher", agent_name="Fetcher Agent", status="failed")
        error_result = _error_result(target_url, [fetch_result["error"]])
        await send(AgentEvent(
            type="final", message="Website audit failed - could not fetch URL.",
            progress=100, payload={"result": error_result},
        ))
        return error_result

    await emit(send, "agent_completed", f"Website fetched ({len(fetch_result['html'])} bytes).", 25,
               agent_id="fetcher", agent_name="Fetcher Agent", status="completed")

    await emit(send, "agent_started", "Capturing desktop preview...", 27,
               agent_id="preview", agent_name="Screenshot Agent", status="running")

    from app.tools.website_audit_tools import capture_preview
    preview = await capture_preview(target_url)

    if preview:
        await send(AgentEvent(
            type="preview",
            message="Desktop preview captured.",
            progress=28,
            payload={"preview": f"data:image/png;base64,{preview}"},
        ))
        await emit(send, "agent_completed", "Desktop preview captured.", 29,
                   agent_id="preview", agent_name="Screenshot Agent", status="completed")
    else:
        await emit(send, "agent_completed", "Screenshot unavailable (non-fatal).", 29,
                   agent_id="preview", agent_name="Screenshot Agent", status="completed")

    await emit(send, "agent_started", "Parsing HTML and extracting signals...", 30,
               agent_id="parser", agent_name="Parser Agent", status="running")

    from app.tools.website_audit_tools import parse_html
    parsed = parse_html(fetch_result["html"], target_url)

    await emit(send, "agent_completed", f"Parsed {parsed['total_images']} images, {parsed['total_links']} links, {parsed['h1_count']} H1 tags.", 45,
               agent_id="parser", agent_name="Parser Agent", status="completed")

    await emit(send, "agent_started", "Scoring SEO signals...", 50,
               agent_id="seo", agent_name="SEO Analyst", status="running")

    from app.tools.website_audit_tools import score_on_page_seo, score_best_practices, score_label
    seo_score = score_on_page_seo(parsed)
    bp_score = score_best_practices(parsed)

    await emit(send, "agent_completed", f"On-page SEO: {seo_score}/100 ({score_label(seo_score)}).", 60,
               agent_id="seo", agent_name="SEO Analyst", status="completed")

    await emit(send, "agent_started", "Analyzing performance heuristics...", 62,
               agent_id="perf", agent_name="Performance Analyst", status="running")

    from app.tools.website_audit_tools import score_performance
    perf_score = score_performance(parsed)

    await emit(send, "agent_completed", f"Performance: {perf_score}/100 ({score_label(perf_score)}).", 72,
               agent_id="perf", agent_name="Performance Analyst", status="completed")

    await emit(send, "agent_started", "Checking accessibility...", 74,
               agent_id="a11y", agent_name="Accessibility Analyst", status="running")

    from app.tools.website_audit_tools import score_accessibility
    a11y_score = score_accessibility(parsed)

    await emit(send, "agent_completed", f"Accessibility: {a11y_score}/100 ({score_label(a11y_score)}).", 84,
               agent_id="a11y", agent_name="Accessibility Analyst", status="completed")

    await emit(send, "agent_started", "Evaluating best practices...", 86,
               agent_id="bestp", agent_name="Best Practices Analyst", status="running")

    await emit(send, "agent_completed", f"Best practices: {bp_score}/100 ({score_label(bp_score)}).", 92,
               agent_id="bestp", agent_name="Best Practices Analyst", status="completed")

    await emit(send, "agent_started", "Generating audit report...", 93,
               agent_id="reportgen", agent_name="Report Generator", status="running")

    from app.tools.website_audit_tools import generate_issues, generate_suggestions
    overall_seo = round((seo_score + bp_score) / 2)
    issues = generate_issues(parsed)
    suggestions = generate_suggestions(parsed)

    result = {
        "url": target_url,
        "scores": {
            "on_page_seo": {"score": seo_score, "label": score_label(seo_score)},
            "performance": {"score": perf_score, "label": score_label(perf_score)},
            "accessibility": {"score": a11y_score, "label": score_label(a11y_score)},
            "seo": {"score": overall_seo, "label": score_label(overall_seo)},
            "best_practices": {"score": bp_score, "label": score_label(bp_score)},
        },
        "issues": issues,
        "suggestions": suggestions,
    }

    await emit(send, "agent_completed", "Audit report ready.", 98,
               agent_id="reportgen", agent_name="Report Generator", status="completed")

    await send(AgentEvent(
        type="final",
        message="Website audit complete.",
        progress=100,
        payload={"result": result},
    ))

    return result


def _error_result(url: str, errors: list[str]) -> dict:
    return {
        "url": url or "",
        "scores": {
            "on_page_seo": {"score": 0, "label": "Poor"},
            "performance": {"score": 0, "label": "Poor"},
            "accessibility": {"score": 0, "label": "Poor"},
            "seo": {"score": 0, "label": "Poor"},
            "best_practices": {"score": 0, "label": "Poor"},
        },
        "issues": errors if errors else ["Unable to analyze website."],
        "suggestions": ["Verify the URL and try again."],
    }
