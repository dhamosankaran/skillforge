"""Usage log ORM model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class UsageLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "usage_logs"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    feature_used: Mapped[str] = mapped_column(String(100), nullable=False)
    tokens_consumed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    # Relationship
    user: Mapped["User"] = relationship(back_populates="usage_logs")  # type: ignore[name-defined]
