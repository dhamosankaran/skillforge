"""Pydantic v2 schemas for the Phase 6 `decks` table.

Spec: docs/specs/phase-6/01-foundation-schema.md §4.1 (slice 6.1) +
docs/specs/phase-6/03-lesson-ux.md §6.3 (slice 6.3 — adds the deck
+ lessons bundle returned by GET /api/v1/decks/{id}/lessons) +
docs/specs/phase-6/04-admin-authoring.md §6.1 + §6.2 (slice 6.4b —
admin write schemas).
ENUM-as-String values are declared here as `Literal` types per D-3.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.lesson import LessonResponse

PersonaVisibility = Literal["climber", "interview_prepper", "both"]
DeckTier = Literal["foundation", "premium"]
AdminDeckStatusFilter = Literal["active", "archived", "all"]

_SLUG_PATTERN = r"^[a-z0-9-]+$"


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


# ── Slice 6.4b — admin write schemas (spec §6.1 + §6.2) ─────────────────────


class DeckCreateRequest(BaseModel):
    """Admin payload for `POST /api/v1/admin/decks` (spec §6.1)."""

    slug: str = Field(..., min_length=1, max_length=100, pattern=_SLUG_PATTERN)
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    display_order: int = Field(default=0, ge=0)
    icon: Optional[str] = Field(default=None, max_length=10)
    persona_visibility: PersonaVisibility = "both"
    tier: DeckTier = "premium"


class DeckUpdateRequest(BaseModel):
    """Admin payload for `PATCH /api/v1/admin/decks/{deck_id}` (spec §6.2).

    All fields Optional. Only fields present in the payload mutate.
    `archived_at` is NOT mutable through this route — uses
    `POST .../archive` instead.
    """

    slug: Optional[str] = Field(
        default=None, min_length=1, max_length=100, pattern=_SLUG_PATTERN
    )
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, min_length=1)
    display_order: Optional[int] = Field(default=None, ge=0)
    icon: Optional[str] = Field(default=None, max_length=10)
    persona_visibility: Optional[PersonaVisibility] = None
    tier: Optional[DeckTier] = None
