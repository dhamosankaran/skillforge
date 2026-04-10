"""Mission Mode ORM models — time-bound study sprints.

Two tables:
  - missions       : user's sprint commitment (target date, daily target, status)
  - mission_days   : per-day tracking (cards_target vs cards_completed)

Category association is handled via the `mission_categories` secondary table.
"""
from datetime import date, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# Association table: mission ↔ category (many-to-many)
mission_categories = Table(
    "mission_categories",
    Base.metadata,
    Column(
        "mission_id",
        String(36),
        ForeignKey("missions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        String(36),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)


class Mission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "missions"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    daily_target: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active | completed | abandoned

    # Relationships
    user: Mapped["User"] = relationship(lazy="select")  # type: ignore[name-defined]
    categories: Mapped[list["Category"]] = relationship(  # type: ignore[name-defined]
        secondary=mission_categories, lazy="selectin"
    )
    days: Mapped[list["MissionDay"]] = relationship(
        back_populates="mission", lazy="selectin", order_by="MissionDay.day_number"
    )


class MissionDay(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "mission_days"

    mission_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    cards_target: Mapped[int] = mapped_column(Integer, nullable=False)
    cards_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    mission: Mapped["Mission"] = relationship(back_populates="days", lazy="select")

    __table_args__ = (
        UniqueConstraint("mission_id", "day_number", name="uq_mission_days_number"),
        UniqueConstraint("mission_id", "date", name="uq_mission_days_date"),
    )
