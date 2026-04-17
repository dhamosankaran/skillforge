"""CI-safe unit tests for the card extraction + embedding helpers.

No DB, no network — these run in the default `-m "not integration"` CI subset.
They pin two invariants that downstream idempotency and vector-search rely on:

  1. `cat_uuid` / `card_uuid` are deterministic (ON CONFLICT idempotency).
  2. `_synthetic_embedding` returns a stable 1536-dim vector (cosine queries
     still work without a live Gemini API key).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.extract_cards import cat_uuid, card_uuid  # noqa: E402
from scripts.generate_embeddings import (  # noqa: E402
    EMBEDDING_DIMS,
    _synthetic_embedding,
)


# ── UUID5 determinism ──────────────────────────────────────────────────────

def test_cat_uuid_is_deterministic() -> None:
    assert cat_uuid("System Design") == cat_uuid("System Design")


def test_card_uuid_is_deterministic() -> None:
    assert card_uuid("System Design", "What is a load balancer?") == card_uuid(
        "System Design", "What is a load balancer?"
    )


def test_cat_uuid_differs_for_different_names() -> None:
    assert cat_uuid("System Design") != cat_uuid("Behavioral")


def test_card_uuid_differs_across_categories_or_questions() -> None:
    a = card_uuid("System Design", "What is a load balancer?")
    b = card_uuid("Behavioral", "What is a load balancer?")
    c = card_uuid("System Design", "What is caching?")
    assert len({a, b, c}) == 3


def test_cat_and_card_namespaces_do_not_collide() -> None:
    # Same human input passed through either helper must yield different IDs,
    # otherwise a category and a card could clash on ON CONFLICT (id).
    assert cat_uuid("Foo") != card_uuid("Foo", "Foo")


# ── Synthetic embedding ────────────────────────────────────────────────────

def test_synthetic_embedding_has_expected_dimensionality() -> None:
    vec = _synthetic_embedding("hello world")
    assert len(vec) == EMBEDDING_DIMS == 1536


def test_synthetic_embedding_is_deterministic() -> None:
    a = _synthetic_embedding("same input")
    b = _synthetic_embedding("same input")
    assert a == pytest.approx(b)


def test_synthetic_embedding_differs_for_different_inputs() -> None:
    a = _synthetic_embedding("alpha")
    b = _synthetic_embedding("beta")
    # Deterministic-but-distinct; at least one component must differ.
    assert any(x != y for x, y in zip(a, b))


def test_synthetic_embedding_has_non_zero_magnitude() -> None:
    vec = _synthetic_embedding("magnitude check")
    magnitude = sum(v * v for v in vec) ** 0.5
    # Guard against degenerate all-zeros vectors, which would make cosine
    # distance undefined.  Assert only non-zero — downstream code should not
    # rely on a specific normalization contract that isn't pinned here.
    assert magnitude > 0.0
