"""Tests for ``pro_digest_service`` (Phase 6 slice 6.14 / B-098).

Spec: docs/specs/phase-6/14-daily-digest-cron.md §10.1 + §11
AC-3..AC-13 + §12 D-3..D-13.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.card_progress import CardProgress
from app.models.email_log import EmailLog
from app.models.email_preference import EmailPreference
from app.models.gamification import GamificationStats
from app.models.mission import Mission
from app.models.subscription import Subscription
from app.models.tracker_application_score import TrackerApplicationScore
from app.models.user import User
from app.services import pro_digest_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Seed helpers ────────────────────────────────────────────────────────────


async def _seed_user(db_session, *, name: str = "Pro User") -> User:
    user = User(
        id=str(uuid.uuid4()),
        google_id=f"g-{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        name=name,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _seed_pro_user(
    db_session,
    *,
    plan: str = "pro",
    status: str = "active",
    opt_out: bool | None = False,
) -> User:
    user = await _seed_user(db_session)
    db_session.add(
        Subscription(
            id=str(uuid.uuid4()), user_id=user.id, plan=plan, status=status
        )
    )
    if opt_out is not None:
        db_session.add(
            EmailPreference(
                user_id=user.id,
                daily_reminder=True,
                daily_digest_opt_out=opt_out,
                timezone="UTC",
                unsubscribe_token=uuid.uuid4().hex,
            )
        )
    await db_session.flush()
    return user


async def _seed_card_due(db_session, user_id: str, *, due_offset_days: int = -1):
    """Seed a single CardProgress row due in the past (so it's "due today")."""
    from app.models.card import Card
    from app.models.category import Category

    cat = Category(
        id=str(uuid.uuid4()),
        name=f"cat-{uuid.uuid4().hex[:6]}",
        icon="📚",
        color="#000000",
        display_order=0,
        source="seed",
    )
    db_session.add(cat)
    await db_session.flush()
    card = Card(
        id=str(uuid.uuid4()),
        category_id=cat.id,
        question="Q?",
        answer="A.",
        difficulty="medium",
    )
    db_session.add(card)
    await db_session.flush()
    cp = CardProgress(
        id=str(uuid.uuid4()),
        user_id=user_id,
        card_id=card.id,
        state="review",
        stability=1.0,
        difficulty_fsrs=5.0,
        due_date=datetime.now(timezone.utc) + timedelta(days=due_offset_days),
        reps=1,
        lapses=0,
    )
    db_session.add(cp)
    await db_session.flush()


async def _seed_streak(db_session, user_id: str, *, streak: int):
    db_session.add(
        GamificationStats(
            user_id=user_id,
            current_streak=streak,
            longest_streak=streak,
            total_xp=0,
        )
    )
    await db_session.flush()


async def _seed_mission(
    db_session, user_id: str, *, days_left: int = 5, status: str = "active"
):
    db_session.add(
        Mission(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title="Test mission",
            target_date=date.today() + timedelta(days=days_left),
            daily_target=10,
            status=status,
        )
    )
    await db_session.flush()


async def _seed_scan(
    db_session, user_id: str, *, score: int, scanned_at: datetime
):
    """Seed a tracker_application_scores row."""
    from app.models.tracker import TrackerApplicationModel

    tracker = TrackerApplicationModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        company="Test Co",
        role="Engineer",
        date_applied=date.today().isoformat(),
        ats_score=score,
        status="applied",
    )
    db_session.add(tracker)
    await db_session.flush()
    db_session.add(
        TrackerApplicationScore(
            id=str(uuid.uuid4()),
            tracker_application_id=tracker.id,
            user_id=user_id,
            scan_id=str(uuid.uuid4()),
            overall_score=score,
            keyword_match_score=0.5,
            skills_coverage_score=0.5,
            formatting_compliance_score=0.5,
            bullet_strength_score=0.5,
            jd_hash="x" * 64,
            resume_hash="y" * 64,
            scanned_at=scanned_at,
        )
    )
    await db_session.flush()


