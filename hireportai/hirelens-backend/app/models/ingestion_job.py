"""IngestionJob ORM model — Phase 6 slice 6.10a foundation.

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §5.3 + §7 + D-11.

Tracks one async ingestion job through the pipeline:
`pending → running → generating → critiquing → publishing →
completed | failed`. The orchestrator (`ingestion_service` — lands with
B-083b) writes pending rows on enqueue; the RQ worker
(`ingestion_worker` — also B-083b) advances `status` per stage.

R2 keys are stored verbatim (no presigned URLs surfaced in v1; admins
inspect artifacts via the R2 dashboard / wrangler CLI per spec §5.4).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IngestionJob(Base):
    """One row per `POST /api/v1/admin/ingest` (slice 6.10b) invocation."""

    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_format: Mapped[str] = mapped_column(
        String(16), nullable=False, default="markdown", server_default="markdown"
    )
    source_content_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    source_r2_key: Mapped[str] = mapped_column(String(255), nullable=False)
    draft_r2_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    critique_r2_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # ON DELETE SET NULL — admin account deletion must not orphan job history
    # (mirrors `quiz_review_events` precedent per slice 6.0 D-1).
    created_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_deck_slug: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_deck_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("decks.id", ondelete="SET NULL"),
        nullable=True,
    )
    generated_lesson_ids: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    generated_quiz_item_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    critique_verdict: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_attempt: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default="3"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        # Admin "recent jobs" query (B-083b's `list_recent_ingestion_jobs`).
        Index(
            "ix_ingestion_jobs_status_created_at",
            "status",
            "created_at",
        ),
        # Per-admin filtering (B-083b's `mine_only=true` query param).
        Index(
            "ix_ingestion_jobs_admin_created_at",
            "created_by_user_id",
            "created_at",
        ),
        # Note: `source_content_sha256` carries `index=True` on its column
        # for the B-083b dedupe lookup; no composite index needed.
    )
