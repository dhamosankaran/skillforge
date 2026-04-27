"""Lesson ORM model — Phase 6 unit of teaching content.

One lesson = one card on the Learn page (concept + production + examples
+ quiz panel rendered as a single multi-section view).

Per D-2 the `source_content_id` ships as a NULLABLE String column WITHOUT
an FK constraint at this slice's migration time — the `source_content`
table is defined in slice 6.9. The FK is added in 6.9's migration once
the target table exists.

Spec: docs/specs/phase-6/01-foundation-schema.md §4.2.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class Lesson(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "lessons"

    deck_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("decks.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    concept_md: Mapped[str] = mapped_column(Text, nullable=False)
    production_md: Mapped[str] = mapped_column(Text, nullable=False)
    examples_md: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    # ENUM-as-String per D-3: 'initial' | 'minor_edit' | 'substantive_edit'
    version_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="initial", server_default="initial"
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    generated_by_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # D-2: NULLABLE String(36) without FK; slice 6.9 adds the FK constraint.
    source_content_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # D-4: Numeric for product analytics (deterministic rounding).
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
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

    deck: Mapped["Deck"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="lessons", lazy="select"
    )
    quiz_items: Mapped[list["QuizItem"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="lesson", lazy="select"
    )

    __table_args__ = (
        UniqueConstraint("deck_id", "slug", name="uq_lessons_deck_slug"),
        # Primary deck-detail query — active lessons within a deck in display order.
        Index(
            "ix_lessons_deck_display_active",
            "deck_id",
            "display_order",
            postgresql_where="archived_at IS NULL",
        ),
        # Admin review queue — drafted but not yet published.
        Index(
            "ix_lessons_review_queue",
            "published_at",
            postgresql_where="published_at IS NULL",
        ),
        # Active-lesson lookup support.
        Index("ix_lessons_deck_archived", "deck_id", "archived_at"),
        # Slice 6.9 forward-link queries (lessons generated from a source).
        Index("ix_lessons_source_content", "source_content_id"),
    )
