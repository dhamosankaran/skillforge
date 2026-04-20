"""Paywall dismissal ORM model.

Append-only log of user decisions to dismiss a paywall. Consumed by
`app/services/paywall_service.py` to drive the per-trigger grace window
(spec #42, LD-1 through LD-8). Win-back consumption is deferred — the
table is intentionally enough to support it when the win-back slice lands.

See docs/specs/phase-5/42-paywall-dismissal.md.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class PaywallDismissal(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "paywall_dismissals"
    __table_args__ = (
        # Serves both the 60s LD-8 dedup read and the "dismissal exists?" check
        # inside should_show_paywall. DESC matches the app-level order-by.
        Index(
            "ix_paywall_dismissals_user_trigger_time",
            "user_id",
            "trigger",
            "dismissed_at",
        ),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    dismissed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    action_count_at_dismissal: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
