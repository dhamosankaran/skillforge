"""Tests for daily email reminder service and email preferences.

Coverage:
  - test_reminder_sent_to_opted_in_user     — opted-in user with due cards gets an email
  - test_no_reminder_for_opted_out_user     — opted-out user is skipped
  - test_email_contains_card_count_and_streak — email body has correct numbers

All tests mock ``email_service.send_email`` so no network calls are made.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.card import Card
from app.models.card_progress import CardProgress
from app.models.category import Category
from app.models.email_preference import EmailPreference
from app.models.gamification import GamificationStats
from app.models.user import User
from app.services import reminder_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Helpers ─────────────────────────────────────────────────────────────────


async def _make_user(db, *, email_suffix: str = "") -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}{email_suffix}@email-test.com",
        name="Email Tester",
    )
    db.add(user)
    await db.flush()
    return user


async def _opt_in(db, user_id: str) -> EmailPreference:
    pref = EmailPreference(
        user_id=user_id,
        daily_reminder=True,
        timezone="UTC",
        unsubscribe_token=secrets.token_hex(32),
    )
    db.add(pref)
    await db.flush()
    return pref


async def _opt_out(db, user_id: str) -> EmailPreference:
    pref = EmailPreference(
        user_id=user_id,
        daily_reminder=False,
        timezone="UTC",
        unsubscribe_token=secrets.token_hex(32),
    )
    db.add(pref)
    await db.flush()
    return pref


async def _create_due_card(db, user_id: str) -> None:
    """Create a category, card, and card_progress row that is due now."""
    cat = Category(
        id=str(uuid.uuid4()),
        name=f"Cat-{uuid.uuid4().hex[:8]}",
        icon="📚",
        color="#6366F1",
    )
    db.add(cat)
    await db.flush()

    card = Card(
        id=str(uuid.uuid4()),
        category_id=cat.id,
        question="What is X?",
        answer="X is X.",
        difficulty="medium",
    )
    db.add(card)
    await db.flush()

    progress = CardProgress(
        id=str(uuid.uuid4()),
        user_id=user_id,
        card_id=card.id,
        due_date=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db.add(progress)
    await db.flush()


async def _create_streak(db, user_id: str, streak: int) -> None:
    stats = GamificationStats(
        user_id=user_id,
        current_streak=streak,
        longest_streak=streak,
        total_xp=0,
    )
    db.add(stats)
    await db.flush()


# ── Tests ───────────────────────────────────────────────────────────────────


async def test_reminder_sent_to_opted_in_user(db_session):
    """An opted-in user with due cards receives a reminder email."""
    user = await _make_user(db_session, email_suffix="-optin")
    await _opt_in(db_session, user.id)
    await _create_due_card(db_session, user.id)

    mock_send = AsyncMock(return_value="msg-id-123")
    with patch.object(reminder_service.email_service, "send_email", mock_send):
        sent = await reminder_service.send_daily_reminders(db_session)

    assert sent >= 1
    mock_send.assert_called()
    # Verify the opted-in user's email was among the calls
    call_emails = [call.kwargs["to"] for call in mock_send.call_args_list]
    assert user.email in call_emails


async def test_no_reminder_for_opted_out_user(db_session):
    """An opted-out user does NOT receive a reminder email."""
    opted_out_user = await _make_user(db_session, email_suffix="-optout")
    await _opt_out(db_session, opted_out_user.id)
    await _create_due_card(db_session, opted_out_user.id)

    users = await reminder_service.get_users_needing_reminder(db_session)
    user_ids = [u["user_id"] for u in users]
    assert opted_out_user.id not in user_ids


async def test_email_contains_card_count_and_streak(db_session):
    """The email body includes the due-card count and streak."""
    user = await _make_user(db_session, email_suffix="-content")
    await _opt_in(db_session, user.id)
    await _create_due_card(db_session, user.id)
    await _create_streak(db_session, user.id, streak=5)

    mock_send = AsyncMock(return_value="msg-id-456")
    with patch.object(reminder_service.email_service, "send_email", mock_send):
        await reminder_service.send_daily_reminders(db_session)

    # Find the call for this user
    for call in mock_send.call_args_list:
        if call.kwargs["to"] == user.email:
            html = call.kwargs["html_body"]
            subject = call.kwargs["subject"]
            # Card count appears in the HTML body
            assert "1" in html  # 1 card due
            # Streak appears in both subject and body
            assert "5" in subject
            assert "5" in html
            break
    else:
        pytest.fail(f"No email sent to {user.email}")
