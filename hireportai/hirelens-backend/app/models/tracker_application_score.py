"""Score history per tracker application (E-043 / spec #63)."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class TrackerApplicationScore(Base, UUIDPrimaryKeyMixin):
    """One row per re-scan against a tracker application.

    Append-only event-shape table — no UPDATE/DELETE from application
    code. CASCADE on tracker_application_id + user_id; scan_id stays a
    plain String(36) (no FK; matches `tracker_applications_v2.scan_id`
    on disk — there is no `scans` table).

    Spec: docs/specs/phase-5/63-ats-rescan-loop.md §5.3 (Q2 LOCKED).
    Q1 LOCKED + D-7 denormalized user_id mirror slice 6.0
    `quiz_review_events` precedent.
    """

    __tablename__ = "tracker_application_scores"

    tracker_application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tracker_applications_v2.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Denormalized FK for admin analytics (cross-user "avg improvement"
    # queries) — D-7 LOCKED; mirrors slice 6.0 `quiz_review_events.user_id`.
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # No FK — `scans` table does not exist; matches the
    # `tracker_applications_v2.scan_id` shape on disk.
    scan_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True
    )

    # Mirrors AnalysisResponse field shapes per JC #1 disk-truth correction
    # (overall_score = ats_score: int; per-axis floats from
    # ATSScoreBreakdown).
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    keyword_match_score: Mapped[float] = mapped_column(Float, nullable=False)
    skills_coverage_score: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    formatting_compliance_score: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    bullet_strength_score: Mapped[float] = mapped_column(
        Float, nullable=False
    )

    # §12 D-2 dedupe keys. NOT FKs — they're hash strings, not row refs.
    jd_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    resume_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_tas_tracker_app_scanned_at",
            "tracker_application_id",
            "scanned_at",
        ),
        Index("ix_tas_user_scanned_at", "user_id", "scanned_at"),
        Index(
            "ix_tas_dedupe_lookup",
            "tracker_application_id",
            "jd_hash",
            "resume_hash",
        ),
    )
