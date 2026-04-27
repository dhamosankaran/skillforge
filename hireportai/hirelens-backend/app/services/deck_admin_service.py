"""Admin authoring service for `decks` (slice 6.4b — B-065).

Spec: docs/specs/phase-6/04-admin-authoring.md §4.1.1 + §5.1-§5.4 + §9.

Synchronous CRUD + archive + admin-LIST. Persona-narrowing detection on
update emits the `admin_deck_persona_narrowed` event per §9 + D-19; the
FE owns the warning modal copy (service layer only persists).
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics import track as analytics_track
from app.models.deck import Deck
from app.schemas.deck import (
    AdminDeckStatusFilter,
    DeckCreateRequest,
    DeckResponse,
    DeckUpdateRequest,
)
from app.services.admin_errors import DeckNotFoundError, DeckSlugConflictError

# Personas that the FE persona-visibility narrowing detector compares against.
_PERSONA_EXPANSION = {
    "both": ("climber", "interview_prepper"),
    "climber": ("climber",),
    "interview_prepper": ("interview_prepper",),
}


def _persona_set(value: str) -> set[str]:
    return set(_PERSONA_EXPANSION.get(value, ()))


async def _fetch_deck(deck_id: str, db: AsyncSession) -> Deck:
    result = await db.execute(select(Deck).where(Deck.id == deck_id))
    deck = result.scalar_one_or_none()
    if deck is None:
        raise DeckNotFoundError(deck_id)
    return deck


async def create_deck(
    payload: DeckCreateRequest, db: AsyncSession, admin_id: str
) -> DeckResponse:
    """Create a deck. 409 on slug collision."""
    deck = Deck(
        id=str(uuid.uuid4()),
        slug=payload.slug,
        title=payload.title,
        description=payload.description,
        display_order=payload.display_order,
        icon=payload.icon,
        persona_visibility=payload.persona_visibility,
        tier=payload.tier,
    )
    db.add(deck)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise DeckSlugConflictError(payload.slug) from exc
    await db.refresh(deck)

    analytics_track(
        admin_id,
        "admin_deck_created",
        {
            "admin_id": admin_id,
            "deck_id": deck.id,
            "slug": deck.slug,
            "persona_visibility": deck.persona_visibility,
            "tier": deck.tier,
            "internal": True,
        },
    )
    return DeckResponse.model_validate(deck)


async def update_deck(
    deck_id: str,
    payload: DeckUpdateRequest,
    db: AsyncSession,
    admin_id: str,
) -> DeckResponse:
    """Patch a deck. PATCH semantic — only fields present mutate.

    Emits `admin_deck_persona_narrowed` when `persona_visibility` shifts
    to a strictly smaller persona set per D-19.
    """
    deck = await _fetch_deck(deck_id, db)

    fields_changed: list[str] = []
    persona_narrowed: Optional[tuple[set[str], set[str]]] = None

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field == "persona_visibility" and value is not None:
            before = _persona_set(deck.persona_visibility)
            after = _persona_set(value)
            if after < before:
                persona_narrowed = (before, after)
            if value != deck.persona_visibility:
                deck.persona_visibility = value
                fields_changed.append(field)
            continue
        if getattr(deck, field) != value:
            setattr(deck, field, value)
            fields_changed.append(field)

    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise DeckSlugConflictError(payload.slug or deck.slug) from exc
    await db.refresh(deck)

    analytics_track(
        admin_id,
        "admin_deck_updated",
        {
            "admin_id": admin_id,
            "deck_id": deck.id,
            "fields_changed": fields_changed,
            "persona_visibility_narrowed": persona_narrowed is not None,
            "internal": True,
        },
    )
    if persona_narrowed is not None:
        before, after = persona_narrowed
        analytics_track(
            admin_id,
            "admin_deck_persona_narrowed",
            {
                "admin_id": admin_id,
                "deck_id": deck.id,
                "removed_personas": sorted(before - after),
                "before_count": len(before),
                "after_count": len(after),
                "internal": True,
            },
        )
    return DeckResponse.model_validate(deck)


async def archive_deck(
    deck_id: str, db: AsyncSession, admin_id: str
) -> DeckResponse:
    """Set `archived_at = now()`. Idempotent — re-archive emits no event."""
    deck = await _fetch_deck(deck_id, db)
    was_active = deck.archived_at is None
    if was_active:
        deck.archived_at = func.now()
        await db.flush()
        await db.refresh(deck)
        analytics_track(
            admin_id,
            "admin_deck_archived",
            {
                "admin_id": admin_id,
                "deck_id": deck.id,
                "slug": deck.slug,
                "internal": True,
            },
        )
    return DeckResponse.model_validate(deck)


async def list_admin_decks(
    db: AsyncSession,
    status_filter: AdminDeckStatusFilter = "active",
) -> list[DeckResponse]:
    """List decks with status filter (D-16)."""
    stmt = select(Deck).order_by(Deck.display_order.asc(), Deck.created_at.asc())
    if status_filter == "active":
        stmt = stmt.where(Deck.archived_at.is_(None))
    elif status_filter == "archived":
        stmt = stmt.where(Deck.archived_at.is_not(None))
    # 'all' applies no filter
    result = await db.execute(stmt)
    return [DeckResponse.model_validate(d) for d in result.scalars().all()]
