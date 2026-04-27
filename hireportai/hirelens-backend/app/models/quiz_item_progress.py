"""QuizItemProgress ORM model — per-user FSRS scheduling state for each quiz_item.

Direct analog of `card_progress` (app/models/card_progress.py) with the FK
retargeted from `cards` to `quiz_items`. The FSRS column shape is
**byte-identical** to `card_progress` modulo the FK swap — this is
intentional so slice 6.5 can copy `study_service`'s FSRS reconstruction
logic verbatim (D-1, AC-6).

Spec: docs/specs/phase-6/01-foundation-schema.md §4.4.
"""
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class QuizItemProgress(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "quiz_item_progress"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quiz_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("quiz_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # FSRS scheduler fields — managed exclusively by py-fsrs.
    state: Mapped[str] = mapped_column(
        String(20), nullable=False, default="new", server_default="new"
    )  # new | learning | review | relearning
    stability: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default="0.0"
    )
    difficulty_fsrs: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default="0.0"
    )
    elapsed_days: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default="0.0"
    )
    scheduled_days: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default="0.0"
    )
    reps: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    lapses: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # py-fsrs v6 learning/relearning step index (None when in Review state).
    fsrs_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_reviewed: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # D-1: NOT NULL with server_default=now() — mirrors card_progress.due_date
    # so the daily-review WHERE clause (`due_date <= now`) needs no null branch.
    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
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

    user: Mapped["User"] = relationship(lazy="select")  # type: ignore[name-defined]  # noqa: F821
    quiz_item: Mapped["QuizItem"] = relationship(lazy="select")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        UniqueConstraint(
            "user_id", "quiz_item_id", name="uq_quiz_item_progress_user_quiz"
        ),
        # Daily review primary query — mirrors card_progress index pattern.
        Index("ix_quiz_item_progress_user_due", "user_id", "due_date"),
        # Per-quiz reviewer / analytics lookups.
        Index("ix_quiz_item_progress_quiz_item", "quiz_item_id"),
    )
