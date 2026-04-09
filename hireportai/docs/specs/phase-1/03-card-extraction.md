# SPEC: Card Data Model + JSX Extraction

## Status: Draft

## Problem
177 study cards are hardcoded in JSX files. This blocks FSRS scheduling (which requires server-side state per user per card), semantic search (which requires embeddings stored in PostgreSQL + pgvector), and any admin CRUD workflow. Until cards live in the database, all Phase 1 study features are unbuildable.

## Solution
Extract cards from JSX source files using a one-off Python script (`scripts/extract_cards.py`). Insert them into a `cards` table with a companion `categories` table. After insertion, generate embeddings for each card via the Gemini API and store them in a `pgvector` column. This is a data migration, not a user-facing feature — no API routes or UI changes are needed in this spec.

## Acceptance Criteria
- [ ] AC-1: Running `python scripts/extract_cards.py` inserts exactly 177 rows into the `cards` table with no duplicates (idempotent on re-run).
- [ ] AC-2: Every card row has a non-null `embedding` vector after the script completes.
- [ ] AC-3: Every card belongs to a valid `category_id` referencing a row in the `categories` table.
- [ ] AC-4: `SELECT count(*) FROM cards` returns 177 in the seeded local and Railway dev databases.
- [ ] AC-5: `SELECT count(*) FROM cards WHERE embedding IS NULL` returns 0.

## API Contract
None — this spec is purely a data migration. No new endpoints.

## Data Model Changes

### Table: `categories`
| Column       | Type          | Constraints                  |
|--------------|---------------|------------------------------|
| `id`         | `UUID`        | PK, default gen_random_uuid()|
| `name`       | `TEXT`        | NOT NULL, UNIQUE             |
| `slug`       | `TEXT`        | NOT NULL, UNIQUE             |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, default now()      |

**Indexes:**
- Primary key on `id`
- Unique index on `slug` (used for idempotent upserts in the extraction script)

---

### Table: `cards`
| Column        | Type             | Constraints                              |
|---------------|------------------|------------------------------------------|
| `id`          | `UUID`           | PK, default gen_random_uuid()            |
| `category_id` | `UUID`           | NOT NULL, FK → categories(id)            |
| `question`    | `TEXT`           | NOT NULL                                 |
| `answer`      | `TEXT`           | NOT NULL                                 |
| `difficulty`  | `SMALLINT`       | NOT NULL, CHECK (difficulty IN (1,2,3))  |
| `tags`        | `TEXT[]`         | NOT NULL, default '{}'                   |
| `embedding`   | `vector(1536)`   | NULL (populated post-insert)             |
| `created_at`  | `TIMESTAMPTZ`    | NOT NULL, default now()                  |
| `updated_at`  | `TIMESTAMPTZ`    | NOT NULL, default now()                  |

**Difficulty encoding:** 1 = easy, 2 = medium, 3 = hard (matches JSX source labels).

**Indexes:**
- Primary key on `id`
- Index on `category_id` (for category-filtered queries)
- `ivfflat` index on `embedding vector_cosine_ops` with `lists = 10` (enables pgvector ANN search; requires at least 177 rows, so created after seeding)

**Alembic notes:**
- Requires `pgvector` extension to be enabled (`CREATE EXTENSION IF NOT EXISTS vector` — already present from Phase 0 migration).
- Two migrations: one for `categories` + `cards` DDL, one for the ivfflat index (index must be created after data is loaded).

---

## Extraction Script Approach (`scripts/extract_cards.py`)

The script runs outside the FastAPI app in a standalone `asyncio` context using the same `DATABASE_URL` from the environment.

**Steps:**
1. **Parse JSX** — walk `hirelens-frontend/src/` for files containing hardcoded card arrays. Use Python `re` to extract objects matching the shape `{ question, answer, category, difficulty, tags }`. No AST parser needed at this scale; a regex over the known structure is sufficient.
2. **Seed categories** — collect the unique category names found during parsing. `INSERT … ON CONFLICT (slug) DO NOTHING` so re-runs are safe.
3. **Seed cards** — for each extracted card, resolve `category_id` from the in-memory map, then `INSERT … ON CONFLICT DO NOTHING` (conflict key: `(question, category_id)`).
4. **Generate embeddings** — fetch all cards where `embedding IS NULL`. Call `google-genai` `embed_content` (model: `models/text-embedding-004`, 1536 dims) in batches of 20 to respect rate limits. `UPDATE cards SET embedding = :vec WHERE id = :id`.
5. **Print summary** — log inserted card count, skipped (already existed), and any embedding failures.

**Idempotency:** Every insert uses `ON CONFLICT DO NOTHING`, so running the script twice produces the same final state.

**Environment:** Script reads `DATABASE_URL` and `GEMINI_API_KEY` from the environment (same `.env` used by the backend). No changes to `app/` code.

## UI/UX
None — data migration only.

## Edge Cases
- Cards whose `question` text contains JSX interpolations (template literals, ternaries) are logged as warnings and skipped; a manual fallback entry is added for each.
- If the Gemini API returns an error for a batch, the script logs the card IDs and continues; the operator re-runs the script to fill remaining nulls.
- Re-running after partial failure is safe due to `ON CONFLICT DO NOTHING` on insert and `WHERE embedding IS NULL` on the embedding pass.

## Dependencies
- Spec #00 (PostgreSQL + pgvector) — complete
- Spec #03 (User roles / admin) — complete (no dependency on auth for this script)
- `pgvector` extension enabled in Railway dev DB — verified in Phase 0

## Test Plan

**Count verification (integration, run against local DB after seeding):**
- `SELECT count(*) FROM cards` = 177
- `SELECT count(DISTINCT category_id) FROM cards` = expected number of categories (to be confirmed during parsing)
- `SELECT count(*) FROM categories` = matches distinct category count

**Embedding non-null check (integration):**
- `SELECT count(*) FROM cards WHERE embedding IS NULL` = 0

**Idempotency check (manual):**
- Run `extract_cards.py` twice; confirm second run logs 0 inserted, 177 skipped, no errors.

**Dimension check (unit test in `tests/test_card_extraction.py`):**
- Mock the Gemini client; assert the vector stored for a single card has exactly 1536 dimensions.

**Regression (manual):**
- Confirm existing auth and scan endpoints still return 200 after migrations are applied.
