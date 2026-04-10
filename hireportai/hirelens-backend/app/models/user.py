"""User ORM model."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "users"

    google_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    role: Mapped[str] = mapped_column(
        String(20), server_default=text("'user'"), nullable=False
    )
    persona: Mapped[str | None] = mapped_column(String(20), nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    subscription: Mapped["Subscription"] = relationship(  # type: ignore[name-defined]
        back_populates="user", uselist=False, lazy="selectin"
    )
    resumes: Mapped[list["Resume"]] = relationship(  # type: ignore[name-defined]
        back_populates="user", lazy="selectin"
    )
    usage_logs: Mapped[list["UsageLog"]] = relationship(  # type: ignore[name-defined]
        back_populates="user", lazy="selectin"
    )
    tracker_applications: Mapped[list["TrackerApplicationModel"]] = relationship(  # type: ignore[name-defined]
        back_populates="user", lazy="selectin"
    )
