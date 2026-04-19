"""Home dashboard schemas — state-aware response (P5-S18c, spec #40)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class HomeStateContext(BaseModel):
    """Context fields backing the state-aware home dashboard.

    All fields are always present in the serialized payload; values may be
    null when the underlying data does not exist or fails to resolve. This
    keeps the TypeScript types stable on the frontend.
    """

    current_streak: int = 0
    last_review_at: Optional[datetime] = None
    active_mission_id: Optional[str] = None
    mission_target_date: Optional[date] = None
    last_scan_date: Optional[datetime] = None
    plan: str = "free"
    last_activity_at: Optional[datetime] = None


class HomeStateResponse(BaseModel):
    """State-aware home dashboard response (spec #40 §5)."""

    persona: Optional[str] = None
    states: list[str] = []
    context: HomeStateContext = HomeStateContext()
