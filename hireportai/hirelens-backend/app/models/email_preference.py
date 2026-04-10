"""EmailPreference ORM model — per-user daily reminder settings."""
import secrets
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EmailPreference(Base):
    """One row per user; stores daily-reminder opt-in, timezone, and
    the unsubscribe token used for one-click email unsubscribe."""

    __tablename__ = "email_preferences"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    daily_reminder: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="UTC"
    )
    unsubscribe_token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        default=lambda: secrets.token_hex(32),
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

    user: Mapped["User"] = relationship(lazy="select")  # type: ignore[name-defined]
