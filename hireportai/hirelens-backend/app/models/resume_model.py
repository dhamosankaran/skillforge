"""Resume ORM model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class Resume(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "resumes"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    optimized_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationship
    user: Mapped["User"] = relationship(back_populates="resumes")  # type: ignore[name-defined]
