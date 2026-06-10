from __future__ import annotations

import json
import logging
import re

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Scoring weights
HEADLINE_MAX = 20
ABOUT_MAX = 15
EXPERIENCE_MAX = 25
SKILLS_MAX = 15
PROJECTS_MAX = 15
ACTIVITY_MAX = 10
PROFILE_TOTAL = 100

VISIBILITY_MAX = 100


_KNOWN_URL_PATTERNS = re.compile(
    r"^(https?://|www\.)?(linkedin\.com/|linkedin\.com/in/|linkedin\.com/pub/)",
    re.IGNORECASE,
)


def _is_url(text: str) -> bool:
    """Return True if *text* looks like a bare LinkedIn URL, not profile content."""
    text = text.strip()
    return bool(re.match(r"^(https?://|www\.)", text)) or bool(
        re.search(r"linkedin\.com/in/", text, re.IGNORECASE)
    )


def _try_parse_json(text: str) -> dict | None:
    """If *text* is a JSON string, parse and return the dict."""
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return None


def _build_profile_text_from_structured(data: dict) -> str:
    """Rebuild a flat string from structured profile fields for backward-compatible scoring."""
    parts = []

    headline = data.get("headline", "")
    if headline:
        parts.append(f"Headline: {headline}")

    about = data.get("about", "")
    if about:
        parts.append(f"About/Summary: {about}")

    experience = data.get("experience", [])
    if isinstance(experience, list):
        for i, exp in enumerate(experience):
            if isinstance(exp, dict):
                title = exp.get("title", exp.get("role", ""))
                company = exp.get("company", "")
                desc = exp.get("description", exp.get("desc", ""))
                parts.append(f"Experience {i + 1}: {title} at {company}. {desc}")
            elif isinstance(exp, str):
                parts.append(f"Experience: {exp}")

    skills = data.get("skills", [])
    if isinstance(skills, list):
        parts.append("Skills: " + ", ".join(str(s) for s in skills))

    projects = data.get("projects", [])
    if isinstance(projects, list):
        for i, proj in enumerate(projects):
            if isinstance(proj, dict):
                name = proj.get("name", proj.get("title", ""))
                desc = proj.get("description", proj.get("desc", ""))
                parts.append(f"Project {i + 1}: {name}. {desc}")
            elif isinstance(proj, str):
                parts.append(f"Project: {proj}")

    education = data.get("education", data.get("educations", []))
    if isinstance(education, list) and education:
        parts.append("Education: " + "; ".join(str(e) for e in education))

    certifications = data.get("certifications", [])
    if isinstance(certifications, list) and certifications:
        parts.append("Certifications: " + "; ".join(str(c) for c in certifications))

    return "\n\n".join(parts)


def _resolve_profile_text(profile_text: str) -> dict:
    """Return a dict with resolved fields or a plain-text string suitable for scoring.

    The returned dict always contains:
      - "profile_text": the final text string to score
      - "structured_fields": dict of extracted fields (may be empty)

    If the input is a bare URL, returns a dict with an ``error`` key.
    """
    result: dict = {}

    # 1. Check for bare URL
    if _is_url(profile_text):
        result["error"] = "Profile content could not be extracted from LinkedIn URL."
        return result

    # 2. Try to parse as JSON / structured dict
    structured = _try_parse_json(profile_text)
    if structured is not None:
        # If it's already structured profile data
        built = _build_profile_text_from_structured(structured)
        result["profile_text"] = built
        result["structured_fields"] = structured
        return result

    # 3. Plain text – use as-is
    result["profile_text"] = profile_text
    result["structured_fields"] = {}
    return result


