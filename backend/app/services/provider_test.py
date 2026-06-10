from app.models.schemas import Credentials
from app.services.llm_factory import create_chat_model, invoke_text


async def test_provider(credentials: Credentials) -> dict:
    llm = create_chat_model(credentials)
    text = await invoke_text(llm, "Reply with exactly: connected")
    return {
        "ok": "connected" in text.lower(),
        "message": text.strip()[:200],
    }

