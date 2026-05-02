"""Admin content-quality aggregator — Phase 6 slice 6.11.

Spec: docs/specs/phase-6/11-content-quality-retention.md §6 +
§11 AC-1..AC-18 + §12 D-1..D-16.

Public API (single entry):
  - ``aggregate_dashboard(db, *, window_days, include_archived)``

Reads (G-2 read-only over user data):
  - ``Lesson`` + ``Deck`` join (archived filter per request flag)
  - ``QuizReviewEvent`` (per-lesson + per-quiz_item rollups)
  - ``LessonViewEvent`` (view-volume denominator; D-14)
  - ``QuizItem`` (preview text + retired filter)

Writes:
  - ``Lesson.quality_score`` (idempotent IS DISTINCT FROM gate; D-1)

# layer-3 user-signal v1; layer-1 critique signal joined via
# card_quality_signals table per LD J2 (slice 6.13.5a / B-094a).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_event import LessonViewEvent, QuizReviewEvent
from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.schemas.admin_content_quality import (
    AdminContentQualityResponse,
    DeckQualityRow,
    LessonQualityRow,
    QuizItemQualityRow,
)
from app.schemas.card_quality_signal import CardQualitySignalWrite
from app.services import card_quality_signal_service

logger = logging.getLogger(__name__)


# ── Locked constants (§6.1 + §12 D-2..D-4) ──────────────────────────────────

DEFAULT_WINDOW_DAYS = 30  # D-3
MIN_WINDOW_DAYS = 7  # D-3 lower clamp
MAX_WINDOW_DAYS = 90  # D-3 upper clamp
MIN_REVIEW_THRESHOLD = 10  # D-4 — non-NULL writeback threshold
WORST_LESSONS_CAP = 25
WORST_QUIZ_ITEMS_CAP = 50
QUESTION_PREVIEW_CHARS = 80

# Bayesian smoothing prior (D-2): 0.5 neutral × prior weight 10
# (= MIN_REVIEW_THRESHOLD by symmetry — at N=10 raw and smoothed
# contribute equally).
SMOOTHING_PRIOR_PASS_RATE = 0.5
SMOOTHING_PRIOR_WEIGHT = 10

# Rating semantics from slice 6.8 D-5 (§12 D-13). py-fsrs Rating:
# Again=1, Hard=2, Good=3, Easy=4. Pass = (3, 4); lapse = (1).
# Hard=2 excluded from both surfaces.
_RECALL_RATINGS = (3, 4)
_LAPSE_RATING = 1


def _smooth(passes: int, total: int) -> float:
    """Bayesian-smoothed pass_rate (§6.1 / D-2)."""
    return (passes + SMOOTHING_PRIOR_PASS_RATE * SMOOTHING_PRIOR_WEIGHT) / (
        total + SMOOTHING_PRIOR_WEIGHT
    )


# ── Public API ──────────────────────────────────────────────────────────────


async def aggregate_dashboard(
    db: AsyncSession,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    include_archived: bool = False,
) -> AdminContentQualityResponse:
    """Aggregate the content-quality dashboard + writeback quality_score.

    Side-effect: idempotent UPDATEs to ``lessons.quality_score`` for
    every lesson where ``review_count_window >= MIN_REVIEW_THRESHOLD``
    AND the smoothed score differs from the persisted value (D-1 / D-4
    / audit finding #14 IS DISTINCT FROM gate).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    lessons_by_id, decks_by_id = await _load_visible_content(
        db, include_archived=include_archived
    )

    review_rows = await _load_review_events(
        db, lesson_ids=list(lessons_by_id.keys()), cutoff=cutoff
    )
    view_rows = await _load_view_events(
        db, lesson_ids=list(lessons_by_id.keys()), cutoff=cutoff
    )
    quiz_items_by_id = await _load_quiz_items(
        db, lesson_ids=list(lessons_by_id.keys())
    )

    lesson_stats = _rollup_per_lesson(review_rows, view_rows, lessons_by_id)
    quiz_item_stats = _rollup_per_quiz_item(review_rows, quiz_items_by_id)

    writebacks_applied = await _writeback_quality_scores(
        db, lessons_by_id=lessons_by_id, lesson_stats=lesson_stats
    )

    # Slice 6.13.5a — per-quiz_item user-aggregate writeback to
    # ``card_quality_signals``. Mirrors lesson-level Bayesian-smoothing /
    # threshold / IS DISTINCT FROM idempotency from slice 6.11 D-2 / D-4 /
    # finding #14, but writes to ``card_quality_signals`` rows rather than
    # a denormalised column on ``quiz_items`` (per §12 D-2).
    quiz_item_writebacks = await _writeback_quiz_item_user_review_signals(
        db,
        quiz_item_stats=quiz_item_stats,
        quiz_items_by_id=quiz_items_by_id,
    )
    writebacks_applied += quiz_item_writebacks

    # Re-read persisted scores so the response reflects the post-writeback
    # state visible to the ranker (idempotent + observable per AC-7).
    persisted_scores = {
        lid: lessons_by_id[lid].quality_score for lid in lessons_by_id
    }

    # Slice 6.13.5a — read-side join: critique scores per lesson +
    # per-quiz_item persisted user_review pass_rate. Both come from
    # ``card_quality_signals`` and are tolerant of empty / cold-start state
    # (return {} when no rows match).
    critique_scores_by_lesson = (
        await card_quality_signal_service.get_critique_scores_for_lessons(
            list(lessons_by_id.keys()), db
        )
    )
    quiz_item_persisted_pass_rates = (
        await card_quality_signal_service.get_persisted_user_review_scores_for_quiz_items(
            list(quiz_items_by_id.keys()), db
        )
    )

    deck_rows = _build_deck_rows(decks_by_id, lessons_by_id, lesson_stats)
    lesson_rows = _build_lesson_rows(
        lessons_by_id,
        decks_by_id,
        lesson_stats,
        persisted_scores,
        critique_scores_by_lesson=critique_scores_by_lesson,
    )
    quiz_item_rows = _build_quiz_item_rows(
        quiz_items_by_id,
        quiz_item_stats,
        lessons_by_id,
        persisted_pass_rates=quiz_item_persisted_pass_rates,
    )

    is_cold_start = sum(s["review_count"] for s in lesson_stats.values()) == 0

    return AdminContentQualityResponse(
        window_days=window_days,
        include_archived=include_archived,
        generated_at=datetime.now(timezone.utc),
        is_cold_start=is_cold_start,
        decks=deck_rows,
        worst_lessons=lesson_rows,
        worst_quiz_items=quiz_item_rows,
        writebacks_applied=writebacks_applied,
    )


