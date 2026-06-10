from __future__ import annotations

import json
import logging

from langchain.agents import create_agent

from app.agents.handlers import ToolEventMiddleware
from app.graphs.workflow import describe_langgraph_workflow
from app.models.schemas import AgentEvent, AgentRunRequest
from app.prompts.templates import RESUME_AGENT_SYSTEM_PROMPT
from app.services.llm_factory import create_chat_model
from app.tools.resume_tools import match_skills, parse_resume, review_grammar, score_ats_compatibility
from app.utils.events import SendEvent, emit

logger = logging.getLogger(__name__)

RESUME_TOOLS = [
    score_ats_compatibility,
    match_skills,
    review_grammar,
]

MAX_RESUME_CHARS = 12000

RESUME_STEP_MAP = {
    "score_ats_compatibility": ("ats", "ATS Scoring Agent"),
    "match_skills": ("skill", "Skill Match Agent"),
    "review_grammar": ("grammar", "Grammar Review Agent"),
}


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _extract_resume_result(tool_history: list[dict], report_text: str) -> dict:
    result = {
        "atsScore": None,
        "skillMatch": None,
        "strengths": [],
        "weaknesses": ["Add stronger quantified impact", "Align summary with target role"],
        "missingSkills": [],
        "suggestions": ["Add metrics to each major project", "Use target-role keywords naturally"],
        "recruiterFeedback": report_text,
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

        if tool_name == "score_ats_compatibility":
            result["atsScore"] = parsed.get("atsScore")
            result["suggestions"] = parsed.get("issues", result["suggestions"])

        elif tool_name == "match_skills":
            result["skillMatch"] = parsed.get("skillMatch")
            result["missingSkills"] = parsed.get("missingSkills", [])
            result["strengths"] = parsed.get("presentSkills", [])[:4]

        elif tool_name == "review_grammar":
            if parsed.get("suggestions"):
                result["suggestions"] = result["suggestions"] + parsed["suggestions"]

    logger.info("Extracted resume result: ats=%s skill=%s strengths=%d missing=%d",
                result["atsScore"], result["skillMatch"],
                len(result["strengths"]), len(result["missingSkills"]))
    return result


def _truncate_resume_text(text: str) -> str:
    if len(text) > MAX_RESUME_CHARS:
        logger.warning("Truncating resume from %d to %d chars", len(text), MAX_RESUME_CHARS)
        return text[:MAX_RESUME_CHARS] + "\n\n[Resume truncated due to length]"
    return text


async def _run_agent_with_retry(
    request: AgentRunRequest,
    send: SendEvent,
    middleware: ToolEventMiddleware,
    user_query: str,
    max_tokens: int,
) -> str:
    llm = create_chat_model(request.credentials, max_tokens=max_tokens)

    token_estimate = _estimate_tokens(user_query)
    logger.info(
        "Resume agent: model=%s max_tokens=%d estimated_prompt_tokens=%d",
        request.credentials.model, max_tokens, token_estimate,
    )

    agent = create_agent(
        model=llm,
        tools=RESUME_TOOLS,
        system_prompt=RESUME_AGENT_SYSTEM_PROMPT,
        middleware=[middleware],
        name="resume_coach",
    )

    raw_result = await agent.ainvoke({"messages": [("human", user_query)]})
    messages = raw_result.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content and hasattr(msg, "type") and msg.type == "ai":
            return msg.content
    return ""


async def run_resume_agent(request: AgentRunRequest, send: SendEvent) -> dict:
    payload = request.input
    file_name = payload.get("fileName", "")
    file_data = payload.get("fileData", "")
    role = payload.get("role", "")
    experience = payload.get("experience", "")

    workflow = describe_langgraph_workflow(["parser", "ats", "skill", "grammar", "coach"])
    await send(AgentEvent(
        type="run_started",
        message=f"Resume review started for role: {role}.",
        progress=2,
        payload={"workflow": workflow, "tools": ["parse_resume", "score_ats_compatibility", "match_skills", "review_grammar"]},
    ))

    # --- STEP 1: Parse resume DIRECTLY (never send base64 to LLM) ---
    await emit(send, "agent_started", "Parsing uploaded resume...", 8,
               agent_id="parser", agent_name="Resume Parser Agent", status="running")

    try:
        parsed_raw = parse_resume.invoke({"file_name": file_name, "file_data": file_data})
        parsed = json.loads(parsed_raw)
    except Exception as exc:
        logger.error("Resume parse failed: %s", exc, exc_info=True)
        await emit(send, "agent_failed", f"Resume parsing error: {exc}", 24,
                   agent_id="parser", agent_name="Resume Parser Agent", status="failed")
        error_result = {
            "error": f"Could not parse resume: {exc}",
            "report": f"## Resume Parse Failed\n\n**Error:** Could not extract text from {file_name}.",
            "atsScore": None, "skillMatch": None, "strengths": [], "missingSkills": [],
            "weaknesses": [], "suggestions": [], "recruiterFeedback": "",
        }
        await send(AgentEvent(type="final", message="Resume parsing failed.", progress=100, payload={"result": error_result}))
        return error_result

    if not parsed.get("available"):
        err = parsed.get("error", "Unknown parse error")
        logger.error("Resume parse returned unavailable: %s", err)
        await emit(send, "agent_failed", f"Resume parsing error: {err}", 24,
                   agent_id="parser", agent_name="Resume Parser Agent", status="failed")
        error_result = {
            "error": err,
            "report": f"## Resume Parse Failed\n\n**Error:** {err}",
            "atsScore": None, "skillMatch": None, "strengths": [], "missingSkills": [],
            "weaknesses": [], "suggestions": [], "recruiterFeedback": "",
        }
        await send(AgentEvent(type="final", message="Resume parsing failed.", progress=100, payload={"result": error_result}))
        return error_result

    resume_text = parsed.get("text", "")
    resume_text = _truncate_resume_text(resume_text)

    logger.info("Resume parsed: file=%s size=%d chars extracted=%d preview=%s...",
                file_name, len(file_data), len(resume_text), resume_text[:200])

    await emit(send, "agent_completed", f"Resume text extracted ({len(resume_text)} chars).", 24,
               agent_id="parser", agent_name="Resume Parser Agent", status="completed",
               payload={"characters": len(resume_text)})

    # --- STEP 2-5: Agent with scoring tools (no parse_resume, no base64) ---
    middleware = ToolEventMiddleware(send, "resume_coach", "Resume Review Agent", tool_step_map=RESUME_STEP_MAP)

    user_query = (
        f"Review this resume for a {role} position (experience level: {experience}).\n\n"
        f"Resume text:\n{resume_text}\n\n"
        f"Call score_ats_compatibility, match_skills, and review_grammar with the resume text above. "
        f"After gathering all tool results, provide a complete career coaching report "
        f"based on the structured data from those tools. Keep the report concise."
    )

    await emit(send, "agent_running", "Agent analyzing resume with scoring tools...", 26,
               agent_id="resume_coach", agent_name="Resume Review Agent", status="running")

    attempts = [
        {"max_tokens": 2000, "label": "standard"},
        {"max_tokens": 1000, "label": "reduced"},
    ]

    output_text = ""
    last_error = None

    for attempt in attempts:
        try:
            middleware.tool_history.clear()
            middleware.tool_index = 0

            output_text = await _run_agent_with_retry(
                request, send, middleware, user_query, attempt["max_tokens"],
            )
            if output_text:
                logger.info("Resume agent succeeded with %s budget (max_tokens=%d)",
                            attempt["label"], attempt["max_tokens"])
                break
        except Exception as exc:
            exc_str = str(exc)
            last_error = exc_str
            is_402 = "402" in exc_str or "insufficient credits" in exc_str.lower() or "max_tokens" in exc_str.lower()

            if is_402 and attempt["label"] == "standard":
                logger.warning("402 error with max_tokens=%d, retrying with %d tokens", attempt["max_tokens"], 1000)
                await emit(send, "log",
                           "Resume too large for current model budget. Trying optimized analysis...",
                           progress=50, agent_id="resume_coach", agent_name="Resume Review Agent")
                continue
            else:
                logger.error("Resume agent failed on %s attempt: %s", attempt["label"], exc_str)
                raise

    if not output_text and last_error:
        raise Exception(last_error)

    report_data = _extract_resume_result(middleware.tool_history, output_text)
    report_data["toolCalls"] = middleware.tool_history

    await send(AgentEvent(
        type="final",
        message="Resume review complete — based on real parsed data.",
        progress=100,
        payload={"result": report_data, "toolCalls": middleware.tool_history},
    ))

    return report_data
