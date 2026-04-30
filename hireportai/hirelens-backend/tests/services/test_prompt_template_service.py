"""Prompt template loader tests (Phase 6 slice 6.10b)."""
from __future__ import annotations

import pytest

from app.services import prompt_template_service
from app.services.prompt_template_service import load_prompt


def setup_function(_):
    # Each test starts with a clean cache so cache-hit assertions are stable.
    load_prompt.cache_clear()


def test_load_prompt_returns_template_body():
    body = load_prompt("lesson_gen")
    assert "LessonGenSchema" in body
    assert "{source_markdown}" in body


def test_load_prompt_caches_after_first_read(monkeypatch):
    # Prime cache.
    first = load_prompt("ingestion_critique")
    info_before = load_prompt.cache_info()

    # A second call must NOT touch the filesystem — patch read_text to raise
    # so a cache miss would fail the test.
    real_read_text = prompt_template_service._PROMPTS_DIR.__class__.read_text

    def _explode(*_args, **_kwargs):
        raise AssertionError("cache miss — load_prompt should not re-read")

    monkeypatch.setattr(
        "pathlib.Path.read_text", _explode
    )
    second = load_prompt("ingestion_critique")
    assert second == first
    info_after = load_prompt.cache_info()
    assert info_after.hits == info_before.hits + 1
    # Restore is automatic via monkeypatch teardown.
    _ = real_read_text


def test_load_prompt_unknown_template_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_prompt("nonexistent-template-xyz")