# ── Loaders ─────────────────────────────────────────────────────────────────


async def _load_visible_content(
    db: AsyncSession, *, include_archived: bool
) -> tuple[dict[str, Lesson], dict[str, Deck]]:
    """Lessons + decks visible per the include_archived flag.

    Persona/tier filters intentionally NOT applied — admin sees the
    universe (G-1).
    """
    deck_filters = []
    lesson_filters = []
    if not include_archived:
        deck_filters.append(Deck.archived_at.is_(None))
        lesson_filters.append(Lesson.archived_at.is_(None))

    decks = (
        await db.execute(
            select(Deck).where(*deck_filters) if deck_filters else select(Deck)
        )
    ).scalars().all()
    decks_by_id = {d.id: d for d in decks}

    lesson_query = select(Lesson).where(
        Lesson.deck_id.in_(list(decks_by_id.keys()) or [""]),
        *lesson_filters,
    )
    lessons = (await db.execute(lesson_query)).scalars().all()
    lessons_by_id = {ll.id: ll for ll in lessons}
    return lessons_by_id, decks_by_id


async def _load_review_events(
    db: AsyncSession, *, lesson_ids: list[str], cutoff: datetime
) -> list[QuizReviewEvent]:
    if not lesson_ids:
        return []
    return list(
        (
            await db.execute(
                select(QuizReviewEvent).where(
                    QuizReviewEvent.lesson_id.in_(lesson_ids),
                    QuizReviewEvent.reviewed_at >= cutoff,
                )
            )
        ).scalars().all()
    )


async def _load_view_events(
    db: AsyncSession, *, lesson_ids: list[str], cutoff: datetime
) -> list[LessonViewEvent]:
    if not lesson_ids:
        return []
    return list(
        (
            await db.execute(
                select(LessonViewEvent).where(
                    LessonViewEvent.lesson_id.in_(lesson_ids),
                    LessonViewEvent.viewed_at >= cutoff,
                )
            )
        ).scalars().all()
    )


