"""Resume↔JD scoring pipeline (E-043 / spec #63 G-6 extraction).

Foundation half (B-086a). The scoring orchestration was previously
inlined inside ``app/api/routes/analyze.py::analyze_resume``; this
module lifts the file-format-agnostic half so both ``/analyze``
(file-upload entry) and ``/rescan`` (text-input entry, lands B-086b)
share the same pipeline.

AC-17 invariant: the /analyze route post-extraction must produce a
byte-identical ``AnalysisResponse`` to the pre-extraction code path.
The optional ``parsed_resume`` kwarg threads file-derived hints
(``formatting_hints`` + ``bullet_points``) through so the file-upload
path keeps its visual-formatting + bullet-extraction quality.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.models.response_models import (
    AnalysisResponse,
    ATSScoreBreakdown,
    KeywordChartData,
    SkillOverlapData,
)
from app.services.bullet_analyzer import analyze_bullets
from app.services.formatter_check import check_formatting
from app.services.gap_detector import detect_gaps, get_skills_overlap_data
from app.services.keywords import get_keyword_chart_data, match_keywords
from app.services.nlp import extract_job_requirements, extract_skills
from app.services.scorer import ATSScorer


_scorer = ATSScorer()


async def score_resume_against_jd(
    resume_text: str,
    jd_text: str,
    db: AsyncSession,
    *,
    user_id: Optional[str] = None,
    prior_scan_id: Optional[str] = None,
    parsed_resume: Optional[dict] = None,
) -> AnalysisResponse:
    """Run the full ATS scoring pipeline for one resume against one JD.

    Mints a fresh ``scan_id`` (UUID4) on every call. ``prior_scan_id``
    is accepted for B-086b telemetry threading but unused in v1 (the
    re-scan loop's "before" anchor is the tracker row's existing
    ``scan_id``, read by the route handler before calling this helper).

    ``parsed_resume`` carries the dict shape returned by
    ``parse_pdf`` / ``parse_docx``: ``{"full_text", "formatting_hints",
    "bullet_points", ...}``. /analyze passes the file-parsed dict;
    /rescan (B-086b) passes ``None`` and accepts degraded formatting +
    bullet analysis since text-only input lacks file-format hints.
    """
    if parsed_resume is None:
        parsed_resume = {
            "full_text": resume_text,
            "formatting_hints": {},
            "bullet_points": [],
        }

    resume_skills = extract_skills(resume_text)
    parsed_resume["skills"] = resume_skills

    jd_requirements = extract_job_requirements(jd_text)
    jd_skills = jd_requirements.get("all_skills", [])

    keyword_results = match_keywords(
        resume_text=resume_text,
        jd_text=jd_text,
        jd_skills=jd_skills,
    )
    matched_keywords: List[str] = keyword_results["matched"]
    missing_keywords: List[str] = keyword_results["missing"]
    jd_keywords: List[str] = keyword_results["jd_keywords"]

    formatting_hints = parsed_resume.get("formatting_hints", {})
    formatting_issues_raw = check_formatting(parsed_resume, formatting_hints)
    formatting_issues_dicts = [fi.model_dump() for fi in formatting_issues_raw]

    bullets_raw = parsed_resume.get("bullet_points", [])
    bullet_analyses = analyze_bullets(bullets_raw, jd_text)
    bullet_dicts = [ba.model_dump() for ba in bullet_analyses]

    score_result = _scorer.score(
        matched_keywords=matched_keywords,
        jd_keywords=jd_keywords,
        resume_skills=resume_skills,
        jd_skills=jd_skills,
        formatting_issues=formatting_issues_dicts,
        bullets=bullet_dicts,
    )

    skill_gaps = detect_gaps(resume_skills, jd_requirements)
    skills_overlap = get_skills_overlap_data(resume_skills, jd_requirements)
    keyword_chart = get_keyword_chart_data(keyword_results["frequency_data"])

    job_fit_explanation = ""
    top_strengths: List[str] = []
    top_gaps: List[str] = []

    try:
        from app.services.gpt_service import generate_job_fit_explanation

        gpt_result = generate_job_fit_explanation(
            resume_data=parsed_resume,
            jd_requirements=jd_requirements,
            ats_score=score_result["total"],
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
        )
        job_fit_explanation = gpt_result.get("explanation", "")
        top_strengths = gpt_result.get("top_strengths", [])
        top_gaps = gpt_result.get("top_gaps", [])
    except Exception:
        job_fit_explanation = (
            f"Your resume achieved an ATS score of {score_result['total']}/100 for this role. "
            f"You matched {len(matched_keywords)} of {len(jd_keywords)} key terms. "
            f"Focus on incorporating the missing keywords naturally into your experience descriptions."
        )
        top_strengths = (
            matched_keywords[:3] if matched_keywords else ["Relevant experience present"]
        )
        top_gaps = (
            missing_keywords[:3]
            if missing_keywords
            else ["Add more role-specific keywords"]
        )

    scan_id = str(uuid.uuid4())

    analytics_track(
        user_id=user_id,
        event="ats_scanned",
        properties={
            "score": score_result["total"],
            "grade": score_result["grade"],
            "gaps_found": len(skill_gaps),
            "matched_keywords": len(matched_keywords),
            "missing_keywords": len(missing_keywords),
        },
    )

    return AnalysisResponse(
        scan_id=scan_id,
        ats_score=score_result["total"],
        grade=score_result["grade"],
        score_breakdown=ATSScoreBreakdown(**score_result["breakdown"]),
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        skill_gaps=skill_gaps,
        bullet_analysis=bullet_analyses,
        formatting_issues=formatting_issues_raw,
        job_fit_explanation=job_fit_explanation,
        top_strengths=top_strengths,
        top_gaps=top_gaps,
        keyword_chart_data=[KeywordChartData(**kcd) for kcd in keyword_chart],
        skills_overlap_data=[SkillOverlapData(**sod) for sod in skills_overlap],
        resume_text=resume_text,
    )
