"""EmailLog ORM model — append-only dedup ledger for cron email sends.

One row per email sent by the Phase-6 digest pipeline (slice 6.14
consumer). Forward-only — no backfill of Phase-2 reminder sends.

Supersedes Phase-2 spec #15 §email_send_log (designed but never built);
see ``docs/specs/phase-6/13-pro-digest-opt-out.md`` §5.2.
"""
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class EmailLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "email_log"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    email_type: Mapped[str] = mapped_column(String(30), nullable=False)
    sent_date: Mapped[date] = mapped_column(Date, nullable=False)
    resend_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "email_type", "sent_date",
            name="uq_email_log_user_type_date",
        ),
        Index("ix_email_log_user_sent_date", "user_id", "sent_date"),
    )
