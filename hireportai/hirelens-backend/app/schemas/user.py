"""Pydantic schemas for the users router.

Introduced in P5-S16 alongside PATCH /api/v1/users/me/persona. See
`docs/specs/phase-5/34-persona-picker-and-home.md` §API Contract.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PersonaEnum(str, Enum):
    """The three personas the product serves (PRD §1.3)."""

    interview_prepper = "interview_prepper"
    career_climber = "career_climber"
    team_lead = "team_lead"


class PersonaUpdateRequest(BaseModel):
    """Request body for PATCH /api/v1/users/me/persona."""

    persona: PersonaEnum
    interview_target_date: Optional[date] = None
    interview_target_company: Optional[str] = Field(default=None, max_length=100)

    @field_validator("interview_target_company", mode="before")
    @classmethod
    def _empty_string_to_none(cls, value: object) -> object:
        """Trim whitespace and coerce empty strings to None per spec."""
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value
