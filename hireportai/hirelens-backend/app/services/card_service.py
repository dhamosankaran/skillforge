"""Card and category read service.

Implements plan-gated access to flashcard content:
  - free users  → categories where source="foundation" only
  - pro/enterprise → all categories

Raises HTTPException directly so routes stay thin.
"""
import asyncio
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.card import Card
from app.models.category import Category
from app.models.user import User
from app.schemas.card import (
    CardResponse,
    CardSearchResult,
    CategoryListResponse,
    CategoryResponse,
)

# Must match the model used to generate stored embeddings (generate_embeddings.py)
_EMBEDDING_MODEL = "gemini-embedding-exp-03-07"
_EMBEDDING_DIMS = 1536


# ── Plan gate ────────────────────────────────────────────────────────────────


def _is_free(user: User) -> bool:
    """Return True when the user must be restricted to foundation content.

    A user is treated as free if:
    - They have no subscription row (new user before first sync)
    - Their subscription status is not "active" (canceled, past_due, etc.)
    - Their plan is "free"
    """
    sub = user.subscription  # loaded via selectin on get_current_user
    if sub is None:
        return True
    if sub.status != "active":
        return True
    return sub.plan == "free"


# ── Embedding helper ─────────────────────────────────────────────────────────


def _embed_sync(query: str, api_key: str) -> list[float]:
    """Blocking Gemini embed call — run via asyncio.to_thread."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    resp = client.models.embed_content(
        model=_EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(
            task_type="SEMANTIC_SIMILARITY",
            output_dimensionality=_EMBEDDING_DIMS,
        ),
    )
    return list(resp.embeddings[0].values)


async def _embed_query(query: str) -> list[float]:
    """Embed a search query string; raises 503 on any Gemini failure."""
    settings = get_settings()
    try:
        return await asyncio.to_thread(_embed_sync, query, settings.gemini_api_key)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service unavailable. Please try again.",
        )


# ── Service methods ──────────────────────────────────────────────────────────


async def list_categories(db: AsyncSession, user: User) -> CategoryListResponse:
    """Return all categories the caller may access, each with a card count.

    Free users receive only categories where source="foundation".
    Results are ordered by display_order ASC.
    """
    stmt = (
        select(Category, func.count(Card.id).label("card_count"))
        .outerjoin(Card, Card.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.display_order)
    )
    if _is_free(user):
        stmt = stmt.where(Category.source == "foundation")

    rows = (await db.execute(stmt)).all()

    categories = [
        CategoryResponse(
            id=row.Category.id,
            name=row.Category.name,
            icon=row.Category.icon,
            color=row.Category.color,
            display_order=row.Category.display_order,
            source=row.Category.source,
            card_count=row.card_count,
        )
        for row in rows
    ]
    return CategoryListResponse(categories=categories)


async def get_cards_by_category(
    category_id: str,
    db: AsyncSession,
    user: User,
) -> tuple[Category, list[CardResponse]]:
    """Return the category and its cards.

    Raises:
        404 — category does not exist
        403 — category exists but caller's plan does not permit access
    """
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    if _is_free(user) and category.source != "foundation":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This category requires a Pro plan.",
        )

    result = await db.execute(
        select(Card).where(Card.category_id == category_id).order_by(Card.created_at)
    )
    cards = result.scalars().all()

    card_responses = [
        CardResponse(
            id=c.id,
            category_id=c.category_id,
            question=c.question,
            answer=c.answer,
            difficulty=c.difficulty,
            tags=c.tags or [],
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in cards
    ]
    return category, card_responses


async def get_card(card_id: str, db: AsyncSession, user: User) -> CardResponse:
    """Return a single card by ID, with category_name included.

    Raises:
        404 — card does not exist
        403 — card's category is not accessible under the caller's plan
    """
    result = await db.execute(
        select(Card, Category)
        .join(Category, Category.id == Card.category_id)
        .where(Card.id == card_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found.")

    card, category = row.Card, row.Category
    if _is_free(user) and category.source != "foundation":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This card requires a Pro plan.",
        )

    return CardResponse(
        id=card.id,
        category_id=card.category_id,
        category_name=category.name,
        question=card.question,
        answer=card.answer,
        difficulty=card.difficulty,
        tags=card.tags or [],
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


async def search_cards(
    query: str,
    limit: int,
    db: AsyncSession,
    user: User,
) -> list[CardSearchResult]:
    """Semantic search over cards using pgvector cosine similarity.

    Embeds `query` via Gemini, then finds the `limit` closest cards by
    cosine distance. Results are filtered by the caller's plan gate before
    being returned — free users never see cards from non-foundation categories.

    Cards with a NULL embedding are excluded from results.

    Raises:
        503 — Gemini embedding API call fails
    """
    query_vector = await _embed_query(query)

    stmt = (
        select(
            Card,
            Category.name.label("category_name"),
            (1 - Card.embedding.cosine_distance(query_vector)).label("score"),
        )
        .join(Category, Category.id == Card.category_id)
        .where(Card.embedding.is_not(None))
        .order_by(Card.embedding.cosine_distance(query_vector))
        .limit(limit)
    )
    if _is_free(user):
        stmt = stmt.where(Category.source == "foundation")

    rows = (await db.execute(stmt)).all()

    return [
        CardSearchResult(
            id=row.Card.id,
            category_id=row.Card.category_id,
            category_name=row.category_name,
            question=row.Card.question,
            answer=row.Card.answer,
            difficulty=row.Card.difficulty,
            tags=row.Card.tags or [],
            score=round(float(row.score), 4),
        )
        for row in rows
    ]
