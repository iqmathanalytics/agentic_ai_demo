from __future__ import annotations

import json
import logging
import re

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def analyze_profile(profile_text: str) -> str:
    """Analyze a LinkedIn profile by examining the provided profile text or URL.

    Extracts key signals: has headline, has summary/about section, experience detail level.
    Returns profile strength indicators.
    """
    word_count = len(re.findall(r"\w+", profile_text))
    has_headline = bool(re.search(r"(?i)(headline|title|role at)", profile_text))
    has_summary = bool(re.search(r"(?i)(about|summary|overview)", profile_text))
    has_experience = bool(re.search(r"(?i)(experience|work at|employment)", profile_text))
    has_skills = bool(re.search(r"(?i)(skills|expertise|proficient)", profile_text))
    has_education = bool(re.search(r"(?i)(education|university|degree)", profile_text))
    has_recommendations = bool(re.search(r"(?i)(recommend|endorse)", profile_text))

    score = 30
    if has_headline:
        score += 10
    if has_summary:
        score += 10
    if has_experience:
        score += 15
    if has_skills:
        score += 10
    if has_education:
        score += 10
    if has_recommendations:
        score += 5
    if word_count > 100:
        score += 5
    if word_count > 300:
        score += 5

    score = min(score, 95)

    missing = []
    if not has_headline:
        missing.append("headline")
    if not has_summary:
        missing.append("about/summary section")
    if not has_skills:
        missing.append("skills section")
    if not has_recommendations:
        missing.append("recommendations or endorsements")

    result = {
        "profileScore": score,
        "wordCount": word_count,
        "hasHeadline": has_headline,
        "hasSummary": has_summary,
        "hasExperience": has_experience,
        "hasSkills": has_skills,
        "hasEducation": has_education,
        "missingElements": missing,
    }
    logger.info("analyze_profile: score=%s missing=%s", score, missing)
    return json.dumps(result)


@tool
def optimize_keywords(profile_text: str, target_role: str) -> str:
    """Analyze keyword presence in the profile for a target role.

    Returns keyword gap analysis and suggestions to improve search discoverability.
    """
    role_keywords = {
        "ai": ["AI", "Machine Learning", "LLM", "LangChain", "RAG", "Python", "MLOps", "Deep Learning"],
        "data": ["Data Science", "SQL", "Python", "Dashboard", "ETL", "Analytics", "Statistics", "Tableau"],
        "frontend": ["React", "TypeScript", "JavaScript", "CSS", "UI/UX", "Frontend", "Web", "Responsive"],
        "backend": ["API", "Backend", "Database", "Docker", "Microservices", "Python", "Node.js", "AWS"],
        "fullstack": ["Full Stack", "React", "Node.js", "API", "Database", "Python", "JavaScript", "DevOps"],
    }

    lowered = target_role.lower()
    if "full" in lowered or "fullstack" in lowered:
        bucket = "fullstack"
    elif "ai" in lowered or "ml" in lowered or "machine learning" in lowered:
        bucket = "ai"
    elif "data" in lowered or "analyst" in lowered or "science" in lowered:
        bucket = "data"
    elif "front" in lowered or "ui" in lowered or "react" in lowered:
        bucket = "frontend"
    elif "back" in lowered or "api" in lowered or "server" in lowered:
        bucket = "backend"
    else:
        bucket = "fullstack"

    target_keywords = role_keywords[bucket]
    present = [kw for kw in target_keywords if kw.lower() in profile_text.lower()]
    missing = [kw for kw in target_keywords if kw not in present]
    coverage = round((len(present) / len(target_keywords)) * 100)

    result = {
        "keywordCoverage": coverage,
        "presentKeywords": present,
        "missingKeywords": missing,
        "detectedRoleCategory": bucket,
        "suggestions": [
            f"Add '{kw}' to your headline, skills section, or experience descriptions"
            for kw in missing[:5]
        ],
    }
    logger.info("optimize_keywords: coverage=%s%% missing=%s", coverage, missing)
    return json.dumps(result)


@tool
def score_recruiter_visibility(profile_text: str) -> str:
    """Score how discoverable the profile is to recruiters.

    Evaluates profile completeness, keyword presence, and credibility signals.
    """
    word_count = len(re.findall(r"\w+", profile_text))
    has_open_to_work = bool(re.search(r"(?i)(open to work|open for|hiring|looking for)", profile_text))
    has_certifications = bool(re.search(r"(?i)(certif|credential|license)", profile_text))
    has_publications = bool(re.search(r"(?i)(publication|article|blog|post)", profile_text))
    skill_count = len(re.findall(r"(?i)(skills|expertise|proficient|experienced)", profile_text))
    recommendation_mentions = len(re.findall(r"(?i)(recommend|endorse)", profile_text))

    score = 30
    if has_open_to_work:
        score += 10
    if has_certifications:
        score += 10
    if has_publications:
        score += 10
    if skill_count >= 3:
        score += 10
    if recommendation_mentions >= 2:
        score += 10
    if word_count > 200:
        score += 10
    if word_count > 500:
        score += 10

    score = min(score, 95)

    tips = []
    if not has_open_to_work:
        tips.append("Enable #OpenToWork or add a clear 'Looking for...' statement")
    if not has_certifications:
        tips.append("Add relevant certifications to boost credibility")
    if not has_publications:
        tips.append("Share posts or articles to demonstrate thought leadership")
    if word_count < 200:
        tips.append("Expand your profile with more detail — aim for 500+ words of substantive content")

    result = {
        "visibilityScore": score,
        "hasOpenToWork": has_open_to_work,
        "hasCertifications": has_certifications,
        "hasPublications": has_publications,
        "skillSignalCount": skill_count,
        "improvementTips": tips,
    }
    logger.info("score_recruiter_visibility: score=%s", score)
    return json.dumps(result)
