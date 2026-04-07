"""Backward-compat shim — imports moved to app.schemas.requests."""
from app.schemas.requests import (  # noqa: F401
    AnalysisOptions,
    CoverLetterRequest,
    InterviewPrepRequest,
    RewriteRequest,
    TrackerApplicationCreate,
    TrackerApplicationUpdate,
)

__all__ = [
    "AnalysisOptions",
    "RewriteRequest",
    "CoverLetterRequest",
    "InterviewPrepRequest",
    "TrackerApplicationCreate",
    "TrackerApplicationUpdate",
]
