"""Interview question set ORM model.

Persists generated interview-question sets keyed on (user_id, jd_hash) so
revisits return cached results instead of re-running the reasoning-tier LLM.
See docs/specs/phase-5/49-interview-question-storage.md.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class InterviewQuestionSet(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "interview_question_sets"
    __table_args__ = (
        UniqueConstraint("user_id", "jd_hash", name="uq_interview_sets_user_jd"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    jd_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    questions: Mapped[list] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    model_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
