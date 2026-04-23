"""Tests for the multi-model LLM router."""
from unittest.mock import MagicMock, patch

import pytest

from app.core.llm_router import FAST_TASKS, REASONING_TASKS, _get_tier, generate_for_task


# ---------------------------------------------------------------------------
# Tier classification
# ---------------------------------------------------------------------------

class TestGetTier:
    def test_fast_tasks(self):
        for task in FAST_TASKS:
            assert _get_tier(task) == "fast"

    def test_reasoning_tasks(self):
        for task in REASONING_TASKS:
            assert _get_tier(task) == "reasoning"

    def test_unknown_task_defaults_to_fast(self):
        assert _get_tier("unknown_thing") == "fast"
        assert _get_tier("") == "fast"


# ---------------------------------------------------------------------------
# Helper to build a mock settings object
# ---------------------------------------------------------------------------

def _mock_settings(
    fast_provider="gemini",
    fast_model="gemini-2.0-flash",
    reasoning_provider="gemini",
    reasoning_model="gemini-2.5-pro",
):
    s = MagicMock()
    s.llm_fast_provider = fast_provider
    s.llm_fast_model = fast_model
    s.llm_reasoning_provider = reasoning_provider
    s.llm_reasoning_model = reasoning_model
    return s


# ---------------------------------------------------------------------------
# Model selection — we patch the _PROVIDER_DISPATCH dict to intercept calls
# ---------------------------------------------------------------------------

class TestGenerateForTask:
    """Verify that the router picks the right provider+model per task."""

    @patch("app.core.llm_router.get_settings")
    @patch("app.core.llm_router._PROVIDER_DISPATCH")
    def test_fast_task_uses_fast_model(self, mock_dispatch, mock_settings):
        mock_settings.return_value = _mock_settings()
        mock_fn = MagicMock(return_value='{"question": "test"}')
        mock_dispatch.get.return_value = mock_fn

        result = generate_for_task(task="card_draft", prompt="Generate a card")

        mock_dispatch.get.assert_called_once_with("gemini")
        mock_fn.assert_called_once()
        assert mock_fn.call_args.kwargs["model"] == "gemini-2.0-flash"
        assert result == '{"question": "test"}'

    @patch("app.core.llm_router.get_settings")
    @patch("app.core.llm_router._PROVIDER_DISPATCH")
    def test_reasoning_task_uses_reasoning_model(self, mock_dispatch, mock_settings):
        mock_settings.return_value = _mock_settings()
        mock_fn = MagicMock(return_value='{"sections": []}')
        mock_dispatch.get.return_value = mock_fn

        generate_for_task(task="resume_rewrite", prompt="Rewrite this resume")

        mock_dispatch.get.assert_called_once_with("gemini")
        assert mock_fn.call_args.kwargs["model"] == "gemini-2.5-pro"

    @patch("app.core.llm_router.get_settings")
    @patch("app.core.llm_router._PROVIDER_DISPATCH")
    def test_unknown_task_defaults_to_fast(self, mock_dispatch, mock_settings):
        mock_settings.return_value = _mock_settings()
        mock_fn = MagicMock(return_value="ok")
        mock_dispatch.get.return_value = mock_fn

        generate_for_task(task="unknown_thing", prompt="test")

        # Unknown task → fast tier → fast model
        assert mock_fn.call_args.kwargs["model"] == "gemini-2.0-flash"

    @patch("app.core.llm_router.get_settings")
    @patch("app.core.llm_router._PROVIDER_DISPATCH")
    def test_model_override_from_env(self, mock_dispatch, mock_settings):
        """If LLM_REASONING_MODEL is overridden, reasoning tasks use the override."""
        mock_settings.return_value = _mock_settings(reasoning_model="gemini-2.0-flash")
        mock_fn = MagicMock(return_value="ok")
        mock_dispatch.get.return_value = mock_fn

        generate_for_task(task="resume_rewrite", prompt="test")

        assert mock_fn.call_args.kwargs["model"] == "gemini-2.0-flash"

    @patch("app.core.llm_router.get_settings")
    @patch("app.core.llm_router._PROVIDER_DISPATCH")
    def test_anthropic_provider_dispatch(self, mock_dispatch, mock_settings):
        """When LLM_REASONING_PROVIDER=anthropic, reasoning tasks use anthropic."""
        mock_settings.return_value = _mock_settings(
            reasoning_provider="anthropic",
            reasoning_model="claude-sonnet-4-20250514",
        )
        mock_fn = MagicMock(return_value="Claude response")
        mock_dispatch.get.return_value = mock_fn

        result = generate_for_task(task="cover_letter", prompt="Write a cover letter")

        mock_dispatch.get.assert_called_once_with("anthropic")
        assert mock_fn.call_args.kwargs["model"] == "claude-sonnet-4-20250514"
        assert result == "Claude response"

    @patch("app.core.llm_router.get_settings")
    @patch("app.core.llm_router._PROVIDER_DISPATCH")
    def test_unsupported_provider_raises(self, mock_dispatch, mock_settings):
        mock_settings.return_value = _mock_settings(fast_provider="unsupported_llm")
        mock_dispatch.get.return_value = None

        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            generate_for_task(task="card_draft", prompt="test")


# ── B-022 — job_fit_explanation promoted to reasoning tier ────────────────

class TestJobFitExplanationTier:
    """B-022: Analysis Results promoted from fast → reasoning tier.

    Before B-022 the call used `task="ats_keyword_extraction"` (fast).
    After, the call uses `task="job_fit_explanation"` and gets Pro.
    Guard the classification and that the shared fast task wasn't moved.
    """

    def test_job_fit_explanation_is_reasoning(self):
        assert "job_fit_explanation" in REASONING_TASKS
        assert _get_tier("job_fit_explanation") == "reasoning"

    def test_ats_keyword_extraction_remains_fast(self):
        # Shared task — still used for pure JD keyword parsing. Must NOT
        # drift to reasoning tier by accident.
        assert "ats_keyword_extraction" in FAST_TASKS
        assert _get_tier("ats_keyword_extraction") == "fast"

    @patch("app.core.llm_router.get_settings")
    @patch("app.core.llm_router._PROVIDER_DISPATCH")
    def test_job_fit_explanation_routes_to_reasoning_model(self, mock_dispatch, mock_settings):
        mock_settings.return_value = _mock_settings()
        mock_fn = MagicMock(return_value='{"explanation": "ok"}')
        mock_dispatch.get.return_value = mock_fn

        generate_for_task(
            task="job_fit_explanation",
            prompt="test",
            json_mode=True,
            max_tokens=3500,
            thinking_budget=800,
        )

        assert mock_fn.call_args.kwargs["model"] == "gemini-2.5-pro"
        # thinking_budget must plumb through — missing it on Gemini Pro
        # reproduces the B-014 empty-output failure mode.
        assert mock_fn.call_args.kwargs["thinking_budget"] == 800
