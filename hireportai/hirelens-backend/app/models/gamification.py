"""Gamification ORM models — XP, streaks, badges.

Three tables:
  - gamification_stats : one row per user; tracks XP, streaks, freeze state
  - badges             : static catalog of badges (id, name, earn condition)
  - user_badges        : join table; one row per user/badge with earned_at

The `badges` catalog is mirrored in `app/services/gamification_service.BADGES`
so badge evaluation does not need a DB roundtrip. The `badges` table exists so
that the catalog is queryable from SQL and joinable from `user_badges`.
"""
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class GamificationStats(Base):
    """Per-user XP / streak / freeze state. PK = user_id (one row per user)."""

    __tablename__ = "gamification_stats"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_active_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    freezes_available: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    freeze_week_start: Mapped[date | None] = mapped_column(Date, nullable=True)
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


class Badge(Base):
    """Static badge catalog. Seeded on migration; no admin CRUD."""

    __tablename__ = "badges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    threshold_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # "xp" | "streak" | "event"
    threshold_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UserBadge(Base, UUIDPrimaryKeyMixin):
    """Earned badges. One row per (user_id, badge_id)."""

    __tablename__ = "user_badges"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    badge_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("badges.id", ondelete="CASCADE"),
        nullable=False,
    )
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    badge: Mapped["Badge"] = relationship(lazy="selectin")

    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="uq_user_badges_user_badge"),
    )
