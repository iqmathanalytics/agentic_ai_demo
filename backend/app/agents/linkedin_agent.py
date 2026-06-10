from __future__ import annotations

import logging

from langchain.agents import create_agent

from app.agents.handlers import ToolEventMiddleware
from app.graphs.workflow import describe_langgraph_workflow
from app.models.schemas import AgentEvent, AgentRunRequest
from app.prompts.templates import LINKEDIN_AGENT_SYSTEM_PROMPT
from app.services.llm_factory import create_chat_model
from app.tools.linkedin_tools import analyze_profile, optimize_keywords, score_recruiter_visibility
from app.utils.events import SendEvent, emit

logger = logging.getLogger(__name__)

LINKEDIN_TOOLS = [
    analyze_profile,
    optimize_keywords,
    score_recruiter_visibility,
]


async def run_linkedin_agent(request: AgentRunRequest, send: SendEvent) -> dict:
    payload = request.input
    profile_url = payload.get("url", "")
    target_role = payload.get("targetRole", payload.get("role", "Software Engineer"))
    profile_text = payload.get("profileText", payload.get("profile", profile_url))

    workflow = describe_langgraph_workflow([t.name for t in LINKEDIN_TOOLS])
    await send(AgentEvent(
        type="run_started",
        message=f"LinkedIn profile optimization started for role: {target_role}.",
        progress=2,
        payload={"workflow": workflow, "tools": [t.name for t in LINKEDIN_TOOLS]},
    ))

    llm = create_chat_model(request.credentials)
    middleware = ToolEventMiddleware(send, "linkedin_strategist", "LinkedIn Optimization Agent")

    agent = create_agent(
        model=llm,
        tools=LINKEDIN_TOOLS,
        system_prompt=LINKEDIN_AGENT_SYSTEM_PROMPT,
        middleware=[middleware],
        name="linkedin_strategist",
    )

    user_query = (
        f"Optimize this LinkedIn profile for a {target_role} position.\n\n"
        f"Profile information: {profile_text}\n"
        f"Profile URL: {profile_url}\n\n"
        f"First, call analyze_profile to assess the profile. "
        f"Then call optimize_keywords with the profile text and target role. "
        f"Then call score_recruiter_visibility.\n\n"
        f"After gathering all tool results, provide a complete optimization report.\n\n"
        f"If any tool returns an error, report it and stop. Do not fabricate scores."
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
        logger.error("LinkedIn agent execution failed: %s", exc, exc_info=True)
        error_result = {
            "error": str(exc),
            "report": f"## LinkedIn Optimization Failed\n\n**Error:** {exc}\n\nTool-based analysis could not complete.",
            "toolCalls": middleware.tool_history,
        }
        await send(AgentEvent(
            type="agent_failed",
            message=f"[Error] {exc}",
            progress=100,
            agent_id="linkedin_strategist",
            agent_name="LinkedIn Optimization Agent",
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
        message="LinkedIn optimization complete — based on profile analysis.",
        progress=100,
        payload={"result": report_data, "toolCalls": middleware.tool_history},
    ))

    return report_data
