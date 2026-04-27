# Phase 6 — Slice 6.4: Admin Authoring (multi-route admin shell + deck/lesson/quiz_item CRUD + lesson_service DB swap + fixture retirement)

## Status: Partially shipped — slice 6.4a shipped (closes B-064 by `b0806d0`); slice 6.4b pending B-065

| Field | Value |
|-------|-------|
| Phase | 6 (Curriculum Platform) |
| Slice | 6.4 — admin authoring (heaviest Phase 6 slice) |
| Mode | 4 (spec-author) |
| Author HEAD | `95bb3c5` (post-spec-status flip + post-CR §6+ regen) |
| Spec authored | 2026-04-27 |
| Implementation slices | TBD — split recommended per §12 D-1: **6.4a (shell, B-064)** + **6.4b (CRUD + lesson_service body swap + fixture retirement, B-065)**. Single-slice fallback covered in §12 D-1. |
| BACKLOG rows | filed at spec-commit time per R17 watermark check (highest in-use `B-063` per slice 6.3): **`B-064`** (slice 6.4a — admin shell refactor) + **`B-065`** (slice 6.4b — admin CRUD + lesson_service body swap + fixture retirement). If watermark drift surfaces at impl-prompt time, file the next free IDs and adjust references in this spec body. |
| Spec dependencies | `docs/specs/phase-6/01-foundation-schema.md` (slice 6.1, shipped at `a989539` / `f621248`) — `decks`, `lessons`, `quiz_items` tables exist on disk + Pydantic read schemas in `app/schemas/{deck,lesson,quiz_item}.py`; `lessons.version_type` ENUM-as-Literal with values `'initial'` / `'minor_edit'` / `'substantive_edit'` per slice 6.1 §4.2; `quiz_items.retired_at` + `quiz_items.superseded_by_id` per slice 6.1 §4.3 §AC-4. `docs/specs/phase-6/02-fsrs-quiz-item-binding.md` (slice 6.2, shipped at `7b654fb` / `a02639c`) — `GET /api/v1/quiz-items/daily` already filters retired quiz_items + archived lessons + archived decks per spec 6.2 §4.5; this slice's substantive-edit retirement cascade pre-existing-FSRS-row preservation invariant defined in spec 6.2 §4.6 D-4 history-preservation rule. `docs/specs/phase-6/03-lesson-ux.md` (slice 6.3, shipped at `ba00331` / `cacf238`) — `GET /api/v1/lessons/{id}`, `GET /api/v1/decks/{id}`, `GET /api/v1/decks/{id}/lessons` route surfaces + response shapes (`LessonWithQuizzesResponse`, `DeckResponse`, `DeckLessonsResponse`) are LOCKED unchanged in this slice (§4 D-2 below). |
| Audit dependencies | `docs/audits/phase-6-scout.md` (commit `5b0aa23`) — §1.6 admin role infrastructure (BE gate + audit chain), §6.4 existing dashboards, §7.1 admin UI today (AdminPanel.tsx is 868 lines as a single file → audit recommendation R-4: split into multi-route shell), §9.4 `react-hook-form` installed but unused (slice 6.4b is the natural first consumer). `.agent/skills/admin-panel.md` — `audit_admin_request → require_admin` chain documented for every `/api/v1/admin/*` route; PostHog `internal: true` flag on admin events. `docs/specs/phase-5/38-admin-analytics.md` — origin spec for `audit_admin_request` (E-018a) + the 403-not-404 admin-non-admin response convention. `CODE-REALITY.md` §3 (admin route block) + §6 (`lesson_service.py` four-function shape) + §11 drift item 18 (`## Status:` heading-2 form) — verified at spec-author time. |
| Slice dependencies | **Upstream:** slice 6.1 (foundation schema, shipped) + slice 6.2 (FSRS quiz-item binding, shipped) + slice 6.3 (lesson-card UX + lesson_service forward-compat affordance, shipped) — all required, all shipped. **Downstream:** unblocks slice 6.4.5 (seed lessons via `app/data/decks/seed_lessons/*.md` per H1 — fixture retirement here clears the path), slice 6.5 (lesson UX polish + three-layer quality — observes admin authoring outcomes), slice 6.6 (Lens-ranked deck/card ordering — needs DB-resident decks/lessons), 6.7 (persona Learn page — needs DB-resident deck list), 6.10 (RQ ingestion pipeline — feeds into the admin draft queue this slice sets up), 6.11 (Gemini-assisted lesson generation — uses the admin write paths shipped here), 6.12 (Claude critique — observes admin authoring quality signals), 6.13.5 (`card_quality_signals` user-thumbs dimension — bound to lesson/quiz_item rows admin authors here). |

### Phase 6 locked decisions referenced by this spec

> Recorded in front-matter so spec readers see the relevant locks
> without chasing SESSION-STATE. Rationale lives in §12 (Decisions) below.

| ID | Decision |
|----|----------|
| **G2** | Background jobs: RQ on Redis for ingestion (slice 6.10); Railway cron for daily Pro digest (slice 6.14). **Not consumed by this slice** — admin write paths are request-time synchronous; substantive-edit retirement cascade runs in the same DB transaction as the lesson PATCH. No RQ enqueue, no async fan-out. (See §12 D-3.) |
| **H1** | Object storage: Cloudflare R2 for ingestion artifacts (slice 6.10); `hirelens-backend/app/data/decks/seed_lessons/*.md` for the 12 locked-deck seeds (slice 6.4.5). **Not consumed by this slice** — admin authors directly into Postgres `lessons.{concept,production,examples}_md` Text columns per slice 6.1 §4.2 schema. R2 binding stays out-of-tree; seed-content layout stays out-of-tree. (See §12 D-4.) |
| **I1** | Events: dual-write. PostHog for funnels/retention; Postgres `quiz_review_events` + `lesson_view_events` for content-quality / retention dashboards. **Slice 6.0 owns the events tables; this slice does NOT depend on them** — admin events ship to PostHog only + persist to `admin_audit_log` per the existing audit-log convention. The Phase-6 events tables are not yet on disk; spec 6.4's events declared in §9 below dual-write only when slice 6.0 ships, not at 6.4 impl time. (See §12 D-5.) |
| **J2** | Quality signals: `card_quality_signals` keyed on `(id, lesson_id, quiz_item_id NULLABLE, signal_source, dimension)`; built in slice 6.13.5. **Not consumed by this slice** — admin-side quality assessment is out of scope; `quality_score` on `lessons` (slice 6.1 §4.2) is read-only in this slice (NULL on create; populated by future critique slices). (See §12 D-6.) |

---

## 1. Problem

Slices 6.1 + 6.2 + 6.3 shipped the foundation schema, FSRS quiz-item
service + routes, and the FE lesson-card UX backed by **fixture data**
served from `app/data/lesson_fixtures.py`. The fixture file is a
deliberate bridge — it lets the lesson page ship and verify the four-
section render contract before DB persistence of authored content
exists. Phase 6's locked decision is greenfield content authoring at
admin time: the 12 locked decks + their lessons + their atomic
quiz_items are typed into Postgres via an admin authoring surface, NOT
seed-loaded from JSON, NOT scraped from a CMS.

Slice 6.4 ships that authoring surface. After this slice ships:

- Admins can create / update / publish / archive **decks** at
  `/admin/decks` + `/admin/decks/:id`.
- Admins can create / update / publish / archive **lessons** at
  `/admin/lessons/:id` (per-deck list lives at `/admin/decks/:id`).
- Admins can create / update / retire **quiz_items** at
  `/admin/quiz-items/:lesson_id` (per-lesson sub-resource — quiz_items
  do NOT have their own top-level admin surface).
- A **substantive lesson edit** retires the lesson's existing
  quiz_items in the same DB transaction (per §7 below) — preserves
  FSRS history per slice 6.1 §4.3 retirement semantic.
- The fixture file `app/data/lesson_fixtures.py` is **deleted** in the
  same impl commit that swaps `lesson_service.py`'s four function
  bodies from `lesson_fixtures` calls to DB queries (per §4.2 below) —
  one atomic file-deletion + body-swap commit per slice 6.4b.
- The `AdminPanel.tsx` 868-line monolith is split into a multi-route
  admin shell at `/admin/*` per audit R-4. Existing `/admin` (cards
  CRUD) is preserved at `/admin/cards`; new sub-routes mount at
  `/admin/decks/*` and `/admin/lessons/:id`.

Without slice 6.4, slices 6.4.5 (seed lessons) and 6.10 (RQ ingestion
pipeline) have no authoring surface to write into; slices 6.6 / 6.7 /
6.16 read against an empty DB; the fixture file lives forever and the
D-4 forward-compat affordance from slice 6.3 never cashes in.

## 2. Goals

1. Ship a multi-route admin shell at `/admin/*` (BE + FE) — split
   `AdminPanel.tsx` per audit R-4 into `AdminLayout.tsx` + per-section
   pages. Existing `/admin/cards` flow preserved unchanged. (Slice 6.4a
   B-064 — see §12 D-1.)
2. Ship admin write routes for decks, lessons, quiz_items at
   `/api/v1/admin/{decks,lessons,quiz-items}` — POST create, PATCH
   update, POST `:id/publish` (lessons only), POST `:id/archive` (decks
   + lessons; quiz_items use POST `:id/retire` per the
   retirement-not-archive semantic of slice 6.1 §4.3) + admin-LIST
   routes that include drafts (`published_at IS NULL`) the user-facing
   `GET /api/v1/lessons/{id}` excludes. (Slice 6.4b B-065.)
3. Swap `lesson_service.py`'s four function bodies from
   `lesson_fixtures` calls to DB queries (D-4 cash-in from slice 6.3) —
   **function signatures, route handlers, and response shapes stay
   byte-identical**. The 6.3 → 6.4 swap is invisible to FE consumers.
   (Slice 6.4b B-065.)
4. Delete `app/data/lesson_fixtures.py` + `app/data/__init__.py` in the
   same impl commit as the body swap. (Slice 6.4b B-065.)
5. Lock the substantive-vs-minor edit classification rule and the
   retirement cascade behavior on substantive lesson edits (§7 below),
   surfaced through a FE confirm modal before the PATCH fires (per OQ-4
   authored hint). (Slice 6.4b B-065.)
