from __future__ import annotations

import logging
from typing import Any

from langchain.agents.middleware import AgentMiddleware

from app.utils.events import SendEvent, emit

logger = logging.getLogger(__name__)


class ToolEventMiddleware(AgentMiddleware):
    """Middleware that streams tool and LLM events to the WebSocket."""

    def __init__(
        self,
        send: SendEvent,
        agent_id: str,
        agent_name: str,
        tool_step_map: dict[str, tuple[str, str]] | None = None,
    ):
        super().__init__()
        self.send = send
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.tool_index = 0
        self.tool_history: list[dict] = []
        self.tool_step_map = tool_step_map or {}

    async def awrap_tool_call(self, request, handler):
        self.tool_index += 1
        tool_call = request.tool_call
        tool_name = tool_call.get("name", "unknown")
        tool_args = tool_call.get("args", {})

        step = self.tool_step_map.get(tool_name)
        step_id = step[0] if step else self.agent_id
        step_name = step[1] if step else self.agent_name

        logger.info("[Tool %s] args=%s", tool_name, tool_args)

        if step:
            await emit(
                self.send,
                "agent_started",
                f"Running {step_name}...",
                progress=0,
                agent_id=step_id,
                agent_name=step_name,
                status="running",
            )

        await emit(
            self.send,
            "tool_start",
            f"[Tool] {tool_name}",
            progress=0,
            agent_id=step_id,
            agent_name=step_name,
            payload={
                "tool": tool_name,
                "args": tool_args,
                "tool_index": self.tool_index,
            },
        )

        try:
            result = await handler(request)
            content = result.content if hasattr(result, "content") else str(result)
            self.tool_history.append({
                "tool_index": self.tool_index,
                "tool": tool_name,
                "args": tool_args,
                "result": str(content),
                "result_preview": str(content)[:500],
            })

            await emit(
                self.send,
                "tool_end",
                f"[Tool] Complete",
                progress=0,
                agent_id=step_id,
                agent_name=step_name,
                payload={"tool_index": self.tool_index, "tool": tool_name},
            )

            if step:
                await emit(
                    self.send,
                    "agent_completed",
                    f"{step_name} complete.",
                    progress=0,
                    agent_id=step_id,
                    agent_name=step_name,
                    status="completed",
                )

            return result
        except Exception as exc:
            logger.error("[Tool Error] %s: %s", tool_name, exc)
            await emit(
                self.send,
                "tool_error",
                f"[Tool] Error: {exc}",
                progress=0,
                agent_id=step_id,
                agent_name=step_name,
                payload={"error": str(exc), "tool": tool_name},
            )

            if step:
                await emit(
                    self.send,
                    "agent_failed",
                    f"{step_name} failed: {exc}",
                    progress=0,
                    agent_id=step_id,
                    agent_name=step_name,
                    status="failed",
                )
            raise

    async def awrap_model_call(self, request, handler):
        await emit(
            self.send,
            "llm_start",
            "LLM reasoning about data...",
            progress=0,
            agent_id=self.agent_id,
            agent_name=self.agent_name,
        )
        try:
            result = await handler(request)
            await emit(
                self.send,
                "llm_end",
                "LLM analysis complete.",
                progress=0,
                agent_id=self.agent_id,
                agent_name=self.agent_name,
            )
            return result
        except Exception as exc:
            logger.error("[LLM Error] %s", exc)
            await emit(
                self.send,
                "llm_end",
                f"LLM error: {exc}",
                progress=0,
                agent_id=self.agent_id,
                agent_name=self.agent_name,
            )
            raise
