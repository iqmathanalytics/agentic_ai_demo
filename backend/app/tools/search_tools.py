import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def perform_search(query: str, search_type: str = "general") -> str:
    """Fallback search tool using Tavily -> Serper -> Brave"""
    # 1. Try Tavily
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults
            tool = TavilySearchResults(max_results=5)
            res = tool.invoke({"query": query})
            if res:
                return json.dumps(res)
        except Exception as e:
            logger.warning(f"Tavily search failed: {e}")

    # 2. Try Serper
    serper_key = os.getenv("SERPER_API_KEY")
    if serper_key:
        try:
            import httpx
            url = "https://google.serper.dev/search"
            payload = json.dumps({"q": query})
            headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
            response = httpx.post(url, headers=headers, data=payload)
            return json.dumps(response.json().get("organic", [])[:5])
        except Exception as e:
            logger.warning(f"Serper search failed: {e}")
            
    # 3. DuckDuckGo as absolute fallback (if others fail)
    try:
        from langchain_community.tools import DuckDuckGoSearchResults
        tool = DuckDuckGoSearchResults()
        return tool.invoke(query)
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return json.dumps([{"error": "All search providers failed."}])

