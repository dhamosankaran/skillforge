"""LLM router extension tests (Phase 6 slice 6.10a — B-083a foundation).

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §10.7 + D-14 + D-15.

Adds two additive kwargs to `app.core.llm_router.generate_for_task`:

    provider_override: Optional[str] = None
        Forces dispatch to a specific provider regardless of the
        per-tier env config. Required for slice 6.10b's cross-model
        critique (Gemini gen → Anthropic critique per D-4).

    response_schema: Optional[Type[BaseModel]] = None
        Pydantic model passed into Gemini's
        `types.GenerateContentConfig(response_schema=...)` for
        structured output (closes drift D-016).

Existing call sites must remain binary-compatible — kwargs default to
None, and these tests assert the no-kwarg path is unchanged.

Mock strategy note: `_PROVIDER_DISPATCH` is a module-level dict
constructed at import time, so patching `llm_router._call_gemini` does
NOT affect dispatch. We patch the dict's entries directly via
`patch.dict(...)`, which is the canonical fix.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from app.core import llm_router
from app.core.llm_router import generate_for_task


class _StubSchema(BaseModel):
    value: str


def _fake_settings(**overrides):
    base = dict(
        gemini_api_key="gk",
        anthropic_api_key="ak",
        openai_api_key="ok",
        llm_fast_provider="gemini",
        llm_fast_model="gemini-2.5-flash",
        llm_reasoning_provider="gemini",
        llm_reasoning_model="gemini-2.5-pro",
    )
    base.update(overrides)
    return MagicMock(**base)


# ---------------------------------------------------------------------------
# AC-14 — provider_override forces dispatch
# ---------------------------------------------------------------------------
def test_provider_override_forces_anthropic_dispatch():
    """`provider_override='anthropic'` calls `_call_anthropic` regardless of env."""
    mock_anthropic = MagicMock(return_value="anthropic-out")
    mock_gemini = MagicMock(return_value="gemini-out")
    mock_openai = MagicMock(return_value="openai-out")
    fake_dispatch = {
        "gemini": mock_gemini,
        "anthropic": mock_anthropic,
        "openai": mock_openai,
    }

    with patch.object(llm_router, "get_settings", return_value=_fake_settings()), \
         patch.object(llm_router, "_PROVIDER_DISPATCH", fake_dispatch):
        text = generate_for_task(
            task="cover_letter",  # would normally route Gemini reasoning tier
            prompt="hi",
            provider_override="anthropic",
        )

    assert text == "anthropic-out"
    mock_anthropic.assert_called_once()
    mock_gemini.assert_not_called()
    # Confirm the call carries the resolved tier model name (env-driven).
    call_kwargs = mock_anthropic.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-pro"


def test_provider_override_unknown_value_raises_value_error():
    """An unrecognized `provider_override` raises before any dispatch."""
    with patch.object(llm_router, "get_settings", return_value=_fake_settings()):
        with pytest.raises(ValueError, match="provider_override"):
            generate_for_task(
                task="cover_letter",
                prompt="hi",
                provider_override="bogus",
            )


# ---------------------------------------------------------------------------
# AC-15 — response_schema plumbed into Gemini (closes drift D-016)
# ---------------------------------------------------------------------------
def test_response_schema_reaches_gemini_generate_content_config():
    """`response_schema` lands in `types.GenerateContentConfig` when json_mode=True.

    Closes drift D-016 — `_call_gemini` previously dropped any schema the
    caller supplied; spec #52 §6 had mandated it but plumbing was absent.
    """
    captured: dict = {}

    fake_response = MagicMock(text='{"value":"ok"}')
    fake_genai = MagicMock()
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response
    fake_genai.Client.return_value = fake_client

    fake_types = MagicMock()

    def _capture_config(**kwargs):
        captured.update(kwargs)
        cfg = MagicMock()
        return cfg

    fake_types.GenerateContentConfig.side_effect = _capture_config

    with patch.object(llm_router, "get_settings", return_value=_fake_settings()), \
         patch.dict(
             "sys.modules",
             {
                 "google": MagicMock(genai=fake_genai),
                 "google.genai": fake_genai,
                 "google.genai.types": fake_types,
             },
         ):
        # Make `from google import genai` resolve to our mock genai.
        fake_genai.types = fake_types
        text = generate_for_task(
            task="card_draft",
            prompt="schema-test",
            json_mode=True,
            response_schema=_StubSchema,
        )

    assert text == '{"value":"ok"}'
    # Schema must be present in the GenerateContentConfig kwargs (the line
    # that closes D-016 in `_call_gemini`).
    assert captured.get("response_schema") is _StubSchema, (
        f"response_schema not plumbed; got config kwargs={list(captured.keys())}"
    )
    assert captured.get("response_mime_type") == "application/json"


def test_response_schema_without_json_mode_raises_value_error():
    """Passing `response_schema` without `json_mode=True` is a programmer error.

    Per D-15 close-shape: schema enforcement only makes sense when the
    provider has been told to emit JSON. Anything else is a footgun.
    """
    with pytest.raises(ValueError, match="json_mode"):
        generate_for_task(
            task="card_draft",
            prompt="oops",
            response_schema=_StubSchema,
            json_mode=False,
        )


def test_response_schema_threads_through_anthropic_dispatcher():
    """Anthropic dispatcher accepts `response_schema` (kwarg-compat for D-4)."""
    captured_kwargs: dict = {}

    def _capture(**kwargs):
        captured_kwargs.update(kwargs)
        return "anthropic-out"

    fake_dispatch = {
        "gemini": MagicMock(),
        "anthropic": _capture,
        "openai": MagicMock(),
    }

    with patch.object(llm_router, "get_settings", return_value=_fake_settings()), \
         patch.object(llm_router, "_PROVIDER_DISPATCH", fake_dispatch):
        text = generate_for_task(
            task="cover_letter",
            prompt="hi",
            json_mode=True,
            response_schema=_StubSchema,
            provider_override="anthropic",
        )

    assert text == "anthropic-out"
    assert captured_kwargs.get("response_schema") is _StubSchema, (
        f"response_schema not threaded to anthropic; got kwargs={list(captured_kwargs.keys())}"
    )


# ---------------------------------------------------------------------------
# Regression — existing call sites unaffected by additive params
# ---------------------------------------------------------------------------
def test_existing_call_sites_no_new_kwargs_route_to_gemini_as_before():
    """No-kwarg call shape (existing callers) still dispatches via env config."""
    mock_gemini = MagicMock(return_value="gemini-out")
    mock_anthropic = MagicMock()
    fake_dispatch = {
        "gemini": mock_gemini,
        "anthropic": mock_anthropic,
        "openai": MagicMock(),
    }

    with patch.object(llm_router, "get_settings", return_value=_fake_settings()), \
         patch.object(llm_router, "_PROVIDER_DISPATCH", fake_dispatch):
        text = generate_for_task(
            task="cover_letter",
            prompt="hello",
            json_mode=False,
            max_tokens=2048,
            temperature=0.5,
        )

    assert text == "gemini-out"
    mock_gemini.assert_called_once()
    mock_anthropic.assert_not_called()
    # The new kwargs are NOT passed when the caller didn't provide them —
    # protects existing services (cover_letter / card_draft / resume_rewrite)
    # from any signature surprise.
    call_kwargs = mock_gemini.call_args.kwargs
    assert "response_schema" not in call_kwargs
    assert call_kwargs.get("system_prompt") is None
    assert call_kwargs.get("model") == "gemini-2.5-pro"
