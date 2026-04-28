# Phase 6 — Slice 6.4.5: Reference Seed Lessons + Bootstrap Loader

## Status: Drafted, not shipped — §12 amended at `<this-slice>` locking D-1..D-10 from §14 OQ-1..OQ-10; impl row filed at `B-071` 🔴

| Field | Value |
|-------|-------|
| Phase | 6 (Curriculum Platform) |
| Slice | 6.4.5 — reference seed lessons + bootstrap loader |
| Mode | 4 (spec-author) |
| Author HEAD | `342b5e1` (post-slice-6.0 implementation SHA backfill) |
| Spec authored | 2026-04-27 |
| Implementation slice | TBD (one-step follow-up to this spec). Will file `B-071` close-line. |
| BACKLOG row | `B-071` filed at status 🔴 by this spec slice for the future implementation slice (per R15(c) + R17). |
| Audit dependency | `docs/audits/phase-6-scout.md` slice 6.1 lock note (line 901: "The 12 locked decks become seed data via either (a) Alembic data migration, (b) `scripts/seed_phase6_decks.py`, or (c) a one-time admin import. No in-repo seed-data convention today; lock it") + Q8 (line 1117) + R-1. |
| Slice dependencies | **Upstream:** slice 6.1 (`decks` / `lessons` / `quiz_items` tables — shipped at `a989539`); slice 6.4b-1 (admin write schemas `DeckCreateRequest` / `LessonCreateRequest` / `QuizItemCreateRequest` + `lesson_service.py` DB-backed body swap with `selectinload` per D-15 — shipped at `d6bda3b`). **Downstream:** slice 6.5 (lesson-UX read-time invariants — needs real seeded content); slice 6.7 / 6.12 (persona Learn page composition — needs real seeded content); slice 6.10 (AI ingestion pipeline — replaces this slice's bootstrap loader for net-new content but does NOT supersede the seed corpus itself). |

### Phase 6 locked decisions referenced by this spec

> Recorded in front-matter so spec readers see the locks without
> chasing SESSION-STATE. Rationale lives in §12 (Decisions) — D-1..D-10
> locked at §12 amendment `<this-slice>` from §14 OQ-1..OQ-10.

| ID | Decision |
|----|----------|
| **H1** | Object storage: Cloudflare R2 for ingestion artifacts (slice 6.10); **`hirelens-backend/app/data/decks/seed_lessons/*.md` for the 12 locked-deck seeds (this slice — 6.4.5)**. |
| **G2** | Background jobs: RQ on Redis for ingestion (slice 6.10); Railway cron for daily Pro digest (slice 6.14). Out of scope here — this slice ships an ops-only one-shot loader, not a recurring job. |

---

## 1. Problem

Phase 6 schema (slice 6.1) shipped four empty tables — `decks`,
`lessons`, `quiz_items`, `quiz_item_progress`. Phase 6 admin authoring
CRUD (slice 6.4b) shipped the BE + FE write surface for hand-edited
content. Both slices ship without **content** — there is no curriculum
on disk to read, study, or test downstream slices against.

Slice 6.5 (lesson-UX read-time invariants), slice 6.7 / 6.12 (persona
Learn page composition), and slice 6.10's ingestion pipeline (which
generates *new* content but assumes the existence of the canonical 12
locked decks as seed targets) all need a populated database to be
meaningfully testable end-to-end. Today, the only way to populate
anything is to manually click through the slice-6.4b admin authoring
UI for every deck + lesson + quiz_item — slow, error-prone, and not
reproducible across environments (dev, CI, staging, prod).

LD **H1** commits to filesystem-based markdown seeds living at
`hirelens-backend/app/data/decks/seed_lessons/*.md`. Audit Q8 (scout
line 1117) explicitly listed three viable shapes — Alembic data
migration vs `scripts/seed_phase6_decks.py` vs one-time admin import
— and instructed: "No in-repo seed convention exists today; lock it."

This spec **locks the in-repo seed convention** and ships the
bootstrap loader that hydrates an empty database from those files.
Specifically:

- A **markdown seed file format** with YAML frontmatter for structured
  fields (see §4) so curriculum authors can hand-edit content in a
  text editor with full git-diff review semantics.
- A **`load_seed_corpus(db)` service** with idempotent UPSERT
  semantics keyed on `(decks.slug, lessons.slug, quiz_items.lesson_id +
  question hash)` natural keys (see §6.1).
- A **`python -m app.scripts.seed_phase6` CLI script** with
  `--dry-run` flag (see §6.2) so the loader runs as an explicit ops
  action, not implicit-on-startup magic (see §14 OQ-4 for the
  bootstrap-on-startup question).
- An **acceptance bar** that:
  - Re-running the loader on a populated DB is a no-op (no UPDATEs,
    no version bumps).
  - Editing one lesson's `concept_md` on disk and re-running causes
    exactly that lesson to bump version + flip `version_type` to
    `'minor_edit'` per slice 6.4b §7.2 + spec #04 D-17, leaving every
    other row byte-identical.
  - Admin actions (archive, retire) survive re-loads. The loader does
    NOT resurrect rows the admin has archived/retired.

Specifically out of scope this slice (deferred or owned elsewhere):
generating content with Gemini (slice 6.10), admin UI for seed-corpus
management (admin UI exists in slice 6.4b but operates on the DB row,
not the seed file), seed-row analytics, retention/TTL on seed rows,
multi-language seeds, and any change to the slice-6.1 schema. See
§13 for the explicit out-of-scope list.

## 2. Goals

1. **Lock the seed file format** at directory + frontmatter
   granularity (§4) so multiple curriculum authors can hand-write
   markdown seeds without re-deriving the convention each time.
2. **Lock the loader API** — `load_seed_corpus(db: AsyncSession) ->
   SeedLoadReport` (§6.1) — with idempotent UPSERT semantics keyed on
   the natural keys `(decks.slug, lessons.slug, quiz_items.lesson_id +
   question hash)`.
3. **Lock the ops surface** — `python -m app.scripts.seed_phase6` CLI
   (§6.2) with `--dry-run` flag for safe pre-deployment verification.
4. **Cover the enum cross-product** — the seed corpus exercises both
   `decks.tier` values (`foundation` + `premium`), all three
   `decks.persona_visibility` values (`climber` /
   `interview_prepper` / `both`), all three `quiz_items.question_type`
   values (`mcq` / `free_text` / `code_completion`), and all three
   `quiz_items.difficulty` values (`easy` / `medium` / `hard`). See
   AC-8.
5. **Survive admin actions** — re-loading after a seeded deck or
   lesson is admin-archived (slice 6.4b POST `…/archive`) or a seeded
   quiz_item is admin-retired (slice 6.4b POST `…/retire`) does NOT
   resurrect those rows. The loader treats `archived_at IS NOT NULL`
   and `retired_at IS NOT NULL` as immutable signals (see §6.1.4 +
   AC-9 + AC-10 + §14 OQ-5 author hint).
6. **Zero new analytics events.** Seed loading is an ops surface,
   not user-facing. Logs go through stdlib `logger.info` with the
   `SeedLoadReport` payload (§9).

## 3. Non-goals

