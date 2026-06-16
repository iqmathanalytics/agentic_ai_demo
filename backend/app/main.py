import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.providers import router as providers_router
from app.database.sqlite import init_db
from app.websocket.agent_socket import router as websocket_router

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(title="Nexperts Academy AI Agent Workspace", version="1.0.0")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=allowed_origins != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(providers_router, prefix="/api")
app.include_router(websocket_router)


@app.on_event("startup")
async def on_startup():
    init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}

