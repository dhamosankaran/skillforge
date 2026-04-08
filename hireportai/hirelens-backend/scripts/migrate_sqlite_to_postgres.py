"""Copy rows from a legacy SQLite hirelens.db into the new PostgreSQL DB.

Usage:
    python scripts/migrate_sqlite_to_postgres.py \
        --sqlite data/hirelens.db \
        --pg postgresql://hireport:dev_password@localhost:5432/hireport

The script is idempotent: re-running it is a no-op because every INSERT
uses ``ON CONFLICT (id) DO NOTHING``. It prints a per-table row-count
diff at the end so you can sanity-check the copy.

Run *after* ``alembic upgrade head`` against the PG database. The script
intentionally uses a synchronous psycopg connection to keep the script
self-contained and free of asyncio surprises.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from typing import Iterable, Sequence

import psycopg

# Order matters: parents before children (FK constraints).
TABLES: Sequence[tuple[str, tuple[str, ...]]] = (
    (
        "users",
        ("id", "google_id", "email", "name", "avatar_url", "created_at"),
    ),
    (
        "subscriptions",
        (
            "id",
            "user_id",
            "plan",
            "status",
            "stripe_customer_id",
            "stripe_subscription_id",
            "current_period_end",
            "created_at",
            "updated_at",
        ),
    ),
    (
        "payments",
        (
            "id",
            "user_id",
            "stripe_payment_intent_id",
            "amount",
            "currency",
            "status",
            "created_at",
        ),
    ),
    (
        "resumes",
        (
            "id",
            "user_id",
            "original_content",
            "optimized_content",
            "template_type",
            "created_at",
            "updated_at",
        ),
    ),
    (
        "usage_logs",
        ("id", "user_id", "feature_used", "tokens_consumed", "created_at"),
    ),
    (
        "tracker_applications_v2",
        (
            "id",
            "user_id",
            "company",
            "role",
            "date_applied",
            "ats_score",
            "status",
            "created_at",
        ),
    ),
)


def _sqlite_rows(sq: sqlite3.Connection, table: str, cols: Sequence[str]) -> Iterable[tuple]:
    col_list = ", ".join(cols)
    cur = sq.execute(f"SELECT {col_list} FROM {table}")
    yield from cur.fetchall()


def _table_exists(sq: sqlite3.Connection, table: str) -> bool:
    row = sq.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _pg_count(pg: psycopg.Connection, table: str) -> int:
    with pg.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        return cur.fetchone()[0]


def migrate(sqlite_path: str, pg_url: str) -> int:
    sq = sqlite3.connect(sqlite_path)
    sq.row_factory = sqlite3.Row

    pg = psycopg.connect(pg_url)
    try:
        for table, cols in TABLES:
            if not _table_exists(sq, table):
                print(f"  - {table}: not in sqlite, skipping")
                continue

            before = _pg_count(pg, table)
            placeholders = ", ".join(["%s"] * len(cols))
            col_list = ", ".join(cols)
            insert_sql = (
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
                f"ON CONFLICT (id) DO NOTHING"
            )

            rows = list(_sqlite_rows(sq, table, cols))
            if rows:
                with pg.cursor() as cur:
                    cur.executemany(insert_sql, rows)
            pg.commit()

            after = _pg_count(pg, table)
            print(f"  - {table}: sqlite={len(rows)}  pg {before} -> {after}")
    finally:
        sq.close()
        pg.close()

    print("Done.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", default="data/hirelens.db")
    parser.add_argument(
        "--pg",
        default="postgresql://hireport:dev_password@localhost:5432/hireport",
        help="Sync psycopg URL (no +asyncpg).",
    )
    args = parser.parse_args(argv)
    return migrate(args.sqlite, args.pg)


if __name__ == "__main__":
    sys.exit(main())
