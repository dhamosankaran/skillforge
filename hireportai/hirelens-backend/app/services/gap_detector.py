"""Skill gap detection service."""
from typing import Any, Dict, List, Set

from app.models.response_models import SkillGap
from app.utils.skill_taxonomy import SKILL_CATEGORIES, get_skill_category


def detect_gaps(
    resume_skills: List[str],
    jd_requirements: Dict[str, Any],
) -> List[SkillGap]:
    """Detect skills required by the JD but missing from the resume.

    Args:
        resume_skills: Skills found in the resume.
        jd_requirements: Parsed job requirements from nlp.extract_job_requirements().

    Returns:
        List of SkillGap objects for missing skills.
    """
    resume_skills_lower: Set[str] = {s.lower() for s in resume_skills}
    required_skills: List[str] = jd_requirements.get("required_skills", [])
    preferred_skills: List[str] = jd_requirements.get("preferred_skills", [])
    all_jd_skills: List[str] = jd_requirements.get("all_skills", [])

    gaps: List[SkillGap] = []
    seen: Set[str] = set()

    for skill in all_jd_skills:
        skill_lower = skill.lower()
        if skill_lower in seen:
            continue
        seen.add(skill_lower)

        if skill_lower not in resume_skills_lower:
            importance = classify_importance(skill, required_skills, preferred_skills)
            category = get_skill_category(skill)
            gaps.append(
                SkillGap(
                    skill=skill,
                    category=category,
                    importance=importance,
                )
            )

    # Sort by importance: critical first, then recommended, then nice-to-have
    importance_order = {"critical": 0, "recommended": 1, "nice-to-have": 2}
    gaps.sort(key=lambda g: importance_order.get(g.importance, 2))

    return gaps


def classify_importance(
    skill: str,
    required_skills: List[str],
    preferred_skills: List[str],
) -> str:
    """Classify a skill's importance level.

    Args:
        skill: The skill to classify.
        required_skills: Skills explicitly required by the JD.
        preferred_skills: Skills preferred but not required.

    Returns:
        One of 'critical', 'recommended', or 'nice-to-have'.
    """
    skill_lower = skill.lower()
    required_lower = {s.lower() for s in required_skills}
    preferred_lower = {s.lower() for s in preferred_skills}

    if skill_lower in required_lower:
        return "critical"
    elif skill_lower in preferred_lower:
        return "recommended"
    else:
        return "nice-to-have"


def get_skills_overlap_data(
    resume_skills: List[str],
    jd_requirements: Dict[str, Any],
) -> List[Dict[str, float]]:
    """Build data for the skills radar/overlap chart.

    Args:
        resume_skills: Skills found in the resume.
        jd_requirements: Parsed job requirements.

    Returns:
        List of dicts with subject, resume, jd values for RadarChart.
    """
    all_jd_skills = jd_requirements.get("all_skills", [])
    resume_skills_lower = {s.lower() for s in resume_skills}

    # Group skills by category and compute coverage
    categories = {
        "Technical": 0,
        "Tool": 0,
        "Soft": 0,
        "Certification": 0,
    }
    jd_counts = {k: 0 for k in categories}
    resume_counts = {k: 0 for k in categories}

    for skill in all_jd_skills:
        category = get_skill_category(skill)
        if category in jd_counts:
            jd_counts[category] += 1
            if skill.lower() in resume_skills_lower:
                resume_counts[category] += 1

    # Add some resume-only categories
    for skill in resume_skills:
        category = get_skill_category(skill)
        if category in resume_counts:
            if skill.lower() not in {s.lower() for s in all_jd_skills}:
                resume_counts[category] = min(resume_counts[category] + 1, 10)

    result = []
    label_map = {
        "Technical": "Technical Skills",
        "Tool": "Tools & Platforms",
        "Soft": "Soft Skills",
        "Certification": "Certifications",
    }

    for category, label in label_map.items():
        jd_val = min(jd_counts[category], 10)
        resume_val = min(resume_counts[category], 10)
        # Normalize to 0-100
        result.append({
            "subject": label,
            "resume": (resume_val / max(jd_val, 1)) * 100,
            "jd": 100,
        })

    return result
