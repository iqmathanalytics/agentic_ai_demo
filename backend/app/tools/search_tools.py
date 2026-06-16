import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _dedupe_results(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for item in items:
        title = (item.get("title") or item.get("name") or item.get("snippet") or "")[:80].lower()
        if title and title not in seen:
            seen.add(title)
            unique.append(item)
    return unique


def _tavily_search(query: str, search_type: str = "general") -> list[dict]:
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        return []
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults

        topic = "news" if search_type == "news" else "general"
        tool = TavilySearchResults(max_results=5, search_depth="advanced", include_answer=False)
        res = tool.invoke({"query": query, "topic": topic})
        if not res:
            return []
        normalized = []
        for item in res if isinstance(res, list) else [res]:
            if isinstance(item, dict):
                normalized.append({
                    "source": "Tavily",
                    "title": item.get("title", ""),
                    "snippet": item.get("content") or item.get("snippet", ""),
                    "url": item.get("url", ""),
                    "date": item.get("published_date", ""),
                })
        return normalized
    except Exception as e:
        logger.warning("Tavily search failed: %s", e)
        return []


def _serper_search(query: str, search_type: str = "general") -> list[dict]:
    serper_key = os.getenv("SERPER_API_KEY")
    if not serper_key:
        return []
    try:
        import httpx

        endpoint = "https://google.serper.dev/news" if search_type == "news" else "https://google.serper.dev/search"
        payload = json.dumps({"q": query, "num": 8})
        headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}
        response = httpx.post(endpoint, headers=headers, data=payload, timeout=15)
        data = response.json()
        key = "news" if search_type == "news" else "organic"
        items = data.get(key, [])[:8]
        return [
            {
                "source": "Serper",
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("link", ""),
                "date": item.get("date", ""),
            }
            for item in items
        ]
    except Exception as e:
        logger.warning("Serper search failed: %s", e)
        return []


def _duckduckgo_search(query: str) -> list[dict]:
    try:
        from langchain_community.tools import DuckDuckGoSearchResults

        tool = DuckDuckGoSearchResults()
        res = tool.invoke(query)
        if isinstance(res, str):
            return [{"source": "DuckDuckGo", "title": query, "snippet": res[:500]}]
        return [{"source": "DuckDuckGo", "snippet": str(res)[:500]}]
    except Exception as e:
        logger.error("DuckDuckGo search failed: %s", e)
        return []


def perform_search(query: str, search_type: str = "general") -> str:
    """Multi-source search: Tavily + Serper merged, DuckDuckGo fallback."""
    results: list[dict] = []
    results.extend(_tavily_search(query, search_type))
    results.extend(_serper_search(query, search_type))
    results = _dedupe_results(results)

    if not results:
        results = _duckduckgo_search(query)

    if not results:
        return json.dumps([{"error": "All search providers failed.", "source": "none"}])

    return json.dumps(results)


def get_search_sources_used() -> list[str]:
    sources = []
    if os.getenv("TAVILY_API_KEY"):
        sources.append("Tavily")
    if os.getenv("SERPER_API_KEY"):
        sources.append("Serper")
    if not sources:
        sources.append("DuckDuckGo")
    return sources
