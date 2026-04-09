"""Unit tests for app.services.gap_mapping_service.

These tests exercise the service against a real Postgres session
(pgvector is already enabled by the conftest engine fixture). They
intentionally do NOT seed any `cards.embedding` values, so the
semantic fallback short-circuits on its `embedded_count == 0` check
without ever calling the Gemini embedder — no API key needed.
"""
from __future__ import annotations

import uuid

import pytest

from app.models.card import Card
from app.models.category import Category
from app.services.gap_mapping_service import map_gaps_to_categories

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── Seed helpers ─────────────────────────────────────────────────────────────


async def _seed_category(
    db_session,
    *,
    name_prefix: str = "Cat",
    display_order: int = 10,
) -> Category:
    cat = Category(
        id=str(uuid.uuid4()),
        name=f"{name_prefix}-{uuid.uuid4().hex[:6]}",
        icon="📚",
        color="from-blue-500 to-indigo-600",
        display_order=display_order,
        source="foundation",
    )
    db_session.add(cat)
    await db_session.flush()
    return cat


async def _seed_card(
    db_session,
    category_id: str,
    tags: list[str],
) -> Card:
    card = Card(
        id=str(uuid.uuid4()),
        category_id=category_id,
        question=f"Q-{uuid.uuid4().hex[:6]}?",
        answer="Seed answer.",
        difficulty="medium",
        tags=tags,
    )
    db_session.add(card)
    await db_session.flush()
    return card


# ── Tests ────────────────────────────────────────────────────────────────────


async def test_rag_gap_maps_to_rag_category(db_session):
    """A gap that exactly matches a card tag resolves via the tag-join tier."""
    rag_cat = await _seed_category(db_session, name_prefix="LLMEng", display_order=1)
    other_cat = await _seed_category(db_session, name_prefix="Other", display_order=2)

    # Three RAG cards in the LLM category
    for _ in range(3):
        await _seed_card(db_session, rag_cat.id, tags=["RAG", "vector-search"])
    # One unrelated card in another category
    await _seed_card(db_session, other_cat.id, tags=["unrelated"])

    results = await map_gaps_to_categories(["RAG"], db_session)

    assert len(results) == 1
    gm = results[0]
    assert gm.gap == "RAG"
    assert gm.match_type == "tag"
    assert len(gm.matching_categories) == 1

    match = gm.matching_categories[0]
    assert match.category_id == rag_cat.id
    assert match.matched_card_count == 3
    assert match.similarity_score is None


async def test_unknown_gap_returns_empty_or_fallback(db_session):
    """A gap with no tag match and no embeddings falls through to match_type='none'."""
    cat = await _seed_category(db_session, name_prefix="Only")
    await _seed_card(db_session, cat.id, tags=["docker", "containers"])

    # No card has a "Quantum Cryptography" tag and no card has an embedding,
    # so the semantic tier short-circuits to []. Expected: match_type='none'.
    results = await map_gaps_to_categories(
        ["Quantum Cryptography"], db_session
    )

    assert len(results) == 1
    gm = results[0]
    assert gm.gap == "Quantum Cryptography"
    assert gm.match_type == "none"
    assert gm.matching_categories == []


async def test_multiple_gaps_return_multiple_categories(db_session):
    """Each input gap produces its own entry in the same order."""
    docker_cat = await _seed_category(
        db_session, name_prefix="DevOps", display_order=5
    )
    k8s_cat = await _seed_category(
        db_session, name_prefix="Orchestration", display_order=6
    )

    await _seed_card(db_session, docker_cat.id, tags=["Docker"])
    await _seed_card(db_session, docker_cat.id, tags=["Docker", "ci"])
    await _seed_card(db_session, k8s_cat.id, tags=["Kubernetes"])

    # Normalization should also kick in: " kubernetes " → matches "Kubernetes".
    results = await map_gaps_to_categories(
        ["Docker", " kubernetes "], db_session
    )

    assert len(results) == 2

    # Order preserved — index 0 is Docker, index 1 is Kubernetes.
    docker_result = results[0]
    assert docker_result.gap == "Docker"
    assert docker_result.match_type == "tag"
    assert len(docker_result.matching_categories) == 1
    assert docker_result.matching_categories[0].category_id == docker_cat.id
    assert docker_result.matching_categories[0].matched_card_count == 2

    k8s_result = results[1]
    assert k8s_result.gap == " kubernetes "  # original echoed, not normalized
    assert k8s_result.match_type == "tag"
    assert len(k8s_result.matching_categories) == 1
    assert k8s_result.matching_categories[0].category_id == k8s_cat.id
    assert k8s_result.matching_categories[0].matched_card_count == 1
