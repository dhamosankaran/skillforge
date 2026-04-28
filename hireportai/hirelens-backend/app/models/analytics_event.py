"""Phase 6 analytics event ORM models — append-only event tables.

Spec: docs/specs/phase-6/00-analytics-tables.md §4.

These tables dual-write alongside PostHog (locked decision I1) so admin
content-quality + FSRS retention dashboards have a SQL-queryable source.
INSERT-only at runtime — `analytics_event_service` exposes no UPDATE /
DELETE method (§4.4 + AC-10).

Denormalized FK columns (D-8): `lesson_id` + `deck_id` are stored on
`quiz_review_events`; `deck_id` is stored on `lesson_view_events`. Lesson
IDs are stable across substantive edits (slice 6.4 D-17 bumps version, not
id). Storage cost is bounded; JOIN-elimination on per-lesson / per-deck
rollups is the read-side win.
"""
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class QuizReviewEvent(Base, UUIDPrimaryKeyMixin):
    """One row per FSRS quiz review (BE-emitted via dual-write hook).

    Keyed by `(user_id, quiz_item_id)` non-uniquely — a user can review the
    same quiz_item multiple times in a single session, and each review is a
    separate row.
    """

    __tablename__ = "quiz_review_events"

    # D-1: SET NULL on user delete — anonymize but preserve aggregates.
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    quiz_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("quiz_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    # D-2 / D-8: denormalized FKs.
    lesson_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
    )
    deck_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("decks.id", ondelete="CASCADE"),
        nullable=False,
    )
    # py-fsrs Rating: Again=1, Hard=2, Good=3, Easy=4.
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    # ENUM-as-String per slice 6.1 D-3: new | learning | review | relearning.
    fsrs_state_before: Mapped[str] = mapped_column(String(20), nullable=False)
    fsrs_state_after: Mapped[str] = mapped_column(String(20), nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    lapses: Mapped[int] = mapped_column(Integer, nullable=False)
    time_spent_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # Client-supplied per-page-mount UUID; nullable per slice 6.2 schema.
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    plan: Mapped[str | None] = mapped_column(String(20), nullable=True)
    persona: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_quiz_review_events_user_reviewed_at",
            "user_id",
            "reviewed_at",
        ),
        Index(
            "ix_quiz_review_events_quiz_item_reviewed_at",
            "quiz_item_id",
            "reviewed_at",
        ),
        Index(
            "ix_quiz_review_events_lesson_reviewed_at",
            "lesson_id",
            "reviewed_at",
        ),
        Index(
            "ix_quiz_review_events_deck_reviewed_at",
            "deck_id",
            "reviewed_at",
        ),
    )


class LessonViewEvent(Base, UUIDPrimaryKeyMixin):
    """One row per lesson page view (FE-emitted via
    `POST /api/v1/lessons/:id/view-event`).
    """

    __tablename__ = "lesson_view_events"

    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    lesson_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
    )
    # D-2 / D-8: denormalized deck_id.
    deck_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("decks.id", ondelete="CASCADE"),
        nullable=False,
    )
    # `lessons.version` at view time — locks the lesson body the user saw
    # (substantive edits bump version per slice 6.4 D-17).
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    plan: Mapped[str | None] = mapped_column(String(20), nullable=True)
    persona: Mapped[str | None] = mapped_column(String(30), nullable=True)
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_lesson_view_events_user_viewed_at",
            "user_id",
            "viewed_at",
        ),
        Index(
            "ix_lesson_view_events_lesson_viewed_at",
            "lesson_id",
            "viewed_at",
        ),
        Index(
            "ix_lesson_view_events_deck_viewed_at",
            "deck_id",
            "viewed_at",
        ),
    )