async def _load_quiz_items(
    db: AsyncSession, *, lesson_ids: list[str]
) -> dict[str, QuizItem]:
    """Active quiz_items only — retired rows are hidden per §12 D-8."""
    if not lesson_ids:
        return {}
    rows = (
        await db.execute(
            select(QuizItem).where(
                QuizItem.lesson_id.in_(lesson_ids),
                QuizItem.retired_at.is_(None),
            )
        )
    ).scalars().all()
    return {qi.id: qi for qi in rows}


# ── Rollups ─────────────────────────────────────────────────────────────────


def _rollup_per_lesson(
    review_rows: list[QuizReviewEvent],
    view_rows: list[LessonViewEvent],
    lessons_by_id: dict[str, Lesson],
) -> dict[str, dict]:
    """Return per-lesson stats keyed by lesson_id.

    Each entry: {review_count, passes, lapses, view_count}.
    """
    out: dict[str, dict] = {
        lid: {"review_count": 0, "passes": 0, "lapses": 0, "view_count": 0}
        for lid in lessons_by_id
    }
    for ev in review_rows:
        bucket = out.get(ev.lesson_id)
        if bucket is None:
            continue
        bucket["review_count"] += 1
        if ev.rating in _RECALL_RATINGS:
            bucket["passes"] += 1
        elif ev.rating == _LAPSE_RATING:
            bucket["lapses"] += 1
        # Hard (rating=2) excluded from both per D-13.
    for ev in view_rows:
        bucket = out.get(ev.lesson_id)
        if bucket is None:
            continue
        bucket["view_count"] += 1
    return out


def _rollup_per_quiz_item(
    review_rows: list[QuizReviewEvent],
    quiz_items_by_id: dict[str, QuizItem],
) -> dict[str, dict]:
    """Return per-quiz_item stats keyed by quiz_item_id."""
    out: dict[str, dict] = {
        qid: {"review_count": 0, "passes": 0, "lapses": 0}
        for qid in quiz_items_by_id
    }
    for ev in review_rows:
        bucket = out.get(ev.quiz_item_id)
        if bucket is None:
            continue
        bucket["review_count"] += 1
        if ev.rating in _RECALL_RATINGS:
            bucket["passes"] += 1
        elif ev.rating == _LAPSE_RATING:
            bucket["lapses"] += 1
    return out


# ── Writeback (D-1 / D-4 / audit finding #14) ───────────────────────────────


async def _writeback_quality_scores(
    db: AsyncSession,
    *,
    lessons_by_id: dict[str, Lesson],
    lesson_stats: dict[str, dict],
) -> int:
    """Idempotent UPDATEs against ``lessons.quality_score``.

    Per D-1 / D-4: writeback only when ``review_count >= MIN_REVIEW_THRESHOLD``.
    Per audit finding #14: ``IS DISTINCT FROM`` semantics so re-runs are
    no-ops (NULL → value transition is included; identical-value
    transition is skipped).
    """
    applied = 0
    for lesson_id, stats in lesson_stats.items():
        if stats["review_count"] < MIN_REVIEW_THRESHOLD:
            continue
        smoothed = _smooth(stats["passes"], stats["review_count"])
        new_score = Decimal(f"{round(smoothed, 2):.2f}")
        try:
            current = lessons_by_id[lesson_id].quality_score
            if current is not None and Decimal(current) == new_score:
                continue
            result = await db.execute(
                update(Lesson)
                .where(
                    Lesson.id == lesson_id,
                    or_(
                        Lesson.quality_score.is_(None),
                        Lesson.quality_score != new_score,
                    ),
                )
                .values(quality_score=new_score)
            )
            if (result.rowcount or 0) > 0:
                lessons_by_id[lesson_id].quality_score = new_score
                applied += 1
        except SQLAlchemyError:  # pragma: no cover — defensive
            logger.warning(
                "admin_content_quality_service: writeback failed for "
                "lesson %s; skipping",
                lesson_id,
            )
            continue
    if applied:
        await db.flush()
    return applied


