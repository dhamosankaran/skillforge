"""Core resume analysis endpoint."""
import json
import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.response_models import (
    AnalysisResponse,
    ATSScoreBreakdown,
    BulletAnalysis,
    FormattingIssue,
    KeywordChartData,
    SkillGap,
    SkillOverlapData,
)
from app.core.analytics import track as analytics_track
from app.core.deps import get_current_user_optional
from app.db.session import get_db
from app.models.user import User
from app.schemas.requests import TrackerApplicationCreate
from app.services.bullet_analyzer import analyze_bullets
from app.services.formatter_check import check_formatting
from app.services.gap_detector import detect_gaps, get_skills_overlap_data
from app.services.keywords import get_keyword_chart_data, match_keywords
from app.services.nlp import extract_job_requirements, extract_skills
from app.services.parser import parse_docx, parse_pdf
from app.services.scorer import ATSScorer
from app.services import home_state_service
from app.services.tracker_service_v2 import create_application, find_by_scan_id
from app.services.usage_service import check_and_increment

router = APIRouter()
scorer = ATSScorer()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",  # Some browsers send this for .docx
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume(
    resume_file: UploadFile = File(..., description="Resume file (PDF or DOCX)"),
    job_description: str = Form(..., description="Job description text"),
    run_rewrite: bool = Form(default=False),
    run_cover_letter: bool = Form(default=False),
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """Analyze a resume against a job description and return full ATS analysis.

    This is the core endpoint that orchestrates:
    1. File parsing (PDF/DOCX)
    2. NLP processing
    3. Keyword extraction and matching
    4. ATS scoring
    5. Skill gap detection
    6. Bullet point analysis
    7. Formatting compliance check
    8. Optional GPT-powered explanations
    """
    # Free-tier lifetime scan cap (spec #56 / B-031). Anonymous scans bypass —
    # spec §10 scopes this cap to authenticated free users only. Admin + Pro +
    # Enterprise short-circuit inside `check_and_increment`. On 402 we mirror
    # spec #50's `DailyReviewLimitError` payload shape exactly (error / trigger /
    # counter fields / plan) so the FE axios interceptor unwraps it identically.
    if current_user is not None:
        usage = await check_and_increment(
            current_user.id, "analyze", db, window="lifetime"
        )
        if not usage["allowed"]:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "free_tier_limit",
                    "trigger": "scan_limit",
                    "scans_used": usage["used"],
                    "scans_limit": usage["limit"],
                    "plan": usage["plan"],
                },
            )

    # Validate file type
    filename = resume_file.filename or ""
    if not (filename.endswith(".pdf") or filename.endswith(".docx")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF and DOCX files are accepted.",
        )

    # Read file bytes
    file_bytes = await resume_file.read()

    # Validate file size
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum allowed size is 5MB.",
        )

    if len(file_bytes) < 100:
        raise HTTPException(
            status_code=400,
            detail="File appears to be empty or corrupted.",
        )

    # Parse resume
    try:
        if filename.endswith(".pdf"):
            resume_data = parse_pdf(file_bytes)
        else:
            resume_data = parse_docx(file_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse resume file: {str(e)}",
        )

    resume_text = resume_data.get("full_text", "")
    if len(resume_text) < 50:
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from the resume. Please ensure the file is not image-only or password-protected.",
        )

    if len(job_description.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Job description is too short. Please provide a complete job description.",
        )

    # Extract resume skills
    resume_skills = extract_skills(resume_text)
    resume_data["skills"] = resume_skills

    # Parse job description
    jd_requirements = extract_job_requirements(job_description)
    jd_skills = jd_requirements.get("all_skills", [])

    # Keyword matching
    keyword_results = match_keywords(
        resume_text=resume_text,
        jd_text=job_description,
        jd_skills=jd_skills,
    )
    matched_keywords: List[str] = keyword_results["matched"]
    missing_keywords: List[str] = keyword_results["missing"]
    jd_keywords: List[str] = keyword_results["jd_keywords"]

    # Formatting check
    formatting_hints = resume_data.get("formatting_hints", {})
    formatting_issues_raw = check_formatting(resume_data, formatting_hints)
    formatting_issues_dicts = [fi.model_dump() for fi in formatting_issues_raw]

    # Bullet analysis
    bullets_raw = resume_data.get("bullet_points", [])
    bullet_analyses = analyze_bullets(bullets_raw, job_description)
    bullet_dicts = [ba.model_dump() for ba in bullet_analyses]

    # Calculate ATS score
    score_result = scorer.score(
        matched_keywords=matched_keywords,
        jd_keywords=jd_keywords,
        resume_skills=resume_skills,
        jd_skills=jd_skills,
        formatting_issues=formatting_issues_dicts,
        bullets=bullet_dicts,
    )

    # Skill gap detection
    skill_gaps = detect_gaps(resume_skills, jd_requirements)

    # Skills overlap data for radar chart
    skills_overlap = get_skills_overlap_data(resume_skills, jd_requirements)

    # Keyword chart data
    keyword_chart = get_keyword_chart_data(keyword_results["frequency_data"])

    # GPT-powered job fit explanation (optional, falls back gracefully)
    job_fit_explanation = ""
    top_strengths: List[str] = []
    top_gaps: List[str] = []

    try:
        from app.services.gpt_service import generate_job_fit_explanation
        gpt_result = generate_job_fit_explanation(
            resume_data=resume_data,
            jd_requirements=jd_requirements,
            ats_score=score_result["total"],
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
        )
        job_fit_explanation = gpt_result.get("explanation", "")
        top_strengths = gpt_result.get("top_strengths", [])
        top_gaps = gpt_result.get("top_gaps", [])
    except Exception:
        # Non-GPT fallback
        job_fit_explanation = (
            f"Your resume achieved an ATS score of {score_result['total']}/100 for this role. "
            f"You matched {len(matched_keywords)} of {len(jd_keywords)} key terms. "
            f"Focus on incorporating the missing keywords naturally into your experience descriptions."
        )
        top_strengths = matched_keywords[:3] if matched_keywords else ["Relevant experience present"]
        top_gaps = missing_keywords[:3] if missing_keywords else ["Add more role-specific keywords"]

    scan_id = str(uuid.uuid4())

    analytics_track(
        user_id=current_user.id if current_user else None,
        event="ats_scanned",
        properties={
            "score": score_result["total"],
            "grade": score_result["grade"],
            "gaps_found": len(skill_gaps),
            "matched_keywords": len(matched_keywords),
            "missing_keywords": len(missing_keywords),
        },
    )

    # Auto-populate the job tracker for authenticated users
    if current_user:
        existing = await find_by_scan_id(scan_id, db, user_id=current_user.id)
        if not existing:
            # Extract company/position from JD requirements
            company = jd_requirements.get("company_name") or "Unknown Company"
            position = jd_requirements.get("job_title") or "Position from scan"

            tracker_data = TrackerApplicationCreate(
                company=company[:200],
                role=position[:200],
                date_applied=date.today().isoformat(),
                ats_score=score_result["total"],
                status="Applied",
                scan_id=scan_id,
            )
            await create_application(
                tracker_data,
                db,
                user_id=current_user.id,
                skills_matched=matched_keywords,
                skills_missing=missing_keywords,
            )
            analytics_track(
                user_id=current_user.id,
                event="tracker_auto_created_from_scan",
                properties={
                    "ats_score": score_result["total"],
                    "gaps_count": len(skill_gaps),
                },
            )
        home_state_service.invalidate(current_user.id)

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
