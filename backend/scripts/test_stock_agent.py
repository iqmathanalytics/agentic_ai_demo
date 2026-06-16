"""Test stock agent with Groq and OpenRouter free models."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.agents.stock_agent import run_stock_agent
from app.models.schemas import AgentRunRequest, Credentials


async def _collect(send):
    events = []

    async def capture(event):
        events.append(event)
        if event.message:
            print(f"  [{event.progress:3d}%] {event.type}: {event.message[:80]}")

    return events, capture


def _assert_result(result: dict, label: str):
    rec = result.get("recommendation") or {}
    assert result.get("currentPrice") or (result.get("valuation") or {}).get("Current Price"), f"{label}: missing price"
    assert rec.get("recommendation") in ("BUY", "HOLD", "SELL"), f"{label}: bad recommendation {rec}"
    assert (rec.get("confidence") or 0) > 0, f"{label}: confidence is 0"
    assert result.get("dataCompleteness", 0) > 30, f"{label}: low completeness {result.get('dataCompleteness')}"
    print(f"  OK {label}: {rec['recommendation']} @ {rec['confidence']}% | completeness={result.get('dataCompleteness')}%")


async def test_provider(provider: str, model: str, api_key: str, symbol: str, exchange: str, name: str):
    if not api_key:
        print(f"SKIP {provider}/{model} — no API key")
        return

    print(f"\n=== Testing {provider}/{model} — {name} ({symbol}.{exchange}) ===")
    events, capture = await _collect(None)

    request = AgentRunRequest(
        agent="stock",
        credentials=Credentials(provider=provider, model=model, api_key=api_key),
        input={"symbol": symbol, "exchange": exchange, "name": name},
    )

    result = await run_stock_agent(request, capture)
    _assert_result(result, f"{provider}/{model}")
    return result


async def main():
    groq_key = os.getenv("TEST_GROQ_API_KEY", "")
    or_key = os.getenv("TEST_OPENROUTER_API_KEY", "")

    tests = [
        ("groq", "llama-3.3-70b-versatile", groq_key, "RELIANCE", "NSE", "Reliance Industries"),
        ("openrouter", "openrouter/free", or_key, "AAPL", "NASDAQ", "Apple Inc"),
    ]

    for args in tests:
        try:
            await test_provider(*args)
        except Exception as exc:
            print(f"  FAIL: {exc}")
            raise

    print("\nAll stock agent tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
