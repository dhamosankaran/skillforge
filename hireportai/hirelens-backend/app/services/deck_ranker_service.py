"""Lens-ranked deck ordering service — Phase 6 slice 6.6.

Spec: docs/specs/phase-6/07-deck-lesson-ranker.md §4 + §6 + §12
D-1..D-16.

Public API:
  - ``rank_decks_for_user(user, db, *, lookback_days, max_scans)``
  - ``get_recent_skill_gaps(user_id, db, *, lookback_days, max_scans)``

Heuristic v1 (D-1): weighted sum of four signals per deck,

    score(deck) = 0.55 * gap_match
                + 0.25 * fsrs_due
                + 0.10 * avg_quality
                + 0.10 * (1 / display_order_rank)

over the user's persona / tier / archive-visible deck set. Cold-start
safe: when no recent scan has ``analysis_payload``, ``cold_start=True``
and decks fall back to ``display_order ASC``. Zero analytics events
(D-11), no caching (D-12), no migration (D-13). Partial failure on the
recent-skill-gaps helper = skip + WARNING log (D-16); a single deck
whose sub-score query errors gets skipped + logged so the rest of the
response still ships.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.models.quiz_item_progress import QuizItemProgress
from app.models.tracker import TrackerApplicationModel
from app.models.user import User
from app.schemas.deck import DeckResponse
from app.schemas.ranker import (
    RankedDeck,
    RankedDecksResponse,
    ScoreBreakdown,
)
from app.schemas.responses import SkillGap
from app.services.curriculum_visibility import (
    _allowed_tiers_for_user,
    _visible_persona_set,
)

logger = logging.getLogger(__name__)


# ── Scoring weights (D-1, locked) ────────────────────────────────────────────
W_GAP = 0.55
W_FSRS = 0.25
W_QUAL = 0.10
W_ORDER = 0.10

# ── Importance weights (D-7) ────────────────────────────────────────────────
_IMPORTANCE_WEIGHTS: dict[str, float] = {
    "critical": 1.0,
    "recommended": 0.5,
    "nice-to-have": 0.25,
}
_IMPORTANCE_RANK: dict[str, int] = {
    "critical": 3,
    "recommended": 2,
    "nice-to-have": 1,
}

# ── Defaults (D-14) ──────────────────────────────────────────────────────────
DEFAULT_LOOKBACK_DAYS = 30
DEFAULT_MAX_SCANS = 5

# ── Quality null-coercion (D-2) ──────────────────────────────────────────────
_NEUTRAL_QUALITY = 0.5


# ── Public helpers ───────────────────────────────────────────────────────────


async def get_recent_skill_gaps(
    user_id: str,
    db: AsyncSession,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    max_scans: int = DEFAULT_MAX_SCANS,
) -> list[SkillGap]:
    """Aggregated read of recent ATS scan ``skill_gaps``.

    Spec §4.5 + §12 D-13. Reads the user's most recent
    ``tracker_applications_v2`` rows with non-null ``analysis_payload``
    (deferred per spec #59 §6 — ``undefer(...)`` is required), unmarshals
    each row's ``skill_gaps`` array, dedupes by ``(skill.lower(),
    importance)`` keeping the highest-importance copy, and returns the
    union ordered by importance DESC then alphabetical skill ASC for
    stable test assertions.

    Malformed rows are logged at WARNING and skipped (D-16).
    """
    # `tracker_applications_v2.created_at` is TIMESTAMP WITHOUT TIME ZONE
    # (spec #57 / #59 schema); asyncpg refuses to compare tz-aware
    # parameters against a naive column. Strip tzinfo for the cutoff.
    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).replace(
        tzinfo=None
    )
    stmt = (
        select(TrackerApplicationModel)
        .options(undefer(TrackerApplicationModel.analysis_payload))
        .where(TrackerApplicationModel.user_id == user_id)
        .where(TrackerApplicationModel.created_at >= cutoff)
        .where(TrackerApplicationModel.analysis_payload.is_not(None))
        .order_by(TrackerApplicationModel.created_at.desc())
        .limit(max_scans)
    )
    rows = (await db.execute(stmt)).scalars().all()

    # Dedupe by skill.lower() keeping the highest-importance variant.
    best_by_skill: dict[str, SkillGap] = {}
    for row in rows:
        payload = row.analysis_payload
        if not isinstance(payload, dict):
            logger.warning(
                "recent_skill_gaps_skip_malformed payload tracker_application_id=%s",
                row.id,
            )
            continue
        gaps = payload.get("skill_gaps")
        if not isinstance(gaps, list):
            logger.warning(
                "recent_skill_gaps_skip_missing_gaps tracker_application_id=%s",
                row.id,
            )
            continue
        for raw in gaps:
            if not isinstance(raw, dict):
                continue
            try:
                gap = SkillGap.model_validate(raw)
            except Exception:
                logger.warning(
                    "recent_skill_gaps_invalid_gap tracker_application_id=%s",
                    row.id,
                )
                continue
            key = gap.skill.lower()
            existing = best_by_skill.get(key)
            if existing is None:
                best_by_skill[key] = gap
                continue
            if _IMPORTANCE_RANK.get(gap.importance, 0) > _IMPORTANCE_RANK.get(
                existing.importance, 0
            ):
                best_by_skill[key] = gap

    deduped = list(best_by_skill.values())
    deduped.sort(
        key=lambda g: (
            -_IMPORTANCE_RANK.get(g.importance, 0),
            g.skill.lower(),
        )
    )
    return deduped


async def rank_decks_for_user(
    user: User,
    db: AsyncSession,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    max_scans: int = DEFAULT_MAX_SCANS,
) -> RankedDecksResponse:
    """Rank persona/tier-visible decks for ``user`` by Lens signals.

    Cold-start safe — see spec §4.4.
    """
    ranked_at = datetime.now(timezone.utc)

    visible_decks = await _list_visible_decks(db, user=user)

    recent_gaps = await get_recent_skill_gaps(
        user.id,
        db,
        lookback_days=lookback_days,
        max_scans=max_scans,
    )
    cold_start = len(recent_gaps) == 0

    # Pre-compute display-order rank within the visible set so ties
    # collapse to the curator's intended order.
    sorted_by_display = sorted(visible_decks, key=lambda d: (d.display_order, d.id))
    display_rank: dict[str, int] = {
        deck.id: idx + 1 for idx, deck in enumerate(sorted_by_display)
    }

    ranked: list[RankedDeck] = []
    for deck in visible_decks:
        try:
            gap_score, matched = _gap_match_score(deck, recent_gaps)
            fsrs_score = await _fsrs_due_score(deck.id, user.id, db)
            quality_score = await _avg_quality_score(deck.id, db)
            rank = display_rank.get(deck.id, len(visible_decks))
            display_score = 1.0 / rank
            composite = (
                W_GAP * gap_score
                + W_FSRS * fsrs_score
                + W_QUAL * quality_score
                + W_ORDER * display_score
            )
        except Exception:
            logger.warning(
                "rank_decks_skip_deck_on_error deck_id=%s", deck.id, exc_info=True
            )
            continue

        ranked.append(
            RankedDeck(
                deck=DeckResponse.model_validate(deck),
                score=round(composite, 4),
                rank=0,  # filled after the global sort below.
                matched_gaps=matched,
                score_breakdown=ScoreBreakdown(
                    gap_match=round(gap_score, 4),
                    fsrs_due=round(fsrs_score, 4),
                    avg_quality=round(quality_score, 4),
                    display_order_rank=round(display_score, 4),
                ),
            )
        )

    # Sort by score DESC, tie-break by display_order ASC.
    deck_by_id = {d.id: d for d in visible_decks}
    ranked.sort(
        key=lambda r: (
            -r.score,
            deck_by_id[r.deck.id].display_order,
            deck_by_id[r.deck.id].id,
        )
    )
    for idx, item in enumerate(ranked):
        item.rank = idx + 1

    return RankedDecksResponse(
        user_id=user.id,
        persona=user.persona,
        cold_start=cold_start,
        lookback_days=lookback_days,
        recent_gap_count=len(recent_gaps),
        ranked_at=ranked_at,
        decks=ranked,
    )


# ── Private helpers ──────────────────────────────────────────────────────────


async def _list_visible_decks(
    db: AsyncSession,
    *,
    user: User,
) -> list[Deck]:
    """Persona/tier/archive-visible deck set for ``user``.

    Imports filter helpers from ``curriculum_visibility`` per slice 6.6
    §12 D-6 (slice 6.5 D-5 escape-hatch fired here). No public ``list
    visible decks`` exists on ``lesson_service`` today, so the ranker
    issues its own SELECT.
    """
    visible_personas = _visible_persona_set(user)
    allowed_tiers = _allowed_tiers_for_user(user)
    stmt = (
        select(Deck)
        .where(Deck.archived_at.is_(None))
        .where(Deck.persona_visibility.in_(visible_personas))
        .where(Deck.tier.in_(allowed_tiers))
    )
    return list((await db.execute(stmt)).scalars().all())


def _gap_match_score(
    deck: Deck,
    recent_gaps: list[SkillGap],
) -> tuple[float, list[str]]:
    """Per §4.2 + §12 D-7: case-insensitive substring match against
    ``deck.slug.replace('-', ' ') + deck.title``.

    Returns ``(score, matched_skill_strings)``. ``score`` is the
    importance-weighted sum normalised by the count of considered gaps,
    bounded to ``[0, 1]``. Empty input → ``(0.0, [])``.
    """
    if not recent_gaps:
        return 0.0, []
    haystack = f"{deck.slug.replace('-', ' ')} {deck.title}".lower()
    matched: list[str] = []
    weighted_sum = 0.0
    for gap in recent_gaps:
        skill_lc = gap.skill.lower()
        if skill_lc and skill_lc in haystack:
            matched.append(gap.skill)
            weighted_sum += _IMPORTANCE_WEIGHTS.get(gap.importance, 0.0)
    if not matched:
        return 0.0, []
    score = weighted_sum / len(recent_gaps)
    return min(1.0, max(0.0, score)), matched


async def _fsrs_due_score(
    deck_id: str,
    user_id: str,
    db: AsyncSession,
) -> float:
    """Per §4.2 + §12 D-3: linear ``min(due_count, total_quiz_items) /
    total_quiz_items`` over the deck's active quiz_items + the user's
    progress rows. Empty-deck floor 0.
    """
    now = datetime.now(timezone.utc)
    total_stmt = (
        select(func.count(QuizItem.id))
        .join(Lesson, Lesson.id == QuizItem.lesson_id)
        .where(Lesson.deck_id == deck_id)
        .where(QuizItem.retired_at.is_(None))
        .where(Lesson.archived_at.is_(None))
        .where(Lesson.published_at.is_not(None))
    )
    total = (await db.execute(total_stmt)).scalar_one() or 0
    if total == 0:
        return 0.0
    due_stmt = (
        select(func.count(QuizItemProgress.id))
        .join(QuizItem, QuizItem.id == QuizItemProgress.quiz_item_id)
        .join(Lesson, Lesson.id == QuizItem.lesson_id)
        .where(Lesson.deck_id == deck_id)
        .where(QuizItemProgress.user_id == user_id)
        .where(QuizItemProgress.due_date <= now)
        .where(QuizItem.retired_at.is_(None))
        .where(Lesson.archived_at.is_(None))
        .where(Lesson.published_at.is_not(None))
    )
    due = (await db.execute(due_stmt)).scalar_one() or 0
    return min(due, total) / total


async def _avg_quality_score(deck_id: str, db: AsyncSession) -> float:
    """Per §4.2 + §12 D-2: mean of ``lessons.quality_score`` across
    published, non-archived lessons. Null-coerced to 0.5 when zero
    lessons have a score.
    """
    stmt = (
        select(func.avg(Lesson.quality_score))
        .where(Lesson.deck_id == deck_id)
        .where(Lesson.archived_at.is_(None))
        .where(Lesson.published_at.is_not(None))
        .where(Lesson.quality_score.is_not(None))
    )
    avg = (await db.execute(stmt)).scalar_one_or_none()
    if avg is None:
        return _NEUTRAL_QUALITY
    return float(avg)
