import asyncio
import logging
import traceback
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from app.models.schemas import AgentEvent

logger = logging.getLogger(__name__)

SendEvent = Callable[[AgentEvent], Awaitable[None]]


def stamp(message: str) -> str:
    return f"[{datetime.now().strftime('%H:%M:%S')}] {message}"


async def emit(send: SendEvent, event_type: str, message: str, progress: int = 0, **kwargs: Any):
    if progress is None:
        progress = 0
    try:
        await send(
            AgentEvent(
                type=event_type,
                message=stamp(message),
                progress=progress,
                **kwargs,
            )
        )
    except Exception as exc:
        logger.warning("emit failed (non-fatal): %s\n%s", exc, traceback.format_exc())


async def heartbeat(send: SendEvent, agent_id: str, agent_name: str, start: int, end: int, messages: list[str]):
    span = max(end - start, 1)
    for index, message in enumerate(messages):
        p = min(end, start + round(span * ((index + 1) / max(len(messages), 1))))
        await emit(
            send,
            "agent_running",
            message,
            p,
            agent_id=agent_id,
            agent_name=agent_name,
            status="running",
        )
        await asyncio.sleep(0.85)
