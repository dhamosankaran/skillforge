"""Pydantic v2 response models for the Cards API."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CardResponse(BaseModel):
    """A single flashcard.

    `category_name` is populated only when fetching a card by ID
    (GET /cards/{id}). It is omitted from category-list responses to
    avoid redundancy.
    """

    id: str
    category_id: str
    category_name: Optional[str] = None
    question: str
    answer: str
    difficulty: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryResponse(BaseModel):
    """A category with an aggregated card count.

    Used in GET /cards (the top-level category list). `card_count` is
    computed server-side; it is never stored on the model.
    """

    id: str
    name: str
    icon: str
    color: str
    display_order: int
    source: Optional[str]
    card_count: int


class CategoryListResponse(BaseModel):
    """Wrapper returned by GET /cards."""

    categories: list[CategoryResponse]


class CardSearchResult(BaseModel):
    """A single result from the semantic search endpoint.

    `score` is cosine similarity in [0, 1]; higher = more relevant.
    The raw embedding vector is never included.
    """

    id: str
    category_id: str
    category_name: str
    question: str
    answer: str
    difficulty: str
    tags: list[str]
    score: float