# ── 1. select_candidates filters (AC-3 / AC-4 / AC-5, §12 D-6) ──────────────


async def test_select_candidates_filters_by_pro_plan(db_session):
    free_user = await _seed_user(db_session)
    db_session.add(
        Subscription(
            id=str(uuid.uuid4()),
            user_id=free_user.id,
            plan="free",
            status="active",
        )
    )
    pro_user = await _seed_pro_user(db_session, plan="pro")
    enterprise_user = await _seed_pro_user(db_session, plan="enterprise")
    await db_session.flush()

    candidates = await pro_digest_service.select_candidates(db_session)
    candidate_ids = {u.id for u in candidates}

    assert pro_user.id in candidate_ids
    assert enterprise_user.id in candidate_ids
    assert free_user.id not in candidate_ids


async def test_select_candidates_excludes_inactive_subscriptions(db_session):
    pro_user = await _seed_pro_user(db_session, plan="pro", status="active")
    canceled_user = await _seed_pro_user(db_session, plan="pro", status="canceled")
    await db_session.flush()

    candidates = await pro_digest_service.select_candidates(db_session)
    candidate_ids = {u.id for u in candidates}

    assert pro_user.id in candidate_ids
    assert canceled_user.id not in candidate_ids


async def test_select_candidates_excludes_opted_out_users(db_session):
    pro_in = await _seed_pro_user(db_session, plan="pro", opt_out=False)
    pro_out = await _seed_pro_user(db_session, plan="pro", opt_out=True)
    await db_session.flush()

    candidates = await pro_digest_service.select_candidates(db_session)
    candidate_ids = {u.id for u in candidates}

    assert pro_in.id in candidate_ids
    assert pro_out.id not in candidate_ids


async def test_select_candidates_includes_pro_users_with_no_email_preference_row(
    db_session,
):
    """AC-5 — outer-join semantics treat NULL preference row as opted-in."""
    pro_user = await _seed_pro_user(db_session, plan="pro", opt_out=None)
    await db_session.flush()

    candidates = await pro_digest_service.select_candidates(db_session)
    candidate_ids = {u.id for u in candidates}

    assert pro_user.id in candidate_ids


# ── 2. compose_digest happy + empty (AC-7 / AC-12 / AC-13, §12 D-3 / D-7) ──


