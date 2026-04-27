"""Pydantic v2 schemas for the Phase 6 `lessons` table.

Spec: docs/specs/phase-6/01-foundation-schema.md §4.2.
"""
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

LessonVersionType = Literal["initial", "minor_edit", "substantive_edit"]


class LessonResponse(BaseModel):
    """A single lesson (read shape)."""

    id: str
    deck_id: str
    slug: str
    title: str
    concept_md: str
    production_md: str
    examples_md: str
    display_order: int
    version: int
    version_type: LessonVersionType
    published_at: Optional[datetime] = None
    generated_by_model: Optional[str] = None
    source_content_id: Optional[str] = None
    quality_score: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
