"""Tracker application ORM model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class TrackerApplicationModel(Base, UUIDPrimaryKeyMixin):
    """ORM model for job application tracker entries."""
    __tablename__ = "tracker_applications_v2"

    # user_id is nullable for backward compat with unauthenticated usage
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(200), nullable=False)
    date_applied: Mapped[str] = mapped_column(String(20), nullable=False)
    ats_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Applied", nullable=False)
    scan_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    skills_matched: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills_missing: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationship
    user: Mapped["User | None"] = relationship(back_populates="tracker_applications")  # type: ignore[name-defined]