- **No admin UI for seed-corpus management.** Admins can edit seeded
  rows post-load via slice 6.4b's PATCH routes (which mutate the DB
  row, not the seed file). The seed FILES are not admin-editable;
  changes flow through git + a re-load.
- **No automated content generation.** Slice 6.10's ingestion pipeline
  uses Gemini to generate net-new lessons. Seeds are hand-authored. The
  two surfaces coexist: seeds are the canonical 12 locked decks +
  reference lessons; ingestion produces *additional* content over time.
- **No seed-row schema migrations.** Any slice-6.1+ schema change
  requires the seed-author to manually update the seed files (and
  their corresponding frontmatter contracts) in the same slice as the
  schema change. The loader does NOT auto-rewrite seed files.
- **No retention / TTL on seed rows.** Seed rows live in `decks` /
  `lessons` / `quiz_items` like any other row; they participate in
  slice 6.0's `quiz_review_events` + `lesson_view_events` analytics
  same as user-authored content.
- **No `card_quality_signals` writes.** Slice 6.13.5 owns the
  quality-signal table; seeds do not pre-populate it.
- **No retire-and-replace handling on re-load.** If a seed file's
  `quiz_item.question` text changes, the loader does NOT trigger the
  slice 6.4b §7.4 retire-and-replace cascade — instead it treats the
  change as a `version` bump on the lesson + `updated_at` bump on the
  quiz_item, preserving FSRS history. Spec writers who want
  retire-and-replace go through the admin UI, not the seed file. See
  §14 OQ-7 author hint.
- **No bootstrap-on-startup magic by default.** §6.2's CLI is the
  canonical ops path; the env-gated startup hook is deferred to a
  follow-up (see §14 OQ-4 author hint = script-only this slice).
- **No deck-card cover image upload.** Seed frontmatter carries the
  deck `icon` field (single-character emoji per slice 6.1 §4.1) but
  not deck cover images — those land in a future slice if/when the
  product surfaces them.
- **No FE surface.** This slice has zero FE deliverables. §8 below
  is a placeholder noting that.
- **No new PostHog events.** Zero this slice (§9).
- **Seed file content authoring.** This spec defines the *format* for
  seed files; the actual curriculum content (deck titles, lesson
  bodies, quiz_item question/answer pairs) is the implementation
  slice's deliverable. Spec lists shapes, not lesson copy.

## 4. Seed file format

> Conventions follow slice 6.1's `decks` / `lessons` / `quiz_items`
> schemas + slice 6.4b's `DeckCreateRequest` / `LessonCreateRequest` /
> `QuizItemCreateRequest` Pydantic write shapes (which the loader's
> validation layer reuses verbatim — §5).

### 4.1 Directory layout

```
hirelens-backend/app/data/
├── __init__.py                        # empty marker; restored if absent
└── decks/
    └── seed_lessons/
        ├── <deck_slug>/
        │   ├── _meta.md               # deck-level metadata (frontmatter only)
        │   ├── <lesson_slug>.md       # one file per lesson
        │   └── <lesson_slug>.md
        ├── <deck_slug>/
        │   └── ...
        └── ...
```

- `app/data/__init__.py` — empty file marking `app.data` as a Python
  package (Python imports + `pkg_resources`-style file discovery
  benefit). Slice 6.4b-1 deleted the prior `app/data/__init__.py`
  alongside `lesson_fixtures.py`; this slice **restores the marker**
  (see §4.5).
- `app/data/decks/seed_lessons/` — root of the seed corpus.
- `<deck_slug>/` — one subdirectory per deck. Subdirectory name is the
  deck's `slug` (matches `_SLUG_PATTERN = ^[a-z0-9-]+$` per slice 6.4b
  schema).
- `_meta.md` — deck-level metadata (frontmatter only; body ignored).
  See §4.2.
- `<lesson_slug>.md` — one file per lesson. Filename stem is the
  lesson's `slug` (must match `_SLUG_PATTERN`). See §4.3.

The `<deck_slug>` directory naming is the canonical key — the
loader keys decks by directory name, NOT by the `slug` field in
`_meta.md`'s frontmatter. If they disagree, the loader raises a
validation error (see §6.1.3). Same for `<lesson_slug>` filename vs
`slug` frontmatter field.

### 4.2 `_meta.md` — deck frontmatter

```markdown
---
slug: foundations-of-rag
title: Foundations of Retrieval-Augmented Generation
description: |
  RAG fundamentals — chunking, embedding, retrieval, generation,
  evaluation. Foundation-tier deck visible to all personas.
display_order: 0
icon: 📚
persona_visibility: both
tier: foundation
---
```

Fields mirror `DeckCreateRequest` (slice 6.4b `app/schemas/deck.py:61`)
field-for-field:

| Frontmatter key | Required | Type / values | Notes |
|------------------|----------|---------------|-------|
| `slug` | yes | string matching `^[a-z0-9-]+$`, 1-100 chars | Must match the `<deck_slug>` directory name. |
| `title` | yes | string, 1-200 chars | |
| `description` | yes | string, 1+ chars | YAML literal-block scalar (`\|`) preserves newlines. |
| `display_order` | no | int ≥ 0 (default `0`) | |
| `icon` | no | string, max 10 chars (default null) | Single emoji or short label. |
| `persona_visibility` | no | `climber` / `interview_prepper` / `both` (default `both`) | |
| `tier` | no | `foundation` / `premium` (default `premium`) | |

Markdown body of `_meta.md` is ignored by the loader. Authors may use
it for in-file notes that don't belong in `description`.

### 4.3 `<lesson_slug>.md` — lesson frontmatter + body

```markdown
---
slug: chunking-strategies
title: Chunking Strategies for RAG
display_order: 1
quiz_items:
  - question: |
      Which chunk size typically balances retrieval recall and
      generation context for English prose at ~512-token windows?
    answer: 256-512 tokens with 64-token overlap
    question_type: free_text
    difficulty: medium
    display_order: 0
  - question: What is the primary failure mode of fixed-size chunking?
    answer: Breaking semantic units (sentences, code blocks, tables) mid-flow.
    question_type: free_text
    difficulty: easy
    display_order: 1
  - question: Pick the best chunking strategy for code documentation.
    answer: Recursive structural chunking
    question_type: mcq
    distractors:
      - Fixed-size character chunking
      - Sentence-only chunking
      - Whole-document chunking
    difficulty: hard
    display_order: 2
---
## Concept

The fundamental tension in chunking is between **retrieval recall** —
small chunks → better keyword/semantic matches — and **generation
context** — large chunks → more coherent answers. Both ends fail in
predictable ways…

## Production

In production, recursive splitters from `langchain.text_splitter` are
the default. Tune `chunk_size` and `chunk_overlap` per corpus type:

```python
splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=64,
)
```

## Examples

| Corpus type | chunk_size | overlap |
|-------------|------------|---------|
| English prose | 512 | 64 |
| Code documentation | 1024 | 128 |
| Markdown / FAQ | 256 | 32 |
```

#### 4.3.1 Lesson frontmatter fields (header)

Mirrors `LessonCreateRequest` (slice 6.4b `app/schemas/lesson.py:72`)
modulo the `concept_md` / `production_md` / `examples_md` fields,
which come from the markdown body (see §4.3.2):

