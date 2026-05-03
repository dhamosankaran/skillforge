"""Interview prep generation endpoint."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.request_models import InterviewPrepRequest
from app.models.response_models import InterviewPrepResponse
from app.models.user import User
from app.services.interview_storage_service import generate_or_get_interview_set

router = APIRouter()


@router.post("/interview-prep", response_model=InterviewPrepResponse)
@limiter.limit("10/minute")
async def generate_interview_prep(
    request: Request,
    body: InterviewPrepRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewPrepResponse:
    """Generate likely interview questions with STAR method answer frameworks.

    Cached sets are keyed on (user_id, jd_hash) per spec #49. Cache hits
    skip the LLM and do not decrement the free-tier counter.
    `force_regenerate=true` bypasses the cache. Anonymous callers are
    rejected with 401 (E-037) — Pro-tier LLM cost is gated by auth +
    monthly quota; rate limited to 10/min/IP defense-in-depth.
    """
    result = await generate_or_get_interview_set(
        user_id=current_user.id,
        resume_text=body.resume_text,
        job_description=body.job_description,
        force_regenerate=body.force_regenerate,
        db=db,
    )
    return InterviewPrepResponse(
        questions=result.questions,
        cached=result.cached,
        generated_at=result.generated_at.isoformat(),
        model_used=result.model_used or "",
    )
