"""B-022 — Analysis Results promoted from fast → reasoning tier.

`generate_job_fit_explanation` previously routed via task
`ats_keyword_extraction` (fast tier, gemini-2.0-flash). The explanation +
strengths + gaps + plan output is a reasoning task — output quality lagged
the rest of the Analysis Results surface.

These tests guard:
- The call-site uses `task="job_fit_explanation"` (reasoning tier).
- The call-site passes `thinking_budget=JOB_FIT_THINKING_BUDGET` — without
  it, Gemini 2.5 Pro's thinking pool can consume the output cap and we
  hit the B-014 empty-output failure mode (fallback branch fires, users
  get the canned deterministic copy forever).
- `max_tokens` has ≥2× headroom above `thinking_budget` so realistic
  responses fit after the cap.
- The shared `ats_keyword_extraction` task did NOT drift to reasoning —
  pure JD keyword parsing is still genuinely fast-tier.
"""
from __future__ import annotations

from unittest.mock import patch

from app.services.gpt_service import (
    JOB_FIT_MAX_TOKENS,
    JOB_FIT_THINKING_BUDGET,
    generate_job_fit_explanation,
)


def _capture_call():
    captured: dict = {}

    def fake(*args, **kwargs):
        captured.update(kwargs)
        return '{"explanation": "ok", "top_strengths": ["a","b","c"], ' \
               '"top_gaps": ["x","y","z"], "improvement_plan": ["p","q","r"]}'

    return captured, fake


def test_job_fit_call_uses_reasoning_task():
    captured, fake = _capture_call()
    with patch("app.services.gpt_service.generate_for_task", side_effect=fake):
        generate_job_fit_explanation(
            resume_data={"skills": ["python"], "sections": {"exp": []}},
            jd_requirements={"required_skills": ["python"], "job_title": "SWE"},
            ats_score=70,
            matched_keywords=["python"],
            missing_keywords=["rust"],
        )

    assert captured.get("task") == "job_fit_explanation", (
        "B-022 regression: Analysis Results must use task='job_fit_explanation' "
        "(reasoning tier). Got task=%r." % captured.get("task")
    )


def test_job_fit_call_pins_thinking_budget():
    """Without thinking_budget, Gemini 2.5 Pro thinking can exhaust the output
    pool → empty text → fallback branch fires. Same failure class as B-014.
    """
    captured, fake = _capture_call()
    with patch("app.services.gpt_service.generate_for_task", side_effect=fake):
        generate_job_fit_explanation(
            resume_data={"skills": [], "sections": {}},
            jd_requirements={"required_skills": [], "job_title": "SWE"},
            ats_score=50,
            matched_keywords=[],
            missing_keywords=[],
        )

    assert "thinking_budget" in captured, (
        "B-022 regression: job_fit_explanation call missing `thinking_budget` "
        "kwarg. Gemini 2.5 Pro's thinking pool can consume max_tokens and "
        "return empty text → deterministic-fallback branch fires silently."
    )
    assert captured["thinking_budget"] == JOB_FIT_THINKING_BUDGET
    assert captured["max_tokens"] == JOB_FIT_MAX_TOKENS


def test_job_fit_max_tokens_has_headroom():
    """Output pool ≥2× thinking budget so realistic responses fit after cap."""
    assert JOB_FIT_MAX_TOKENS >= JOB_FIT_THINKING_BUDGET * 2, (
        f"JOB_FIT_MAX_TOKENS={JOB_FIT_MAX_TOKENS} is too close to "
        f"JOB_FIT_THINKING_BUDGET={JOB_FIT_THINKING_BUDGET}. Leave ≥2× "
        "headroom so the explanation + strengths + gaps + plan fit after "
        "the model exhausts the thinking allowance."
    )