async def test_compose_digest_populates_all_fields_when_present(db_session):
    # Pin the service's "today" so mission_days_left is deterministic
    # regardless of the runner's UTC clock position (B-124 — was off-by-one
    # when local date and UTC date crossed midnight).
    fixed_today = date(2026, 5, 1)
    fixed_now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)

    user = await _seed_pro_user(db_session)
    await _seed_card_due(db_session, user.id)
    await _seed_streak(db_session, user.id, streak=7)
    db_session.add(
        Mission(
            id=str(uuid.uuid4()),
            user_id=user.id,
            title="Test mission",
            target_date=fixed_today + timedelta(days=5),
            daily_target=10,
            status="active",
        )
    )
    await db_session.flush()
    await _seed_scan(
        db_session,
        user.id,
        score=72,
        scanned_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    await _seed_scan(
        db_session,
        user.id,
        score=85,
        scanned_at=datetime.now(timezone.utc),
    )

    with patch("app.services.pro_digest_service.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_now
        payload = await pro_digest_service.compose_digest(user, db_session)

    assert payload is not None
    assert payload.user_id == user.id
    assert payload.cards_due == 1
    assert payload.streak == 7
    assert payload.mission_active is True
    assert payload.mission_days_left == 5
    assert payload.last_scan_score == 85
    assert payload.last_scan_delta == 13


async def test_compose_digest_returns_none_when_zero_engagement_signal(
    db_session,
):
    """AC-7 / §12 D-7 — strict empty-rule."""
    user = await _seed_pro_user(db_session)

    payload = await pro_digest_service.compose_digest(user, db_session)
    assert payload is None


async def test_compose_digest_skips_mission_fields_when_inactive(db_session):
    user = await _seed_pro_user(db_session)
    await _seed_card_due(db_session, user.id)  # one signal so we don't return None
    await _seed_mission(db_session, user.id, status="completed")

    payload = await pro_digest_service.compose_digest(user, db_session)
    assert payload is not None
    assert payload.mission_active is False
    assert payload.mission_days_left is None


async def test_compose_digest_skips_scan_delta_when_history_below_two_rows(
    db_session,
):
    """AC-13 — delta only populated when ≥2 history rows."""
    user = await _seed_pro_user(db_session)
    await _seed_card_due(db_session, user.id)
    await _seed_scan(
        db_session,
        user.id,
        score=80,
        scanned_at=datetime.now(timezone.utc),
    )

    payload = await pro_digest_service.compose_digest(user, db_session)
    assert payload is not None
    assert payload.last_scan_score == 80
    assert payload.last_scan_delta is None


# ── 3. send_pro_digest orchestrator (AC-6 / AC-8 / AC-9 / AC-10 / AC-11) ───


async def test_send_pro_digest_writes_email_log_row_on_success(db_session):
    user = await _seed_pro_user(db_session)
    await _seed_card_due(db_session, user.id)
    captured: list[tuple[str, dict]] = []

    async def _send_email_mock(*, to, subject, html_body):
        return "resend-msg-1"

    with patch.object(
        pro_digest_service.email_service, "send_email", new=AsyncMock(side_effect=_send_email_mock)
    ), patch.object(
        pro_digest_service, "analytics_track",
        side_effect=lambda uid, evt, props: captured.append((evt, props)),
    ):
        summary = await pro_digest_service.send_pro_digest(db_session)

    assert summary.sent == 1
    assert summary.skipped_dedup == 0
    assert summary.skipped_empty == 0
    assert summary.failed == 0
    assert summary.candidates_total == 1

    rows = (
        await db_session.execute(
            select(EmailLog).where(EmailLog.user_id == user.id)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].email_type == pro_digest_service.EMAIL_TYPE_PRO_DIGEST
    assert rows[0].sent_date == datetime.now(timezone.utc).date()
    assert rows[0].resend_id == "resend-msg-1"

    sent_events = [e for e, _ in captured if e == "pro_digest_sent"]
    assert len(sent_events) == 1


async def test_send_pro_digest_dedup_short_circuits_already_sent_users(
    db_session,
):
    """AC-6 / §6.2 — was_sent_today guard skips already-sent users."""
    user = await _seed_pro_user(db_session)
    await _seed_card_due(db_session, user.id)
    today = datetime.now(timezone.utc).date()
    db_session.add(
        EmailLog(
            id=str(uuid.uuid4()),
            user_id=user.id,
            email_type=pro_digest_service.EMAIL_TYPE_PRO_DIGEST,
            sent_date=today,
            resend_id="prior-tick",
        )
    )
    await db_session.flush()
    captured: list[tuple[str, dict]] = []

    with patch.object(
        pro_digest_service.email_service, "send_email", new=AsyncMock()
    ) as send_mock, patch.object(
        pro_digest_service, "analytics_track",
        side_effect=lambda uid, evt, props: captured.append((evt, props)),
    ):
        summary = await pro_digest_service.send_pro_digest(db_session)

    assert summary.sent == 0
    assert summary.skipped_dedup == 1
    send_mock.assert_not_called()
    assert any(e == "pro_digest_skipped_dedup" for e, _ in captured)


async def test_send_pro_digest_empty_content_user_fires_skipped_empty_event(
    db_session,
):
    """AC-7 / §12 D-7 — skip + telemetry when compose returns None."""
    user = await _seed_pro_user(db_session)
    captured: list[tuple[str, dict]] = []

    with patch.object(
        pro_digest_service.email_service, "send_email", new=AsyncMock()
    ) as send_mock, patch.object(
        pro_digest_service, "analytics_track",
        side_effect=lambda uid, evt, props: captured.append((evt, props)),
    ):
        summary = await pro_digest_service.send_pro_digest(db_session)

    assert summary.skipped_empty == 1
    assert summary.sent == 0
    send_mock.assert_not_called()
    rows = (
        await db_session.execute(
            select(EmailLog).where(EmailLog.user_id == user.id)
        )
    ).scalars().all()
    assert rows == []
    assert any(e == "pro_digest_skipped_empty" for e, _ in captured)


async def test_send_pro_digest_send_error_skips_record_send(db_session):
    """AC-9 / §12 D-8 — Resend permanent error: no email_log write."""
    user = await _seed_pro_user(db_session)
    await _seed_card_due(db_session, user.id)
    captured: list[tuple[str, dict]] = []

    async def _raise(*, to, subject, html_body):
        raise pro_digest_service.email_service.EmailSendError("permanent failure")

    with patch.object(
        pro_digest_service.email_service, "send_email", new=AsyncMock(side_effect=_raise)
    ), patch.object(
        pro_digest_service, "analytics_track",
        side_effect=lambda uid, evt, props: captured.append((evt, props)),
    ):
        summary = await pro_digest_service.send_pro_digest(db_session)

    assert summary.failed == 1
    assert summary.sent == 0
    rows = (
        await db_session.execute(
            select(EmailLog).where(EmailLog.user_id == user.id)
        )
    ).scalars().all()
    assert rows == []
    failed_events = [props for evt, props in captured if evt == "pro_digest_failed"]
    assert len(failed_events) == 1
    assert failed_events[0]["error_class"] == "send_error"


async def test_send_pro_digest_compose_error_skips_record_send(db_session):
    """AC-10 / §12 D-8 — compose error: no email_log write."""
    user = await _seed_pro_user(db_session)
    await _seed_card_due(db_session, user.id)
    captured: list[tuple[str, dict]] = []

    async def _explode(user, db):
        raise RuntimeError("compose explode")

    with patch.object(
        pro_digest_service, "compose_digest", new=AsyncMock(side_effect=_explode)
    ), patch.object(
        pro_digest_service.email_service, "send_email", new=AsyncMock()
    ) as send_mock, patch.object(
        pro_digest_service, "analytics_track",
        side_effect=lambda uid, evt, props: captured.append((evt, props)),
    ):
        summary = await pro_digest_service.send_pro_digest(db_session)

    assert summary.failed == 1
    send_mock.assert_not_called()
    rows = (
        await db_session.execute(
            select(EmailLog).where(EmailLog.user_id == user.id)
        )
    ).scalars().all()
    assert rows == []
    failed_props = [p for e, p in captured if e == "pro_digest_failed"]
    assert failed_props[0]["error_class"] == "compose_error"


async def test_send_pro_digest_is_idempotent_across_back_to_back_calls(
    db_session,
):
    """AC-11 — second invocation skips already-sent users via dedup."""
    user = await _seed_pro_user(db_session)
    await _seed_card_due(db_session, user.id)

    async def _send(*, to, subject, html_body):
        return "msg-1"

    with patch.object(
        pro_digest_service.email_service, "send_email", new=AsyncMock(side_effect=_send)
    ), patch.object(
        pro_digest_service, "analytics_track",
    ):
        first = await pro_digest_service.send_pro_digest(db_session)
        second = await pro_digest_service.send_pro_digest(db_session)

    assert first.sent == 1
    assert first.skipped_dedup == 0
    assert second.sent == 0
    assert second.skipped_dedup == 1


# ── 4. Spec #67 (E-052) — aggregate intent block ────────────────────────────


async def test_compose_digest_no_intent_path_unchanged(db_session):
    """Spec #67 AC-13 — composer return shape unchanged when no intent."""
    user = await _seed_pro_user(db_session)
    await _seed_card_due(db_session, user.id)

    payload = await pro_digest_service.compose_digest(user, db_session)
    assert payload is not None
    assert payload.aggregate_intent_block is None


async def test_compose_digest_intent_below_threshold_omits_block(db_session):
    """Spec #67 AC-14 — silent suppression when cohort < MIN_COHORT_SIZE."""
    from app.services import career_intent_service
    from app.schemas.career_intent import _current_quarter_tuple

    user = await _seed_pro_user(db_session)
    await _seed_card_due(db_session, user.id)
    user.persona = "career_climber"
    await db_session.flush()

    year, q = _current_quarter_tuple()
    quarter = f"{year}-Q{q + 1}" if q < 4 else f"{year + 1}-Q1"

    # Only this user has the intent — cohort=1 < 10.
    await career_intent_service.set_intent(
        db_session, user.id, "staff", quarter
    )

    payload = await pro_digest_service.compose_digest(user, db_session)
    assert payload is not None
    assert payload.aggregate_intent_block is None


async def test_compose_digest_intent_at_threshold_populates_block(db_session):
    """Spec #67 AC-15 — aggregate block populated when cohort ≥ 10."""
    import uuid
    from datetime import datetime, timezone
    from app.models.card import Card
    from app.models.card_progress import CardProgress
    from app.models.category import Category
    from app.schemas.career_intent import _current_quarter_tuple
    from app.services import career_intent_service

    year, q = _current_quarter_tuple()
    quarter = f"{year}-Q{q + 1}" if q < 4 else f"{year + 1}-Q1"

    cat = Category(
        id=str(uuid.uuid4()),
        name=f"system-design-{uuid.uuid4().hex[:6]}",
        icon="🧱",
        color="#000000",
        display_order=0,
        source="seed",
    )
    db_session.add(cat)
    await db_session.flush()
    card = Card(
        id=str(uuid.uuid4()),
        category_id=cat.id,
        question="Q?",
        answer="A.",
        difficulty="medium",
    )
    db_session.add(card)
    await db_session.flush()

    main_user = await _seed_pro_user(db_session)
    main_user.persona = "career_climber"
    await db_session.flush()
    await _seed_card_due(db_session, main_user.id)
    await career_intent_service.set_intent(
        db_session, main_user.id, "distinguished", quarter
    )
    db_session.add(
        CardProgress(
            id=str(uuid.uuid4()),
            user_id=main_user.id,
            card_id=card.id,
            state="review",
            stability=1.0,
            difficulty_fsrs=5.0,
            due_date=datetime.now(timezone.utc),
            reps=10,
            lapses=0,
        )
    )
    # Add 9 more cohort members (10 total) — meets threshold.
    for _ in range(9):
        peer = await _seed_user(db_session)
        peer.persona = "career_climber"
        await db_session.flush()
        await career_intent_service.set_intent(
            db_session, peer.id, "distinguished", quarter
        )
        db_session.add(
            CardProgress(
                id=str(uuid.uuid4()),
                user_id=peer.id,
                card_id=card.id,
                state="review",
                stability=1.0,
                difficulty_fsrs=5.0,
                due_date=datetime.now(timezone.utc),
                reps=5,
                lapses=0,
            )
        )
    await db_session.flush()

    payload = await pro_digest_service.compose_digest(main_user, db_session)
    assert payload is not None
    assert payload.aggregate_intent_block is not None
    assert payload.aggregate_intent_block.target_role == "distinguished"
    # Tolerate leaked rows from prior committed tests in the same session;
    # the contract under test is "cohort >= MIN_COHORT_SIZE → block populated".
    assert (
        payload.aggregate_intent_block.cohort_size
        >= career_intent_service.MIN_COHORT_SIZE
    )
    assert len(payload.aggregate_intent_block.top_categories) >= 1
