"""Interview prep generation endpoint."""
from fastapi import APIRouter, HTTPException
from app.models.request_models import InterviewPrepRequest
from app.models.response_models import InterviewPrepResponse
from app.services.nlp import extract_job_requirements

router = APIRouter()


@router.post("/interview-prep", response_model=InterviewPrepResponse)
async def generate_interview_prep(body: InterviewPrepRequest) -> InterviewPrepResponse:
    """Generate likely interview questions with STAR method answer frameworks."""
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
