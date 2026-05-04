"""Pydantic v2 response schema for the AppShell loop-progress endpoint.

Spec: docs/specs/phase-5/66-appshell-loop-progress-strip.md §5 + §6.1
+ §12 D-13.
"""
from __future__ import annotations

from pydantic import BaseModel


class LoopProgressResponse(BaseModel):
    """Per-tracker gap-card review progress + days since last scan.

    Consumed by `<LoopProgressStrip>` (FE) to derive step-2 ('Studying')
    state and step-3 ('Re-scan') unlock predicate per spec §8.2.
    """

    tracker_application_id: str
    total_gap_cards: int
    reviewed_gap_cards: int
    percent_reviewed: float
    days_since_last_scan: int | None
