"""Core resume analysis endpoint."""
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.response_models import AnalysisResponse
from app.core.analytics import track as analytics_track
from app.core.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.user import User
from app.schemas.requests import TrackerApplicationCreate
from app.schemas.rescan import RescanRequest
from app.services.analysis_service import score_resume_against_jd
from app.services.nlp import extract_job_requirements
from app.services.parser import parse_docx, parse_pdf
from app.services import (
    home_state_service,
    tracker_application_score_service,
)
from app.services.tracker_service_v2 import (
    create_application,
    find_by_scan_id,
    get_application_model_by_id,
    get_scan_by_id,
)
from app.services.usage_service import check_and_increment
from app.utils.text_hash import hash_jd

router = APIRouter()

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

    # G-6 extraction (E-043 / spec #63 §6.1) — file parsing stays in the
    # route; the file-format-agnostic scoring pipeline lives in
    # `app/services/analysis_service.py` so /rescan (B-086b) can reuse it
    # with text-only input. The `parsed_resume` kwarg threads file-derived
    # `formatting_hints` + `bullet_points` through to preserve AC-17
    # byte-identity for the file-upload path.
    response = await score_resume_against_jd(
        resume_text=resume_text,
        jd_text=job_description,
        db=db,
        user_id=current_user.id if current_user else None,
        parsed_resume=resume_data,
    )

    # Auto-populate the job tracker for authenticated users. Spec #63 §6.1
    # write hook: post-migration tracker rows always carry `jd_text` +
    # `jd_hash` (D-9 422 path becomes unreachable for new rows; only
    # pre-migration rows fall through to it).
    if current_user:
        existing = await find_by_scan_id(response.scan_id, db, user_id=current_user.id)
        if not existing:
            jd_requirements = extract_job_requirements(job_description)
            company = jd_requirements.get("company_name") or "Unknown Company"
            position = jd_requirements.get("job_title") or "Position from scan"

            tracker_data = TrackerApplicationCreate(
                company=company[:200],
                role=position[:200],
                date_applied=date.today().isoformat(),
                ats_score=response.ats_score,
                status="Applied",
                scan_id=response.scan_id,
            )
            new_tracker = await create_application(
                tracker_data,
                db,
                user_id=current_user.id,
                skills_matched=response.matched_keywords,
                skills_missing=response.missing_keywords,
                analysis_payload=response.model_dump(mode="json"),
                jd_text=job_description,
                jd_hash=hash_jd(job_description),
            )
            # Spec #63 §16.6 R-5 / §6.3 — REQUIRED baseline write so the first
            # /rescan after /analyze lands history.length=2 (delta envelope
            # non-degenerate; HomeScoreDeltaWidget renders without two
            # rescans).
            await tracker_application_score_service.write_score_row(
                tracker_application_id=new_tracker.id,
                user_id=current_user.id,
                response=response,
                scan_id=response.scan_id,
                jd_hash=hash_jd(job_description),
                resume_hash=hash_jd(resume_text),
                db=db,
            )
            analytics_track(
                user_id=current_user.id,
                event="tracker_auto_created_from_scan",
                properties={
                    "ats_score": response.ats_score,
                    "gaps_count": len(response.skill_gaps),
                },
            )
        home_state_service.invalidate(current_user.id)

    return response


