from __future__ import annotations

import json
import logging

from langchain.agents import create_agent

from app.agents.handlers import ToolEventMiddleware
from app.graphs.workflow import describe_langgraph_workflow
from app.models.schemas import AgentEvent, AgentRunRequest
from app.prompts.templates import LINKEDIN_AGENT_SYSTEM_PROMPT
from app.services.llm_factory import create_chat_model
from app.tools.linkedin_tools import (
    _is_url,
    _resolve_profile_text,
    analyze_profile,
    optimize_keywords,
    score_recruiter_visibility,
)
from app.utils.events import SendEvent, emit

logger = logging.getLogger(__name__)

LINKEDIN_TOOLS = [
    analyze_profile,
    optimize_keywords,
    score_recruiter_visibility,
]

LINKEDIN_STEP_MAP = {
    "analyze_profile": ("scanner", "Profile Scanner"),
    "optimize_keywords": ("keyword", "Keyword Optimizer"),
    "score_recruiter_visibility": ("visibility", "Recruiter Visibility Agent"),
}


def _extract_linkedin_result(tool_history: list[dict], report_text: str) -> dict:
    result = {
        "profileScore": None,
        "visibilityScore": None,
        "profileScoreBreakdown": {},
        "visibilityScoreBreakdown": {},
        "headlineSuggestions": ["Lead with target role, domain, and measurable value."],
        "keywordRecommendations": [],
        "tips": [],
        "report": report_text,
    }

    for entry in tool_history:
        raw = entry.get("result", "")
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(parsed, dict):
            continue

        tool_name = entry.get("tool", "")

        # If any tool returned a URL error, propagate it
        if parsed.get("error"):
            result["error"] = parsed["error"]
            logger.warning("Tool %s returned error: %s", tool_name, parsed["error"])
            # Still continue to collect whatever fragments are available
            continue

        if tool_name == "analyze_profile":
            result["profileScore"] = parsed.get("profileScore")
            result["profileScoreBreakdown"] = parsed.get("scoreBreakdown", {})
            missing = parsed.get("missingElements", [])
            if missing:
                result["headlineSuggestions"] = [f"Add missing element: {m}" for m in missing]

        elif tool_name == "optimize_keywords":
            result["keywordRecommendations"] = parsed.get("missingKeywords", [])
            if not result["keywordRecommendations"]:
                result["keywordRecommendations"] = parsed.get("suggestions", [])

        elif tool_name == "score_recruiter_visibility":
            result["visibilityScore"] = parsed.get("visibilityScore")
            result["visibilityScoreBreakdown"] = parsed.get("scoreBreakdown", {})
            result["tips"] = parsed.get("improvementTips", [])

    logger.info("Extracted linkedin result: profile=%s visibility=%s keywords=%d tips=%d error=%s",
                result["profileScore"], result["visibilityScore"],
                len(result["keywordRecommendations"]), len(result["tips"]),
                result.get("error"))
    return result


