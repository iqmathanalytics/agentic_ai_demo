"""Build resume review reports from tool results."""

from __future__ import annotations

import json
from typing import Any

SCORE_MAX = {"contact": 20, "structure": 25, "content": 25, "keywords": 30}

BULLET_REWRITE_TEMPLATES: dict[str, list[tuple[str | None, str, str]]] = {
    "devops": [
        (
            "Python",
            "Developed Python scripts for data extraction.",
            "Automated daily ETL pipelines with Python, reducing data-load time by 45% and eliminating manual errors.",
        ),
        (
            "Power BI",
            "Created dashboards in Power BI for performance monitoring.",
            "Implemented Grafana dashboards to monitor CI/CD pipeline latency, enabling a 30% reduction in build time.",
        ),
        (
            None,
            "Collaborated with developers to troubleshoot API issues.",
            "Partnered with development teams to containerize legacy APIs using Docker, cutting deployment time from 2 hrs to 15 min.",
        ),
    ],
    "data": [
        (
            "Python",
            "Used Python for various data tasks.",
            "Built Python ETL pipelines processing 2M+ rows daily, cutting report generation time from 4 hours to 20 minutes.",
        ),
        (
            "SQL",
            "Worked with SQL databases.",
            "Optimized complex SQL queries across 15+ tables, improving dashboard load speed by 60%.",
        ),
        (
            "Power BI",
            "Created Power BI reports for the team.",
            "Designed executive Power BI dashboards used by 50+ stakeholders, driving a 25% faster decision cycle.",
        ),
    ],
    "backend": [
        (
            "API",
            "Built REST APIs for internal use.",
            "Designed and deployed RESTful APIs handling 10K+ daily requests with 99.9% uptime.",
        ),
        (
            "C#",
            "Developed features in C#.",
            "Refactored core C# services, reducing API latency by 35% and improving test coverage to 85%.",
        ),
        (
            None,
            "Worked on backend improvements.",
            "Led migration of monolithic services to microservices, cutting deployment time from 2 hours to 15 minutes.",
        ),
    ],
    "dotnet": [
        (
            "ASP.NET",
            "Built ASP.NET web applications.",
            "Delivered ASP.NET Core APIs serving 5K+ users with sub-200ms response times.",
        ),
        (
            "C#",
            "Wrote C# code for business logic.",
            "Implemented C# domain services that reduced defect rate by 40% through unit-tested modules.",
        ),
        (
            None,
            "Maintained .NET applications.",
            "Modernized legacy .NET Framework apps to .NET 8, improving performance by 50%.",
        ),
    ],
    "frontend": [
        (
            "React",
            "Worked on React components.",
            "Built reusable React component library used across 8 products, cutting UI dev time by 30%.",
        ),
        (
            None,
            "Improved website performance.",
            "Optimized React bundle and lazy-loading, improving Lighthouse performance score from 62 to 94.",
        ),
        (
            None,
            "Collaborated on UI features.",
            "Shipped accessible UI features (WCAG 2.1 AA) adopted by 12K+ monthly active users.",
        ),
    ],
    "ai": [
        (
            "Python",
            "Used Python for ML experiments.",
            "Deployed Python ML pipelines in production, improving model inference latency by 40%.",
        ),
        (
            "Machine Learning",
            "Built machine learning models.",
            "Trained and deployed ML models that increased prediction accuracy from 78% to 91%.",
        ),
        (
            None,
            "Worked on AI features.",
            "Integrated LLM-powered features reducing manual review time by 55% for 200+ daily tickets.",
        ),
    ],
}


def _parse_tool(raw: str) -> dict:
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return {}


