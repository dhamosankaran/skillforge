"""Card ORM model."""
from datetime import datetime

from sqlalchemy import DateTime, JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Card(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cards"

    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    embedding: Mapped[list | None] = mapped_column(Vector(1536), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    category: Mapped["Category"] = relationship(  # type: ignore[name-defined]
        back_populates="cards", lazy="select"
    )
