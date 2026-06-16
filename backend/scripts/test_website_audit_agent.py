"""Test website audit agent logic on a public URL."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tools.website_audit_tools import run_website_audit


async def main():
    url = "https://www.nexpertsai.com/"
    result = await run_website_audit(url)

    assert result.get("url"), "Missing url"
    assert "scores" in result, "Missing scores"
    assert "issues" in result, "Missing issues"
    assert "suggestions" in result, "Missing suggestions"

    print(json.dumps(result, indent=2))
    print("\nWebsite audit test passed.")


if __name__ == "__main__":
    asyncio.run(main())

