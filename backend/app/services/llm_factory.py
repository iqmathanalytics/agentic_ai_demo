from app.models.schemas import Credentials

FREE_TIER_PROVIDERS = {"groq", "openrouter"}


def create_chat_model(credentials: Credentials, max_tokens: int | None = None, streaming: bool = True):
    provider = credentials.provider.lower()
    if not getattr(credentials, "api_key", ""):
        raise ValueError(f"Missing API key for provider '{credentials.provider}'.")
    if max_tokens is None:
        max_tokens = 1500 if provider in FREE_TIER_PROVIDERS else 4000

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=credentials.model,
            api_key=credentials.api_key,
            temperature=0.2,
            streaming=streaming,
            max_tokens=max_tokens,
        )
    if provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=credentials.model,
            api_key=credentials.api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.2,
            streaming=streaming,
            max_tokens=max_tokens,
            default_headers={
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "Nexperts Academy AI Agent Workspace",
            },
        )
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=credentials.model,
            google_api_key=credentials.api_key,
            temperature=0.2,
            streaming=streaming,
            max_tokens=max_tokens,
        )
    if provider == "claude":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=credentials.model,
            api_key=credentials.api_key,
            temperature=0.2,
            streaming=streaming,
            max_tokens=max_tokens,
        )
    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            groq_api_key=credentials.api_key,
            model_name=credentials.model,
            temperature=0.2,
            streaming=streaming,
            max_tokens=max_tokens,
        )
    raise ValueError(f"Unsupported provider: {credentials.provider}")


async def invoke_text(llm, prompt: str) -> str:
    response = await llm.ainvoke(prompt)
    content = getattr(response, "content", response)
    if isinstance(content, list):
        return "\n".join(str(part.get("text", part)) if isinstance(part, dict) else str(part) for part in content)
    return str(content)
