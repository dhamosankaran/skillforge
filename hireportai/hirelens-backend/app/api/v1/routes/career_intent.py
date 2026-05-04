"""Career-Climber role-intent capture route (E-052 / B-125a).

Spec: docs/specs/phase-5/67-career-climber-role-intent.md §6.2.

Three endpoints — POST / GET / DELETE — at
``/api/v1/users/me/career-intent``. Persona guard rejects non-CC users
with 422 (B-038 isolation discipline; the legacy ``PATCH /persona``
remains untouched).

Telemetry per spec §9.1:

- ``career_intent_captured`` — first-time capture (no prior current row).
- ``career_intent_updated`` — subsequent change (prior current row was
  superseded) OR explicit clear via DELETE.

``X-Capture-Source`` request header (default ``'api'``) discriminates
``persona_picker`` vs ``profile_edit`` vs ``profile_clear`` callers in
PostHog dashboards (D-13).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.career_intent import (
    CareerIntentCreate,
    CareerIntentResponse,
)
from app.services import career_intent_service


router = APIRouter()

_CC_PERSONA = "career_climber"


def _persona_guard(user: User) -> None:
    if (user.persona or "") != _CC_PERSONA:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Career intent capture is only available for "
                "career_climber persona users."
            ),
        )


@router.post(
    "/users/me/career-intent",
    response_model=CareerIntentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def set_career_intent(
    body: CareerIntentCreate,
    x_capture_source: str | None = Header(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CareerIntentResponse:
    _persona_guard(user)

    prior = await career_intent_service.get_current_intent(db, user.id)
    intent = await career_intent_service.set_intent(
        db, user.id, body.target_role, body.target_quarter
    )
    await db.commit()
    await db.refresh(intent)

    source = x_capture_source or "api"
    if prior is None:
        analytics_track(
            user.id,
            "career_intent_captured",
            {
                "target_role": intent.target_role,
                "target_quarter": intent.target_quarter,
                "source": source,
            },
        )
    else:
        analytics_track(
            user.id,
            "career_intent_updated",
            {
                "from_role": prior.target_role,
                "to_role": intent.target_role,
                "from_quarter": prior.target_quarter,
                "to_quarter": intent.target_quarter,
                "source": source,
            },
        )

    return CareerIntentResponse.model_validate(intent)


@router.get(
    "/users/me/career-intent",
    response_model=CareerIntentResponse,
)
async def get_career_intent(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CareerIntentResponse:
    _persona_guard(user)
    intent = await career_intent_service.get_current_intent(db, user.id)
    if intent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current career intent",
        )
    return CareerIntentResponse.model_validate(intent)


@router.delete(
    "/users/me/career-intent",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_career_intent(
    x_capture_source: str | None = Header(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    _persona_guard(user)

    prior = await career_intent_service.get_current_intent(db, user.id)
    cleared = await career_intent_service.clear_intent(db, user.id)
    await db.commit()

    if cleared and prior is not None:
        analytics_track(
            user.id,
            "career_intent_updated",
            {
                "from_role": prior.target_role,
                "to_role": None,
                "from_quarter": prior.target_quarter,
                "to_quarter": None,
                "source": x_capture_source or "profile_clear",
            },
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
