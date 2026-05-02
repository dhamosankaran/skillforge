"""Tests for the cron CLI entry script (Phase 6 slice 6.14).

Spec: docs/specs/phase-6/14-daily-digest-cron.md §10.2 + §11 AC-2 + AC-18.

These tests exercise the script's boot sequence + JSON output without
running the full subprocess (avoids alembic-roundtrip + DB-engine
boot-cost in CI). The full subprocess invocation is verified at impl
time via shell smoke per §10.2.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.pro_digest import SendSummary
from app.scripts import send_pro_digest as cron_script


def test_script_main_returns_zero_on_clean_run(capsys):
    """AC-2 — script exits 0 + prints SendSummary JSON on clean run."""
    summary = SendSummary(
        sent=3,
        skipped_dedup=1,
        skipped_empty=2,
        failed=0,
        candidates_total=6,
        duration_seconds=0.42,
    )

    async def _fake_run() -> int:
        # Mimic the body of `_run` without booting an engine — the
        # production path is exercised by service tests; here we only
        # assert the exit-code + stdout shape contract.
        print(summary.model_dump_json())
        return 0

    with patch.object(cron_script, "_run", new=_fake_run):
        rc = cron_script.main()

    captured = capsys.readouterr()
    assert rc == 0
    assert '"sent":3' in captured.out
    assert '"candidates_total":6' in captured.out


def test_script_main_returns_one_on_fatal_exception(capsys):
    """Fatal-wrapper contract: any exception in _run → exit code 1."""
    async def _explode() -> int:
        raise RuntimeError("DB engine boot failed")

    with patch.object(cron_script, "_run", new=_explode):
        rc = cron_script.main()

    assert rc == 1


def test_script_module_exports_main_and_run():
    """AC-18 — script exposes `_run` async + `main` int-returning entry."""
    assert callable(cron_script.main)
    assert asyncio.iscoroutinefunction(cron_script._run)