def build_ats_breakdown_rows(ats: dict, role: str) -> list[dict[str, Any]]:
    """Structured ATS component rows for UI tables."""
    breakdown = ats.get("scoreBreakdown") or {}
    word_count = ats.get("wordCount", 0)
    keyword_pct = ats.get("keywordMatchPct", 0)
    matched = ats.get("matchedKeywords") or []
    has_contact = ats.get("hasContactInfo", False)
    has_sections = ats.get("hasStandardSections", False)

    contact_comment = (
        "Complete and machine-readable contact details."
        if breakdown.get("contact", 0) >= 16
        else "Add email, phone, and LinkedIn/GitHub for recruiter reach."
    )

    structure_comment = (
        f"Clear headings and bullet structure ({word_count} words)."
        if has_sections and word_count <= 900
        else f"Sections are present but length ({word_count} words) or mixed formatting may confuse parsers."
        if has_sections
        else "Add standard sections: Experience, Skills, Education, Projects."
    )
    if word_count > 900:
        structure_comment = (
            f"Clear headings, but excessive length ({word_count} words) and mixed formatting "
            "(tables, graphics) can confuse parsers."
        )

    content_score = breakdown.get("content", 0)
    if content_score >= 18:
        content_comment = "Strong impact language with metrics and action verbs."
    elif keyword_pct < 20:
        track = "analytics" if "devops" in role.lower() or "sre" in role.lower() else "another track"
        content_comment = f"Relevant experience is present but framed for {track}, not operations."
    elif content_score >= 12:
        content_comment = "Relevant experience is present but needs more quantified outcomes."
    else:
        content_comment = f"Relevant experience is present but not positioned for {role}."

    kw_comment = (
        f"Strong keyword density ({keyword_pct}%) for {role}."
        if keyword_pct >= 40
        else f"Only {', '.join(matched[:3]) or 'few role keywords'} matches the {role} keyword set ({keyword_pct}% density)."
    )

    comments = {
        "contact": contact_comment,
        "structure": structure_comment,
        "content": content_comment,
        "keywords": kw_comment,
    }

    rows = []
    for key, max_pts in SCORE_MAX.items():
        score = breakdown.get(key, 0)
        rows.append({
            "component": key.title(),
            "score": score,
            "max": max_pts,
            "comment": comments[key],
        })
    return rows


def build_bullet_rewrites(role: str, role_bucket: str, resume_skills: list[str]) -> list[dict[str, str]]:
    """Role-tailored before/after bullet examples for the UI."""
    templates = BULLET_REWRITE_TEMPLATES.get(role_bucket, BULLET_REWRITE_TEMPLATES["backend"])
    skills_lower = {s.lower() for s in resume_skills}
    label = f"{role}-focused" if role else "Role-focused"
    selected: list[dict[str, str]] = []
    seen_originals: set[str] = set()

    for skill_hint, original, revised in templates:
        if skill_hint and skill_hint.lower() not in skills_lower:
            continue
        if original in seen_originals:
            continue
        seen_originals.add(original)
        selected.append({"label": label, "original": original, "revised": revised})
        if len(selected) >= 3:
            break

    if len(selected) < 3:
        for _, original, revised in templates:
            if original in seen_originals:
                continue
            seen_originals.add(original)
            selected.append({"label": label, "original": original, "revised": revised})
            if len(selected) >= 3:
                break

    return selected[:3]


