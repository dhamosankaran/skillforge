"""Cards API — read-only endpoints for flashcard content.

Route order matters: /cards/search must appear before /cards/{card_id}
so FastAPI does not match the literal string "search" as a UUID path param.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.card import CardResponse, CategoryListResponse
from app.services import card_service

router = APIRouter()


@router.get("/cards", response_model=CategoryListResponse, tags=["v1 Cards"])
async def list_categories(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all plan-accessible categories with card counts."""
    return await card_service.list_categories(db, user)


@router.get("/cards/search", tags=["v1 Cards"])
async def search_cards(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50, description="Max results (1–50)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Semantic search over cards using pgvector cosine similarity."""
    results = await card_service.search_cards(q, limit, db, user)
    return {"query": q, "results": [r.model_dump() for r in results], "total": len(results)}


@router.get("/cards/category/{category_id}", tags=["v1 Cards"])
async def get_category_cards(
    category_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a category and all its cards. 403 if plan gate blocks access."""
    category, cards = await card_service.get_cards_by_category(category_id, db, user)
    return {
        "category": {
            "id": category.id,
            "name": category.name,
            "icon": category.icon,
            "color": category.color,
            "display_order": category.display_order,
            "source": category.source,
        },
        "cards": [c.model_dump() for c in cards],
        "total": len(cards),
    }


@router.get("/cards/{card_id}", response_model=CardResponse, tags=["v1 Cards"])
async def get_card(
    card_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a single card by UUID. 403 if plan gate blocks access."""
    return await card_service.get_card(card_id, db, user)
