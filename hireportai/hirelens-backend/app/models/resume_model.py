"""Resume ORM model."""
from datetime import datetime

from pgvector.sqlalchemy import Vector
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
    # Phase-1: 1536-dim embedding of original_content for pgvector similarity
    # search (replaces TF-IDF in app/services/nlp.py). Nullable so existing
    # rows are unaffected until a backfill job populates them.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationship
    user: Mapped["User"] = relationship(back_populates="resumes")  # type: ignore[name-defined]
