"""Interview question set storage + cache-aware generation.

Per spec #49. Wraps the existing `gpt_service.generate_interview_questions`
LLM call with a (user_id, jd_hash)-keyed cache in `interview_question_sets`.

Cache hits skip both the LLM call and the free-tier counter; new generations
call `check_and_increment(... , "interview_prep", ...)` and persist the result.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.interview_question_set import InterviewQuestionSet
from app.schemas.responses import InterviewPrepResponse, InterviewQuestion
from app.services.nlp import extract_job_requirements
from app.services.usage_service import check_and_increment
from app.utils.text_hash import hash_jd


@dataclass
class InterviewGenerationResult:
    questions: List[InterviewQuestion]
    cached: bool
    generated_at: datetime
    model_used: str | None


async def generate_or_get_interview_set(
    *,
    user_id: str,
    resume_text: str,
    job_description: str,
    force_regenerate: bool,
    db: AsyncSession,
) -> InterviewGenerationResult:
    """Return a cached set on hit; generate + persist on miss or force."""
    jd_hash = hash_jd(job_description)

    existing = await db.execute(
        select(InterviewQuestionSet).where(
            InterviewQuestionSet.user_id == user_id,
            InterviewQuestionSet.jd_hash == jd_hash,
        )
    )
    row = existing.scalar_one_or_none()

    if row is not None and not force_regenerate:
        return InterviewGenerationResult(
            questions=[InterviewQuestion(**q) for q in row.questions],
            cached=True,
            generated_at=row.generated_at,
            model_used=row.model_used,
        )

    usage = await check_and_increment(user_id, "interview_prep", db)
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

    result = _call_llm(resume_text, job_description)
    model_used = getattr(get_settings(), "llm_reasoning_model", None) or ""
    questions_payload: List[Dict[str, Any]] = [
        {"question": q.question, "star_framework": q.star_framework}
        for q in result.questions
    ]

    if row is None:
        row = InterviewQuestionSet(
            user_id=user_id,
            jd_hash=jd_hash,
            jd_text=job_description,
            questions=questions_payload,
            model_used=model_used or None,
        )
        db.add(row)
    else:
        row.jd_text = job_description
        row.questions = questions_payload
        row.model_used = model_used or None
        row.generated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(row)

    return InterviewGenerationResult(
        questions=result.questions,
        cached=False,
        generated_at=row.generated_at,
        model_used=row.model_used,
    )


def _call_llm(resume_text: str, job_description: str) -> InterviewPrepResponse:
    # Local import so tests can monkeypatch `gpt_service.generate_interview_questions`.
    from app.services.gpt_service import generate_interview_questions

    resume_data = {"full_text": resume_text}
    jd_requirements = extract_job_requirements(job_description)
    return generate_interview_questions(resume_data, jd_requirements)