| Frontmatter key | Required | Type / values | Notes |
|------------------|----------|---------------|-------|
| `slug` | yes | string matching `^[a-z0-9-]+$`, 1-100 chars | Must match `<lesson_slug>` filename stem. |
| `title` | yes | string, 1-200 chars | |
| `display_order` | no | int ≥ 0 (default `0`) | |
| `quiz_items` | yes | array of QuizItem dicts, length ≥ 1 | See §4.3.3. |

`version`, `version_type`, `published_at`, `quality_score`,
`source_content_id`, `generated_by_model` are server-set by the
loader (see §6.1.2) — they are **not** seed-file fields.

#### 4.3.2 `concept_md` / `production_md` / `examples_md` from body

Author hint locked in §14 OQ-3 = labeled H2 sections (option (a) over
frontmatter fields). The loader parses the markdown body into three
slots by H2 section header:

- `concept_md` = body content **before** the first H2 (or under
  `## Concept` H2 if present).
- `production_md` = body under `## Production` H2.
- `examples_md` = body under `## Examples` H2.

If a section is absent, the loader stores an **empty string** (the
slice 6.1 schema has `NOT NULL` on all three columns). H2 headers are
matched case-insensitively and trimmed of whitespace; ordering must be
`Concept` → `Production` → `Examples` (the loader does NOT reorder).

If the body contains H2 sections with names other than these three,
the loader raises a validation error (`UnexpectedH2SectionError`,
§6.1.3) — prevents silent drift where an author writes `## Edge Cases`
expecting it to land somewhere.

#### 4.3.3 `quiz_items[]` element shape

Each `quiz_items[]` entry mirrors `QuizItemCreateRequest` (slice 6.4b
`app/schemas/quiz_item.py:117`) field-for-field:

| Key | Required | Type / values | Notes |
|------|----------|---------------|-------|
| `question` | yes | string, 1+ chars | YAML literal-block scalar for multi-line. |
| `answer` | yes | string, 1+ chars | |
| `question_type` | no | `mcq` / `free_text` / `code_completion` (default `free_text`) | |
| `distractors` | conditional | array of strings | **Required if `question_type='mcq'`; forbidden otherwise.** Mirrors `QuizItemCreateRequest._validate_distractors`. |
| `difficulty` | no | `easy` / `medium` / `hard` (default `medium`) | |
| `display_order` | no | int ≥ 0 (default `0`) | Within-lesson ordering. |

### 4.4 Loader-internal natural keys

The loader keys rows on **natural keys** (slug-based) rather than UUID
PKs:

| Entity | Natural key | DB lookup |
|--------|-------------|-----------|
| Deck | `slug` (from directory name) | `SELECT … FROM decks WHERE slug = :slug` |
| Lesson | `(deck_id, slug)` (from directory + filename) | `SELECT … FROM lessons WHERE deck_id = :deck_id AND slug = :slug` (matches the `uq_lessons_deck_slug` UNIQUE constraint) |
| QuizItem | `(lesson_id, question_hash)` where `question_hash = sha256(question.strip())[:16]` | `SELECT … FROM quiz_items WHERE lesson_id = :lid` then in-memory match by hash on `question` |

QuizItems have no on-disk natural key shorter than the question text
itself; the SHA-256 prefix is a stable de-dup key for "did this
exact question already get loaded?". Slug-based keying is impractical
because question text is the authoring affordance, not a slug. See
§14 OQ-8 for the alternative (slug-per-quiz_item) and the trade-off
analysis.

### 4.5 `app/data/__init__.py` restoration

Slice 6.4b-1 deleted `app/data/__init__.py` alongside
`app/data/lesson_fixtures.py` (the now-retired Phase 6 fixture
module). The empty `app/data/` directory itself was preserved per
spec #04 §4.3 — explicitly as the slot for this slice (6.4.5).

This slice **restores the marker file** at `app/data/__init__.py` so
`app.data` resolves as a Python package for any future loader code
that wants to use `pkg_resources` / `importlib.resources` for
file-discovery. The file ships empty (no exports).

## 5. Pydantic validation contracts

This slice ships **zero new Pydantic schemas**. The loader reuses
slice 6.4b's existing admin write schemas verbatim:

| Schema | Source | Loader use |
|--------|--------|------------|
| `DeckCreateRequest` | `app/schemas/deck.py:61` | Validates each `_meta.md` frontmatter dict. |
| `LessonCreateRequest` | `app/schemas/lesson.py:72` | Validates each lesson frontmatter dict (after `concept_md` / `production_md` / `examples_md` are spliced from the body). |
| `QuizItemCreateRequest` | `app/schemas/quiz_item.py:117` | Validates each `quiz_items[]` entry. |

The loader emits `pydantic.ValidationError` on any contract violation
(missing required fields, slug mismatch, distractors-on-non-mcq, etc.)
and short-circuits the whole load — no partial-corpus state. See
§6.1.3 for the error taxonomy.

A new internal report shape is defined for the loader's return value
but is NOT exposed via HTTP, so it lives in
`app/services/seed_lessons_service.py` as a `@dataclass` rather than a
Pydantic `BaseModel`:

### 5.1 `SeedLoadReport` (internal dataclass)

```python
@dataclass(frozen=True)
class SeedEntityCounts:
    created: int
    updated: int
    unchanged: int
    skipped_archived: int  # rows the loader left alone because admin archived/retired them


@dataclass(frozen=True)
class SeedLoadReport:
    decks: SeedEntityCounts
    lessons: SeedEntityCounts
    quiz_items: SeedEntityCounts
    dry_run: bool
    started_at: datetime
    finished_at: datetime
    seed_root: str  # absolute path to app/data/decks/seed_lessons
```

Returned by `load_seed_corpus(db)` (§6.1) and emitted to stdlib
logging by `python -m app.scripts.seed_phase6` (§6.2).

## 6. BE service & loader shape

Slice 6.4.5 introduces one new service module + one new script.

### 6.1 New service — `app/services/seed_lessons_service.py`

Public entry point:

```python
async def load_seed_corpus(
    db: AsyncSession,
    *,
    dry_run: bool = False,
    seed_root: Path | None = None,  # default: app/data/decks/seed_lessons
) -> SeedLoadReport: ...
```

#### 6.1.1 Behavior

1. Resolve `seed_root` (default `Path(app.__file__).parent /
   "data" / "decks" / "seed_lessons"`).
2. Walk `seed_root/<deck_slug>/`. For each:
   - Read `_meta.md` → frontmatter → `DeckCreateRequest.model_validate`.
   - Validate `slug` field matches `<deck_slug>` directory name.
   - UPSERT deck (see §6.1.2).
3. For each `<lesson_slug>.md`:
   - Read file → split frontmatter from body.
   - Parse body into `concept_md` / `production_md` / `examples_md`
     (§4.3.2).
   - Build `LessonCreateRequest.model_validate` payload (frontmatter
     fields + the three body slots).
   - Validate `slug` field matches `<lesson_slug>` filename stem.
   - UPSERT lesson (see §6.1.2).
   - For each `quiz_items[]` element:
     - `QuizItemCreateRequest.model_validate`.
     - UPSERT quiz_item (see §6.1.2).
