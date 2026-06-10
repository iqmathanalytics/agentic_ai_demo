from __future__ import annotations

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
    parse_resume,
    score_ats_compatibility,
    match_skills,
    review_grammar,
]


async def run_resume_agent(request: AgentRunRequest, send: SendEvent) -> dict:
    payload = request.input
    file_name = payload.get("fileName", "")
    file_data = payload.get("fileData", "")
    role = payload.get("role", "")
    experience = payload.get("experience", "")

    workflow = describe_langgraph_workflow([t.name for t in RESUME_TOOLS])
    await send(AgentEvent(
        type="run_started",
        message=f"Resume review started for role: {role}.",
        progress=2,
        payload={"workflow": workflow, "tools": [t.name for t in RESUME_TOOLS]},
    ))

    llm = create_chat_model(request.credentials)
    middleware = ToolEventMiddleware(send, "resume_coach", "Resume Review Agent")

    agent = create_agent(
        model=llm,
        tools=RESUME_TOOLS,
        system_prompt=RESUME_AGENT_SYSTEM_PROMPT,
        middleware=[middleware],
        name="resume_coach",
    )

    file_data_short = (file_data[:200] + "...") if len(file_data) > 200 else file_data
    user_query = (
        f"Review this resume for a {role} position (experience level: {experience}).\n\n"
        f"The file is named '{file_name}' and its base64 data is: {file_data_short}\n\n"
        f"First, call parse_resume with the file name and the full base64 data to extract text. "
        f"If it fails, report the error and stop.\n\n"
        f"Then use the extracted text to call score_ats_compatibility, match_skills, and review_grammar. "
        f"After gathering all tool results, provide a complete career coaching report."
    )

    try:
        result = await agent.ainvoke({"messages": [("human", user_query)]})
        messages = result.get("messages", [])
        output_text = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content and hasattr(msg, "type") and msg.type == "ai":
                output_text = msg.content
                break
    except Exception as exc:
        logger.error("Resume agent execution failed: %s", exc, exc_info=True)
        error_result = {
            "error": str(exc),
            "report": f"## Resume Review Failed\n\n**Error:** {exc}\n\nTool-based analysis could not complete.",
            "toolCalls": middleware.tool_history,
        }
        await send(AgentEvent(
            type="agent_failed",
            message=f"[Error] {exc}",
            progress=100,
            agent_id="resume_coach",
            agent_name="Resume Review Agent",
            status="failed",
            payload={"error": str(exc), "toolCalls": middleware.tool_history},
        ))
        return error_result

    report_data = {
        "report": output_text,
        "toolCalls": middleware.tool_history,
    }

    await send(AgentEvent(
        type="final",
        message="Resume review complete — based on real parsed data.",
        progress=100,
        payload={"result": report_data, "toolCalls": middleware.tool_history},
    ))

    return report_data
