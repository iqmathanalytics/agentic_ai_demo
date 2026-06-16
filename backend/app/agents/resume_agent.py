from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.handlers import ToolEventMiddleware
from app.agents.resume_report_builder import build_deterministic_report, extract_report_data
from app.graphs.workflow import describe_langgraph_workflow
from app.models.schemas import AgentEvent, AgentRunRequest
from app.prompts.templates import RESUME_AGENT_SYSTEM_PROMPT
from app.services.llm_factory import create_chat_model
from app.tools.resume_scoring import normalize_resume_text
from app.tools.resume_tools import (
    match_skills,
    parse_resume,
    review_grammar,
    score_ats_compatibility,
)
from app.utils.events import SendEvent, emit

logger = logging.getLogger(__name__)

RESUME_TOOLS = [score_ats_compatibility, match_skills, review_grammar]

# Full text used for deterministic scoring (no truncation for accuracy)
MAX_RESUME_CHARS = 50000
# Excerpt sent to LLM for narrative only
LLM_RESUME_EXCERPT = 6000

RESUME_STEP_MAP = {
    "score_ats_compatibility": ("ats", "ATS Scoring Agent"),
    "match_skills": ("skill", "Skill Match Agent"),
    "review_grammar": ("grammar", "Grammar Review Agent"),
}


def _smart_excerpt(text: str, max_chars: int = LLM_RESUME_EXCERPT) -> str:
    if len(text) <= max_chars:
        return text
    head = text[: int(max_chars * 0.6)]
    tail = text[-int(max_chars * 0.35):]
    return f"{head}\n\n[... middle section omitted for length ...]\n\n{tail}"


async def _run_tools_directly(
    send: SendEvent,
    resume_text: str,
    role: str,
    middleware: ToolEventMiddleware,
    job_description: str = "",
) -> list[dict]:
    """Run all scoring tools deterministically — primary path for accurate scores."""
    for tool_name, tool_fn, args in [
        ("score_ats_compatibility", score_ats_compatibility, {
            "resume_text": resume_text, "role": role, "job_description": job_description,
        }),
        ("match_skills", match_skills, {
            "resume_text": resume_text, "role": role, "job_description": job_description,
        }),
        ("review_grammar", review_grammar, {"resume_text": resume_text}),
    ]:
        middleware.tool_index += 1
        step = RESUME_STEP_MAP.get(tool_name)
        step_id = step[0] if step else "resume_coach"
        step_name = step[1] if step else "Resume Review Agent"

        await emit(send, "agent_started", f"Running {step_name}...", 0,
                   agent_id=step_id, agent_name=step_name, status="running")
        await emit(send, "tool_start", f"[Tool] {tool_name}", 0,
                   agent_id=step_id, agent_name=step_name,
                   payload={"tool": tool_name, "tool_index": middleware.tool_index})

        try:
            raw_result = tool_fn.invoke(args)
        except Exception as exc:
            logger.error("Tool %s failed: %s", tool_name, exc)
            middleware.tool_history.append({
                "tool_index": middleware.tool_index,
                "tool": tool_name,
                "args": {"role": role},
                "result": json.dumps({"error": str(exc)}),
                "result_preview": str(exc),
            })
            await emit(send, "agent_failed", f"{step_name} failed: {exc}", 0,
                       agent_id=step_id, agent_name=step_name, status="failed")
            continue

        middleware.tool_history.append({
            "tool_index": middleware.tool_index,
            "tool": tool_name,
            "args": {"role": role},
            "result": raw_result,
            "result_preview": raw_result[:500],
        })

        await emit(send, "tool_end", f"[Tool] {tool_name} complete", 0,
                   agent_id=step_id, agent_name=step_name,
                   payload={"tool_index": middleware.tool_index, "tool": tool_name})
        await emit(send, "agent_completed", f"{step_name} complete.", 0,
                   agent_id=step_id, agent_name=step_name, status="completed")

    return middleware.tool_history


