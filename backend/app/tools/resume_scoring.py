"""Deterministic resume analysis — ATS, skills, grammar."""

from __future__ import annotations

import re
from typing import Any

# Role-specific skill catalogs (case-insensitive word-boundary matching)
ROLE_SKILLS: dict[str, list[str]] = {
    "devops": [
        "Docker", "Kubernetes", "K8s", "CI/CD", "Jenkins", "GitHub Actions", "GitLab",
        "AWS", "Azure", "GCP", "Google Cloud", "Terraform", "Ansible", "Puppet", "Chef",
        "Linux", "Bash", "Shell", "Prometheus", "Grafana", "ELK", "Splunk",
        "Nginx", "Apache", "Git", "Helm", "ArgoCD", "DevOps", "SRE",
        "Infrastructure as Code", "IaC", "CloudFormation", "EC2", "S3", "VPC",
        "Microservices", "Container", "YAML", "Networking", "Load Balancer",
        "Python", "Monitoring", "Automation", "Agile", "Scrum",
    ],
    "ai": [
        "Python", "LangChain", "RAG", "LLM", "MLOps", "Vector Database", "FastAPI",
        "PyTorch", "TensorFlow", "NLP", "Machine Learning", "Deep Learning",
        "Generative AI", "OpenAI", "Hugging Face", "Pandas", "NumPy",
    ],
    "data": [
        "SQL", "Python", "Power BI", "Tableau", "Excel", "ETL", "Statistics",
        "Machine Learning", "Data Analysis", "Analytics", "Dashboard", "Pandas",
    ],
    "frontend": [
        "React", "TypeScript", "JavaScript", "CSS", "HTML", "Vue", "Angular",
        "Testing", "Accessibility", "Performance", "Tailwind", "Next.js",
    ],
    "backend": [
        "Python", "Java", "C#", "API", "REST", "SQL", "PostgreSQL", "MongoDB",
        "Docker", "Redis", "Caching", "Microservices", "ASP.NET", "FastAPI", "Node.js",
    ],
    "dotnet": [
        "C#", "ASP.NET", ".NET", "Web API", "SQL Server", "Entity Framework",
        "Azure", "MVC", "LINQ", "REST API",
    ],
}

SECTION_KEYWORDS = [
    "experience", "education", "skills", "profile", "summary", "objective",
    "projects", "certifications", "work experience", "technical",
]

WEAK_PHRASES = {
    "responsible for", "tasked with", "helped with", "worked on",
    "participated in", "involved in", "duties included",
}

ACTION_VERBS = {
    "built", "developed", "designed", "implemented", "deployed", "automated",
    "optimized", "led", "managed", "delivered", "reduced", "increased",
    "improved", "created", "architected", "migrated", "configured",
}


