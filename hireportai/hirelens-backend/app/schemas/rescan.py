"""Pydantic schemas for the ATS re-scan loop (E-043 / spec #63).

Foundation half (B-086a): scaffolds the request + score-history +
delta envelopes. The /rescan route handler + score-history GET + the
service that writes / reads these rows land in B-086b.

Schema names + field shapes follow §5 of the spec, with field names
aligned to JC #1 disk-truth (`AnalysisResponse.score_breakdown`):
``keyword_match`` / ``skills_coverage`` / ``formatting_compliance`` /
``bullet_strength``.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RescanRequest(BaseModel):
    """POST /api/v1/analyze/rescan request body."""

    tracker_application_id: str = Field(
        ...,
        description=(
            "UUID of tracker_applications_v2 row to re-score against the "
            "row's stored jd_text."
        ),
    )
    resume_text: str = Field(..., min_length=200, max_length=50_000)


class ScoreHistoryEntry(BaseModel):
    """One row of ``tracker_application_scores`` flattened for the wire."""

    id: str
    scan_id: Optional[str]
    overall_score: int
    keyword_match_score: float
    skills_coverage_score: float
    formatting_compliance_score: float
    bullet_strength_score: float
    scanned_at: datetime


class ScoreDelta(BaseModel):
    """Pre-computed delta between the latest two history rows.

    BE owns the math per §12 D-6 — FE renders pre-computed values
    without re-doing the subtraction. ``None`` when ``len(history) < 2``.
    """

    overall_delta: int
    keyword_match_delta: float
    skills_coverage_delta: float
    formatting_compliance_delta: float
    bullet_strength_delta: float
    days_between: int


class ScoreHistoryResponse(BaseModel):
    """GET /api/v1/tracker/{id}/scores response envelope.

    ``history`` is chronological (oldest-first); ``delta`` is null on
    cold-start (single-row history).
    """

    tracker_application_id: str
    history: List[ScoreHistoryEntry]
    delta: Optional[ScoreDelta] = None


class ScoreDeltaResponse(BaseModel):
    """Per-axis delta envelope for the /rescan response surface.

    Reserved for B-086b — the route returns ``AnalysisResponse`` directly
    today (§5.2). This envelope captures the audit-#11 / D-12 shape so
    the impl slice has a stable contract to fill in. ``short_circuited``
    flips true when the §12 D-2 dedupe path matches and no LLM call ran.
    """

    tracker_application_id: str
    ats_score_before: Optional[int] = None
    ats_score_after: int
    ats_score_delta: Optional[int] = None
    keyword_match_delta: Optional[float] = None
    skills_coverage_delta: Optional[float] = None
    formatting_compliance_delta: Optional[float] = None
    bullet_strength_delta: Optional[float] = None
    short_circuited: bool = False
