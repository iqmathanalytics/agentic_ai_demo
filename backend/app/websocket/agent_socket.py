from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.linkedin_agent import run_linkedin_agent
from app.agents.resume_agent import run_resume_agent
from app.agents.stock_agent import run_stock_agent
from app.database.sqlite import save_run
from app.models.schemas import AgentEvent, AgentRunRequest

router = APIRouter()

RUNNERS = {
    "stock": run_stock_agent,
    "resume": run_resume_agent,
    "linkedin": run_linkedin_agent,
}


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
            save_run(
                request.agent,
                request.credentials.provider,
                request.credentials.model,
                "failed",
                {"error": str(exc)},
            )
            await send(AgentEvent(type="run_failed", message=str(exc), progress=100, status="failed"))
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await send(AgentEvent(type="run_failed", message=str(exc), progress=100, status="failed"))
    finally:
        await websocket.close()

