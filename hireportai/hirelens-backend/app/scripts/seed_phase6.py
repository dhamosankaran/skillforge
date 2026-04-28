"""Phase 6 seed-corpus bootstrap CLI.

Loads the canonical reference seed corpus from
``app/data/decks/seed_lessons/`` into the database.

Usage::

    python -m app.scripts.seed_phase6           # commit
    python -m app.scripts.seed_phase6 --dry-run # validate, no commit

Exit codes:
- ``0`` on success.
- ``1`` on validation error (Pydantic, slug mismatch, unexpected H2,
  duplicate question hash, missing _meta.md, etc.).
- ``2`` on operational/DB error.

Spec: docs/specs/phase-6/05-seed-lessons.md §6.2.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.services.seed_lessons_service import (
    SeedLoadError,
    SeedLoadReport,
    load_seed_corpus,
)

logger = logging.getLogger("seed_phase6")


def _format_report(report: SeedLoadReport) -> str:
    parts = [
        f"seed_root={report.seed_root}",
        f"dry_run={report.dry_run}",
        (
            f"decks created={report.decks.created} updated={report.decks.updated} "
            f"unchanged={report.decks.unchanged} skipped={report.decks.skipped_archived}"
        ),
        (
            f"lessons created={report.lessons.created} updated={report.lessons.updated} "
            f"unchanged={report.lessons.unchanged} skipped={report.lessons.skipped_archived}"
        ),
        (
            f"quiz_items created={report.quiz_items.created} "
            f"updated={report.quiz_items.updated} "
            f"unchanged={report.quiz_items.unchanged} "
            f"skipped={report.quiz_items.skipped_archived}"
        ),
        f"elapsed={(report.finished_at - report.started_at).total_seconds():.2f}s",
    ]
    return " | ".join(parts)


async def _run(dry_run: bool, seed_root: Path | None) -> int:
    from sqlalchemy.ext.asyncio import create_async_engine

    settings = get_settings()
    engine = create_async_engine(settings.async_database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with factory() as session:
            try:
                report = await load_seed_corpus(
                    session, dry_run=dry_run, seed_root=seed_root
                )
            except (ValidationError, SeedLoadError) as exc:
                logger.error("seed validation failed: %s", exc)
                return 1
    finally:
        await engine.dispose()

    logger.info("seed load complete: %s", _format_report(report))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="seed_phase6",
        description="Load the Phase 6 reference seed corpus into the database.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and emit SeedLoadReport without committing.",
    )
    parser.add_argument(
        "--seed-root",
        type=Path,
        default=None,
        help="Override the seed-corpus root directory (default: app/data/decks/seed_lessons).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        return asyncio.run(_run(dry_run=args.dry_run, seed_root=args.seed_root))
    except Exception:
        logger.exception("seed load failed with operational error")
        return 2


if __name__ == "__main__":
    sys.exit(main())
