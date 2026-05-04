"""Phase 6 slice 6.14 — daily Pro digest cron consumer.

Spec: docs/specs/phase-6/14-daily-digest-cron.md §6 + §12 D-1..D-14.

Three public functions:

- ``select_candidates(db)`` — Pro/Enterprise active subscribers w/o
  opt-out (§6.1, §12 D-6). Pro-tier gating happens in the SQL selector,
  not middleware (§4.4 — no HTTP route).
- ``compose_digest(user, db)`` — per-user payload composer; returns
  ``None`` per §12 D-7 strict empty-rule when all-three engagement
  signals are zero.
- ``send_pro_digest(db)`` — orchestrator. Iterates candidates
  sequentially per §12 D-11, fires dedup short-circuit per §6.2, sends
  via Phase-2 ``email_service.send_email``, records via slice-6.13
  ``email_log_service.record_send``, fires 4 PostHog events per §12
  D-10. Returns ``SendSummary`` for the CLI to print as JSON.

Idempotent end-to-end (§6.5): re-invocation on the same UTC day is a
no-op for already-sent users via the ``was_sent_today`` short-circuit.
``record_send`` raises IntegrityError on UNIQUE collision (slice 6.13
contract); the orchestrator catches that as a concurrent-tick already-
sent and counts it under ``skipped_dedup``.

Failure-mode contract per §4.3 + §12 D-8: ``EmailSendError`` and
``compose_digest`` exceptions DO NOT write ``email_log`` rows so the
next cron tick retries. ``pro_digest_failed`` event fires with
``error_class``.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import desc, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.models.card_progress import CardProgress
from app.models.email_log import EmailLog
from app.models.email_preference import EmailPreference
from app.models.gamification import GamificationStats
from app.models.mission import Mission
from app.models.subscription import Subscription
from app.models.tracker_application_score import TrackerApplicationScore
from app.models.user import User
from app.schemas.pro_digest import DigestPayload, SendSummary
from app.services import career_intent_service, email_log_service, email_service

logger = logging.getLogger(__name__)


EMAIL_TYPE_PRO_DIGEST = "pro_digest"
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


# ── Selector (§6.1, §12 D-6) ────────────────────────────────────────────────


async def select_candidates(db: AsyncSession) -> list[User]:
    """Pro/Enterprise active subscribers who have not opted out.

    Pro-tier gating + opt-out filter happen here (§4.4, §6.1). Engagement
    -signal filter is applied by ``compose_digest`` per §6.3 + §12 D-7
    (returning None → ``skipped_empty`` event).

    Outer-join on ``email_preferences`` so Pro users without a
    preference row default to "opted-in" (no row → ``daily_digest_opt_out``
    is NULL → ``IS NOT TRUE`` matches).
    """
    stmt = (
        select(User)
        .join(Subscription, Subscription.user_id == User.id)
        .outerjoin(EmailPreference, EmailPreference.user_id == User.id)
        .where(Subscription.plan.in_(("pro", "enterprise")))
        .where(Subscription.status == "active")
        .where(
            or_(
                EmailPreference.daily_digest_opt_out.is_(False),
                EmailPreference.daily_digest_opt_out.is_(None),
            )
        )
    )
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows)


# ── Compose (§6.3, §12 D-3 / D-7) ───────────────────────────────────────────


async def compose_digest(
    user: User, db: AsyncSession
) -> Optional[DigestPayload]:
    """Build the per-user payload from existing tables.

    Returns ``None`` per §12 D-7 strict empty-rule when ALL of
    (cards_due == 0, !mission_active, last_scan_score is None,
    aggregate_intent_block is None). Spec #67 §6.3 extends the rule
    additively — a CC user with no cards / mission / scan but WITH a
    current intent + ≥10 cohort still receives the digest.
    """
    cards_due = await _count_cards_due(db, user.id)
    streak = await _get_streak(db, user.id)
    mission_active, mission_days_left = await _mission_info(db, user.id)
    last_scan_score, last_scan_delta = await _last_scan_info(db, user.id)
    aggregate_intent_block = await _aggregate_intent_block(db, user.id)

    # §12 D-7 strict empty-rule (extended by spec #67 §6.3).
    if (
        cards_due == 0
        and not mission_active
        and last_scan_score is None
        and aggregate_intent_block is None
    ):
        return None

    return DigestPayload(
        user_id=user.id,
        user_name=user.name or user.email or "there",
        user_email=user.email,
        cards_due=cards_due,
        streak=streak,
        mission_active=mission_active,
        mission_days_left=mission_days_left,
        last_scan_score=last_scan_score,
        last_scan_delta=last_scan_delta,
        aggregate_intent_block=aggregate_intent_block,
    )


async def _aggregate_intent_block(db: AsyncSession, user_id: str):
    """Spec #67 §6.5 — wraps career_intent reads in try/except so a DB
    timeout cannot block the digest send. Returns None on failure, fires
    ``pro_digest_intent_aggregate_failed`` for ops visibility.
    """
    try:
        intent = await career_intent_service.get_current_intent(db, user_id)
        if intent is None:
            return None
        return await career_intent_service.get_aggregate_stats(
            db, intent.target_role, intent.target_quarter
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "pro_digest aggregate_intent_block failed for user %s: %s",
            user_id,
            exc,
        )
        analytics_track(
            user_id,
            "pro_digest_intent_aggregate_failed",
            {
                "user_id": user_id,
                "error_class": type(exc).__name__,
                "internal": True,
            },
        )
        return None


async def _count_cards_due(db: AsyncSession, user_id: str) -> int:
    """Count of CardProgress rows where due_date <= now() for this user.

    Mirrors ``reminder_service:75-97`` precedent (Phase-2 reminder selector)
    but filtered per-user instead of joined-on-prefs.
    """
    result = await db.execute(
        select(func.count())
        .select_from(CardProgress)
        .where(CardProgress.user_id == user_id)
        .where(CardProgress.due_date <= func.now())
    )
    count = result.scalar_one_or_none()
    return int(count or 0)


async def _get_streak(db: AsyncSession, user_id: str) -> int:
    """``GamificationStats.current_streak`` (default 0 if no row).

    Mirrors ``reminder_service._get_streak`` precedent verbatim.
    """
    result = await db.execute(
        select(GamificationStats.current_streak).where(
            GamificationStats.user_id == user_id
        )
    )
    row = result.scalar_one_or_none()
    return int(row) if row is not None else 0


async def _mission_info(
    db: AsyncSession, user_id: str
) -> tuple[bool, Optional[int]]:
    """First active mission for the user (if any).

    Returns (mission_active, mission_days_left). ``days_left`` may be
    negative if the target date passed without status flip — surface as-is.
    """
    result = await db.execute(
        select(Mission.target_date)
        .where(Mission.user_id == user_id)
        .where(Mission.status == "active")
        .order_by(Mission.target_date.asc())
        .limit(1)
    )
    target = result.scalar_one_or_none()
    if target is None:
        return False, None
    today_utc = datetime.now(timezone.utc).date()
    days_left = (target - today_utc).days
    return True, days_left


async def _last_scan_info(
    db: AsyncSession, user_id: str
) -> tuple[Optional[int], Optional[int]]:
    """Latest tracker_application_scores row + delta vs prior.

    Mirrors HomeScoreDeltaWidget's ``history.length >= 2`` gate per
    spec §6.3 — populates the delta only when at least 2 scores exist.
    """
    result = await db.execute(
        select(TrackerApplicationScore.overall_score)
        .where(TrackerApplicationScore.user_id == user_id)
        .order_by(desc(TrackerApplicationScore.scanned_at))
        .limit(2)
    )
    rows = list(result.scalars().all())
    if not rows:
        return None, None
    latest = int(rows[0])
    if len(rows) < 2:
        return latest, None
    prior = int(rows[1])
    return latest, latest - prior


# ── Template render (§6.4, §12 D-4) ─────────────────────────────────────────


def _load_template() -> str:
    """Read the Pro digest HTML template from disk."""
    return (_TEMPLATE_DIR / "pro_digest.html").read_text()


def _build_subject(payload: DigestPayload) -> str:
    """Subject line — leans on the strongest signal in the payload."""
    if payload.cards_due > 0:
        return f"Your daily Pro digest — {payload.cards_due} cards due today"
    if payload.mission_active:
        return f"Your daily Pro digest — mission countdown: {payload.mission_days_left} days"
    return "Your daily Pro digest"


def _build_html(payload: DigestPayload) -> str:
    """Template substitution per §12 D-4 (CSS-driven empty-section visibility).

    Sections without content get ``display:none`` style block; populated
    sections get the default style (empty replacement). Mirrors Phase-2
    ``reminder_service.build_email_body`` simple ``str.replace`` pattern;
    no Jinja2.
    """
    template = _load_template()

    cards_section_style = "" if payload.cards_due > 0 else "display:none;"
    mission_section_style = "" if payload.mission_active else "display:none;"
    scan_section_style = "" if payload.last_scan_score is not None else "display:none;"
    intent_section_style = (
        "" if payload.aggregate_intent_block is not None else "display:none;"
    )
    intent_role_label, intent_copy = _intent_block_copy(
        payload.aggregate_intent_block
    )

    streak_unit = "day" if payload.streak == 1 else "days"

    if payload.last_scan_delta is None:
        delta_display = "no prior scan"
    elif payload.last_scan_delta > 0:
        delta_display = f"+{payload.last_scan_delta} vs prior"
    elif payload.last_scan_delta < 0:
        delta_display = f"{payload.last_scan_delta} vs prior"
    else:
        delta_display = "unchanged"

    app_url = os.getenv("FRONTEND_URL", "http://localhost:5199")
    study_link = f"{app_url}/learn/daily?utm_source=email&utm_medium=pro_digest"
    prefs_link = f"{app_url}/profile?section=email-preferences"

    replacements = {
        "{{name}}": payload.user_name,
        "{{cards_due}}": str(payload.cards_due),
        "{{streak}}": str(payload.streak),
        "{{streak_unit}}": streak_unit,
        "{{mission_days_left}}": str(payload.mission_days_left or 0),
        "{{last_scan_score}}": str(payload.last_scan_score or 0),
        "{{last_scan_delta_display}}": delta_display,
        "{{cards_section_style}}": cards_section_style,
        "{{mission_section_style}}": mission_section_style,
        "{{scan_section_style}}": scan_section_style,
        "{{intent_section_style}}": intent_section_style,
        "{{intent_role_label}}": intent_role_label,
        "{{intent_copy}}": intent_copy,
        "{{study_link}}": study_link,
        "{{prefs_link}}": prefs_link,
    }
    out = template
    for key, value in replacements.items():
        out = out.replace(key, value)
    return out


_ROLE_LABELS: dict[str, str] = {
    "staff": "Staff",
    "senior_staff": "Senior Staff",
    "principal": "Principal",
    "distinguished": "Distinguished",
    "em": "Engineering Manager",
    "sr_em": "Senior EM",
    "director": "Director",
}


def _intent_block_copy(block) -> tuple[str, str]:
    """Spec #67 §8.5 — aggregate-only copy for the intent block.

    Privacy contract: copy uses ONLY aggregate phrasing (§8.5 ban list
    enforced via snapshot test). Returns ``("", "")`` when no block, so
    the template substitution leaves the section visually empty (its
    ``display:none`` style hides the wrapper in that case).
    """
    if block is None:
        return "", ""
    role_label = _ROLE_LABELS.get(block.target_role, block.target_role)
    parts = [
        f"{share.percent_of_study_time:g}% on {share.category_name}"
        for share in block.top_categories
    ]
    if not parts:
        return role_label, ""
    if len(parts) == 1:
        joined = parts[0]
    elif len(parts) == 2:
        joined = f"{parts[0]} and {parts[1]}"
    else:
        joined = ", ".join(parts[:-1]) + f", and {parts[-1]}"
    copy = (
        f"Engineers targeting {role_label} this quarter spend {joined} "
        f"of study time."
    )
    return role_label, copy


# ── Orchestrator (§6.5, §12 D-8/D-10/D-11) ──────────────────────────────────


async def send_pro_digest(db: AsyncSession) -> SendSummary:
    """Fan-out + dedup + send + record. Cron-safe + idempotent.

    Per §6.5 + §4.3 failure-mode contract: ``EmailSendError`` /
    ``compose_digest`` errors leave the user re-eligible for the next
    tick (no ``email_log`` write). Concurrent tick collision on
    ``record_send`` (IntegrityError) → counted under ``skipped_dedup``.
    """
    started_at = time.monotonic()
    today_utc = datetime.now(timezone.utc).date()

    candidates = await select_candidates(db)
    summary = SendSummary(candidates_total=len(candidates))

    for user in candidates:
        # 1. Dedup short-circuit (§6.2).
        if await email_log_service.was_sent_today(
            db, user.id, EMAIL_TYPE_PRO_DIGEST, today_utc
        ):
            summary.skipped_dedup += 1
            analytics_track(
                user.id,
                "pro_digest_skipped_dedup",
                {"user_id": user.id, "internal": True},
            )
            continue

        # 2. Compose (§6.3 + §12 D-7 empty-rule).
        try:
            payload = await compose_digest(user, db)
        except Exception as exc:  # noqa: BLE001
            summary.failed += 1
            logger.warning(
                "pro_digest compose error for user %s: %s", user.id, exc
            )
            analytics_track(
                user.id,
                "pro_digest_failed",
                {
                    "user_id": user.id,
                    "plan": _plan_for_user(user),
                    "error_class": "compose_error",
                    "internal": True,
                },
            )
            continue

        if payload is None:
            summary.skipped_empty += 1
            analytics_track(
                user.id,
                "pro_digest_skipped_empty",
                {
                    "user_id": user.id,
                    "plan": _plan_for_user(user),
                    "internal": True,
                },
            )
            continue

        # 3. Render + send (§6.4 + Phase-2 email_service).
        try:
            subject = _build_subject(payload)
            html = _build_html(payload)
            resend_id = await email_service.send_email(
                to=payload.user_email, subject=subject, html_body=html
            )
        except email_service.EmailSendError as exc:
            summary.failed += 1
            logger.warning(
                "pro_digest send error for user %s: %s", user.id, exc
            )
            analytics_track(
                user.id,
                "pro_digest_failed",
                {
                    "user_id": user.id,
                    "plan": _plan_for_user(user),
                    "error_class": "send_error",
                    "internal": True,
                },
            )
            continue

        # 4. Record + emit sent event.
        try:
            await email_log_service.record_send(
                db,
                user_id=user.id,
                email_type=EMAIL_TYPE_PRO_DIGEST,
                sent_date=today_utc,
                resend_id=resend_id,
            )
        except IntegrityError:
            # Concurrent-tick already-sent (§6.5).
            await db.rollback()
            summary.skipped_dedup += 1
            analytics_track(
                user.id,
                "pro_digest_skipped_dedup",
                {"user_id": user.id, "internal": True},
            )
            continue
        except SQLAlchemyError as exc:  # pragma: no cover — defensive
            await db.rollback()
            summary.failed += 1
            logger.warning(
                "pro_digest record_send error for user %s: %s", user.id, exc
            )
            analytics_track(
                user.id,
                "pro_digest_failed",
                {
                    "user_id": user.id,
                    "plan": _plan_for_user(user),
                    "error_class": "record_error",
                    "internal": True,
                },
            )
            continue

        summary.sent += 1
        analytics_track(
            user.id,
            "pro_digest_sent",
            {
                "user_id": user.id,
                "plan": _plan_for_user(user),
                "cards_due": payload.cards_due,
                "streak": payload.streak,
                "has_mission": payload.mission_active,
                "has_recent_scan": payload.last_scan_score is not None,
                "has_aggregate_block": payload.aggregate_intent_block
                is not None,
                "resend_id": resend_id,
                "internal": True,
            },
        )

        # Spec #67 §9.1 + D-13 — fire ONLY on actual send-success path,
        # gated on aggregate block being present in the payload.
        if payload.aggregate_intent_block is not None:
            block = payload.aggregate_intent_block
            top_category = (
                block.top_categories[0].category_name
                if block.top_categories
                else None
            )
            analytics_track(
                user.id,
                "career_intent_email_block_rendered",
                {
                    "target_role": block.target_role,
                    "target_quarter": block.target_quarter,
                    "cohort_size": block.cohort_size,
                    "top_category": top_category,
                    "internal": True,
                },
            )

    # Caller owns transaction commit (mirrors slice 6.0
    # ``analytics_event_service`` / slice 6.13 ``email_log_service``
    # write-only convention). The CLI script
    # ``app/scripts/send_pro_digest.py`` commits after this returns;
    # tests under ``conftest.db_session`` rely on rollback isolation
    # so this function flushes (via ``email_log_service.record_send``)
    # but does NOT commit.

    summary.duration_seconds = round(time.monotonic() - started_at, 3)
    logger.info(
        "pro_digest tick complete: sent=%d skipped_dedup=%d skipped_empty=%d "
        "failed=%d candidates_total=%d duration_seconds=%.3f",
        summary.sent,
        summary.skipped_dedup,
        summary.skipped_empty,
        summary.failed,
        summary.candidates_total,
        summary.duration_seconds,
    )
    return summary


def _plan_for_user(user: User) -> str:
    """Best-effort plan label for analytics payloads.

    The selector already filtered to plan IN ('pro','enterprise'), so the
    user MUST have one of those plans on disk; we read from the
    relationship if eager-loaded, else fall back to ``'pro'`` (the
    common case) — this is a telemetry hint, not load-bearing for
    business logic.
    """
    sub = getattr(user, "subscription", None)
    if sub is not None:
        return getattr(sub, "plan", "pro") or "pro"
    return "pro"


__all__ = [
    "EMAIL_TYPE_PRO_DIGEST",
    "compose_digest",
    "select_candidates",
    "send_pro_digest",
]
