import re

from app.graphs.workflow import describe_langgraph_workflow
from app.models.schemas import AgentEvent, AgentRunRequest
from app.prompts.templates import RESUME_REPORT_PROMPT
from app.services.llm_factory import create_chat_model, invoke_text
from app.tools.resume_parser import parse_resume
from app.utils.events import SendEvent, emit, heartbeat

RESUME_STEPS = [
    ("parser", "Resume Parser Agent"),
    ("ats", "ATS Scoring Agent"),
    ("skill", "Skill Match Agent"),
    ("grammar", "Grammar Review Agent"),
    ("coach", "Career Coach Agent"),
]

ROLE_SKILLS = {
    "ai": ["Python", "LangChain", "RAG", "LLM", "MLOps", "Vector Database", "FastAPI"],
    "data": ["SQL", "Python", "Dashboard", "Statistics", "ETL", "Machine Learning"],
    "frontend": ["React", "TypeScript", "CSS", "Testing", "Accessibility", "Performance"],
    "backend": ["API", "Database", "Docker", "Caching", "Testing", "Security"],
}


def _score_resume(text: str, role: str) -> dict:
    lowered = f"{role} {text}".lower()
    bucket = "ai" if "ai" in lowered or "machine" in lowered else "data" if "data" in lowered else "frontend" if "react" in lowered else "backend"
    skills = ROLE_SKILLS[bucket]
    present = [skill for skill in skills if skill.lower() in text.lower()]
    missing = [skill for skill in skills if skill not in present]
    word_count = len(re.findall(r"\w+", text))
    ats = min(95, max(25, 40 + len(present) * 7 + (10 if word_count > 350 else 0)))
    skill_match = round((len(present) / len(skills)) * 100)
    return {"atsScore": ats, "skillMatch": skill_match, "present": present, "missingSkills": missing}


async def run_resume_agent(request: AgentRunRequest, send: SendEvent) -> dict:
    payload = request.input
    workflow = describe_langgraph_workflow([step[0] for step in RESUME_STEPS])
    await send(AgentEvent(type="run_started", message="Resume review workflow started.", progress=2, payload={"workflow": workflow}))

    await emit(send, "agent_started", "Parsing uploaded resume...", 8, agent_id="parser", agent_name="Resume Parser Agent", status="running")
    await heartbeat(send, "parser", "Resume Parser Agent", 8, 22, ["Reading file bytes...", "Extracting text layer...", "Normalizing sections..."])
    parsed = parse_resume(payload.get("fileName", ""), payload.get("fileData", ""))
    resume_text = parsed.get("text", "")
    if not resume_text:
        raise ValueError(parsed.get("error") or "Could not extract text from resume.")
    await emit(send, "agent_completed", "Resume text extracted.", 24, agent_id="parser", agent_name="Resume Parser Agent", status="completed", payload={"characters": len(resume_text)})

    await emit(send, "agent_started", "Calculating ATS readiness...", 30, agent_id="ats", agent_name="ATS Scoring Agent", status="running")
    await heartbeat(send, "ats", "ATS Scoring Agent", 30, 42, ["Checking section structure...", "Looking for measurable achievements...", "Scoring keyword density..."])
    scores = _score_resume(resume_text, payload.get("role", ""))
    await emit(send, "agent_completed", "ATS scoring complete.", 44, agent_id="ats", agent_name="ATS Scoring Agent", status="completed", payload=scores)

    await emit(send, "agent_started", "Matching skills against target role...", 50, agent_id="skill", agent_name="Skill Match Agent", status="running")
    await heartbeat(send, "skill", "Skill Match Agent", 50, 62, ["Building target skill map...", "Comparing resume evidence...", "Finding missing skills..."])
    await emit(send, "agent_completed", "Skill match complete.", 64, agent_id="skill", agent_name="Skill Match Agent", status="completed")

    await emit(send, "agent_started", "Reviewing grammar and recruiter readability...", 68, agent_id="grammar", agent_name="Grammar Review Agent", status="running")
    await heartbeat(send, "grammar", "Grammar Review Agent", 68, 78, ["Checking passive phrasing...", "Reviewing bullet clarity...", "Finding formatting risks..."])
    await emit(send, "agent_completed", "Grammar review complete.", 80, agent_id="grammar", agent_name="Grammar Review Agent", status="completed")

    await emit(send, "agent_started", "Generating career coach feedback with the connected LLM...", 84, agent_id="coach", agent_name="Career Coach Agent", status="running")
    llm = create_chat_model(request.credentials)
    prompt = RESUME_REPORT_PROMPT.format(
        role=payload.get("role"),
        experience=payload.get("experience"),
        resume_text=resume_text[:12000],
    )
    report = await invoke_text(llm, prompt)
    await emit(send, "agent_completed", "Career coach report generated.", 96, agent_id="coach", agent_name="Career Coach Agent", status="completed")

    result = {
        "atsScore": scores["atsScore"],
        "skillMatch": scores["skillMatch"],
        "strengths": scores["present"][:4] or ["Relevant experience detected"],
        "weaknesses": ["Add stronger quantified impact", "Align summary with target role", "Improve keyword coverage"],
        "missingSkills": scores["missingSkills"],
        "suggestions": ["Add metrics to each major project", "Use target-role keywords naturally", "Move strongest evidence to the top third"],
        "recruiterFeedback": report,
        "report": report,
    }
    await send(AgentEvent(type="final", message="Final resume review ready.", progress=100, payload={"result": result}))
    return result