async def _writeback_quiz_item_user_review_signals(
    db: AsyncSession,
    *,
    quiz_item_stats: dict[str, dict],
    quiz_items_by_id: dict[str, QuizItem],
) -> int:
    """Per-quiz_item user-aggregate writeback to ``card_quality_signals``.

    Per §12 D-2 (writeback target = card_quality_signals row only) +
    §6.5 (mirror slice 6.11 D-1 / D-4 / finding #14 IS DISTINCT FROM
    idempotency gate). Writes one
    ``signal_source='user_review', dimension='pass_rate'`` row per
    quiz_item that has crossed ``MIN_REVIEW_THRESHOLD`` reviews in the
    window AND whose smoothed score has changed since last writeback
    (matches the lesson-level idempotency that slice 6.11's tests
    encode).

    Returns the count of UPSERTs that actually flipped the score —
    unchanged scores are skipped entirely so re-runs of
    ``aggregate_dashboard`` produce ``writebacks_applied=0`` mirroring
    the lesson-level path.
    """
    candidate_ids = [
        qid
        for qid, stats in quiz_item_stats.items()
        if stats.get("review_count", 0) >= MIN_REVIEW_THRESHOLD
        and qid in quiz_items_by_id
    ]
    if not candidate_ids:
        return 0
    persisted = (
        await card_quality_signal_service.get_persisted_user_review_scores_for_quiz_items(
            candidate_ids, db
        )
    )

    written = 0
    for quiz_item_id in candidate_ids:
        stats = quiz_item_stats[quiz_item_id]
        smoothed = round(_smooth(stats["passes"], stats["review_count"]), 2)
        existing = persisted.get(quiz_item_id)
        if existing is not None and round(existing, 2) == smoothed:
            continue
        try:
            await card_quality_signal_service.upsert_signal(
                CardQualitySignalWrite(
                    lesson_id=quiz_items_by_id[quiz_item_id].lesson_id,
                    quiz_item_id=quiz_item_id,
                    signal_source="user_review",
                    dimension="pass_rate",
                    score=smoothed,
                    source_ref=None,
                    recorded_by_user_id=None,
                ),
                db,
            )
            written += 1
        except SQLAlchemyError:  # pragma: no cover — defensive
            logger.warning(
                "admin_content_quality_service: per-quiz_item UPSERT "
                "failed for quiz_item=%s; skipping",
                quiz_item_id,
            )
            continue
    return written


# ── Row builders ────────────────────────────────────────────────────────────


def _build_deck_rows(
    decks_by_id: dict[str, Deck],
    lessons_by_id: dict[str, Lesson],
    lesson_stats: dict[str, dict],
) -> list[DeckQualityRow]:
    """Per-deck rollup ordered by review_count_window DESC + display_order ASC."""
    by_deck: dict[str, list[Lesson]] = {}
    for lesson in lessons_by_id.values():
        by_deck.setdefault(lesson.deck_id, []).append(lesson)

    rows: list[DeckQualityRow] = []
    for deck_id, deck in decks_by_id.items():
        deck_lessons = by_deck.get(deck_id, [])
        review_count = 0
        weighted_num = 0.0
        scored_lessons: list[float] = []
        for lesson in deck_lessons:
            stats = lesson_stats.get(lesson.id, {})
            rc = stats.get("review_count", 0)
            review_count += rc
            if rc > 0:
                pass_rate = stats["passes"] / rc
                weighted_num += pass_rate * rc
            if lesson.quality_score is not None:
                scored_lessons.append(float(lesson.quality_score))

        weighted_pass_rate = (
            weighted_num / review_count if review_count > 0 else None
        )
        avg_quality = (
            sum(scored_lessons) / len(scored_lessons)
            if scored_lessons
            else None
        )
        rows.append(
            DeckQualityRow(
                deck_id=deck.id,
                deck_slug=deck.slug,
                deck_title=deck.title,
                tier=deck.tier,
                persona_visibility=deck.persona_visibility,
                archived=deck.archived_at is not None,
                lesson_count=len(deck_lessons),
                review_count_window=review_count,
                weighted_pass_rate=weighted_pass_rate,
                avg_quality_score=avg_quality,
            )
        )
    rows.sort(
        key=lambda r: (
            -r.review_count_window,
            decks_by_id[r.deck_id].display_order,
        )
    )
    return rows


