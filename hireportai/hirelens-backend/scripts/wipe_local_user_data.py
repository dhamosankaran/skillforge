"""One-shot local dev DB wipe.

Deletes all user-generated data (users, subscriptions, tracker entries,
card progress, missions, gamification, email prefs, card feedback,
registration logs, stripe webhook events). Preserves:

  - content tables: cards (incl. embeddings), categories, badges
  - schema: every table stays, only rows are removed
  - migration history: alembic_version untouched

SAFETY:
  - Hard-fails if DATABASE_URL hostname is not in the local allowlist.
  - Requires --yes-i-mean-it to actually run DELETEs.
  - Wraps deletes in a single transaction; rollback on any error.

Usage:
    python scripts/wipe_local_user_data.py --yes-i-mean-it
"""
from __future__ import annotations

import argparse
import os
import sys
from urllib.parse import urlparse

import psycopg
from dotenv import load_dotenv

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "db", "postgres"}

# Deletion order: children first, parents last. Matches Step 2b of the
# slice plan. Every entry here is user-generated; content tables (cards,
# categories, badges) are intentionally absent.
DELETE_ORDER: tuple[str, ...] = (
    "mission_days",
    "mission_categories",
    "missions",
    "user_badges",
    "gamification_stats",
    "email_preferences",
    "card_feedback",
    "card_progress",
    "resumes",
    "usage_logs",
    "tracker_applications_v2",
    "payments",
    "subscriptions",
    "registration_logs",
    "stripe_events",
    "users",
)

CONTENT_TABLES: tuple[str, ...] = ("cards", "categories", "badges")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--yes-i-mean-it",
        action="store_true",
        help="Required. Confirms you understand this is destructive.",
    )
    return p.parse_args()


def normalize_url(url: str) -> str:
    """psycopg wants a plain libpq URL, not SQLAlchemy's `+asyncpg` dialect."""
    return url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


def require_local(url: str) -> None:
    host = urlparse(url).hostname or ""
    if host not in LOCAL_HOSTS:
        sys.stderr.write(
            f"REFUSING TO RUN: DATABASE_URL hostname {host!r} is not in the "
            f"local allowlist {sorted(LOCAL_HOSTS)}. This script is for "
            "local dev only.\n"
        )
        sys.exit(1)


def count_rows(cur: psycopg.Cursor, table: str) -> int:
    cur.execute(f"SELECT count(*) FROM {table}")
    row = cur.fetchone()
    return int(row[0]) if row else 0


def main() -> int:
    args = parse_args()
    if not args.yes_i_mean_it:
        sys.stderr.write("Refusing to run without --yes-i-mean-it.\n")
        return 1

    load_dotenv()
    raw_url = os.getenv("DATABASE_URL")
    if not raw_url:
        sys.stderr.write("DATABASE_URL not set.\n")
        return 1

    url = normalize_url(raw_url)
    require_local(url)

    parsed = urlparse(url)
    print(f"Target DB: {parsed.hostname}:{parsed.port or 5432}/"
          f"{(parsed.path or '').lstrip('/')}")

    with psycopg.connect(url, autocommit=False) as conn:
        with conn.cursor() as cur:
            print("\n--- Before ---")
            before = {t: count_rows(cur, t) for t in DELETE_ORDER}
            for t, n in before.items():
                print(f"  {t:30s} {n}")

            content_before = {t: count_rows(cur, t) for t in CONTENT_TABLES}
            print("\nContent (must be unchanged):")
            for t, n in content_before.items():
                print(f"  {t:30s} {n}")

            print("\n--- Deleting ---")
            total_deleted = 0
            try:
                for table in DELETE_ORDER:
                    cur.execute(f"DELETE FROM {table}")
                    n = cur.rowcount
                    total_deleted += n
                    print(f"  DELETE FROM {table:28s} -> {n} rows")

                print("\n--- After (pre-commit) ---")
                after = {t: count_rows(cur, t) for t in DELETE_ORDER}
                for t, n in after.items():
                    print(f"  {t:30s} {n}")

                content_after = {t: count_rows(cur, t) for t in CONTENT_TABLES}
                print("\nContent (must match before):")
                for t, n in content_after.items():
                    expected = content_before[t]
                    flag = "OK" if n == expected else "CHANGED"
                    print(f"  {t:30s} {n}  [{flag}]")

                if any(after[t] != 0 for t in DELETE_ORDER):
                    raise RuntimeError(
                        "Post-delete count not zero on at least one table; "
                        "rolling back."
                    )
                if content_after != content_before:
                    raise RuntimeError(
                        "Content-table counts changed; rolling back."
                    )

            except Exception:
                conn.rollback()
                raise

            conn.commit()

    print(
        f"\nWiped {total_deleted} rows across {len(DELETE_ORDER)} tables. "
        f"Content preserved: "
        f"{sum(content_before.values())} rows "
        f"({', '.join(f'{t}={n}' for t, n in content_before.items())})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