def _score_profile_sections(profile_text: str) -> dict:
    lower = profile_text.lower()
    word_count = len(re.findall(r"\w+", profile_text))

    # Headline score (0-20)
    has_headline = bool(re.search(r"(?i)(headline|title|role at| at \w+)", profile_text))
    headline_keywords = len(re.findall(r"(?i)(engineer|developer|architect|lead|manager|specialist|analyst|scientist)", profile_text))
    headline_score = 0
    if has_headline:
        headline_score = HEADLINE_MAX // 2
    if headline_keywords >= 2:
        headline_score = min(HEADLINE_MAX, headline_score + 8)
    elif headline_keywords >= 1:
        headline_score = min(HEADLINE_MAX, headline_score + 4)

    # About/Summary score (0-15)
    has_about = bool(re.search(r"(?i)(about|summary|overview|profile)", lower))
    about_words = 0
    if has_about:
        about_section = re.split(r"(?i)(experience|skills|education|projects)", profile_text)[0]
        about_words = len(re.findall(r"\w+", about_section))
    about_score = 0
    if has_about and about_words > 50:
        about_score = ABOUT_MAX
    elif has_about and about_words > 20:
        about_score = ABOUT_MAX * 2 // 3
    elif has_about:
        about_score = ABOUT_MAX // 3

    # Experience score (0-25)
    has_experience = bool(
        re.search(r"(?i)(experience|employment|work history|work at|job)", lower)
    )
    exp_bullets = len(re.findall(r"(?i)(developed|built|led|managed|created|designed|implemented|delivered)", profile_text))
    exp_score = 0
    if has_experience:
        exp_score = EXPERIENCE_MAX // 3
    if exp_bullets >= 6:
        exp_score = min(EXPERIENCE_MAX, exp_score + 15)
    elif exp_bullets >= 3:
        exp_score = min(EXPERIENCE_MAX, exp_score + 10)
    elif exp_bullets >= 1:
        exp_score = min(EXPERIENCE_MAX, exp_score + 5)

    # Skills score (0-15)
    has_skills_section = bool(re.search(r"(?i)(skills|expertise|technologies|proficient)", lower))
    skill_items = len(re.findall(r"(?i)(python|java|javascript|react|angular|node|docker|kubernetes|aws|gcp|azure|sql|nosql|api|ml|ai|langchain|git|ci/cd)", profile_text))
    skills_score = 0
    if has_skills_section:
        skills_score = SKILLS_MAX // 3
    if skill_items >= 8:
        skills_score = min(SKILLS_MAX, skills_score + 10)
    elif skill_items >= 4:
        skills_score = min(SKILLS_MAX, skills_score + 6)
    elif skill_items >= 1:
        skills_score = min(SKILLS_MAX, skills_score + 3)

    # Projects score (0-15)
    has_projects = bool(re.search(r"(?i)(project|portfolio|github|repo|deployed|shipped)", lower))
    project_mentions = len(re.findall(r"(?i)(built|created|launched|developed|implemented)", profile_text))
    projects_score = 0
    if has_projects:
        projects_score = PROJECTS_MAX // 3
    if project_mentions >= 4:
        projects_score = min(PROJECTS_MAX, projects_score + 10)
    elif project_mentions >= 2:
        projects_score = min(PROJECTS_MAX, projects_score + 5)

    # Activity/Engagement score (0-10)
    has_activity = bool(re.search(r"(?i)(post|article|publication|certif|course|recommend|endorse)", lower))
    activity_mentions = len(re.findall(r"(?i)(certif|course|degree|bachelor|master|phd|post|published|speaker|conference)", profile_text))
    activity_score = 0
    if has_activity:
        activity_score = ACTIVITY_MAX // 2
    if activity_mentions >= 3:
        activity_score = min(ACTIVITY_MAX, activity_score + 5)
    elif activity_mentions >= 1:
        activity_score = min(ACTIVITY_MAX, activity_score + 3)

    total = headline_score + about_score + exp_score + skills_score + projects_score + activity_score
    total = min(total, PROFILE_TOTAL)

    breakdown = {
        "headline": {"score": headline_score, "max": HEADLINE_MAX},
        "about": {"score": about_score, "max": ABOUT_MAX},
        "experience": {"score": exp_score, "max": EXPERIENCE_MAX},
        "skills": {"score": skills_score, "max": SKILLS_MAX},
        "projects": {"score": projects_score, "max": PROJECTS_MAX},
        "activity": {"score": activity_score, "max": ACTIVITY_MAX},
    }

    missing = []
    if headline_score == 0:
        missing.append("headline")
    if about_score == 0:
        missing.append("about/summary section")
    if skills_score == 0:
        missing.append("skills section")
    if exp_score == 0:
        missing.append("experience section")
    if projects_score == 0:
        missing.append("projects or portfolio")

    logger.info(
        "analyze_profile dynamic scoring: total=%s/100 headline=%s about=%s exp=%s skills=%s projects=%s activity=%s",
        total, headline_score, about_score, exp_score, skills_score, projects_score, activity_score,
    )

    return {
        "profileScore": total,
        "scoreBreakdown": breakdown,
        "wordCount": word_count,
        "hasHeadline": has_headline,
        "hasSummary": has_about,
        "hasExperience": has_experience,
        "hasSkills": has_skills_section,
        "hasProjects": has_projects,
        "hasActivity": has_activity,
        "missingElements": missing,
    }


@tool
def analyze_profile(profile_text: str) -> str:
    """Analyze a LinkedIn profile from structured profile data or raw text.

    Accepts:

    - **JSON string** with keys: ``headline``, ``about``, ``experience`` (list),
      ``skills`` (list), ``projects`` (list), ``education`` (list),
      ``certifications`` (list).
    - **Plain text** — sections like Headline, About, Experience, Skills,
      Projects.

    Scores each section independently: Headline(20pts), About(15pts),
    Experience(25pts), Skills(15pts), Projects(15pts), Activity(10pts).
    Total = 100.  Returns profile strength indicators with per-section breakdown.

    **Does NOT accept bare LinkedIn URLs.** Pass profile content instead.
    """
    resolved = _resolve_profile_text(profile_text)
    if "error" in resolved:
        logger.warning("analyze_profile: bare URL detected — returning error")
        return json.dumps(resolved)

    text = resolved["profile_text"]
    structured = resolved["structured_fields"]
    result = _score_profile_sections(text)

    # Log extracted fields for debugging
    if structured:
        logger.info("Extracted structured profile data: headline=%s about_len=%d exp_count=%d skills=%d projects=%d",
                    structured.get("headline", "")[:60],
                    len(structured.get("about", "")),
                    len(structured.get("experience", [])),
                    len(structured.get("skills", [])),
                    len(structured.get("projects", [])))
    else:
        logger.info("Extracted profile text: word_count=%d", result["wordCount"])

    logger.info("analyze_profile: score=%s missing=%s", result["profileScore"], result["missingElements"])
    return json.dumps(result)