async def _enhance_report_with_llm(
    request: AgentRunRequest,
    role: str,
    experience: str,
    base_report: str,
    tool_summary: dict,
) -> str:
    """Optional LLM polish — deterministic report is always the fallback."""
    llm = create_chat_model(request.credentials, max_tokens=2000, streaming=False)
    prompt = (
        f"Enhance this resume coaching report for a {role} role ({experience} level). "
        f"Keep ATS score {tool_summary.get('atsScore')} and skill match {tool_summary.get('skillMatch')}% unchanged. "
        "Do NOT use markdown tables — ATS breakdown and bullet rewrites are rendered separately in the UI. "
        "Write prose and bullet lists only: Executive Summary, Skill Gap narrative, Style feedback, and Final Verdict. "
        "Max 400 words.\n\n"
        f"Tool data: {json.dumps(tool_summary, default=str)[:2000]}\n\n"
        f"Base report:\n{base_report[:4000]}"
    )
    try:
        response = await llm.ainvoke([
            SystemMessage(content=RESUME_AGENT_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        content = getattr(response, "content", str(response))
        if isinstance(content, list):
            content = " ".join(str(p) for p in content)
        if content and len(content) > 200:
            return str(content)
    except Exception as exc:
        logger.warning("LLM report enhancement skipped: %s", exc)
    return base_report


async def run_resume_agent(request: AgentRunRequest, send: SendEvent) -> dict:
    payload = request.input
    file_name = payload.get("fileName", "")
    file_data = payload.get("fileData", "")
    role = payload.get("role", "")
    experience = payload.get("experience", "")
    job_description = payload.get("jobDescription", "")

    workflow = describe_langgraph_workflow(["parser", "ats", "skill", "grammar", "coach"])
    await send(AgentEvent(
        type="run_started",
        message=f"Resume review started for role: {role}.",
        progress=2,
        payload={"workflow": workflow, "tools": ["parse_resume", "score_ats_compatibility", "match_skills", "review_grammar"]},
    ))

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
            "recruiterFeedback": "",
        }
        await send(AgentEvent(type="final", message="Resume parsing failed.", progress=100, payload={"result": error_result}))
        return error_result

    if not parsed.get("available"):
        err = parsed.get("error", "Unknown parse error")
        await emit(send, "agent_failed", f"Resume parsing error: {err}", 24,
                   agent_id="parser", agent_name="Resume Parser Agent", status="failed")
        error_result = {"error": err, "report": f"## Resume Parse Failed\n\n**Error:** {err}", "recruiterFeedback": ""}
        await send(AgentEvent(type="final", message="Resume parsing failed.", progress=100, payload={"result": error_result}))
        return error_result

    resume_text = normalize_resume_text(parsed.get("text", ""))
    original_len = len(resume_text)
    if len(resume_text) > MAX_RESUME_CHARS:
        logger.warning("Resume very large (%d chars), scoring uses first %d chars", original_len, MAX_RESUME_CHARS)
        resume_text = resume_text[:MAX_RESUME_CHARS]

    logger.info("Resume parsed: file=%s chars=%d (original=%d) preview=%s...",
                file_name, len(resume_text), original_len, resume_text[:200])

    await emit(send, "agent_completed", f"Resume text extracted ({len(resume_text)} chars).", 24,
               agent_id="parser", agent_name="Resume Parser Agent", status="completed",
               payload={"characters": len(resume_text), "pages": parsed.get("pages")})

    middleware = ToolEventMiddleware(send, "resume_coach", "Resume Review Agent", tool_step_map=RESUME_STEP_MAP)

    await emit(send, "agent_running", "Running ATS, skill, and grammar analysis...", 30,
               agent_id="resume_coach", agent_name="Resume Review Agent", status="running")

    await _run_tools_directly(send, resume_text, role, middleware, job_description)

    ats_data, skills_data, grammar_data = {}, {}, {}
    for entry in middleware.tool_history:
        parsed_result = json.loads(entry["result"]) if entry.get("result") else {}
        if entry["tool"] == "score_ats_compatibility":
            ats_data = parsed_result
        elif entry["tool"] == "match_skills":
            skills_data = parsed_result
        elif entry["tool"] == "review_grammar":
            grammar_data = parsed_result

    base_report = build_deterministic_report(role, experience, ats_data, skills_data, grammar_data)
    report_data = extract_report_data(middleware.tool_history, base_report, role)

    await emit(send, "agent_started", "Synthesizing career coaching insights...", 80,
               agent_id="coach", agent_name="Career Coach Agent", status="running")

    try:
        enhanced = await _enhance_report_with_llm(request, role, experience, base_report, report_data)
        report_data["report"] = enhanced
        report_data["recruiterFeedback"] = enhanced
    except Exception as exc:
        logger.warning("Report enhancement failed, using deterministic report: %s", exc)

    report_data["toolCalls"] = middleware.tool_history
    if original_len > MAX_RESUME_CHARS:
        report_data["suggestions"] = report_data.get("suggestions", []) + [
            f"Large resume detected ({original_len} chars) — full content was analyzed for scoring"
        ]

    await emit(send, "agent_completed", "Career coaching report complete.", 95,
               agent_id="coach", agent_name="Career Coach Agent", status="completed")

    logger.info("Resume review complete: ATS=%s skillMatch=%s%% role=%s",
                report_data.get("atsScore"), report_data.get("skillMatch"), role)

    await send(AgentEvent(
        type="final",
        message="Resume review complete — based on real parsed data.",
        progress=100,
        payload={"result": report_data, "toolCalls": middleware.tool_history},
    ))

    return report_data
