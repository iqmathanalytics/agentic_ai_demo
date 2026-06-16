"""Test resume agent with a local PDF file."""

import asyncio
import base64
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.agents.resume_agent import run_resume_agent
from app.models.schemas import AgentRunRequest, Credentials


async def _collect():
    events = []

    async def capture(event):
        events.append(event)
        if event.message:
            print(f"  [{event.progress:3d}%] {event.type}: {event.message[:70]}")

    return events, capture


async def main():
    pdf = Path(__file__).resolve().parents[2] / "Hariprathap A Resume Nexperts.pdf"
    if not pdf.exists():
        print(f"Resume not found: {pdf}")
        return

    api_key = os.getenv("TEST_GROQ_API_KEY", "")
    if not api_key:
        print("Set TEST_GROQ_API_KEY to run full agent test")
        return

    b64 = base64.b64encode(pdf.read_bytes()).decode()
    events, capture = await _collect()

    request = AgentRunRequest(
        agent="resume",
        credentials=Credentials(provider="groq", model="llama-3.3-70b-versatile", api_key=api_key),
        input={
            "fileName": pdf.name,
            "fileData": f"data:application/pdf;base64,{b64}",
            "role": "DevOps Engineer",
            "experience": "Experienced",
            "jobDescription": "",
        },
    )

    print(f"\n=== Resume Agent Test: {pdf.name} / DevOps Engineer ===")
    result = await run_resume_agent(request, capture)

    assert result.get("atsScore") is not None, "Missing ATS score"
    assert result.get("skillMatch") is not None, "Missing skill match"
    assert result.get("report"), "Missing report"

    print(f"\n  ATS Score: {result['atsScore']}")
    print(f"  Skill Match: {result['skillMatch']}%")
    print(f"  Strengths: {result.get('strengths', [])}")
    print(f"  Missing: {result.get('missingSkills', [])[:5]}")
    print(f"  Suggestions: {len(result.get('suggestions', []))}")

    out = Path(__file__).parent / "_resume_agent_result.json"
    out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nFull result saved to {out}")
    print("Resume agent test passed.")


if __name__ == "__main__":
    asyncio.run(main())
