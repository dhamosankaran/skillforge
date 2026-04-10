"""Pydantic v2 schemas for the Progress / Analytics endpoints."""
from datetime import date

from pydantic import BaseModel


class CategoryCoverage(BaseModel):
    """One category's mastery breakdown for the radar chart."""

    category: str
    total_cards: int
    studied: int
    mastery_pct: float  # 0.0 – 100.0


class HeatmapDay(BaseModel):
    """One day's review activity for the heatmap."""

    date: date
    review_count: int


class RadarResponse(BaseModel):
    """Response for GET /api/v1/progress/radar."""

    categories: list[CategoryCoverage]


class HeatmapResponse(BaseModel):
    """Response for GET /api/v1/progress/heatmap."""

    days: list[HeatmapDay]
