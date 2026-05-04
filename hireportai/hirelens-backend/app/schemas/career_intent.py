"""Pydantic schemas for the Career-Climber role-intent capture surface.

Spec: docs/specs/phase-5/67-career-climber-role-intent.md §5.3 + §5.4.

Three external schemas:

- ``CareerIntentCreate`` — request body for ``POST /users/me/career-intent``.
  Validates ``target_role`` against ``ALLOWED_ROLES`` (D-11) and
  ``target_quarter`` against the ``YYYY-Q[1-4]`` regex + current-or-future
  rule (§5.4).
- ``CareerIntentResponse`` — response shape for POST/GET; mirrors the
  ORM row including ``superseded_at`` so the FE can distinguish current
  vs historical (always NULL on the GET happy path).
- ``AggregateStats`` / ``CategoryShare`` — internal payload from
  ``get_aggregate_stats``; consumed by ``pro_digest_service`` to populate
  the optional ``aggregate_intent_block`` on the digest payload.

``ALLOWED_ROLES`` lives here as a frozenset (D-11). Easier to extend
than a DB CHECK and mirrors the existing enum patterns at
``app/schemas/study.py``.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


ALLOWED_ROLES: frozenset[str] = frozenset(
    {
        "staff",
        "senior_staff",
        "principal",
        "distinguished",
        "em",
        "sr_em",
        "director",
    }
)

_QUARTER_RE = re.compile(r"^\d{4}-Q[1-4]$")


def _current_quarter_tuple(now: datetime | None = None) -> tuple[int, int]:
    """Return ``(year, quarter_index)`` for the current UTC quarter."""
    ts = now if now is not None else datetime.now(timezone.utc)
    quarter = (ts.month - 1) // 3 + 1
    return ts.year, quarter


def _parse_quarter(value: str) -> tuple[int, int]:
    """Parse a ``YYYY-Q[1-4]`` string into ``(year, quarter_index)``."""
    year_str, quarter_str = value.split("-Q", 1)
    return int(year_str), int(quarter_str)


class CareerIntentCreate(BaseModel):
    """POST body — captures one (target_role, target_quarter) pair.

    Per §5.4, ``target_quarter`` must be the **current** quarter or a
    **future** quarter at insert time. Past quarters → 422.
    """

    target_role: str = Field(..., max_length=30)
    target_quarter: str = Field(..., max_length=7)

    @field_validator("target_role")
    @classmethod
    def _validate_role(cls, value: str) -> str:
        if value not in ALLOWED_ROLES:
            allowed = ", ".join(sorted(ALLOWED_ROLES))
            raise ValueError(
                f"target_role must be one of: {allowed}"
            )
        return value

    @field_validator("target_quarter")
    @classmethod
    def _validate_quarter(cls, value: str) -> str:
        if not _QUARTER_RE.match(value):
            raise ValueError(
                "target_quarter must match the YYYY-Q[1-4] format "
                "(e.g. '2026-Q3')"
            )
        target = _parse_quarter(value)
        if target < _current_quarter_tuple():
            raise ValueError(
                "target_quarter must be current or future"
            )
        return value


class CareerIntentResponse(BaseModel):
    """GET / POST response shape — mirrors ``UserCareerIntent`` row."""

    id: str
    user_id: str
    target_role: str
    target_quarter: str
    created_at: datetime
    superseded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CategoryShare(BaseModel):
    """One row in ``AggregateStats.top_categories``."""

    category_name: str
    percent_of_study_time: float = Field(..., ge=0.0, le=100.0)


class AggregateStats(BaseModel):
    """Aggregate cohort study-time-by-category — returned by
    ``get_aggregate_stats`` only when cohort ≥ ``MIN_COHORT_SIZE`` (§4.4).

    None below threshold (silent suppression — D-8). The composer never
    sees raw counts and never bypasses the threshold check.
    """

    target_role: str
    target_quarter: str
    cohort_size: int = Field(..., ge=0)
    top_categories: list[CategoryShare]
