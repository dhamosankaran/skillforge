"""Pydantic v2 schemas for the Admin Card CRUD API."""
from datetime import datetime
from typing import Literal, Optional, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CardCreateRequest(BaseModel):
    category_id: str
    question: str = Field(..., min_length=1, max_length=5000)
    answer: str = Field(..., min_length=1, max_length=10000)
    difficulty: Literal["easy", "medium", "hard"]
    tags: list[str] = Field(default_factory=list)


class CardUpdateRequest(BaseModel):
    category_id: Optional[str] = None
    question: Optional[str] = Field(None, min_length=1, max_length=5000)
    answer: Optional[str] = Field(None, min_length=1, max_length=10000)
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    tags: Optional[list[str]] = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> Self:
        if not any([
            self.category_id, self.question, self.answer,
            self.difficulty, self.tags is not None,
        ]):
            raise ValueError("At least one field must be provided")
        return self


class AdminCardResponse(BaseModel):
    id: str
    category_id: str
    category_name: str
    question: str
    answer: str
    difficulty: str
    tags: list[str]
    embedding_status: Literal["pending", "ready"]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminCardListResponse(BaseModel):
    cards: list[AdminCardResponse]
    total: int
    page: int
    per_page: int
    pages: int


class CardImportRowError(BaseModel):
    row: int
    error: str


class CardImportResponse(BaseModel):
    created_count: int
    skipped_count: int
    errors: list[CardImportRowError]


class CardGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    difficulty: Literal["easy", "medium", "hard"]


class CardDraftResponse(BaseModel):
    question: str
    answer: str
    difficulty: str
    tags: list[str]