6. Ship admin authoring telemetry — every admin write route lands an
   `admin_audit_log` row via `audit_admin_request → require_admin`
   chain (per spec #38 E-018a + admin-panel skill §Audit Logging) AND
   fires a PostHog event with `internal: true` per the admin event
   convention. Postgres event-table dual-write deferred to slice 6.0
   per I1 — admin events PostHog-only at 6.4 impl time. (Slice 6.4b
   B-065.)
7. Lock per-OQ resolutions or surface them as authored hints (not
   locked decisions; impl prompt may lift to LDs) — see §14 OQ-1..OQ-6.

## 3. Non-goals

- **Card quality signals dual-write.** Slice 6.13.5 introduces the
  `card_quality_signals` table; slice 6.4 admin authoring does NOT
  write quality signals. `lessons.quality_score` stays NULL on
  admin-authored content (populated by future critique slices). (J2.)
- **Gemini-assisted lesson generation** — slice 6.11. The admin
  authoring surface in this slice is pure CRUD; the "generate via LLM"
  button comes later. AdminPanel.tsx's existing card-draft AI surface
  (`POST /api/v1/admin/cards/generate`) stays unchanged.
- **Cross-model critique on save** — slice 6.12. No
  `generate_for_task(task='admin_lesson_critique')` call in this slice.
  The admin-side LLM contract is ZERO LLM calls in slice 6.4 impl.
- **Golden-set evaluation** — slice 6.13.
- **AI-anything else.** This is hand-authored CRUD only.
- **Seed content for the 12 locked decks** — slice 6.4.5 owns the
  one-time seed (per H1 via `app/data/decks/seed_lessons/*.md`). Slice
  6.4 ships the WRITE PATHS the seed slice will consume; slice 6.4 does
  NOT ship the 12-deck seed content itself.
- **Background-job RQ enqueue on save** — slice 6.10. Substantive-edit
  cascade runs synchronously in the same DB transaction as the lesson
  PATCH (G2 — no RQ in 6.4). (See §12 D-3.)
- **R2 / object-storage binding** — slice 6.10. Admin authors directly
  into Postgres Text columns; no PDF / image / Markdown-file upload
  surface in 6.4. (H1.)
- **Postgres event-table writes** for admin events
  (`lesson_published`, `lesson_archived`, etc.) — slice 6.0 builds the
  events table; slice 6.4 admin events PostHog-only + audit-log
  persistence per the existing E-018a convention. (I1.)
- **Postgres `quiz_review_events` table FK pointing at quiz_items** —
  slice 6.0 / 6.13.5. Slice 6.4's quiz_item retire path mutates
  `retired_at` + `superseded_by_id` only; no event-table mutation.
- **Promotion UI for admins** — out of phase 6. Admin promotion stays
  Direct DB UPDATE per `.agent/skills/admin-panel.md` §Admin Promotion.
- **/admin/critique-runs surface** — audit R-4 names this as a future
  admin route; ship NOTHING at that path in 6.4 (slice 6.12 owns).
- **Free-tier wall on admin write routes** — admin role bypasses all
  free-tier walls per existing convention (`require_admin` + plan-gate
  early returns in `usage_service`); no new wall logic in this slice.
- **`react-hook-form` adoption beyond this slice's editor pages** —
  audit §9.4 flagged the dep as installed-but-unused; slice 6.4b is
  the natural first consumer. Adopt it for editor pages; do NOT
  retrofit existing forms (PersonaPicker, EmailPreferences, etc.) —
  out of scope.
- **DB schema changes** — slice 6.1 already shipped all four foundation
  tables. No Alembic migration in slice 6.4 (a or b). N7 STOP if a gap
  surfaces.
- **Mutating user-facing read shapes** — `LessonWithQuizzesResponse`,
  `DeckResponse`, `DeckLessonsResponse` from spec #03 §6 are byte-
  identical post-slice-6.4. Admin write schemas extend ADDITIVELY in
  the same files (§4.4 + §6).
- **Touching `app/api/v1/routes/quiz_items.py` (slice 6.2)** —
  user-facing FSRS routes stay unmodified. Slice 6.4 admin quiz_item
  routes mount at `/api/v1/admin/quiz-items` (NOT `/api/v1/quiz-items`).
- **Touching `app/api/v1/routes/{lessons,decks}.py` (slice 6.3)** —
  user-facing read routes stay unmodified. Slice 6.4 admin routes
  mount at `/api/v1/admin/{decks,lessons}` (NOT `/api/v1/{decks,lessons}`).

## 4. Service surface — admin services + lesson_service DB swap

> **D-2 (locked).** Slice #03 (slice 6.3) §5 route surfaces +
> `LessonWithQuizzesResponse` / `DeckResponse` / `DeckLessonsResponse`
> response shapes are **LOCKED UNCHANGED** by slice 6.4. The 6.3 → 6.4
> swap is internal to `lesson_service.py` function bodies; route
> handlers, response models, status codes, and 404/401 semantics stay
> byte-identical. AC-6 + AC-7 verify (§11).

### 4.1 New BE files (slice 6.4b — B-065)

#### 4.1.1 `app/services/deck_admin_service.py` (new)

```python
async def create_deck(payload: DeckCreateRequest, db: AsyncSession, admin_id: str) -> DeckResponse: ...
async def update_deck(deck_id: str, payload: DeckUpdateRequest, db: AsyncSession, admin_id: str) -> DeckResponse: ...
async def archive_deck(deck_id: str, db: AsyncSession, admin_id: str) -> DeckResponse: ...
async def list_admin_decks(db: AsyncSession, status: AdminDeckStatusFilter = "active") -> list[DeckResponse]: ...
```

Behavioral notes:
- `create_deck` asserts unique `slug` (DB UNIQUE handles enforcement;
  service catches IntegrityError → raises `DeckSlugConflictError` → 409
  at route layer).
- `update_deck` allows mutating any column the schema admits; explicit
  `archived_at` mutation routes through `archive_deck` instead.
- `archive_deck` sets `archived_at = func.now()`; idempotent (re-
  archiving a soft-deleted deck returns the same row, no error).
- `list_admin_decks` honors a status filter (`'active'` excludes
  `archived_at IS NOT NULL`; `'archived'` returns only archived;
  `'all'` returns the full table). Default `'active'` matches user-
  facing semantics.
- Persona-visibility narrowing edits surface a warning at the FE layer
  (per OQ-6 authored hint) — service layer simply persists; no
  warning logic in the BE service.

#### 4.1.2 `app/services/lesson_admin_service.py` (new)

```python
async def create_lesson(payload: LessonCreateRequest, db: AsyncSession, admin_id: str) -> LessonResponse: ...
async def update_lesson(lesson_id: str, payload: LessonUpdateRequest, db: AsyncSession, admin_id: str) -> LessonUpdateResponse: ...
async def publish_lesson(lesson_id: str, db: AsyncSession, admin_id: str) -> LessonResponse: ...
async def archive_lesson(lesson_id: str, db: AsyncSession, admin_id: str) -> LessonResponse: ...
async def list_admin_lessons(deck_id: str, db: AsyncSession, status: AdminLessonStatusFilter = "active") -> list[LessonResponse]: ...
```

Behavioral notes:
- `create_lesson`: composite UNIQUE `(deck_id, slug)` enforced at DB
  layer; `LessonSlugConflictError` → 409 at route. `version=1`,
  `version_type='initial'`, `published_at=NULL`, `quality_score=NULL`,
  `source_content_id=NULL`, `generated_by_model=NULL` per slice 6.1
  §4.2 defaults.
- `update_lesson` is the substantive-vs-minor classification entry
  point — see §7 for the full algorithm. Returns
  `LessonUpdateResponse` (extends `LessonResponse` with
  `version_type`, `quiz_items_retired_count`, `quiz_items_retired_ids`
  — additive top-level fields letting FE confirm-modal copy reflect
  cascade outcome). Per OQ-4 authored hint, admin's intent (`MINOR` vs
  `SUBSTANTIVE`) is passed via the request payload as
  `edit_classification` enum + the BE re-validates against the §7
  rule. If admin claims MINOR but the rule says SUBSTANTIVE the route
  returns 409 `EditClassificationConflictError` so FE can re-prompt.
- `publish_lesson` flips `published_at` from NULL → `func.now()`;
  idempotent (re-publishing emits no PostHog event the second time per
  slice 6.1 §6 idempotency rule).
- `archive_lesson` sets `archived_at = func.now()`; idempotent. Does
  NOT cascade to quiz_items (their retirement is bound to substantive-
  edit not archive — confirmed at slice 6.1 §4.2 + §4.3).
- `list_admin_lessons` honors status filter
  (`'active'` excludes `archived_at IS NOT NULL`; `'drafts'` is
  `archived_at IS NULL AND published_at IS NULL`; `'published'` is
  `archived_at IS NULL AND published_at IS NOT NULL`; `'archived'`
  returns only archived; `'all'` returns the full table per `deck_id`).
  Default `'active'` matches user-facing semantics. Index
  `ix_lessons_review_queue` shipped in slice 6.1 §4.2 supports the
  `'drafts'` filter.

#### 4.1.3 `app/services/quiz_item_admin_service.py` (new)

```python
async def create_quiz_item(payload: QuizItemCreateRequest, db: AsyncSession, admin_id: str) -> QuizItemResponse: ...
async def update_quiz_item(quiz_item_id: str, payload: QuizItemUpdateRequest, db: AsyncSession, admin_id: str) -> QuizItemResponse: ...
async def retire_quiz_item(quiz_item_id: str, db: AsyncSession, admin_id: str, superseded_by_id: Optional[str] = None) -> QuizItemResponse: ...
async def list_admin_quiz_items(lesson_id: str, db: AsyncSession, status: AdminQuizItemStatusFilter = "active") -> list[QuizItemResponse]: ...
```

Behavioral notes:
- `create_quiz_item`: parent lesson must exist + not be archived
  (raises `LessonNotFoundError` 404 / `LessonArchivedError` 409
  respectively). `version=1`, `retired_at=NULL`,
  `superseded_by_id=NULL`.
- `update_quiz_item`: a substantive change to question/answer/
  question_type/distractors flips through `retire_quiz_item` per
  slice 6.1 §4.3 invariant — caller specifies via
  `edit_classification` enum on the request payload (mirrors
  `update_lesson`). Same 409 conflict if the admin claim and the §7
  rule disagree.
- `retire_quiz_item` sets `retired_at = func.now()`; if
  `superseded_by_id` is provided, links forward (per slice 6.1 §4.3
  retirement semantic). Idempotent: re-retiring already-retired returns
  the same row, no error. The retire path does NOT delete
  `quiz_item_progress` rows pointing at this item — FSRS history
  preservation per slice 6.2 §4.6 D-4 invariant + spec 6.1 §4.3.
- `list_admin_quiz_items`: status filter (`'active'`,
  `'retired'`, `'all'`) keyed off `retired_at`; partial index from
  slice 6.1 §4.3 already supports the `'active'` path.

#### 4.1.4 Service-layer error classes (new)

Mirror slice 6.2 §4.8 service-error pattern. Errors live in
`app/services/admin_errors.py` (new file) so the three admin services
share the import.

```python
class DeckSlugConflictError(Exception): ...        # 409
class DeckNotFoundError(Exception): ...            # 404
class LessonSlugConflictError(Exception): ...      # 409
class LessonNotFoundError(Exception): ...          # 404
class LessonArchivedError(Exception): ...          # 409 (operating on archived lesson)
class QuizItemNotFoundError(Exception): ...        # 404
class EditClassificationConflictError(Exception): ...  # 409 (admin claim vs §7 rule)
```

`QuizItemNotFoundError` is a NEW class in `admin_errors.py`; the
slice-6.2 class of the same name in
`app/services/quiz_item_study_service.py` stays where it is — they
serve different code paths and the duplicate is locked-in by slice 6.2
D-1 (no shared FSRS-helper module). Slice 6.15 cleanup folds them.

### 4.2 `app/services/lesson_service.py` body swap (slice 6.4b — B-065)

Slice 6.3 D-4 cash-in. The four function signatures stay byte-
identical (per §4 D-2). Bodies become DB queries:

#### 4.2.1 `get_lesson_with_quizzes(lesson_id, db)`

Replaces the current `lesson_fixtures.get_lesson(lesson_id)` call with
a DB query loading the lesson + active quiz_items + parent deck:

```python
stmt = (
    select(Lesson)
    .options(
        selectinload(Lesson.quiz_items.and_(QuizItem.retired_at.is_(None))),
        selectinload(Lesson.deck),
    )
    .where(Lesson.id == lesson_id)
    .where(Lesson.archived_at.is_(None))
    .where(Lesson.published_at.is_not(None))   # only published lessons visible to user-facing route
)
```

