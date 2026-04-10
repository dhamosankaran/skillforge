"""Progress analytics service — category radar + activity heatmap.

Provides two read-only views over the existing card_progress, cards, and
categories tables:

  - get_category_coverage: per-category mastery breakdown (radar chart data)
  - get_activity_heatmap: daily review counts over the last N days (heatmap data)

No writes — pure reporting queries.
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.schemas.progress import CategoryCoverage, HeatmapDay


async def get_category_coverage(
    user_id: str,
    db: AsyncSession,
) -> list[CategoryCoverage]:
    """Return mastery breakdown for every category.

    mastery_pct = (cards in 'review' state) / (total cards in category) * 100
    A category with zero cards gets mastery_pct=0.
    """
    # Subquery: per-category counts of studied cards and mastered cards
    progress_sq = (
        select(
            Card.category_id,
            func.count(CardProgress.id).label("studied"),
            func.sum(
                case((CardProgress.state == "review", 1), else_=0)
            ).label("mastered"),
        )
        .join(CardProgress, (CardProgress.card_id == Card.id) & (CardProgress.user_id == user_id))
        .group_by(Card.category_id)
        .subquery()
    )

    stmt = (
        select(
            Category.name,
            func.count(Card.id).label("total_cards"),
            func.coalesce(progress_sq.c.studied, 0).label("studied"),
            func.coalesce(progress_sq.c.mastered, 0).label("mastered"),
        )
        .outerjoin(Card, Card.category_id == Category.id)
        .outerjoin(progress_sq, progress_sq.c.category_id == Category.id)
        .group_by(Category.name, progress_sq.c.studied, progress_sq.c.mastered)
        .order_by(Category.name)
    )

    rows = (await db.execute(stmt)).all()

    result: list[CategoryCoverage] = []
    for row in rows:
        total = row.total_cards or 0
        mastered = row.mastered or 0
        pct = round((mastered / total) * 100, 1) if total > 0 else 0.0
        result.append(
            CategoryCoverage(
                category=row.name,
                total_cards=total,
                studied=row.studied or 0,
                mastery_pct=pct,
            )
        )
    return result


async def get_activity_heatmap(
    user_id: str,
    days: int,
    db: AsyncSession,
) -> list[HeatmapDay]:
    """Return daily review counts for the last `days` days (most recent first).

    A day with no reviews is included with review_count=0.
    """
    today = date.today()
    start_date = today - timedelta(days=days - 1)

    # Query: count distinct card_progress rows reviewed on each day
    stmt = (
        select(
            func.date(CardProgress.last_reviewed).label("review_date"),
            func.count(CardProgress.id).label("cnt"),
        )
        .where(CardProgress.user_id == user_id)
        .where(CardProgress.last_reviewed >= datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc))
        .group_by(func.date(CardProgress.last_reviewed))
    )

    rows = (await db.execute(stmt)).all()
    counts_by_date: dict[date, int] = {row.review_date: row.cnt for row in rows}

    # Fill all days in range
    result: list[HeatmapDay] = []
    for i in range(days):
        d = today - timedelta(days=i)
        result.append(
            HeatmapDay(
                date=d,
                review_count=counts_by_date.get(d, 0),
            )
        )

    return result
