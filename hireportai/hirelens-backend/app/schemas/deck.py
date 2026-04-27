"""Pydantic v2 schemas for the Phase 6 `decks` table.

Spec: docs/specs/phase-6/01-foundation-schema.md §4.1 (slice 6.1) +
docs/specs/phase-6/03-lesson-ux.md §6.3 (slice 6.3 — adds the deck
+ lessons bundle returned by GET /api/v1/decks/{id}/lessons).
ENUM-as-String values are declared here as `Literal` types per D-3.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.lesson import LessonResponse

PersonaVisibility = Literal["climber", "interview_prepper", "both"]
DeckTier = Literal["foundation", "premium"]


class DeckResponse(BaseModel):
    """A single deck (read shape)."""

    id: str
    slug: str
    title: str
    description: str
    display_order: int
    icon: Optional[str] = None
    persona_visibility: PersonaVisibility
    tier: DeckTier
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ── Slice 6.3 — deck + lessons bundle (spec §6.3) ───────────────────────────


class DeckLessonsResponse(BaseModel):
    """Deck shell + ordered list of active lessons.

    Returned by GET /api/v1/decks/{deck_id}/lessons. Empty `lessons`
    list when the deck exists but has no lessons (200, not 404).
    """

    deck: DeckResponse
    lessons: list[LessonResponse]

    model_config = ConfigDict(from_attributes=True)
