"""Email preferences API — GET + PUT /email-preferences.

Lets authenticated users read and update their daily-reminder settings.
"""
from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.email_preference import EmailPreference
from app.models.user import User

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────────────


class EmailPreferenceResponse(BaseModel):
    user_id: str
    daily_reminder: bool
    timezone: str

    model_config = ConfigDict(from_attributes=True)


class EmailPreferenceUpdate(BaseModel):
    daily_reminder: Optional[bool] = None
    timezone: Optional[str] = None


# ── Helpers ─────────────────────────────────────────────────────────────────


async def _get_or_create(user_id: str, db: AsyncSession) -> EmailPreference:
    """Return the user's preference row, creating one with defaults if missing."""
    result = await db.execute(
        select(EmailPreference).where(EmailPreference.user_id == user_id)
    )
    pref = result.scalar_one_or_none()
    if pref is not None:
        return pref

    pref = EmailPreference(
        user_id=user_id,
        daily_reminder=True,
        timezone="UTC",
        unsubscribe_token=secrets.token_hex(32),
    )
    db.add(pref)
    await db.flush()
    return pref


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get(
    "/email-preferences",
    response_model=EmailPreferenceResponse,
    summary="Get the caller's email preferences",
)
async def get_email_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EmailPreferenceResponse:
    pref = await _get_or_create(user.id, db)
    return EmailPreferenceResponse.model_validate(pref)


@router.put(
    "/email-preferences",
    response_model=EmailPreferenceResponse,
    summary="Update the caller's email preferences",
)
async def update_email_preferences(
    body: EmailPreferenceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EmailPreferenceResponse:
    pref = await _get_or_create(user.id, db)
    old_reminder = pref.daily_reminder

    if body.daily_reminder is not None:
        pref.daily_reminder = body.daily_reminder
    if body.timezone is not None:
        pref.timezone = body.timezone

    await db.flush()

    # Track opt-out / opt-in transitions
    if old_reminder and not pref.daily_reminder:
        track(user.id, "email_unsubscribed", {"method": "preferences"})
    elif not old_reminder and pref.daily_reminder:
        track(user.id, "email_resubscribed", {})

    return EmailPreferenceResponse.model_validate(pref)
