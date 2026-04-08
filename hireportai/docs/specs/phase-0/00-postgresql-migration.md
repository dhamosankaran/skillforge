# SPEC: PostgreSQL + pgvector Migration

## Status: Done

## Problem
The backend currently runs on SQLite via `aiosqlite` with two parallel access
paths: the SQLAlchemy 2.0 async ORM and a raw-`aiosqlite` legacy tracker
(`app/db/database.py`, `app/services/tracker_service.py`). SQLite blocks the
roadmap in three concrete ways:
1. No `pgvector` — Phase-1 FSRS/embedding features cannot store or query
   vector embeddings at the database layer (today similarity is TF-IDF in
   Python under `app/services/nlp.py`, which does not scale).
2. Single-writer concurrency and `check_same_thread=False` workarounds make
   real concurrent FastAPI workloads unsafe in production.
3. Alembic migrations are forced into `render_as_batch=True` mode, which
   prevents normal `ALTER TABLE` evolution and complicates every future
   schema change.

## Solution
Move the canonical datastore to PostgreSQL 16 with the `pgvector` extension,
collapse the dual DB paths onto the SQLAlchemy ORM, and remove all
SQLite-specific shims. Introduce a single new Alembic migration that
(a) enables `CREATE EXTENSION vector` and (b) is the first migration authored
without batch mode. No new product features ship in this spec — it is a
pure infrastructure migration that unblocks Phase-1.

## Acceptance Criteria
- [ ] AC-1: Given a fresh developer machine with PostgreSQL 16 + pgvector
      installed via Homebrew, when they run
      `alembic upgrade head && uvicorn app.main:app --reload --port 8000`,
      then the app starts with zero SQLite references in logs and
      `GET /health` returns `{"status": "healthy", "service": "hireport-ai"}`
      with HTTP 200. (The health endpoint is `/health`, not `/healthz`.)
- [ ] AC-2: Given the configured DATABASE_URL points at PostgreSQL, when the
      Alembic upgrade runs, then `CREATE EXTENSION IF NOT EXISTS vector` has
      executed and all six existing tables (`users`, `subscriptions`,
      `payments`, `resumes`, `usage_logs`, `tracker_applications_v2`) exist
      with identical column names, types, nullability, uniques, and FKs to
      the SQLite schema produced by revision `49ffb3a3b5ae`.
- [ ] AC-3: Given the legacy raw-`aiosqlite` tracker code path, when this
      spec is complete, then `app/db/database.py`,
      `app/services/tracker_service.py`'s direct `aiosqlite.connect` calls,
      the `enable_sqlite_tracker` flag in `app/core/config.py`, and the
      `init_db()` call in `app/main.py` are all removed; tracker reads/writes
      go exclusively through `app/services/tracker_service_v2.py` which
      uses the `TrackerApplicationModel` ORM model backed by
      `tracker_applications_v2`.
- [ ] AC-4: Given `app/db/session.py`, when this spec is complete, then the
      `if "sqlite" in db_url` branch and `check_same_thread=False` are
      removed and the engine is created via `create_async_engine` with an
      `asyncpg` URL.
- [ ] AC-5: Given `alembic/env.py`, when this spec is complete, then
      `render_as_batch=True` is removed and a comment documents that future
      migrations target PostgreSQL.
- [ ] AC-6: Given `requirements.txt`, when this spec is complete, then
      `aiosqlite` is removed and `asyncpg>=0.29`, `psycopg[binary]>=3.1`
      (for Alembic sync use), and `pgvector>=0.3` are added and pinned.
- [ ] AC-7: Given the test suite, when `python -m pytest tests/ -v` runs
      against a disposable PostgreSQL test database, then all existing tests
      pass and the new integration tests in AC-8 pass.
- [ ] AC-8: Given a new `tests/conftest.py` providing an async PostgreSQL
      session fixture, when the new integration tests run, then they verify:
      a user can be inserted and read back, a `vector(3)` round-trips through
      a throwaway test table, and an FK violation on `subscriptions.user_id`
      raises `IntegrityError`.
- [ ] AC-9: Given an existing local SQLite database at `data/hirelens.db`,
      when the developer runs `python scripts/migrate_sqlite_to_postgres.py`,
      then all rows from the six tables are copied into PostgreSQL preserving
      UUIDs, timestamps, and FKs; the script is idempotent (re-run is a
      no-op) and prints a per-table row-count diff at the end.

## API Contract
No public HTTP API surface changes. All routes under `app/api/routes/` keep
their existing request/response Pydantic schemas. The only externally
observable change is the `DATABASE_URL` environment variable format:

- Before: `sqlite+aiosqlite:///data/hirelens.db`
- After:  `postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport`

`.env.example` is updated accordingly. `app/core/config.py`'s `database_url`
default is updated to the PostgreSQL URL above and the `enable_sqlite_tracker`
setting is deleted.

## Data Model Changes
**No business-column changes** in this spec. The six existing tables are
recreated 1:1 in PostgreSQL with the following type-mapping rules applied
during the new initial migration:

| SQLAlchemy type today      | PostgreSQL type in this migration | Notes                                       |
|----------------------------|------------------------------------|---------------------------------------------|
| `String` (with length)     | `VARCHAR(n)`                       |                                             |
| `String` (no length)       | `TEXT`                             |                                             |
| `Text`                     | `TEXT`                             |                                             |
| `Integer`                  | `INTEGER`                          |                                             |
| `Boolean`                  | `BOOLEAN`                          |                                             |
| `DateTime()` (naive)       | `TIMESTAMP WITHOUT TIME ZONE`      | Models use naive datetimes + `func.now()`; TIMESTAMPTZ promotion deferred to a follow-up spec. |
| `UUIDPrimaryKeyMixin.id`   | `VARCHAR(36)`                      | ORM field is `Mapped[str]`; native `UUID` promotion deferred to the same follow-up spec. |

> **Deferred:** Promoting IDs to native `UUID` and timestamps to `TIMESTAMPTZ`
> requires changing `UUIDPrimaryKeyMixin`, all model `Mapped[str]` id fields,
> and every `server_default`. That is out of scope for a pure infra swap and
> will be done in a dedicated Phase-0 follow-up spec so this PR stays
> reviewable in isolation.

Indexes/uniques carried over verbatim:
- `users.email` unique + index, `users.google_id` unique
- `subscriptions.user_id` unique, `subscriptions.stripe_customer_id` unique,
  `subscriptions.stripe_subscription_id` unique
- `payments.stripe_payment_intent_id` unique, `payments.user_id` index
- `resumes.user_id` index
- `usage_logs.user_id` index, `usage_logs.created_at` index
- `tracker_applications_v2.user_id` index (nullable FK preserved)

**New** in this migration:
- `CREATE EXTENSION IF NOT EXISTS vector;` at the top of the upgrade.
- No embedding columns are added yet — that is intentionally deferred to the
  first Phase-1 spec that actually consumes them, to keep this PR a pure
  infra swap.

### Alembic strategy
Because revision `49ffb3a3b5ae` was authored with `batch_alter_table` for
SQLite and a fresh PostgreSQL DB has no history, the cleanest path is:
1. Delete `49ffb3a3b5ae_initial_schema_users_subscriptions_.py`.
2. Hand-author a new initial migration
   `alembic/versions/0001_initial_postgres_pgvector.py` (revision ID
   `0001_pg_init`, `down_revision = None`) that:
   - Prepends `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` in
     `upgrade()`.
   - Creates all six tables with types matched to the current ORM models
     (i.e., `VARCHAR(36)` for ids, `TIMESTAMP WITHOUT TIME ZONE` for dates —
     not native `UUID`/`TIMESTAMPTZ`, which are deferred).
   - Has a matching `downgrade()` that drops tables in reverse FK order and
     ends with `op.execute("DROP EXTENSION IF EXISTS vector")`.
3. Remove `render_as_batch=True` from `alembic/env.py` and add a comment
   documenting that future migrations target PostgreSQL.

Autogenerate (`alembic revision --autogenerate`) is intentionally **not**
used for this initial migration: the ORM models still use `Mapped[str]` for
IDs and timezone-naive `DateTime`, so autogenerate would emit those types
verbatim rather than the correct PostgreSQL target types we want. Hand-
authoring the migration gives us precise control and serves as the canonical
reference for the six table schemas.

This is acceptable because there is no production data that has been migrated
through `49ffb3a3b5ae` — local dev SQLite data is handled by the one-shot
script in AC-9, not by Alembic.

## UI/UX
None. Frontend is unchanged.

## Edge Cases
- **Existing local SQLite data**: handled by
  `scripts/migrate_sqlite_to_postgres.py` (AC-9). Idempotency via
  `INSERT ... ON CONFLICT (id) DO NOTHING`.
- **`tracker_applications_v2.user_id` nullable**: preserved so unauthenticated
  tracker rows continue to work after the consolidation in AC-3.
- **Connection pool exhaustion under reload**: `create_async_engine` is
  configured with `pool_pre_ping=True` and `pool_size=5, max_overflow=10` to
  avoid `--reload` worker leaks during dev.
