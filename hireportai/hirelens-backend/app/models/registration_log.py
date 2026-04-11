"""Registration log — tracks IP addresses used for new account creation."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class RegistrationLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "registration_logs"

    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    google_email: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
