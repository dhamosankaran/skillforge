# Phase 6 — Slice 6.1: Foundation Schema (decks / lessons / quiz_items / quiz_item_progress)

## Status: Drafted, not shipped

| Field | Value |
|-------|-------|
| Phase | 6 (Curriculum Platform) |
| Slice | 6.1 — foundation schema |
| Mode | 4 (spec-author) |
| Author HEAD | `5b0aa23` (post-audit) |
| Spec authored | 2026-04-26 |
| Implementation slice | TBD (will follow this spec) |
| BACKLOG row | none yet — implementation slice files at execution time per R17 (next free is `B-061`) |
| Audit dependency | `docs/audits/phase-6-scout.md` (commit `5b0aa23`) — §1 study engine, §1.1 card/category model, §1.2 FSRS, §1.3 free-tier wall, §6.3 internal analytics tables, §7.1 admin UI |
| Slice dependencies | None upstream. **Blocks** every other Phase 6 slice (per audit cross-cutting #3 + slice-by-slice notes for 6.0, 6.4, 6.5, 6.6, 6.10). |

### Phase 6 locked decisions referenced by this spec

> Recorded in front-matter so spec readers see the locks without
> chasing SESSION-STATE. Rationale lives in §11 (Decisions) below.

| ID | Decision |
|----|----------|
| **G2** | Background jobs: **RQ on Redis** for ingestion (slice 6.10), **Railway cron** for daily Pro digest (slice 6.14). |
| **H1** | Object storage: **Cloudflare R2** for ingestion artifacts (slice 6.10). **`hirelens-backend/app/data/decks/seed_lessons/*.md`** for the 12 locked-deck seed content (slice 6.4.5). |
| **I1** | Events: **dual-write**. PostHog for funnels/retention; Postgres `quiz_review_events` + `lesson_view_events` for the content-quality / retention dashboards (spec #38 banned HogQL in `/admin/analytics`). Tables built in slice 6.0; this spec defines the FK targets. |
| **J2** | Quality signals table: `card_quality_signals` keyed `(id, lesson_id, quiz_item_id NULLABLE, signal_source, dimension)`. Built in slice 6.13.5. This slice does NOT define it; spec records that it lives on the Phase-6 horizon so the FK target `lessons.id` and the optional `quiz_items.id` it points to exist. |

---

## 1. Problem

Phase 6 introduces a content lifecycle platform: greenfield deck/lesson
schema, lesson-card UX, three-layer quality system, persona-aware Learn
page, AI ingestion, Pro-only daily digest, admin authoring UI, FSRS
retention dashboard. 18 slices total (after merge of original 6.7+6.12
into a single Learn-page composition slice).

The existing flat `cards` + `categories` schema (audit §1.1) is
load-bearing across study-engine, gap-mapping, admin-CRUD,
home-state, progress-analytics, mission, and experience-narrative
surfaces. Phase 6's locked decision retires that schema and replaces it
with a four-table content model: **decks** (12 locked top-level
buckets), **lessons** (the unit of teaching content rendered as a
multi-section card on the Learn page), **quiz_items** (atomic
FSRS-reviewable recall units owned by a lesson), and
**quiz_item_progress** (per-user FSRS state, direct analog of
`card_progress`).

This spec defines those four tables at column granularity with
indexes, constraints, and the consumer blast radius the implementation
slice will need to address. It does **not** specify model file
contents, Alembic migration code, route handlers, service refactors,
or test plans — those are the implementation slice's deliverables.

## 2. Goals

1. Lock the four foundation tables (decks, lessons, quiz_items,
   quiz_item_progress) at column granularity so subsequent slices
   (6.0 events, 6.2 metadata, 6.4 admin UI, 6.5 lesson UX, 6.6
   ranker, 6.10 ingestion, 6.13.5 quality signals) reference them by
   column name without ambiguity.
2. Lock the FSRS-binds-to-quiz_item-only invariant (substantive
   lesson edits do **not** reset FSRS state; substantive quiz_item
   edits retire the row via `retired_at` + `superseded_by_id`).
3. Lock the retirement plan for the existing `cards` / `categories` /
   `card_progress` / `card_feedback` tables: enumerate every consumer
   the implementation slice must rewrite. **Drop is deferred to slice
   6.15 (cleanup)** — keeps a rollback path through the rest of Phase 6.
4. Declare the analytics events that operations against these tables
   will emit, so slice 6.0 (events table) can pre-shape its column
   set.

## 3. Non-goals

- `card_metadata` (tech_tags, scenario_type, seniority, prerequisites,
  difficulty refinement) — slice 6.2 spec resolves.
- `card_quality_signals` table — slice 6.13.5 spec resolves.
- `source_content` table (admin uploads, ingestion provenance) —
  slice 6.9 / 6.10 spec resolves. Referenced here as a NULLABLE FK
  target on `lessons.source_content_id` so manually-authored lessons
  remain valid.
- Events table column shape (`quiz_review_events`,
  `lesson_view_events`) — slice 6.0 spec resolves.
- Seed data loading mechanism for the 12 locked decks — slice 6.4.5
  spec resolves (audit Q8; chat-Claude recommends
  `scripts/seed_phase6_decks.py`).
- Edit-classification rule logic (the >15 % char-delta rule) — slice
  6.9 spec resolves. This spec **stores** the result on
  `lessons.version` + `lessons.version_type` but does not define how
  the classification is computed.
- Cold-start behavior for Interview-Prepper Pro users with no Lens
  scan — slice 6.7 spec resolves (audit Q7).
- Migration code, model file contents, route handlers, service
  refactors, tests, FE changes — implementation slice (one-step
  follow-up to this spec).

## 4. Schema definitions

> Conventions follow the existing codebase per `db-migration.md` and
> CODE-REALITY §2:
> - PK columns are `String(36)` (UUID stored as string — deferred
>   promotion to native UUID is Phase-0 known debt).
> - Timestamp columns are `DateTime(timezone=True)` with `server_default=func.now()`
>   (matches the post-Phase-5 pattern; e.g.
>   `paywall_dismissals.dismissed_at`, `admin_audit_log.created_at`).
> - `archived_at` / `retired_at` / `deleted_at` follow the soft-delete
>   pattern already used by `cards.deleted_at` and the
>   subscription-related downgrades.
> - ENUM columns are stored as `String(N)` with the value set declared
>   in a Python `Literal` / Pydantic enum on the schema layer (matches
>   `card_progress.state` and `tracker.status` patterns rather than
>   Postgres-native ENUM, which complicates Alembic).
> - Numeric columns for FSRS values are `Float` (matches existing
>   `card_progress.stability` / `.difficulty_fsrs` shape — not
>   `Numeric` — to keep `quiz_item_progress` byte-identical with
>   `card_progress` modulo the FK swap).
> - `quality_score` on `lessons` is `Numeric(3,2)` per the prompt
>   (different from FSRS columns; this is product analytics, not
>   scheduler input).

### 4.1 Table 1 — `decks`

The 12 top-level curriculum buckets. Replaces the role of
`categories` for Phase 6 content.

| Column | Type | Constraints / Default | Notes |
|--------|------|----------------------|-------|
| `id` | `String(36)` | PK | UUID-as-string per §4 conventions |
| `slug` | `String(100)` | UNIQUE NOT NULL | URL-safe (`transformer-llm-internals`, `agentic-systems-mcp`, etc.). Stable identifier; titles can change without breaking links / analytics. |
| `title` | `String(200)` | NOT NULL | Human-readable (e.g. "Transformer & LLM Internals") |
| `description` | `Text` | NOT NULL | 2–4 sentence elevator pitch surfaced on the Learn page deck card |
| `display_order` | `Integer` | NOT NULL DEFAULT 0 | Sort order within the deck list |
| `icon` | `String(10)` | NULLABLE | Emoji or short identifier (mirrors `categories.icon`) |
| `persona_visibility` | `String(20)` | NOT NULL DEFAULT `'both'` | ENUM-as-String: `'climber'`, `'interview_prepper'`, `'both'`. Drives Learn-page filtering for slice 6.7 (persona-aware composition). |
| `tier` | `String(20)` | NOT NULL DEFAULT `'premium'` | ENUM-as-String: `'foundation'`, `'premium'`. Replaces `categories.source`. `'foundation'` decks are free-tier accessible; `'premium'` are Pro-gated (audit §1.3). |
| `created_at` | `DateTime(timezone=True)` | NOT NULL, `server_default=func.now()` | |
| `updated_at` | `DateTime(timezone=True)` | NOT NULL, `server_default=func.now()`, `onupdate=func.now()` | |
| `archived_at` | `DateTime(timezone=True)` | NULLABLE | Soft-delete pattern. Archived decks are excluded from Learn page queries; FK references stay intact for audit. |

**Indexes:**

- `(persona_visibility, display_order)` partial WHERE `archived_at IS NULL` — Learn page primary query (slice 6.7 ranker reads "all visible decks for persona X").
- `slug` — UNIQUE constraint provides this implicitly.

**Free-tier gate semantics.** The implementation slice replicates the
existing `_is_free(user)` filter pattern (audit §1.3) but reads
`decks.tier = 'foundation'` instead of `categories.source = 'foundation'`. No
behavior change for free users — same one-deck-tier gate, new column
name. The `tier` column is the **canonical** source for "is this
content free-accessible". (Future per-deck pricing tiers — out of Phase
6 scope.)

### 4.2 Table 2 — `lessons`

The unit of teaching content. One lesson = one card on the Learn page
(concept + production + examples + quiz panel rendered as a single
multi-section view per the locked Phase 6 lesson-card UX).

| Column | Type | Constraints / Default | Notes |
|--------|------|----------------------|-------|
| `id` | `String(36)` | PK | |
| `deck_id` | `String(36)` | FK → `decks.id` ON DELETE RESTRICT, NOT NULL, indexed | RESTRICT (not CASCADE) — deleting a deck with lessons should fail loudly; archive the deck instead via `archived_at`. |
| `slug` | `String(100)` | NOT NULL, composite UNIQUE on `(deck_id, slug)` | URL-safe lesson identifier within deck. |
| `title` | `String(200)` | NOT NULL | |
| `concept_md` | `Text` | NOT NULL | Markdown for the "concept explanation" section. Required — every lesson explains its concept. |
| `production_md` | `Text` | NOT NULL | Markdown for "how this is used in production". Required — separates this curriculum from generic study material. |
| `examples_md` | `Text` | NOT NULL | Markdown with concrete examples / code blocks. Required — examples are non-negotiable per the Phase 6 lesson-card UX locked decision. |
| `display_order` | `Integer` | NOT NULL DEFAULT 0 | Within deck. |
| `version` | `Integer` | NOT NULL DEFAULT 1 | Increments on substantive edits per slice 6.9's edit-classification rule. |
| `version_type` | `String(20)` | NOT NULL DEFAULT `'initial'` | ENUM-as-String: `'initial'`, `'minor_edit'`, `'substantive_edit'`. Set by slice 6.9 logic; this column stores the result. |
| `published_at` | `DateTime(timezone=True)` | NULLABLE | NULL = in admin review queue (lesson is drafted but not user-visible). Non-null = visible to users. Replaces "is_published bool" — timestamp lets us measure draft → publish latency. |
| `generated_by_model` | `String(64)` | NULLABLE | Model identifier (e.g. `'gemini-2.5-pro'`) for AI-generated lessons; NULL for hand-authored. |
| `source_content_id` | `String(36)` | NULLABLE FK → `source_content.id` ON DELETE SET NULL | NULLABLE means "manually authored, not from ingestion". `source_content` table defined in slice 6.9; FK target may not exist at this slice's implementation time — if so, the FK is added as a **deferred constraint** in slice 6.9's migration. |
| `quality_score` | `Numeric(3,2)` | NULLABLE | 0.00–1.00 from cross-model critique; populated by slice 6.11 (or earlier per slice 6.5's quality wiring). NULL = not yet evaluated. |
| `created_at` | `DateTime(timezone=True)` | NOT NULL, `server_default=func.now()` | |
| `updated_at` | `DateTime(timezone=True)` | NOT NULL, `server_default=func.now()`, `onupdate=func.now()` | |
| `archived_at` | `DateTime(timezone=True)` | NULLABLE | Soft-delete. Archived lessons are excluded from Learn page; existing quiz_item_progress rows stay intact for analytics. |

**Indexes:**

- `(deck_id, display_order)` partial WHERE `archived_at IS NULL` — primary deck-detail query.
- `(published_at)` partial WHERE `published_at IS NULL` — admin review queue ("show me unpublished lessons").
- `(deck_id, archived_at)` — supports `archived_at IS NULL` filter on the active-lesson lookup path.
- `(source_content_id)` — when slice 6.9 lands the FK, this supports "show me all lessons generated from this source".

**FK target deferral.** `source_content_id` references a table that
does not yet exist. The implementation slice has two clean options:
(a) declare the column NULLABLE without an FK in this migration, and
slice 6.9 adds the FK constraint atomically with the table; or (b)
ship `source_content` as a stub table in this implementation slice
(empty, no app code reading it) so the FK can land cleanly here.
**Implementation slice picks (a)** — keeps this slice's blast radius
minimal and respects the non-goal that 6.9's spec owns the
source_content shape.

### 4.3 Table 3 — `quiz_items`

The atomic FSRS-reviewable recall unit. A lesson has 1+ quiz_items.
**Substantive quiz edits retire the row** (set `retired_at`, link
`superseded_by_id` to the new row) — this is what makes the
lesson/quiz_item split work for FSRS stability per the locked
decision.

| Column | Type | Constraints / Default | Notes |
|--------|------|----------------------|-------|
| `id` | `String(36)` | PK | |
| `lesson_id` | `String(36)` | FK → `lessons.id` ON DELETE CASCADE, NOT NULL, indexed | CASCADE — deleting a lesson removes its quiz items (and via further CASCADE on quiz_item_progress, their FSRS state). Delete-via-archive is the user-facing path; CASCADE only fires on hard-delete which is admin-only. |
| `question` | `Text` | NOT NULL | |
| `answer` | `Text` | NOT NULL | Canonical correct answer. |
| `question_type` | `String(20)` | NOT NULL DEFAULT `'free_text'` | ENUM-as-String: `'mcq'`, `'free_text'`, `'code_completion'`. |
| `distractors` | `JSONB` | NULLABLE | Array of strings for `'mcq'`. NULL for `'free_text'` and `'code_completion'`. |
| `difficulty` | `String(10)` | NOT NULL DEFAULT `'medium'` | ENUM-as-String: `'easy'`, `'medium'`, `'hard'`. Surfaced to py-fsrs as initial difficulty hint at first review (the implementation slice maps `easy → 0.3`, `medium → 0.5`, `hard → 0.7` or similar — out of scope here, slice 6.5 ties down). |
| `display_order` | `Integer` | NOT NULL DEFAULT 0 | Within lesson. |
| `version` | `Integer` | NOT NULL DEFAULT 1 | Tracks substantive-edit history. |
| `superseded_by_id` | `String(36)` | NULLABLE FK → `quiz_items.id` ON DELETE SET NULL (self-reference) | When a substantive edit fires, the OLD row's `superseded_by_id` points to the NEW row; the old row's `retired_at` is also set. Forward-link semantic so a reader can walk old → new. |
| `retired_at` | `DateTime(timezone=True)` | NULLABLE | Non-null = no longer shown to new reviewers. Existing `quiz_item_progress` rows pointing to this row stay intact (FSRS history is preserved for analytics) but no NEW progress rows are created against it. |
| `generated_by_model` | `String(64)` | NULLABLE | Model identifier for AI-generated; NULL for hand-authored. |
| `created_at` | `DateTime(timezone=True)` | NOT NULL, `server_default=func.now()` | |
| `updated_at` | `DateTime(timezone=True)` | NOT NULL, `server_default=func.now()`, `onupdate=func.now()` | |

**Indexes:**

- `(lesson_id, retired_at, display_order)` partial WHERE `retired_at IS NULL` — primary active-quiz lookup ("give me the active quizzes for lesson X in display order").
- `(superseded_by_id)` — forward-linkage queries (rare, but cheap).
- `lesson_id` — FK index for cascade lookups.

**Retirement semantic.** The locked decision says "substantive quiz_item
edits retire the old quiz_item and create a new one." The
implementation slice chooses between (a) admin UI computes the edit
classification and decides at edit time, or (b) classification logic
runs as a service helper and the route picks. Either way, the
**database invariant** this spec locks is: a quiz_item with
`retired_at IS NOT NULL` must NOT receive new
`quiz_item_progress` rows (enforced at the service layer, not via DB
constraint, since service-layer ownership is cleaner — adding a row to
a retired quiz is a programming error, not a constraint we want a 23000
SQLSTATE for).

### 4.4 Table 4 — `quiz_item_progress`

FSRS state per `(user, quiz_item)`. **Direct analog of
`card_progress`** (audit §1.1, `app/models/card_progress.py`) with the
FK retargeted from `cards` to `quiz_items`. The FSRS column shape is
**byte-identical** to `card_progress` modulo the FK swap — this is
intentional so the implementation slice can copy `study_service`'s
FSRS reconstruction logic verbatim.

| Column | Type | Constraints / Default | Notes |
|--------|------|----------------------|-------|
| `id` | `String(36)` | PK | |
| `user_id` | `String(36)` | FK → `users.id` ON DELETE CASCADE, NOT NULL, indexed | Mirrors `card_progress.user_id`. |
| `quiz_item_id` | `String(36)` | FK → `quiz_items.id` ON DELETE CASCADE, NOT NULL, indexed | Mirrors `card_progress.card_id`. |
| `state` | `String(20)` | NOT NULL DEFAULT `'new'` | Values: `'new'`, `'learning'`, `'review'`, `'relearning'` (mirrors `_STATE_TO_FSRS` in `study_service.py:52-57`). |
| `stability` | `Float` | NOT NULL DEFAULT 0.0 | py-fsrs scheduler value. |
| `difficulty_fsrs` | `Float` | NOT NULL DEFAULT 0.0 | Distinct from `quiz_items.difficulty` (which is the static authored hint); this is the live FSRS-managed value. |
| `elapsed_days` | `Float` | NOT NULL DEFAULT 0.0 | Mirrors `card_progress.elapsed_days` (Float, not Integer — fractional days are written by `_apply_fsrs_result`). |
| `scheduled_days` | `Float` | NOT NULL DEFAULT 0.0 | Same — Float to match. |
| `reps` | `Integer` | NOT NULL DEFAULT 0 | |
| `lapses` | `Integer` | NOT NULL DEFAULT 0 | |
| `fsrs_step` | `Integer` | NULLABLE | py-fsrs v6 learning/relearning step index; NULL when in `Review` state (matches existing `card_progress.fsrs_step`). |
| `last_reviewed` | `DateTime(timezone=True)` | NULLABLE | NULL = never reviewed. |
| `due_date` | `DateTime(timezone=True)` | NOT NULL, `server_default=func.now()` | Mirrors `card_progress.due_date` (note: the existing column is non-nullable with default `now()`; the prompt allowed NULLABLE here, but matching the existing `card_progress` shape is strictly better — keeps `study_service` query patterns identical). |
| `created_at` | `DateTime(timezone=True)` | NOT NULL, `server_default=func.now()` | |
| `updated_at` | `DateTime(timezone=True)` | NOT NULL, `server_default=func.now()`, `onupdate=func.now()` | |

**Constraints:**

- `UNIQUE (user_id, quiz_item_id)` — same `uq_card_progress_user_card` pattern (named `uq_quiz_item_progress_user_quiz`).

**Indexes:**

- `(user_id, due_date)` — daily review primary query (mirrors `card_progress` index pattern from audit §1.2). The implementation slice's `quiz_item_service.get_daily_review` reads this exact index for the `due_date <= now` ORDER BY ASC LIMIT 5 pattern.
- `(quiz_item_id)` — supports "all reviewers of this quiz" / per-quiz analytics queries.
- `user_id` — FK index for cascade.

**Drift from prompt.** The prompt described `due_date` as `TIMESTAMPTZ NULLABLE`. The existing `card_progress.due_date` is `NOT NULL server_default=func.now()`. This spec keeps the existing shape so the implementation slice can copy `study_service.get_daily_review`'s WHERE clause without the null-handling branch. Recorded as Decision **D-1** in §11.

## 5. Retirement plan — existing `cards` / `categories` / `card_progress` / `card_feedback`

> **Drop is deferred to slice 6.15 (cleanup).** Keeping the legacy
> tables through Phase 6 preserves a rollback path if greenfield
> content authoring (slice 6.4.5) reveals a schema flaw. Once the 18
> Phase 6 slices ship and 30+ lessons exist on disk, the legacy
> tables are safe to drop. The implementation slice for 6.1 leaves
> them in place; it adds the new tables alongside.

### 5.1 Tables to drop in slice 6.15 (NOT this slice)

- `cards` (`hirelens-backend/app/models/card.py`)
- `card_progress` (`hirelens-backend/app/models/card_progress.py`) —
  data is greenfield-acceptable; existing FSRS state does not migrate.
- `card_feedback` (`hirelens-backend/app/models/card_feedback.py`)
- `categories` (`hirelens-backend/app/models/category.py`)

Slice 6.15 also drops the FE `Card` interface
(`hirelens-frontend/src/types/index.ts:148`) and the lone direct
import (`hirelens-frontend/src/hooks/useCardViewer.ts:3` per audit §1.4).

### 5.2 Consumers requiring rewrite in the slice 6.1 IMPLEMENTATION slice

> Sourced from `grep -lrn "from app.models.card\|from
> app.models.category" hirelens-backend/app --include="*.py"` and
> audit §1.4 / §6 / §7.

**Backend services** (re-import `Lesson` / `QuizItem` / `Deck` / `QuizItemProgress`):

| File | Current usage | Implementation-slice action |
|------|---------------|------------------------------|
| `hirelens-backend/app/models/__init__.py` | Re-exports `Card`, `Category`, `CardProgress`, `CardFeedback` | Add `Deck`, `Lesson`, `QuizItem`, `QuizItemProgress` re-exports alongside. |
| `hirelens-backend/app/services/study_service.py` | FSRS daily-review + `_check_daily_wall` + review-card path read `Card`, `CardProgress`, `Category` | Implementation slice migrates the daily-review path to read `QuizItem` / `QuizItemProgress` and filters via `Deck.tier='foundation'` (replacing `Category.source='foundation'`). The free-tier daily wall logic (audit §1.3) stays unchanged — it counts review submissions, not specific tables. |
| `hirelens-backend/app/services/card_service.py` | Plan-gated category + card reads | Migrate to `Deck` / `Lesson` / `QuizItem` reads. The legacy endpoint shape (`/api/v1/cards/...`) stays during Phase 6 to keep FE stable until slice 6.7 lands the new Learn surface. |
| `hirelens-backend/app/services/card_admin_service.py` | Admin CRUD on `Card` / `Category` | Implementation slice does NOT touch this — admin UI for the new schema is slice 6.4. Legacy admin remains operating on legacy tables until 6.15 cleanup. |
| `hirelens-backend/app/services/gap_mapping_service.py` | Maps ATS gaps → categories via `categories.tags` JSONB join + pgvector cosine over `cards.embedding` (audit §2.4) | Implementation slice does NOT touch this in 6.1. Slice 6.6 (Lens-ranked deck/card ordering) re-targets gap-mapping to decks/lessons. Until then, gap-mapping continues to read the legacy tables (which is fine — categories/cards stay populated through Phase 6). |
| `hirelens-backend/app/services/mission_service.py` | Reads `Card` for mission daily-card selection | Out of scope for slice 6.1 implementation. Mission Mode operates on the legacy schema until a Phase-6 follow-up retires it (out of the 18-slice plan). |
| `hirelens-backend/app/services/experience_service.py` | Reads `CardProgress` for "experience narrative" generation | Out of scope for slice 6.1 implementation. Slice 6.15 cleanup OR a future slice migrates the narrative source. |
| `hirelens-backend/app/services/home_state_service.py` | Reads `CardProgress` for `last_review_at` (audit §1.5 / home-state evaluator) | Implementation slice updates this to ALSO read `QuizItemProgress` so home-state correctly reflects Phase 6 reviews. Dual-read until 6.15 cleanup. |
| `hirelens-backend/app/services/onboarding_checklist_service.py` | Reads `Card` for "studied N cards" telemetry checklist | Out of scope for slice 6.1 implementation. Audit later — check if checklist needs to count quiz_item reviews instead. |
| `hirelens-backend/app/services/progress_service.py` | Reads `CardProgress` for radar + heatmap (audit §6.4 surface) | Out of scope for slice 6.1 implementation. Slice 6.16 (FSRS retention dashboard) re-platforms this. |
| `hirelens-backend/app/services/admin_analytics_service.py` | Reads `CardProgress`, `Subscription` for admin metrics (audit §6.4) | Implementation slice updates this to read BOTH `CardProgress` AND `QuizItemProgress` (UNION) so admin metrics include Phase 6 activity. Dual-read until 6.15. |
| `hirelens-backend/app/services/reminder_service.py` | Daily reminder query joins `EmailPreference` × `CardProgress` (cards due today) | Implementation slice updates the cards-due query to UNION `card_progress` + `quiz_item_progress` (both keyed by `due_date <= now`). Email cadence unchanged. |
| `hirelens-backend/app/api/v1/routes/feedback.py` | `card_feedback` writes | Out of scope for slice 6.1 implementation. The new quality-signal table (slice 6.13.5) takes over the user-thumbs path; `card_feedback` continues operating on the legacy schema until then. |
| `hirelens-backend/app/api/v1/routes/study.py` | `_is_free` filter + daily/review/progress endpoints | Implementation slice updates daily + review endpoints to operate on `QuizItem` / `QuizItemProgress`. The `_is_free` helper itself doesn't change. |

**Frontend** (audit §1.4 — single direct `Card` consumer):

| File | Current usage | Implementation-slice action |
|------|---------------|------------------------------|
| `hirelens-frontend/src/types/index.ts:148-158` | Defines `Card` interface | Add `Lesson`, `QuizItem`, `Deck`, `QuizItemProgress` interfaces alongside; keep `Card` until slice 6.15. |
| `hirelens-frontend/src/hooks/useCardViewer.ts:3` | Imports `Card` | Out of scope for slice 6.1 implementation; kept until lesson-card UX (slice 6.5) replaces the single-card viewer. |
| `hirelens-frontend/src/types/index.ts:181-228` | `DailyCard`, `DailyQueueResponse`, `DailyStatus` | Implementation slice adds parallel `DailyQuizItem` / `DailyQuizQueueResponse` shapes. `DailyStatus` is reusable as-is (the daily wall counter is surface-agnostic). |
| `hirelens-frontend/src/components/study/QuizPanel.tsx` | Submit chokepoint for `POST /api/v1/study/review` (audit §1.4) | Out of scope for slice 6.1 implementation. Slice 6.5 updates QuizPanel to submit to the quiz_item endpoint. |
| `hirelens-frontend/src/pages/DailyReview.tsx` + `CardViewer.tsx` + `MissionMode.tsx` | Card-based daily/single/mission views | Out of scope for slice 6.1 implementation. The new lesson-card UX (slice 6.5) introduces `DailyLessonReview` etc.; legacy views remain. |
| `hirelens-frontend/src/pages/StudyDashboard.tsx` | Renders categories from `GET /api/v1/cards` | Out of scope for slice 6.1 implementation. Slice 6.7 (Learn page composition) re-platforms the deck list. |

**Routes table impact.** The implementation slice mounts new
`/api/v1/lessons` / `/api/v1/decks` / `/api/v1/quiz-items` /
`/api/v1/quiz-review` routers (exact paths chosen by the
implementation slice — not mandated here). The legacy `/api/v1/cards`
+ `/api/v1/study/...` routes stay alive throughout Phase 6. Slice 6.15
(cleanup) drops them.

### 5.3 What the slice 6.1 IMPLEMENTATION slice ships

Based on §5.2 above, the minimum implementation-slice scope:

1. Four new model files (`app/models/deck.py`, `lesson.py`,
   `quiz_item.py`, `quiz_item_progress.py`).
2. One Alembic migration `<rev>_phase6_foundation_schema.py` creating
   the four tables with the indexes/constraints from §4.
3. Re-exports in `app/models/__init__.py`.
4. Pydantic schemas in `app/schemas/` for the new tables (separate
   files so slice 6.0 / 6.4 / 6.5 can extend without circular imports).
5. **No** route handlers, **no** service refactors, **no** FE changes.
   Adding tables but no consumers keeps the slice surgical and
   matches Phase 5's pattern (e.g. `paywall_dismissals` landed before
   the service that wrote to it).
6. Tests: schema-shape + index-presence asserts (`test_phase6_schema.py`).
   No FSRS-behavior tests yet — those land in slice 6.5 when
   `quiz_item_service.review_quiz_item` ships.

The remaining service / route / FE rewrites land in their dedicated
slices (6.0, 6.4, 6.5, 6.7, etc.). This spec is **schema only**.

## 6. Analytics events emitted by this schema

Per the analytics-as-foundation rule, every Phase 6 spec declares
which events its schema's operations will emit. Slice 6.0 builds the
events table; this spec just declares the contract so 6.0's column
shape can pre-accommodate.

> Per Decision **I1** (front-matter), all Phase 6 events dual-write to
> PostHog (funnel/retention) AND Postgres (`quiz_review_events` /
> `lesson_view_events` / generic event log to be specced in slice 6.0).

| Event | Emit point | Properties | PostHog | Postgres |
|-------|------------|-----------|---------|----------|
| `lesson_published` | BE `lesson_admin_service.publish_lesson` (slice 6.4) — fires when `lessons.published_at` transitions NULL → non-NULL | `{admin_id, lesson_id, deck_id, version, version_type, generated_by_model: str \| null}` | ✓ | ✓ (lesson lifecycle audit) |
| `lesson_archived` | BE `lesson_admin_service.archive_lesson` — fires when `lessons.archived_at` set | `{admin_id, lesson_id, deck_id, was_published: bool}` | ✓ | ✓ |
| `quiz_item_retired` | BE `quiz_item_admin_service.retire_quiz_item` — fires when `quiz_items.retired_at` set + `superseded_by_id` linked | `{admin_id, quiz_item_id, lesson_id, superseded_by_id, prior_version: int}` | ✓ | ✓ |
| `quiz_item_progress_initialized` | BE `quiz_item_service.review_quiz_item` (slice 6.5) — fires on first review against a quiz_item (creates the progress row) | `{user_id, quiz_item_id, lesson_id, deck_id, plan, persona}` | ✓ | ✓ (powers slice 6.16's first-touch retention metric) |
| `deck_persona_visibility_changed` | BE `deck_admin_service.update_deck` — fires when `decks.persona_visibility` column changes | `{admin_id, deck_id, prior_value, new_value}` | ✓ | ✓ |

**Event payload conventions** (mirror `.agent/skills/analytics.md`):

- `snake_case` event names; flat property dicts.
- Backend events pass `user_id` / `admin_id` first (analytics
  `track()` signature).
- Idempotency: BE events fire from the service layer at the end of the
  successful transaction — not from FE on action click — so a 500
  partway through doesn't leave a misleading event in PostHog.

These five events are the **minimum contract**. Slice 6.4 (admin UI),
6.5 (lesson UX), 6.6 (ranker), 6.7 (Learn page), 6.10 (ingestion) will
each add their own events when they ship; this spec doesn't pre-empt
them.

## 7. Acceptance criteria

The implementation slice (one-step follow-up) must pass:

- **AC-1** — Alembic `upgrade head → downgrade -1 → upgrade head`
  cleanly. Per `db-migration.md` rule 2.
- **AC-2** — All four tables exist on disk with the columns,
  constraints, indexes, and defaults specified in §4. Verified by a
  schema-introspection test (`test_phase6_schema.py`).
- **AC-3** — `decks` has UNIQUE on `slug`; `lessons` has composite
  UNIQUE on `(deck_id, slug)`; `quiz_item_progress` has UNIQUE on
  `(user_id, quiz_item_id)` (named `uq_quiz_item_progress_user_quiz`
  for symmetry with `uq_card_progress_user_card`).
- **AC-4** — `quiz_items.superseded_by_id` is a self-referential FK
  with ON DELETE SET NULL.
- **AC-5** — `lessons.source_content_id` is `String(36) NULLABLE`
  with NO FK constraint at this slice's migration time. Slice 6.9 adds
  the FK once `source_content` exists.
- **AC-6** — `quiz_item_progress` schema is byte-identical (modulo
  FK swap) to `card_progress`. Verified by a schema-diff test that
  reflects both tables and asserts column type equivalence.
- **AC-7** — Legacy tables `cards`, `categories`, `card_progress`,
  `card_feedback` still exist on disk after the implementation slice.
  No DROP statements in the migration.
- **AC-8** — No new route handlers, no service refactors, no FE
  changes ship in the implementation slice. Verified by `git diff
  --stat` showing only `app/models/`, `app/schemas/`, `alembic/`,
  `tests/` paths touched.
- **AC-9** — `app/models/__init__.py` re-exports the four new models
  alongside the existing ones.
- **AC-10** — Test suite stays green. New schema-shape tests run
  under the default `not integration` selector (no LLM keys required).

## 8. Test plan (implementation slice)

> This spec lists tests the implementation slice will add. No test
> code is written in this spec slice.

- `tests/test_phase6_schema.py::test_decks_table_shape` — column types,
  defaults, indexes, UNIQUE on slug.
- `tests/test_phase6_schema.py::test_lessons_table_shape` — column
  types, defaults, indexes (incl. partial WHERE clauses), composite
  UNIQUE on (deck_id, slug), FK to decks ON DELETE RESTRICT,
  source_content_id is NULLABLE String(36) without FK constraint at
  this revision.
- `tests/test_phase6_schema.py::test_quiz_items_table_shape` — column
  types, defaults, indexes, FK to lessons ON DELETE CASCADE,
  self-referential FK on superseded_by_id with ON DELETE SET NULL.
- `tests/test_phase6_schema.py::test_quiz_item_progress_table_shape`
  — column types, defaults, indexes, UNIQUE
  `uq_quiz_item_progress_user_quiz`, FK to users + quiz_items both
  ON DELETE CASCADE.
- `tests/test_phase6_schema.py::test_quiz_item_progress_mirrors_card_progress`
  — reflects both `card_progress` and `quiz_item_progress`, asserts
  every column on `card_progress` (except `card_id`) has an
  equivalent column with matching type and default on
  `quiz_item_progress` (with `card_id` → `quiz_item_id` rename).
- `tests/test_phase6_schema.py::test_alembic_round_trip` — upgrade
  → downgrade → upgrade leaves the database identical (schema
  introspection diff = empty).
- `tests/test_phase6_schema.py::test_legacy_tables_intact` — assert
  `cards`, `categories`, `card_progress`, `card_feedback` still exist
  post-migration.

## 9. Manual post-deploy verification (implementation slice)

After the implementation slice ships:

1. SSH to the Railway PG instance (or psql to the deployed URL) and
   `\d decks`, `\d lessons`, `\d quiz_items`, `\d quiz_item_progress`
   — confirm columns + indexes match §4.
2. Confirm legacy tables still exist: `\d cards`, `\d categories`,
   `\d card_progress`, `\d card_feedback`.
3. Confirm row counts on legacy tables are unchanged (no
   accidental TRUNCATE in the migration).
4. Spot-check `alembic history` shows the new revision at HEAD, with
   `down_revision` pointing at `30bf39fa04f8` (current head per
   CODE-REALITY §5).

No app-behavior verification — slice 6.1 implementation has no live
consumer of the new tables. That comes in slice 6.4 / 6.5 onwards.

## 10. UI / UX

**None.** Schema-only spec. Slice 6.5 specs the lesson-card UX; slice
6.7 specs the Learn-page composition; slice 6.4 specs the admin
authoring UI.

## 11. Decisions

> Phase-level decisions referenced here use the IDs from this slice's
> front-matter (G2, H1, I1, J2). Slice-local decisions are numbered
> D-1, D-2, …

### Phase-level decision rationale

- **G2 (background jobs).** RQ on Redis is the right tradeoff for
  Phase 6: Redis is already a hard dep (daily-card wall counter,
  `geo_pricing_service` cache, `home_state_service` cache,
  `admin_analytics_service` cache). RQ has no extra infra surface
  beyond a single worker process. Celery would add a broker config
  decision and a results-backend decision; Dramatiq adds a different
  set of operational quirks. Daily Pro digest stays on Railway cron
  because the cadence is fixed (1 × day) and no fan-out is needed —
  forcing it into RQ would add complexity without benefit. Audit §7.3
  + §5.2 are the underlying findings.
- **H1 (object storage).** Cloudflare R2 was already named in
  AGENTS.md but never wired (audit §7.2 — "aspirational"); slice 6.10
  wires it for ingestion artifacts (generated lesson Markdown drafts,
  critique reports, source uploads). For the 12 locked-deck seed
  content, `app/data/decks/seed_lessons/*.md` keeps everything in-repo
  and version-controlled — slice 6.4.5 reads it in via a one-time
  seed script. R2 is the right call for ingestion (variable-volume,
  durable, low-egress) and `app/data/` is the right call for seeds
  (small, fixed, change-controlled via PR).
- **I1 (events).** Spec #38 banned the PostHog Query API in
  `/admin/analytics`, so the slice 6.16 (FSRS retention) and slice
  6.13/6.13.5 (quality-signal dashboards) need a Postgres event
  source. PostHog stays for funnels (where HogQL excels) and product
  retention. Dual-write is simpler than picking one storage and
  building a sync. Storage cost is bounded — events are light JSON
  rows with a TTL the slice 6.0 spec sets.
- **J2 (quality signals key).** The locked decision says
  `card_quality_signals` is keyed `(id, lesson_id, quiz_item_id
  NULLABLE, signal_source, dimension)`. The NULLABLE `quiz_item_id`
  is the bridge: AI critique that targets the lesson as a whole
  (concept_md / production_md / examples_md cohesion) leaves
  `quiz_item_id` NULL; AI critique that targets a specific quiz_item
  (answer correctness, distractor quality) populates it. Slice 6.13.5
  defines the signal_source / dimension vocabularies. **Open
  question Q1 from the audit is implicitly resolved here**: `quiz_item_id`
  is NULLABLE, so both lesson-level and quiz-item-level critique fit
  the same table without a discriminator collision.

### Slice-local decisions

- **D-1 — `quiz_item_progress.due_date` NOT NULL with `server_default=func.now()`.**
  The prompt described `due_date TIMESTAMPTZ NULLABLE`. The existing
  `card_progress.due_date` (which this column intentionally mirrors)
  is `NOT NULL server_default=func.now()`. Keeping the existing shape
  lets the implementation slice copy `study_service.get_daily_review`'s
  WHERE clause (`due_date <= now`) without the null-handling branch.
  No semantic loss — a never-reviewed card has `due_date = created_at`
  (i.e. immediately due), which is the correct behavior for a
  "new" card.
- **D-2 — `lessons.source_content_id` ships without FK constraint.**
  The FK target (`source_content`) does not exist until slice 6.9.
  The two clean options are (a) NULLABLE column without FK in this
  slice, FK added in 6.9, or (b) ship `source_content` as a stub
  table in this slice's implementation. Picked (a) — keeps this
  slice's blast radius minimal and respects the non-goal that 6.9
  owns the source_content shape. The FK constraint is a one-line
  Alembic add in 6.9's migration.
- **D-3 — ENUM-as-String storage.** Postgres-native ENUM types
  complicate Alembic (renames, additions, removals all require
  custom SQL). The existing codebase uses `String(N)` everywhere
  (`card_progress.state`, `tracker.status`, `subscription.plan`, etc.)
  with the value set declared in Pydantic. Phase 6 keeps that
  convention.
- **D-4 — Float (not Numeric) for FSRS columns.** `card_progress`
  uses `Float`. `quiz_item_progress` mirrors it. `lessons.quality_score`
  is `Numeric(3,2)` because that's product analytics (deterministic
  rounding matters), not scheduler input.
- **D-5 — `archived_at` (soft-delete) on decks + lessons; `retired_at`
  on quiz_items; no soft-delete on quiz_item_progress.** Decks and
  lessons can be archived (taken offline without losing history);
  quiz_items get a stronger "retired" semantic (with `superseded_by_id`
  forward-link) because FSRS state on the old row needs to remain
  queryable for analytics. `quiz_item_progress` has no soft-delete
  because FSRS history is never archived — when a user is deleted,
  CASCADE removes their rows; otherwise rows are immortal.

## 12. Out of scope (deferred to other Phase-6 slices)

- `card_metadata` table shape (tech_tags, scenario_type, seniority,
  prerequisites, difficulty refinement) — **slice 6.2**.
- `card_quality_signals` table per Decision J2 — **slice 6.13.5**.
- `source_content` table (admin uploads, ingestion provenance) —
  **slice 6.9** / **6.10**.
- Events table column shape (`quiz_review_events`,
  `lesson_view_events`) — **slice 6.0**.
- Seed data loading mechanism for the 12 locked decks — **slice
  6.4.5** (audit Q8; chat-Claude recommends
  `scripts/seed_phase6_decks.py`).
- Edit-classification rule (`>15 %` char-delta on
  concept_md/production_md/examples_md OR any quiz_item question/answer
  change = substantive) — **slice 6.9**.
- Cold-start behavior for IP no-Lens-scan users — **slice 6.7** (audit Q7).
- Background-job system selection (RQ vs APScheduler vs in-process)
  — **locked at G2**, slice 6.10 / 6.14 wire.
- Object-storage selection (R2 vs S3 vs `app/data/`) — **locked at H1**,
  slice 6.4.5 / 6.10 wire.
- Lens → recent-skill-gaps service helper — **slice 6.6** (audit R-2).
- Multi-route admin shell refactor of `AdminPanel.tsx` — **slice 6.4**
  (audit R-4).
- Dropping legacy tables (`cards`, `categories`, `card_progress`,
  `card_feedback`) — **slice 6.15** cleanup.
- Per-deck pricing tiers — **out of Phase 6 scope** entirely.

## 13. Open questions for chat-Claude / Dhamo

> Questions that the schema design surfaced but does NOT block this
> spec. Resolve in the implementation slice's pre-flight or in a
> follow-up.

- **OQ-1.** `quiz_items.distractors` is `JSONB NULLABLE` — should we
  add a CHECK constraint that `(question_type = 'mcq') ↔ (distractors IS NOT NULL)`?
  Engineering judgment: defer. The check is enforceable at the
  service layer where the error message can be informative;
  Postgres CHECK violations surface as opaque 23514 SQLSTATE codes.
- **OQ-2.** `lessons.version_type` enum has three values; slice 6.9
  may need a fourth (e.g., `'minor_quiz_change'` for "lesson body
  unchanged but a quiz_item was retired"). Adding values is
  trivial (it's a String, not a Postgres ENUM — see D-3) — defer
  to 6.9.
- **OQ-3.** Should `decks.tier` allow values beyond `'foundation'` /
  `'premium'` (e.g., `'beta'` for unfinished-but-released content)?
  Locked decision and free-tier semantics only require the two
  values today. Defer to a future per-deck pricing slice if needed.
- **OQ-4.** Implementation slice baseline-test count is unknown —
  the spec just adds a new test file. Pre-flight will read live BE
  count and report delta.

---

*End of slice 6.1 spec. Authored 2026-04-26 at HEAD `5b0aa23`. Audit
basis: `docs/audits/phase-6-scout.md` (commit `5b0aa23`). Next step:
Mode 1 implementation slice executes against this spec.*