def _build_lesson_rows(
    lessons_by_id: dict[str, Lesson],
    decks_by_id: dict[str, Deck],
    lesson_stats: dict[str, dict],
    persisted_scores: dict[str, Optional[Decimal]],
    *,
    critique_scores_by_lesson: Optional[dict[str, dict[str, float]]] = None,
) -> list[LessonQualityRow]:
    """Worst-first lessons sorted by smoothed_quality_score ASC NULLS LAST.

    Capped at WORST_LESSONS_CAP. Lessons with zero reviews in the window
    are excluded (no signal to surface).
    """
    rows: list[LessonQualityRow] = []
    for lesson_id, lesson in lessons_by_id.items():
        stats = lesson_stats.get(lesson_id, {})
        rc = stats.get("review_count", 0)
        if rc == 0:
            continue
        passes = stats["passes"]
        pass_rate = passes / rc if rc > 0 else None
        low_volume = rc < MIN_REVIEW_THRESHOLD
        smoothed = None if low_volume else round(_smooth(passes, rc), 4)
        persisted = persisted_scores.get(lesson_id)
        deck = decks_by_id.get(lesson.deck_id)
        critique_for_lesson = (
            (critique_scores_by_lesson or {}).get(lesson.id) or None
        )
        rows.append(
            LessonQualityRow(
                lesson_id=lesson.id,
                lesson_slug=lesson.slug,
                lesson_title=lesson.title,
                deck_id=lesson.deck_id,
                deck_slug=deck.slug if deck else "",
                review_count_window=rc,
                view_count_window=stats.get("view_count", 0),
                pass_rate=pass_rate,
                smoothed_quality_score=smoothed,
                persisted_quality_score=(
                    float(persisted) if persisted is not None else None
                ),
                low_volume=low_volume,
                archived=lesson.archived_at is not None,
                published_at=lesson.published_at,
                critique_scores=critique_for_lesson,
                # Slice 6.13.5b populates these via thumbs_service.
                thumbs_aggregate=None,
                thumbs_count=0,
            )
        )
    # ASC NULLS LAST — non-NULL worst-first; NULL low-volume rows tail.
    rows.sort(
        key=lambda r: (
            r.smoothed_quality_score is None,
            r.smoothed_quality_score
            if r.smoothed_quality_score is not None
            else 1.0,
            r.lesson_id,
        )
    )
    return rows[:WORST_LESSONS_CAP]


def _build_quiz_item_rows(
    quiz_items_by_id: dict[str, QuizItem],
    quiz_item_stats: dict[str, dict],
    lessons_by_id: dict[str, Lesson],
    *,
    persisted_pass_rates: Optional[dict[str, float]] = None,
) -> list[QuizItemQualityRow]:
    """Worst-first quiz_items sorted by pass_rate ASC NULLS LAST.

    Capped at WORST_QUIZ_ITEMS_CAP. Quiz_items with zero reviews are
    excluded (no signal). Retired rows are excluded upstream at load
    time per D-8.
    """
    rows: list[QuizItemQualityRow] = []
    for qid, qi in quiz_items_by_id.items():
        stats = quiz_item_stats.get(qid, {})
        rc = stats.get("review_count", 0)
        if rc == 0:
            continue
        passes = stats["passes"]
        lapses = stats["lapses"]
        pass_rate = passes / rc
        lapse_rate = lapses / rc
        preview = qi.question[:QUESTION_PREVIEW_CHARS]
        lesson = lessons_by_id.get(qi.lesson_id)
        deck_id = lesson.deck_id if lesson is not None else ""
        rows.append(
            QuizItemQualityRow(
                quiz_item_id=qi.id,
                lesson_id=qi.lesson_id,
                deck_id=deck_id,
                question_preview=preview,
                review_count_window=rc,
                pass_rate=pass_rate,
                lapse_rate=lapse_rate,
                low_volume=rc < MIN_REVIEW_THRESHOLD,
                retired=qi.retired_at is not None,
                pass_rate_persisted=(persisted_pass_rates or {}).get(qi.id),
                # Slice 6.13.5b populates these via thumbs_service.
                thumbs_aggregate=None,
                thumbs_count=0,
            )
        )
    rows.sort(
        key=lambda r: (
            r.pass_rate is None,
            r.pass_rate if r.pass_rate is not None else 1.0,
            r.quiz_item_id,
        )
    )
    return rows[:WORST_QUIZ_ITEMS_CAP]
