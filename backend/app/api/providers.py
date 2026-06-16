from fastapi import APIRouter, HTTPException

from app.config.provider_models import get_providers_payload
from app.models.schemas import Credentials
from app.services.provider_test import test_provider

router = APIRouter()


@router.get("/providers")
async def providers():
    return get_providers_payload()


@router.post("/providers/test")
async def test_connection(credentials: Credentials):
    try:
        return await test_provider(credentials)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

