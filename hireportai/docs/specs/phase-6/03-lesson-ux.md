# Phase 6 — Slice 6.3: Lesson-Card UX (FE-first, fixture-driven, BE read-only)

## Status: Shipped (spec + impl) — closes B-063. Impl `ba00331` on 2026-04-27.

| Field | Value |
|-------|-------|
| Phase | 6 (Curriculum Platform) |
| Slice | 6.3 — lesson-card UX |
| Mode | 4 (spec-author) |
| Author HEAD | `a02639c` (post-slice-6.2 SHA backfill) |
| Spec authored | 2026-04-27 |
| Implementation slice | TBD (will follow this spec) |
| BACKLOG row | none yet — implementation slice files at execution time per R17 (next free is `B-063`; current highest in-use `B-062` per slice 6.2) |
| Spec dependencies | `docs/specs/phase-6/01-foundation-schema.md` (slice 6.1) — `decks`, `lessons`, `quiz_items` tables exist on disk + Pydantic schemas in `app/schemas/{deck,lesson,quiz_item}.py`. `docs/specs/phase-6/02-fsrs-quiz-item-binding.md` (slice 6.2) — `POST /api/v1/quiz-items/review` exists on disk + `QuizReviewRequest` / `QuizReviewResponse` Pydantic schemas in `app/schemas/quiz_item.py`. |
| Audit dependency | `docs/audits/phase-6-scout.md` (commit `5b0aa23`) — §1.4 card review UX live FE component graph, §1.5 persona filtering on Learn page, §6.3 internal analytics tables, §7.1 admin UI today. |
| Slice dependencies | **Upstream:** slice 6.1 (foundation schema) + slice 6.2 (FSRS quiz-item binding) — both required, both shipped. **Downstream:** unblocks slice 6.4 (admin authoring UI — replaces fixtures with DB persistence), 6.5 (three-layer quality — needs the lesson page surface to wire user-thumbs feedback), 6.7 (Learn-page composition — links from deck list to lesson page). |

### Phase 6 locked decisions referenced by this spec

| ID | Decision |
|----|----------|
| **G2** | Background jobs: not consumed by this slice (read-only routes, synchronous). |
| **H1** | Object storage: not consumed by this slice (lesson media is inline Markdown). The 12 locked-deck seed Markdown will eventually live at `app/data/decks/seed_lessons/*.md` per slice 6.4.5 — this slice's fixture-data file `app/data/lesson_fixtures.py` is a different artifact (Python, retires in 6.4) and does NOT prefigure that seed-content layout. |
| **I1** | Events: dual-write. Slice 6.0 owns the `lesson_view_events` Postgres table; this spec declares the contract for `lesson_viewed` and `lesson_section_expanded` events. |

---

## 1. Problem

Slices 6.1 + 6.2 shipped the foundation schema and the FSRS service +
routes against `quiz_item_progress`, but no FE consumer renders a
lesson page or routes user attention through the four-section
lesson-card UX (concept_md / production_md / examples_md / quiz panel)
that Phase 6's locked decision specifies. Without slice 6.3,
slice 6.4 (admin authoring UI) has no consumer surface to verify
content authoring against, slice 6.5 (three-layer quality) has no
user-thumbs target, and slice 6.7 (Learn-page composition) has no
lesson page to link to. Slice 6.3 ships the FE consumer surface
(page + components + types + tests) backed by **read-only BE routes
returning fixture data** so the lesson UX can be designed,
implemented, and verified before slice 6.4 introduces DB persistence
of lessons.

## 2. Goals

1. Ship the new FE page `pages/Lesson.tsx` mounted at
   `/learn/lesson/:id` (D-8), wrapped in `<ProtectedRoute>` (which
   internally wraps `<PersonaGate>`) — same protection envelope as
   the rest of `/learn/*` per `App.tsx:78-90` precedent.
2. Ship `components/lesson/LessonRenderer.tsx` rendering the
   four-section lesson layout (concept / production / examples /
   quiz panel) using `react-markdown` + `remark-gfm` (D-3) — no
   `dangerouslySetInnerHTML`, GFM tables + fenced code blocks
   render correctly.
3. Ship `components/lesson/QuizItemPanel.tsx` — quiz-submit panel
   scoped to a single `quiz_item` (D-7). Posts to
   `POST /api/v1/quiz-items/review` (slice 6.2 endpoint, D-5). Does
   NOT replace the legacy `components/study/QuizPanel.tsx` which
   stays alive for the legacy card flow until slice 6.15 cleanup.
4. Ship three new BE read-only routes at the new namespace
   `/api/v1/lessons` + `/api/v1/decks` (D-4): `GET /api/v1/lessons/{id}`,
   `GET /api/v1/decks/{id}`, `GET /api/v1/decks/{id}/lessons`. All
   return fixture data (D-2), all `Depends(get_current_user)`. No DB
   read in this slice — the fixture loader is the source of truth.
5. Ship `app/data/lesson_fixtures.py` (D-2) — a Python module
   exporting fully-typed Pydantic instances. Retires cleanly in
   slice 6.4 by switching the route handlers from the loader call to
   a DB query; **the route Pydantic shape stays unchanged across the
   6.3 → 6.4 switch**, so FE need not redeploy.
