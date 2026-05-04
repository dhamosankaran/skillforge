"""UserCareerIntent ORM model — append-only Career-Climber role-intent history.

Spec: docs/specs/phase-5/67-career-climber-role-intent.md §5.1 + §5.2.

Each ``set_intent`` write inserts a new row and stamps the prior current
row's ``superseded_at``. ``superseded_at IS NULL`` selects the current
intent for a user; non-NULL rows are historical (E-053 longitudinal
narrative).

Indexes:

- ``(user_id)`` — drives FK joins; CASCADE on user delete (spec §5.1).
- ``(user_id, superseded_at)`` — drives current-intent lookup
  ``WHERE user_id = ? AND superseded_at IS NULL``.
- ``(target_role, target_quarter, superseded_at)`` — drives the
  cohort-size + aggregate-stats queries in
  ``career_intent_service.get_aggregate_stats``.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class UserCareerIntent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "user_career_intents"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_role: Mapped[str] = mapped_column(String(30), nullable=False)
    target_quarter: Mapped[str] = mapped_column(String(7), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    __table_args__ = (
        Index(
            "ix_user_career_intents_user_current",
            "user_id",
            "superseded_at",
        ),
        Index(
            "ix_user_career_intents_bucket_current",
            "target_role",
            "target_quarter",
            "superseded_at",
        ),
    )
