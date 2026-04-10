"""Per-card feedback endpoints — user votes + admin dashboard."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.card import Card
from app.models.card_feedback import CardFeedback
from app.models.user import User

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class FeedbackCreateRequest(BaseModel):
    vote: str  # "up" or "down"
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    user_id: str
    card_id: str
    vote: str
    comment: Optional[str]
    created_at: str


class FeedbackListResponse(BaseModel):
    feedback: list[FeedbackResponse]
    total: int
    page: int
    per_page: int


class WorstCard(BaseModel):
    card_id: str
    question: str
    down_count: int


class FeedbackSummaryResponse(BaseModel):
    total_up: int
    total_down: int
    worst_cards: list[WorstCard]


# ── User endpoint ────────────────────────────────────────────────────────────

@router.post(
    "/cards/{card_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(
    card_id: str,
    body: FeedbackCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit thumbs-up or thumbs-down feedback on a card."""
    if body.vote not in ("up", "down"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="vote must be 'up' or 'down'",
        )

    # Verify card exists
    result = await db.execute(select(Card).where(Card.id == card_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found",
        )

    feedback = CardFeedback(
        user_id=user.id,
        card_id=card_id,
        vote=body.vote,
        comment=body.comment,
    )
    db.add(feedback)
    await db.flush()

    return FeedbackResponse(
        id=feedback.id,
        user_id=feedback.user_id,
        card_id=feedback.card_id,
        vote=feedback.vote,
        comment=feedback.comment,
        created_at=str(feedback.created_at),
    )


# ── Admin endpoints ──────────────────────────────────────────────────────────

@router.get("/admin/feedback", response_model=FeedbackListResponse)
async def list_feedback(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    vote: Optional[str] = None,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Paginated list of all card feedback, sorted by most recent."""
    query = select(CardFeedback)
    count_query = select(func.count(CardFeedback.id))

    if vote in ("up", "down"):
        query = query.where(CardFeedback.vote == vote)
        count_query = count_query.where(CardFeedback.vote == vote)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(CardFeedback.created_at))
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    rows = result.scalars().all()

    return FeedbackListResponse(
        feedback=[
            FeedbackResponse(
                id=f.id,
                user_id=f.user_id,
                card_id=f.card_id,
                vote=f.vote,
                comment=f.comment,
                created_at=str(f.created_at),
            )
            for f in rows
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/admin/feedback/summary", response_model=FeedbackSummaryResponse)
async def feedback_summary(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Summary stats: total up/down votes + top 10 worst-rated cards."""
    # Count ups and downs
    up_result = await db.execute(
        select(func.count(CardFeedback.id)).where(CardFeedback.vote == "up")
    )
    total_up = up_result.scalar() or 0

    down_result = await db.execute(
        select(func.count(CardFeedback.id)).where(CardFeedback.vote == "down")
    )
    total_down = down_result.scalar() or 0

    # Top 10 cards by down-vote count
    worst_query = (
        select(
            CardFeedback.card_id,
            Card.question,
            func.count(CardFeedback.id).label("down_count"),
        )
        .join(Card, Card.id == CardFeedback.card_id)
        .where(CardFeedback.vote == "down")
        .group_by(CardFeedback.card_id, Card.question)
        .order_by(desc("down_count"))
        .limit(10)
    )
    worst_result = await db.execute(worst_query)
    worst_rows = worst_result.all()

    return FeedbackSummaryResponse(
        total_up=total_up,
        total_down=total_down,
        worst_cards=[
            WorstCard(card_id=row.card_id, question=row.question, down_count=row.down_count)
            for row in worst_rows
        ],
    )
