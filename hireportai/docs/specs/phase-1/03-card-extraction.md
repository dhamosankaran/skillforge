# SPEC: Card Data Model + JSX Extraction

## Status: Partially Done — gaps to close in P1-S1

Most of this slice was built during Phase 0 scaffolding. This spec rewrite re-baselines against reality, enumerates what remains, and defines the acceptance criteria for closing out P1-S1.

## Problem
Study cards currently live in a prototype JSX source (`archive/prototype/src/data/cards.js` — 15 cards across 14 categories). They must move to PostgreSQL with pgvector embeddings so that Phase 1 can:

1. Schedule per-user review via FSRS (requires server-side card rows + per-user progress join).
2. Support semantic card search over the embedding column.
3. Power the ATS gap-mapping feature that maps missing resume skills to categories via tags.
4. Enable admin CRUD with soft-delete (so deletes don't orphan `card_progress` rows).

Until every one of those preconditions is satisfied in the database (not just "tables exist"), downstream Phase 1 slices are blocked.

## Solution
- `Card` and `Category` SQLAlchemy ORM models with soft-delete (`Card.deleted_at`).
- Alembic migrations for the tables, `cards.deleted_at`, `categories.tags` (new), and the pgvector ANN index.
- `scripts/extract_cards.py` parses the JSX source via a Node subprocess and seeds both tables idempotently.
- `scripts/generate_embeddings.py` populates `cards.embedding` via the Gemini embedding model, with a deterministic synthetic fallback for CI / offline dev.

All embedding / LLM calls in new code must go through `generate_for_task()` in `app/core/llm_router.py`. The existing script predates the router and uses the Gemini client directly; that is grandfathered for this one script but new code must not follow the same pattern.

## Acceptance Criteria

- **AC-1 — Seed count (Given/When/Then)**
  - **Given** a freshly migrated empty database
  - **When** an operator runs `python scripts/extract_cards.py`
  - **Then** `SELECT count(*) FROM cards` equals the number of cards in `archive/prototype/src/data/cards.js` (currently 15) and `SELECT count(*) FROM categories` equals the number of distinct categories in that file (currently 14).

- **AC-2 — Idempotent re-run**
  - **Given** a database that has already been seeded by `extract_cards.py`
  - **When** the operator runs the script a second time with no source changes
  - **Then** the script completes without error, inserts 0 new rows, reports `skipped` counts equal to the first run's `inserted` counts, and leaves `cards` / `categories` row counts unchanged.

- **AC-3 — Every card has an embedding**
  - **Given** a database that has been seeded with cards
  - **When** `python scripts/generate_embeddings.py` finishes successfully
  - **Then** `SELECT count(*) FROM cards WHERE embedding IS NULL` returns 0, and `SELECT vector_dims(embedding) FROM cards LIMIT 1` returns `1536`.

- **AC-4 — Soft-delete filter is respected**
  - **Given** a card row with `deleted_at` set to a non-null timestamp
  - **When** a service layer query uses the canonical "active cards" filter (`WHERE deleted_at IS NULL`)
  - **Then** the soft-deleted card is excluded from the result set, even though the underlying row still exists and its `card_progress` children are untouched.

- **AC-5 — ANN index is used**
  - **Given** a seeded + embedded `cards` table
  - **When** the post-seed ANN index migration is applied and `EXPLAIN (ANALYZE, BUFFERS) SELECT … ORDER BY embedding <=> :query LIMIT 10` is run
  - **Then** the plan uses the pgvector index (HNSW or IVFFlat) rather than a sequential scan.

- **AC-6 — Category tags present for gap mapping**
  - **Given** the P1-S1 migration that adds `categories.tags`
  - **When** `extract_cards.py` seeds categories
  - **Then** every category row has a non-null JSON `tags` array (may be empty), so the ATS gap-mapping feature in P1-S13 can populate / read it without a schema change.

## API Contract
None — this spec is data-layer + one-off scripts. No HTTP routes are added or changed here. The user-facing read API for cards is covered by spec `04-cards-api.md`.

## Data Model

### Table: `cards` (exists)

| Column        | Type              | Notes                                           |
|---------------|-------------------|-------------------------------------------------|
| `id`          | `String(36)`      | PK, deterministic UUID5 from `(category, question)` |
| `category_id` | `String(36)`      | FK → `categories.id` `ON DELETE RESTRICT`       |
| `question`    | `Text`            | NOT NULL                                        |
| `answer`      | `Text`            | NOT NULL                                        |
| `difficulty`  | `String(10)`      | NOT NULL — stores source labels (`Easy`/`Medium`/`Hard`) |
| `tags`        | `JSON`            | NOT NULL, default `[]`                          |
| `embedding`   | `Vector(1536)`    | NULL until `generate_embeddings.py` runs        |
| `deleted_at`  | `DateTime(tz)`    | NULL = active                                   |
| `created_at`  | `DateTime`        | default `now()`                                 |
| `updated_at`  | `DateTime`        | default `now()`, updated on write               |

Source of truth: `app/models/card.py`. Migrations: `9bb18657d55d_add_cards_and_categories_tables.py` + `b1674f79f780_add_cards_deleted_at_for_soft_delete.py`.

### Table: `categories` (exists — **needs one new column**)

| Column          | Type          | Notes                                    |
|-----------------|---------------|------------------------------------------|
| `id`            | `String(36)`  | PK, deterministic UUID5 from name         |
| `name`          | `String(100)` | NOT NULL, UNIQUE                          |
| `icon`          | `String(10)`  | NOT NULL — emoji                          |
| `color`         | `String(30)`  | NOT NULL — hex string for prototype UI    |
| `display_order` | `Integer`     | NOT NULL, default 0                       |
| `source`        | `String(50)`  | NULL — e.g. `foundation`                  |
| **`tags`**      | **`JSON`**    | **NEW — NOT NULL, default `[]`. Used by ATS gap-mapping to match missing resume skills to a category.** |

Source of truth: `app/models/category.py`. The `tags` column is **not yet in the codebase** and must be added in this slice via a new Alembic migration (`add_categories_tags_for_gap_mapping`).

## Indexes

| Index | Status | Notes |
|-------|--------|-------|
| PK on `cards.id`, `categories.id` | ✅ exists | From `9bb18657d55d` |
| `ix_cards_category_id` | ✅ exists | From `9bb18657d55d` |
| Unique on `categories.name` | ✅ exists | From `9bb18657d55d` |
| **ANN index on `cards.embedding`** | ❌ **TODO** | Create **after** seeding + embedding generation. **Prefer HNSW** (`USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)`) since pgvector ≥ 0.5.0 is available in the Phase 0 Postgres 16 stack; fall back to `ivfflat (lists=10)` only if HNSW is unavailable. Put in its own migration so it can be rebuilt later without touching DDL. |
| **Partial index `WHERE deleted_at IS NULL`** | ❌ **TODO** | `CREATE INDEX ix_cards_active ON cards (category_id) WHERE deleted_at IS NULL` — keeps the hot "active cards per category" query off the dead rows. |

## Extraction Script (`scripts/extract_cards.py`) — verify, don't rebuild

The script is already implemented and currently works. Verify during P1-S1 that it still meets the following contract; only patch if one of these drifts:

1. **Source** — reads `archive/prototype/src/data/cards.js` via a Node 18+ dynamic import subprocess (pure-Python regex parsing is out of scope — the JSX uses template literals and re-exports).
2. **IDs are deterministic** — `uuid5(NAMESPACE_URL, "category:<name>")` and `uuid5(NAMESPACE_URL, "card:<category>:<question[:200]>")`. This is what makes `ON CONFLICT (id) DO NOTHING` give AC-2.
3. **Inserts** — one pass for categories, one pass for cards, both with `ON CONFLICT (id) DO NOTHING`.
4. **Summary output** — prints `inserted` / `skipped` counts per table and a per-category breakdown; exits non-zero if the final `NULL embedding` count is unexpected.
5. **P1-S1 delta** — once `categories.tags` is added, the script must seed the new column (empty array for cards.js categories today; real values arrive in P1-S13).

## Embedding Script (`scripts/generate_embeddings.py`) — verify, don't rebuild

Already implemented. Contract to preserve:

1. Uses `gemini-embedding-exp-03-07` with `output_dimensionality=1536`.
2. Probes the Gemini API once at startup; on missing/invalid `GEMINI_API_KEY`, falls back to a deterministic SHA-256-seeded synthetic embedding. This is what lets CI seed embeddings without a live key.
3. Idempotent: `SELECT … WHERE embedding IS NULL` — only fills gaps.
4. Batch size 20 with a 0.5s sleep between batches when hitting the real API.
5. Exits non-zero if any card is still NULL at the end.

New LLM calls anywhere else must go through `app/core/llm_router.py` (`generate_for_task(task=…)`) — this script is the only embedding caller grandfathered in.

## Edge Cases

1. **Duplicate card ID in `cards.js`** — two entries with the same `(category_name, question)` produce the same UUID5. The second `INSERT` is absorbed by `ON CONFLICT (id) DO NOTHING`; the summary prints one `inserted` and one `skipped`. Log a warning (not an error) — collisions usually mean duplicated prototype content, not data loss.

2. **Embedding generation fails for one card** — `generate_embeddings.py` already continues on per-batch exceptions and counts `errors`. The script exits non-zero at the end if any row is still NULL, so CI fails loudly and re-running fills only the missing rows (because of the `WHERE embedding IS NULL` filter).

3. **Card references an unknown category** — shouldn't happen since the script seeds categories first from the same JSX object and resolves `category_id` from the in-memory map. If the JSX ever decouples the two lists, the card INSERT will fail the FK (`ON DELETE RESTRICT`) and the whole transaction rolls back; the operator sees a clear FK violation rather than half-seeded state. We rely on that behavior — do not soften the FK.

4. **`deleted_at` not filtered** — an admin soft-deletes a card but a query forgets the `WHERE deleted_at IS NULL` clause. Mitigations: (a) the partial index above makes the "right" query path faster so it becomes the default, and (b) AC-4 is enforced by an explicit test.

5. **Source file missing** — `extract_cards.py` already hard-exits with the expected path in the error message; tests should not try to cover this path (environmental).

## Test Plan

| Test | Type | Status | Notes |
|------|------|--------|-------|
| `tests/test_card_extraction.py::test_cards_seeded` | integration | ✅ exists | Marked `@pytest.mark.integration`; runs against dev DB |
| `test_categories_seeded` | integration | ✅ exists | Same file |
| `test_all_cards_have_embeddings` | integration | ✅ exists | Same file |
| `test_embedding_dimensionality` | integration | ✅ exists | Asserts 1536 dims |
| **Unit test for `cat_uuid` / `card_uuid` determinism** | unit | ❌ **TODO** | Import from `scripts.extract_cards`; assert the same inputs always produce the same UUID; assert namespace is `NAMESPACE_URL`. No DB touch — lives in the CI subset. |
| **Unit test for `_synthetic_embedding`** | unit | ❌ **TODO** | Assert length = 1536, unit-norm (L2 ≈ 1.0), deterministic for the same input, different for different inputs. No DB, no network — lives in the CI subset. |
| **Soft-delete filter test** | integration or model-level | ❌ **TODO** | Insert two cards, set `deleted_at` on one, assert the canonical active-card query returns exactly one. Uses the test DB (`TEST_DATABASE_URL`), not the dev DB, so it does **not** need the `integration` marker. |
| **HNSW/IVFFlat index presence** | integration | ❌ **TODO** | After the new migration, `SELECT indexname FROM pg_indexes WHERE tablename='cards'` must include the ANN index. Integration-marked because it depends on the dev DB state. |

CI subset (`-m "not integration"`) must stay green after this slice: the two unit tests and the soft-delete filter test all live in that subset.

## Work Remaining — split into P1-S1a and P1-S1b

Original single-slice scope (7 items) was estimated at 55–70 min, exceeding the 30-min slice budget. Split along theme:
- **P1-S1a** addresses items 1-2-4 plus the soft-delete filter test.
- **P1-S1b** addresses items 3-5 plus the ANN-index EXPLAIN check test.

### P1-S1a — Schema closeout + soft-delete filter test (~25–30 min)

In execution order (one commit for the slice):

1. **Add `Category.tags` JSON column** — update `app/models/category.py` and generate Alembic migration `add_categories_tags_for_gap_mapping`; default server-side to `'[]'::json`.
2. **Patch `extract_cards.py`** to populate `tags=[]` (or a mapped value if cards.js ever grows one) in the category INSERT.
3. **Add partial index migration** — `create_cards_active_partial_index` on `(category_id) WHERE deleted_at IS NULL`.
4. **Soft-delete filter integration test** — insert two cards, set `deleted_at` on one, assert the canonical active-card query returns exactly one. Lives in the CI subset (uses `TEST_DATABASE_URL`, no `integration` marker).
5. **Run `pytest -m "not integration"` and then `pytest -m integration`** locally; both must pass before closing the slice.

### P1-S1b — ANN index + extraction unit tests (~25–30 min)

In execution order (one commit for the slice):

1. **Version-check pgvector** at start of slice: `SELECT extversion FROM pg_extension WHERE extname='vector'`. If ≥ 0.5.0 use HNSW; else fall back to IVFFlat.
2. **Add ANN index migration** — `create_cards_embedding_hnsw_index` (or `…_ivfflat_…` depending on version). After-seed safe; idempotent via `IF NOT EXISTS`.
3. **UUID5 determinism unit test** — import `cat_uuid` / `card_uuid` from `scripts.extract_cards`; assert determinism + namespace. No DB, CI subset.
4. **`_synthetic_embedding` unit test** — assert length 1536, unit-norm, deterministic for same input, different for different inputs. No DB, CI subset.
5. **ANN-index EXPLAIN check** (integration test) — assert `pg_indexes` lists the new ANN index and that `EXPLAIN` uses it for a cosine-distance query.
6. **Run `pytest -m "not integration"` and then `pytest -m integration`** locally; both must pass before closing the slice.

### Post-slice

- Update `SESSION-STATE.md` to mark S1a / S1b complete as each lands (already advanced from P0-S7 → P1-S1a in the current session).

## Dependencies
- Phase 0 PostgreSQL + pgvector migration — ✅ complete.
- `archive/prototype/src/data/cards.js` — present in repo.
- `GEMINI_API_KEY` — optional for local dev (synthetic fallback); required in the environment where we want real semantic embeddings before Phase 1 UX work.

## Out of Scope (explicitly)
- The 177-card authored deck (the old spec referenced this). Real content authoring happens after P1 UX lands, not in this data slice.
- Admin CRUD UI for cards / categories — covered by the admin routes registered at `/api/v1/admin` in later slices.
- ATS gap-mapping logic itself — this slice only adds the `categories.tags` column the mapping will read.