`selectinload` strategy is the OQ-2 authored hint — eager-loads
quiz_items and deck in two extra queries (one per relationship), avoids
the N+1 over `quiz_items` that lazy-load would force, and bounds the
query plan. Authored hint not locked — impl prompt may lift to LD if
production traffic warrants. Returns `None` (route maps to 404) when:

- `lesson_id` does not match any row;
- the matching row has `archived_at IS NOT NULL`;
- the matching row has `published_at IS NULL` (admin draft, not yet
  visible to users);
- the parent deck is archived (`Deck.archived_at IS NOT NULL`).

Active quiz_items only (`retired_at IS NULL`) per the slice-6.3 §4.3
contract preserved.

#### 4.2.2 `get_deck_with_meta(deck_id, db)`

Replaces `lesson_fixtures.get_deck(deck_id)`:

```python
stmt = (
    select(Deck)
    .where(Deck.id == deck_id)
    .where(Deck.archived_at.is_(None))
)
```

Returns `None` for unknown / archived deck.

#### 4.2.3 `list_lessons_in_deck(deck_id, db)`

Replaces `lesson_fixtures.list_lessons(deck_id)`:

```python
stmt = (
    select(Lesson)
    .where(Lesson.deck_id == deck_id)
    .where(Lesson.archived_at.is_(None))
    .where(Lesson.published_at.is_not(None))
    .order_by(Lesson.display_order.asc(), Lesson.created_at.asc())
)
```

User-facing: only published lessons. Unknown deck returns empty list
(route maps to 404 only if the deck itself is missing — handled in
`get_deck_lessons_bundle`).

#### 4.2.4 `get_deck_lessons_bundle(deck_id, db)`

Composes `get_deck_with_meta` + `list_lessons_in_deck` into the
existing `DeckLessonsResponse` shape (slice 6.3 §6.3). Two-query
strategy avoids loading lessons when the deck itself is missing /
archived:

```python
deck = await get_deck_with_meta(deck_id, db)
if deck is None:
    return None
lessons = await list_lessons_in_deck(deck_id, db)
return DeckLessonsResponse(deck=deck, lessons=lessons)
```

Empty `lessons` list when the deck exists but has no published
lessons (200, not 404 — preserves slice 6.3 §5.3 contract).

### 4.3 Fixture-file retirement (slice 6.4b — B-065)

The same impl commit that swaps the four `lesson_service.py` bodies
**deletes**:

- `hirelens-backend/app/data/lesson_fixtures.py` (185 lines per slice
  6.3 impl — verified at spec-author time as on-disk).
- `hirelens-backend/app/data/__init__.py` (empty marker — verified at
  spec-author time as 0 bytes).
- `hirelens-backend/app/data/__pycache__/` (auto-clean on the next
  pytest run; no commit action needed).

The directory `hirelens-backend/app/data/` is NOT removed — slice
6.4.5 will reintroduce it as `app/data/decks/seed_lessons/*.md` per H1.
Leaving the directory in place avoids a churn (`mkdir` in 6.4.5) and
matches the H1 lock (the directory is not a 6.4 retirement target;
only the two Python files are). If the impl prompt for 6.4b finds
`app/data/` empty after deletions, it MAY remove the directory (low-
churn cleanup) but is NOT required to.

### 4.4 Pydantic write schemas (slice 6.4b — B-065)

