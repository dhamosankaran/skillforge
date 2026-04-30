"""Prompt-template loader (Phase 6 slice 6.10b — D-3).

Spec: docs/specs/phase-6/10-ai-ingestion-pipeline.md §6.5 + D-3.

Reads `app/prompts/<name>.md` once per process via `@functools.cache`. No
hot-reload, no version registry, no A/B variants — all future-slice scope
per §13. Pre-Phase-6 prompts inlined as f-strings stay where they are;
this module is only consumed by the ingestion worker today.
"""
from __future__ import annotations

import functools
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@functools.cache
def load_prompt(name: str) -> str:
    """Return the contents of `app/prompts/<name>.md`.

    Raises `FileNotFoundError` if the template is absent — the worker
    surfaces this to the job's `error_message` so admin can spot a typo.
    """
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
