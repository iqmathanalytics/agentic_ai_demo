from typing import Any, Literal

from pydantic import BaseModel, Field

Provider = Literal["openai", "gemini", "claude", "openrouter", "groq"]
AgentKind = Literal["stock", "resume", "linkedin"]
EventType = Literal[
    "run_started",
    "agent_started",
    "agent_running",
    "agent_completed",
    "agent_failed",
    "tool_start",
    "tool_end",
    "tool_error",
    "llm_start",
    "llm_end",
    "log",
    "token",
    "metric",
    "final",
    "run_failed",
    "run_completed",
]


class Credentials(BaseModel):
    provider: Provider
    model: str
    api_key: str = Field(min_length=6)


class AgentRunRequest(BaseModel):
    agent: AgentKind
    credentials: Credentials
    input: dict[str, Any]


class AgentEvent(BaseModel):
    type: EventType
    agent_id: str | None = None
    agent_name: str | None = None
    status: str | None = None
    message: str | None = None
    progress: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)