@router.post("/analyze/rescan", response_model=AnalysisResponse)
async def rescan_application(
    request: RescanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """Re-score an existing tracker application against an updated resume.

    Spec #63 (E-043) §6.2 — orchestrator half (B-086b). Auth required
    (NOT optional, unlike legacy /analyze): re-scan is by definition a
    user-owned operation against a tracker row. Slowapi default rate
    limit (100/min) inherits per §12 D-8 — no per-route override.

    Flow:
      1. Fetch + verify ownership of the tracker row.
      2. 422 if `jd_text` is NULL (pre-migration row, §12 D-9).
      3. Compute `(jd_hash, resume_hash)`; short-circuit on dedupe match
         (§12 D-2 — return existing scores, fire `rescan_short_circuited`,
         do NOT consume the lifetime counter).
      4. Counter (§12 D-1 / G-7) — same `"analyze"` lifetime counter as
         fresh scans.
      5. Score via the G-6 helper.
      6. Persist score row + flip tracker `ats_score` (transactional).
      7. Fire `rescan_completed` with the per-axis delta envelope (§12
         D-12).
    """
    row = await get_application_model_by_id(
        request.tracker_application_id, db, user_id=current_user.id
    )
    if row is None:
        analytics_track(
            user_id=current_user.id,
            event="rescan_failed",
            properties={
                "tracker_application_id": request.tracker_application_id,
                "error_class": "not_found",
            },
        )
        raise HTTPException(
            status_code=404,
            detail={"error": "tracker_not_found"},
        )

    if row.jd_text is None:
        analytics_track(
            user_id=current_user.id,
            event="rescan_failed",
            properties={
                "tracker_application_id": request.tracker_application_id,
                "error_class": "jd_missing",
            },
        )
        raise HTTPException(
            status_code=422,
            detail={
                "error": "jd_text_missing",
                "message": (
                    "JD text not stored on this tracker — please run a "
                    "fresh scan to populate."
                ),
            },
        )

    resume_hash = hash_jd(request.resume_text)
    jd_hash = row.jd_hash or hash_jd(row.jd_text)

    existing = await tracker_application_score_service.find_by_dedupe(
        tracker_application_id=request.tracker_application_id,
        jd_hash=jd_hash,
        resume_hash=resume_hash,
        db=db,
    )
    if existing is not None:
        analytics_track(
            user_id=current_user.id,
            event="rescan_short_circuited",
            properties={
                "tracker_application_id": request.tracker_application_id,
                "jd_hash_prefix": jd_hash[:8],
            },
        )
        return AnalysisResponse(
            scan_id=existing.scan_id or "",
            ats_score=existing.overall_score,
            grade="",
            score_breakdown={
                "keyword_match": existing.keyword_match_score,
                "skills_coverage": existing.skills_coverage_score,
                "formatting_compliance": existing.formatting_compliance_score,
                "bullet_strength": existing.bullet_strength_score,
            },
            matched_keywords=[],
            missing_keywords=[],
            skill_gaps=[],
            bullet_analysis=[],
            formatting_issues=[],
            job_fit_explanation="",
            top_strengths=[],
            top_gaps=[],
            keyword_chart_data=[],
            skills_overlap_data=[],
            resume_text=request.resume_text,
        )

    usage = await check_and_increment(
        current_user.id, "analyze", db, window="lifetime"
    )
    if not usage["allowed"]:
        analytics_track(
            user_id=current_user.id,
            event="rescan_failed",
            properties={
                "tracker_application_id": request.tracker_application_id,
                "error_class": "paywall",
            },
        )
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

    analytics_track(
        user_id=current_user.id,
        event="rescan_initiated",
        properties={
            "tracker_application_id": request.tracker_application_id,
        },
    )

    try:
        response = await score_resume_against_jd(
            resume_text=request.resume_text,
            jd_text=row.jd_text,
            db=db,
            user_id=current_user.id,
            prior_scan_id=row.scan_id,
        )
    except Exception:
        analytics_track(
            user_id=current_user.id,
            event="rescan_failed",
            properties={
                "tracker_application_id": request.tracker_application_id,
                "error_class": "scoring_error",
            },
        )
        raise HTTPException(
            status_code=502,
            detail={"error": "scoring_failed"},
        )

    await tracker_application_score_service.write_score_row(
        tracker_application_id=request.tracker_application_id,
        user_id=current_user.id,
        response=response,
        scan_id=response.scan_id,
        jd_hash=jd_hash,
        resume_hash=resume_hash,
        db=db,
    )
    row.ats_score = response.ats_score

    history = await tracker_application_score_service.get_score_history(
        tracker_application_id=request.tracker_application_id,
        user_id=current_user.id,
        db=db,
    )
    delta = tracker_application_score_service.compute_delta(history)
    prior_overall = (
        history[-2].overall_score if len(history) >= 2 else None
    )
    analytics_track(
        user_id=current_user.id,
        event="rescan_completed",
        properties={
            "tracker_application_id": request.tracker_application_id,
            "scan_id": response.scan_id,
            "jd_hash_prefix": jd_hash[:8],
            "ats_score_before": prior_overall,
            "ats_score_after": response.ats_score,
            "ats_score_delta": delta.overall_delta if delta else None,
            "keyword_match_delta": (
                delta.keyword_match_delta if delta else None
            ),
            "skills_coverage_delta": (
                delta.skills_coverage_delta if delta else None
            ),
            "formatting_compliance_delta": (
                delta.formatting_compliance_delta if delta else None
            ),
            "bullet_strength_delta": (
                delta.bullet_strength_delta if delta else None
            ),
            "short_circuited": False,
        },
    )

    return response


@router.get("/analyze/{scan_id}", response_model=AnalysisResponse)
async def get_scan_analysis(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """Return the full stored AnalysisResponse for a scan owned by the
    current user.

    Spec #59. 404 if scan_id unknown OR owned by a different user (LD-4 —
    do not leak existence). 410 if the tracker row exists but
    `analysis_payload` is NULL (LD-5 — legacy row written before spec
    #59 shipped). 200 with the full payload otherwise.

    Mounted at both `/api/analyze/{scan_id}` (legacy) and
    `/api/v1/analyze/{scan_id}` (via v1 re-export shim) — the v1 path is
    the canonical one for new callers per spec §7.
    """
    row = await get_scan_by_id(scan_id=scan_id, db=db, user_id=current_user.id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "scan_not_found", "scan_id": scan_id},
        )
    if row.analysis_payload is None:
        raise HTTPException(
            status_code=410,
            detail={
                "error": "scan_payload_unavailable",
                "code": "legacy_scan_pre_persistence",
                "scan_id": scan_id,
                "message": (
                    "This scan was created before full results were stored."
                ),
            },
        )
    return AnalysisResponse(**row.analysis_payload)
