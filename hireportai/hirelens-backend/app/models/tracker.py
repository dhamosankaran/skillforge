"""Tracker application ORM model."""
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

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
    # Spec #63 (E-043) — re-scan loop. `jd_text` is the source of truth for
    # /rescan re-scoring; `jd_hash` is the (jd_hash, resume_hash) dedupe key
    # for §12 D-2 short-circuit. Both nullable per D-10 (no backfill of
    # pre-migration rows; D-9 422 path handles the `jd_text=NULL` case).
    # Q1 LOCKED — bundled in the foundation migration that closes drift D-020.
    jd_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    jd_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Spec #57 — per-application interview target. Home countdown selects
    # MIN(interview_date) across the user's active (Applied/Interview) rows;
    # see home_state_service.get_next_interview.
    interview_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Spec #59 — full AnalysisResponse payload for scan re-view. Loaded via
    # deferred() so GET /tracker list responses do not inflate (LD-2). Access
    # through tracker_service_v2.get_scan_by_id which applies undefer().
    analysis_payload: Mapped[dict[str, Any] | None] = deferred(
        mapped_column(JSONB, nullable=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationship
    user: Mapped["User | None"] = relationship(back_populates="tracker_applications")  # type: ignore[name-defined]