4. Tally counts per entity into `SeedLoadReport`.
5. If `dry_run=True`, call `await db.rollback()` before returning;
   else `await db.commit()`. The caller does NOT manage the
   transaction — the loader owns its session usage.

#### 6.1.2 UPSERT semantics

For each entity:

- **Lookup** by natural key (§4.4).
- **Not found** → INSERT new row with server-generated `id` (UUID4).
  `version=1`, `version_type='initial'`, `published_at=func.now()`
  for lessons (seeds are pre-published per §14 OQ-9 author hint).
  Increment `created` count.
- **Found AND `archived_at IS NOT NULL` (deck/lesson) OR `retired_at
  IS NOT NULL` (quiz_item)** → SKIP (no UPDATE). Increment
  `skipped_archived` count. This is the admin-action survival
  guarantee per AC-9 + AC-10 + §14 OQ-5 author hint.
- **Found AND active** → diff field-by-field against the seed payload.
  - **No fields differ** → no-op. Increment `unchanged` count.
  - **Some fields differ** → UPDATE the differing fields, do NOT
    touch `created_at`. For lessons:
    - Bump `version` by 1.
    - Compute `version_type` via the slice 6.9 `classify_lesson_edit`
      rule (or its slice 6.4b D-17 placeholder until 6.9 ships) —
      author hint locked at §14 OQ-6: until slice 6.9 ships, treat
      every seed-file change as a `'minor_edit'` (loader-side opt-out
      from the substantive-edit retire-and-replace cascade per §3
      "No retire-and-replace handling on re-load").
    - For quiz_items: changing `question` text is allowed in-place;
      DOES NOT trigger retire-and-replace (per §3 + §14 OQ-7 author
      hint). The loader treats seed-file evolution as authoring
      polish, not curriculum-substantive change. Admins who want
      retire-and-replace go through the slice-6.4b admin PATCH route.
  - Increment `updated` count.

#### 6.1.3 Validation error taxonomy

The loader raises and short-circuits on:

- `pydantic.ValidationError` — frontmatter or body fails the slice
  6.4b write-schema contract.
- `SlugMismatchError` — `<deck_slug>` directory name ≠ `_meta.md`'s
  `slug` field; or `<lesson_slug>` filename stem ≠ lesson's `slug`
  field.
- `UnexpectedH2SectionError` — lesson body has H2 sections other than
  `Concept` / `Production` / `Examples`.
- `DuplicateQuestionHashError` — two `quiz_items[]` entries within
  the same lesson have identical question text (collision under the
  natural key).
- `MissingDeckMetaError` — a `<deck_slug>/` directory has no
  `_meta.md`.
- `OrphanLessonError` — a `<lesson_slug>.md` exists outside any
  `<deck_slug>/` directory (shouldn't happen given the directory
  layout, but defensive).

All errors abort the load with a non-zero return code from the script
and zero rows committed. Partial loads are not tolerated.

#### 6.1.4 Concurrency safety

`load_seed_corpus` is **safe to invoke concurrently** under the
following conditions:

- The natural-key UPSERT semantics (§6.1.2) tolerate two concurrent
  loaders racing on the same seed file — the second loader's lookup
  finds the first loader's INSERT and treats it as a no-op or a
  trivial "re-INSERT skipped" branch.
- For multi-row INSERT races (concurrent creates of the same deck +
  lesson + quiz_item chain), the database's existing UNIQUE
  constraints (`uq_decks_slug`, `uq_lessons_deck_slug`) catch the
  collision; the loser's `IntegrityError` is caught and re-routed
  through the same lookup path, treated as an "already exists" hit.
- See AC-11 for the test that pins this guarantee.

A simpler alternative (Postgres advisory lock) is documented at §14
OQ-10 if the natural-key path proves brittle in practice. Author hint:
ship the natural-key path first; advisory lock is the escape hatch.

### 6.2 New script — `app/scripts/seed_phase6.py`

CLI entry point (run via `python -m app.scripts.seed_phase6`):

```
$ python -m app.scripts.seed_phase6 [--dry-run]

  options:
    --dry-run       Validate + emit SeedLoadReport without committing.
                    Returns 0 on success even if no rows would change.
                    Returns non-zero on validation error.
```

Behavior:

- Builds an `AsyncSession` from `app.db.session.get_db_context_manager`
  (or equivalent — verify at impl time; `get_db` is a FastAPI
  dependency, not a context manager, so the script likely opens its
  own session via `async_sessionmaker(engine, class_=AsyncSession)`).
- Calls `await load_seed_corpus(db, dry_run=args.dry_run)`.
- Logs the `SeedLoadReport` via `logger.info` with one line per
  entity-count summary (`decks created=N updated=N unchanged=N
  skipped=N`, etc.).
- Exits 0 on success, non-zero on validation error / DB error.

The script is the **canonical ops surface** for re-loading seeds:
deploy a curriculum change → push to main → CI doesn't auto-run the
loader (no startup hook by default — §14 OQ-4); ops engineer runs
`python -m app.scripts.seed_phase6` against the target environment
when ready.

### 6.3 No new HTTP routes

Slice 6.4b's admin PATCH routes already cover ad-hoc post-load edits.
The loader is an **ops/CLI surface only**; it has no HTTP entry point.
This is intentional: an HTTP-triggered seed reload would require new
auth surface (admin-only? superadmin-only?), new rate-limit policy,
new audit logging — all out of proportion to a once-per-deploy
operation.

### 6.4 No bootstrap-on-startup hook (this slice)

§14 OQ-4 author hint: **script-only**. The startup hook
(env-flag-gated, e.g. `SEED_PHASE6_ON_STARTUP=true` triggering an
auto-load on FastAPI lifespan startup) is deferred to a follow-up
slice if ops needs it. Reasoning:

- A startup hook in prod would fire on every Railway redeploy — that
  is once per merge to main, sometimes multiple times per day during
  active development. Most of those firings are no-ops (unchanged
  counts), but each costs a transaction + a log entry + a few seconds
  of startup latency.
- A startup hook in CI / staging would surface seed-corpus regressions
  on deploy-time rather than at PR-time. Better to have a CI job run
  `python -m app.scripts.seed_phase6 --dry-run` on PRs touching
  `app/data/decks/seed_lessons/` and fail the PR if validation breaks.
- Script-only is the lowest blast-radius default. If/when ops asks
  for "auto-load on Railway redeploy", a 5-line lifespan hook lands in
  a follow-up slice gated on `SEED_PHASE6_ON_STARTUP=true`.

## 7. Alembic migration

**No Alembic migration this slice.** The slice 6.1 schema is
sufficient — the loader writes into existing tables. `app/data/`
restoration (§4.5) is a marker file, not a schema artifact.

## 8. FE component graph

**No FE deliverable this slice.** The seed corpus + loader are
ops/BE-only. FE consumers (slice 6.5 lesson UX, slice 6.7 / 6.12
persona Learn page composition) read seeded rows through the same
existing slice-6.3 / slice-6.4b read routes — no new FE surface.

## 9. Analytics events declared by this slice

**Zero new PostHog events.** Seed loading is an ops / admin / CLI
surface, not a user-facing feature. Three places where one might
*expect* an event but explicitly do not get one:

