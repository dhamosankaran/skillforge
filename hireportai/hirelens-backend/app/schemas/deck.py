"""Pydantic v2 schemas for the Phase 6 `decks` table.

Spec: docs/specs/phase-6/01-foundation-schema.md §4.1.
ENUM-as-String values are declared here as `Literal` types per D-3.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

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
