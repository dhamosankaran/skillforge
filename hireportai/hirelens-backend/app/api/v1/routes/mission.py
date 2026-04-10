"""Mission Mode API routes — time-bound study sprints.

Endpoints:
  POST /missions/create       Create a new mission
  GET  /missions/active       Get current active mission with countdown
  GET  /missions/daily        Get today's FSRS-prioritised card set
  POST /missions/complete-day Mark today's mission day as complete

All endpoints require a valid JWT (via get_current_user).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.mission import (
    MissionCreateRequest,
    MissionDailyCardItem,
    MissionDailyResponse,
    MissionDayCompleteResponse,
    MissionDayItem,
    MissionDetailResponse,
    MissionResponse,
)
from app.services import mission_service

router = APIRouter()


def _mission_to_response(mission, total_cards: int, days_remaining: int) -> MissionResponse:
    """Build a MissionResponse from an ORM Mission object."""
    total_completed = sum(d.cards_completed for d in mission.days)
    progress_pct = (total_completed / total_cards * 100) if total_cards > 0 else 0.0
    return MissionResponse(
        id=mission.id,
        title=mission.title,
        target_date=mission.target_date,
        category_ids=[c.id for c in mission.categories],
        daily_target=mission.daily_target,
        total_cards=total_cards,
        days_remaining=days_remaining,
        status=mission.status,
        progress_pct=round(progress_pct, 1),
        created_at=mission.created_at,
    )


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post(
    "/missions/create",
    response_model=MissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new mission",
)
async def create_mission(
    body: MissionCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MissionResponse:
    try:
        mission = await mission_service.create_mission(
            user_id=user.id,
            title=body.title,
            target_date=body.target_date,
            category_ids=body.category_ids,
            db=db,
        )
    except mission_service.MissionInvalidError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except mission_service.MissionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    category_ids = [c.id for c in mission.categories]
    total_cards = await mission_service._count_cards_for_categories(category_ids, db)
    from app.services.mission_service import _today_utc
    days_remaining = (mission.target_date - _today_utc()).days + 1

    return _mission_to_response(mission, total_cards, days_remaining)


@router.get(
    "/missions/active",
    response_model=MissionDetailResponse,
    summary="Get current active mission",
)
async def get_active_mission(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MissionDetailResponse:
    try:
        mission = await mission_service.get_active_mission(user_id=user.id, db=db)
    except mission_service.MissionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    category_ids = [c.id for c in mission.categories]
    total_cards = await mission_service._count_cards_for_categories(category_ids, db)
    from app.services.mission_service import _today_utc
    today = _today_utc()
    days_remaining = max(0, (mission.target_date - today).days + 1)

    total_completed = sum(d.cards_completed for d in mission.days)
    progress_pct = (total_completed / total_cards * 100) if total_cards > 0 else 0.0

    return MissionDetailResponse(
        id=mission.id,
        title=mission.title,
        target_date=mission.target_date,
        category_ids=category_ids,
        daily_target=mission.daily_target,
        total_cards=total_cards,
        days_remaining=days_remaining,
        status=mission.status,
        progress_pct=round(progress_pct, 1),
        created_at=mission.created_at,
        days=[
            MissionDayItem(
                day_number=d.day_number,
                date=d.date,
                cards_target=d.cards_target,
                cards_completed=d.cards_completed,
            )
            for d in mission.days
        ],
    )


@router.get(
    "/missions/daily",
    response_model=MissionDailyResponse,
    summary="Get today's mission cards",
)
async def get_daily_cards(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MissionDailyResponse:
    try:
        mission, today_day, cards = await mission_service.get_mission_daily_cards(
            user_id=user.id, db=db
        )
    except mission_service.MissionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except mission_service.MissionGoneError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc))

    return MissionDailyResponse(
        mission_id=mission.id,
        day_number=today_day.day_number,
        date=today_day.date,
        cards_target=today_day.cards_target,
        cards_completed=today_day.cards_completed,
        cards=[
            MissionDailyCardItem(
                id=c["id"],
                question=c["question"],
                answer=c["answer"],
                category=c["category"],
                difficulty=c["difficulty"],
            )
            for c in cards
        ],
    )


@router.post(
    "/missions/complete-day",
    response_model=MissionDayCompleteResponse,
    summary="Complete today's mission day",
)
async def complete_day(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MissionDayCompleteResponse:
    try:
        mission, today_day, xp_awarded = await mission_service.complete_mission_day(
            user_id=user.id, db=db
        )
    except mission_service.MissionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except mission_service.MissionGoneError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc))

    return MissionDayCompleteResponse(
        mission_id=mission.id,
        day_number=today_day.day_number,
        cards_completed=today_day.cards_completed,
        cards_target=today_day.cards_target,
        xp_awarded=xp_awarded,
        mission_status=mission.status,
    )
