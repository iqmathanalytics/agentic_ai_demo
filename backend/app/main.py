from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.providers import router as providers_router
from app.websocket.agent_socket import router as websocket_router
from app.database.sqlite import init_db

app = FastAPI(title="IQ Math AI Agent Workspace", version="1.0.0")

import os

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
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