def normalize_resume_text(text: str) -> str:
    """Fix PDF extraction artifacts (extra spaces between words, broken lines)."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of whitespace to single space
    text = re.sub(r"[ \t]+", " ", text)
    # Join lines that look like broken PDF word-per-line output
    lines = [ln.strip() for ln in text.split("\n")]
    merged: list[str] = []
    buf: list[str] = []
    for line in lines:
        if not line:
            if buf:
                merged.append(" ".join(buf))
                buf = []
            merged.append("")
            continue
        # Short fragment lines (1-3 words) likely broken PDF layout
        word_count = len(line.split())
        if word_count <= 3 and len(line) < 40:
            buf.append(line)
        else:
            if buf:
                merged.append(" ".join(buf))
                buf = []
            merged.append(line)
    if buf:
        merged.append(" ".join(buf))
    text = "\n".join(merged)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_role_bucket(role: str, job_description: str = "") -> str:
    combined = f"{role} {job_description}".lower()
    if any(k in combined for k in ["devops", "dev ops", "sre", "site reliability", "platform engineer", "cloud engineer", "infrastructure"]):
        return "devops"
    if any(k in combined for k in ["data analyst", "data scientist", "analytics", "bi ", "business intelligence"]):
        return "data"
    if any(k in combined for k in ["frontend", "react", "ui engineer", "web developer"]):
        return "frontend"
    if any(k in combined for k in [".net", "dotnet", "c#", "asp.net"]):
        return "dotnet"
    if any(k in combined for k in ["backend", "api developer", "server"]):
        return "backend"
    if any(k in combined for k in ["ai", "ml", "machine learning", "llm", "nlp"]):
        return "ai"
    return "backend"


def _skill_in_text(skill: str, text: str) -> bool:
    """Word-boundary skill match to avoid false positives (e.g. RAG in leverage)."""
    pattern = r"(?<![a-zA-Z0-9+#])" + re.escape(skill) + r"(?![a-zA-Z0-9+#])"
    return bool(re.search(pattern, text, re.IGNORECASE))


def extract_skills_from_jd(job_description: str) -> list[str]:
    if not job_description:
        return []
    found = []
    all_skills = {s for skills in ROLE_SKILLS.values() for s in skills}
    for skill in all_skills:
        if _skill_in_text(skill, job_description):
            found.append(skill)
    # Also pick capitalized tech terms from JD
    for term in re.findall(r"\b[A-Z][a-zA-Z0-9+#./]{1,}(?:\s[A-Z][a-zA-Z0-9+#./]{1,})?\b", job_description):
        if len(term) > 2 and term not in found:
            found.append(term)
    return found[:40]


def get_target_skills(role: str, job_description: str = "") -> list[str]:
    jd_skills = extract_skills_from_jd(job_description)
    if jd_skills:
        return jd_skills
    bucket = detect_role_bucket(role, job_description)
    return ROLE_SKILLS.get(bucket, ROLE_SKILLS["backend"])


def extract_resume_skills(text: str) -> list[str]:
    """Skills explicitly listed in resume."""
    found = []
    all_skills = {s for skills in ROLE_SKILLS.values() for s in skills}
    for skill in all_skills:
        if _skill_in_text(skill, text):
            found.append(skill)
    return sorted(set(found), key=str.lower)


def score_ats(resume_text: str, role: str, job_description: str = "") -> dict[str, Any]:
    text = normalize_resume_text(resume_text)
    lowered = text.lower()
    words = re.findall(r"\b\w+\b", text)
    word_count = len(words)

    has_email = bool(re.search(r"\S+@\S+\.\S+", text))
    has_phone = bool(re.search(r"\+?\d[\d\s\-()]{8,}\d", text))
    has_linkedin = "linkedin.com" in lowered
    has_github = "github.com" in lowered
    sections_found = sum(1 for kw in SECTION_KEYWORDS if kw in lowered)
    has_sections = sections_found >= 3

    target_skills = get_target_skills(role, job_description)
    matched = [s for s in target_skills if _skill_in_text(s, text)]
    keyword_pct = round(len(matched) / max(len(target_skills), 1) * 100)

    bullets = len(re.findall(r"^[\s]*[●•\-\*]", text, re.MULTILINE))
    has_metrics = bool(re.search(r"\b\d+[%$]|\b\d+\s*(%|percent|users|clients|teams|projects)\b", text, re.I))
    action_count = sum(1 for v in ACTION_VERBS if re.search(rf"\b{v}\b", lowered))

    score = 0
    breakdown: dict[str, int] = {}

    # Contact (20 pts)
    contact = 0
    if has_email:
        contact += 8
    if has_phone:
        contact += 5
    if has_linkedin:
        contact += 4
    if has_github:
        contact += 3
    breakdown["contact"] = contact
    score += contact

    # Structure (25 pts)
    structure = min(sections_found * 4, 16)
    if has_sections:
        structure += 4
    if bullets >= 5:
        structure += 5
    structure = min(structure, 25)
    breakdown["structure"] = structure
    score += structure

    # Content quality (25 pts)
    content = 0
    if word_count >= 350:
        content += 8
    if word_count >= 500:
        content += 4
    if has_metrics:
        content += 8
    if action_count >= 5:
        content += 5
    content = min(content, 25)
    breakdown["content"] = content
    score += content

    # Role keyword match (30 pts)
    keyword_pts = min(round(keyword_pct * 0.3), 30)
    breakdown["keywords"] = keyword_pts
    score += keyword_pts

    score = min(max(score, 0), 98)

    issues: list[str] = []
    if not has_email:
        issues.append("Add a professional email address at the top")
    if not has_phone:
        issues.append("Add a phone number for recruiter contact")
    if sections_found < 3:
        issues.append("Add clear sections: Experience, Skills, Education, Projects")
    if word_count < 350:
        issues.append(f"Resume is short ({word_count} words) — expand with quantified bullet points")
    if word_count > 1500:
        issues.append(f"Resume is long ({word_count} words) — trim to 1-2 pages for ATS")
    if keyword_pct < 30:
        issues.append(f"Only {keyword_pct}% of {role} keywords found — tailor skills and experience to the role")
    if not has_metrics:
        issues.append("Add measurable outcomes (%, $, time saved, users impacted) to bullet points")
    if bullets < 5:
        issues.append("Use more bullet points (● or -) to highlight achievements")
    if action_count < 4:
        issues.append("Start bullets with strong action verbs (Built, Deployed, Automated, Led)")

    # Role alignment check
    objective_match = re.search(r"(career objective|objective|summary)(.{0,500})", lowered, re.DOTALL)
    if objective_match:
        obj_text = objective_match.group(2)
        role_words = [w for w in role.lower().split() if len(w) > 3]
        if role_words and not any(w in obj_text for w in role_words):
            if "data analyst" in obj_text and "devops" in role.lower():
                issues.append("Career objective says 'Data Analyst' but you're applying for DevOps — update your headline and objective")
            elif not any(_skill_in_text(w, obj_text) for w in role_words):
                issues.append(f"Career objective/summary doesn't mention '{role}' — align it with your target role")

    return {
        "atsScore": score,
        "wordCount": word_count,
        "hasContactInfo": has_email or has_phone,
        "hasStandardSections": has_sections,
        "keywordMatchPct": keyword_pct,
        "matchedKeywords": matched[:15],
        "scoreBreakdown": breakdown,
        "issues": issues,
    }


def match_skills_analysis(resume_text: str, role: str, job_description: str = "") -> dict[str, Any]:
    text = normalize_resume_text(resume_text)
    target_skills = get_target_skills(role, job_description)
    present = [s for s in target_skills if _skill_in_text(s, text)]
    missing = [s for s in target_skills if s not in present]
    resume_skills = extract_resume_skills(text)

    match_pct = round(len(present) / max(len(target_skills), 1) * 100)

    suggestions = []
    for ms in missing[:6]:
        suggestions.append(f"Add '{ms}' if you have experience — it's relevant for {role}")

    return {
        "skillMatch": match_pct,
        "presentSkills": present,
        "missingSkills": missing[:10],
        "resumeSkills": resume_skills[:20],
        "detectedRole": role,
        "roleBucket": detect_role_bucket(role, job_description),
        "suggestions": suggestions,
    }


def review_grammar_analysis(resume_text: str) -> dict[str, Any]:
    text = normalize_resume_text(resume_text)
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 10]
    passive_count = sum(
        1 for s in sentences
        if re.search(r"\b(was|were|been|being|am|is|are)\s+\w+ed\b", s.lower())
    )
    weak_count = sum(1 for w in WEAK_PHRASES if w in text.lower())
    total_sentences = len(sentences)
    passive_ratio = round(passive_count / max(total_sentences, 1) * 100, 1)

    suggestions: list[str] = []
    if passive_ratio > 20:
        suggestions.append("Reduce passive voice — use active, impact-driven phrasing")
    if weak_count > 2:
        suggestions.append("Replace weak phrases ('responsible for', 'worked on') with action verbs")
    if total_sentences < 8:
        suggestions.append("Add more detailed bullet points with measurable outcomes")
    if re.search(r"\s{3,}", resume_text):
        suggestions.append("Fix inconsistent spacing — some sections have broken formatting from PDF export")

    return {
        "passiveVoiceRatio": passive_ratio,
        "weakPhrasesFound": weak_count,
        "totalSentences": total_sentences,
        "suggestions": suggestions,
    }
