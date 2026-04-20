"""User-local timezone resolution for day-boundary calculations (spec #50).

Canonical store: ``EmailPreference.timezone`` (IANA name, non-nullable,
default ``"UTC"``). Callers that need to know a user's local calendar
day — free-tier daily-card wall, future daily-reminder cadence tweaks,
etc. — resolve through this module so the fallback behaviour is
consistent.

No helper exists prior to this module; the codebase was UTC-only before
spec #50 (grep of ``ZoneInfo|zoneinfo|pytz`` returned zero hits).
"""
from __future__ import annotations

import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_preference import EmailPreference

logger = logging.getLogger(__name__)

_UTC = ZoneInfo("UTC")


async def get_user_timezone(user_id: str, db: AsyncSession) -> ZoneInfo:
    """Return the user's IANA timezone, defaulting to UTC.

    Resolution order:
      1. ``EmailPreference.timezone`` for the user → parse as ``ZoneInfo``.
      2. No ``EmailPreference`` row → UTC.
      3. Parse failure (malformed IANA name) → UTC, with a warning so bad
         values can be cleaned up later.

    Note: ``EmailPreference.timezone`` is non-nullable with a ``"UTC"``
    default, so an explicit NULL cannot occur today. The no-row branch
    is the only real fallback path.
    """
    row = (
        await db.execute(
            select(EmailPreference.timezone).where(
                EmailPreference.user_id == user_id
            )
        )
    ).scalar_one_or_none()

    if row is None:
        return _UTC
    try:
        return ZoneInfo(row)
    except ZoneInfoNotFoundError:
        logger.warning(
            "Unrecognised IANA timezone %r for user %s; falling back to UTC",
            row,
            user_id,
        )
        return _UTC
