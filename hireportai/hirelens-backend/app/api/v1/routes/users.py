"""Users router — persona and interview-target fields.

Introduced in P5-S16. See spec
`docs/specs/phase-5/34-persona-picker-and-home.md` §API Contract.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes.auth import _user_dict
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import PersonaUpdateRequest
from app.services import home_state_service

router = APIRouter()


@router.patch("/users/me/persona")
@limiter.limit("10/minute")
async def update_persona(
    request: Request,
    body: PersonaUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Set or update the caller's persona and optional interview targets.

    If the caller had no persona before this call, also flips
    ``onboarding_completed`` to True so the legacy column stays coherent
    (cleanup deferred to Phase 6 per spec).
    """
    first_time_set = user.persona is None

    user.persona = body.persona.value
    user.interview_target_date = body.interview_target_date
    user.interview_target_company = body.interview_target_company
    if first_time_set:
        user.onboarding_completed = True

    db.add(user)
    await db.commit()
    await db.refresh(user)
    home_state_service.invalidate(user.id)
    return _user_dict(user)
