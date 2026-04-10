"""Stripe webhook event log for idempotency (Spec #22)."""
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StripeEvent(Base):
    __tablename__ = "stripe_events"

    id: Mapped[str] = mapped_column(
        String(255), primary_key=True
    )  # Stripe event ID (evt_*)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