6. Ship a single source of truth for the lesson + deck wire shapes:
   BE Pydantic schemas in `app/schemas/lesson.py` + `app/schemas/deck.py`
   (slice 6.1 already ships read shapes for both — this slice extends
   them additively for list responses + the lesson page's quiz-item
   bundle). FE TS types added to `src/types/index.ts` mirror the
   Pydantic shape field-for-field.
7. Declare the `lesson_viewed` and `lesson_section_expanded` analytics
   events the implementation slice will fire (slice 6.0 owns the
   table; this spec locks the payload shape).

## 3. Non-goals

- **DB persistence of lessons / decks** — slice 6.3 ships read-only
  routes returning fixture data only. No `lesson_service.create_lesson(...)`
  or admin-write paths. DB persistence of authored content is slice 6.4.
  (D-4)
- **Admin authoring UI** — slice 6.4. No `/admin/lessons` or
  `/admin/decks` routes; no AdminPanel changes.
- **New quiz-submit endpoint** — quiz submission goes through the
  slice 6.2 endpoint `POST /api/v1/quiz-items/review`. **Do NOT
  introduce a new submit path.** (D-5)
- **Persona-aware ranking** — the lesson page renders the lesson it's
  given. No "next lesson by persona" logic. Slice 6.6 owns ranking;
  slice 6.7 owns persona-aware composition. (D-6)
- **Daily-flow integration** — daily review is per-quiz_item per slice
  6.2 (`GET /api/v1/quiz-items/daily`), NOT per-lesson. The lesson
  page is invoked via direct navigation (`/learn/lesson/:id`), deck
  detail navigation (out of scope here, slice 6.7), or — in future
  slices — a "lesson card" surface composed by the Learn page. (D-6)
- **Code-fence syntax highlighting** — defer (OQ-2 below). Plain
  fenced-code rendering ships in 6.3; syntax highlighting is its own
  slice if any.
- **Lesson-list deck navigation chrome** — sidebar / prev-next /
  breadcrumb / "back to deck" — defer to slice 6.7 (Learn-page
  composition). The lesson page in 6.3 renders lesson content + quiz
  panel only; navigation back to `/learn` is via the existing
  `AppShell` chrome.
- **Quiz scoring / answer-reveal UX beyond what slice 6.2's wire
  shape provides** — slice 6.2's `QuizReviewResponse` returns FSRS
  state post-review (`fsrs_state`, `stability`, `difficulty`,
  `due_date`, `reps`, `lapses`, `scheduled_days`); the lesson page
  surfaces this same response. Whether the user sees a literal
  "correct / incorrect" verdict or a self-rated FSRS scale is
  resolved at OQ-4.
- **DB schema changes** — slice 6.1 already shipped `decks`,
  `lessons`, `quiz_items`, `quiz_item_progress`. No Alembic migration
  in this slice. (N7 STOP if a gap surfaces.)
- **Mutating gamification on lesson view** — slice 6.2 D-7 covers
  XP/streak on quiz_item review; slice 6.3 ships no
  gamification-service call from the lesson page or its routes.
- **Server-side rendering of Markdown** — react-markdown renders
  client-side. BE never serializes HTML.
- **Free-tier wall on lesson reads** — out of scope. Slice 6.7
  composes deck.tier-aware filtering; this slice's routes are
  authenticated but not tier-gated, so a free user can deep-link to
  any fixture lesson. The expected "free tier locked" UX lives at
  slice 6.7 list-level, not slice 6.3 detail-level.

## 4. Service surface — fixture loader + route handlers

> **D-2 (locked).** Fixture data location is `app/data/lesson_fixtures.py`
> exporting fully-typed Pydantic instances. NOT JSON, NOT
> Markdown-with-frontmatter. Rationale: typed import — schema drift
> surfaces at module-import time, not at request time; no parse step;
> retires cleanly when slice 6.4 ships real authoring (delete file +
> swap loader call to a DB query — wire shape stays the same).

### 4.1 `app/data/lesson_fixtures.py`

Module surface (function signatures only — content is §7):

```python
from app.schemas.deck import DeckResponse
from app.schemas.lesson import LessonResponse
from app.schemas.quiz_item import QuizItemResponse


def list_decks() -> list[DeckResponse]: ...
def get_deck(deck_id: str) -> DeckResponse | None: ...
def list_lessons(deck_id: str) -> list[LessonResponse]: ...
def get_lesson(lesson_id: str) -> LessonResponse | None: ...
def list_quiz_items(lesson_id: str) -> list[QuizItemResponse]: ...
```

Behavioral notes:
- Module-level constants `_DECKS`, `_LESSONS`, `_QUIZ_ITEMS` populated
  at import time. Each is a `dict[str, Pydantic instance]` keyed by
  `id`.
- `get_*` returns `None` for unknown IDs (route handler maps `None`
  → 404).
- `list_*` returns a stable-ordered list (decks by `display_order`,
  lessons by `display_order`, quiz_items by `display_order`).
- All instances built directly from `app/schemas/{deck,lesson,quiz_item}.py`
  — no shadow types, no JSON loads.

### 4.2 `app/services/lesson_service.py`

Thin wrapper over the fixture loader (so slice 6.4 swaps in a DB
query without touching route handlers).

