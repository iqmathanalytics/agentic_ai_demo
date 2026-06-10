import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from app.models.schemas import AgentEvent

SendEvent = Callable[[AgentEvent], Awaitable[None]]


def stamp(message: str) -> str:
    return f"[{datetime.now().strftime('%H:%M:%S')}] {message}"


async def emit(send: SendEvent, event_type: str, message: str, progress: int, **kwargs: Any):
    await send(
        AgentEvent(
            type=event_type,
            message=stamp(message),
            progress=progress,
            **kwargs,
        )
    )


async def heartbeat(send: SendEvent, agent_id: str, agent_name: str, start: int, end: int, messages: list[str]):
    span = max(end - start, 1)
    for index, message in enumerate(messages):
        progress = min(end, start + round(span * ((index + 1) / max(len(messages), 1))))
        await emit(
            send,
            "agent_running",
            message,
            progress,
            agent_id=agent_id,
            agent_name=agent_name,
            status="running",
        )
        await asyncio.sleep(0.85)

