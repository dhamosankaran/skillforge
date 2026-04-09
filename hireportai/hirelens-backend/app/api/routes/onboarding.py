"""Onboarding API — ATS gap → study card bridge.

Closes the post-scan conversion loop described in
.agent/skills/ats-card-bridge.md: after an ATS scan, the frontend calls
this endpoint with the gap tags it just received and gets back a ranked
list of study categories the user can click into.

Endpoint:
  GET /api/v1/onboarding/recommendations
      ?scan_id=<optional tracking id>
      &gaps=<gap1>&gaps=<gap2>...

Notes on `scan_id`
------------------
ATS scans are currently stateless — `/api/analyze` returns gaps inline
without persisting anything, so we have no table to look a scan up in.
The frontend passes its current scan's gap list via the `gaps` query
parameter; `scan_id` is accepted as an optional client-generated token
purely for analytics correlation and is echoed back in the response.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.gap_mapping_service import GapMapping, map_gaps_to_categories

router = APIRouter()


class OnboardingRecommendationsResponse(BaseModel):
    """Response body for GET /onboarding/recommendations."""

    scan_id: Optional[str] = None
    results: list[GapMapping]


@router.get(
    "/onboarding/recommendations",
    response_model=OnboardingRecommendationsResponse,
    summary="Get study category recommendations for ATS scan gaps",
)
async def get_recommendations(
    scan_id: Optional[str] = Query(
        None, description="Client-provided scan identifier (echoed back)."
    ),
    gaps: list[str] = Query(
        ...,
        description="Gap tags from the ATS scan. Repeat the query parameter per gap.",
        min_length=1,
        max_length=50,
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingRecommendationsResponse:
    """Return `{ gap → [recommended categories] }` for each input gap.

    For each gap we first try a deterministic tag join against
    `cards.tags`. If nothing matches, we fall back to pgvector cosine
    similarity over card embeddings. Gaps with neither kind of match
    are returned with `match_type: "none"` rather than being dropped,
    so the frontend can still show them alongside the other results.
    """
    results = await map_gaps_to_categories(gaps, db=db)
    return OnboardingRecommendationsResponse(scan_id=scan_id, results=results)
