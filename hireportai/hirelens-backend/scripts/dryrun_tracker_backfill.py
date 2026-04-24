"""Dry-run the spec #57 tracker-interview-date backfill.

Runs the SAME selection logic as
``alembic/versions/eb59d4fc1f7e_backfill_tracker_interview_date_from_.py``
but emits a summary to stdout WITHOUT mutating any row. Intended to be
run immediately before ``alembic upgrade head`` so the operator knows
how many rows the backfill will touch.

Usage:
    source hirelens-backend/venv/bin/activate
    cd hirelens-backend
    DATABASE_URL=postgresql+asyncpg://... python scripts/dryrun_tracker_backfill.py

Output (example):
    --- spec #57 backfill dry-run ---
    users with interview_target_date set ..... 3
    would UPDATE existing tracker rows ....... 2
    would INSERT synthetic tracker rows ...... 1
    (no changes applied; run `alembic upgrade head` to apply)

Safety:
  - Read-only. Uses SELECT only.
  - Does not touch Stripe, PostHog, Redis, or anything outside PG.
"""
from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


COUNT_USERS_WITH_TARGET = text(
    """
    SELECT COUNT(*)
    FROM users
    WHERE interview_target_date IS NOT NULL;
    """
)

COUNT_WOULD_UPDATE = text(
    """
    WITH ranked AS (
        SELECT
            t.id,
            ROW_NUMBER() OVER (
                PARTITION BY t.user_id
                ORDER BY t.created_at DESC
            ) AS rn
        FROM tracker_applications_v2 t
        JOIN users u ON u.id = t.user_id
        WHERE u.interview_target_date IS NOT NULL
          AND t.status IN ('Applied', 'Interview')
          AND t.interview_date IS NULL
    )
    SELECT COUNT(*) FROM ranked WHERE rn = 1;
    """
)

COUNT_WOULD_INSERT = text(
    """
    SELECT COUNT(*)
    FROM users u
    WHERE u.interview_target_date IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM tracker_applications_v2 t
          WHERE t.user_id = u.id
            AND t.status IN ('Applied', 'Interview')
      );
    """
)


async def _main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print(
            "DATABASE_URL not set; export it before running "
            "(see hirelens-backend/.env for the local default).",
            file=sys.stderr,
        )
        return 2

    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            users_count = (await conn.execute(COUNT_USERS_WITH_TARGET)).scalar_one()
            update_count = (await conn.execute(COUNT_WOULD_UPDATE)).scalar_one()
            insert_count = (await conn.execute(COUNT_WOULD_INSERT)).scalar_one()
    finally:
        await engine.dispose()

    total_covered = int(update_count) + int(insert_count)
    print("--- spec #57 backfill dry-run ---")
    print(f"users with interview_target_date set ..... {users_count}")
    print(f"would UPDATE existing tracker rows ....... {update_count}")
    print(f"would INSERT synthetic tracker rows ...... {insert_count}")
    if users_count != total_covered:
        print(
            f"WARN: {users_count - total_covered} user(s) with a target date "
            "are not covered by either branch — investigate before "
            "running the migration.",
            file=sys.stderr,
        )
    print("(no changes applied; run `alembic upgrade head` to apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
