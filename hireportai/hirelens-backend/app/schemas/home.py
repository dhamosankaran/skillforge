"""Home dashboard schemas — state-aware response (P5-S18c, spec #40)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class NextInterview(BaseModel):
    """Per-user nearest-upcoming interview (spec #57 §4.3 / AC-4).

    Computed server-side from ``tracker_applications_v2`` via the
    selection rule in spec #57 §2.2: MIN(interview_date) WHERE the row
    is the user's AND date >= today AND status IN ('Applied','Interview').
    """

    date: date
    company: str
    tracker_id: str


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
    next_interview: Optional[NextInterview] = None


class HomeStateResponse(BaseModel):
    """State-aware home dashboard response (spec #40 §5)."""

    persona: Optional[str] = None
    states: list[str] = []
    context: HomeStateContext = HomeStateContext()
