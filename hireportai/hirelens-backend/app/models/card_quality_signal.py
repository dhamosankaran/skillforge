"""CardQualitySignal ORM model — Phase 6 slice 6.13.5a (LD J2 home).

Spec: docs/specs/phase-6/12-quality-signals.md §5.1 + §12 D-1..D-14.

One row per ``(lesson_id, quiz_item_id, signal_source, dimension,
recorded_by_user_id)`` tuple — the 5-tuple intentionally distinct from
LD J2's 4-tuple key per §12 D-5 so per-user ``user_thumbs`` rows do not
collide while ``critique`` / ``user_review`` rows (where
``recorded_by_user_id IS NULL``) still collapse to the LD J2 4-tuple
under NULLS-distinct UNIQUE semantics.

UPSERT semantics per §12 D-8: ``INSERT ... ON CONFLICT (...) DO UPDATE
SET score=EXCLUDED.score, recorded_at=NOW()``. Re-running any consumer
with unchanged inputs is a no-op for ``score`` but bumps ``recorded_at``
per §12 D-13.

``signal_source`` is ``String(20)`` rather than enum to allow future
sources (e.g. ``'generation'`` per §13 last bullet) without a migration.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class CardQualitySignal(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "card_quality_signals"

    lesson_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
    )
    quiz_item_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("quiz_items.id", ondelete="CASCADE"),
        nullable=True,
    )
    signal_source: Mapped[str] = mapped_column(String(20), nullable=False)
    dimension: Mapped[str] = mapped_column(String(30), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(36), nullable=True)
    recorded_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        # NULLS NOT DISTINCT (Postgres 15+) so critique signals — where
        # both ``quiz_item_id`` and ``recorded_by_user_id`` are NULL —
        # re-conflict on subsequent UPSERTs. Per-user thumbs rows still
        # stay distinct via their non-NULL ``recorded_by_user_id``.
        UniqueConstraint(
            "lesson_id",
            "quiz_item_id",
            "signal_source",
            "dimension",
            "recorded_by_user_id",
            name="ux_card_quality_signals_key",
            postgresql_nulls_not_distinct=True,
        ),
        Index(
            "ix_card_quality_signals_lesson_source",
            "lesson_id",
            "signal_source",
            text("recorded_at DESC"),
        ),
        Index(
            "ix_card_quality_signals_quiz_item_source",
            "quiz_item_id",
            "signal_source",
            text("recorded_at DESC"),
            postgresql_where=text("quiz_item_id IS NOT NULL"),
        ),
        Index(
            "ix_card_quality_signals_user",
            "recorded_by_user_id",
            "signal_source",
            text("recorded_at DESC"),
            postgresql_where=text("recorded_by_user_id IS NOT NULL"),
        ),
    )
