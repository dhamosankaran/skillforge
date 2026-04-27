"""QuizItem ORM model — Phase 6 atomic FSRS-reviewable recall unit.

A lesson has 1+ quiz_items. Substantive quiz edits retire the row
(set `retired_at`, link `superseded_by_id` to the new row) — this is what
keeps FSRS state on the OLD row queryable for analytics while preventing
new progress rows from being created against it.

The "no new quiz_item_progress rows against retired quiz_items" invariant
is enforced at the service layer (slice 6.5), NOT via DB constraint, per
the spec's D-3-adjacent reasoning (informative error messages > opaque
SQLSTATE codes).

Spec: docs/specs/phase-6/01-foundation-schema.md §4.3.
"""
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class QuizItem(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "quiz_items"

    lesson_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    # ENUM-as-String per D-3: 'mcq' | 'free_text' | 'code_completion'
    question_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="free_text", server_default="free_text"
    )
    distractors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # ENUM-as-String per D-3: 'easy' | 'medium' | 'hard' (authored hint, not
    # FSRS-managed difficulty — that lives on quiz_item_progress).
    difficulty: Mapped[str] = mapped_column(
        String(10), nullable=False, default="medium", server_default="medium"
    )
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    # Self-referential FK; old row → new row when a substantive edit fires.
    superseded_by_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("quiz_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    generated_by_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    lesson: Mapped["Lesson"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="quiz_items", lazy="select"
    )

    __table_args__ = (
        # Primary active-quiz lookup — active quizzes for a lesson in display order.
        Index(
            "ix_quiz_items_lesson_active_order",
            "lesson_id",
            "display_order",
            postgresql_where="retired_at IS NULL",
        ),
        # Forward-linkage queries (rare, but cheap).
        Index("ix_quiz_items_superseded_by", "superseded_by_id"),
    )
