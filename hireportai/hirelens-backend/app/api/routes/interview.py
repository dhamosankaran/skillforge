"""Interview prep generation endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_optional
from app.db.session import get_db
from app.models.request_models import InterviewPrepRequest
from app.models.response_models import InterviewPrepResponse
from app.models.user import User
from app.services.interview_storage_service import generate_or_get_interview_set
from app.services.nlp import extract_job_requirements
from app.services.usage_service import check_and_increment

router = APIRouter()


@router.post("/interview-prep", response_model=InterviewPrepResponse)
async def generate_interview_prep(
    body: InterviewPrepRequest,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> InterviewPrepResponse:
    """Generate likely interview questions with STAR method answer frameworks.

    For authenticated callers, serves cached sets keyed on (user_id, jd_hash)
    (spec #49). Cache hits skip the LLM and do not decrement the free-tier
    counter. `force_regenerate=true` bypasses the cache.
    """
    if current_user is not None:
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

    # Anonymous callers: preserve today's behavior — no cache, gate-free generation.
    resume_data = {"full_text": body.resume_text}
    jd_requirements = extract_job_requirements(body.job_description)
    try:
        from app.services.gpt_service import generate_interview_questions

        result = generate_interview_questions(resume_data, jd_requirements)
        return InterviewPrepResponse(
            questions=result.questions,
            cached=False,
            generated_at="",
            model_used="",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:  # noqa: BLE001 — preserve legacy 500 behavior on any LLM error
        raise HTTPException(status_code=500, detail=f"Interview prep generation failed: {str(e)}")
