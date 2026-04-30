"""Pydantic v2 schemas for the AI ingestion pipeline (Phase 6 slice 6.10b).

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §5 + §12 D-1 / D-9.

Three groups of schemas live here:

1. Request / response wire shapes for `POST /api/v1/admin/ingest`.
2. R2 artifact-key envelope (`IngestionArtifacts`).
3. LLM structured-output schemas (`LessonGenSchema` + `CritiqueSchema`)
   passed as `response_schema=` to `generate_for_task` per D-15.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Status state machine per spec §5.2 + §6.2 stage table.
IngestionStatus = Literal[
    "pending",
    "running",
    "generating",
    "critiquing",
    "publishing",
    "completed",
    "failed",
]

CritiqueVerdict = Literal["PASS", "FAIL", "NEEDS_REVIEW"]

# 1MB cap per §12 D-9; min length keeps trivial pastes out of the queue.
_SOURCE_TEXT_MIN = 100
_SOURCE_TEXT_MAX = 1_048_576


class IngestionJobCreateRequest(BaseModel):
    """Admin pastes Markdown; ingestion produces a draft lesson + N quiz items."""

    source_text: str = Field(..., min_length=_SOURCE_TEXT_MIN, max_length=_SOURCE_TEXT_MAX)
    target_deck_slug: Optional[str] = Field(
        default=None,
        max_length=64,
        description=(
            "Existing deck slug. If None or unknown, the orchestrator will "
            "create a deck from the LLM's `target_deck_slug` output."
        ),
    )
    expected_lesson_count: int = Field(default=1, ge=1, le=5)
    notes: Optional[str] = Field(default=None, max_length=2000)


class IngestionArtifacts(BaseModel):
    """R2 artifact keys for the three artifacts the pipeline persists."""

    source_r2_key: str
    draft_r2_key: Optional[str] = None
    critique_r2_key: Optional[str] = None


class IngestionJobResponse(BaseModel):
    """Read shape for `GET /api/v1/admin/ingest/{job_id}` and POST 202."""

    job_id: str
    status: IngestionStatus
    source_format: str = "markdown"
    source_content_sha256: str
    target_deck_slug: Optional[str] = None
    target_deck_id: Optional[str] = None
    generated_lesson_ids: list[str] = Field(default_factory=list)
    generated_quiz_item_count: int = 0
    critique_verdict: Optional[CritiqueVerdict] = None
    error_message: Optional[str] = None
    current_attempt: int = 0
    max_attempts: int = 3
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    artifacts: IngestionArtifacts

    model_config = ConfigDict(from_attributes=True)


# ── LLM structured-output schemas (passed as response_schema=) ──────────────
#
# Both schemas land at `generate_for_task(json_mode=True, response_schema=…)`.
# Gemini honors the schema server-side per `_call_gemini` D-15 plumbing;
# Anthropic / OpenAI surface it as a prompt hint. The orchestrator validates
# via `Schema.model_validate_json(...)` either way before persistence.


class GeneratedQuizItem(BaseModel):
    """One quiz item inside an `LessonGenSchema` payload."""

    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    question_type: Literal["recall", "application"] = "recall"
    difficulty: Literal["easy", "medium", "hard"] = "medium"


class LessonGenSchema(BaseModel):
    """Stage-1 (Gemini reasoning-tier) output shape per spec §5.5."""

    target_deck_slug: str = Field(..., min_length=1, max_length=64)
    lesson_slug: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    concept_md: str = Field(..., min_length=1)
    production_md: str = Field(..., min_length=1)
    examples_md: str = Field(..., min_length=1)
    quiz_items: list[GeneratedQuizItem] = Field(..., min_length=1, max_length=5)


class CritiqueDimension(BaseModel):
    """One scored dimension inside the cross-model critique."""

    name: Literal["accuracy", "clarity", "completeness", "cohesion"]
    score: int = Field(..., ge=1, le=5)
    rationale: str = Field(..., min_length=1)


class CritiqueSchema(BaseModel):
    """Stage-2 (Anthropic per D-4) critique output shape per spec §5.5."""

    verdict: CritiqueVerdict
    dimensions: list[CritiqueDimension] = Field(default_factory=list)
    rationale: str = Field(..., min_length=1)
