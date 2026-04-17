"""AI experience generator — turns study history into resume-ready narratives."""
import asyncio
import json

from fastapi import HTTPException, status
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.core.llm_router import generate_for_task

_PROMPT_TEMPLATE = """You are a career coach helping a software engineer write resume bullet points.

The engineer has been studying with a spaced-repetition system. Here are their stats:

Topic focus: {topic}
Categories studied: {categories}
Total cards studied: {cards_studied}
Total successful reviews: {total_reps}
Quiz accuracy: {accuracy}%

Generate a single, compelling resume/LinkedIn bullet point that:
1. Quantifies their demonstrated knowledge (use the actual numbers above)
2. Names the specific technical areas they've mastered
3. Reads naturally as a professional achievement
4. Is 1-2 sentences max

Return a JSON object:
{{
  "experience_text": "The bullet point text",
  "summary": "A 1-sentence plain summary of what they've mastered"
}}

Example output:
{{
  "experience_text": "Demonstrated deep proficiency in distributed systems and API design through completion of 85+ expert-curated assessments with 92% accuracy, covering microservices architecture, consensus algorithms, and fault tolerance patterns.",
  "summary": "Strong in distributed systems and API design."
}}"""


async def generate_experience(
    user_id: str,
    topic: str,
    db: AsyncSession,
) -> dict:
    """Generate a resume-ready experience narrative from the user's study history.

    Queries card_progress to build per-category stats, then calls the LLM
    to produce a polished bullet point. Returns dict with experience_text
    and summary.

    Raises HTTPException 503 if the LLM call fails.
    """
    # Gather per-category study stats for this user
    rows = (
        await db.execute(
            select(
                Category.name,
                sa_func.count(CardProgress.id).label("card_count"),
                sa_func.coalesce(sa_func.sum(CardProgress.reps), 0).label("reps"),
                sa_func.coalesce(sa_func.sum(CardProgress.lapses), 0).label("lapses"),
            )
            .join(Card, Card.id == CardProgress.card_id)
            .join(Category, Category.id == Card.category_id)
            .where(CardProgress.user_id == user_id)
            .where(CardProgress.state != "new")
            .group_by(Category.name)
            .order_by(sa_func.count(CardProgress.id).desc())
        )
    ).all()

    if not rows:
        return {
            "experience_text": "Start studying cards to generate your experience narrative.",
            "summary": "No study history yet.",
            "cards_studied": 0,
        }

    categories = [r.name for r in rows]
    cards_studied = sum(r.card_count for r in rows)
    total_reps = sum(r.reps for r in rows)
    total_lapses = sum(r.lapses for r in rows)
    total_attempts = total_reps + total_lapses
    accuracy = round((total_reps / total_attempts) * 100) if total_attempts > 0 else 0

    prompt = _PROMPT_TEMPLATE.format(
        topic=topic or "general software engineering",
        categories=", ".join(categories[:6]),
        cards_studied=cards_studied,
        total_reps=total_reps,
        accuracy=accuracy,
    )

    try:
        response_text = await asyncio.to_thread(
            generate_for_task,
            "experience_narrative",
            prompt,
            None,   # system_prompt
            True,   # json_mode
            2048,   # max_tokens
            0.7,    # temperature
        )
        data = json.loads(response_text)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Experience generation unavailable. Please try again.",
        )

    experience_text = data.get("experience_text", "")
    if not experience_text:
        # LLM returned valid JSON but no usable bullet (e.g. missing key,
        # empty string, or truncated by token cap). Surface as 503 so the
        # caller retries instead of silently rendering nothing.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Experience generation returned empty — please retry.",
        )

    analytics_track(
        user_id=user_id,
        event="experience_generated",
        properties={"topic": topic, "cards_studied_count": cards_studied},
    )

    return {
        "experience_text": experience_text,
        "summary": data.get("summary", ""),
        "cards_studied": cards_studied,
    }