```python
async def get_lesson_with_quizzes(
    lesson_id: str, db: AsyncSession
) -> LessonWithQuizzesResponse | None: ...

async def get_deck_with_meta(
    deck_id: str, db: AsyncSession
) -> DeckResponse | None: ...

async def list_lessons_in_deck(
    deck_id: str, db: AsyncSession
) -> list[LessonResponse]: ...
```

Behavioral notes:
- Slice 6.3 implementations ignore `db` and call `lesson_fixtures`.
  The signature accepts `db` so slice 6.4 swap is signature-clean.
- `get_lesson_with_quizzes` bundles the lesson Pydantic model with
  its quiz_items list — the lesson page renders all four sections
  from a single response (lesson body + quiz_items list); avoids an
  N+1 over `/api/v1/quiz-items/...`.
- Returns `None` from `get_*` when the loader returns `None`.

### 4.3 Route handlers (signatures only — full surface in §5)

```python
@router.get("/lessons/{lesson_id}", response_model=LessonWithQuizzesResponse)
async def get_lesson_route(lesson_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> LessonWithQuizzesResponse: ...

@router.get("/decks/{deck_id}", response_model=DeckResponse)
async def get_deck_route(deck_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> DeckResponse: ...

@router.get("/decks/{deck_id}/lessons", response_model=DeckLessonsResponse)
async def list_deck_lessons_route(deck_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> DeckLessonsResponse: ...
```

Behavioral notes:
- All three: 401 on unauthenticated, 404 on unknown `id`. No
  ownership check (lesson/deck content is shared, not user-scoped).
- Two routers: one for `/lessons/...` (`app/api/v1/routes/lessons.py`)
  and one for `/decks/...` (`app/api/v1/routes/decks.py`). Splitting
  by resource keeps the file small and matches existing repo
  precedent (e.g. `cards.py` vs `study.py` are separate routers).

## 5. Route surface — `app/api/v1/routes/{lessons,decks}.py`

All endpoints `Depends(get_current_user)`. Global slowapi default
(100 req/min) — no per-route override.

### 5.1 `GET /api/v1/lessons/{lesson_id}`

| Field | Value |
|-------|-------|
| Method | GET |
| Path | `/api/v1/lessons/{lesson_id}` |
| Auth | `Depends(get_current_user)` |
| Path params | `lesson_id: str` (UUID-as-string) |
| Response model | `LessonWithQuizzesResponse` (§6.2) |
| Status codes | 200 / 401 / 404 (unknown lesson_id) |
| Rate limit | global default 100 req/min |

Behavior: returns lesson body + ordered list of active (not retired)
quiz_items. Archived lessons (`archived_at IS NOT NULL`) return 404
in this slice — fixture data has no archived lessons, but the
implementation slice's loader filters them so 6.4's DB swap is
behavior-identical.

### 5.2 `GET /api/v1/decks/{deck_id}`

