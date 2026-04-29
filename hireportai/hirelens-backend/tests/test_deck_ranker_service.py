"""Service-layer tests for `deck_ranker_service` (Phase 6 slice 6.6).

Spec: docs/specs/phase-6/07-deck-lesson-ranker.md §10.1 + §11
AC-1..AC-15 + §12 D-1..D-16.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio

from app.models.deck import Deck
from app.models.lesson import Lesson
from app.models.quiz_item import QuizItem
from app.models.quiz_item_progress import QuizItemProgress
from app.models.subscription import Subscription
from app.models.tracker import TrackerApplicationModel
from app.models.user import User
from app.services import deck_ranker_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Seed helpers ─────────────────────────────────────────────────────────────


async def _seed_user(
    db_session,
    *,
    persona: str | None = "interview_prepper",
    plan: str = "free",
) -> User:
    user = User(
        google_id=f"g-{uuid.uuid4()}",
        email=f"{uuid.uuid4()}@ranker-svc-test.com",
        name="Ranker Svc Tester",
        persona=persona,
    )
    db_session.add(user)
    await db_session.flush()
    sub = Subscription(
        id=str(uuid.uuid4()),
        user_id=user.id,
        plan=plan,
        status="active",
    )
    db_session.add(sub)
    await db_session.flush()
    await db_session.refresh(user, attribute_names=["subscription"])
    return user


async def _seed_deck(
    db_session,
    *,
    slug: str | None = None,
    title: str = "Generic Deck",
    persona_visibility: str = "both",
    tier: str = "foundation",
    archived: bool = False,
    display_order: int = 0,
) -> Deck:
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=slug or f"deck-{uuid.uuid4().hex[:8]}",
        title=title,
        description="seeded for ranker tests",
        display_order=display_order,
        persona_visibility=persona_visibility,
        tier=tier,
        archived_at=datetime.now(timezone.utc) if archived else None,
    )
    db_session.add(deck)
    await db_session.flush()
    return deck


async def _seed_lesson(
    db_session,
    deck_id: str,
    *,
    quality_score: Decimal | None = None,
    published: bool = True,
) -> Lesson:
    lesson = Lesson(
        id=str(uuid.uuid4()),
        deck_id=deck_id,
        slug=f"lesson-{uuid.uuid4().hex[:6]}",
        title="Ranker Svc Lesson",
        concept_md="c",
        production_md="p",
        examples_md="e",
        display_order=0,
        version=1,
        version_type="initial",
        published_at=datetime.now(timezone.utc) if published else None,
        quality_score=quality_score,
    )
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def _seed_quiz_item(db_session, lesson_id: str) -> QuizItem:
    qi = QuizItem(
        id=str(uuid.uuid4()),
        lesson_id=lesson_id,
        question="Q?",
        answer="A.",
        question_type="free_text",
        difficulty="medium",
        display_order=0,
        version=1,
    )
    db_session.add(qi)
    await db_session.flush()
    return qi


async def _seed_progress(
    db_session,
    *,
    user_id: str,
    quiz_item_id: str,
    due_at: datetime,
) -> QuizItemProgress:
    progress = QuizItemProgress(
        id=str(uuid.uuid4()),
        user_id=user_id,
        quiz_item_id=quiz_item_id,
        state="review",
        due_date=due_at,
        reps=1,
    )
    db_session.add(progress)
    await db_session.flush()
    return progress


async def _seed_scan(
    db_session,
    *,
    user_id: str,
    skill_gaps: list[dict],
    created_offset_days: float = 0.0,
) -> TrackerApplicationModel:
    row = TrackerApplicationModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        company="Acme",
        role="Engineer",
        date_applied="2026-04-28",
        ats_score=70,
        status="Applied",
        scan_id=str(uuid.uuid4()),
        analysis_payload={"skill_gaps": skill_gaps},
    )
    db_session.add(row)
    await db_session.flush()
    if created_offset_days:
        row.created_at = datetime.now(timezone.utc) - timedelta(
            days=created_offset_days
        )
        await db_session.flush()
    return row


# ── 1. Cold start ────────────────────────────────────────────────────────────


async def test_rank_decks_cold_start_returns_display_order(db_session):
    user = await _seed_user(db_session, persona="interview_prepper")
    d1 = await _seed_deck(db_session, slug="alpha", title="Alpha", display_order=2)
    d2 = await _seed_deck(db_session, slug="beta", title="Beta", display_order=1)

    response = await deck_ranker_service.rank_decks_for_user(user, db_session)

    assert response.cold_start is True
    assert response.recent_gap_count == 0
    # display_order ASC tie-break: Beta (1) before Alpha (2).
    assert [r.deck.slug for r in response.decks] == ["beta", "alpha"]
    assert {d1.id, d2.id} == {r.deck.id for r in response.decks}


async def test_rank_decks_cold_start_response_shape_correct(db_session):
    user = await _seed_user(db_session, persona="interview_prepper")
    await _seed_deck(db_session)

    response = await deck_ranker_service.rank_decks_for_user(user, db_session)

    assert response.cold_start is True
    assert response.lookback_days == 30
    assert response.persona == "interview_prepper"
    assert response.lessons is None  # D-5: decks-only output in v1.


# ── 2. Gap-match scoring (D-7 + AC-8) ────────────────────────────────────────


async def test_rank_decks_with_recent_scan_promotes_matching_deck(db_session):
    user = await _seed_user(db_session, persona="interview_prepper")
    rag_deck = await _seed_deck(
        db_session, slug="llm-internals", title="LLM Internals — RAG", display_order=5
    )
    other_deck = await _seed_deck(
        db_session, slug="leadership", title="Leadership", display_order=1
    )

    await _seed_scan(
        db_session,
        user_id=user.id,
        skill_gaps=[
            {"skill": "RAG", "category": "Technical", "importance": "critical"},
        ],
    )

    response = await deck_ranker_service.rank_decks_for_user(user, db_session)

    assert response.cold_start is False
    # The RAG-matching deck must rank above the unrelated one even with
    # a worse display_order.
    slugs = [r.deck.slug for r in response.decks]
    assert slugs.index("llm-internals") < slugs.index("leadership")
    rag_entry = next(r for r in response.decks if r.deck.slug == "llm-internals")
    assert "RAG" in rag_entry.matched_gaps


async def test_rank_decks_critical_importance_outweighs_recommended(db_session):
    user = await _seed_user(db_session, persona="interview_prepper")
    critical_deck = await _seed_deck(
        db_session, slug="kubernetes", title="Kubernetes", display_order=0
    )
    recommended_deck = await _seed_deck(
        db_session, slug="terraform", title="Terraform", display_order=0
    )

    await _seed_scan(
        db_session,
        user_id=user.id,
        skill_gaps=[
            {"skill": "Kubernetes", "category": "Tool", "importance": "critical"},
            {"skill": "Terraform", "category": "Tool", "importance": "recommended"},
        ],
    )

    response = await deck_ranker_service.rank_decks_for_user(user, db_session)

    by_slug = {r.deck.slug: r for r in response.decks}
    assert by_slug["kubernetes"].score > by_slug["terraform"].score


# ── 3. Lifecycle filters (AC-4 / AC-5 / AC-6) ────────────────────────────────


async def test_rank_decks_filters_archived_deck(db_session):
    user = await _seed_user(db_session, persona="interview_prepper")
    await _seed_deck(db_session, slug="alive", title="Alive")
    await _seed_deck(db_session, slug="zombie", title="Zombie", archived=True)

    response = await deck_ranker_service.rank_decks_for_user(user, db_session)

    slugs = [r.deck.slug for r in response.decks]
    assert "zombie" not in slugs
    assert "alive" in slugs


async def test_rank_decks_filters_persona_narrowed_deck(db_session):
    user = await _seed_user(db_session, persona="interview_prepper")
    await _seed_deck(db_session, slug="prep", persona_visibility="interview_prepper")
    await _seed_deck(db_session, slug="climber-only", persona_visibility="climber")

    response = await deck_ranker_service.rank_decks_for_user(user, db_session)

    slugs = [r.deck.slug for r in response.decks]
    assert "climber-only" not in slugs
    assert "prep" in slugs


async def test_rank_decks_filters_premium_for_free_user(db_session):
    user = await _seed_user(db_session, persona="interview_prepper", plan="free")
    await _seed_deck(db_session, slug="foundation-deck", tier="foundation")
    await _seed_deck(db_session, slug="premium-deck", tier="premium")

    response = await deck_ranker_service.rank_decks_for_user(user, db_session)

    slugs = [r.deck.slug for r in response.decks]
    assert "premium-deck" not in slugs
    assert "foundation-deck" in slugs


async def test_rank_decks_pro_user_sees_premium_decks(db_session):
    user = await _seed_user(db_session, persona="interview_prepper", plan="pro")
    await _seed_deck(db_session, slug="premium-deck", tier="premium")
    await _seed_deck(db_session, slug="foundation-deck", tier="foundation")

    response = await deck_ranker_service.rank_decks_for_user(user, db_session)

    slugs = {r.deck.slug for r in response.decks}
    assert {"premium-deck", "foundation-deck"} == slugs


# ── 4. FSRS-due signal (AC-9) ────────────────────────────────────────────────


async def test_rank_decks_fsrs_due_score_pulls_engaged_deck_up(db_session):
    user = await _seed_user(db_session, persona="interview_prepper")
    engaged = await _seed_deck(db_session, slug="engaged", display_order=5)
    fresh = await _seed_deck(db_session, slug="fresh", display_order=5)

    engaged_lesson = await _seed_lesson(db_session, engaged.id)
    fresh_lesson = await _seed_lesson(db_session, fresh.id)
    engaged_qi = await _seed_quiz_item(db_session, engaged_lesson.id)
    await _seed_quiz_item(db_session, fresh_lesson.id)
    await _seed_progress(
        db_session,
        user_id=user.id,
        quiz_item_id=engaged_qi.id,
        due_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )

    response = await deck_ranker_service.rank_decks_for_user(user, db_session)

    by_slug = {r.deck.slug: r for r in response.decks}
    assert by_slug["engaged"].score_breakdown.fsrs_due == 1.0
    assert by_slug["fresh"].score_breakdown.fsrs_due == 0.0
    assert by_slug["engaged"].score > by_slug["fresh"].score


# ── 5. Quality null-coercion (D-2) ───────────────────────────────────────────


async def test_rank_decks_quality_score_null_coerced_to_neutral(db_session):
    user = await _seed_user(db_session, persona="interview_prepper")
    deck = await _seed_deck(db_session, slug="unscored")
    await _seed_lesson(db_session, deck.id, quality_score=None)

    response = await deck_ranker_service.rank_decks_for_user(user, db_session)

    by_slug = {r.deck.slug: r for r in response.decks}
    assert by_slug["unscored"].score_breakdown.avg_quality == 0.5


# ── 6. Output invariants (AC-10) ─────────────────────────────────────────────


async def test_rank_decks_zero_match_gap_does_not_filter(db_session):
    user = await _seed_user(db_session, persona="interview_prepper")
    await _seed_deck(db_session, slug="alpha")
    await _seed_deck(db_session, slug="beta")

    await _seed_scan(
        db_session,
        user_id=user.id,
        skill_gaps=[
            {"skill": "Nonexistent", "category": "Tool", "importance": "critical"},
        ],
    )

    response = await deck_ranker_service.rank_decks_for_user(user, db_session)

    # No deck matches; response keeps the full set.
    assert {r.deck.slug for r in response.decks} == {"alpha", "beta"}
    for r in response.decks:
        assert r.score_breakdown.gap_match == 0.0


async def test_rank_decks_score_in_zero_to_one_range(db_session):
    user = await _seed_user(db_session, persona="interview_prepper", plan="pro")
    for slug in ("a", "b", "c"):
        await _seed_deck(db_session, slug=slug)
    await _seed_scan(
        db_session,
        user_id=user.id,
        skill_gaps=[
            {"skill": "X", "category": "Tool", "importance": "critical"},
        ],
    )

    response = await deck_ranker_service.rank_decks_for_user(user, db_session)

    for r in response.decks:
        assert 0.0 <= r.score <= 1.0
        assert 0.0 <= r.score_breakdown.gap_match <= 1.0
        assert 0.0 <= r.score_breakdown.fsrs_due <= 1.0
        assert 0.0 <= r.score_breakdown.avg_quality <= 1.0


async def test_rank_decks_stable_tiebreak_by_display_order(db_session):
    user = await _seed_user(db_session, persona="interview_prepper")
    await _seed_deck(db_session, slug="third", display_order=3)
    await _seed_deck(db_session, slug="first", display_order=1)
    await _seed_deck(db_session, slug="second", display_order=2)

    response = await deck_ranker_service.rank_decks_for_user(user, db_session)

    # Cold-start: gap=0 across all; scores tie on gap; sort falls to
    # display_order ASC.
    slugs = [r.deck.slug for r in response.decks]
    assert slugs == ["first", "second", "third"]
    assert [r.rank for r in response.decks] == [1, 2, 3]


# ── 7. Persona null fallback ─────────────────────────────────────────────────


async def test_rank_decks_persona_null_user_falls_back_to_both_only(db_session):
    user = await _seed_user(db_session, persona=None)
    await _seed_deck(db_session, slug="generic", persona_visibility="both")
    await _seed_deck(db_session, slug="climber-only", persona_visibility="climber")
    await _seed_deck(db_session, slug="prep-only", persona_visibility="interview_prepper")

    response = await deck_ranker_service.rank_decks_for_user(user, db_session)

    slugs = {r.deck.slug for r in response.decks}
    assert slugs == {"generic"}


# ── 8. `get_recent_skill_gaps` invariants (AC-11 + D-16) ─────────────────────


async def test_get_recent_skill_gaps_dedupes_across_scans(db_session):
    user = await _seed_user(db_session, persona="interview_prepper")
    await _seed_scan(
        db_session,
        user_id=user.id,
        skill_gaps=[
            {"skill": "Kubernetes", "category": "Tool", "importance": "recommended"},
        ],
    )
    await _seed_scan(
        db_session,
        user_id=user.id,
        skill_gaps=[
            {"skill": "Kubernetes", "category": "Tool", "importance": "recommended"},
        ],
    )

    gaps = await deck_ranker_service.get_recent_skill_gaps(user.id, db_session)

    assert len(gaps) == 1
    assert gaps[0].skill == "Kubernetes"


async def test_get_recent_skill_gaps_promotes_highest_importance(db_session):
    user = await _seed_user(db_session, persona="interview_prepper")
    await _seed_scan(
        db_session,
        user_id=user.id,
        skill_gaps=[
            {"skill": "RAG", "category": "Technical", "importance": "recommended"},
        ],
    )
    await _seed_scan(
        db_session,
        user_id=user.id,
        skill_gaps=[
            {"skill": "RAG", "category": "Technical", "importance": "critical"},
        ],
    )

    gaps = await deck_ranker_service.get_recent_skill_gaps(user.id, db_session)

    assert len(gaps) == 1
    assert gaps[0].importance == "critical"


async def test_get_recent_skill_gaps_skips_malformed_payload(db_session, caplog):
    user = await _seed_user(db_session, persona="interview_prepper")
    # Good row.
    await _seed_scan(
        db_session,
        user_id=user.id,
        skill_gaps=[
            {"skill": "Docker", "category": "Tool", "importance": "critical"},
        ],
    )
    # Malformed payload — `skill_gaps` not a list.
    bad_row = TrackerApplicationModel(
        id=str(uuid.uuid4()),
        user_id=user.id,
        company="Bad",
        role="Bad",
        date_applied="2026-04-28",
        ats_score=0,
        status="Applied",
        scan_id=str(uuid.uuid4()),
        analysis_payload={"skill_gaps": "not-a-list"},
    )
    db_session.add(bad_row)
    await db_session.flush()

    with caplog.at_level("WARNING"):
        gaps = await deck_ranker_service.get_recent_skill_gaps(user.id, db_session)

    # Helper continued past the bad row and surfaced the good one.
    assert {g.skill for g in gaps} == {"Docker"}
    assert any(
        "recent_skill_gaps_skip" in record.message for record in caplog.records
    )
