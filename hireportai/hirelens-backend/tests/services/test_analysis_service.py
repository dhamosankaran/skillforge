"""G-6 extraction parity tests for `analysis_service.score_resume_against_jd`.

Spec: docs/specs/phase-5/63-ats-rescan-loop.md §6.1 + AC-17.

Foundation slice (B-086a). Confirms that lifting the scoring pipeline
out of `analyze_resume` into `analysis_service` preserves the
``AnalysisResponse`` shape + non-stochastic field values for the same
inputs (deterministic helpers only — keyword match / formatting check /
bullet count / score breakdown). The GPT-powered `job_fit_explanation`
falls back to a deterministic template when the LLM call fails, which
is what these tests exercise (no live LLM).
"""
from __future__ import annotations

import pytest

from app.models.response_models import AnalysisResponse, ATSScoreBreakdown
from app.services.analysis_service import score_resume_against_jd

pytestmark = pytest.mark.asyncio(loop_scope="session")


_RESUME_TEXT = (
    "John Doe\n"
    "Software Engineer with 5 years of experience in Python, FastAPI, and PostgreSQL.\n"
    "Built distributed systems handling 10k requests per second using Redis caching.\n"
    "Led a team of 4 engineers to migrate a monolith to microservices architecture.\n"
    "Designed REST APIs with OpenAPI specs and integrated CI/CD pipelines via GitHub Actions.\n"
    "Improved p99 latency by 40% through query optimization and connection pooling.\n"
)

_JD_TEXT = (
    "Senior Backend Engineer — Stripe\n"
    "We are looking for a backend engineer with strong Python, FastAPI, "
    "and PostgreSQL experience. The role requires building scalable REST APIs, "
    "deep familiarity with Redis, and leading engineering teams. Experience with "
    "GitHub Actions, CI/CD, and microservices architecture is a plus.\n"
)


async def test_score_resume_against_jd_returns_analysis_response_shape(db_session):
    response = await score_resume_against_jd(
        resume_text=_RESUME_TEXT,
        jd_text=_JD_TEXT,
        db=db_session,
    )
    assert isinstance(response, AnalysisResponse)
    assert isinstance(response.score_breakdown, ATSScoreBreakdown)
    # Per-axis floats per JC #1 disk-truth.
    assert isinstance(response.score_breakdown.keyword_match, float)
    assert isinstance(response.score_breakdown.skills_coverage, float)
    assert isinstance(response.score_breakdown.formatting_compliance, float)
    assert isinstance(response.score_breakdown.bullet_strength, float)
    assert isinstance(response.ats_score, int)
    assert response.scan_id  # fresh UUID minted
    assert response.resume_text == _RESUME_TEXT


async def test_score_resume_against_jd_is_deterministic_for_pipeline_fields(
    db_session,
):
    """Same inputs → same deterministic-pipeline outputs (modulo scan_id)."""
    a = await score_resume_against_jd(
        resume_text=_RESUME_TEXT, jd_text=_JD_TEXT, db=db_session
    )
    b = await score_resume_against_jd(
        resume_text=_RESUME_TEXT, jd_text=_JD_TEXT, db=db_session
    )
    assert a.scan_id != b.scan_id  # fresh UUID per call
    assert a.ats_score == b.ats_score
    assert a.grade == b.grade
    assert a.score_breakdown == b.score_breakdown
    assert a.matched_keywords == b.matched_keywords
    assert a.missing_keywords == b.missing_keywords
    assert a.formatting_issues == b.formatting_issues
    assert a.keyword_chart_data == b.keyword_chart_data
    assert a.skills_overlap_data == b.skills_overlap_data


async def test_text_only_path_omits_file_derived_artifacts(db_session):
    """/rescan call shape (parsed_resume=None) returns a valid response.

    Text-only callers lose visual formatting hints + file-extracted
    bullet points. The pipeline must still produce a usable
    AnalysisResponse without crashing.
    """
    response = await score_resume_against_jd(
        resume_text=_RESUME_TEXT,
        jd_text=_JD_TEXT,
        db=db_session,
        parsed_resume=None,
    )
    assert isinstance(response, AnalysisResponse)
    # Bullet analysis is empty when the route doesn't pre-extract bullets.
    assert response.bullet_analysis == []
    assert response.score_breakdown.bullet_strength >= 0.0


async def test_parsed_resume_threads_bullets_and_hints(db_session):
    """File-upload callers pass `parsed_resume`; bullets land in response."""
    parsed = {
        "full_text": _RESUME_TEXT,
        "formatting_hints": {},
        "bullet_points": [
            "Built distributed systems handling 10k requests per second.",
            "Led a team of 4 engineers on a microservices migration.",
        ],
    }
    response = await score_resume_against_jd(
        resume_text=_RESUME_TEXT,
        jd_text=_JD_TEXT,
        db=db_session,
        parsed_resume=parsed,
    )
    assert len(response.bullet_analysis) == 2
    for ba in response.bullet_analysis:
        assert isinstance(ba.score, int)
        assert ba.original
