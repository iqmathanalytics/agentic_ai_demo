"""Central catalog of LLM providers and models for the agent workspace."""

PROVIDER_MODELS: dict[str, dict] = {
    "openai": {
        "label": "OpenAI",
        "recommended": "gpt-4o-mini",
        "models": [
            {"id": "gpt-4o-mini", "label": "GPT-4o Mini", "free_tier": False},
            {"id": "gpt-4o", "label": "GPT-4o", "free_tier": False},
            {"id": "gpt-4.1-mini", "label": "GPT-4.1 Mini", "free_tier": False},
            {"id": "gpt-4.1", "label": "GPT-4.1", "free_tier": False},
        ],
    },
    "gemini": {
        "label": "Gemini",
        "recommended": "gemini-2.0-flash",
        "models": [
            {"id": "gemini-2.0-flash", "label": "Gemini 2.0 Flash", "free_tier": False},
            {"id": "gemini-1.5-flash", "label": "Gemini 1.5 Flash", "free_tier": False},
            {"id": "gemini-1.5-pro", "label": "Gemini 1.5 Pro", "free_tier": False},
        ],
    },
    "claude": {
        "label": "Claude",
        "recommended": "claude-3-5-haiku-latest",
        "models": [
            {"id": "claude-3-5-haiku-latest", "label": "Claude 3.5 Haiku", "free_tier": False},
            {"id": "claude-3-5-sonnet-latest", "label": "Claude 3.5 Sonnet", "free_tier": False},
            {"id": "claude-3-opus-latest", "label": "Claude 3 Opus", "free_tier": False},
        ],
    },
    "groq": {
        "label": "Groq",
        "recommended": "llama-3.3-70b-versatile",
        "models": [
            {"id": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B (Best quality)", "free_tier": True},
            {"id": "llama-3.1-8b-instant", "label": "Llama 3.1 8B (Fastest / highest limits)", "free_tier": True},
            {"id": "meta-llama/llama-4-scout-17b-16e-instruct", "label": "Llama 4 Scout 17B", "free_tier": True},
            {"id": "qwen/qwen3-32b", "label": "Qwen3 32B", "free_tier": True},
            {"id": "moonshotai/kimi-k2-instruct", "label": "Kimi K2 Instruct", "free_tier": True},
            {"id": "openai/gpt-oss-20b", "label": "GPT-OSS 20B", "free_tier": True},
            {"id": "openai/gpt-oss-120b", "label": "GPT-OSS 120B", "free_tier": True},
            {"id": "groq/compound", "label": "Groq Compound (experimental)", "free_tier": True},
        ],
    },
    "openrouter": {
        "label": "OpenRouter",
        "recommended": "openrouter/free",
        "models": [
            {"id": "openrouter/free", "label": "Free Models Router (recommended)", "free_tier": True},
            {"id": "meta-llama/llama-3.3-70b-instruct:free", "label": "Llama 3.3 70B Instruct", "free_tier": True},
            {"id": "deepseek/deepseek-r1:free", "label": "DeepSeek R1", "free_tier": True},
            {"id": "deepseek/deepseek-chat-v3-0324:free", "label": "DeepSeek V3", "free_tier": True},
            {"id": "meta-llama/llama-4-scout:free", "label": "Llama 4 Scout", "free_tier": True},
            {"id": "google/gemma-3-12b-it:free", "label": "Gemma 3 12B", "free_tier": True},
            {"id": "qwen/qwen3-4b:free", "label": "Qwen3 4B", "free_tier": True},
            {"id": "mistralai/mistral-small-3.1-24b-instruct:free", "label": "Mistral Small 24B", "free_tier": True},
            {"id": "openai/gpt-oss-20b:free", "label": "GPT-OSS 20B", "free_tier": True},
            {"id": "openai/gpt-oss-120b:free", "label": "GPT-OSS 120B", "free_tier": True},
        ],
    },
}


def get_providers_payload() -> dict:
    """API-friendly provider catalog."""
    providers = {}
    for provider_id, config in PROVIDER_MODELS.items():
        providers[provider_id] = {
            "label": config["label"],
            "recommended": config["recommended"],
            "models": config["models"],
            "model_ids": [m["id"] for m in config["models"]],
        }
    return {"providers": providers}
