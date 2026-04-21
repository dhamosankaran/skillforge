"""Cover letter generation endpoint."""
from fastapi import APIRouter, HTTPException
from app.core.analytics import track as analytics_track
from app.core.config import get_settings
from app.models.request_models import CoverLetterRequest
from app.models.response_models import CoverLetterResponse
from app.services.gpt_service import (
    CoverLetterError,
    generate_cover_letter as gpt_cover_letter,
)
from app.services.nlp import extract_job_requirements

router = APIRouter()


@router.post("/cover-letter", response_model=CoverLetterResponse)
async def generate_cover_letter(body: CoverLetterRequest) -> CoverLetterResponse:
    """Generate a structured cover letter (spec #52)."""
    resume_data = {"full_text": body.resume_text}
    jd_requirements = extract_job_requirements(body.job_description)

    try:
        result = gpt_cover_letter(resume_data, jd_requirements, body.tone)
    except CoverLetterError as e:
        # Spec #52 §9 — emit cover_letter_failed before raising the
        # spec #LD-6 / AC-5 structured 502 envelope. Never silent fallback.
        analytics_track(
            user_id=None,
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
        user_id=None,
        event="cover_letter_succeeded",
        properties={
            "tone": body.tone,
            "body_paragraphs_count": len(result.body_paragraphs),
            "model_used": get_settings().llm_reasoning_model,
        },
    )
    return result
