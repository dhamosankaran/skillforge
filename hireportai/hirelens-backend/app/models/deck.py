"""Deck ORM model — Phase 6 top-level curriculum bucket.

Replaces the role of `categories` for Phase 6 content. The 12 locked
top-level buckets (e.g. "Transformer & LLM Internals", "Agentic Systems &
MCP") seed this table; `tier='foundation'` rows are free-tier accessible,
`tier='premium'` rows are Pro-gated. `persona_visibility` drives Learn
page filtering for slice 6.7 (persona-aware composition).

Spec: docs/specs/phase-6/01-foundation-schema.md §4.1.
"""
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class Deck(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "decks"

    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    icon: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # ENUM-as-String per D-3: 'climber' | 'interview_prepper' | 'both'
    persona_visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default="both", server_default="both"
    )
    # ENUM-as-String per D-3: 'foundation' | 'premium'
    tier: Mapped[str] = mapped_column(
        String(20), nullable=False, default="premium", server_default="premium"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    lessons: Mapped[list["Lesson"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="deck", lazy="select"
    )

    __table_args__ = (
        # Learn page primary query: visible decks for persona X in display order.
        Index(
            "ix_decks_persona_display_active",
            "persona_visibility",
            "display_order",
            postgresql_where="archived_at IS NULL",
        ),
    )