| Field | Value |
|-------|-------|
| Method | GET |
| Path | `/api/v1/decks/{deck_id}` |
| Auth | `Depends(get_current_user)` |
| Response model | `DeckResponse` (slice 6.1's existing schema; reused as-is) |
| Status codes | 200 / 401 / 404 |
| Rate limit | global default 100 req/min |

### 5.3 `GET /api/v1/decks/{deck_id}/lessons`

| Field | Value |
|-------|-------|
| Method | GET |
| Path | `/api/v1/decks/{deck_id}/lessons` |
| Auth | `Depends(get_current_user)` |
| Response model | `DeckLessonsResponse` (§6.3) |
| Status codes | 200 / 401 / 404 (unknown deck_id) |
| Rate limit | global default 100 req/min |

Behavior: returns the deck shell + its ordered list of lessons. Empty
`lessons` list when the deck exists but has no lessons (200, not 404).

### 5.4 Wiring

`app/main.py` mounts both routers under `/api/v1`:

```python
app.include_router(v1_lessons.router, prefix="/api/v1", tags=["v1 Lessons"])
app.include_router(v1_decks.router,   prefix="/api/v1", tags=["v1 Decks"])
```

Following the slice 6.2 precedent for register-after-`v1_quiz_items`
ordering. Implementation slice picks final ordering per repo
convention.

## 6. Pydantic schemas

> Slice 6.1 shipped `app/schemas/deck.py::DeckResponse` and
> `app/schemas/lesson.py::LessonResponse` — the lesson read shape
> covers the four content fields the renderer needs. Slice 6.3
> extends additively for two new bundled responses + reuses
> existing schemas elsewhere.

### 6.1 Existing slice-6.1 schemas reused

- `app/schemas/deck.py::DeckResponse` — used as-is in `GET /decks/{id}`.
  Already has `id, slug, title, description, display_order, icon,
  persona_visibility, tier, created_at, updated_at, archived_at`
  fields.
- `app/schemas/lesson.py::LessonResponse` — used as-is for the lesson
  body inside `LessonWithQuizzesResponse`. Already has `id, deck_id,
  slug, title, concept_md, production_md, examples_md, display_order,
  version, version_type, published_at, generated_by_model,
  source_content_id, quality_score, created_at, updated_at,
  archived_at` fields.
- `app/schemas/quiz_item.py::QuizItemResponse` — used as-is for the
  quiz_item entries inside `LessonWithQuizzesResponse`. Already has
  `id, lesson_id, question, answer, question_type, distractors,
  difficulty, display_order, version, superseded_by_id, retired_at,
  generated_by_model, created_at, updated_at` fields.

### 6.2 New: `LessonWithQuizzesResponse` (extend `app/schemas/lesson.py`)

Lesson body + ordered list of active quiz_items, returned by
`GET /api/v1/lessons/{lesson_id}`.

| Field | Type | Source-of-truth | Notes |
|-------|------|-----------------|-------|
| `lesson` | `LessonResponse` | slice 6.1 schema | Full lesson body. |
| `quiz_items` | `list[QuizItemResponse]` | slice 6.1 schema | Active quiz_items only (`retired_at IS NULL`), ordered by `display_order`. |
| `deck_id` | `str` | `lessons.deck_id` (also redundantly `lesson.deck_id`) | Lifted to top level for FE convenience (breadcrumb / back-link). |
| `deck_slug` | `str` | `decks.slug` | Lifted top-level for stable URLs in FE breadcrumb. |
| `deck_title` | `str` | `decks.title` | Lifted top-level for breadcrumb display. |

`model_config = ConfigDict(from_attributes=True)`.

### 6.3 New: `DeckLessonsResponse` (extend `app/schemas/deck.py`)

Deck shell + ordered list of lessons, returned by
`GET /api/v1/decks/{deck_id}/lessons`.

| Field | Type | Source-of-truth | Notes |
|-------|------|-----------------|-------|
| `deck` | `DeckResponse` | slice 6.1 schema | Full deck body. |
| `lessons` | `list[LessonResponse]` | slice 6.1 schema | Active lessons only (`archived_at IS NULL`), ordered by `display_order`. |

`model_config = ConfigDict(from_attributes=True)`.

### 6.4 Schema audit — no conflict with slice 6.1

The slice 6.1 schemas are used as-is. The two new types
(`LessonWithQuizzesResponse`, `DeckLessonsResponse`) are net-new
classes in their respective files; no fields renamed, no `Literal`
types modified. AC-9 (slice 6.1) remains green.

## 7. Fixture content — file shape

> Spec defines the **shape**, not the literal text. Implementation
> slice picks the canonical sample content (likely cribbed from the
> Phase 6 audit + product framing for the 12 locked decks). Treat
> the lesson titles below as illustrative, not normative.

`app/data/lesson_fixtures.py` ships **2-3 sample lessons** across
**1-2 decks** sufficient to exercise the renderer + route surface:

- **Deck 1 — `transformer-llm-internals`** (sample slug; `tier='foundation'`, `persona_visibility='both'`):
  - **Lesson 1.1 — slug `attention-mechanism`** — short concept_md
    (~3 paragraphs), production_md with one `pip install` snippet
    (fenced code block), examples_md with a GFM table comparing
    self-attention vs cross-attention. **3 quiz_items** covering
    `question_type='free_text'`, `'mcq'` (with 3 distractors), and
    `'code_completion'`. Difficulty mix: 1 easy / 1 medium / 1 hard.
  - **Lesson 1.2 — slug `tokenization-byte-pair-encoding`** —
    concept_md medium-long, production_md with two fenced code
    blocks (Python BPE example + bash dependency install),
    examples_md with a numbered list. **2 quiz_items**, both
    `question_type='free_text'`.
- **Deck 2 — `agentic-systems-mcp`** (sample slug; `tier='premium'`,
  `persona_visibility='interview_prepper'`) (optional in v0):
  - **Lesson 2.1 — slug `mcp-tool-calling-loop`** — minimal content;
    serves the `tier='premium'` + `persona_visibility !='both'`
    branch coverage. **1 quiz_item** (`question_type='mcq'`).

Quiz_item count target: **6 total** across all fixture lessons —
enough for the Test Plan §8 `LessonRenderer` + `QuizItemPanel`
coverage matrix (one of each `question_type`, plus a happy-path
free-text submission).

The fixture file documents in its module docstring that retirement is
slice 6.4: deletion-not-replacement — slice 6.4 swaps the loader
call to a DB query and removes the file in the same commit.

## 8. FE component graph

> R16 component-graph audit applies. Per the audit (`docs/audits/phase-6-scout.md`
> §1.4) the only direct `Card` shape consumer is
> `hooks/useCardViewer.ts:3`. There is no existing `Lesson` /
> `LessonContent` / `Deck` shape in `src/types/index.ts` (verified at
> spec-author time — `grep -n "interface Lesson\|interface Deck"
> src/types/index.ts` returns zero hits). Slice 6.3's new types are
> net-new; no rename, no merge.

### 8.1 New files

| File | Purpose |
|------|---------|
| `src/pages/Lesson.tsx` | New page mounted at `/learn/lesson/:id`. Loads `useLesson(id)`, renders `<LessonRenderer lesson={...} />`. Persona-gated (inside `<ProtectedRoute>`). |
| `src/components/lesson/LessonRenderer.tsx` | Renders four-section layout (concept_md / production_md / examples_md / quiz panel). Uses `react-markdown` + `remark-gfm` to render the three Markdown sections. The quiz panel section iterates over `lesson.quiz_items` and mounts `<QuizItemPanel>` per item. |
| `src/components/lesson/QuizItemPanel.tsx` | Quiz-submit panel scoped to a single quiz_item. Posts to `POST /api/v1/quiz-items/review` (slice 6.2 endpoint). State machine: idle → revealed → submitting → done. Mirrors `QuizPanel.tsx`'s state-machine shape but talks to the quiz_item route, not the legacy card route. **Does NOT replace `study/QuizPanel.tsx`** — both coexist until slice 6.15. |
| `src/hooks/useLesson.ts` | `(lessonId: string) => { lesson, isLoading, error, reload }` hook. Calls `fetchLesson(lessonId)` from `services/api.ts`. |
| `src/services/api.ts` (extension) | New module-level helpers: `fetchLesson(lessonId): Promise<LessonWithQuizzes>`, `fetchDeck(deckId): Promise<Deck>`, `fetchDeckLessons(deckId): Promise<DeckWithLessons>`, `submitQuizReview(req: QuizReviewRequest): Promise<QuizReviewResponse>`. The submit helper is **net-new** even though slice 6.2 shipped the BE route — no FE consumer existed pre-6.3. |
| `src/types/index.ts` (extension) | Net-new TS types `Lesson`, `Deck`, `QuizItem`, `LessonWithQuizzes`, `DeckWithLessons`, `QuizReviewRequest` (already-aliased shape from slice 6.2; re-declare here for the FE-side consumer), `QuizReviewResponse` (same), and `QuestionType` / `DeckTier` / `PersonaVisibility` / `LessonVersionType` `union` aliases. Field-for-field mirrors of the BE Pydantic shapes. |

### 8.2 Modified files

| File | Change |
|------|--------|
| `src/App.tsx` | Add `<Route path="/learn/lesson/:id" element={<ProtectedRoute><Lesson /></ProtectedRoute>} />` inside the existing `/learn/*` block (line ~89, after `/learn/card/:id`). Persona-gating inherited via `<ProtectedRoute>`. |
| `package.json` | Add `remark-gfm` (net-new dep) under `dependencies`. **Drift surfaced at spec-author time:** `react-markdown@^10.1.0` is **already** a dependency (consumed by `src/components/rewrite/ResumeEditor.tsx:4-185`). D-3 says "new FE deps" — only `remark-gfm` is net-new. Implementation slice runs `npm install remark-gfm` and verifies the lockfile updates without churning the existing react-markdown version. |

### 8.3 Existing components — no touch

- `src/components/study/QuizPanel.tsx` — **untouched** (D-7 explicit:
  `QuizItemPanel` is a NEW component, NOT a rename). `QuizPanel`
  continues to power the legacy card-based `/learn/daily`,
  `/learn/card/:id`, `/learn/mission` flows.
- `src/components/rewrite/ResumeEditor.tsx` — **untouched** (continues
  using react-markdown without remark-gfm).
- `src/types/index.ts::Card` interface (line 148) — **untouched**
  (slice 6.15 retires).
- `src/components/study/FlipCard.tsx`, `DailyReviewWalledView.tsx`,
  `WallInlineNudge.tsx`, `CategoryCard.tsx` — **untouched**.

### 8.4 Wire-shape contract — single source of truth

For each shared shape, the BE Pydantic schema is the source of truth;
the FE TS type mirrors it field-for-field. To prevent silent drift,
the implementation slice ships **at least one FE test that
asserts a fixture-shaped object satisfies the TS type**:

```ts
// tests/types/Lesson.shape.test.ts (or similar)
const fixture: Lesson = { id: '...', deck_id: '...', slug: '...', title: '...',
  concept_md: '...', production_md: '...', examples_md: '...', display_order: 0,
  version: 1, version_type: 'initial', published_at: null, generated_by_model: null,
  source_content_id: null, quality_score: null, created_at: '...', updated_at: '...',
  archived_at: null }
expect(fixture.id).toBeDefined()
```

Similar for `Deck`, `QuizItem`, `LessonWithQuizzes`. tsc would catch
field renames; this guard catches accidental optionalization or
field deletion in the TS type during refactors.

## 9. Analytics events declared by this slice

| Event | Emit point | Properties | PostHog | Postgres (slice 6.0) |
|-------|------------|-----------|---------|----------------------|
| `lesson_viewed` | FE `Lesson.tsx` `useEffect` once-per-mount (idempotent via `useRef`, matches `home_dashboard_viewed` precedent) | `{lesson_id, deck_id, deck_slug, version, persona, plan}` | ✓ | ✓ (powers slice 6.16 retention dashboard's "lessons viewed per active user" metric) |
| `lesson_section_expanded` | FE `LessonRenderer.tsx` — fires when a section is uncollapsed (only meaningful if §11 OQ-3 picks a collapsed-by-default mobile layout). | `{lesson_id, section: 'concept' \| 'production' \| 'examples' \| 'quiz'}` | ✓ | — |

The `quiz_item_progress_initialized` and `quiz_item_reviewed` events
already declared in slice 6.2 §8 fire from the BE service layer when
`QuizItemPanel` submits. **Do not duplicate** with FE-side
`quiz_submitted` events — slice 6.2's events ARE the canonical record
per spec 6.2 §8 idempotency rule (BE-side, post-flush, single source).

## 10. Test plan

Implementation slice will add tests in three files (matching repo
flat layout per slice 6.1's D-024/D-025 disposition).

### 10.1 BE — `tests/test_lesson_fixtures_routes.py`

- `test_get_lesson_auth_required` — unauthenticated GET → 401.
- `test_get_lesson_404_unknown_id` — authenticated GET against random
  UUID → 404.
- `test_get_lesson_returns_fixture_with_quizzes` — authenticated GET
  against fixture lesson_id returns `LessonWithQuizzesResponse` with
  populated `lesson` body + `quiz_items` ordered by `display_order` +
  top-level `deck_id` / `deck_slug` / `deck_title`.
- `test_get_deck_404_unknown_id` — authenticated GET against random
  UUID → 404.
- `test_get_deck_returns_fixture` — authenticated GET against fixture
  deck_id returns `DeckResponse`.
- `test_list_deck_lessons_returns_ordered` — lessons returned ordered
  by `display_order ASC`.
- `test_list_deck_lessons_empty_deck` — deck with zero lessons returns
  200 with empty `lessons` list (not 404).

### 10.2 FE — `tests/pages/Lesson.test.tsx`

- `test_lesson_page_renders_concept_production_examples` — mounts
  `<Lesson />` with mocked `useLesson` returning a fixture; asserts
  three Markdown sections render text content.
- `test_lesson_page_renders_gfm_table` — mocked fixture includes a
  GFM table in `examples_md`; asserts the rendered DOM contains a
  `<table>` element.
- `test_lesson_page_renders_fenced_code` — mocked fixture includes a
  fenced code block in `production_md`; asserts the rendered DOM
  contains a `<pre>` element.
- `test_lesson_page_404_branch` — `useLesson` returns 404 / null;
  asserts the empty-state copy renders ("This lesson doesn't exist
  yet" or similar — concrete copy in OQ-6).
- `test_lesson_page_route_mount_persona_gated` — renders
  `<App />` at `/learn/lesson/<id>` with persona-null user; asserts
  `<Navigate>` to `/onboarding/persona` (existing PersonaGate
  behavior).

### 10.3 FE — `tests/components/QuizItemPanel.test.tsx`

- `test_quiz_item_panel_idle_to_revealed` — renders question; clicks
  "Reveal Answer"; asserts answer is shown.
- `test_quiz_item_panel_submit_calls_review_endpoint` — mocks
  `submitQuizReview`; clicks "Good" rating; asserts the API call
  fires with `{quiz_item_id, rating: 3, session_id, time_spent_ms}`.
- `test_quiz_item_panel_done_state_renders_post_review_fsrs` —
  post-submit, asserts FSRS `due_date` / `scheduled_days` rendered.
- `test_quiz_item_panel_mcq_distractors_render` — fixture
  `question_type='mcq'` with 3 distractors → 4 radio buttons render
  before reveal.
- `test_quiz_item_panel_404_existing_progress_path` — mock
  `submitQuizReview` to return 409 (retired-no-progress); asserts the
  inline error copy renders without crashing.

**Target test count target: +14** (7 BE route + 5 FE Lesson page + 5
FE QuizItemPanel = 17; trim to ~14 if some collapse during impl).
Spec §10 of slice 6.2 set the precedent of multi-file test layout for
mixed BE + FE slices.

## 11. Acceptance criteria

The implementation slice (one-step follow-up) must pass:

- **AC-1** — `GET /api/v1/lessons/{lesson_id}` returns 200 with
  `LessonWithQuizzesResponse` for fixture lesson_ids; returns 404 for
  unknown lesson_ids; returns 401 for unauthenticated requests.
- **AC-2** — `GET /api/v1/decks/{deck_id}` returns `DeckResponse` (the
  slice 6.1 schema) with the same auth + 404 semantics.
- **AC-3** — `GET /api/v1/decks/{deck_id}/lessons` returns
  `DeckLessonsResponse` with `lessons` ordered by `display_order
  ASC`. Empty deck returns 200 with empty list (not 404).
- **AC-4** — `app/data/lesson_fixtures.py` exists; module imports
  cleanly; exports the five functions named in §4.1; populates at
  least 2 lessons across at least 1 deck with at least 6 total
  quiz_items spanning all three `question_type` values.
- **AC-5** — `pages/Lesson.tsx` mounts at `/learn/lesson/:id`,
  protected by `<ProtectedRoute>` (which includes `<PersonaGate>`).
- **AC-6** — `LessonRenderer.tsx` renders concept_md / production_md
  / examples_md as Markdown via `react-markdown` + `remark-gfm`. GFM
  tables and fenced code blocks render as `<table>` / `<pre>` DOM
  nodes. NO `dangerouslySetInnerHTML`.
- **AC-7** — `QuizItemPanel.tsx` posts to
  `POST /api/v1/quiz-items/review` (slice 6.2 endpoint) with
  `QuizReviewRequest` payload. Renders post-review FSRS state in the
  done state. Does NOT introduce a new submit endpoint (D-5).
- **AC-8** — `QuizPanel.tsx` (legacy card flow) is **unchanged** by
  this slice (D-7).
- **AC-9** — TS types `Lesson`, `Deck`, `QuizItem`,
  `LessonWithQuizzes`, `DeckWithLessons` exist in
  `src/types/index.ts` and mirror the BE Pydantic shapes
  field-for-field. `tsc --noEmit` clean.
- **AC-10** — `lesson_viewed` PostHog event fires once-per-mount on
  `pages/Lesson.tsx`. `quiz_item_reviewed` (slice 6.2's BE-side event)
  fires from the BE on `QuizItemPanel.tsx` submit (no FE-side
  duplicate event).
- **AC-11** — `package.json` adds `remark-gfm` as a new dependency.
  `react-markdown` (already present) is unchanged. Lockfile updated.
- **AC-12** — `app/api/v1/routes/quiz_items.py` (slice 6.2) and
  `app/api/v1/routes/study.py` (legacy) are **unchanged** by this
  slice. Verified by `git diff --stat` showing only
  `app/api/v1/routes/{lessons,decks}.py` (new), `app/services/lesson_service.py`
  (new), `app/data/lesson_fixtures.py` (new), `app/schemas/{lesson,deck}.py`
  (additive), `app/main.py` (additive), `tests/...` paths touched.
- **AC-13** — Test suite stays green. New tests run under default
  `not integration` selector for BE; new FE tests run under default
  `npx vitest run`.

## 12. Decisions

> Phase-level decisions referenced here use the IDs from this slice's
> front-matter (G2, H1, I1). Slice-local decisions use D-1..D-8 from
> the prompt; slice-author additions get D-9+.

### Slice-local decisions

- **D-1 — FE-first slice.** Lesson page + components ship as the
  primary deliverable; BE returns fixture data only. Rationale:
  surfaces the lesson UX for design + product validation BEFORE
  slice 6.4 introduces DB persistence; lets slice 6.4 swap loader
  → DB without UX rework; matches the "scaffolding-first" pattern
  used in Phase 5 (e.g. paywall scaffolding shipped before the gate
  service that populated it).
- **D-2 — Fixture data location = `app/data/lesson_fixtures.py`
  (Python file exporting Pydantic instances).** Rationale: typed
  import (schema drift fails at import time, not request time); no
  parse step; deletes cleanly when slice 6.4 ships authoring (single
  file removal + loader-call swap). NOT JSON / Markdown-with-frontmatter
  because both add a parse layer that 6.4 retirement would drop, and
  the seed-content path (slice 6.4.5) at `app/data/decks/seed_lessons/*.md`
  is a different artifact governed by H1.
- **D-3 — Markdown rendering = `react-markdown` + `remark-gfm`.**
  No `dangerouslySetInnerHTML`. **Drift recorded:** `react-markdown@^10.1.0`
  is already in `package.json` (consumed by `src/components/rewrite/ResumeEditor.tsx`).
  Only `remark-gfm` is net-new. Implementation slice's commit message
  must say "adds remark-gfm" (singular) rather than "adds
  react-markdown + remark-gfm" so CODEX doesn't flag a phantom
  dependency. Default sanitization sufficient for this slice (content
  is fixture-authored, hence trusted) — security review revisited
  pre-slice-6.4 admin-authored content per OQ-1.
- **D-4 — BE routes return fixture data; no DB persistence in this
  slice.** Read-only endpoints only. Slice 6.4 swaps the
  `lesson_service` body from fixture-loader call to DB query without
  changing the route surface or response shape. The `db: AsyncSession
  = Depends(get_db)` parameter on the service signatures is a
  forward-compat affordance — slice 6.3 ignores it; slice 6.4 uses
  it.
- **D-5 — Quiz submission goes through slice 6.2 endpoint
  `POST /api/v1/quiz-items/review`.** No new submit path. Rationale:
  slice 6.2 already shipped that endpoint with FSRS scheduling +
  retired-quiz / archived-lesson guards; duplicating would create
  two independent "what counts as a review" code paths.
- **D-6 — No persona-aware ranking, no daily-flow integration.**
  Lesson page renders the lesson it's given; no "next lesson"
  recommendation. Daily review is per-quiz_item per slice 6.2;
  per-lesson daily flow would conflict with the FSRS-binds-to-quiz_item-only
  invariant from slice 6.1. Slice 6.6 + 6.7 own ranking +
  composition.
- **D-7 — Component naming.** New file
  `components/lesson/QuizItemPanel.tsx` (NOT a rename of
  `components/study/QuizPanel.tsx`). Rationale: legacy card flow
  (`/learn/daily`, `/learn/card/:id`, `/learn/mission`) keeps
  `QuizPanel`; rename would require touching three pages outside
  this slice's scope. Slice 6.15 cleanup deletes `QuizPanel.tsx`
  when the legacy card flow retires.
- **D-8 — Page file `pages/Lesson.tsx`. Route at `/learn/lesson/:id`.**
  Inside the existing `/learn/*` block. Wrapped in `<ProtectedRoute>`
  (which composes `<PersonaGate>`) per `App.tsx:78-90` precedent.
  Not lazy-loaded in v0 — match `CardViewer.tsx` precedent
  (eager-loaded inside the same `/learn/*` block). If the bundle
  cost of `react-markdown` + `remark-gfm` measurably hurts initial
  paint, switch to lazy-load via `lazy(() => import('@/pages/Lesson'))`
  in a follow-up slice.

### Slice-author additions

- **D-9 — Fixture file is per-instance Python, NOT JSON or
  fixture-factory.** Sub-clarification of D-2. Why not JSON: lacks
  type checks at import. Why not fixture-factory pattern (`make_lesson(
  title=..., quiz_items=[make_quiz(...)])`): factories add an
  abstraction layer that retires in 6.4 too — single-file
  per-instance Pydantic constructions are simpler.
- **D-10 — Lesson page eagerly loaded via static import in
  `App.tsx`.** Sub-clarification of D-8. Performance check deferred
  to post-impl; lazy-load is a one-line change behind `lazy()` if
  needed.

## 13. Out of scope (explicit list per the prompt)

- DB persistence of lessons / decks — slice 6.4.
- Admin authoring UI (`/admin/lessons`, `/admin/decks`) — slice 6.4.
- New quiz-submit endpoint — slice 6.2 endpoint reused (D-5).
- Persona-aware ranking — slice 6.6.
- Daily-flow integration / per-lesson daily queue — out of phase
  6 scope (FSRS binds to quiz_item only).
- Code-fence syntax highlighting — OQ-2; defer.
- Lesson-list deck navigation chrome (sidebar / prev-next /
  breadcrumb) — slice 6.7.
- DB schema changes — slice 6.1 already covers; N7 STOP.
- Gamification / XP / streak on lesson view — out (slice 6.2 D-7
  already covers quiz review).
- Free-tier wall on lesson detail reads — slice 6.7 list-level filter.
- Server-side rendering of Markdown — react-markdown is client-side.
- Touching `QuizPanel.tsx` (legacy card flow) — D-7.

## 14. Open questions

> Questions the schema design surfaced but does NOT block this spec.
> Resolve in the implementation slice's pre-flight or in a follow-up.

- **OQ-1 — Markdown rendering security.** `react-markdown` defaults
  do NOT execute embedded HTML, but inline `<script>` / `<iframe>` /
  `javascript:` URL contents could still surface visually if a
  malicious lesson author wrote them. For slice 6.3 (fixture-authored,
  trusted content) defaults are sufficient. Question: should the
  implementation slice add `rehype-sanitize` proactively, or defer
  until slice 6.4 admin-authored content lands and revisit then?
  Recommendation: defer (one extra dep, no measurable risk in the
  fixture window) and re-audit at slice 6.4 spec time.
- **OQ-2 — Code-fence syntax highlighting.** Plain fenced-code
  rendering (`<pre><code>`) ships in 6.3. Syntax highlighting
  (Prism, Shiki, refractor) adds 50-200kb to the bundle. Question:
  ship plain in 6.3, plan a follow-up; or pull `prism-react-renderer`
  / `react-syntax-highlighter` in now? Recommendation: defer to a
  dedicated bundle-size-aware slice; don't bundle into 6.3.
- **OQ-3 — Mobile-first vs desktop-first responsive layout.** The
  four-section layout (concept / production / examples / quiz) at
  ≥768px is likely two columns (concept+production / examples+quiz);
  at <768px it's a vertical stack with collapse-by-default sections
  (concept expanded, others collapsed) so the page fits a phone fold.
  Question: which behavior is canonical for v0? `lesson_section_expanded`
  event (§9) only fires if collapse-by-default is the canonical
  mobile UX — if the v0 is "always expanded, scroll the page" then
  the event is dead-on-arrival. Recommendation: spec the canonical
  layout in the implementation slice's Step 1 audit; don't pre-resolve
  here.
- **OQ-4 — Quiz scoring display.** `QuizReviewResponse` returns FSRS
  state post-review (`fsrs_state, stability, difficulty, due_date,
  reps, lapses, scheduled_days`). It does NOT include a binary
  correct/incorrect verdict — FSRS is a self-rated scheduler, not a
  scorer. Question: does the lesson page surface the FSRS schedule
  ("review again in 2 days") inline, in a modal, on the next quiz
  item, or only at end-of-session? Recommendation: inline below the
  question, mirroring `QuizPanel`'s done state (audit §1.4
  `QuizPanel.tsx`).
- **OQ-5 — Inter-lesson navigation in v0.** No prev/next, no
  sidebar, no "back to deck" breadcrumb in v0 (D-6 → slice 6.7
  composes the deck list). Question: confirm v0 ships with **no**
  inter-lesson navigation chrome — users return via `AppShell`
  TopNav `Learn` link. Recommendation: confirm; surface in CODEX
  review.
- **OQ-6 — Empty / error states for fixture data.** What displays
  when `lesson_id` doesn't match a fixture? 404 BE → empty state in
  FE. Question: copy text? "This lesson doesn't exist yet." vs
  "Lesson not found." vs full-page upsell. Recommendation: minimal
  empty state ("Lesson not found.") + a "Back to Learn" button —
  bigger upsell can land in slice 6.7 once the deck-list surface
  exists.

---

*End of slice 6.3 spec. Authored 2026-04-27 at HEAD `a02639c`. Spec
basis: `docs/specs/phase-6/01-foundation-schema.md` +
`docs/specs/phase-6/02-fsrs-quiz-item-binding.md` +
`docs/audits/phase-6-scout.md` (commit `5b0aa23`). Next step: Mode 1
implementation slice executes against this spec — files B-063 at
execution time per R17.*