- **Timezone drift**: all `DateTime` columns are migrated as `TIMESTAMPTZ`;
  any naive `datetime.utcnow()` writes in services are audited and switched
  to `datetime.now(timezone.utc)` if found.
- **CI without PostgreSQL**: CI must spin up a PostgreSQL 16 + pgvector
  service container before `pytest` runs and set `TEST_DATABASE_URL` to
  point at it. Without that env var the integration tests auto-skip via
  `pytest.skip` so the CI job still passes for unit-only runs.
- **Alembic downgrade on a DB that other apps share**: `DROP EXTENSION vector`
  is gated behind `IF EXISTS` and a comment warning that running downgrade on
  a shared DB will break other consumers.

## Dependencies
- None. This is the first Phase-0 spec and unblocks every later spec that
  needs concurrent writes or vector search.
- External prereq: developer machine must have PostgreSQL 16 and the
  `pgvector` extension installed (Homebrew:
  `brew install postgresql@16 pgvector`). This is consistent with
  `CLAUDE.md`'s "No Docker for dev" rule.

## Test Plan
- **Unit tests**:
  - Existing `tests/test_nlp.py`, `tests/test_parser.py`, `tests/test_scorer.py`
    must continue to pass unchanged (they do not touch the DB).
  - New `tests/test_config.py`: asserts `settings.database_url` starts with
    `postgresql+asyncpg://` and that `enable_sqlite_tracker` no longer exists
    on the `Settings` class.

- **Integration tests** (new, require live PostgreSQL test DB):
  - New `tests/conftest.py` exposing:
    - `engine` fixture (session-scoped) that:
      - Creates an async engine pointed at `TEST_DATABASE_URL` (defaults to
        `postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport_test`).
      - Calls `pytest.skip` if the DB is unreachable, so unit tests still
        run on machines without a local Postgres instance.
      - Runs `CREATE EXTENSION IF NOT EXISTS vector` before schema creation.
      - Creates the schema via `Base.metadata.create_all` (not `alembic
        upgrade head`) so the fixture is fast and self-contained; the Alembic
        migration path is exercised by the manual verification steps below.
      - Drops all tables via `Base.metadata.drop_all` on teardown.
    - `db_session` fixture (function-scoped) wrapping each test in a session
      whose transaction is always rolled back on teardown — no `ON CONFLICT`
      needed between tests.
  - New `tests/test_db_smoke.py`:
    - `test_pgvector_extension_present`: queries
      `SELECT extname FROM pg_extension WHERE extname='vector'` and asserts
      one row.
    - `test_user_insert_roundtrip`: inserts a `User` row and reads it back
      via the ORM.
    - `test_subscription_fk_enforced`: inserting a `Subscription` with a
      bogus `user_id` raises `sqlalchemy.exc.IntegrityError`.
    - `test_vector_roundtrip`: creates a temp table
      `tmp_vec(id int, embedding vector(3))`, inserts `[1.0, 2.0, 3.0]`,
      reads it back via `embedding::text`, and asserts the result equals
      `"[1,2,3]"` (pgvector normalises floats with no trailing zeros). The
      temp table is session-scoped and dropped automatically by PostgreSQL.
  - New `tests/test_tracker_orm.py`: verifies the consolidated tracker path
    (post AC-3) via `tracker_service_v2`:
    - `test_unauthenticated_crud`: create / list / update / delete with
      `user_id=None` (unauthenticated rows).
    - `test_authenticated_scoped_crud`: create with a real `User` FK,
      assert the row is visible to that user's `get_applications` call,
      and assert it is **not** visible when querying with a different
      `user_id`.

- **Manual verification**:
  1. `brew services start postgresql@16` and confirm pgvector is loadable via
     `psql -c "CREATE EXTENSION vector;"` in a scratch DB.
  2. `createdb hireport && createuser hireport` matching the URL in
     `CLAUDE.md`.
  3. `cd hirelens-backend && source venv/bin/activate && pip install -r
     requirements.txt && alembic upgrade head`.
  4. Run `python scripts/migrate_sqlite_to_postgres.py` against an existing
     `data/hirelens.db` and confirm the printed row counts match
     `sqlite3 data/hirelens.db ".tables"` row counts.
  5. `uvicorn app.main:app --reload --port 8000` and hit `/health`,
     `/api/v1/users/me` (with a valid JWT), and one tracker route to confirm
     the consolidated tracker path works end-to-end.
  6. `python -m pytest tests/ -v --tb=short` — all green.
  7. `grep -ri sqlite hirelens-backend/app hirelens-backend/alembic` returns
     **zero** matches (sanity check for AC-3/AC-4/AC-5).
