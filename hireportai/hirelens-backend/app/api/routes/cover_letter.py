"""Cover letter generation endpoint."""
from fastapi import APIRouter, HTTPException
from app.core.analytics import track as analytics_track
from app.models.request_models import CoverLetterRequest
from app.models.response_models import CoverLetterResponse
from app.services.nlp import extract_job_requirements

router = APIRouter()


@router.post("/cover-letter", response_model=CoverLetterResponse)
async def generate_cover_letter(body: CoverLetterRequest) -> CoverLetterResponse:
    """Generate a personalized, ATS-friendly cover letter."""
    resume_data = {"full_text": body.resume_text}
    jd_requirements = extract_job_requirements(body.job_description)

    try:
        from app.services.gpt_service import generate_cover_letter as gpt_cover_letter
        result = gpt_cover_letter(resume_data, jd_requirements, body.tone)
        analytics_track(
            user_id=None,
            event="cover_letter_generated",
            properties={
                "tone": body.tone,
                "resume_chars": len(body.resume_text),
                "company_name_present": bool(jd_requirements.get("company_name")),
            },
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cover letter generation failed: {str(e)}")
