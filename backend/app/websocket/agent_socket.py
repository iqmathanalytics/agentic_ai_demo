import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.linkedin_agent import run_linkedin_agent
from app.agents.resume_agent import run_resume_agent
from app.agents.stock_agent import run_stock_agent
from app.database.sqlite import save_run
from app.models.schemas import AgentEvent, AgentRunRequest

logger = logging.getLogger(__name__)

router = APIRouter()

RUNNERS = {
    "stock": run_stock_agent,
    "resume": run_resume_agent,
    "linkedin": run_linkedin_agent,
}

_USER_402_MESSAGE = (
    "This analysis requires more credits than your current plan allows. "
    "The agent automatically retried with a reduced token budget. "
    "If the error persists, try a smaller input or a different model."
)


def _friendly_error(exc: Exception) -> str:
    exc_str = str(exc)
    if "402" in exc_str or "insufficient credits" in exc_str.lower() or "max_tokens" in exc_str.lower():
        logger.warning("402/credit error caught in websocket handler: %s", exc_str)
        return _USER_402_MESSAGE
    return exc_str


@router.websocket("/ws/agents")
async def agent_socket(websocket: WebSocket):
    await websocket.accept()

    async def send(event: AgentEvent):
        await websocket.send_json(event.model_dump())

    try:
        payload = await websocket.receive_json()
        request = AgentRunRequest.model_validate(payload)
        runner = RUNNERS[request.agent]
        try:
            result = await runner(request, send)
            save_run(
                request.agent,
                request.credentials.provider,
                request.credentials.model,
                "completed",
                result,
            )
            await send(AgentEvent(type="run_completed", message="Agent workflow completed.", progress=100, payload={"result": result}))
        except Exception as exc:
            error_msg = _friendly_error(exc)
            logger.error("Agent execution error for %s: %s", request.agent, exc, exc_info=True)
            save_run(
                request.agent,
                request.credentials.provider,
                request.credentials.model,
                "failed",
                {"error": error_msg},
            )
            await send(AgentEvent(type="run_failed", message=error_msg, progress=100, status="failed"))
    except WebSocketDisconnect:
        return
    except Exception as exc:
        error_msg = _friendly_error(exc)
        logger.error("Websocket error: %s", exc, exc_info=True)
        await send(AgentEvent(type="run_failed", message=error_msg, progress=100, status="failed"))
    finally:
        await websocket.close()
