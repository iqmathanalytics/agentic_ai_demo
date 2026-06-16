from __future__ import annotations

import base64
import io
import json
import logging

from pydantic import BaseModel, Field
from langchain_core.tools import tool

from app.tools.resume_scoring import (
    match_skills_analysis,
    normalize_resume_text,
    review_grammar_analysis,
    score_ats,
)

logger = logging.getLogger(__name__)


class AtsScoreOutput(BaseModel):
    atsScore: int = Field(description="ATS compatibility score 0-100")
    wordCount: int = Field(description="Word count of resume")
    hasContactInfo: bool = False
    hasStandardSections: bool = False
    keywordMatchPct: int = 0
    matchedKeywords: list[str] = Field(default_factory=list)
    scoreBreakdown: dict = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)


class SkillMatchOutput(BaseModel):
    skillMatch: int = Field(description="Skill match percentage 0-100")
    presentSkills: list[str] = Field(default_factory=list)
    missingSkills: list[str] = Field(default_factory=list)
    resumeSkills: list[str] = Field(default_factory=list)
    detectedRole: str = ""
    roleBucket: str = ""
    suggestions: list[str] = Field(default_factory=list)


class GrammarReviewOutput(BaseModel):
    passiveVoiceRatio: float = 0.0
    weakPhrasesFound: int = 0
    totalSentences: int = 0
    suggestions: list[str] = Field(default_factory=list)


@tool
def parse_resume(file_name: str, file_data: str) -> str:
    """Extract text from an uploaded resume file (PDF or DOCX).

    Provide the file name and the base64-encoded data. Returns the full text content.
    """
    try:
        raw = base64.b64decode(file_data.split(",")[-1])
    except Exception as exc:
        return json.dumps({"error": f"Could not decode file data: {exc}", "available": False})

    lower_name = file_name.lower()
    try:
        if lower_name.endswith(".pdf"):
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(raw))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            text = normalize_resume_text(text.strip())
            result = {
                "available": True,
                "text": text,
                "pages": len(reader.pages),
                "characters": len(text),
            }
            logger.info("parse_resume: extracted %d chars from PDF (%d pages)", result["characters"], result["pages"])
            return json.dumps(result)
        if lower_name.endswith(".docx"):
            from docx import Document

            document = Document(io.BytesIO(raw))
            text = normalize_resume_text("\n".join(paragraph.text for paragraph in document.paragraphs).strip())
            result = {"available": True, "text": text, "pages": None, "characters": len(text)}
            logger.info("parse_resume: extracted %d chars from DOCX", result["characters"])
            return json.dumps(result)
    except Exception as exc:
        return json.dumps({"error": f"Parse error: {exc}", "available": False})

    return json.dumps({"error": "Unsupported file type. Use PDF or DOCX.", "available": False})


@tool
def score_ats_compatibility(resume_text: str, role: str, job_description: str = "") -> str:
    """Score the resume for ATS (Applicant Tracking System) compatibility.

    Analyzes structure, keyword density, word count, and section completeness.
    Provide the raw resume text, the target role, and an optional job description.
    """
    result = score_ats(resume_text, role, job_description)
    logger.info("score_ats_compatibility: score=%s words=%s keywords=%s%%",
                result["atsScore"], result["wordCount"], result.get("keywordMatchPct"))
    return json.dumps(result)


@tool
def match_skills(resume_text: str, role: str, job_description: str = "") -> str:
    """Match skills in the resume against the target role requirements.

    Identifies present skills, missing skills, and computes a skill match percentage.
    Provide the resume text, the target role, and an optional job description.
    """
    result = match_skills_analysis(resume_text, role, job_description)
    logger.info("match_skills: match=%s%% present=%d missing=%d bucket=%s",
                result["skillMatch"], len(result["presentSkills"]),
                len(result["missingSkills"]), result.get("roleBucket"))
    return json.dumps(result)


@tool
def review_grammar(resume_text: str) -> str:
    """Review resume text for grammar issues, passive voice, and clarity.

    Provides a basic style and grammar assessment.
    """
    result = review_grammar_analysis(resume_text)
    logger.info("review_grammar: passive=%s%% weak=%d sentences=%d",
                result["passiveVoiceRatio"], result["weakPhrasesFound"], result["totalSentences"])
    return json.dumps(result)
