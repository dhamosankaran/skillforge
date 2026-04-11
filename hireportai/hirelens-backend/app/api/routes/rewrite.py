"""Resume rewrite endpoint."""
from fastapi import APIRouter, HTTPException
from app.models.request_models import RewriteRequest
from app.models.response_models import RewriteResponse
from app.services.nlp import extract_job_requirements, extract_skills
from app.services.keywords import match_keywords

router = APIRouter()


@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_resume(body: RewriteRequest) -> RewriteResponse:
    """Generate an ATS-optimized rewrite tailored to the candidate's resume."""
    try:
        from app.services.gpt_service import generate_resume_rewrite
    except ImportError:
        raise HTTPException(status_code=501, detail="GPT service not available.")

    resume_skills = extract_skills(body.resume_text)
    resume_data = {
        "full_text": body.resume_text,
        "skills": resume_skills,
        "sections": {},
    }
    jd_requirements = extract_job_requirements(body.job_description)
    jd_skills = jd_requirements.get("all_skills", [])

    # Run keyword gap analysis so the AI knows exactly what to incorporate
    keyword_results = match_keywords(
        resume_text=body.resume_text,
        jd_text=body.job_description,
        jd_skills=jd_skills,
    )
    missing_keywords = keyword_results.get("missing", [])

    # Find missing skills
    resume_skills_lower = {s.lower() for s in resume_skills}
    missing_skills = [s for s in jd_skills if s.lower() not in resume_skills_lower]

    try:
        result = generate_resume_rewrite(
            resume_data,
            jd_requirements,
            template_type=body.template_type or "general",
            major=body.major,
            missing_keywords=missing_keywords,
            missing_skills=missing_skills,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rewrite failed: {str(e)}")
