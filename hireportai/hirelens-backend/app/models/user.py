"""User ORM model."""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, func, text
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
    persona: Mapped[str | None] = mapped_column(String(30), nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    # DEPRECATED — see spec #57 (docs/specs/phase-5/57-tracker-level-interview-date.md).
    # Read via tracker_applications_v2.interview_date + the tracker row's
    # company; new code MUST NOT read these columns. Dual-write retained for
    # one release post-spec-57 for backfill safety; column drop is a
    # Phase-6 cleanup slice gated on zero in-code readers.
    interview_target_company: Mapped[str | None] = mapped_column(String(100), nullable=True)
    interview_target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Set by customer.subscription.deleted webhook. Consumed by the deferred
    # win-back churn guard (spec #42 LD-5); landed now to avoid an unbackfillable
    # gap if we waited. Dormant for dismissal-only enforcement.
    downgraded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    # NULL = user has not yet landed on /home; stamp flips the greeting copy
    # from first-visit ("Welcome") to return-visit ("Welcome back"). B-016.
    home_first_visit_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
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
