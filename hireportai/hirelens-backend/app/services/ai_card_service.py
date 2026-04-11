"""AI card generation service — generates flashcard drafts via LLM."""
import json

from fastapi import HTTPException, status

from app.core.llm_router import generate_for_task
from app.schemas.admin_card import CardDraftResponse, CardGenerateRequest

_PROMPT_TEMPLATE = """You are an expert educator creating flashcards for software engineering interview prep.

Generate a single flashcard for the following topic and difficulty level.

Topic: {topic}
Difficulty: {difficulty}

Difficulty guidelines:
- easy: fundamental concept, suitable for beginners
- medium: requires understanding of trade-offs or implementation details
- hard: advanced topic, requires deep understanding or multi-step reasoning

Return a JSON object with exactly these fields:
{{
  "question": "A clear, specific question about the topic",
  "answer": "A thorough but concise answer (2-5 sentences). Include key points and why they matter.",
  "tags": ["tag1", "tag2", "tag3"]
}}

Rules:
- The question should test understanding, not just recall
- The answer should be educational and self-contained
- Tags should be lowercase, hyphenated, 2-5 relevant tags
- Do not include the difficulty level in the tags"""


def generate_card_draft(payload: CardGenerateRequest) -> CardDraftResponse:
    """Generate a flashcard draft using the configured LLM provider.

    The draft is transient — not saved to the database. The admin reviews
    and optionally edits before publishing via POST /api/v1/admin/cards.

    Raises HTTPException 503 if the LLM call fails or returns invalid JSON.
    """
    prompt = _PROMPT_TEMPLATE.format(
        topic=payload.topic,
        difficulty=payload.difficulty,
    )

    try:
        response_text = generate_for_task(
            task="card_draft",
            prompt=prompt,
            json_mode=True,
            max_tokens=800,
        )
        data = json.loads(response_text)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI card generation unavailable. Please try again.",
        )

    return CardDraftResponse(
        question=data.get("question", ""),
        answer=data.get("answer", ""),
        difficulty=payload.difficulty,
        tags=data.get("tags", []),
    )
