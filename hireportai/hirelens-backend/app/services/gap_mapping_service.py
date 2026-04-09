"""ATS gap → card category mapping service.

Closes the onboarding loop described in .agent/skills/ats-card-bridge.md:
an ATS scan produces skill gaps (e.g. ["RAG", "Kubernetes"]), and we need
to tell the user which study categories will teach those gaps.

Two-tier strategy
-----------------
1. **Tag join (primary, deterministic).** For each gap, find cards whose
   `tags` JSON array contains a case-insensitive match for the gap string,
   then aggregate by category. Tie-break by `categories.display_order`.

2. **pgvector similarity (fallback).** If the tag join returns nothing and
   the caller allows it, embed the gap string and run a cosine-similarity
   search against `cards.embedding`. Group the top-K nearest cards by
   category and return the strongest group.

If both tiers produce nothing, the gap is returned with
`match_type="none"` and an empty category list — it is never dropped,
so the frontend can still render a "no cards yet" state.
"""
from __future__ import annotations

from typing import Awaitable, Callable, Literal, Optional

from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.category import Category


# ── Response schemas ─────────────────────────────────────────────────────────


class RecommendedCategory(BaseModel):
    """A study category recommended for a specific ATS gap."""

    category_id: str
    name: str
    icon: str
    color: str
    matched_card_count: int
    similarity_score: Optional[float] = None


class GapMapping(BaseModel):
    """A single gap and the categories that teach it."""

    gap: str  # original user-facing string, not normalized
    match_type: Literal["tag", "semantic", "none"]
    matching_categories: list[RecommendedCategory]


# ── Embedding callable type ──────────────────────────────────────────────────

EmbedFn = Callable[[str], Awaitable[list[float]]]


async def _default_embed_fn(query: str) -> list[float]:
    """Default embedder — reuses the Gemini caller from card_service.

    Imported lazily so unit tests that seed zero embeddings never touch
    the Gemini client.
    """
    from app.services.card_service import _embed_query

    return await _embed_query(query)


# ── Tier 1: tag join ─────────────────────────────────────────────────────────


_TAG_JOIN_SQL = text(
    """
    SELECT
        c.category_id            AS category_id,
        cat.name                 AS name,
        cat.icon                 AS icon,
        cat.color                AS color,
        cat.display_order        AS display_order,
        COUNT(*)                 AS match_count
    FROM cards c
    JOIN categories cat ON cat.id = c.category_id
    CROSS JOIN LATERAL jsonb_array_elements_text(
        CASE
            WHEN jsonb_typeof(c.tags::jsonb) = 'array' THEN c.tags::jsonb
            ELSE '[]'::jsonb
        END
    ) AS tag
    WHERE LOWER(tag) = :gap
    GROUP BY c.category_id, cat.name, cat.icon, cat.color, cat.display_order
    ORDER BY match_count DESC, cat.display_order ASC
    LIMIT :lim
    """
)


async def _match_by_tags(
    gap_lower: str,
    db: AsyncSession,
    limit: int,
) -> list[RecommendedCategory]:
    rows = (
        await db.execute(_TAG_JOIN_SQL, {"gap": gap_lower, "lim": limit})
    ).all()
    return [
        RecommendedCategory(
            category_id=row.category_id,
            name=row.name,
            icon=row.icon,
            color=row.color,
            matched_card_count=int(row.match_count),
            similarity_score=None,
        )
        for row in rows
    ]


# ── Tier 2: pgvector semantic similarity ─────────────────────────────────────


