"""Pydantic v2 request models for HirePort AI API."""
from typing import Optional

from pydantic import BaseModel, Field


class AnalysisOptions(BaseModel):
    """Optional flags to control which GPT features run."""

    run_rewrite: bool = False
    run_cover_letter: bool = False
    run_interview_prep: bool = False


class RewriteRequest(BaseModel):
    """Request body for resume rewrite endpoint."""

    resume_text: str = Field(..., min_length=50, description="Plain text of the resume")
    job_description: str = Field(..., min_length=50, description="Job description text")
    template_type: Optional[str] = Field(
        default=None,
        description="Resume template: 'general', 'business', or 'data_science'. Auto-detected if omitted.",
    )
    major: Optional[str] = Field(
        default=None,
        description="User's major/field of study, used to tailor the resume.",
    )


class CoverLetterRequest(BaseModel):
    """Request body for cover letter generation."""

    resume_text: str = Field(..., min_length=50)
    job_description: str = Field(..., min_length=50)
    tone: str = Field(default="professional", pattern="^(professional|confident|conversational)$")


class InterviewPrepRequest(BaseModel):
    """Request body for interview prep generation."""

    resume_text: str = Field(..., min_length=50)
    job_description: str = Field(..., min_length=50)
    force_regenerate: bool = Field(
        default=False,
        description="Bypass the per-JD cache and regenerate. Spec #49.",
    )


class TrackerApplicationCreate(BaseModel):
    """Request body for creating a tracker application."""

    company: str = Field(..., min_length=1, max_length=200)
    role: str = Field(..., min_length=1, max_length=200)
    date_applied: str = Field(..., description="ISO date string YYYY-MM-DD")
    ats_score: int = Field(default=0, ge=0, le=100)
    status: str = Field(default="Applied", pattern="^(Applied|Interview|Offer|Rejected)$")
    scan_id: Optional[str] = None


class TrackerApplicationUpdate(BaseModel):
    """Request body for updating a tracker application."""

    company: Optional[str] = Field(None, min_length=1, max_length=200)
    role: Optional[str] = Field(None, min_length=1, max_length=200)
    date_applied: Optional[str] = None
    ats_score: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[str] = Field(None, pattern="^(Applied|Interview|Offer|Rejected)$")
