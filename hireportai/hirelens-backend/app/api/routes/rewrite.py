"""Resume rewrite endpoint."""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.analytics import track as analytics_track
from app.models.request_models import RewriteRequest
from app.models.response_models import RewriteResponse, RewriteSection
from app.services.nlp import extract_job_requirements, extract_skills
from app.services.keywords import match_keywords

logger = logging.getLogger(__name__)
router = APIRouter()


class SectionRewriteRequest(BaseModel):
    """Request body for per-section regenerate (spec #51 §6.2)."""

    section_id: str = Field(..., min_length=1, max_length=128)
    section_title: str = Field(..., min_length=1, max_length=200)
    section_text: str = Field(..., min_length=1)
    jd_text: str = Field(..., min_length=1)
    missing_keywords: Optional[List[str]] = Field(default=None)


class SectionRewriteResponse(BaseModel):
    """Response for per-section regenerate."""

    section_id: str
    section: RewriteSection


def _rewrite_error_body(error_code: str, message: str, retry_hint: str) -> dict:
    """AC-5 structured error envelope."""
    return {
        "error": error_code,
        "message": message,
        "retry_hint": retry_hint,
    }


@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_resume(body: RewriteRequest) -> RewriteResponse:
    """Generate an ATS-optimized rewrite tailored to the candidate's resume."""
    try:
        from app.services.gpt_service import (
            RewriteError,
            generate_resume_rewrite_async,
        )
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

    keyword_results = match_keywords(
        resume_text=body.resume_text,
        jd_text=body.job_description,
        jd_skills=jd_skills,
    )
    missing_keywords = keyword_results.get("missing", [])

    resume_skills_lower = {s.lower() for s in resume_skills}
    missing_skills = [s for s in jd_skills if s.lower() not in resume_skills_lower]

    resume_chars = len(body.resume_text)
    try:
        result, path = await generate_resume_rewrite_async(
            resume_data,
            jd_requirements,
            template_type=body.template_type or "general",
            major=body.major,
            missing_keywords=missing_keywords,
            missing_skills=missing_skills,
        )
    except RewriteError as exc:
        analytics_track(
            user_id=None,
            event="rewrite_failed",
            properties={
                "reason": exc.error_code,
                "resume_chars": resume_chars,
            },
        )
        logger.warning(
            "rewrite_failed: reason=%s resume_chars=%d", exc.error_code, resume_chars
        )
        raise HTTPException(
            status_code=502,
            detail=_rewrite_error_body(exc.error_code, exc.message, exc.retry_hint),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected rewrite failure")
        raise HTTPException(
            status_code=500,
            detail=_rewrite_error_body(
                "rewrite_llm_error", f"Rewrite failed: {e}", "contact_support"
            ),
        )

    output_chars = len(result.full_text)
    analytics_track(
        user_id=None,
        event="rewrite_succeeded",
        properties={
            "resume_chars": resume_chars,
            "output_chars": output_chars,
            "sections_count": len(result.sections),
            "strategy": path,
            "template_type": body.template_type or "general",
        },
    )
    # Operational logging (spec #51 §9): input/output sizes for first-week
    # histogram review. Remove once the distribution is understood.
    logger.info(
        "rewrite_succeeded: path=%s resume_chars=%d output_chars=%d sections=%d",
        path,
        resume_chars,
        output_chars,
        len(result.sections),
    )
    return result


@router.post("/rewrite/section", response_model=SectionRewriteResponse)
async def rewrite_section(body: SectionRewriteRequest) -> SectionRewriteResponse:
    """Regenerate a single section of the resume (spec #51 §6.2)."""
    try:
        from app.services.gpt_service import (
            RewriteError,
            generate_section_rewrite,
        )
    except ImportError:
        raise HTTPException(status_code=501, detail="GPT service not available.")

    try:
        section = await generate_section_rewrite(
            section_id=body.section_id,
            section_title=body.section_title,
            section_text=body.section_text,
            jd_text=body.jd_text,
            missing_keywords=body.missing_keywords,
        )
    except RewriteError as exc:
        analytics_track(
            user_id=None,
            event="rewrite_failed",
            properties={
                "reason": exc.error_code,
                "surface": "section",
                "section_title": body.section_title,
            },
        )
        raise HTTPException(
            status_code=502,
            detail=_rewrite_error_body(exc.error_code, exc.message, exc.retry_hint),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected section rewrite failure")
        raise HTTPException(
            status_code=500,
            detail=_rewrite_error_body(
                "rewrite_llm_error", f"Section rewrite failed: {e}", "contact_support"
            ),
        )

    logger.info(
        "rewrite_section_succeeded: section_title=%s output_chars=%d",
        body.section_title,
        len(section.content),
    )
    return SectionRewriteResponse(section_id=body.section_id, section=section)
