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
from app.services.analysis_service import score_resume_against_jd
from app.services.nlp import extract_job_requirements
from app.services.parser import parse_docx, parse_pdf
from app.services import home_state_service
from app.services.tracker_service_v2 import (
    create_application,
    find_by_scan_id,
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
            await create_application(
                tracker_data,
                db,
                user_id=current_user.id,
                skills_matched=response.matched_keywords,
                skills_missing=response.missing_keywords,
                analysis_payload=response.model_dump(mode="json"),
                jd_text=job_description,
                jd_hash=hash_jd(job_description),
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