- `seed_corpus_loaded` (BE) — **rejected.** The CLI script logs the
  `SeedLoadReport` via `logger.info`; no PostHog event fires.
  Rationale: ops events don't belong in the product analytics catalog;
  Railway / CI logs are the right surface.
- `seed_corpus_load_failed` (BE) — **rejected.** Validation errors
  surface via the script's non-zero exit + Sentry capture
  (slice-existing) of any uncaught exception. PostHog is for product
  analytics, not ops alerts.
- `lesson_seeded` / `quiz_item_seeded` (BE, per-row) — **rejected.**
  Per-row events at corpus-load time would generate ~50-200
  zero-value events per re-load. The created/updated/unchanged
  counts in `SeedLoadReport` are the right granularity, and they
  live in stdlib logs, not PostHog.

`.agent/skills/analytics.md` requires no edits this slice — no events
added or renamed.

## 10. Test plan (implementation slice)

> This spec lists tests the implementation slice will add. No test
> code is written in this spec slice.

Expected test count delta: **+8 to +12 BE, +0 FE** (this slice has
zero FE surface).

### 10.1 Backend — `tests/test_seed_lessons_service.py` (~6-8 tests)

- `test_load_seed_corpus_empty_db_creates_all` — fresh DB; assert
  every deck / lesson / quiz_item row from a fixture seed corpus is
  created; `SeedLoadReport.created` counts match the fixture; all
  other counts (`updated` / `unchanged` / `skipped_archived`) are
  zero.
- `test_load_seed_corpus_idempotent_no_diff` — load fixture corpus
  twice; second load returns `SeedLoadReport` with `updated=0`,
  `created=0`, `unchanged=N` (one per loaded entity). Verify no
  `version` bump on any lesson row.
- `test_load_seed_corpus_lesson_concept_md_change_bumps_version` —
  load fixture; mutate one lesson's `concept_md` in the fixture
  source; re-load. Assert that one lesson's `version` is bumped
  from 1 → 2 + `version_type='minor_edit'`; all other lessons
  unchanged.
- `test_load_seed_corpus_archived_deck_not_resurrected` — load
  fixture; admin-archive one deck via a direct SQL UPDATE
  (`UPDATE decks SET archived_at = now() WHERE slug = :slug`);
  re-load. Assert `SeedLoadReport.decks.skipped_archived == 1`,
  `updated == 0`, `unchanged == N-1`. Verify the archived deck still
  has `archived_at IS NOT NULL` post-load.
- `test_load_seed_corpus_retired_quiz_item_not_resurrected` — same
  shape as above for a retired quiz_item.
- `test_load_seed_corpus_validation_error_aborts_load` — fixture
  corpus with one malformed `_meta.md` (e.g. `tier: bogus`). Assert
  the loader raises `pydantic.ValidationError`; assert the DB has
  zero rows post-call (transactional integrity).
- `test_load_seed_corpus_dry_run_commits_nothing` — fresh DB; call
  with `dry_run=True`. Assert `SeedLoadReport.dry_run is True`; assert
  DB has zero rows post-call; assert the report's `created` counts
  show what *would* have been created.
- `test_load_seed_corpus_slug_mismatch_raises` — fixture with one
  `_meta.md` whose `slug` field disagrees with its directory name.
  Assert `SlugMismatchError`.
- `test_load_seed_corpus_unexpected_h2_section_raises` — fixture
  lesson body with `## Edge Cases` H2 between `## Production` and
  `## Examples`. Assert `UnexpectedH2SectionError`.
- `test_load_seed_corpus_concurrent_invocation_safe` — two
  concurrent `await load_seed_corpus(db1, db2)` calls on disjoint
  AsyncSessions against the same DB. Assert both return; assert the
  final row count matches a single load (no duplicates, no
  IntegrityErrors).

### 10.2 Backend — `tests/test_seed_phase6_script.py` (~2-3 tests)

Marker-gated `@pytest.mark.integration` per slice 6.0 §10.1
precedent (the test shells out to `python -m app.scripts.seed_phase6`
via `subprocess`):

- `test_seed_phase6_script_dry_run` — invoke `python -m
  app.scripts.seed_phase6 --dry-run` against the test DB; assert exit
  0; assert no rows created.
- `test_seed_phase6_script_full_load` — invoke without `--dry-run`;
  assert exit 0; assert rows created. (May be replaced by a
  programmatic `await load_seed_corpus(db)` call wrapper if
  subprocess invocation proves flaky in CI.)

### 10.3 Backend — corpus coverage assertion (~1 test)

- `test_seed_corpus_covers_enum_cross_product` — load the **canonical**
  seed corpus (NOT a fixture); assert AC-8: at least one deck of each
  `tier` × `persona_visibility`; at least one quiz_item of each
  `question_type` × `difficulty`. This is a smoke test on the
  authored corpus, not the loader logic. Lives in
  `tests/test_seed_corpus_coverage.py` to keep loader tests fast
  (loader tests use small synthetic fixtures; this test loads the
  full ~12-deck corpus).

### 10.4 No FE tests

This slice has zero FE surface; no FE tests are added.

## 11. Acceptance criteria

The implementation slice (one-step follow-up) must pass:

- **AC-1** — `app/data/decks/seed_lessons/` exists on disk with the
  full canonical corpus (12 decks per LD H1; lessons-per-deck count
  pinned by §14 OQ-1 disposition). `app/data/__init__.py` empty
  marker is restored.
- **AC-2** — Each `_meta.md` validates against `DeckCreateRequest`.
  Verified by `test_seed_corpus_covers_enum_cross_product` (which
  loads the canonical corpus and would fail validation if any
  `_meta.md` is malformed).
- **AC-3** — Each `<lesson_slug>.md` validates against
  `LessonCreateRequest` + each nested `quiz_items[]` validates
  against `QuizItemCreateRequest`. Verified by the same canonical-load
  test.
- **AC-4** — `load_seed_corpus(db)` on empty DB inserts all decks /
  lessons / quiz_items; `SeedLoadReport` returns all-`created`
  counts equal to the corpus size; other counts zero.
  Verified by `test_load_seed_corpus_empty_db_creates_all`.
- **AC-5** — `load_seed_corpus(db)` re-run on populated DB returns
  `SeedLoadReport` with all-`unchanged` counts (no UPDATE, no
  version bump). Verified by `test_load_seed_corpus_idempotent_no_diff`.
- **AC-6** — `load_seed_corpus(db)` after on-disk edit to one
  lesson's `concept_md` returns `SeedLoadReport` with that lesson
  updated (`version` bump, `version_type='minor_edit'`); other
  lessons unchanged. Verified by
  `test_load_seed_corpus_lesson_concept_md_change_bumps_version`.
- **AC-7** — `python -m app.scripts.seed_phase6 --dry-run` emits
  report without committing. Pre-call row count = post-call row
  count. Verified by `test_seed_phase6_script_dry_run`.
- **AC-8** — Canonical seed corpus covers all 3 `persona_visibility`,
  both `tier`, all 3 `question_type`, all 3 `difficulty` values.
  Verified by `test_seed_corpus_covers_enum_cross_product`.