async def run_linkedin_agent(request: AgentRunRequest, send: SendEvent) -> dict:
    logger.info("[FLOW] Entering LinkedIn agent — run_linkedin_agent called")
    payload = request.input
    profile_url = payload.get("url", "")
    target_role = payload.get("targetRole", payload.get("role", "Software Engineer"))

    logger.info("[FLOW] Input received: url=%s target_role=%s payload_keys=%s",
                profile_url, target_role, list(payload.keys()))

    # --- Profile content resolution ---
    # Priority: 1) structured JSON in profileText  2) plain text  3) fallback to URL
    raw_profile = payload.get("profileText", payload.get("profile", ""))
    logger.info("[FLOW] URL detection: profileText=%s profile_url=%s",
                raw_profile[:120] if raw_profile else "(empty)", profile_url)

    if not raw_profile or not raw_profile.strip():
        logger.info("[FLOW] profileText is empty — falling back to profile_url=%s", profile_url)
        raw_profile = profile_url

    # Check for bare URL with no actual profile content
    url_detected = _is_url(raw_profile)
    logger.info("[FLOW] URL detection result: _is_url=%s starts_with_brace=%s",
                url_detected, raw_profile.startswith("{") if raw_profile else False)

    if url_detected and not raw_profile.startswith("{"):
        logger.warning("[FLOW] EARLY EXIT: bare URL detected at linkedin_agent.py:105 — "
                       "no profile content provided. URL=%s", profile_url)
        logger.warning("[FLOW] Tools NEVER invoked: analyze_profile, optimize_keywords, "
                       "score_recruiter_visibility all skipped — execution returns before agent creation")
        report_data = {
            "profileScore": None,
            "visibilityScore": None,
            "profileScoreBreakdown": {},
            "visibilityScoreBreakdown": {},
            "headlineSuggestions": [],
            "keywordRecommendations": [],
            "tips": [],
            "error": "Profile content could not be extracted from LinkedIn URL.",
            "report": (
                "## LinkedIn Optimization — Content Missing\n\n"
                "A LinkedIn URL was provided without actual profile content.\n\n"
                "**Please provide profile content in one of these ways:**\n\n"
                "1. **Paste profile text:** Copy your LinkedIn profile and paste it into the profile text field.\n"
                "2. **Upload a LinkedIn PDF export:** Export your profile as a PDF from LinkedIn and upload it.\n"
                "3. **Use structured data:** Provide profile sections as JSON with keys: "
                "headline, about, experience, skills, projects, education, certifications.\n\n"
                "Once profile content is available, the optimizer will score each section "
                "and provide targeted improvement suggestions."
            ),
        }
        await send(AgentEvent(
            type="agent_failed",
            message="[Error] Profile content could not be extracted from LinkedIn URL.",
            progress=100,
            agent_id="linkedin_strategist",
            agent_name="LinkedIn Optimization Agent",
            status="failed",
            payload={"result": report_data, "toolCalls": []},
        ))
        return report_data

    logger.info("[FLOW] Attempting profile extraction via _resolve_profile_text")
    resolved = _resolve_profile_text(raw_profile)
    if "error" in resolved:
        logger.warning("[FLOW] _resolve_profile_text returned error: %s", resolved["error"])
        # JSON parse failed or other — pass through raw
        profile_display = raw_profile
        structured_fields = {}
    else:
        profile_display = resolved["profile_text"]
        structured_fields = resolved["structured_fields"]

    # Log extracted profile data for debugging
    if structured_fields:
        logger.info(
            "Extracted structured profile data: headline=%s about_len=%d exp=%d skills=%d projects=%d certs=%d edu=%d",
            structured_fields.get("headline", "")[:60],
            len(structured_fields.get("about", "")),
            len(structured_fields.get("experience", [])),
            len(structured_fields.get("skills", [])),
            len(structured_fields.get("projects", [])),
            len(structured_fields.get("certifications", [])),
            len(structured_fields.get("education", [])),
        )
    else:
        logger.info("Profile text length=%d chars (word count approx %d)",
                     len(profile_display), len(profile_display.split()))

    workflow = describe_langgraph_workflow([s[0] for s in LINKEDIN_STEP_MAP.values()])
    await send(AgentEvent(
        type="run_started",
        message=f"LinkedIn profile optimization started for role: {target_role}.",
        progress=2,
        payload={"workflow": workflow, "tools": [t.name for t in LINKEDIN_TOOLS]},
    ))

    logger.info("[FLOW] Creating LLM and middleware — about to build agent")
    llm = create_chat_model(request.credentials)
    middleware = ToolEventMiddleware(send, "linkedin_strategist", "LinkedIn Optimization Agent",
                                     tool_step_map=LINKEDIN_STEP_MAP)

    logger.info("[FLOW] Building LangChain agent with tools: %s", [t.name for t in LINKEDIN_TOOLS])
    agent = create_agent(
        model=llm,
        tools=LINKEDIN_TOOLS,
        system_prompt=LINKEDIN_AGENT_SYSTEM_PROMPT,
        middleware=[middleware],
        name="linkedin_strategist",
    )
    logger.info("[FLOW] Agent built — about to call agent.ainvoke (tools will execute here)")

    user_query = (
        f"Optimize this LinkedIn profile for a {target_role} position.\n\n"
        f"Profile information: {profile_display}\n"
        f"Profile URL: {profile_url}\n\n"
        f"First, call analyze_profile to assess the profile. "
        f"Then call optimize_keywords with the profile text and target role. "
        f"Then call score_recruiter_visibility.\n\n"
        f"After gathering all tool results, provide a complete optimization report.\n\n"
        f"If any tool returns an error, report it and stop. Do not fabricate scores."
    )

    try:
        logger.info("[FLOW] Calling analyze_profile tool (via LLM agent.ainvoke)")
        logger.info("[FLOW] If successful, optimize_keywords and score_recruiter_visibility will follow")
        raw_result = await agent.ainvoke({"messages": [("human", user_query)]})
        messages = raw_result.get("messages", [])
        output_text = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content and hasattr(msg, "type") and msg.type == "ai":
                output_text = msg.content
                break
        logger.info("[FLOW] Agent execution completed — tool_history has %d entries", len(middleware.tool_history))
        if middleware.tool_history:
            logger.info("[FLOW] Executed tools: %s",
                        [e.get("tool") for e in middleware.tool_history])
    except Exception as exc:
        logger.error("[FLOW] LinkedIn agent execution FAILED: %s", exc, exc_info=True)
        report_data = _extract_linkedin_result(middleware.tool_history, "")
        report_data["error"] = str(exc)
        report_data["report"] = f"## LinkedIn Optimization Failed\n\n**Error:** {exc}"
        await send(AgentEvent(
            type="agent_failed",
            message=f"[Error] {exc}",
            progress=100,
            agent_id="linkedin_strategist",
            agent_name="LinkedIn Optimization Agent",
            status="failed",
            payload={"result": report_data, "toolCalls": middleware.tool_history},
        ))
        return report_data

    logger.info("[FLOW] Extracting final result from %d tool entries", len(middleware.tool_history))
    report_data = _extract_linkedin_result(middleware.tool_history, output_text)
    report_data["toolCalls"] = middleware.tool_history

    logger.info("[FLOW] Final result: profileScore=%s visibilityScore=%s error=%s",
                report_data.get("profileScore"), report_data.get("visibilityScore"),
                report_data.get("error"))
    await send(AgentEvent(
        type="final",
        message="LinkedIn optimization complete — based on profile analysis.",
        progress=100,
        payload={"result": report_data, "toolCalls": middleware.tool_history},
    ))

    return report_data
