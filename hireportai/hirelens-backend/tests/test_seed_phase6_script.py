"""Integration tests for the Phase 6 seed CLI script.

Spec: docs/specs/phase-6/05-seed-lessons.md §6.2, §10.2.

Marker-gated ``@pytest.mark.integration`` per slice 6.0 §10.1
precedent — the test shells out via ``subprocess`` and connects to the
real ``DATABASE_URL`` (test DB in CI / dev DB locally), so it is
deselected by default.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.models.deck import Deck
from app.models.lesson import Lesson


pytestmark = pytest.mark.integration


@pytest_asyncio.fixture(loop_scope="session")
async def clean_curriculum(db_session):
    """Truncate curriculum tables before+after each test."""

    async def _truncate() -> None:
        await db_session.execute(
            text(
                "TRUNCATE TABLE quiz_item_progress, quiz_items, lessons, decks "
                "RESTART IDENTITY CASCADE"
            )
        )
        await db_session.commit()

    await _truncate()
    try:
        yield db_session
    finally:
        await _truncate()


def _write_one_deck_corpus(root: Path) -> None:
    deck = root / "cli-test-deck"
    deck.mkdir(parents=True)
    (deck / "_meta.md").write_text(
        dedent(
            """\
            ---
            slug: cli-test-deck
            title: CLI Test Deck
            description: A deck for the CLI test.
            display_order: 0
            persona_visibility: both
            tier: foundation
            ---
            """
        ),
        encoding="utf-8",
    )
    (deck / "lesson-only.md").write_text(
        dedent(
            """\
            ---
            slug: lesson-only
            title: The Only Lesson
            display_order: 0
            quiz_items:
              - question: 'CLI Q?'
                answer: 'CLI A.'
                question_type: free_text
                difficulty: easy
                display_order: 0
            ---
            ## Concept
            Concept body.
            ## Production
            Production body.
            ## Examples
            Examples body.
            """
        ),
        encoding="utf-8",
    )


def _run_cli(seed_root: Path, *args: str) -> subprocess.CompletedProcess:
    """Invoke the CLI as a subprocess.

    Uses ``DATABASE_URL`` from the test environment (TEST_DATABASE_URL via
    ``app.core.config`` if set, otherwise the dev fallback).
    """
    backend_dir = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    test_db = env.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport_test",
    )
    env["DATABASE_URL"] = test_db
    env["PYTHONPATH"] = str(backend_dir)
    env["SEED_ROOT_OVERRIDE"] = str(seed_root)

    return subprocess.run(
        [sys.executable, "-m", "app.scripts.seed_phase6", *args],
        cwd=str(backend_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_seed_phase6_cli_dry_run(clean_curriculum, tmp_path: Path) -> None:
    _write_one_deck_corpus(tmp_path)
    proc = _run_cli(tmp_path, "--dry-run", "--seed-root", str(tmp_path))
    assert proc.returncode == 0, proc.stderr

    decks = (await clean_curriculum.execute(select(Deck))).scalars().all()
    assert decks == []


@pytest.mark.asyncio(loop_scope="session")
async def test_seed_phase6_cli_happy_path(clean_curriculum, tmp_path: Path) -> None:
    _write_one_deck_corpus(tmp_path)
    proc = _run_cli(tmp_path, "--seed-root", str(tmp_path))
    assert proc.returncode == 0, proc.stderr

    decks = (await clean_curriculum.execute(select(Deck))).scalars().all()
    assert len(decks) == 1
    lessons = (await clean_curriculum.execute(select(Lesson))).scalars().all()
    assert len(lessons) == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_seed_phase6_cli_validation_error_exit_nonzero(
    clean_curriculum, tmp_path: Path
) -> None:
    _write_one_deck_corpus(tmp_path)
    meta = (tmp_path / "cli-test-deck" / "_meta.md").read_text(encoding="utf-8")
    meta = meta.replace("tier: foundation", "tier: bogus")
    (tmp_path / "cli-test-deck" / "_meta.md").write_text(meta, encoding="utf-8")

    proc = _run_cli(tmp_path, "--seed-root", str(tmp_path))
    assert proc.returncode != 0
    assert "validation" in proc.stderr.lower() or "validation" in proc.stdout.lower()
