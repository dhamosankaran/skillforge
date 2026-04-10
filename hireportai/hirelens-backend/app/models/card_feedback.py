"""CardFeedback ORM model — per-card user feedback (thumbs up/down)."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class CardFeedback(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "card_feedback"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    card_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vote: Mapped[str] = mapped_column(String(4), nullable=False)  # "up" or "down"
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(lazy="select")  # type: ignore[name-defined]
    card: Mapped["Card"] = relationship(lazy="select")  # type: ignore[name-defined]
