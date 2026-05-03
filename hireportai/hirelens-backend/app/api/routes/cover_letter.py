"""Cover letter generation endpoint."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.request_models import CoverLetterRequest
from app.models.response_models import CoverLetterResponse
from app.models.user import User
from app.services.gpt_service import (
    CoverLetterError,
    generate_cover_letter as gpt_cover_letter,
)
from app.services.nlp import extract_job_requirements
from app.services.usage_service import check_and_increment

router = APIRouter()


@router.post("/cover-letter", response_model=CoverLetterResponse)
@limiter.limit("10/minute")
async def generate_cover_letter(
    request: Request,
    body: CoverLetterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CoverLetterResponse:
    """Generate a structured cover letter (spec #52).

    Quota: spec #58 §4.1 — `"cover_letter"` bucket, separate from the
    `"rewrite"` bucket (D1 hybrid). Pro / Enterprise / admin unlimited;
    free tier capped at 0 lifetime (LD-2 Pro-only) so every free-plan
    call returns 402 with `trigger="cover_letter_limit"`.
    """
    usage = await check_and_increment(
        current_user.id, "cover_letter", db, window="lifetime"
    )
    if not usage["allowed"]:
        analytics_track(
            user_id=current_user.id,
            event="cover_letter_limit_hit",
            properties={
                "plan": usage["plan"],
                "auth_status": "authed",
            },
        )
        raise HTTPException(
            status_code=402,
            detail={
                "error": "free_tier_limit",
                "trigger": "cover_letter_limit",
                "feature": "cover_letter",
                "plan": usage["plan"],
                "used": usage["used"],
                "limit": usage["limit"],
            },
        )

    resume_data = {"full_text": body.resume_text}
    jd_requirements = extract_job_requirements(body.job_description)

    try:
        result = gpt_cover_letter(resume_data, jd_requirements, body.tone)
    except CoverLetterError as e:
        # Spec #52 §9 — emit cover_letter_failed before raising the
        # spec #LD-6 / AC-5 structured 502 envelope. Never silent fallback.
        analytics_track(
            user_id=current_user.id,
            event="cover_letter_failed",
            properties={"error_code": e.error_code, "tone": body.tone},
        )
        raise HTTPException(
            status_code=502,
            detail={
                "error": e.error_code,
                "message": e.message,
                "retry_hint": e.retry_hint,
            },
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    analytics_track(
        user_id=current_user.id,
        event="cover_letter_succeeded",
        properties={
            "tone": body.tone,
            "body_paragraphs_count": len(result.body_paragraphs),
            "model_used": get_settings().llm_reasoning_model,
        },
    )
    return result
