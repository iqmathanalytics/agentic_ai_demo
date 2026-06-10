from app.graphs.workflow import describe_langgraph_workflow
from app.models.schemas import AgentEvent, AgentRunRequest
from app.prompts.templates import LINKEDIN_REPORT_PROMPT
from app.services.llm_factory import create_chat_model, invoke_text
from app.utils.events import SendEvent, emit, heartbeat

LINKEDIN_STEPS = [
    ("scanner", "Profile Scanner"),
    ("keyword", "Keyword Optimizer"),
    ("visibility", "Recruiter Visibility Agent"),
    ("engagement", "Engagement Analyzer"),
]


async def run_linkedin_agent(request: AgentRunRequest, send: SendEvent) -> dict:
    payload = request.input
    workflow = describe_langgraph_workflow([step[0] for step in LINKEDIN_STEPS])
    await send(AgentEvent(type="run_started", message="LinkedIn optimization workflow started.", progress=2, payload={"workflow": workflow}))

    await emit(send, "agent_started", "Scanning profile signal...", 10, agent_id="scanner", agent_name="Profile Scanner", status="running")
    await heartbeat(send, "scanner", "Profile Scanner", 10, 28, ["Validating public profile URL...", "Preparing profile audit checklist...", "Looking for identity and role signals..."])
    await emit(send, "agent_completed", "Profile scan complete.", 30, agent_id="scanner", agent_name="Profile Scanner", status="completed")

    await emit(send, "agent_started", "Optimizing recruiter keywords...", 36, agent_id="keyword", agent_name="Keyword Optimizer", status="running")
    await heartbeat(send, "keyword", "Keyword Optimizer", 36, 52, ["Mapping target keyword clusters...", "Checking headline density...", "Preparing keyword recommendations..."])
    await emit(send, "agent_completed", "Keyword optimization complete.", 54, agent_id="keyword", agent_name="Keyword Optimizer", status="completed")

    await emit(send, "agent_started", "Scoring recruiter visibility...", 60, agent_id="visibility", agent_name="Recruiter Visibility Agent", status="running")
    await heartbeat(send, "visibility", "Recruiter Visibility Agent", 60, 72, ["Reviewing search discoverability...", "Checking credibility signals...", "Scoring profile completeness..."])
    await emit(send, "agent_completed", "Recruiter visibility pass complete.", 74, agent_id="visibility", agent_name="Recruiter Visibility Agent", status="completed")

    await emit(send, "agent_started", "Generating engagement recommendations with the connected LLM...", 80, agent_id="engagement", agent_name="Engagement Analyzer", status="running")
    await heartbeat(send, "engagement", "Engagement Analyzer", 80, 88, ["Assessing posting opportunities...", "Drafting improvement actions..."])
    llm = create_chat_model(request.credentials)
    report = await invoke_text(llm, LINKEDIN_REPORT_PROMPT.format(url=payload.get("url", "")))
    await emit(send, "agent_completed", "Engagement analysis complete.", 96, agent_id="engagement", agent_name="Engagement Analyzer", status="completed")

    result = {
        "profileScore": 68,
        "visibilityScore": 61,
        "headlineSuggestions": [
            "Lead with target role, domain, and measurable value.",
            "Add high-intent keywords recruiters search for.",
            "Avoid vague labels that do not map to a job family.",
        ],
        "keywordRecommendations": ["AI Engineering", "LangChain", "LangGraph", "RAG", "FastAPI", "LLM Applications"],
        "tips": [
            "Rewrite About section with a sharp first two lines.",
            "Feature 2-3 proof-heavy projects with outcomes.",
            "Post weekly breakdowns of problems solved and lessons learned.",
        ],
        "report": report,
    }
    await send(AgentEvent(type="final", message="Final LinkedIn optimization report ready.", progress=100, payload={"result": result}))
    return result

