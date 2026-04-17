"""Daily email reminder service.

Queries opted-in users who have cards due, builds an HTML digest for
each, and sends it via ``email_service``.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track
from app.models.card_progress import CardProgress
from app.models.email_preference import EmailPreference
from app.models.gamification import GamificationStats
from app.models.user import User
from app.services import email_service

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


# ── Helpers ─────────────────────────────────────────────────────────────────


def _load_template() -> str:
    """Read the HTML email template from disk."""
    path = _TEMPLATE_DIR / "daily_reminder.html"
    return path.read_text()


def build_email_body(
    name: str,
    cards_due: int,
    streak: int,
) -> str:
    """Render the daily-reminder HTML with user-specific values."""
    app_url = os.getenv("FRONTEND_URL", "http://localhost:5199")
    study_link = f"{app_url}/learn/daily?utm_source=email&utm_medium=daily_reminder"

    template = _load_template()
    return (
        template
        .replace("{{name}}", name)
        .replace("{{cards_due}}", str(cards_due))
        .replace("{{streak}}", str(streak))
        .replace("{{study_link}}", study_link)
    )


def build_subject(cards_due: int, streak: int) -> str:
    """Return the email subject line."""
    if streak > 0:
        return (
            f"You have {cards_due} cards due "
            f"\u2014 keep your {streak}-day streak alive!"
        )
    return f"You have {cards_due} cards due \u2014 start a new streak today!"


# ── Core logic ──────────────────────────────────────────────────────────────


async def get_users_needing_reminder(
    db: AsyncSession,
) -> list[dict]:
    """Return opted-in users who have at least one card due today.

    Each dict contains: user_id, email, name, cards_due.
    """
    # Sub-query: count due cards per user
    due_counts = (
        select(
            CardProgress.user_id,
            func.count().label("cards_due"),
        )
        .where(CardProgress.due_date <= func.now())
        .group_by(CardProgress.user_id)
        .subquery()
    )

    stmt = (
        select(
            User.id,
            User.email,
            User.name,
            due_counts.c.cards_due,
        )
        .join(EmailPreference, EmailPreference.user_id == User.id)
        .join(due_counts, due_counts.c.user_id == User.id)
        .where(EmailPreference.daily_reminder.is_(True))
        .where(due_counts.c.cards_due > 0)
    )

    result = await db.execute(stmt)
    return [
        {
            "user_id": row.id,
            "email": row.email,
            "name": row.name,
            "cards_due": row.cards_due,
        }
        for row in result.all()
    ]


async def _get_streak(user_id: str, db: AsyncSession) -> int:
    """Fetch the user's current streak (0 if no stats row exists)."""
    result = await db.execute(
        select(GamificationStats.current_streak).where(
            GamificationStats.user_id == user_id
        )
    )
    row = result.scalar_one_or_none()
    return row if row is not None else 0


async def send_daily_reminders(db: AsyncSession) -> int:
    """Send daily reminder emails to all eligible users.

    Returns the number of emails successfully sent.
    """
    users = await get_users_needing_reminder(db)
    sent = 0

    for u in users:
        streak = await _get_streak(u["user_id"], db)
        subject = build_subject(u["cards_due"], streak)
        html = build_email_body(u["name"], u["cards_due"], streak)

        try:
            await email_service.send_email(
                to=u["email"],
                subject=subject,
                html_body=html,
            )
            track(
                u["user_id"],
                "email_sent",
                {
                    "type": "daily_reminder",
                    "cards_due": u["cards_due"],
                    "streak": streak,
                },
            )
            sent += 1
        except Exception:
            logger.exception("Failed to send reminder to %s", u["email"])

    logger.info("Daily reminders: sent %d / %d eligible", sent, len(users))
    return sent