@tool
def optimize_keywords(profile_text: str, target_role: str) -> str:
    """Analyze keyword presence in the profile for a target role.

    Accepts the same input formats as ``analyze_profile`` (JSON, plain text, or
    raw profile content).  Does NOT accept bare URLs.

    Returns keyword gap analysis and suggestions to improve search discoverability.
    """
    resolved = _resolve_profile_text(profile_text)
    if "error" in resolved:
        logger.warning("optimize_keywords: bare URL detected — returning error")
        return json.dumps(resolved)

    text = resolved["profile_text"]

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
    present = [kw for kw in target_keywords if kw.lower() in text.lower()]
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

    Accepts the same input formats as ``analyze_profile`` (JSON, plain text, or
    raw profile content).  Does NOT accept bare URLs.

    Evaluates profile completeness, keyword presence, and credibility signals.
    Returns score out of 100 with per-section breakdown.
    """
    resolved = _resolve_profile_text(profile_text)
    if "error" in resolved:
        logger.warning("score_recruiter_visibility: bare URL detected — returning error")
        return json.dumps(resolved)

    text = resolved["profile_text"]

    word_count = len(re.findall(r"\w+", text))
    has_open_to_work = bool(re.search(r"(?i)(open to work|open for|hiring|looking for)", text))
    has_certifications = bool(re.search(r"(?i)(certif|credential|license)", text))
    has_publications = bool(re.search(r"(?i)(publication|article|blog|post)", text))
    skill_count = len(re.findall(r"(?i)(skills|expertise|proficient|experienced)", text))
    recommendation_mentions = len(re.findall(r"(?i)(recommend|endorse)", text))
    has_education = bool(re.search(r"(?i)(education|university|degree|bachelor|master|phd)", text))

    # Open To Work: 0-15
    o2w_score = 15 if has_open_to_work else 0

    # Certifications: 0-15
    cert_score = 15 if has_certifications else 0

    # Publications/Content: 0-15
    pub_score = 15 if has_publications else 0

    # Skills density: 0-20
    if skill_count >= 5:
        skills_vis_score = 20
    elif skill_count >= 3:
        skills_vis_score = 12
    elif skill_count >= 1:
        skills_vis_score = 5
    else:
        skills_vis_score = 0

    # Recommendations/Endorsements: 0-15
    if recommendation_mentions >= 3:
        rec_score = 15
    elif recommendation_mentions >= 1:
        rec_score = 8
    else:
        rec_score = 0

    # Profile depth (word count): 0-20
    if word_count > 500:
        depth_score = 20
    elif word_count > 300:
        depth_score = 14
    elif word_count > 150:
        depth_score = 8
    elif word_count > 50:
        depth_score = 4
    else:
        depth_score = 0

    # Education: 0-15 (bonus)
    edu_score = 15 if has_education else 0

    total = o2w_score + cert_score + pub_score + skills_vis_score + rec_score + depth_score + edu_score
    total = min(total, VISIBILITY_MAX)

    breakdown = {
        "openToWork": {"score": o2w_score, "max": 15},
        "certifications": {"score": cert_score, "max": 15},
        "publications": {"score": pub_score, "max": 15},
        "skillsDensity": {"score": skills_vis_score, "max": 20},
        "recommendations": {"score": rec_score, "max": 15},
        "profileDepth": {"score": depth_score, "max": 20},
        "education": {"score": edu_score, "max": 15},
    }

    tips = []
    if not has_open_to_work:
        tips.append("Enable #OpenToWork or add a clear 'Looking for...' statement")
    if not has_certifications:
        tips.append("Add relevant certifications to boost credibility")
    if not has_publications:
        tips.append("Share posts or articles to demonstrate thought leadership")
    if word_count < 200:
        tips.append("Expand your profile with more detail — aim for 500+ words of substantive content")
    if skill_count < 3:
        tips.append("Add more technical skills to your profile")
    if recommendation_mentions < 1:
        tips.append("Request recommendations from colleagues and managers")

    result = {
        "visibilityScore": total,
        "scoreBreakdown": breakdown,
        "hasOpenToWork": has_open_to_work,
        "hasCertifications": has_certifications,
        "hasPublications": has_publications,
        "hasEducation": has_education,
        "skillSignalCount": skill_count,
        "improvementTips": tips,
    }
    logger.info(
        "score_recruiter_visibility dynamic: total=%s/100 o2w=%s cert=%s pub=%s skills=%s rec=%s depth=%s edu=%s",
        total, o2w_score, cert_score, pub_score, skills_vis_score, rec_score, depth_score, edu_score,
    )
    return json.dumps(result)
