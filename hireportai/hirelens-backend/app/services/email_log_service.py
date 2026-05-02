"""email_log dedup service — record_send + was_sent_today.

Spec: docs/specs/phase-6/13-pro-digest-opt-out.md §6.2.

Append-only. ``sent_date`` is caller-supplied per OQ-G — the service is
timezone-agnostic so cron callers can pass per-user-tz "today" without
service awareness. Slice 6.13 ships the service + tests; the wiring
into the slice 6.14 cron is out of this slice's scope.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_log import EmailLog


async def record_send(
    db: AsyncSession,
    user_id: str,
    email_type: str,
    sent_date: date,
    resend_id: Optional[str] = None,
) -> EmailLog:
    """Insert one ``email_log`` row.

    Raises ``IntegrityError`` (DB-side) if a row already exists for the
    ``(user_id, email_type, sent_date)`` triple — uniqueness is enforced
    by ``uq_email_log_user_type_date``. Callers MUST handle the integrity
    error if they want to treat duplicates as a no-op.
    """
    row = EmailLog(
        user_id=user_id,
        email_type=email_type,
        sent_date=sent_date,
        resend_id=resend_id,
    )
    db.add(row)
    await db.flush()
    return row


async def was_sent_today(
    db: AsyncSession,
    user_id: str,
    email_type: str,
    today: date,
) -> bool:
    """Return ``True`` iff an ``email_log`` row exists for the
    ``(user_id, email_type, today)`` triple.

    Used by slice 6.14 cron to short-circuit before attempting a Resend
    dispatch.
    """
    result = await db.execute(
        select(EmailLog.id)
        .where(EmailLog.user_id == user_id)
        .where(EmailLog.email_type == email_type)
        .where(EmailLog.sent_date == today)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None
