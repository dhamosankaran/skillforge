"""CardProgress ORM model — per-user FSRS scheduling state for each card."""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class CardProgress(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "card_progress"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    card_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # FSRS scheduler fields (managed exclusively by py-fsrs; never computed in app code)
    state: Mapped[str] = mapped_column(
        String(20), nullable=False, default="new"
    )  # new | learning | review | relearning
    stability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    difficulty_fsrs: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    elapsed_days: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    scheduled_days: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lapses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_reviewed: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(lazy="select")  # type: ignore[name-defined]
    card: Mapped["Card"] = relationship(lazy="select")  # type: ignore[name-defined]

    __table_args__ = (
        UniqueConstraint("user_id", "card_id", name="uq_card_progress_user_card"),
    )
