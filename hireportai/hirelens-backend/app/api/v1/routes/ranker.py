"""Deck-ranker API route — Phase 6 slice 6.6.

Spec: docs/specs/phase-6/07-deck-lesson-ranker.md §6.2 + §12 D-9.

  GET /api/v1/learn/ranked-decks
    Auth: Depends(get_current_user)
    Query: ?lookback_days=N&max_scans=M (defaults 30 / 5 per D-14)
    Returns: RankedDecksResponse
    Errors: 400 (non-positive query params), 401 (no auth)

No 403 path — the ranker re-orders the user's already-visible deck set;
authenticated users always get a ``200`` (potentially with
``cold_start=True``) per spec §6.2.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ranker import RankedDecksResponse
from app.services import deck_ranker_service

router = APIRouter()


@router.get(
    "/learn/ranked-decks",
    response_model=RankedDecksResponse,
    summary="Lens-ranked deck ordering for the authenticated user",
)
async def get_ranked_decks(
    lookback_days: int = Query(
        default=deck_ranker_service.DEFAULT_LOOKBACK_DAYS,
        ge=1,
        le=365,
        description="Days of recent ATS scans to consider for skill_gap aggregation.",
    ),
    max_scans: int = Query(
        default=deck_ranker_service.DEFAULT_MAX_SCANS,
        ge=1,
        le=50,
        description="Maximum number of recent scans to read.",
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RankedDecksResponse:
    """Return the user's persona/tier-visible decks re-ordered by Lens.

    Cold-start (no recent scan with ``analysis_payload``) returns
    ``cold_start=True`` and ``display_order ASC`` ordering. The same
    response shape is used in both branches.
    """
    return await deck_ranker_service.rank_decks_for_user(
        user,
        db,
        lookback_days=lookback_days,
        max_scans=max_scans,
    )
