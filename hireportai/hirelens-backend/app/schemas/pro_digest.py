"""Pydantic schemas for the Phase 6 slice 6.14 Pro daily digest.

Spec: docs/specs/phase-6/14-daily-digest-cron.md §5.1.

Internal-only (never crosses HTTP boundary). The cron entry script is
a closed-box CLI; ``DigestPayload`` is the per-user composer output;
``SendSummary`` is the orchestrator return shape (printed as JSON to
stdout for ops dashboards).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class DigestPayload(BaseModel):
    """Per-user Pro digest content payload (§5.1, §6.3).

    Returned by ``pro_digest_service.compose_digest``. Returns ``None``
    when the user has no engagement signal in the window per §12 D-7
    (strict empty-rule).

    The four core fields per §12 D-3: ``cards_due`` / ``streak`` /
    ``mission_days_left`` (when ``mission_active``) / ``last_scan_score``
    + ``last_scan_delta`` (when tracker history has ≥2 rows).
    """

    user_id: str
    user_name: str
    user_email: str
    cards_due: int = Field(..., ge=0)
    streak: int = Field(..., ge=0)
    mission_active: bool
    mission_days_left: Optional[int] = None
    last_scan_score: Optional[int] = None
    last_scan_delta: Optional[int] = None


class SendSummary(BaseModel):
    """Orchestrator return shape (§5.1).

    Logged at INFO + printed as JSON to stdout by the CLI script per
    §12 D-12. ``candidates_total`` is the selector-layer Pro-tier count
    BEFORE per-user dedup / empty-content guards fire; the difference
    between ``candidates_total`` and ``sent + skipped_dedup +
    skipped_empty + failed`` equals the implicit selector-layer opt-out
    count (per §12 D-10 — no separate ``_skipped_optout`` event).
    """

    sent: int = Field(default=0, ge=0)
    skipped_optout: int = Field(default=0, ge=0)
    skipped_dedup: int = Field(default=0, ge=0)
    skipped_empty: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    candidates_total: int = Field(default=0, ge=0)
    duration_seconds: float = Field(default=0.0, ge=0.0)