- **AC-9** — Re-loading after a deck/lesson is admin-archived (via
  slice 6.4b POST `…/archive`) does NOT resurrect it.
  `archived_at IS NOT NULL` is treated as immutable.
  Verified by `test_load_seed_corpus_archived_deck_not_resurrected`.
- **AC-10** — Re-loading after a quiz_item is admin-retired (via
  slice 6.4b POST `…/retire`) does NOT resurrect it.
  `retired_at IS NOT NULL` is treated as immutable.
  Verified by `test_load_seed_corpus_retired_quiz_item_not_resurrected`.
- **AC-11** — Loader is callable safely concurrently — second
  concurrent invocation returns a `SeedLoadReport` with
  all-`unchanged` counts (or one-off `IntegrityError` retry that
  reconverges to the same state). Verified by
  `test_load_seed_corpus_concurrent_invocation_safe`.

## 12. Decisions

> §14 OQ-1..OQ-10 all RESOLVED at spec amendment `<this-slice>` —
> locked into §12 as D-1..D-10 below, mirroring slice 6.0 §12
> amendment (`e8eecdd`) + slice 6.4 spec slice 2/2 / 3/3
> (`4fce036` / `de1e9a9`) precedent. Locks honor the §14 author
> hints verbatim where on-disk and prompt-side phrasings agree;
> divergences resolved in favor of the on-disk hint per R3.

### Phase-level decision rationale

- **H1 (seed file location).** Already locked at Phase 6 SESSION-STATE;
  cited here for completeness. Filesystem-based markdown seeds
  (`hirelens-backend/app/data/decks/seed_lessons/*.md`) over Alembic
  data migration (which would require a new migration on every
  curriculum tweak — wrong granularity) and over admin bulk-import
  CSV (which would mean curriculum lives in CSV instead of markdown,
  losing diff-friendly authorial review).
- **G2 (job runner choice).** Out of scope here. Slice 6.4.5 is a
  one-shot CLI loader; G2's RQ-vs-Railway-cron choice doesn't apply.

### Slice-local decisions

- **D-1 (resolves OQ-1) — Corpus size: 12 decks × 2 reference
  lessons each = 24 reference lessons total.** 12-deck count anchored
  to scout body line 901 + Q8 line 1117 + LD H1; two-lessons-per-deck
  balances AC-8 enum coverage (3 personas × 2 tiers × 3 question_types
  × 3 difficulties — exercised across the 24 lessons + ~50-100
  quiz_items rather than artificially stretched to fit a single
  lesson per deck) against authoring effort (~10-20 hours of
  curriculum authoring at the impl slice). Future authoring slices
  may add additional lessons per deck via slice 6.4b admin authoring;
  the seed corpus is a floor, not a ceiling. Cross-ref §3 G-4, §4,
  AC-1, AC-8.
- **D-2 (resolves OQ-2) — Deck-meta file shape: `_meta.md` per-deck
  under `app/data/decks/seed_lessons/<deck_slug>/_meta.md` with YAML
  frontmatter mirroring `DeckCreateRequest` field-for-field.**
  Rejected alternatives: top-level `decks.yaml` (no per-deck
  description-authoring slot, harder to author multi-line `description`
  via YAML literal-block scalar `|`) and `_deck.md` (rename of same
  shape — no semantic gain). `_meta.md` mirrors the lesson file
  convention (one markdown file per entity), keeps the filesystem
  layout self-documenting (one directory = one deck = one bundle),
  and allows multi-line descriptions via YAML literal-block syntax.
  Markdown body of `_meta.md` is ignored by the loader. Cross-ref
  §4.1, §4.2.
- **D-3 (resolves OQ-3) — Lesson body text-field allocation: H2
  section parsing.** `concept_md` = body content **before** the
  first H2 (or under `## Concept` H2 if present); `production_md` =
  body under `## Production` H2; `examples_md` = body under
  `## Examples` H2. Empty section → empty string in DB (the slice
  6.1 schema has `NOT NULL` on all three columns). Frontmatter holds
  non-body lesson fields only (`slug`, `title`, `display_order`,
  nested `quiz_items[]`). Author ergonomics win: markdown is more
  readable in a text editor than YAML literal-block scalars, H2
  headers preview cleanly in GitHub web UI, markdown linters /
  formatters work on body sections but not on YAML strings. Trade-off
  accepted: parser is slightly more complex than "just read frontmatter
  dict" (~15-20 LoC for H2 splitter), but the author-side ergonomics
  win is non-trivial and frontmatter literal-blocks lose `prettier` /
  `markdownlint` coverage. Cross-ref §4.3, §4.3.2.
- **D-4 (resolves OQ-4) — Bootstrap path: script-only via
  `python -m app.scripts.seed_phase6 [--dry-run]`. NO startup-event
  hook this slice.** Lowest blast radius; adds zero startup-time
  cost; avoids the multi-redeploy-per-day scenario where every
  Railway redeploy fires a no-op load (each costing a transaction +
  a log entry + a few seconds of startup latency). Ops invokes the
  script deliberately when ready. CI may run `--dry-run` on PRs
  touching `app/data/decks/seed_lessons/` and fail the PR if
  validation breaks; that integration is out of scope for this slice
  but unblocked. Future "auto-seed on Railway redeploy" startup hook
  can ship as its own slice gated on `SEED_PHASE6_ON_STARTUP=true`
  if ops needs it (~5-line FastAPI lifespan hook). Cross-ref §6.2,
  §6.4, §13 (Out of scope).
- **D-5 (resolves OQ-5) — Archived/retired-row resurrection policy:
  skip.** Loader skips rows where `archived_at IS NOT NULL` (decks,
  lessons) or `retired_at IS NOT NULL` (quiz_items); increments
  `SeedLoadReport.<entity>.skipped_archived` counter; does NOT mutate
  `archived_at` / `retired_at`. Admin's archive/retire decision is
  authoritative — re-running the loader does NOT bounce admin-archived
  seeds back to active. Rejected alternatives: resurrect (clearing
  `archived_at` would silently undo admin curation — hard-to-debug
  surprise) and error-on-collision (forces operator manual cleanup
  for routine re-loads — wrong granularity). Escape hatch for
  archive-by-mistake is a future slice 6.4b admin un-archive PATCH
  path (does not exist today; production archives should be rare).
  Cross-ref §6.1.2, §6.1.4, §10 AC-9, §10 AC-10.
- **D-6 (resolves OQ-6) — Lesson-edit classification on re-load:
  loader-side opt-out → always `version_type='minor_edit'` on
  lesson updates.** When on-disk diff exists between seed file and
  active DB row, loader bumps `lesson.version` per the existing
  slice 6.4b minor-edit path and stamps `version_type='minor_edit'`
  unconditionally. Substantive-edit cascade (per slice 6.4 D-8 / D-15)
  + slice 6.9 `classify_lesson_edit` rule are admin-UI semantics for
  human curation; loader-driven re-loads must NOT trigger quiz_item
  retirement cascades because the seed corpus is authored as a single
  source-of-truth tree (admin retires happen *after* seed load in the
  lifecycle). Treats seed-file evolution as authoring polish, not
  curriculum-substantive change. Cross-ref §6.1.2, §3 (Non-goals
  "No retire-and-replace handling on re-load").
