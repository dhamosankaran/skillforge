# Phase 6 — Slice 6.4.5: Reference Seed Lessons + Bootstrap Loader

## Status: Drafted, not shipped — §12 empty pending OQ disposition; impl row filed at `B-071` 🔴

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
> chasing SESSION-STATE. Rationale lives in §12 (Decisions) once
> §14 OQs are dispositioned via amendment slice.

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

> Spec authored with §14 OQ-1..OQ-10 surfaced for Dhamo disposition
> (some carry author hints, others are real architectural calls).
> §12 will be filled in by a §12 amendment slice (mirrors slice 6.0
> spec slice 2/2 / slice 6.4 spec slice 2/2 / 3/3 precedent) once
> Dhamo locks the OQs into D-N decisions.
>
> No D-N decisions locked at spec-author time. The author-hinted
> options in §14 are **tentative** and may be overridden during the
> §12 amendment slice or directly at the implementation slice's
> Step 1 audit.

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

*To be authored by the §12 amendment slice once §14 OQs are
dispositioned. Placeholder bullets:*

- **D-1 (resolves OQ-1) — Corpus size + structure.** TBD.
- **D-2 (resolves OQ-2) — Deck-meta file shape.** TBD.
- **D-3 (resolves OQ-3) — Body-section parsing strategy.** TBD.
- **D-4 (resolves OQ-4) — Bootstrap-on-startup vs script-only.**
  TBD.
- **D-5 (resolves OQ-5) — Archived/retired-row resurrection
  policy.** TBD.
- **D-6 (resolves OQ-6) — Lesson-edit classification rule for the
  loader.** TBD.
- **D-7 (resolves OQ-7) — Quiz_item question-text-change handling
  on re-load.** TBD.
- **D-8 (resolves OQ-8) — QuizItem natural-key shape.** TBD.
- **D-9 (resolves OQ-9) — Seed-row `published_at` initialization.**
  TBD.
- **D-10 (resolves OQ-10) — Concurrency-safety strategy.** TBD.

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

> All §14 OQs are explicit Dhamo decision points. **Author hints**
> below are tentative and become D-N locks when the §12 amendment
> slice fires. Hints lean toward minimum blast radius + slice-6.0 /
> slice-6.4 precedent shape.

### OQ-1 — Corpus size + structure

LD H1 phrasing: "12 locked-deck seeds (slice 6.4.5)." Scout body
(line 901) confirms: "The 12 locked decks become seed data via either
…". Scout Q8 (line 1117): "Seed data for the 12 locked decks…".

**12 decks is the canonical number** — both LD and scout agree. The
open question is **lessons-per-deck count + corpus density**.
Options:

- **(a)** 12 decks × 1 reference lesson each = 12 lessons total
  (minimum corpus for AC-8 enum coverage; fastest to author; thin on
  end-to-end realism for downstream slice testing).
- **(b)** 12 decks × 2-3 reference lessons each = ~24-36 lessons
  total (richer end-to-end realism; more author work; still tractable
  hand-authoring).
- **(c)** 12 decks × 1 lesson + a separate "exemplar deck" with
  5-10 lessons demonstrating the full quiz_type cross-product = ~17-22
  lessons (mixes coverage with realism; one deck pulls double duty
  as the enum-coverage exemplar, avoiding artificial per-deck
  inflation).

**Author hint:** **(b)** — 12 decks × 2 lessons each = 24 lessons.
Roughly mirrors a "minimum viable curriculum" feel; AC-8 enum coverage
naturally lands across the 24 lessons + 50-100 quiz_items without
forcing artificial single-lesson-per-deck stretching. Scope estimate:
~24 lesson markdown files + 12 `_meta.md` files = ~36 seed files
total, ~10-20 hours of curriculum authoring (not in this slice's
scope — implementation slice owns content authoring).

### OQ-2 — Deck-meta file shape

Three options for where deck-level metadata lives:

- **(a)** `<deck_slug>/_meta.md` per-deck frontmatter file (this
  spec's §4 default). Description body becomes
  `decks.description` if author writes it as a YAML literal-block;
  alternative interpretation: description body == markdown body, used
  for richer authoring.
- **(b)** `<deck_slug>/_deck.md` same shape, different filename
  convention.
- **(c)** Top-level `decks.yaml` listing all 12 decks in one file;
  per-deck subdirectories then only contain lesson files.

**Author hint:** **(a)** `_meta.md` per-deck — keeps deck description
authorable in its own slot, allows YAML literal-block `\|` syntax for
multi-line descriptions, mirrors the lesson file convention (one
markdown file per entity), keeps the filesystem layout
self-documenting (one directory = one deck = one bundle).

### OQ-3 — `concept_md` / `production_md` / `examples_md` location

Two options for where the three lesson body slots come from:

- **(a)** Markdown body H2 sections (this spec's §4.3.2 default):
  `concept_md = body before first H2 (or under ## Concept)`,
  `production_md = body under ## Production`, `examples_md = body
  under ## Examples`.
- **(b)** Frontmatter fields: `concept_md: \|`, `production_md: \|`,
  `examples_md: \|` as YAML literal-blocks.

**Author hint:** **(a)** body H2 sections — markdown is more readable
in a text editor than YAML literal-blocks; H2 headers preview cleanly
in GitHub web UI; markdown linters / formatters work on body sections
but not on YAML strings. Trade-off: parser is slightly more complex
than "just read frontmatter dict", but the author-side ergonomics
win.

### OQ-4 — Bootstrap-on-startup vs script-only

Three options for *how* the loader runs:

- **(a)** Script-only (this spec's §6.4 default). `python -m
  app.scripts.seed_phase6` is the only entry point; ops decides when
  to run it. CI may run `--dry-run` on PRs touching `app/data/`.
- **(b)** Env-gated startup hook — `if SEED_PHASE6_ON_STARTUP:
  await load_seed_corpus(db)` in the FastAPI lifespan. Defaults to
  False in prod; True in dev/CI. Catches developer "forgot to seed"
  state.
- **(c)** Both — script for explicit runs, startup hook for
  dev/CI convenience.

**Author hint:** **(a)** script-only this slice. Lowest blast radius;
adds zero startup-time cost; avoids the multi-redeploy-per-day
scenario described in §6.4. If ops or DX needs the hook later, a
follow-up adds it in 5 lines. Reasoning: "default to surprise-free."

### OQ-5 — Archived/retired-row resurrection policy

What does the loader do when a row exists with `archived_at IS NOT
NULL` (decks/lessons) or `retired_at IS NOT NULL` (quiz_items)?

- **(a)** **Skip** — leave the row alone; increment
  `skipped_archived` counter; do NOT mutate `archived_at` /
  `retired_at`. Admin's archive decision is authoritative.
- **(b)** **Resurrect** — clear `archived_at` / `retired_at` and
  apply the seed file's payload as if active. Useful if a deck was
  archived by mistake and you want a re-deploy to undo it.
- **(c)** **Error** — raise on first archived-row collision, force
  the operator to either delete the seed file or un-archive the row
  manually before re-loading.

**Author hint:** **(a)** skip. Admins archive for a reason; a re-load
"forcing" the row back is a hard-to-debug surprise. The escape hatch
for "I archived this by mistake" is the slice 6.4b admin un-archive
PATCH path (which doesn't exist today — that's a separate row to
file if needed, but archived rows in production should be rare).

### OQ-6 — Lesson-edit classification rule for the loader

When a lesson's seed file changes between loads, what
`version_type` does the loader stamp?

- **(a)** Always `'minor_edit'` until slice 6.9
  (`classify_lesson_edit` rule) ships. After slice 6.9, the loader
  delegates to that classifier.
- **(b)** Always `'minor_edit'` regardless of slice 6.9 — loader-side
  opt-out from substantive-edit cascade because seed re-loads should
  never trigger quiz_item retirement. Substantive-edit cascade is an
  admin-UI concern, not a corpus-curation concern.
- **(c)** Run slice 6.9's classifier (when it ships) and let
  substantive edits trigger the retire-and-replace cascade. Risky:
  a seed-file polish (e.g. fixing a typo in `concept_md` that
  crosses the >15% char-delta threshold) would silently retire all
  the lesson's quiz_items.

**Author hint:** **(b)** loader-side opt-out → always `'minor_edit'`.
Substantive-edit cascade is admin-UI semantics; corpus curation
should never accidentally trigger it. The loader is a content-author's
tool, not a curriculum-evolution event source.

### OQ-7 — Quiz_item question-text-change handling on re-load

When a `quiz_items[]` entry's `question` text changes between loads,
what does the loader do?

- **(a)** UPDATE in place (preserve PK, preserve FSRS history on the
  existing `quiz_item_progress` rows). Question hash changes; the
  natural-key lookup may fail to match, but a fallback lookup by
  `display_order` within the lesson can re-anchor.
- **(b)** Treat as DELETE-old + INSERT-new (loses FSRS history; bad
  default).
- **(c)** Treat as retire-and-replace cascade per slice 6.4b §7.4
  (mirrors the admin substantive-edit path; preserves FSRS history
  on the *old* row but starts fresh on the *new* row — which means
  user retention metrics get reset for that quiz_item).

**Author hint:** **(a)** UPDATE in place + fallback by
`(lesson_id, display_order)` if question-hash lookup fails.
Reasoning: seed-file question polish (typo fix, clarification) should
not reset retention; it's content-edit, not content-replacement.
Authors who genuinely want retire-and-replace go through slice 6.4b
admin PATCH. **Caveat:** §4.4 frames the natural-key as
`(lesson_id, question_hash)` — if author hint (a) lands, the natural
key relaxes to `(lesson_id, question_hash) OR (lesson_id,
display_order)` with hash preferred and display_order fallback.

### OQ-8 — QuizItem natural-key shape

Three options for the QuizItem natural key (§4.4):

- **(a)** `(lesson_id, sha256(question)[:16])` — hash of question
  text. Stable across loader runs as long as the question text
  doesn't change. Breaks under question-text edit (relies on OQ-7's
  fallback).
- **(b)** `(lesson_id, slug)` — add a `slug` field to
  `QuizItemCreateRequest` + slice 6.1's `quiz_items` table. Slug is
  author-supplied + immutable. Cleanest natural key but is a slice-6.1
  schema change → out of scope for this slice (slice 6.1 schema
  changes were closed at AC-8 of spec #01).
- **(c)** `(lesson_id, display_order)` — only stable as long as
  authors don't reorder. Brittle.

**Author hint:** **(a)** hash-based with display_order fallback per
OQ-7. Avoids slice-6.1 schema change. The fallback covers the
question-edit case. If hash-based lookups prove brittle in practice,
(b) becomes a slice 6.13.5+ schema-evolution candidate.

### OQ-9 — Seed-row `published_at` initialization

`lessons.published_at` is `Optional[datetime]` per slice 6.1 §4.2.
Lessons with `published_at IS NULL` are treated as "drafts" and
hidden from user-facing read routes (`lesson_service.py:46`).

For seed rows, what's the initial `published_at`?

- **(a)** `func.now()` at first INSERT — seed rows are
  pre-published.
- **(b)** NULL — seed rows ship as drafts; admin must manually
  publish each one through the slice 6.4b admin POST `…/publish`
  route.
- **(c)** Optional frontmatter field `published: true` (default true)
  controls per-lesson.

**Author hint:** **(a)** pre-publish. Seeds are the canonical curated
corpus; the whole point is they're available out of the box. If a
specific seed lesson should ship as a draft, the curriculum author
flips frontmatter (option (c) extension) — but the default is
published.

### OQ-10 — Concurrency-safety strategy

§6.1.4 documents two paths:

- **(a)** Natural-key UPSERT semantics + race-tolerant `IntegrityError`
  catch — relies on database UNIQUE constraints to serialize concurrent
  loaders. Lowest blast radius; no new locking primitive.
- **(b)** Postgres advisory lock (`pg_advisory_lock(<deterministic_id>)`)
  serializing the entire load. Strong correctness guarantee; requires
  a new locking primitive but is well-trod Postgres territory.

**Author hint:** **(a)** start with natural-key path; if
multi-pod concurrent-load races prove brittle (e.g. on Railway when
two ops engineers run the script simultaneously, or if the future
startup hook lands and two pods race on cold start), fall back to
(b).

### OQ-11+ (placeholder)

If chat-Claude or impl-time CC surfaces additional product OQs
(e.g. "should the loader support `pyproject.toml`-style include/exclude
globs to load only a subset of decks?" or "should the loader emit
a structured JSON report instead of a stdlib log?"), file them as
OQ-11 / OQ-12 below at spec-amendment time.
