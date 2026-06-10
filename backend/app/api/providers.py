from fastapi import APIRouter, HTTPException

from app.models.schemas import Credentials
from app.services.provider_test import test_provider

router = APIRouter()


@router.get("/providers")
async def providers():
    return {
        "providers": {
            "openai": ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "gpt-4o"],
            "gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
            "claude": ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-latest"],
            "openrouter": [
                "openai/gpt-4o-mini",
                "anthropic/claude-3.5-sonnet",
                "google/gemini-flash-1.5",
                "meta-llama/llama-3.1-70b-instruct",
            ],
        }
    }


@router.post("/providers/test")
async def test_connection(credentials: Credentials):
    try:
        return await test_provider(credentials)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