- **D-7 (resolves OQ-7) — Quiz_item question-text-change handling
  on re-load: UPDATE in place via natural-key fallback.** Loader
  natural-key lookup is `(lesson_id, sha256(question.strip())[:16])`
  per D-8; if hash-based lookup misses (question text edited on
  disk), loader falls back to `(lesson_id, display_order)` to
  re-anchor the existing row, then UPDATEs that row in place
  (preserves PK + preserves FSRS history on the existing
  `quiz_item_progress` rows). Hash preferred, display_order is the
  fallback. Reasoning: seed-file question polish (typo fix,
  clarification) should NOT reset user retention — it's a content-edit,
  not a content-replacement. Authors who genuinely want retire-and-
  replace cascade go through slice 6.4b admin PATCH `…/retire`
  (the substantive-edit path). Within-lesson `display_order` clashes
  on re-load (two seed rows targeting the same `display_order`)
  resolve by honoring the disk value and bumping the existing DB row's
  `display_order` to next-free integer. Cross-ref §4.4, §6.1.2,
  §3 (Non-goals "No retire-and-replace handling on re-load").
- **D-8 (resolves OQ-8) — QuizItem natural-key shape: hash-based
  composite `(quiz_items.lesson_id, sha256(quiz_items.question.strip())[:16])`
  with display_order fallback per D-7.** Avoids reopening slice 6.1
  schema (would otherwise require a new `quiz_items.slug` column +
  Alembic migration; slice 6.1 schema additions were closed at AC-8
  of spec #01). Hash truncation length 16 hex chars = 64 bits ≈
  1.8e19 collision space — acceptable for a seed corpus of ~24
  reference quiz_items per D-1 + N future authored quiz_items via
  slice 6.4b. Hash is computed in-memory at lookup time (loader
  reads question text from seed file, hashes the trimmed value,
  searches DB for matching row); not persisted as a DB column.
  Brittleness on question-edit is mitigated by D-7's display_order
  fallback. If hash-based lookups prove brittle in practice, slug-per-
  quiz_item (option (b) at OQ-8) becomes a slice 6.13.5+
  schema-evolution candidate. Cross-ref §4.4, §6.1.2, §10 AC-3.
- **D-9 (resolves OQ-9) — Seed-row `published_at` initialization:
  pre-publish at first INSERT.** All seeded lessons set
  `published_at = func.now()` at initial INSERT (NOT NULL / draft).
  Rationale: the seeded corpus is admin-curated reference content,
  intended to be visible in `/learn` immediately on deploy — that's
  the whole point of having a seed corpus. Rejected alternatives:
  ship-as-draft (would require admin to manually publish each seed
  through slice 6.4b POST `…/publish` — defeats the purpose of an
  automated loader) and per-lesson frontmatter `published: bool`
  (premature configurability per Q1; default-published covers the
  canonical case, and admins can post-load archive any seeded lesson
  via slice 6.4b PATCH which the loader respects per D-5 thereafter).
  Cross-ref §6.1.2, §10 AC-1.
- **D-10 (resolves OQ-10) — Concurrency-safety strategy: natural-key
  UPSERT semantics + race-tolerant `IntegrityError` catch.** Loader
  performs lookup-by-natural-key → diff-or-insert; on the
  multi-row INSERT race (two concurrent loaders both miss the lookup
  and both try to INSERT the same `decks.slug` /
  `(lessons.deck_id, lessons.slug)` row), the database's existing
  UNIQUE constraints (`uq_decks_slug`, `uq_lessons_deck_slug`) catch
  the collision; the loser's `IntegrityError` is caught and re-routed
  through the same lookup path, treated as an "already exists" hit
  (no-op or unchanged-count branch). Concurrent loader invocations
  (e.g. two ops engineers running the script simultaneously, or — if
  the future startup hook lands — two pods racing on cold start)
  safely converge to the same final state. Postgres advisory lock
  (`pg_advisory_lock(<seed-loader-namespace-id>)`) is the **deferred
  escape-hatch** path (b) — to be picked up if the natural-key path
  proves brittle in practice (e.g. high contention or recurring
  IntegrityError loops). Cross-ref §6.1.4, §10 AC-11.

## 13. Out of scope (deferred to other Phase-6 slices)

Explicit list:

- **AI-generated seed content** — slice 6.10 (Gemini ingestion
  pipeline) generates *additional* lessons over time. The seed corpus
  is hand-authored and is the *canonical* set of 12 locked decks.
- **Admin UI for seed-corpus management** — slice 6.4b's admin
  authoring UI mutates DB rows; it does NOT mutate seed files. Seed
  files are git-tracked, edited via PR.
- **Seed-row schema migrations on slice-6.1+ schema changes** — seed
  files are hand-updated alongside any schema change in the same
  slice as that change. The loader does not auto-rewrite seed files.
- **Retention / TTL on seed rows** — orthogonal to slice 6.0's
  retention slice (deferred per spec #00 §14 OQ-3 / §12 D-9).
- **`card_quality_signals` pre-population** — slice 6.13.5 owns the
  table; seeds do not pre-populate it.
- **Retire-and-replace handling for changed seed quiz_items** — slice
  6.4b §7.4 retire-and-replace cascade is admin-PATCH-only; seed
  re-loads do NOT trigger it. See §14 OQ-7 author hint.
- **Multi-language seeds** — single-language (English) only this slice.
  i18n is its own future spec.
- **Deck cover-image upload** — out of scope. `decks.icon` field
  remains the single emoji slot; cover images land in a future slice
  if/when the product surfaces them.
- **Per-deck pricing tiers** — `decks.tier` is the binary
  foundation/premium split (slice 6.1). No additional pricing
  granularity this slice.
- **Bootstrap-on-startup hook** — script-only this slice (§6.4 +
  §14 OQ-4 author hint).
- **HTTP route for seed-load** — script-only ops surface; no HTTP
  trigger.
- **Seed authoring guide / runbook** — a separate doc-only slice may
  author `docs/runbooks/seed-corpus-authoring.md`; this spec defines
  the format but does not author a runbook.

## 14. Open questions

> **OQ-1..OQ-10 all RESOLVED at spec amendment `<this-slice>`** —
> locked into §12 as D-1..D-10 respectively. OQ headings + question
> text retained verbatim below for forward-readability; the
> resolution line cites the §12 D-N decision that closes each one.
> Mirrors slice 6.0 §14 OQ-1..OQ-4 + slice 6.4 §14 OQ-2..OQ-6
> post-amendment shape (`e8eecdd` / `4fce036` / `de1e9a9`).

### OQ-1 — Corpus size + structure

LD H1 phrasing: "12 locked-deck seeds (slice 6.4.5)." Scout body
(line 901) confirms: "The 12 locked decks become seed data via either
…". Scout Q8 (line 1117): "Seed data for the 12 locked decks…".
12 decks is the canonical number — both LD and scout agree. The
open question was **lessons-per-deck count + corpus density**.

**RESOLVED** — see §12 **D-1** (`<this-slice>`): 12 decks × 2
reference lessons each = 24 reference lessons total. Author hint
(b) selected per the AC-8 enum-coverage-vs-authoring-effort balance
discussed in the original OQ.

### OQ-2 — Deck-meta file shape

Where does deck-level metadata live? Options were (a) `_meta.md`
per-deck frontmatter file under each `<deck_slug>/` directory,
(b) `_deck.md` rename of same shape, or (c) top-level `decks.yaml`
listing all 12 decks in one file.

**RESOLVED** — see §12 **D-2** (`<this-slice>`): `_meta.md` per-deck
under `app/data/decks/seed_lessons/<deck_slug>/_meta.md`. Author
hint (a) selected — keeps deck description authorable in its own
slot, allows multi-line descriptions via YAML literal-block scalar
`|`, mirrors the lesson file convention (one markdown file per
entity), and keeps the filesystem layout self-documenting (one
directory = one deck = one bundle).

### OQ-3 — `concept_md` / `production_md` / `examples_md` location

Where do the three lesson body slots come from? Options were (a)
markdown body H2 sections (`## Concept` / `## Production` /
`## Examples`) parsed by the loader, or (b) frontmatter fields
holding the body content as YAML literal-block scalars.

**RESOLVED** — see §12 **D-3** (`<this-slice>`): markdown body H2
sections per §4.3.2. Author hint (a) selected — markdown is more
readable in a text editor than YAML literal-blocks, H2 headers
preview cleanly in GitHub web UI, and markdown linters / formatters
work on body sections but not on YAML strings. Parser complexity
trade-off (~15-20 LoC) accepted.

### OQ-4 — Bootstrap-on-startup vs script-only

How does the loader run? Options were (a) script-only
(`python -m app.scripts.seed_phase6`), (b) env-gated startup hook
in the FastAPI lifespan (`SEED_PHASE6_ON_STARTUP=true`), or (c) both.

**RESOLVED** — see §12 **D-4** (`<this-slice>`): script-only this
slice. Author hint (a) selected — lowest blast radius; adds zero
startup-time cost; avoids the multi-redeploy-per-day scenario where
every Railway redeploy fires a no-op load. Future startup hook
deferred to its own follow-up slice gated on
`SEED_PHASE6_ON_STARTUP=true` if ops needs it.

### OQ-5 — Archived/retired-row resurrection policy

What does the loader do when a row exists with `archived_at IS NOT
NULL` (decks/lessons) or `retired_at IS NOT NULL` (quiz_items)?
Options were (a) skip (leave the row alone), (b) resurrect (clear
`archived_at` / `retired_at` and apply the seed payload), or (c)
error (raise on first archived-row collision).

**RESOLVED** — see §12 **D-5** (`<this-slice>`): skip. Author hint
(a) selected — admin's archive/retire decision is authoritative;
re-running the loader does NOT bounce admin-archived seeds back to
active. Loader increments `SeedLoadReport.<entity>.skipped_archived`
without mutating `archived_at` / `retired_at`.

### OQ-6 — Lesson-edit classification rule for the loader

When a lesson's seed file changes between loads, what `version_type`
does the loader stamp? Options were (a) always `'minor_edit'` until
slice 6.9 ships then delegate to its classifier, (b) always
`'minor_edit'` regardless of slice 6.9 (loader-side opt-out from
substantive-edit cascade), or (c) run slice 6.9's classifier and let
substantive edits trigger retire-and-replace.

**RESOLVED** — see §12 **D-6** (`<this-slice>`): loader-side opt-out
→ always `'minor_edit'`. Author hint (b) selected — substantive-edit
cascade is admin-UI semantics for human curation; corpus curation
should never accidentally trigger it via re-load. Loader still bumps
`lesson.version` per slice 6.4b minor-edit path.

### OQ-7 — Quiz_item question-text-change handling on re-load

When a `quiz_items[]` entry's `question` text changes between loads,
what does the loader do? Options were (a) UPDATE in place (preserve
PK + FSRS history; relax natural key with display_order fallback when
hash-lookup fails), (b) DELETE-old + INSERT-new (loses FSRS history),
or (c) retire-and-replace cascade per slice 6.4b §7.4.

**RESOLVED** — see §12 **D-7** (`<this-slice>`): UPDATE in place via
natural-key fallback. Author hint (a) selected — hash-based lookup
preferred, `(lesson_id, display_order)` fallback re-anchors when the
question text was edited; both paths converge on UPDATE-in-place to
preserve FSRS history continuity. Authors who want retire-and-replace
go through slice 6.4b admin PATCH `…/retire`.

### OQ-8 — QuizItem natural-key shape

Options for the QuizItem natural key (§4.4) were (a)
`(lesson_id, sha256(question)[:16])` — hash of question text, (b)
`(lesson_id, slug)` — requires adding a `slug` column to slice 6.1's
`quiz_items` table (out of scope per spec #01 AC-8 closure), or (c)
`(lesson_id, display_order)` — brittle under reorder.

**RESOLVED** — see §12 **D-8** (`<this-slice>`): hash-based composite
`(lesson_id, sha256(question.strip())[:16])` with `display_order`
fallback per D-7. Author hint (a) selected — avoids slice-6.1 schema
change; hash truncation length 16 hex chars (~64 bits collision
space) is sufficient for reference + future-authored quiz_items.
Slug-per-quiz_item (option (b)) becomes a slice 6.13.5+ schema-
evolution candidate if hash-based lookups prove brittle.

### OQ-9 — Seed-row `published_at` initialization

`lessons.published_at` is `Optional[datetime]` per slice 6.1 §4.2;
NULL = "draft" hidden from user-facing read routes. Options for seed
rows' initial `published_at` were (a) `func.now()` (pre-published),
(b) NULL (ship as drafts; admin manually publishes each), or (c)
optional frontmatter `published: true` per-lesson.

**RESOLVED** — see §12 **D-9** (`<this-slice>`): pre-publish at
first INSERT. Author hint (a) selected — seeded corpus is admin-
curated reference content, intended to be visible in `/learn`
immediately on deploy. Admins can post-load archive any seeded
lesson via slice 6.4b PATCH; loader respects D-5 thereafter.

### OQ-10 — Concurrency-safety strategy

§6.1.4 documented two paths: (a) natural-key UPSERT semantics +
race-tolerant `IntegrityError` catch (relies on existing DB UNIQUE
constraints to serialize concurrent loaders), or (b) Postgres
advisory lock serializing the entire load.

**RESOLVED** — see §12 **D-10** (`<this-slice>`): natural-key UPSERT
semantics + `IntegrityError` catch. Author hint (a) selected — lowest
blast radius; no new locking primitive; relies on the existing
`uq_decks_slug` + `uq_lessons_deck_slug` constraints to converge
concurrent-loader races to the same final state. Postgres advisory
lock is the deferred escape-hatch path (b) if the natural-key path
proves brittle in practice (e.g. high contention or recurring
IntegrityError loops).

### OQ-11+ (placeholder)

If chat-Claude or impl-time CC surfaces additional product OQs
(e.g. "should the loader support `pyproject.toml`-style include/exclude
globs to load only a subset of decks?" or "should the loader emit
a structured JSON report instead of a stdlib log?"), file them as
OQ-11 / OQ-12 below at spec-amendment time.
