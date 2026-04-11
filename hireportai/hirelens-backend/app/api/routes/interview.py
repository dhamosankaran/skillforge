"""Interview prep generation endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_optional
from app.db.session import get_db
from app.models.request_models import InterviewPrepRequest
from app.models.response_models import InterviewPrepResponse
from app.models.user import User
from app.services.nlp import extract_job_requirements
from app.services.usage_service import check_and_increment

router = APIRouter()


@router.post("/interview-prep", response_model=InterviewPrepResponse)
async def generate_interview_prep(
    body: InterviewPrepRequest,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> InterviewPrepResponse:
    """Generate likely interview questions with STAR method answer frameworks."""
    # Enforce usage limits for authenticated users
    if current_user:
        usage = await check_and_increment(current_user.id, "interview_prep", db)
        if not usage["allowed"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "detail": "Free limit reached",
                    "code": "LIMIT_REACHED",
                    "limit": usage["limit"],
                    "remaining": 0,
                    "upgrade_url": "/pricing",
                },
            )

    resume_data = {"full_text": body.resume_text}
    jd_requirements = extract_job_requirements(body.job_description)

    try:
        from app.services.gpt_service import generate_interview_questions
        result = generate_interview_questions(resume_data, jd_requirements)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interview prep generation failed: {str(e)}")