Extend `app/schemas/{deck,lesson,quiz_item}.py` additively (per slice
6.1 §5.3 #4 + slice 6.3 §6 precedent). No new schema files. No mutation
of existing read shapes.

Full field tables in §6 below. Summary:

- `app/schemas/deck.py` gains `DeckCreateRequest`,
  `DeckUpdateRequest`. Existing `DeckResponse` (slice 6.1) +
  `DeckLessonsResponse` (slice 6.3) unchanged.
- `app/schemas/lesson.py` gains `LessonCreateRequest`,
  `LessonUpdateRequest`, `LessonUpdateResponse` (extends
  `LessonResponse` additively for the substantive-edit cascade
  surface), `EditClassification` `Literal` alias. Existing
  `LessonResponse` (slice 6.1) + `LessonWithQuizzesResponse` (slice
  6.3) unchanged.
- `app/schemas/quiz_item.py` gains `QuizItemCreateRequest`,
  `QuizItemUpdateRequest`. Existing `QuizItemResponse` (slice 6.1) +
  the slice-6.2 daily-queue / review schemas unchanged.

### 4.5 Service-layer admin attribution

Every admin service function takes `admin_id: str` as a required
parameter. The route layer reads admin_id from the
`get_current_user` chain (via `require_admin`) and passes it through.
Service uses `admin_id` for:

- PostHog event attribution (`{admin_id, ...}` first per `.agent/skills/analytics.md` convention).
- Audit-log row attribution — the existing `audit_admin_request`
  background task already writes `admin_id` per spec #38; service
  layer does NOT redundantly write a second audit row.

`admin_id` is NOT written to the entity row (no
`decks.created_by_admin_id` or similar — rejected; admin authorship is
captured in `admin_audit_log` per spec #38, sufficient for forensic
queries without entity-table denormalization).

## 5. Route surface — admin write routes

> **D-7 (locked).** Every new admin route declares the canonical
> `Depends(audit_admin_request)` chain (which itself chains
> `Depends(require_admin)` per the existing `app/core/deps.py:104-143`
> shape). This is the SAME chain used by `/admin/audit`,
> `/admin/analytics/metrics`, `/admin/analytics/performance` per CR §3
> + spec #38 E-018a + `.agent/skills/admin-panel.md` §Audit Logging.
> AC-3 verifies (§11).

> **Route-file naming.** Slice 6.4b adds three new files:
> `app/api/v1/routes/admin_decks.py`, `app/api/v1/routes/admin_lessons.py`,
> `app/api/v1/routes/admin_quiz_items.py`. **Do NOT extend** the
> existing `app/api/v1/routes/admin.py` (cards CRUD) — it is already
> co-located with `card_admin_service`, and bundling deck/lesson/
> quiz_item routes there would push the file past 1500 lines (per audit
> §7.1 finding on AdminPanel.tsx already-868-lines). The four files
> share the `audit_admin_request` chain via per-file `router =
> APIRouter(prefix="/api/v1/admin", dependencies=[Depends(audit_admin_request)])`
> declarations (matches existing `admin_analytics.py` pattern).

### 5.1 `POST /api/v1/admin/decks`

| Field | Value |
|-------|-------|
| Method | POST |
| Path | `/api/v1/admin/decks` |
| Auth | `Depends(audit_admin_request)` → chains `require_admin` |
| Request body | `DeckCreateRequest` (§6.1) |
| Response model | `DeckResponse` (slice 6.1 schema reused) |
| Status codes | 201 / 400 (validation) / 401 / 403 (non-admin) / 409 (slug conflict) |
| Rate limit | global default 100 req/min (no per-route override; admin role bypasses free-tier walls) |

### 5.2 `PATCH /api/v1/admin/decks/{deck_id}`

| Field | Value |
|-------|-------|
| Method | PATCH |
| Path | `/api/v1/admin/decks/{deck_id}` |
| Auth | `Depends(audit_admin_request)` → `require_admin` |
| Request body | `DeckUpdateRequest` (§6.2 — partial; only fields present in payload mutate) |
| Response model | `DeckResponse` |
| Status codes | 200 / 400 / 401 / 403 / 404 (unknown deck_id) / 409 (slug conflict on rename) |

### 5.3 `POST /api/v1/admin/decks/{deck_id}/archive`

| Field | Value |
|-------|-------|
| Method | POST |
| Path | `/api/v1/admin/decks/{deck_id}/archive` |
| Auth | `Depends(audit_admin_request)` → `require_admin` |
| Request body | none |
| Response model | `DeckResponse` (with `archived_at` populated) |
| Status codes | 200 / 401 / 403 / 404 |

Idempotent — re-archiving a soft-deleted deck returns the same row.

### 5.4 `GET /api/v1/admin/decks`

| Field | Value |
|-------|-------|
| Method | GET |
| Path | `/api/v1/admin/decks` |
| Auth | `Depends(audit_admin_request)` → `require_admin` |
| Query params | `status: 'active' \| 'archived' \| 'all' = 'active'` (per OQ-3) |
| Response model | `list[DeckResponse]` |
| Status codes | 200 / 401 / 403 |

OQ-3 authored hint: default `'active'`. Drafts are not a deck-level
concept (decks have no `published_at`); archived is the only
non-default status. The hint is unlikely to flip at impl.

### 5.5 `POST /api/v1/admin/decks/{deck_id}/lessons` + `GET /api/v1/admin/decks/{deck_id}/lessons`

POST creates a lesson within the deck (lesson list scoped to deck);
GET returns the admin-side lesson list (drafts + published + archived
per `?status=`):

| Method | Path | Body | Response | Status codes |
|--------|------|------|----------|--------------|
| POST | `/api/v1/admin/decks/{deck_id}/lessons` | `LessonCreateRequest` (§6.4) | `LessonResponse` | 201 / 400 / 401 / 403 / 404 (unknown deck_id) / 409 (slug conflict on `(deck_id, slug)`) |
| GET | `/api/v1/admin/decks/{deck_id}/lessons` | — | `list[LessonResponse]` | 200 / 401 / 403 / 404 |

Query param on GET: `status: 'active' \| 'drafts' \| 'published' \| 'archived' \| 'all' = 'active'` (per OQ-3 authored hint).

### 5.6 `PATCH /api/v1/admin/lessons/{lesson_id}`

| Field | Value |
|-------|-------|
| Method | PATCH |
| Path | `/api/v1/admin/lessons/{lesson_id}` |
| Auth | `Depends(audit_admin_request)` → `require_admin` |
| Request body | `LessonUpdateRequest` (§6.5 — partial; includes `edit_classification: 'minor' \| 'substantive'`) |
| Response model | `LessonUpdateResponse` (§6.6 — extends `LessonResponse` with cascade outcome fields) |
| Status codes | 200 / 400 (validation) / 401 / 403 / 404 / 409 (`edit_classification` admin-claim vs §7 rule disagreement) |

Behavior: substantive edits run the §7 retirement cascade in the same
DB transaction as the lesson PATCH (per OQ-4 authored hint). `version`
increments by 1, `version_type` flips to `'substantive_edit'`, all
existing active quiz_items on the lesson get
`retired_at = func.now()` set in the same transaction.
`LessonUpdateResponse.quiz_items_retired_count` reports the cascade
outcome so FE can render confirm-modal results copy.

### 5.7 `POST /api/v1/admin/lessons/{lesson_id}/publish`

| Field | Value |
|-------|-------|
| Method | POST |
| Path | `/api/v1/admin/lessons/{lesson_id}/publish` |
| Auth | `Depends(audit_admin_request)` → `require_admin` |
| Request body | none |
| Response model | `LessonResponse` (with `published_at` populated) |
| Status codes | 200 / 401 / 403 / 404 / 409 (lesson archived; can't publish an archived lesson — must un-archive first) |

Idempotent — re-publishing an already-published lesson returns the
same row, no PostHog event the second time.

### 5.8 `POST /api/v1/admin/lessons/{lesson_id}/archive`

| Field | Value |
|-------|-------|
| Method | POST |
| Path | `/api/v1/admin/lessons/{lesson_id}/archive` |
| Auth | `Depends(audit_admin_request)` → `require_admin` |
| Request body | none |
| Response model | `LessonResponse` |
| Status codes | 200 / 401 / 403 / 404 |

Idempotent. Does NOT cascade-retire quiz_items — quiz_item retirement
is bound to substantive-edit only per slice 6.1 §4.3 §AC-4. Existing
quiz_item_progress rows survive (slice 6.2 §4.6 history preservation).

### 5.9 `POST /api/v1/admin/lessons/{lesson_id}/quiz-items` + `GET /api/v1/admin/lessons/{lesson_id}/quiz-items`

| Method | Path | Body | Response | Status codes |
|--------|------|------|----------|--------------|
| POST | `/api/v1/admin/lessons/{lesson_id}/quiz-items` | `QuizItemCreateRequest` (§6.7) | `QuizItemResponse` | 201 / 400 / 401 / 403 / 404 (unknown lesson_id) / 409 (lesson archived) |
| GET | `/api/v1/admin/lessons/{lesson_id}/quiz-items` | — | `list[QuizItemResponse]` | 200 / 401 / 403 / 404 |

Query param on GET: `status: 'active' \| 'retired' \| 'all' = 'active'` (per OQ-3 authored hint).

### 5.10 `PATCH /api/v1/admin/quiz-items/{quiz_item_id}` + `POST /api/v1/admin/quiz-items/{quiz_item_id}/retire`

| Method | Path | Body | Response | Status codes |
|--------|------|------|----------|--------------|
| PATCH | `/api/v1/admin/quiz-items/{quiz_item_id}` | `QuizItemUpdateRequest` (§6.8 — partial; includes `edit_classification`) | `QuizItemResponse` | 200 / 400 / 401 / 403 / 404 / 409 |
| POST | `/api/v1/admin/quiz-items/{quiz_item_id}/retire` | `{superseded_by_id: str \| null}` | `QuizItemResponse` | 200 / 401 / 403 / 404 |

PATCH branches per `edit_classification`: minor edits mutate in place
(version unchanged); substantive edits route through `retire_quiz_item`
internally + create a new replacement quiz_item, returning the new
row's `QuizItemResponse` (the old row's `retired_at` + `superseded_by_id`
get set in the same transaction). The 409 conflict shape mirrors
`update_lesson` (admin claim vs §7 rule).

### 5.11 Wiring — `app/main.py` additive

```python
app.include_router(admin_decks.router,        tags=["v1 Admin Decks"])
app.include_router(admin_lessons.router,      tags=["v1 Admin Lessons"])
app.include_router(admin_quiz_items.router,   tags=["v1 Admin Quiz Items"])
```

Each router declares `prefix="/api/v1/admin"` + the
`audit_admin_request` dependency at file scope. Order inside the
`include_router` block: alphabetical by tag (matches existing repo
convention). The slice 6.3 `v1_lessons` + `v1_decks` routers are
**unchanged** — admin routes mount under a separate prefix.

## 6. Pydantic schemas — write-side additions

> All write schemas are NEW classes within existing slice-6.1 / 6.3
> files. No new schema files. No mutation of existing read shapes
> (per §4 D-2 + §3 non-goal).

### 6.1 `DeckCreateRequest` (extend `app/schemas/deck.py`)

| Field | Type | Validation | Notes |
|-------|------|------------|-------|
| `slug` | `str` | `Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")` | URL-safe per slice 6.1 §4.1 schema. |
| `title` | `str` | `Field(..., min_length=1, max_length=200)` | |
| `description` | `str` | `Field(..., min_length=1)` | Text column; no max in schema (DB Text is unbounded). |
| `display_order` | `int` | `Field(default=0, ge=0)` | |
| `icon` | `Optional[str]` | `Field(default=None, max_length=10)` | Emoji or short ID. |
| `persona_visibility` | `PersonaVisibility` (`Literal['climber', 'interview_prepper', 'both']`) | default `'both'` | Reuse the `Literal` alias from slice 6.1 schema. |
| `tier` | `DeckTier` (`Literal['foundation', 'premium']`) | default `'premium'` | Reuse alias. |

### 6.2 `DeckUpdateRequest` (extend `app/schemas/deck.py`)

All fields `Optional`. PATCH semantic: only fields present in the
payload mutate; `None` means "do not update". Field set + validation
mirrors `DeckCreateRequest` modulo Optional wrapping. `archived_at`
is NOT mutable through this route — uses `POST .../archive` instead
(per OQ-6 authored hint, persona_visibility narrowing edits surface
the warning at FE; service layer just persists).

### 6.3 Existing `DeckResponse` (slice 6.1) — unchanged

Reused as-is for create / update / archive / list response models.

### 6.4 `LessonCreateRequest` (extend `app/schemas/lesson.py`)

| Field | Type | Validation | Notes |
|-------|------|------------|-------|
| `slug` | `str` | `Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")` | |
| `title` | `str` | `Field(..., min_length=1, max_length=200)` | |
| `concept_md` | `str` | `Field(..., min_length=1)` | Required per slice 6.1 §4.2. |
| `production_md` | `str` | `Field(..., min_length=1)` | Required. |
| `examples_md` | `str` | `Field(..., min_length=1)` | Required. |
| `display_order` | `int` | `Field(default=0, ge=0)` | |

`deck_id` is NOT in the body — it comes from the URL path
(`POST /api/v1/admin/decks/{deck_id}/lessons` per §5.5).
`version=1`, `version_type='initial'`, `published_at=NULL`,
`quality_score=NULL`, `source_content_id=NULL`,
`generated_by_model=NULL` are all server-set defaults per slice 6.1
§4.2 — NOT admin-supplied.

### 6.5 `LessonUpdateRequest` (extend `app/schemas/lesson.py`)

All fields `Optional` except `edit_classification`:

| Field | Type | Validation | Notes |
|-------|------|------------|-------|
| `edit_classification` | `EditClassification` (`Literal['minor', 'substantive']`) | required | Admin's intent. BE re-validates against §7 rule; mismatch → 409. |
| `slug` | `Optional[str]` | as `LessonCreateRequest` | Renaming a lesson re-checks composite UNIQUE on `(deck_id, slug)`. |
| `title` | `Optional[str]` | as create | |
| `concept_md` | `Optional[str]` | non-empty if present | |
| `production_md` | `Optional[str]` | non-empty if present | |
| `examples_md` | `Optional[str]` | non-empty if present | |
| `display_order` | `Optional[int]` | as create | |

`published_at` and `archived_at` are NOT in the body — uses dedicated
routes (§5.7, §5.8). `version` and `version_type` are server-set per §7
+ §6.6 below; admin does NOT pass them.

### 6.6 `LessonUpdateResponse` (NEW; extend `app/schemas/lesson.py`)

Extends `LessonResponse` additively for substantive-edit cascade
surfacing:

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `lesson` | `LessonResponse` | slice 6.1 | Full updated lesson body. |
| `version_type_applied` | `EditClassification` | service | What §7 rule decided (matches request `edit_classification` when not 409'd). |
| `quiz_items_retired_count` | `int` | service | `0` for minor edits; `len(active_quiz_items_at_PATCH_time)` for substantive. |
| `quiz_items_retired_ids` | `list[str]` | service | UUIDs of newly-retired quiz_items (empty for minor; non-empty for substantive). FE confirm-modal results copy uses this. |

`model_config = ConfigDict(from_attributes=True)`.

### 6.7 `QuizItemCreateRequest` (extend `app/schemas/quiz_item.py`)

| Field | Type | Validation | Notes |
|-------|------|------------|-------|
| `question` | `str` | `Field(..., min_length=1)` | |
| `answer` | `str` | `Field(..., min_length=1)` | |
| `question_type` | `QuestionType` (`Literal['mcq', 'free_text', 'code_completion']`) | default `'free_text'` | Reuse slice 6.1 alias. |
| `distractors` | `Optional[list[str]]` | required when `question_type='mcq'` (validator); `None` otherwise | Pydantic `model_validator` enforces shape (§13 §OQ-1 of slice 6.1 deferred CHECK constraint to service-layer validation per spec 6.1 OQ-1). |
| `difficulty` | `QuizDifficulty` (`Literal['easy', 'medium', 'hard']`) | default `'medium'` | |
| `display_order` | `int` | `Field(default=0, ge=0)` | |

`lesson_id` from URL path (`POST /api/v1/admin/lessons/{lesson_id}/quiz-items`).
`version=1`, `retired_at=NULL`, `superseded_by_id=NULL`,
`generated_by_model=NULL` server-set per slice 6.1 §4.3.

### 6.8 `QuizItemUpdateRequest` (extend `app/schemas/quiz_item.py`)

All fields `Optional` except `edit_classification`. Same structure as
`LessonUpdateRequest`. `retired_at` + `superseded_by_id` are NOT in
the body — uses dedicated `POST .../retire` route. PATCH semantic
substantive branch: service internally creates a replacement quiz_item
(version+1) + retires the old one with `superseded_by_id` link, returns
the NEW row's `QuizItemResponse` (per §5.10 contract).

### 6.9 Schema audit — no conflict with prior slices

Slice 6.1 `DeckResponse` / `LessonResponse` / `QuizItemResponse` and
slice 6.3 `LessonWithQuizzesResponse` / `DeckLessonsResponse` are
**byte-identical** post-slice-6.4 — no fields renamed, no `Literal`
types modified. AC-9 of slice 6.1 + AC-9 of slice 6.3 remain green.

## 7. Substantive vs minor edit semantics + retirement cascade

> **D-8 (locked).** Substantive lesson edits retire the lesson's
> existing active quiz_items in the **same DB transaction** as the
> lesson PATCH. No async fan-out, no RQ enqueue (G2 — slice 6.4 is
> synchronous). FE surfaces a confirm modal BEFORE the PATCH fires per
> OQ-4 authored hint; user-facing FSRS daily queue already filters
> retired quiz_items per slice 6.2 §4.5 — no daily-queue dirty read.

### 7.1 Classification rule (BE-side)

Admin's intent comes in as `edit_classification: 'minor' | 'substantive'` on `LessonUpdateRequest`. BE re-validates by comparing the proposed update against the on-disk lesson row:

A lesson edit is **substantive** iff ANY of the following hold:

- `concept_md` differs by more than the §7.2 character-delta threshold
  from the on-disk row.
- `production_md` differs by more than the §7.2 threshold.
- `examples_md` differs by more than the §7.2 threshold.

Otherwise it is **minor**.

If the BE rule and admin's claim disagree, the route returns 409
`EditClassificationConflictError` with `detail` naming which field
exceeded the threshold; FE re-surfaces the confirm modal with the
corrected classification + cascade preview, admin re-submits.

> **Why server re-validates instead of trusting the client.** A
> substantive edit retires quiz_items + bumps version; a minor edit
> does not. Letting the client decide would let an admin "soft-edit" a
> question's answer without retiring the FSRS history pointing at the
> old answer — a correctness violation of slice 6.1 §4.3's retirement
> invariant. Server-side re-validation is the boundary.

### 7.2 Character-delta threshold

`>15%` character-delta on any of the three Markdown fields (per phase-6 audit cross-cutting #9 + spec 6.1 §3 non-goal — slice 6.9 owns the rule logic; slice 6.4 codifies the threshold for the cascade trigger):

```python
def _is_substantive_change(old: str, new: str, threshold: float = 0.15) -> bool:
    if old == new:
        return False
    delta = abs(len(new) - len(old)) + _levenshtein_or_similar(old, new)
    return delta / max(len(old), 1) > threshold
```

The exact distance metric (`Levenshtein` vs `difflib.SequenceMatcher.ratio()`
vs simple character-set diff) is impl-prompt judgment per OQ-4
authored hint (lean toward `difflib.SequenceMatcher` — stdlib, no new
dep). Slice 6.9's eventual classification spec may refine; this slice
locks the trigger surface (the function lives at
`app/services/lesson_admin_service.py::_is_substantive_change` — slice
6.9 may lift to a shared module).

### 7.3 Retirement cascade — same-transaction semantic

`update_lesson` opens a transaction (or uses the route's existing
session); inside the transaction, when the classification is
substantive:

```python
async def update_lesson(lesson_id, payload, db, admin_id):
    lesson = await _fetch_lesson_for_update(lesson_id, db)
    classification = _classify(lesson, payload)
    if classification != payload.edit_classification:
        raise EditClassificationConflictError(...)

    if classification == "substantive":
        retired_ids: list[str] = []
        for qi in await _fetch_active_quiz_items(lesson_id, db):
            qi.retired_at = func.now()
            retired_ids.append(qi.id)

        lesson.version += 1
        lesson.version_type = "substantive_edit"
    else:
        lesson.version_type = "minor_edit"
        retired_ids = []

    _apply_payload(lesson, payload)
    # session.flush() — caller responsible per repo pattern
    return LessonUpdateResponse(
        lesson=LessonResponse.model_validate(lesson),
        version_type_applied=lesson.version_type,
        quiz_items_retired_count=len(retired_ids),
        quiz_items_retired_ids=retired_ids,
    )
```

### 7.4 Quiz-item-level substantive edit

Per §5.10, substantive `quiz_item` edits route through
`retire_quiz_item` internally:

- Old row gets `retired_at = func.now()` + `superseded_by_id = <new_row.id>`.
- New row is inserted with `version = old.version + 1`, all other
  fields from the PATCH payload + parent `lesson_id` carried over.
- Existing `quiz_item_progress` rows pointing at the OLD row stay
  intact (slice 6.2 §4.6 D-4 history-preservation invariant).
- Daily-queue path filters retired quiz_items per slice 6.2 §4.5 — no
  user-facing dirty read.

### 7.5 Lesson archive does NOT cascade-retire quiz_items

Per slice 6.1 §4.2 §AC-4 + §4.3 retirement semantic: archiving a
lesson sets `lessons.archived_at` only. The lesson's quiz_items keep
`retired_at IS NULL`. Rationale: archive is reversible (un-archive by
clearing `archived_at`); quiz_item retirement is permanent (FSRS
history preserved, but no new progress rows ever again). Cascading
archive → retire would conflate the two semantics.

This rule is locked at slice 6.1 §AC-4; slice 6.4 codifies the
implementation: `archive_lesson` does NOT touch quiz_items.

## 8. FE component graph

> R16 component-graph audit applies. Per the audit (`docs/audits/phase-6-scout.md`
> §1.6 + §7.1) `pages/AdminPanel.tsx` is 868 lines as a single file
> with cards CRUD + bulk-import + AI draft. Audit R-4 recommends
> splitting into a multi-route admin shell BEFORE adding deck/lesson/
> quiz_item surfaces. Slice 6.4a (B-064) executes the split; slice
> 6.4b (B-065) fills the new shell with editor pages.

### 8.1 New FE files (slice 6.4a — B-064)

| File | Purpose |
|------|---------|
| `src/components/admin/AdminLayout.tsx` | New multi-route admin shell. Renders sidebar nav (Cards / Decks / Lessons / Audit / Analytics) + `<Outlet />` for nested routes. Wrapped in `<AdminGate>` (existing component, audit §1.6). |
| `src/pages/admin/AdminCards.tsx` | Extracted from `AdminPanel.tsx` (cards CRUD + AI draft + bulk-import). Behavior is byte-identical to today's `/admin` flow. Mounts at `/admin/cards`. |

### 8.2 New FE files (slice 6.4b — B-065)

| File | Purpose |
|------|---------|
| `src/pages/admin/AdminDecks.tsx` | Deck list page (`?status=active|archived|all` segmented control matching OQ-3). Create-Deck form (modal or drawer; impl-prompt picks). Mounts at `/admin/decks`. |
| `src/pages/admin/AdminDeckDetail.tsx` | Single deck editor + nested lesson list (`?status=` filter). Mounts at `/admin/decks/:deck_id`. |
| `src/pages/admin/AdminLessonEditor.tsx` | Single lesson editor — Markdown editor for concept_md / production_md / examples_md + slug/title/display_order + Publish/Archive buttons + nested quiz_items list. Mounts at `/admin/lessons/:lesson_id`. |
| `src/pages/admin/AdminQuizItems.tsx` | Per-lesson quiz_item editor. Mounts at `/admin/lessons/:lesson_id/quiz-items`. (Quiz items are sub-resources; no top-level `/admin/quiz-items` page.) |
| `src/components/admin/MarkdownEditor.tsx` | Reusable Markdown textarea with live preview (uses existing `react-markdown` + `remark-gfm` from slice 6.3). |
| `src/components/admin/ConfirmCascadeModal.tsx` | Confirm modal for substantive-edit retirement cascade. Surfaces `quiz_items_retired_count` post-PATCH from `LessonUpdateResponse` (§6.6). Per OQ-4 authored hint, modal fires BEFORE the PATCH so admin sees the cascade preview; cascade preview is computed FE-side from the same §7.2 rule (BE re-validates server-side per §7.1). |
| `src/hooks/useAdminDecks.ts` | List + create/update/archive admin decks. |
| `src/hooks/useAdminDeckDetail.ts` | Single deck + lessons within. |
| `src/hooks/useAdminLessonEditor.ts` | Single lesson + quiz_items + edit-classification compute. |
| `src/hooks/useAdminQuizItems.ts` | Per-lesson quiz_items list + create/update/retire. |
| `src/services/api.ts` (extension) | New helpers: `adminCreateDeck`, `adminUpdateDeck`, `adminArchiveDeck`, `adminListDecks`, `adminCreateLesson`, `adminUpdateLesson`, `adminPublishLesson`, `adminArchiveLesson`, `adminListLessons`, `adminCreateQuizItem`, `adminUpdateQuizItem`, `adminRetireQuizItem`, `adminListQuizItems`. 13 helpers total. |
| `src/types/index.ts` (extension) | New TS interfaces mirror BE write schemas: `DeckCreateRequest`, `DeckUpdateRequest`, `LessonCreateRequest`, `LessonUpdateRequest`, `LessonUpdateResponse`, `QuizItemCreateRequest`, `QuizItemUpdateRequest`, `EditClassification` (`'minor' \| 'substantive'`). Field-for-field mirror of BE Pydantic. |

### 8.3 Modified FE files (slice 6.4a — B-064)

| File | Change |
|------|--------|
| `src/App.tsx` | Replace single `<Route path="/admin" element={<AdminGate><AdminPanel /></AdminGate>} />` with nested routes under `<AdminLayout />`: `/admin` redirects to `/admin/cards`; `/admin/cards` mounts `AdminCards`; `/admin/decks` and `/admin/decks/:deck_id` mount placeholder pages in 6.4a + the real `AdminDecks` / `AdminDeckDetail` in 6.4b; `/admin/lessons/:lesson_id` mounts placeholder in 6.4a + real `AdminLessonEditor` in 6.4b; `/admin/lessons/:lesson_id/quiz-items` likewise. |
| `src/components/auth/AdminGate.tsx` | **No change** — existing wrapper continues to work (per audit §1.6 + spec #54 E-040). |
| `src/components/layout/TopNav.tsx` + `MobileNav.tsx` | If admin nav was a single `/admin` link, leave unchanged (the `AdminLayout` sidebar takes over once the user lands on `/admin/*`). If a sub-link was needed, add inside `AdminLayout` only — do NOT add admin sub-links to TopNav. |

### 8.4 Modified FE files (slice 6.4b — B-065)

Same `App.tsx` (placeholder → real components) + the new editor /
hook / api / types files from §8.2.

### 8.5 Existing components — no touch

- `src/pages/Lesson.tsx` (slice 6.3) — **untouched** (§3 non-goal). Its
  data source flips from fixture to DB transparently via the
  `lesson_service` body swap (§4.2); no FE-side change required.
- `src/components/lesson/{LessonRenderer,QuizItemPanel}.tsx` (slice
  6.3) — **untouched**.
- `src/components/study/QuizPanel.tsx` (legacy card flow) —
  **untouched**.
- `src/pages/AdminAnalytics.tsx` (Phase 5) — **untouched**. Keeps its
  existing `/admin/analytics` mount path inside the new `AdminLayout`'s
  `<Outlet />`. Slice 6.4a may move its route definition inside the
  `AdminLayout` `<Outlet />` block in `App.tsx`; the page component
  itself does not change.
- `src/pages/AdminPanel.tsx` — **gets renamed/repurposed** in slice
  6.4a per audit R-4: either deleted (logic extracted to
  `pages/admin/AdminCards.tsx`) or repurposed as an alias re-export.
  Impl prompt picks. Recommendation: delete + extract — minimizes drift
  surface.

> **AdminAudit FE consumer deferred per §12 D-14.**

### 8.6 Wire-shape contract — single source of truth

For each shared shape, BE Pydantic is the source of truth; FE TS
mirrors field-for-field per slice 6.3 §8.4 precedent. The impl slice
ships at least one FE shape-test per write schema (see §10).

## 9. Analytics events declared by this slice

Per slice 6.1 §6 + I1, every Phase 6 spec declares which events its
operations will emit. Slice 6.4 admin events fire to PostHog only
(slice 6.0 events table ships later); audit-log persistence is via the
existing `audit_admin_request` chain (per spec #38 E-018a). All admin
events set `internal: true` in properties per
`.agent/skills/admin-panel.md` §Admin-only PostHog Events.

| Event | Emit point | Properties | PostHog | Postgres (slice 6.0) |
|-------|------------|-----------|---------|----------------------|
| `admin_deck_created` | BE `deck_admin_service.create_deck` — fires at end of successful transaction. | `{admin_id, deck_id, slug, persona_visibility, tier, internal: true}` | ✓ | (slice 6.0; 6.4 PostHog-only) |
| `admin_deck_updated` | BE `deck_admin_service.update_deck` — fires at end of successful transaction. | `{admin_id, deck_id, fields_changed: list[str], persona_visibility_narrowed: bool, internal: true}` | ✓ | (6.0) |
| `admin_deck_archived` | BE `deck_admin_service.archive_deck` — fires only when the row transitions NULL → non-NULL (idempotent re-archive emits NO event). | `{admin_id, deck_id, slug, internal: true}` | ✓ | (6.0) |
| `admin_lesson_created` | BE `lesson_admin_service.create_lesson` — end of transaction. | `{admin_id, lesson_id, deck_id, slug, internal: true}` | ✓ | (6.0) |
| `admin_lesson_updated_minor` | BE `lesson_admin_service.update_lesson` — minor classification branch only. | `{admin_id, lesson_id, deck_id, version: int, fields_changed: list[str], internal: true}` | ✓ | (6.0) |
| `admin_lesson_substantively_edited` | BE `lesson_admin_service.update_lesson` — substantive branch only. Fires AFTER the cascade transaction commits. | `{admin_id, lesson_id, deck_id, version: int, prior_version: int, quiz_items_retired_count: int, quiz_items_retired_ids: list[str], internal: true}` | ✓ | (6.0) |
| `admin_lesson_published` | BE `lesson_admin_service.publish_lesson` — only on NULL → non-NULL transition. | `{admin_id, lesson_id, deck_id, version: int, version_type: str, generated_by_model: str \| null, internal: true}` | ✓ | (6.0) |
| `admin_lesson_archived` | BE `lesson_admin_service.archive_lesson` — only on NULL → non-NULL transition. | `{admin_id, lesson_id, deck_id, was_published: bool, internal: true}` | ✓ | (6.0) |
| `admin_quiz_item_created` | BE `quiz_item_admin_service.create_quiz_item` — end of transaction. | `{admin_id, quiz_item_id, lesson_id, question_type, difficulty, internal: true}` | ✓ | (6.0) |
| `admin_quiz_item_retired` | BE `quiz_item_admin_service.retire_quiz_item` (direct retire OR cascade from substantive lesson edit OR substantive quiz_item PATCH). Only on NULL → non-NULL transition. | `{admin_id, quiz_item_id, lesson_id, superseded_by_id: str \| null, prior_version: int, retire_reason: 'direct' \| 'lesson_substantive_cascade' \| 'quiz_item_substantive_replace', internal: true}` | ✓ | (6.0) |
| `admin_deck_persona_narrowed` | BE `deck_admin_service.update_deck` — fires only on the narrowing branch (one or more personas removed from `decks.persona_visibility`). Per D-19. | `{admin_id, deck_id, removed_personas: list[str], before_count: int, after_count: int, internal: true}` | ✓ | (6.0) |

> **Cascade-retire idempotency.** When a substantive lesson edit
> retires N quiz_items, the cascade fires N
> `admin_quiz_item_retired` events (one per row) PLUS the single
> `admin_lesson_substantively_edited` event. The two are correlated
> via `lesson_id` for funnel queries. Rationale: per-row event lets
> admin analytics surface "which quiz_item retirements were cascade
> vs direct" without a JOIN — `retire_reason='lesson_substantive_cascade'`
> is the discriminator.

> **Idempotency of publish/archive.** Per slice 6.1 §6 + slice 6.2 §8
> convention, all transition events fire only on the NULL → non-NULL
> flip. Re-publishing an already-published lesson MUTATES nothing and
> emits NO event. Same for archive.

> **Postgres dual-write deferral.** Slice 6.0 (events tables) is not
> yet on disk. Slice 6.4 admin events are PostHog-only at impl time +
> the existing `admin_audit_log` row from `audit_admin_request`. Once
> slice 6.0 ships, a follow-up may retroactively dual-write — out of
> 6.4 scope per I1.

> **Admin-LIST routes do NOT emit PostHog events.** Same convention as
> existing `/admin/cards` GET (no `admin_cards_listed` event). Audit-
> log row covers it.

Catalog update: `.agent/skills/analytics.md` gains 11 new admin event
rows in slice 6.4b (10 lifecycle events + `admin_deck_persona_narrowed`
per D-19). Slice 6.4a touches no analytics (shell refactor is no-op at
the catalog level — `/admin/cards` keeps emitting the same spec #17
events).

## 10. Test plan

Implementation slices add tests in flat layout per slice 6.1's D-024 /
D-025 + slice 6.3's repo-precedent.

### 10.1 Slice 6.4a (B-064) — admin shell refactor

#### BE tests
None new. The shell refactor is FE-only; existing `tests/test_admin_*.py`
suite (cards CRUD) continues to pass unchanged. AC-1 (slice 6.4a) is
verified by the existing suite staying green.

#### FE tests — `tests/admin/AdminLayout.test.tsx` (NEW)

- `test_admin_layout_redirects_root_to_cards` — visiting `/admin`
  with admin role → renders cards page (verifies `<Navigate replace
  to="/admin/cards" />` works).
- `test_admin_layout_renders_sidebar_with_4_links` — 4 nav links:
  Cards / Decks / Lessons / Analytics. (`/admin/audit` is intentionally
  omitted per §12 D-14.)
- `test_admin_layout_unauthenticated_redirects` — non-admin role →
  AdminGate redirect (existing behavior preserved).
- `test_admin_cards_byte_identical_behavior` — cards CRUD smoke
  through the new `/admin/cards` route. Re-uses existing
  `AdminPanel.test.tsx` cases retargeted to the new mount.

#### FE tests — `tests/admin/AdminCards.test.tsx` (NEW)

If `AdminPanel.test.tsx` exists and is non-trivial, slice 6.4a moves
those tests to `AdminCards.test.tsx` in lockstep with the page
extraction. If `AdminPanel.test.tsx` does not exist (per pre-flight
verification at impl time), this file becomes a thin smoke test.

**Target test count for 6.4a:** +5 to +8 FE tests (4 layout + 1-4
extracted card tests). BE unchanged.

### 10.2 Slice 6.4b (B-065) — admin CRUD + lesson_service body swap

#### BE tests — `tests/test_admin_decks_routes.py` (NEW)

- `test_create_deck_201_response_shape` — POST returns 201 +
  `DeckResponse`.
- `test_create_deck_409_slug_conflict` — duplicate slug → 409.
- `test_create_deck_403_non_admin` — non-admin → 403 (NOT 404 per spec
  #38 + admin-panel skill).
- `test_create_deck_401_unauthenticated` — no JWT → 401.
- `test_update_deck_200_partial_payload` — PATCH with one field
  mutates only that field; others unchanged.
- `test_update_deck_409_slug_conflict_on_rename` — renaming to an
  existing slug → 409.
- `test_archive_deck_idempotent` — re-archiving returns same row, no
  error.
- `test_list_decks_status_filter_active` / `archived` / `all` — query
  param honored.
- `test_admin_audit_log_row_per_request` — every successful admin
  call writes one `admin_audit_log` row (verifies
  `audit_admin_request` chain).

#### BE tests — `tests/test_admin_lessons_routes.py` (NEW)

- `test_create_lesson_201_within_deck` — POST nested at
  `/admin/decks/:id/lessons` returns 201.
- `test_create_lesson_404_unknown_deck` — POST to unknown deck → 404.
- `test_create_lesson_409_composite_slug_conflict` — `(deck_id, slug)`
  collision → 409.
- `test_update_lesson_minor_no_cascade` — minor classification leaves
  quiz_items active, version unchanged.
- `test_update_lesson_substantive_cascades_quiz_item_retirement` —
  substantive flips `version_type='substantive_edit'`, increments
  `version`, sets `retired_at` on all active quiz_items in same
  transaction. `LessonUpdateResponse.quiz_items_retired_count` matches.
- `test_update_lesson_409_classification_disagreement` — admin claims
  minor but §7 rule says substantive → 409.
- `test_publish_lesson_idempotent` — second publish emits no event.
- `test_publish_lesson_409_archived` — can't publish archived.
- `test_archive_lesson_does_not_cascade_retire` — quiz_items stay
  `retired_at IS NULL` after parent lesson archive.
- `test_list_admin_lessons_status_drafts_returns_unpublished` — uses
  ix_lessons_review_queue per slice 6.1.

#### BE tests — `tests/test_admin_quiz_items_routes.py` (NEW)

- `test_create_quiz_item_201` + `test_create_quiz_item_409_archived_lesson`.
- `test_update_quiz_item_minor_in_place` — version unchanged.
- `test_update_quiz_item_substantive_creates_replacement` — old row
  retired with `superseded_by_id` link to new; new row is `version+1`.
- `test_retire_quiz_item_idempotent`.
- `test_retire_quiz_item_preserves_progress_rows` — existing
  `quiz_item_progress` rows pointing at the retired quiz_item stay
  intact (slice 6.2 §4.6 invariant).
- `test_list_admin_quiz_items_retired_filter`.

#### BE tests — `tests/test_lesson_service_db_query.py` (NEW)

Validates the §4.2 body swap. The 6.3-era `tests/test_lesson_fixtures_routes.py`
is **renamed** to `tests/test_lesson_routes.py` (the routes are no
longer fixture-backed). Test cases preserved verbatim, modulo seeding:

- `test_get_lesson_returns_db_lesson_with_quizzes` — seeds DB with a
  published lesson + 3 active quiz_items, GET via the user-facing
  `/api/v1/lessons/{id}` returns `LessonWithQuizzesResponse` matching
  slice 6.3 §6.2.
- `test_get_lesson_excludes_unpublished` — seeds an unpublished lesson
  → user-facing GET returns 404.
- `test_get_lesson_excludes_archived` — seeds an archived lesson →
  404.
- `test_get_lesson_filters_retired_quiz_items` — seeds 2 active + 1
  retired quiz_item, response contains only the 2 active ones.
- `test_get_deck_excludes_archived`.
- `test_list_deck_lessons_orders_by_display_order_then_created_at`.
- `test_list_deck_lessons_filters_unpublished_for_user_facing_route`.
- `test_get_deck_lessons_bundle_404_unknown_deck` / `_empty_lessons`.
- `test_lesson_fixtures_module_deleted` — verifies
  `app/data/lesson_fixtures.py` no longer exists on disk + no remaining
  imports anywhere in `app/`.

#### FE tests — `tests/admin/AdminDecks.test.tsx`, `AdminDeckDetail.test.tsx`, `AdminLessonEditor.test.tsx`, `AdminQuizItems.test.tsx`, `ConfirmCascadeModal.test.tsx` (NEW × 5)

Each editor page gets:
- Render-without-crash + 401/403 redirect.
- Happy-path create / update / publish / archive / retire flow with
  mocked api helpers.
- Confirm-cascade modal preview computation matches BE `LessonUpdateResponse`.
- Substantive-edit flow: modal fires before PATCH, surfaces cascade
  preview, admin confirms, PATCH fires, results modal renders
  `quiz_items_retired_count`.
- 409 `EditClassificationConflictError` UX: re-prompts with corrected
  classification.

#### FE tests — `tests/types/AdminWriteShapes.shape.test.ts` (NEW)

Mirror slice 6.3 §8.4 — at least one fixture-shaped object per write
schema satisfies the TS type. Catches optionalization / field deletion
during refactors.

**Target test count for 6.4b:** +25 to +30 BE (10 + 10 + 6 + 9 across
4 files) + +20 to +25 FE (5+5+5+5+3+5 across 6 files). Total slice
6.4b: ~+50 across BE + FE.

**Combined slice 6.4 (a + b) target:** ~+55 to +65 tests. Significant
delta — heaviest Phase 6 slice as flagged in the prompt.

### 10.3 Test fixture seeding

The `lesson_service.py` body-swap tests need DB seeding (no fixture
file post-retirement). Two clean options the impl prompt picks
between:

- (A) **pytest fixtures** — module-level pytest fixtures in
  `tests/conftest.py` build a small deck + lesson + quiz_item set per
  test session (or per test, if isolation needed).
- (B) **Direct SQL inserts in setUp** — each test inserts what it
  needs.

Authored hint: (A) — matches existing `tests/conftest.py` pattern for
auth-fixtures + DB session fixtures (verified at spec-author time as
the canonical pattern). Defer to impl judgment if (B) cleaner per
specific test.

## 11. Acceptance criteria

The implementation slices (6.4a + 6.4b) must pass:

### Slice 6.4a (B-064)

- **AC-1** — `pages/AdminPanel.tsx` is removed (or repurposed as
  an alias re-export — impl picks; recommendation: delete). New
  `AdminLayout.tsx` mounts at `/admin` and renders the multi-route
  shell. Existing `/admin` URL deep-links redirect to `/admin/cards`.
- **AC-2** — `/admin/cards` renders the existing card CRUD + AI
  draft + bulk-import surface byte-identically. Existing
  `tests/AdminPanel.test.tsx` (or its successor) stays green at
  `/admin/cards`.
- **AC-3** — `AdminLayout` sidebar renders 4 nav links
  (Cards / Decks / Lessons / Analytics) wrapped in `<AdminGate>`,
  navigating to `/admin/cards`, `/admin/decks`, `/admin/lessons`,
  `/admin/analytics`. Admin sub-route `/admin/lessons` mounts a
  placeholder ("Pick a deck to author lessons") in 6.4a. The
  `/admin/audit` link is intentionally omitted per §12 D-14 — the
  FE consumer was never built.
- **AC-4** — `<AdminGate>` continues to wrap all `/admin/*` routes;
  non-admin → AdminGate redirect (existing behavior).
- **AC-5** — `tsc --noEmit` clean. FE test suite green; +4 to +8
  tests.
- **AC-6** — `app/api/v1/routes/admin.py` (cards) is **unchanged**.
  No BE work in 6.4a.
- **AC-7** — No new BACKLOG row created beyond B-064.

### Slice 6.4b (B-065)

- **AC-1** — Three new BE route files
  (`admin_decks.py`, `admin_lessons.py`, `admin_quiz_items.py`)
  registered in `app/main.py` under `/api/v1/admin` prefix with
  `Depends(audit_admin_request)` chain.
- **AC-2** — `app/services/{deck,lesson,quiz_item}_admin_service.py`
  ship as new files. Service-error classes consolidated in
  `app/services/admin_errors.py`.
- **AC-3** — Every admin write route lands one `admin_audit_log` row
  per request (verified by `test_admin_audit_log_row_per_request`).
  Non-admin requests get 403 (NOT 404 per spec #38) BEFORE writing
  audit row.
- **AC-4** — Substantive lesson edits retire all active quiz_items
  in the same DB transaction. `LessonUpdateResponse.quiz_items_retired_count`
  matches the cascade actuals. Existing `quiz_item_progress` rows
  pointing at retired items survive (slice 6.2 §4.6).
- **AC-5** — `lesson_service.py`'s four function signatures stay
  byte-identical pre-/post-swap. Slice 6.3 user-facing routes
  (`/api/v1/lessons/{id}`, `/api/v1/decks/{id}`,
  `/api/v1/decks/{id}/lessons`) return the same response shapes; the
  swap is invisible to `pages/Lesson.tsx`.
- **AC-6** — `app/data/lesson_fixtures.py` and `app/data/__init__.py`
  removed from disk. `grep -rn "lesson_fixtures" hirelens-backend/app`
  returns zero hits. (`tests/test_lesson_service_db_query.py::test_lesson_fixtures_module_deleted`
  enforces.)
- **AC-7** — Slice 6.3 §5 user-facing route 404 behaviors preserved:
  unknown id → 404, archived → 404, unpublished → 404. AC-7 of slice
  6.3 + this AC overlap intentionally — both must stay green.
- **AC-8** — Admin shell auth gate (slice 6.4a) continues to gate
  6.4b's editor pages — non-admin → 403 at every BE write route, and
  `<AdminGate>` redirect at every FE editor mount.
- **AC-9** — `app/api/v1/routes/{admin,quiz_items,lessons,decks}.py`,
  `app/services/{study_service,quiz_item_study_service,lesson_service}.py`
  modulo lesson_service body swap, `app/api/v1/routes/study.py` are
  unmodified or modified only as enumerated. `git diff --stat` shows
  the expected file set.
- **AC-10** — `LessonResponse`, `DeckResponse`, `QuizItemResponse`,
  `LessonWithQuizzesResponse`, `DeckLessonsResponse` shapes
  byte-identical. Schema additions are net-new classes only.
- **AC-11** — All 10 PostHog admin events fire from the BE service
  layer at end-of-transaction (mockable via `analytics_track`); test
  asserts property keys match §9 verbatim. `internal: true` set on
  every event payload.
- **AC-12** — Substantive `quiz_item` edits create a `version+1`
  replacement row + retire the old row with `superseded_by_id` link in
  the same transaction.
- **AC-13** — `archive_lesson` does NOT cascade-retire quiz_items
  (slice 6.1 §AC-4 invariant preserved).
- **AC-14** — Test suite stays green. New tests run under default
  `not integration` selector for BE; new FE tests run under default
  `npx vitest run`.
- **AC-15** — `react-hook-form` adopted in 6.4b editor pages (per
  audit §9.4 + §3 non-goal "do not retrofit existing forms"). Existing
  `PersonaPicker`, `EmailPreferences`, `MissionSetup`, etc. forms
  stay native-HTML — out of scope.
- **AC-16** — No new BACKLOG row created beyond B-064 + B-065.
- **AC-17** — `.agent/skills/analytics.md` updated with the 10 new
  admin event rows from §9.
- **AC-18** — `.agent/skills/admin-panel.md` updated to reflect the
  new admin write surface (decks / lessons / quiz_items) per the
  skill's "Adding a New Admin Endpoint" §9 checklist (step 9 calls
  this out explicitly).
- **AC-19** — CODE-REALITY.md regen (targeted): §3 +12 admin write
  routes, §4 +3 admin services + lesson_service body-swap note, §6
  fixture-file deletion note, §7 component graph +6 admin pages /
  components, §13 spec #04 status flip per CR §11 drift item 18
  (`## Status:`). Header SHA bump.

## 12. Decisions

> Phase-level decisions (G2, H1, I1, J2) are recorded in the
> front-matter Phase 6 locked-decisions table and elaborated in the
> §3 non-goals + below. Slice-local decisions are numbered
> D-1, D-2, …

### Slice-local decisions

- **D-1 — Recommend split into 6.4a (shell) + 6.4b (CRUD + body swap
  + fixture retirement).** File count audit projects ~35-40 files
  total (admin shell refactor + 3 BE route files + 3 BE service files
  + write schemas + body swap + fixture deletion + 4 FE editor pages +
  Markdown editor primitive + confirm modal + 4 hooks + api helpers +
  TS types + tests + analytics catalog update) — well over the
  authored single-slice threshold of ~25 files (per OQ-1). Audit
  R-4 explicitly recommends shell-first per audit §7.1 finding on the
  868-line `AdminPanel.tsx`. The split files two BACKLOG impl-tracker
  rows: B-064 (6.4a) + B-065 (6.4b). 6.4a is FE-only (no BE route
  changes); 6.4b contains all BE work + the FE editors filling 6.4a's
  placeholder pages. **Single-slice fallback:** if the impl prompt
  finds the shell-first split awkward (e.g. 6.4a placeholder pages
  feel like dead code shipping to production), it MAY collapse to a
  single B-064 slice — the spec body is structured so either split
  works. The authored hint is split; the impl prompt can lift to a
  locked decision.
- **D-2 — Slice 6.3 §5 route surfaces + response shapes are LOCKED
  unchanged.** Carried in §4 preamble. The 6.3 → 6.4 swap is internal
  to `lesson_service.py` function bodies; no FE consumer redeploy
  needed; AC-5 + AC-7 verify. Rationale: minimizes blast radius of
  6.4b — admin authoring doesn't double as a FE consumer rewrite.
- **D-3 — All admin writes are synchronous (G2).** Substantive-edit
  retirement cascade runs in the same DB transaction as the lesson
  PATCH; no RQ enqueue, no Railway cron. Rationale: G2 locks RQ for
  ingestion (slice 6.10) and cron for daily Pro digest (slice 6.14);
  admin authoring is neither. Adding async fan-out to admin save would
  introduce a new failure mode (transaction commits but cascade RQ job
  fails) without product benefit (admin sees the cascade outcome
  inline via `LessonUpdateResponse`).
- **D-4 — Admin authoring writes directly to Postgres Text columns
  (H1).** No R2 binding, no `app/data/decks/seed_lessons/*.md`
  involvement. Rationale: H1 locks R2 for ingestion artifacts (slice
  6.10) and seed-content layout for slice 6.4.5; slice 6.4 is neither.
  Admin authors `concept_md` / `production_md` / `examples_md` Text
  columns directly via the lesson editor — same persistence path as
  every other lesson field.
- **D-5 — Admin events PostHog-only at 6.4 impl time (I1).** Postgres
  events tables (`quiz_review_events`, `lesson_view_events`) ship in
  slice 6.0; slice 6.4 admin events fire to PostHog + persist via the
  existing `admin_audit_log` row (per spec #38 E-018a). Rationale: I1
  decouples slice 6.4 from slice 6.0 (which is not yet on disk);
  retroactive Postgres dual-write is a follow-up if the slice-0 spec
  retains the events-table FK constraints implied by I1.
- **D-6 — Admin-side quality assessment is out of scope (J2).**
  `lessons.quality_score` stays NULL on admin-authored content; the
  `card_quality_signals` table is a slice 6.13.5 concern. Rationale:
  J2 explicitly defers quality-signal infrastructure; slice 6.4 admin
  authoring focuses on CRUD + lifecycle, not quality scoring.
- **D-7 — Admin route audit chain locked at
  `audit_admin_request → require_admin`.** Carried in §5 preamble.
  Per `.agent/skills/admin-panel.md` §Audit Logging + spec #38 E-018a
  + CR §3 admin block. Every new admin route lands one
  `admin_audit_log` row per request. AC-3 verifies.
- **D-8 — Substantive lesson edits cascade-retire quiz_items in same
  DB transaction.** Locked in §7 preamble. Mirrors slice 6.1 §4.3
  retirement semantic. Rationale recorded in §7.1 — server-side rule
  re-validation is the boundary against client-side soft-edits that
  would orphan FSRS history pointing at the old answer.
- **D-9 — Three admin route files, three admin service files; no
  monolithic `app/api/v1/routes/admin_curriculum.py`.** Mirrors the
  existing `admin.py` (cards) + `admin_analytics.py` (analytics) split
  per CR §3. Rationale: keeps file size bounded (audit §7.1 +
  AdminPanel.tsx-already-868-lines finding); each domain (deck /
  lesson / quiz_item) has its own route + service file. The FE
  multi-route shell (slice 6.4a) mirrors the BE split.
- **D-10 — `EditClassification` `Literal` alias lives in
  `app/schemas/lesson.py`.** Mirrors slice 6.1's `Literal` ENUM
  pattern (D-3 of slice 6.1). The `quiz_item` PATCH route imports the
  alias from `lesson.py` to avoid a duplicate type. Rationale: there's
  exactly one classification rule across both edit paths — duplicating
  the type would invite drift.
- **D-11 — Admin error classes consolidated in `app/services/admin_errors.py`.**
  Slice 6.2 D-1 locked-in service-by-service error duplication for the
  FSRS-helpers split; slice 6.4 admin services share enough errors
  (slug conflicts, archive states, classification disagreements) that
  a single shared module is cleaner. Rationale: 6.2's
  `QuizItemNotFoundError` stays where it is; the new admin
  `QuizItemNotFoundError` in `admin_errors.py` is a separate class
  for a separate code path. Slice 6.15 cleanup folds them into a
  single shared `quiz_item_errors.py` if useful — out of 6.4 scope.
- **D-12 — `AdminPanel.tsx` is deleted in 6.4a (extract path), not
  re-exported.** Recommendation in §8.5; impl prompt may flip if a
  call-site outside `App.tsx` surfaces (e.g. a deep-link to
  `pages/AdminPanel`). At spec-author time `grep -rn "AdminPanel" hirelens-frontend/src/`
  was not run — pre-flight at impl time is the gate. Rationale:
  delete-not-rename minimizes the drift surface — there's exactly one
  consumer today (`App.tsx`); the rename is a one-line change.
- **D-13 — `react-hook-form` adopted for 6.4b editor pages only.**
  audit §9.4 flagged the dep as installed-but-unused; 6.4b is the
  natural first consumer (heavy form-rich admin surface). Existing
  uncontrolled forms (PersonaPicker, EmailPreferences, MissionSetup,
  etc.) are out of scope (§3 non-goal). Rationale: don't pay the
  retrofit cost in this slice; let `react-hook-form` adoption spread
  organically across future form-rich slices.
- **D-14 — `AdminAudit.tsx` FE consumer never shipped despite the BE
  `/api/v1/admin/audit` endpoint landing in E-018a (`3b43772`,
  2026-04-23).** Spec author (slice 6.4 spec-author at `309f6c4`)
  referenced an `AdminAudit.tsx` page in §8.5 + §11 6.4a AC-3 + §10.1
  that does not exist on disk; this slice (6.4a impl) drops
  `/admin/audit` from the sidebar entirely rather than ship dead UI.
  The BE endpoint remains live and un-consumed. A future slice may
  build the FE consumer when product demand surfaces — file as a new
  BACKLOG row at that time. Drift logged in `SESSION-STATE.md`.
- **D-15 (resolves OQ-2) — `lesson_service.py` body-swap queries use
  `selectinload(Lesson.quiz_items)`.** Mirrors slice 6.2 precedent
  (`app/services/quiz_item_study_service.py`). Avoids N+1 on
  `getDeckLessons` / `getLesson` paths; cost is one extra SELECT per
  relationship per request, negligible at expected request volume.
  Cross-ref §4.2.
- **D-16 (resolves OQ-3) — Admin-LIST `?status=` query param
  vocabulary: `'active'` | `'drafts'` | `'published'` | `'archived'` |
  `'all'`.** Default `'active'`. `'active'` includes drafts AND
  published; excludes archived (so the authoring queue is not
  fragmented). Vocabulary applies to all three admin-LIST endpoints
  (decks, lessons, quiz_items) per §5. Drafts surfaced via
  `?status=drafts` using `ix_lessons_review_queue` from slice 6.1
  §4.2. Cross-ref §5.4.
- **D-17 (resolves OQ-4) — Substantive-edit confirm modal preview
  computes classification FE-side via new `src/utils/lessonEdit.ts`.**
  Module exports `classifyEdit(before, after) -> 'minor' |
  'substantive'` mirroring the BE rule (>15% char-delta on
  `concept_md` / `production_md` / `examples_md`). BE re-validates on
  PATCH per §7.1; FE classification is advisory-only for
  confirm-modal UX (no extra round trip). Both sides import from the
  same threshold constant `SUBSTANTIVE_EDIT_THRESHOLD = 0.15` —
  declared FE-side in `lessonEdit.ts`, BE-side in
  `app/services/admin_errors.py` constants block (per D-11). Drift
  case is handled by `EditClassificationConflictError` per §7.1.
  Cross-ref §7.1, §7.2.
- **D-18 (resolves OQ-5) — Quiz_item version cascade rules differ by
  edit path.**
  - **Lesson-level substantive PATCH** → cascade-retires all active
    `quiz_items` for that lesson in the same DB transaction (per
    D-8). Sets `quiz_items.retired_at = now()`. Does NOT auto-create
    replacements — admin authors new quiz_items manually after
    lesson edit. Rationale: a lesson body change does not necessarily
    invalidate every question; auto-replacement would be a wrong
    assumption about admin intent.
  - **Quiz_item-level substantive PATCH** → retire-and-replace:
    insert a new `quiz_item` row with `version = old.version + 1`,
    set `old.superseded_by_id = new.id`, set
    `old.retired_at = now()`. Preserves FSRS history continuity via
    the `superseded_by_id` foreign key chain (downstream
    FSRS-history follow-up out of scope this slice).

  Cross-ref §7.3, §5 quiz_item PATCH endpoint.
- **D-19 (resolves OQ-6) — `decks.persona_visibility` is admin-
  editable post-creation, with FE narrowing-confirm modal.**
  Narrowing edits (removing one or more personas from the array)
  trigger a `ConfirmPersonaNarrowingModal` on the FE before PATCH
  submit. Modal copy: "Narrowing persona visibility will hide this
  deck from N learners currently in personas X, Y. Their existing
  FSRS progress on quiz_items in this deck is preserved but they
  will no longer see the deck in /learn surfaces. Continue?" BE
  PATCH validates the change but does not gate it (service layer
  simply persists; FE owns the warning). New event
  `admin_deck_persona_narrowed {deck_id, removed_personas,
  before_count, after_count}` added to §9 events table. Cross-ref
  §6.2.

  **Open follow-up flagged for slice 6.7 / 6.8:** narrowing does not
  retire in-flight `quiz_item_progress` rows for users now in
  excluded personas — those rows linger but become unreachable via
  /learn surfaces. If FSRS-history orphan cleanup is desired, file a
  separate B-row at slice 6.7 (persona Learn) impl time.

## 13. Out of scope (explicit list)

- Slice 6.4.5 (seed lessons via `app/data/decks/seed_lessons/*.md`).
- Slice 6.5 (lesson UX polish + three-layer quality user-thumbs surface).
- Slice 6.6 (Lens-ranked deck/card ordering).
- Slice 6.7 (persona Learn page composition).
- Slice 6.8 (FSRS retention dashboard).
- Slice 6.9 (edit-classification rule logic refinement — slice 6.4
  ships the >15% threshold trigger; slice 6.9 may refine the metric).
- Slice 6.10 (RQ ingestion pipeline).
- Slice 6.11 (Gemini-assisted lesson generation).
- Slice 6.12 (Claude critique).
- Slice 6.13 (golden-set evaluation).
- Slice 6.13.5 (`card_quality_signals` user-thumbs dimension).
- Slice 6.14 (daily Pro digest).
- Slice 6.15 (Phase-6 cleanup — drops legacy `cards`/`categories`,
  consolidates duplicate error classes per D-11, etc.).
- Slice 6.16 (admin dashboard for FSRS retention).
- Card quality signals dual-write — J2 / slice 6.13.5.
- Gemini-assisted lesson generation — slice 6.11.
- Claude critique on save — slice 6.12.
- Golden-set evaluation — slice 6.13.
- AI-anything else.
- Promotion UI for admins — out of phase 6.
- `/admin/critique-runs` surface — slice 6.12.
- `react-hook-form` retrofit of existing forms (PersonaPicker, EmailPreferences, etc.).
- DB schema changes — N7 STOP.
- Touching `app/api/v1/routes/quiz_items.py` (slice 6.2).
- Touching `app/api/v1/routes/{lessons,decks}.py` (slice 6.3 user-facing).
- Touching `pages/Lesson.tsx` / `LessonRenderer.tsx` / `QuizItemPanel.tsx` (slice 6.3).
- Mutating slice-6.1 / 6.3 read shapes.
- BE Postgres event-table dual-write — slice 6.0.
- Admin-side LLM calls — slice 6.11 / 6.12.

## 14. Open questions

> Questions the schema design surfaced but does NOT block this spec.
> Resolve in the implementation slice's pre-flight or in a follow-up.
> Recommendations are AUTHORED HINTS, not locked decisions; the impl
> prompt may lift any of them to LD-N.

- **OQ-1 — Single-slice or split shell-first / CRUD-second?** File
  count projects ~35-40 (well over the ~25 threshold from the prompt's
  authored hint); audit R-4 + spec authoring lean toward split. **Authored
  hint:** SPLIT into 6.4a (shell, B-064) + 6.4b (CRUD + body swap +
  fixture retirement, B-065). Single-slice fallback documented in §12
  D-1. Impl prompt confirms or flips at slice-start.
- **OQ-2 — `selectinload` or N+1-tolerant lazy load on the four
  `lesson_service` body-swap queries?** User-facing
  `/api/v1/lessons/{id}` will notice the difference at scale; admin-
  facing surface won't. **Authored hint:** `selectinload` on all four
  queries — mirrors slice 6.2's `get_current_user` eager-load
  precedent + the slice-6.1 partial-index design that already
  optimizes this access pattern. Trade-off acknowledged: one extra
  SELECT per relationship per request; cost negligible at the
  expected request volume.
- **OQ-3 — Admin-LIST route status filter shape.** Three options:
  drafts only, all (drafts + published + archived), paginated
  `?status=` query param. **Authored hint:** `?status=` query param
  with sensible defaults — `'active'` for decks (excludes archived),
  `'active'` for lesson list (excludes archived; drafts AND published
  shown together so authoring queue isn't fragmented). Drafts surfaced
  via `?status=drafts` using `ix_lessons_review_queue` from slice 6.1
  §4.2. The exact filter vocabulary (`'drafts'` vs `'unpublished'` vs
  `'review'`) is impl judgment.
- **OQ-4 — Substantive-edit cascade UX: confirm modal placement +
  preview computation.** Synchronous DB transaction is locked at §7
  D-8. Open question is FE flow: does the modal preview compute the
  cascade FE-side (mirroring §7.1 BE rule — risk of FE/BE drift) or
  call a `POST /api/v1/admin/lessons/:id/preview-edit` dry-run
  endpoint (one extra round trip)? **Authored hint:** FE-side preview
  using a shared TS function that mirrors the BE `_is_substantive_change`
  rule — mounted in `src/utils/lessonEdit.ts` so unit tests pin the
  parity. BE re-validates via `EditClassificationConflictError` per
  §7.1 — handles the drift case. Trade-off: 0 extra round trips vs
  potential FE/BE drift. Authored hint is preview-FE-side.
- **OQ-5 — Quiz_item version cascade on substantive lesson edit:
  retire-only or retire-and-replace?** Slice 6.1 §4.3 supports both
  (`retired_at` + optional `superseded_by_id`). Authored hint:
  **retire-only** on lesson cascade (each old quiz_item gets
  `retired_at = func.now()` set; `superseded_by_id` stays NULL — admin
  re-authors quiz_items separately). Rationale: lesson-level
  substantive edit changes the body but not necessarily the questions
  — auto-creating replacement quiz_items would be a wrong assumption
  about admin intent. Quiz_item-level substantive edit (per §5.10 +
  §7.4) DOES retire-and-replace because the old question/answer is
  being explicitly replaced. The two paths are deliberately distinct.
- **OQ-6 — `persona_visibility` editing on decks: admin-editable
  post-create or set-once at create?** Slice 6.1 schema allows
  mutation. Product call. **Authored hint:** admin-editable, with a
  warning modal if the edit narrows visibility (e.g. `'both' →
  'climber'` would hide the deck from `interview_prepper` users
  mid-stream — affects `quiz_item_progress` retention). The narrowing
  detection is FE-side; service layer simply persists. Modal copy:
  "This change will hide deck {title} from {N} active reviewers
  (last-reviewed within 7 days). Continue?" — N computed via a
  separate `GET /api/v1/admin/decks/:id/active-reviewers-count`
  endpoint OR inlined as a count via the response of the GET deck
  page. Impl prompt picks. Authored hint is admin-editable + warning.

---

*End of slice 6.4 spec. Authored 2026-04-27 at HEAD `95bb3c5`. Spec
basis: `docs/specs/phase-6/01-foundation-schema.md` (slice 6.1) +
`docs/specs/phase-6/02-fsrs-quiz-item-binding.md` (slice 6.2) +
`docs/specs/phase-6/03-lesson-ux.md` (slice 6.3) +
`docs/audits/phase-6-scout.md` (commit `5b0aa23`) + `.agent/skills/admin-panel.md`
+ `docs/specs/phase-5/38-admin-analytics.md` (audit_admin_request
chain origin) + `CODE-REALITY.md` (CR §3 routes / §6 services / §11
drift / §13 specs). Next step: Mode 1 implementation slice executes
against this spec — files B-064 and B-065 at execution time per R17,
or B-064-only if the impl prompt collapses per §12 D-1 single-slice
fallback.*