async def _match_by_embedding(
    gap: str,
    db: AsyncSession,
    limit: int,
    embed_fn: EmbedFn,
    top_k_cards: int = 20,
) -> list[RecommendedCategory]:
    # Skip the embedding call entirely if there are no embeddings to
    # search against. Keeps tests self-contained (no Gemini key needed).
    embedded_count = (
        await db.execute(
            select(func.count(Card.id)).where(Card.embedding.is_not(None))
        )
    ).scalar_one()
    if embedded_count == 0:
        return []

    try:
        query_vec = await embed_fn(gap)
    except Exception:
        # Embedding service failure → degrade gracefully to "none".
        return []

    stmt = (
        select(
            Card.category_id.label("category_id"),
            Category.name.label("name"),
            Category.icon.label("icon"),
            Category.color.label("color"),
            Category.display_order.label("display_order"),
            (1 - Card.embedding.cosine_distance(query_vec)).label("score"),
        )
        .join(Category, Category.id == Card.category_id)
        .where(Card.embedding.is_not(None))
        .order_by(Card.embedding.cosine_distance(query_vec))
        .limit(top_k_cards)
    )
    rows = (await db.execute(stmt)).all()

    # Group top-K cards by category; keep each group's best similarity.
    by_cat: dict[str, dict] = {}
    for row in rows:
        cid = row.category_id
        score = float(row.score)
        if cid not in by_cat:
            by_cat[cid] = {
                "category_id": cid,
                "name": row.name,
                "icon": row.icon,
                "color": row.color,
                "display_order": row.display_order,
                "count": 0,
                "score": score,
            }
        by_cat[cid]["count"] += 1
        if score > by_cat[cid]["score"]:
            by_cat[cid]["score"] = score

    sorted_cats = sorted(
        by_cat.values(),
        key=lambda c: (-c["score"], c["display_order"]),
    )[:limit]

    return [
        RecommendedCategory(
            category_id=c["category_id"],
            name=c["name"],
            icon=c["icon"],
            color=c["color"],
            matched_card_count=c["count"],
            similarity_score=round(c["score"], 4),
        )
        for c in sorted_cats
    ]


# ── Public API ───────────────────────────────────────────────────────────────


async def map_gaps_to_categories(
    gaps: list[str],
    db: AsyncSession,
    *,
    use_semantic: bool = True,
    max_categories_per_gap: int = 3,
    embed_fn: Optional[EmbedFn] = None,
) -> list[GapMapping]:
    """Map a list of ATS skill gaps to recommended study categories.

    Order of the returned list mirrors the input `gaps` order so the
    frontend can render recommendations inline with the scan output.

    Parameters
    ----------
    gaps:
        Raw gap strings straight from the ATS scanner.
    db:
        Async SQLAlchemy session.
    use_semantic:
        When True (default), fall back to pgvector similarity for gaps
        that have zero tag matches.
    max_categories_per_gap:
        Maximum number of categories returned per gap (default 3).
    embed_fn:
        Optional embedder override; defaults to the Gemini embedder
        used by card_service. Tests can inject a stub to avoid
        network calls.
    """
    if embed_fn is None:
        embed_fn = _default_embed_fn

    results: list[GapMapping] = []

    for raw_gap in gaps:
        normalized = raw_gap.strip().lower()
        if not normalized:
            results.append(
                GapMapping(
                    gap=raw_gap,
                    match_type="none",
                    matching_categories=[],
                )
            )
            continue

        # Tier 1 — tag join
        tag_matches = await _match_by_tags(
            normalized, db, limit=max_categories_per_gap
        )
        if tag_matches:
            results.append(
                GapMapping(
                    gap=raw_gap,
                    match_type="tag",
                    matching_categories=tag_matches,
                )
            )
            continue

        # Tier 2 — semantic fallback
        if use_semantic:
            semantic_matches = await _match_by_embedding(
                raw_gap, db, limit=max_categories_per_gap, embed_fn=embed_fn
            )
            if semantic_matches:
                results.append(
                    GapMapping(
                        gap=raw_gap,
                        match_type="semantic",
                        matching_categories=semantic_matches,
                    )
                )
                continue

        # Neither tier matched — keep the gap in the response with no recs.
        results.append(
            GapMapping(
                gap=raw_gap,
                match_type="none",
                matching_categories=[],
            )
        )

    return results
