from __future__ import annotations

import json
import logging
import re

from langchain.agents import create_agent

from app.agents.handlers import ToolEventMiddleware
from app.graphs.workflow import describe_langgraph_workflow
from app.models.schemas import AgentEvent, AgentRunRequest
from app.prompts.templates import RESUME_AGENT_SYSTEM_PROMPT
from app.services.llm_factory import create_chat_model
from app.tools.resume_tools import (
    AtsScoreOutput,
    GrammarReviewOutput,
    SkillMatchOutput,
    match_skills,
    parse_resume,
    review_grammar,
    score_ats_compatibility,
)
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

    logger.info("=== _extract_resume_result: %d tool entries in history ===", len(tool_history))

    for entry in tool_history:
        raw = entry.get("result", "")
        tool_name = entry.get("tool", "")

        logger.info("Tool entry #%s: tool=%s result_len=%d preview=%s...",
                     entry.get("tool_index", "?"), tool_name,
                     len(raw) if raw else 0, raw[:300] if raw else "EMPTY")

        if not raw:
            logger.warning("Tool %s: empty result", tool_name)
            continue

        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("Tool %s: JSON parse failed: %s  raw=%s", tool_name, e, raw[:500])
            continue

        if not isinstance(parsed, dict):
            logger.warning("Tool %s: parsed result is not a dict, got %s", tool_name, type(parsed).__name__)
            continue

        logger.info("Tool %s: parsed JSON keys=%s  values=%s",
                     tool_name, list(parsed.keys()), parsed)

        if tool_name == "score_ats_compatibility":
            raw_ats = parsed.get("atsScore")
            logger.info(">>> Field: atsScore -> raw_value=%s (type=%s)", raw_ats, type(raw_ats).__name__ if raw_ats is not None else "NoneType")
            result["atsScore"] = raw_ats
            issues = parsed.get("issues", [])
            if issues:
                result["suggestions"] = issues

        elif tool_name == "match_skills":
            raw_skill = parsed.get("skillMatch")
            logger.info(">>> Field: skillMatch -> raw_value=%s (type=%s)", raw_skill, type(raw_skill).__name__ if raw_skill is not None else "NoneType")
            result["skillMatch"] = raw_skill
            result["missingSkills"] = parsed.get("missingSkills", [])
            present = parsed.get("presentSkills", [])
            result["strengths"] = present[:4]
            logger.info(">>> Field: missingSkills=%d strengths=%d", len(result["missingSkills"]), len(result["strengths"]))

        elif tool_name == "review_grammar":
            if parsed.get("suggestions"):
                result["suggestions"] = result["suggestions"] + parsed["suggestions"]
                logger.info(">>> review_grammar added %d suggestions", len(parsed["suggestions"]))

    # If tool_history is empty, try to extract structured JSON from report_text
    if not tool_history:
        logger.warning("tool_history is EMPTY — falling back to LLM report parsing")
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", report_text, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                logger.info("Parsed JSON from LLM report: keys=%s", list(parsed.keys()))
                result["atsScore"] = parsed.get("ats_score", parsed.get("atsScore", result["atsScore"]))
                result["skillMatch"] = parsed.get("skill_match", parsed.get("skillMatch", result["skillMatch"]))
                result["strengths"] = parsed.get("strengths", result["strengths"])
                result["missingSkills"] = parsed.get("missing_skills", parsed.get("missingSkills", result["missingSkills"]))
                recs = parsed.get("recommendations", parsed.get("suggestions", []))
                if recs:
                    result["suggestions"] = recs
                logger.info("Fallback JSON parse: ats=%s skill=%s strengths=%d missing=%d",
                            result["atsScore"], result["skillMatch"],
                            len(result["strengths"]), len(result["missingSkills"]))
            except json.JSONDecodeError as e:
                logger.error("Fallback JSON parse failed: %s", e)

    logger.info("=== FINAL extracted resume result: ats=%s skill=%s strengths=%d missing=%d ===",
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


async def _run_tools_directly(
    send: SendEvent,
    resume_text: str,
    role: str,
    middleware: ToolEventMiddleware,
    job_description: str = "",
) -> list[dict]:
    """Fallback: call scoring tools directly if the LLM skipped them."""
    logger.warning("Running tools directly as fallback (LLM did not call them)")

    for tool_name, tool_fn, args in [
        ("score_ats_compatibility", score_ats_compatibility, {"resume_text": resume_text, "role": role, "job_description": job_description}),
        ("match_skills", match_skills, {"resume_text": resume_text, "role": role, "job_description": job_description}),
        ("review_grammar", review_grammar, {"resume_text": resume_text}),
    ]:
        middleware.tool_index += 1
        step = RESUME_STEP_MAP.get(tool_name)
        step_id = step[0] if step else "resume_coach"
        step_name = step[1] if step else "Resume Coach"

        if step:
            await emit(send, "agent_started", f"Running {step_name}...", progress=0,
                       agent_id=step_id, agent_name=step_name, status="running")

        await emit(send, "tool_start", f"[Direct] {tool_name}", progress=0,
                   agent_id=step_id, agent_name=step_name,
                   payload={"tool": tool_name, "args": args, "tool_index": middleware.tool_index, "direct": True})

        try:
            raw_result = tool_fn.invoke(args)
        except Exception as exc:
            logger.error("Direct tool %s failed: %s", tool_name, exc)
            middleware.tool_history.append({
                "tool_index": middleware.tool_index,
                "tool": tool_name,
                "args": args,
                "result": json.dumps({"error": str(exc)}),
                "result_preview": f"[Error] {exc}",
            })
            if step:
                await emit(send, "agent_failed", f"{step_name} failed: {exc}", progress=0,
                           agent_id=step_id, agent_name=step_name, status="failed")
            continue

        middleware.tool_history.append({
            "tool_index": middleware.tool_index,
            "tool": tool_name,
            "args": args,
            "result": raw_result,
            "result_preview": raw_result[:500],
        })

        await emit(send, "tool_end", f"[Direct] {tool_name} complete", progress=0,
                   agent_id=step_id, agent_name=step_name,
                   payload={"tool_index": middleware.tool_index, "tool": tool_name, "direct": True})

        if step:
            await emit(send, "agent_completed", f"{step_name} complete.", progress=0,
                       agent_id=step_id, agent_name=step_name, status="completed")

    return middleware.tool_history


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

    # --- STEP 2-5: Agent with scoring tools (no base64) ---
    middleware = ToolEventMiddleware(send, "resume_coach", "Resume Review Agent", tool_step_map=RESUME_STEP_MAP)

    jd_text = f"\n\nTarget Job Description:\n{job_description}" if job_description else ""
    user_query = (
        f"Review this resume for a {role} position (experience level: {experience}).{jd_text}\n\n"
        f"Resume text:\n{resume_text}\n\n"
        f"You MUST call score_ats_compatibility, match_skills, and review_grammar with the resume text above. "
        f"If a job description was provided, pass it to score_ats_compatibility and match_skills. "
        f"Call all three tools before writing your report. "
        f"After gathering all tool results, provide a complete career coaching report "
        f"based on the structured data from those tools. Be extremely thorough in your suggestions.\n\n"
        f"At the end of your report, include a JSON block on its own line:\n"
        f"```json\n"
        f"{{\n"
        f'  "ats_score": <integer 0-100>,\n'
        f'  "skill_match": <integer 0-100>,\n'
        f'  "strengths": ["skill1", "skill2"],\n'
        f'  "missing_skills": ["skill3", "skill4"],\n'
        f'  "recommendations": ["detailed suggestion 1", "detailed suggestion 2", "detailed suggestion 3"]\n'
        f"}}\n"
        f"```"
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

    # Emit running status for Career Coach Agent
    await emit(send, "agent_started", "Synthesizing career coaching insights...", 80,
               agent_id="coach", agent_name="Career Coach Agent", status="running")

    # --- Log raw LLM response before parsing ---
    logger.info("=== RAW LLM RESPONSE (first 2000 chars) ===")
    logger.info(output_text[:2000])
    logger.info("=== END RAW LLM RESPONSE ===")

    # --- Extract result from tool history ---
    if not middleware.tool_history:
        logger.warning("LLM did not call any tools — running tools directly as fallback")
        await emit(send, "log",
                   "Falling back to direct tool execution...",
                   progress=60, agent_id="resume_coach", agent_name="Resume Review Agent")
        await _run_tools_directly(send, resume_text, role, middleware, job_description)

    report_data = _extract_resume_result(middleware.tool_history, output_text)

    # If both tool history and JSON fallback failed, attach raw response
    if report_data["atsScore"] is None and report_data["skillMatch"] is None:
        logger.warning("Extraction produced None values — attaching raw LLM response")
        report_data["_raw_llm_response"] = output_text[:5000]
        report_data["report"] = (
            report_data.get("report", "")
            + "\n\n---\n*Note: Structured scores could not be parsed from the LLM response. "
            "Raw response is included for debugging.*"
        )

    report_data["toolCalls"] = middleware.tool_history

    # Emit completed status for Career Coach Agent
    await emit(send, "agent_completed", "Career coaching report complete.", 95,
               agent_id="coach", agent_name="Career Coach Agent", status="completed")

    await send(AgentEvent(
        type="final",
        message="Resume review complete — based on real parsed data.",
        progress=100,
        payload={"result": report_data, "toolCalls": middleware.tool_history},
    ))

    return report_data
