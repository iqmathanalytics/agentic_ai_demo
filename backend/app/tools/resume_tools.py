from __future__ import annotations

import base64
import io
import json
import logging
import re

from pydantic import BaseModel, Field
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


class AtsScoreOutput(BaseModel):
    atsScore: int = Field(description="ATS compatibility score 0-100")
    wordCount: int = Field(description="Word count of resume")
    hasContactInfo: bool = False
    hasStandardSections: bool = False
    issues: list[str] = Field(default_factory=list)


class SkillMatchOutput(BaseModel):
    skillMatch: int = Field(description="Skill match percentage 0-100")
    presentSkills: list[str] = Field(default_factory=list)
    missingSkills: list[str] = Field(default_factory=list)
    detectedRole: str = ""


class GrammarReviewOutput(BaseModel):
    passiveVoiceRatio: float = 0.0
    weakPhrasesFound: int = 0
    totalSentences: int = 0
    suggestions: list[str] = Field(default_factory=list)

ROLE_SKILLS = {
    "ai": ["Python", "LangChain", "RAG", "LLM", "MLOps", "Vector Database", "FastAPI"],
    "data": ["SQL", "Python", "Dashboard", "Statistics", "ETL", "Machine Learning"],
    "frontend": ["React", "TypeScript", "CSS", "Testing", "Accessibility", "Performance"],
    "backend": ["API", "Database", "Docker", "Caching", "Testing", "Security"],
}


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
            result = {"available": True, "text": text.strip(), "pages": len(reader.pages), "characters": len(text.strip())}
            logger.info("parse_resume: extracted %d chars from PDF", result["characters"])
            return json.dumps(result)
        if lower_name.endswith(".docx"):
            from docx import Document

            document = Document(io.BytesIO(raw))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
            result = {"available": True, "text": text.strip(), "pages": None, "characters": len(text.strip())}
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
    word_count = len(re.findall(r"\w+", resume_text))
    has_email = bool(re.search(r"\S+@\S+", resume_text))
    has_phone = bool(re.search(r"\+?\d[\d\s\-\(\)]{7,}", resume_text))
    has_sections = any(
        keyword in resume_text.lower()
        for keyword in ["experience", "education", "skills", "profile", "summary", "projects", "certifications"]
    )

    score = 40
    if has_email:
        score += 10
    if has_phone:
        score += 5
    if has_sections:
        score += 10
    if word_count > 300:
        score += 10
    if word_count > 500:
        score += 5
    if word_count > 800:
        score += 5

    # Keyword matching based on JD or Role
    keywords_to_check = []
    if job_description:
        # Simple extraction of capitalized words as potential keywords
        keywords_to_check = list(set(re.findall(r"\b[A-Z][a-zA-Z0-9+#]{1,}\b", job_description)))
    
    if not keywords_to_check:
        keywords_to_check = ROLE_SKILLS.get(role.lower(), ROLE_SKILLS["ai"])

    matched_keywords = [kw for kw in keywords_to_check if kw.lower() in resume_text.lower()]
    keyword_score = min(len(matched_keywords) * 2, 10)
    score += keyword_score

    score = min(score, 98)

    issues = []
    if not has_email:
        issues.append("No email address found")
    if not has_phone:
        issues.append("No phone number found")
    if not has_sections:
        issues.append("Missing standard resume sections (Experience, Education, Skills)")
    if word_count < 400:
        issues.append(f"Resume is quite short ({word_count} words — aim for 400-800)")
    if word_count > 1200:
        issues.append(f"Resume may be too long ({word_count} words — aim for under 1000)")
    if len(matched_keywords) < 5:
        issues.append("Low keyword density for the target role/description")

    result = AtsScoreOutput(
        atsScore=score,
        wordCount=word_count,
        hasContactInfo=has_email or has_phone,
        hasStandardSections=has_sections,
        issues=issues,
    )
    logger.info("score_ats_compatibility: score=%s words=%s", result.atsScore, result.wordCount)
    return result.model_dump_json()


@tool
def match_skills(resume_text: str, role: str, job_description: str = "") -> str:
    """Match skills in the resume against the target role requirements.

    Identifies present skills, missing skills, and computes a skill match percentage.
    Provide the resume text, the target role, and an optional job description.
    """
    lowered_resume = resume_text.lower()
    
    # Identify target skills
    target_skills = []
    if job_description:
        # Extract potential skills from JD (common tech keywords)
        tech_keywords = {
            "Python", "Java", "JavaScript", "TypeScript", "React", "Angular", "Vue", "Node.js",
            "Express", "FastAPI", "Flask", "Django", "SQL", "NoSQL", "MongoDB", "PostgreSQL",
            "Docker", "Kubernetes", "AWS", "Azure", "GCP", "CI/CD", "Git", "Machine Learning",
            "Deep Learning", "NLP", "LLM", "RAG", "LangChain", "PyTorch", "TensorFlow", "Pandas",
            "NumPy", "Scikit-learn", "Tableau", "PowerBI", "Agile", "Scrum", "REST API", "GraphQL"
        }
        target_skills = [kw for kw in tech_keywords if kw.lower() in job_description.lower()]
    
    if not target_skills:
        # Fallback to role-based buckets
        bucket = "ai"
        lowered_input = f"{role} {job_description}".lower()
        if "data" in lowered_input:
            bucket = "data"
        elif any(k in lowered_input for k in ["frontend", "react", "ui"]):
            bucket = "frontend"
        elif any(k in lowered_input for k in ["backend", "api", "server"]):
            bucket = "backend"
        target_skills = ROLE_SKILLS.get(bucket, ROLE_SKILLS["ai"])

    present = [skill for skill in target_skills if skill.lower() in lowered_resume]
    missing = [skill for skill in target_skills if skill not in present]
    
    if not target_skills:
        match_pct = 0
    else:
        match_pct = round((len(present) / len(target_skills)) * 100)

    result = SkillMatchOutput(
        skillMatch=match_pct,
        presentSkills=present,
        missingSkills=missing,
        detectedRole=role,
    )
    logger.info("match_skills: match=%s%% present=%d missing=%d", result.skillMatch, len(present), len(missing))
    return result.model_dump_json()


@tool
def review_grammar(resume_text: str) -> str:
    """Review resume text for grammar issues, passive voice, and clarity.

    Provides a basic style and grammar assessment.
    """
    sentences = re.split(r"[.!?]+", resume_text)
    passive_count = 0
    for sentence in sentences:
        if re.search(r"\b(was|were|been|being|am|is|are)\s+\w+ed\b", sentence.lower()):
            passive_count += 1

    weak_words = {"responsible for", "tasked with", "helped", "worked on", "participated in"}
    weak_count = sum(1 for w in weak_words if w in resume_text.lower())

    total_sentences = len([s for s in sentences if len(s.strip()) > 10])
    passive_ratio = round(passive_count / max(total_sentences, 1) * 100, 1)

    suggestions = []
    if passive_ratio > 20:
        suggestions.append("Reduce passive voice — use active, impact-driven phrasing")
    if weak_count > 2:
        suggestions.append("Replace weak verbs with strong action verbs (led, built, delivered, optimized)")
    if total_sentences < 10:
        suggestions.append("Add more detailed bullet points with measurable outcomes")

    result = GrammarReviewOutput(
        passiveVoiceRatio=passive_ratio,
        weakPhrasesFound=weak_count,
        totalSentences=total_sentences,
        suggestions=suggestions,
    )
    logger.info("review_grammar: passive=%s%% weak=%d sentences=%d", result.passiveVoiceRatio, result.weakPhrasesFound, result.totalSentences)
    return result.model_dump_json()
