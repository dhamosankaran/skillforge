"""Pydantic v2 schemas for Mission Mode endpoints."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MissionCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    target_date: date
    category_ids: list[str] = Field(..., min_length=1)


class MissionDayItem(BaseModel):
    day_number: int
    date: date
    cards_target: int
    cards_completed: int

    model_config = ConfigDict(from_attributes=True)


class MissionResponse(BaseModel):
    id: str
    title: str
    target_date: date
    category_ids: list[str]
    daily_target: int
    total_cards: int
    days_remaining: int
    status: str
    progress_pct: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MissionDetailResponse(MissionResponse):
    days: list[MissionDayItem]


class MissionDailyCardItem(BaseModel):
    id: str
    question: str
    answer: str
    category: str
    difficulty: str

    model_config = ConfigDict(from_attributes=True)


class MissionDailyResponse(BaseModel):
    mission_id: str
    day_number: int
    date: date
    cards_target: int
    cards_completed: int
    cards: list[MissionDailyCardItem]


class MissionDayCompleteResponse(BaseModel):
    mission_id: str
    day_number: int
    cards_completed: int
    cards_target: int
    xp_awarded: int
    mission_status: str
