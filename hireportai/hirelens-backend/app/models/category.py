"""Category ORM model."""
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class Category(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    icon: Mapped[str] = mapped_column(String(10), nullable=False)
    color: Mapped[str] = mapped_column(String(30), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    cards: Mapped[list["Card"]] = relationship(  # type: ignore[name-defined]
        back_populates="category", lazy="select"
    )