def build_deterministic_report(
    role: str,
    experience: str,
    ats: dict,
    skills: dict,
    grammar: dict,
) -> str:
    ats_score = ats.get("atsScore", 0)
    skill_match = skills.get("skillMatch", 0)
    lines = [
        f"# Resume Review: {role}",
        "",
        f"**Experience level:** {experience or 'Not specified'}",
        "",
        "## Executive Summary",
        f"- **ATS Score:** {ats_score}/100",
        f"- **Skill Match:** {skill_match}% for {role}",
        f"- **Word Count:** {ats.get('wordCount', 'N/A')}",
        "",
        "## ATS Compatibility",
        f"Your resume scores **{ats_score}/100** for ATS parsing and role alignment.",
        "",
    ]

    breakdown = ats.get("scoreBreakdown") or {}
    if breakdown:
        lines.append("**Score breakdown:**")
        for k, v in breakdown.items():
            lines.append(f"- {k.title()}: {v} pts")
        lines.append("")

    matched = ats.get("matchedKeywords") or []
    if matched:
        lines.append(f"**Role keywords found:** {', '.join(matched[:12])}")
        lines.append("")

    if ats.get("issues"):
        lines.append("**Issues to fix:**")
        for issue in ats["issues"]:
            lines.append(f"- {issue}")
        lines.append("")

    lines.extend(["## Skill Gap Analysis", f"**Match: {skill_match}%**", ""])
    present = skills.get("presentSkills") or []
    missing = skills.get("missingSkills") or []
    resume_skills = skills.get("resumeSkills") or []

    if present:
        lines.append("**Skills aligned with role:**")
        for s in present[:12]:
            lines.append(f"- {s}")
        lines.append("")

    if missing:
        lines.append("**Skills to add or highlight:**")
        for s in missing[:8]:
            lines.append(f"- {s}")
        lines.append("")

    if resume_skills:
        lines.append(f"**All detected skills on resume:** {', '.join(resume_skills[:15])}")
        lines.append("")

    if grammar.get("suggestions"):
        lines.extend(["## Style & Grammar", ""])
        for s in grammar["suggestions"]:
            lines.append(f"- {s}")
        lines.append("")

    lines.extend([
        "## Top Recommendations",
    ])
    all_suggestions: list[str] = list(ats.get("issues") or [])
    all_suggestions.extend(skills.get("suggestions") or [])
    all_suggestions.extend(grammar.get("suggestions") or [])
    seen = set()
    for s in all_suggestions:
        if s not in seen:
            seen.add(s)
            lines.append(f"- {s}")

    if skill_match < 40:
        lines.extend([
            "",
            "## Recruiter Verdict",
            f"**Needs significant tailoring** for {role}. Your background shows strong technical and training experience, "
            "but the resume is not positioned for this role. Rewrite your objective, retitle your experience bullets, "
            "and add role-specific keywords before applying.",
        ])
    elif skill_match < 65:
        lines.extend([
            "",
            "## Recruiter Verdict",
            f"**Potential fit with revisions.** You have relevant transferable skills. Strengthen DevOps/cloud keywords "
            "and quantify impact in bullet points to improve shortlist chances.",
        ])
    else:
        lines.extend([
            "",
            "## Recruiter Verdict",
            f"**Strong candidate** for {role}. Polish formatting issues and add metrics to stand out further.",
        ])

    return "\n".join(lines)


def extract_report_data(tool_history: list[dict], report_text: str, role: str) -> dict[str, Any]:
    ats, skills, grammar = {}, {}, {}
    for entry in tool_history:
        name = entry.get("tool", "")
        parsed = _parse_tool(entry.get("result", ""))
        if name == "score_ats_compatibility":
            ats = parsed
        elif name == "match_skills":
            skills = parsed
        elif name == "review_grammar":
            grammar = parsed

    suggestions: list[str] = []
    suggestions.extend(ats.get("issues") or [])
    suggestions.extend(skills.get("suggestions") or [])
    suggestions.extend(grammar.get("suggestions") or [])

    return {
        "atsScore": ats.get("atsScore"),
        "skillMatch": skills.get("skillMatch"),
        "strengths": (skills.get("presentSkills") or [])[:8],
        "missingSkills": skills.get("missingSkills") or [],
        "resumeSkills": skills.get("resumeSkills") or [],
        "keywordMatchPct": ats.get("keywordMatchPct"),
        "matchedKeywords": ats.get("matchedKeywords") or [],
        "scoreBreakdown": ats.get("scoreBreakdown") or {},
        "scoreBreakdownMax": SCORE_MAX,
        "atsBreakdown": build_ats_breakdown_rows(ats, role),
        "bulletRewrites": build_bullet_rewrites(
            role,
            skills.get("roleBucket", "backend"),
            skills.get("resumeSkills") or [],
        ),
        "wordCount": ats.get("wordCount"),
        "suggestions": list(dict.fromkeys(suggestions)),
        "recruiterFeedback": report_text,
        "report": report_text,
        "role": role,
        "roleBucket": skills.get("roleBucket", ""),
    }
