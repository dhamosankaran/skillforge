# Phase 6 — Slice 6.0: Analytics Tables Foundation (`quiz_review_events`, `lesson_view_events`)

## Status: Drafted, not shipped — §12 D-1..D-10 locked at amendment `<this-slice>` (OQ-1..OQ-4 closed; see §14 RESOLVED markers)

| Field | Value |
|-------|-------|
| Phase | 6 (Curriculum Platform) |
| Slice | 6.0 — analytics tables foundation |
| Mode | 4 (spec-author) |
| Author HEAD | `045e012` (post-slice-6.4b-3 SHA backfill) |
| Spec authored | 2026-04-27 |
| Implementation slice | TBD (one-step follow-up to this spec). Will file `B-069` close-line. |
| BACKLOG row | `B-069` filed at status 🔴 by this spec slice for the future implementation slice (per R15(c) + R17). |
| Audit dependency | `docs/audits/phase-6-scout.md` §6.3 (internal analytics tables in PG) + slice-by-slice 6.0 entry + R-3 + Q2. |
| Slice dependencies | **Upstream:** slice 6.1 (FK targets `quiz_items.id` + `lessons.id` + `decks.id` + `users.id` must exist — shipped at `a989539`); slice 6.2 (`quiz_item_reviewed` PostHog emission point — shipped at `7b654fb`); slice 6.3 (`lesson_viewed` FE PostHog emission — shipped at `ba00331`). **Downstream:** slice 6.13 / 6.13.5 (content-quality dashboards), slice 6.16 (FSRS retention dashboard). |

### Phase 6 locked decisions referenced by this spec

> Recorded in front-matter so spec readers see the locks without
> chasing SESSION-STATE. Rationale lives in §12 (Decisions).

| ID | Decision |
|----|----------|
| **I1** | Events: **dual-write**. PostHog stays for funnels/retention; Postgres `quiz_review_events` + `lesson_view_events` power the SQL-queryable content-quality / retention dashboards (spec #38 banned HogQL in `/admin/analytics`). **This spec defines those two tables, the write path, and the Pydantic write schemas.** |
| **J2** | `card_quality_signals` is keyed on `(id, lesson_id, quiz_item_id NULLABLE, signal_source, dimension)` and lives in slice 6.13.5. **Out of scope here** — flagged so spec readers don't conflate quality signals (admin spot-check / AI critique / user thumbs feedback) with raw event capture. |

---

## 1. Problem

Phase 6's content-quality dashboards (slice 6.13 / 6.13.5) and FSRS
retention dashboard (slice 6.16) need a SQL-queryable event source.
Spec #38 (admin analytics) banned the PostHog Query API / HogQL inside
`/admin/analytics`, citing latency + cost + the dependency on a
third-party service for what is fundamentally a Postgres aggregation
problem. Per locked decision **I1**, every Phase 6 review/view event
**dual-writes** to PostHog (funnels, retention, product analytics) AND
to a Postgres event table (admin dashboards, retention SQL).

Today, the two relevant emissions are:

| Event | Tier | Site | Payload (current) |
|-------|------|------|--------------------|
| `quiz_item_reviewed` | BE | `app/services/quiz_item_study_service.py:438-451` (after `_apply_fsrs_result_to_quiz_item`, post-`db.flush()`, end of successful `review_quiz_item`) | `{quiz_item_id, lesson_id, deck_id, plan, persona, rating, fsrs_state_before, fsrs_state_after, reps, lapses, time_spent_ms, session_id}` + `user_id` first arg |
| `quiz_item_progress_initialized` | BE | `app/services/quiz_item_study_service.py:431-436` (same site, branch on `is_first_review=True`) | `{quiz_item_id, lesson_id, deck_id, plan, persona}` + `user_id` first arg |
| `lesson_viewed` | **FE** | `hirelens-frontend/src/pages/Lesson.tsx:37` (idempotent `useEffect`, `useRef` guard) | `{lesson_id, deck_id, deck_slug, version, persona, plan}` |
| `lesson_section_expanded` | **FE** | `hirelens-frontend/src/components/lesson/LessonRenderer.tsx:43` (per-section toggle, on-expand only) | `{lesson_id, section}` |

Two of these are BE-emitted (and trivially dual-writable from the same
service-layer site); two are **FE-only** today. The FE-only emission
path means slice 6.0's lesson view dual-write requires a new BE write
route — `POST /api/v1/lessons/:id/view-event` — that the FE calls
alongside its existing PostHog `capture()`. See §6 + §12 D-4 + §12 D-10
for the locked pattern (path (a) — confirmed at amendment
`<this-slice>`).

This spec defines the two events tables (`quiz_review_events`,
`lesson_view_events`) at column granularity, the new
`analytics_event_service` that owns the Postgres-side write, the
service-layer hook in `quiz_item_study_service.py`, and the new
read-receiving BE route + FE caller for `lesson_view_events`. It does
**not** define query routes, admin dashboards, retention/TTL,
`card_quality_signals`, the `lesson_section_expanded` table, or any FE
display surface — those belong to downstream slices.

## 2. Goals

1. Lock the two events tables (`quiz_review_events`,
   `lesson_view_events`) at column granularity, mirroring the existing
   PostHog payloads field-for-field (§4).
2. Lock the `analytics_event_service` write API + the dual-write
   pattern at the existing `quiz_item_reviewed` emission site (§6.1)
   and at a new `lesson_view_events` emission path (§6.2).
3. Lock the FK `ON DELETE` semantics per row: `SET NULL` on
   `user_id` (preserve event row for analytics if user deletes
   account, anonymize the user link); `CASCADE` on
   `quiz_item_id` / `lesson_id` / `deck_id` (if the content is
   gone, the analytical value is gone too).
4. Lock the **append-only** invariant: tables are INSERT-only at
   runtime; no UPDATE, no DELETE except via a future retention slice.
5. Declare zero new PostHog events. Slice 6.0 reuses
   `quiz_item_reviewed` (BE) and `lesson_viewed` (FE) verbatim; the
   delta is the Postgres write path, not the wire emission.

## 3. Non-goals

- **Query routes** — no `GET /api/v1/admin/analytics/quiz-reviews`,
  no aggregated reads. Slice 6.13 / 6.13.5 / 6.16 spec resolves.
- **Admin dashboards** — no FE surface that consumes these tables.
  Slice 6.16 spec resolves.
- **`card_quality_signals` table** — slice 6.13.5 spec resolves
  (J2 lock).
- **Retention / TTL policy** — these tables grow unbounded by design
  this slice; a future slice locks retention. See **§14 OQ-3**.
- **`lesson_section_expanded` event capture in Postgres** — FE-only
  for now. If slice 6.13 / 6.16 wants section-level engagement
  signals in SQL, a separate `lesson_section_event` table is its
  spec to author. This slice does **not** dual-write
  `lesson_section_expanded`.
- **Event-replay backfill of historical PostHog data** — these
  tables start empty at impl-merge. Historical PostHog events stay
  in PostHog; the dashboards that consume them either accept the
  cutover boundary or query PostHog directly for pre-cutover periods.
- **PostHog Query API / HogQL integration** — explicitly banned per
  spec #38. Postgres is the SQL-queryable source.
- **FE consumer surface for the new `POST /lessons/:id/view-event`
  route** — limited to a single best-effort `services/api.ts` helper
  + a single call site. No loading state, no error surface, no UI
  change.
- **New PostHog events** — zero this slice.
- **Alembic migration code, model file contents, route handler code,
  service file code, test code** — implementation slice's
  deliverables. This spec lists shapes, not lines.

## 4. Schema definitions

> Conventions follow slice 6.1's spec §4 + on-disk migration
> `57951e9f4cdc_phase6_foundation_schema.py`:
> - PK columns are `String(36)` (UUID stored as string).
> - FK columns are `String(length=36)`, named `<table>_id`.
> - Timestamp columns are `DateTime(timezone=True)` with
>   `server_default=func.now()` for the event-time column.
> - JSONB columns via `postgresql.JSONB(astext_type=Text())` (none
>   needed in this slice — both tables ship as flat columns).
> - Indexes on hot read paths use partial-index syntax via
>   `postgresql_where` only when the table itself can be soft-deleted.
>   Append-only event tables have no soft-delete branch, so indexes
>   are full-table.

### 4.1 Table 1 — `quiz_review_events`

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | `String(36)` | NOT NULL | (server-generated UUID) | PK. |
| `user_id` | `String(36)` | NULL | — | FK `users.id` `ON DELETE SET NULL` (D-1). NULL = user deleted account post-event. |
| `quiz_item_id` | `String(36)` | NOT NULL | — | FK `quiz_items.id` `ON DELETE CASCADE`. If quiz_item deleted, events lose meaning. |
| `lesson_id` | `String(36)` | NOT NULL | — | FK `lessons.id` `ON DELETE CASCADE`. **Denormalized** from `quiz_items.lesson_id` per D-2 + OQ-2 hint. |
| `deck_id` | `String(36)` | NOT NULL | — | FK `decks.id` `ON DELETE CASCADE`. **Denormalized** from `lessons.deck_id` per D-2 + OQ-2 hint. |
| `rating` | `Integer` | NOT NULL | — | py-fsrs `Rating` enum: `1=Again`, `2=Hard`, `3=Good`, `4=Easy`. Mirrors PostHog payload. |
| `fsrs_state_before` | `String(20)` | NOT NULL | — | One of `new` / `learning` / `review` / `relearning`. From `_state_before` in `quiz_item_study_service.py:486-496`. |
| `fsrs_state_after` | `String(20)` | NOT NULL | — | Same vocab; from `progress.state` post-`_apply_fsrs_result_to_quiz_item`. |
| `reps` | `Integer` | NOT NULL | — | Post-review reps count. |
| `lapses` | `Integer` | NOT NULL | — | Post-review lapses count. |
| `time_spent_ms` | `Integer` | NOT NULL | `0` | Client-supplied dwell time. Mirrors PostHog payload + `review_quiz_item(..., time_spent_ms: int = 0, ...)` signature. |
| `session_id` | `String(64)` | NULL | — | Client-supplied per-page-mount UUID (FE generates via `crypto.randomUUID`, e.g. `pages/Lesson.tsx:18-24`). NULL allowed because slice 6.2 `QuizReviewRequest` makes it Optional. |
| `plan` | `String(20)` | NULL | — | One of `free` / `pro` / `enterprise` / NULL. NULL when `_resolve_plan` returns None (subscription not eagerly loaded — service-test path). Mirrors PostHog payload. |
| `persona` | `String(30)` | NULL | — | One of `interview_prepper` / `career_climber` / `team_lead` / NULL (persona-not-set). |
| `reviewed_at` | `DateTime(tz=True)` | NOT NULL | `func.now()` | Event time. Server-side `now()` matches the `now` variable used inside `review_quiz_item` for FSRS scheduling. |

**Indexes:**

| Name | Columns | Use |
|------|---------|-----|
| `ix_quiz_review_events_user_reviewed_at` | `(user_id, reviewed_at DESC)` | Per-user retention queries (slice 6.16: "your review history", "your recent lapses"). |
| `ix_quiz_review_events_quiz_item_reviewed_at` | `(quiz_item_id, reviewed_at DESC)` | Per-quiz-item content-quality queries (slice 6.13.5: "how is this quiz_item performing"). |
| `ix_quiz_review_events_lesson_reviewed_at` | `(lesson_id, reviewed_at DESC)` | Per-lesson rollups (slice 6.13.5: "which lessons have the worst recall"). |
| `ix_quiz_review_events_deck_reviewed_at` | `(deck_id, reviewed_at DESC)` | Per-deck rollups (slice 6.16: "deck-level retention curve"). |

No UNIQUE constraint — a single user can review a single quiz_item
multiple times in a single session, and each review is a row.

### 4.2 Table 2 — `lesson_view_events`

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | `String(36)` | NOT NULL | (server-generated UUID) | PK. |
| `user_id` | `String(36)` | NULL | — | FK `users.id` `ON DELETE SET NULL` (D-1). |
| `lesson_id` | `String(36)` | NOT NULL | — | FK `lessons.id` `ON DELETE CASCADE`. |
| `deck_id` | `String(36)` | NOT NULL | — | FK `decks.id` `ON DELETE CASCADE`. **Denormalized** from `lessons.deck_id` per D-2. |
| `version` | `Integer` | NOT NULL | — | `lessons.version` at view time — locks the lesson body the user actually saw, since substantive edits bump version (slice 6.4 D-17 cascade). |
| `session_id` | `String(64)` | NULL | — | FE-generated per-page-mount UUID (`pages/Lesson.tsx:18-24`). |
| `plan` | `String(20)` | NULL | — | Same vocab as §4.1. |
| `persona` | `String(30)` | NULL | — | Same vocab as §4.1. |
| `viewed_at` | `DateTime(tz=True)` | NOT NULL | `func.now()` | Event time. |

**Indexes:**

| Name | Columns | Use |
|------|---------|-----|
| `ix_lesson_view_events_user_viewed_at` | `(user_id, viewed_at DESC)` | Per-user view history (slice 6.16). |
| `ix_lesson_view_events_lesson_viewed_at` | `(lesson_id, viewed_at DESC)` | Per-lesson view-volume rollups (slice 6.13.5). |
| `ix_lesson_view_events_deck_viewed_at` | `(deck_id, viewed_at DESC)` | Per-deck rollups (slice 6.16). |

**Columns explicitly NOT shipped this slice (with rationale):**

- `dwell_time_ms` — FE doesn't measure or emit dwell time today.
  Adding the column would force the FE to instrument a
  `beforeunload` / route-change measurement, which is its own design
  surface. Defer to a future slice if a dashboard needs it.
- `sections_expanded` (JSONB array) — `lesson_section_expanded` is a
  separate event with a separate table-or-not OQ. Deferred per §3.
- `deck_slug` — present in the FE PostHog payload for funnel
  readability, but redundant with `deck_id` for SQL queries (joinable
  via `decks.slug`). Skip; storage discipline.

### 4.3 FK `ON DELETE` semantics

| Column | Behavior | Reasoning |
|--------|----------|-----------|
| `quiz_review_events.user_id` | `SET NULL` | Anonymize: a user deleting their account should not erase aggregate retention data. The remaining columns (deck/lesson/quiz_item/rating/state/timing) stay queryable for content-quality dashboards. |
| `quiz_review_events.quiz_item_id` | `CASCADE` | If a quiz_item is hard-deleted (rare — slice 6.4 uses soft-retire), the events lose anchor. Aggregate-level retention dashboards key on `lesson_id` / `deck_id` which still exist on this row. |
| `quiz_review_events.lesson_id` | `CASCADE` | Same as quiz_item — hard-delete means the analytical anchor is gone. |
| `quiz_review_events.deck_id` | `CASCADE` | Decks soft-archive (slice 6.4); hard-delete is rare. |
| `lesson_view_events.user_id` | `SET NULL` | Same anonymization principle. |
| `lesson_view_events.lesson_id` | `CASCADE` | Same as above. |
| `lesson_view_events.deck_id` | `CASCADE` | Same as above. |

In practice, slice 6.4's admin authoring path uses **soft-delete** on
decks (`archived_at`) and lessons (`archived_at`) and **soft-retire**
on quiz_items (`retired_at`). Hard-delete only happens via
direct-DB intervention or test cleanup. The CASCADE behavior above is
the safety net for those exceptional paths.

### 4.4 Append-only invariant

These tables are **INSERT-only at runtime**. Concretely:

- `analytics_event_service.write_quiz_review_event` is the **only**
  service that writes to `quiz_review_events` in app code. There is
  no UPDATE path, no DELETE path, no admin-facing edit surface.
- Same for `analytics_event_service.write_lesson_view_event` and
  `lesson_view_events`.
- Tests that need to clear rows between test cases use `TRUNCATE` /
  the conftest fixture's per-test rollback, not a service method.
- A future retention slice (see §14 OQ-3) will add a periodic
  DELETE-WHERE-`reviewed_at < cutoff` job, but that operates outside
  the request path.

This invariant is structural (no service method exposes
UPDATE/DELETE) rather than enforced by a Postgres-side trigger or
RULE. Keeps the migration simple.

## 5. Pydantic schemas

Slice 6.0 ships **two write-only schemas** in a new file
`app/schemas/analytics_event.py`. No read schemas — there is no API
consumer surface this slice.

### 5.1 `QuizReviewEventCreate`

```python
class QuizReviewEventCreate(BaseModel):
    user_id: Optional[str]
    quiz_item_id: str
    lesson_id: str
    deck_id: str
    rating: int                              # 1..4 (py-fsrs Rating)
    fsrs_state_before: Literal["new", "learning", "review", "relearning"]
    fsrs_state_after: Literal["new", "learning", "review", "relearning"]
    reps: int
    lapses: int
    time_spent_ms: int = 0
    session_id: Optional[str] = None
    plan: Optional[Literal["free", "pro", "enterprise"]] = None
    persona: Optional[Literal["interview_prepper", "career_climber", "team_lead"]] = None
```

### 5.2 `LessonViewEventCreate`

```python
class LessonViewEventCreate(BaseModel):
    user_id: Optional[str]
    lesson_id: str
    deck_id: str
    version: int
    session_id: Optional[str] = None
    plan: Optional[Literal["free", "pro", "enterprise"]] = None
    persona: Optional[Literal["interview_prepper", "career_climber", "team_lead"]] = None
```

`reviewed_at` / `viewed_at` are server-set (`func.now()`); not part
of the write schema.

A separate **request schema** for the new `POST
/api/v1/lessons/:id/view-event` route is needed since the route can't
trust client-supplied `user_id` / `plan` / `persona`:

### 5.3 `LessonViewEventRequest` (route input)

```python
class LessonViewEventRequest(BaseModel):
    deck_id: str
    version: int
    session_id: Optional[str] = None
```

The route resolves `user_id` from `Depends(get_current_user)`, derives
`plan` via `_resolve_plan(user)` (mirrors `quiz_item_study_service`'s
helper), and reads `persona` from `user.persona`. Path param supplies
`lesson_id`. **Server-derived fields are not client-trusted.**

## 6. Service-layer dual-write hooks

Slice 6.0 introduces one new service module and modifies one existing
service.

### 6.1 New service — `app/services/analytics_event_service.py`

Two `async def` functions encapsulate the Postgres-side write:

```python
async def write_quiz_review_event(
    payload: QuizReviewEventCreate,
    db: AsyncSession,
) -> None: ...

async def write_lesson_view_event(
    payload: LessonViewEventCreate,
    db: AsyncSession,
) -> None: ...
```

Behavior:

- Each function inserts exactly one row into the corresponding
  table, server-generates `id` (UUID4), and lets the DB set
  `reviewed_at` / `viewed_at` via `server_default`.
- Each function calls `await db.flush()` (NOT `commit` — the caller
  owns the transaction).
- **Failure semantics:** see §14 OQ-1. Author hint locked at impl
  time; the spec records the surfaces involved without pre-locking.
- No return value (write-only path; no read needed).

Why a new service rather than inline writes inside
`quiz_item_study_service` / a new `lesson_view_routes.py`:

- Keeps the dual-write pattern in **one** place. Slice 6.13 / 6.13.5
  / 6.16 will add their own dual-write callers; routing them through
  this service keeps the failure-semantics policy in one location.
- Mirrors the slice 6.4 pattern of grouping admin-CRUD service
  helpers (`deck_admin_service`, `lesson_admin_service`,
  `quiz_item_admin_service`) — separation by concern, not by table.
- Trivial to mock in service-layer unit tests.

### 6.2 Modify — `app/services/quiz_item_study_service.py`

Inside `review_quiz_item` (currently lines 324-462), at the existing
PostHog emission site (lines 438-451), add a dual-write call:

```python
# Existing PostHog emission stays verbatim:
analytics_track(user_id=user_id, event="quiz_item_reviewed", properties={...})

# NEW dual-write (per I1 + slice 6.0 §6.2):
await analytics_event_service.write_quiz_review_event(
    QuizReviewEventCreate(
        user_id=user_id,
        quiz_item_id=quiz_item_id,
        lesson_id=lesson.id,
        deck_id=deck.id,
        rating=rating,
        fsrs_state_before=("new" if is_first_review else _state_before(progress, fsrs_card)),
        fsrs_state_after=progress.state,
        reps=progress.reps,
        lapses=progress.lapses,
        time_spent_ms=time_spent_ms,
        session_id=session_id,
        plan=plan,
        persona=persona,
    ),
    db=db,
)
```

Order matters: PostHog emission stays first (preserves existing
behavior for tests that mock `analytics_track`); Postgres write
follows. Failure-mode handling per §14 OQ-1 wraps both calls.

`quiz_item_progress_initialized` is **not** dual-written this slice.
Rationale: slice 6.16's first-touch retention metric can be derived
from the **first** `quiz_review_events` row per `(user_id,
quiz_item_id)` (via `MIN(reviewed_at) GROUP BY user_id, quiz_item_id`).
Dual-writing the init event would denormalize a derivable signal.

### 6.3 New BE route — `POST /api/v1/lessons/:lesson_id/view-event`

Lives in a new file `app/api/v1/routes/lesson_view_events.py`
(separate from the existing `lessons.py` which is read-only and
slice-6.3-shipped, to keep the file's intent clean — read vs write).

Route shape:

```
POST /api/v1/lessons/{lesson_id}/view-event
Auth: Depends(get_current_user)
Body: LessonViewEventRequest
Returns: 204 No Content (no body — fire-and-forget from the FE)
Errors: 401 unauthenticated; 404 lesson not found.
```

Implementation:
- Validate `lesson_id` (404 if not found).
- Optional sanity check that `body.deck_id == lesson.deck_id`
  (422 mismatch). Defensive — drift surfaces early.
- Construct `LessonViewEventCreate` with server-derived `user_id` /
  `plan` / `persona`.
- Call `analytics_event_service.write_lesson_view_event(payload, db)`.
- Return 204.

This route is the **BE half of the FE-emitted `lesson_viewed`
dual-write**. The existing FE PostHog `capture('lesson_viewed', ...)`
at `pages/Lesson.tsx:37` stays verbatim. See §14 OQ-4 for why this is
a real architectural call — the alternative ("move emission entirely
to BE; drop FE PostHog capture") was considered and rejected.

### 6.4 FE caller — `pages/Lesson.tsx` `useEffect`

The FE adds one new helper in `services/api.ts`:

```typescript
async function recordLessonView(
  lessonId: string,
  body: { deck_id: string; version: number; session_id: string }
): Promise<void>
```

Returns `void` on success, swallows errors silently (best-effort —
Postgres analytics fire-and-forget is the same posture as the FE
PostHog capture itself). The existing `useEffect` at `Lesson.tsx:34`
is amended:

```typescript
useEffect(() => {
  if (lesson && !hasFiredViewed.current) {
    hasFiredViewed.current = true
    capture('lesson_viewed', { /* unchanged */ })
    recordLessonView(lesson.lesson.id, {
      deck_id: lesson.deck_id,
      version: lesson.lesson.version,
      session_id: sessionId,
    }).catch(() => { /* best-effort: see OQ-1 */ })
  }
}, [lesson, user?.persona, usage.plan])
```

No loading state, no error UI. Failure is silent.

## 7. Alembic migration

Single migration file:
`alembic/versions/<HASH>_phase6_analytics_tables.py`.

- `revision`: server-generated by `alembic revision --autogenerate
  -m "phase6 analytics tables"`.
- `down_revision`: current Alembic head at impl time. **Do NOT
  hardcode in this spec** — verify via `alembic current` at impl
  start. The current head as of slice-6.4b-3 close (`78abe56`) is
  whatever slice 6.4b-1's BE schema work didn't touch (slice 6.4b-1
  shipped no new migration — it only added admin routes/services
  against the existing slice-6.1 schema), so the head should still be
  `57951e9f4cdc` (slice 6.1's foundation schema migration). Confirm.
- `upgrade()`: `op.create_table` for both tables in FK-ordered
  dependency safety (FKs target `users` / `decks` / `lessons` /
  `quiz_items` which all pre-exist), then `op.create_index` for the
  7 indexes (4 on `quiz_review_events`, 3 on `lesson_view_events`).
- `downgrade()`: drop indexes, then drop tables, in reverse FK order.
- Migration body follows slice 6.1's
  `57951e9f4cdc_phase6_foundation_schema.py` conventions verbatim
  (`String(length=36)` for FK columns, `DateTime(timezone=True)` with
  `server_default=sa.func.now()`, named constraints).

## 8. FE component graph

| File | Touch | Purpose |
|------|-------|---------|
| `hirelens-frontend/src/pages/Lesson.tsx` | **modify** | Add `recordLessonView()` call in existing `lesson_viewed` `useEffect`. Best-effort — `.catch(() => {})`. |
| `hirelens-frontend/src/services/api.ts` | **modify** | Add `recordLessonView(lessonId, body)` helper. Mirrors existing API helper patterns (auth header, fetch wrapper, JSON body). |

No new pages, no new components, no new hooks. The dual-write FE
surface is a single `useEffect` line + a single `services/api.ts`
helper.

`QuizPanel.tsx` / `quiz_item_study_service` review path is
**BE-emitted**; FE-side change for the quiz-review dual-write is
**zero**.

## 9. Analytics events declared by this slice

**Zero new PostHog events.** The dual-write reuses two existing
events verbatim:

| Event | Tier (existing) | New action this slice |
|-------|-----------------|------------------------|
| `quiz_item_reviewed` | BE (slice 6.2, `quiz_item_study_service.py:438`) | Add Postgres dual-write at the same site. PostHog payload unchanged. |
| `lesson_viewed` | FE (slice 6.3, `pages/Lesson.tsx:37`) | Add FE call to new BE route `POST /api/v1/lessons/:id/view-event`, which writes to Postgres. PostHog `capture()` payload unchanged. |

`quiz_item_progress_initialized` is not dual-written (see §6.2).
`lesson_section_expanded` is not dual-written (see §3 + §4.2 dwell
exclusion + future-slice scope).

`.agent/skills/analytics.md` requires no edits this slice — no
events added or renamed.

## 10. Test plan (implementation slice)

> This spec lists tests the implementation slice will add. No test
> code is written in this spec slice.

Expected test count delta: **+18 to +22 BE, +1 to +2 FE.**

### 10.1 Backend — schema tests in `tests/test_phase6_analytics_schema.py`

(~5 tests, mirrors `tests/test_phase6_schema.py` pattern)

- `test_quiz_review_events_table_shape` — column types, defaults,
  indexes (4), FK ON DELETE SET NULL on user_id, CASCADE on the
  other three.
- `test_lesson_view_events_table_shape` — column types, defaults,
  indexes (3), FK ON DELETE shapes per §4.3.
- `test_alembic_round_trip_analytics_tables` — `upgrade head →
  downgrade -1 → upgrade head` leaves schema identical.
- `test_quiz_review_events_appendonly_invariant` — service
  `analytics_event_service` exposes only `write_*`, no
  `update_*` / `delete_*` / `archive_*`. Verified via
  `inspect.getmembers` on the module.
- `test_quiz_review_events_no_unique_constraint` — assert no UNIQUE
  on `(user_id, quiz_item_id)` (multiple reviews per session must be
  permitted). Defensive against a future authoring mistake.

### 10.2 Backend — dual-write integration tests

`tests/test_quiz_item_study_service_dual_write.py` (~5 tests):

- `test_review_quiz_item_writes_quiz_review_events_row` — call
  `review_quiz_item`, assert one row in `quiz_review_events` with
  expected payload.
- `test_review_quiz_item_writes_correct_state_transitions` — first
  review: `fsrs_state_before='new'`, `fsrs_state_after='learning'`;
  subsequent review: state transitions match
  `_apply_fsrs_result_to_quiz_item` output.
- `test_review_quiz_item_denormalizes_lesson_and_deck_id` — assert
  written row's `lesson_id` matches `quiz_item.lesson_id` and
  `deck_id` matches `lesson.deck_id`.
- `test_review_quiz_item_still_fires_posthog` — assert PostHog
  `analytics_track` called once with `event="quiz_item_reviewed"`
  AND Postgres write occurred (both legs of dual-write fire).
- `test_review_quiz_item_postgres_failure_does_not_break_request` —
  verify dual-write failure handling per locked OQ-1. Test shape
  TBD at impl time once OQ-1 is locked.

### 10.3 Backend — `analytics_event_service` unit tests

`tests/test_analytics_event_service.py` (~4 tests):

- `test_write_quiz_review_event_inserts_row` — happy path.
- `test_write_lesson_view_event_inserts_row` — happy path.
- `test_write_quiz_review_event_handles_null_user_id` — anonymized
  write (post-account-deletion replay scenario).
- `test_write_quiz_review_event_handles_null_plan_persona` —
  service-test path (subscription not eagerly loaded).

### 10.4 Backend — lesson view route

`tests/test_lesson_view_route.py` (~4 tests):

- `test_post_lesson_view_event_204` — happy path, verifies row in
  `lesson_view_events`.
- `test_post_lesson_view_event_404_unknown_lesson` — bad path.
- `test_post_lesson_view_event_401_unauthenticated` — auth gate
  (R3-rule).
- `test_post_lesson_view_event_422_deck_id_mismatch` — defensive
  drift check.

### 10.5 Frontend — `recordLessonView` helper

`tests/services/api.test.ts` or co-located (~1-2 tests):

- `test_recordLessonView_posts_to_correct_url` — fetch mock asserts
  URL + method + body shape.
- `test_recordLessonView_swallows_errors` — assert no throw on
  network error.

No FE component test for `Lesson.tsx` is required — the existing
`tests/pages/Lesson.test.tsx` (slice 6.3) only asserts the lesson
renders + the `lesson_viewed` PostHog capture fires. Adding a mock
for `recordLessonView` is a one-line addition to the existing test;
no new test file.

## 11. Acceptance criteria

The implementation slice (one-step follow-up) must pass:

- **AC-1** — Alembic `upgrade head → downgrade -1 → upgrade head`
  cleanly. Per `db-migration.md` rule 2.
- **AC-2** — Both tables exist on disk with the columns,
  constraints, indexes, and defaults specified in §4.1 and §4.2.
  Verified by `test_quiz_review_events_table_shape` +
  `test_lesson_view_events_table_shape`.
- **AC-3** — Calling `quiz_item_study_service.review_quiz_item(...)`
  with a successful FSRS review writes exactly **one** row to
  `quiz_review_events` AND fires the existing PostHog
  `quiz_item_reviewed` event (both legs of dual-write fire).
- **AC-4** — Calling `POST /api/v1/lessons/:id/view-event` with
  valid auth + valid body writes exactly **one** row to
  `lesson_view_events` and returns 204 No Content.
- **AC-5** — Dual-write failure semantics honor §12 D-4 / §14 OQ-1
  lock. Verified by `test_review_quiz_item_postgres_failure_does_not_break_request`.
- **AC-6** — Zero new PostHog events. Verified by `git diff` on
  `.agent/skills/analytics.md` showing no event additions.
- **AC-7** — Legacy `card_progress` / `card_review` (if any) +
  `card_feedback` event paths untouched. Verified by `git diff
  --stat` showing no changes to `study_service.py`,
  `card_service.py`, or related test files.
- **AC-8** — No schema change to slice 6.1 tables (`decks`,
  `lessons`, `quiz_items`, `quiz_item_progress`). Verified by `git
  diff --stat` on `app/models/{deck,lesson,quiz_item,quiz_item_progress}.py`
  showing no changes.
- **AC-9** — FK `ON DELETE` behaviors verified per §4.3:
  `user_id → SET NULL`; `quiz_item_id`/`lesson_id`/`deck_id →
  CASCADE` on both tables. Verified inside the schema-shape tests.
- **AC-10** — `analytics_event_service` exposes only write methods
  (no UPDATE / DELETE), enforcing the §4.4 append-only invariant
  structurally. Verified by `test_quiz_review_events_appendonly_invariant`.
- **AC-11** — FE `pages/Lesson.tsx` calls `recordLessonView()`
  alongside the existing `capture('lesson_viewed', ...)` on the
  same `useEffect`. Verified by component test (mocked fetch).

## 12. Decisions

> Phase-level decisions referenced here use the IDs from this
> slice's front-matter (I1, J2). Slice-local decisions are numbered
> D-1, D-2, …

### Phase-level decision rationale

- **I1 (events dual-write).** Spec #38 banned the PostHog Query API
  in `/admin/analytics`, so slice 6.13/6.13.5 (content-quality
  dashboards) and slice 6.16 (FSRS retention) need a Postgres event
  source. PostHog stays for funnels (where HogQL excels) and product
  retention. Dual-write is simpler than picking one storage and
  building a sync. Storage cost is bounded — events are flat rows
  with a TTL a future retention slice will set (§14 OQ-3). This
  spec is the slice that builds those tables.
- **J2 (quality signals key).** Out of scope here. Reference only
  so spec readers understand the line between event capture (slice
  6.0) and quality signals (slice 6.13.5). Quality signals are
  derived analytics (admin spot-check / AI critique / user thumbs
  feedback), keyed differently, with a different write cadence.
  Two separate tables, two separate slices.

### Slice-local decisions

- **D-1 — `user_id` FK `ON DELETE SET NULL`; content FKs
  CASCADE.** Anonymization vs analytical-anchor preservation.
  Account deletion (privacy / GDPR-adjacent) should not erase
  aggregate retention data — the user's individual contribution
  becomes anonymous, but the deck/lesson-level rollups stay
  meaningful. Hard-delete of content (rare in practice — slice 6.4
  uses soft-archive / soft-retire) means the event row no longer
  has an analytical anchor, so CASCADE is correct.
- **D-2 — Denormalize `lesson_id` and `deck_id` on
  `quiz_review_events`; denormalize `deck_id` on
  `lesson_view_events`.** Storage is cheap; JOIN speed at scale
  matters. `lesson_id` is joinable via `quiz_items.lesson_id` and
  `deck_id` via `lessons.deck_id`, but every retention/quality
  dashboard query that aggregates by lesson or deck would otherwise
  do a 3-table join. Lesson IDs are stable (slice 6.4 substantive
  edits **bump version**, not lesson_id; lesson_id-on-row drift is
  not a real concern). Confirmed via slice 6.1 §4.2 (lessons.id is
  the PK and is set at create-time, never reassigned).
- **D-3 — Append-only invariant enforced structurally, not via
  trigger.** `analytics_event_service` exposes only `write_*`
  functions; no UPDATE/DELETE method exists. Postgres-side trigger
  / RULE would be a stronger guarantee but adds migration
  complexity. The structural constraint is sufficient for app-code
  correctness; admin / direct-DB intervention is out of band by
  design (matches existing `usage_logs` / `paywall_dismissals`
  patterns).
- **D-4 — `lesson_view_events` ships with a new BE write route +
  FE call alongside the existing FE PostHog `capture()`.**
  Considered alternatives:
  - (a) Add a thin `POST /api/v1/lessons/:id/view-event` route the
    FE calls in addition to the existing `capture('lesson_viewed')`.
    **Picked.** Minimum blast radius. Preserves existing FE
    telemetry. Mirrors the BE-side dual-write shape used for
    `quiz_item_reviewed`.
  - (b) Move emission entirely to BE — drop FE `capture()`,
    forward PostHog event from BE post-write. **Rejected.** Larger
    blast radius (changes existing FE telemetry, requires PostHog
    `track()` from a route handler + identify-mapping work),
    diverges from the slice 6.3-shipped pattern, and provides no
    new analytical capability over (a).
  - See §14 OQ-4 for the open-question framing — Dhamo to confirm
    (a) at impl-lock time.
- **D-5 — `quiz_item_progress_initialized` is NOT dual-written.**
  Derivable from the `MIN(reviewed_at) GROUP BY user_id,
  quiz_item_id` aggregate over `quiz_review_events`. Dual-writing
  would denormalize a cheap-to-derive signal.
- **D-6 — `lesson_section_expanded` is NOT dual-written.** A
  separate event with a separate table-or-not OQ. If slice
  6.13/6.16 needs section-level engagement signals in SQL, that
  spec authors a `lesson_section_event` table; this slice does not
  pre-empt the design.
- **D-7 (resolves OQ-1) — Dual-write failure semantics: best-effort
  both writes.** Both `analytics_event_service.write_quiz_review_event`
  and `analytics_event_service.write_lesson_view_event` wrap their
  Postgres INSERT in `try/except SQLAlchemyError`, log via
  `logger.exception(...)` with an event-type tag, and return `None`
  on failure (no raise). The wrapper inside
  `quiz_item_study_service.review_quiz_item` (lines 438-451 emission
  site) wraps the `write_quiz_review_event` call in its own
  `try/except Exception` so analytics failure NEVER blocks the
  user's review request — the existing PostHog `analytics_track`
  call retains its current shape verbatim. Same wrapper shape applies
  to the new `POST /api/v1/lessons/:lesson_id/view-event` route's
  `write_lesson_view_event` call. Both writes are analytical;
  neither belongs in the user-blocking critical path. Cross-ref
  §6.2, §6.3, §4.4.
- **D-8 (resolves OQ-2) — Denormalization extent: lock the
  author-hinted shape.** `quiz_review_events` carries denormalized
  `lesson_id` + `deck_id` columns; `lesson_view_events` carries a
  denormalized `deck_id` column. Stability lock derives from slice
  6.4 D-17 (substantive lesson edits bump `lessons.version`, not
  `lessons.id`); deck-FK stability follows from `lessons.deck_id`
  being immutable on the `lessons` table. Indexes
  `ix_quiz_review_events_lesson_reviewed_at`,
  `ix_quiz_review_events_deck_reviewed_at`, and
  `ix_lesson_view_events_deck_viewed_at` retained per §4.1 + §4.2.
  Storage cost is bounded; JOIN-elimination on per-lesson /
  per-deck rollups is the read-side win that justifies the columns.
  Cross-ref §4.1, §4.2.
- **D-9 (resolves OQ-3) — Retention/TTL: out of scope this slice.**
  Append-only invariant per §4.4 + AC-10 is the only durability
  constraint locked here. A future "Phase 6 6.x — analytics-table
  retention" slice handles purge cadence + GDPR right-to-erasure
  cascade beyond the existing `user_id ON DELETE SET NULL` shape.
  Job-runner choice — **Railway cron preferred over RQ-on-Redis**
  per LD G2 confirmation 2026-04-27 (cadence is fixed daily / weekly,
  no fan-out, matches the daily-Pro-digest pattern slice 6.14 will
  also use). Retention cutoff (90d / 365d / per-event-type) deferred
  to that slice's own §12 lock. Cross-ref §4.4, §13 (Out of scope).
- **D-10 (resolves OQ-4) — `lesson_view_events` emission path:
  path (a) thin BE write route + FE caller alongside the existing
  FE `capture('lesson_viewed')`.** New BE route
  `POST /api/v1/lessons/:lesson_id/view-event` returning 204
  No Content per §6.3 stays as authored. FE `pages/Lesson.tsx`
  `useEffect` (currently lines 34-46) retains its
  `capture('lesson_viewed', { lesson_id, ... })` call verbatim AND
  adds a parallel `recordLessonView(lessonId, body).catch(() => {})`
  call — both fire on the same `useEffect` mount. Postgres
  `lesson_view_events` and PostHog `lesson_viewed` carry
  identical-payload-shape guarantees from the FE side; payload
  divergence (BE-only fields like server-resolved `persona`) is
  allowed but FE-emitted fields must match between the PostHog
  payload and the `LessonViewEventRequest` body. Path (b) (drop FE
  `capture()`, BE forwards to PostHog post-write) explicitly
  rejected — would require §6.3 / §6.4 rewrite, a new AC-11, and a
  re-derived integration-test shape; marginal architectural purity
  not worth scope expansion. Cross-ref §6.3, §6.4, §3.

## 13. Out of scope (deferred to other Phase-6 slices)

Explicit list:

- **Query routes** — `GET /api/v1/admin/analytics/quiz-reviews`,
  `GET /api/v1/admin/analytics/lesson-views`, etc. Slice 6.13 /
  6.13.5 / 6.16 spec resolves.
- **Admin dashboards** — `pages/AdminAnalytics.tsx` extension,
  `pages/AdminQuizReviewExplorer.tsx`, etc. Slice 6.16 spec
  resolves.
- **`card_quality_signals` table** — slice 6.13.5 spec resolves
  (per J2 lock).
- **Retention / TTL / row-aging policy** — see §14 OQ-3. A future
  slice picks the cutoff (90d? 365d? per-event-type?) and the
  job-running pattern (RQ vs Railway cron, both available per G2).
- **`lesson_section_expanded` Postgres capture** — D-6 above.
- **Event-replay backfill of historical PostHog data** — these
  tables start empty at impl-merge. Pre-cutover analytics either
  query PostHog directly or accept the boundary.
- **PostHog Query API / HogQL integration** — banned per spec #38.
- **FE consumer surface beyond a single best-effort call** — see
  §6.4. No loading state, no error UI, no retry queue.
- **New PostHog events** — zero this slice.
- **Migration code, model code, route code, service code, test
  code** — implementation slice's deliverables.
- **Schema for slice 6.1 tables** — untouched. Slice 6.0 only
  ADDs new tables; slice 6.1's four tables stay byte-identical.
- **Edit-classification rule logic** — slice 6.4's D-17 +
  `_is_substantive_change`; out of band for analytics-table
  authoring.

## 14. Open questions

> **OQ-1 / OQ-2 / OQ-3 / OQ-4 all RESOLVED at spec amendment
> `<this-slice>`** — locked into §12 as D-7 / D-8 / D-9 / D-10
> respectively. OQ headings + question text retained verbatim below
> for forward-readability; the resolution line cites the §12 D-N
> decision that closes each one. Mirrors slice 6.4 §14 OQ-2..OQ-6
> post-amendment shape (`4fce036` / `de1e9a9`).

### OQ-1 — Dual-write failure semantics

If Postgres write succeeds but PostHog fails (or vice versa), what's
the right behavior?

**RESOLVED** — see §12 **D-7** (`<this-slice>`): best-effort both
writes. `analytics_event_service.write_*` wraps the Postgres INSERT
in `try/except SQLAlchemyError` + `logger.exception(...)`; the
calling site (`review_quiz_item` lines 438-451 + the new lesson
view-event route) wraps in `try/except Exception` so analytics
failure never blocks the user request. PostHog `analytics_track`
shape unchanged.

### OQ-2 — Schema redundancy vs query speed (denormalization extent)

Should `quiz_review_events` denormalize fields like `lesson_id`
(joinable via `quiz_item.lesson_id`) and `deck_id` (joinable via
`lesson.deck_id`) for query speed, or stay strictly normalized?

**RESOLVED** — see §12 **D-8** (`<this-slice>`): denormalize
`lesson_id` + `deck_id` on `quiz_review_events`; denormalize
`deck_id` on `lesson_view_events`. Stability lock derives from
slice 6.4 D-17 (lesson IDs immutable on substantive edits — only
version bumps); §4.1 / §4.2 indexes retained as authored.

### OQ-3 — Retention / TTL policy

These tables grow unbounded. A power user reviewing 50 quiz_items/day
generates ~18k rows/year per user. Do we lock retention now or defer?

**RESOLVED** — see §12 **D-9** (`<this-slice>`): out of scope this
slice. Append-only invariant per §4.4 + AC-10 is the only durability
constraint. A future "Phase 6 6.x — analytics-table retention"
slice owns purge cadence + GDPR right-to-erasure cascade beyond
the existing `user_id ON DELETE SET NULL` shape; job runner
**Railway cron** per LD G2 confirmation 2026-04-27 (over RQ-on-Redis).
Cutoff value deferred to that slice.

### OQ-4 — `lesson_view_events` emission path (FE-only `lesson_viewed` reality)

**Surfaced at spec authoring per R19 push-back.**

`lesson_viewed` is **FE-only** today (`pages/Lesson.tsx:37`). There
is no BE service-layer site to dual-write at. The prompt's framing
("service-layer hooks in `lesson_service.py` to dual-write
on event emission alongside the existing PostHog calls") doesn't
match disk — `lesson_service.py` does not emit `lesson_viewed`.

**RESOLVED** — see §12 **D-10** (`<this-slice>`): path (a) — thin
BE write route (`POST /api/v1/lessons/:lesson_id/view-event` per
§6.3) + FE caller (`recordLessonView()` per §6.4) alongside the
existing FE `capture('lesson_viewed')`. Both fire on the same
`useEffect` mount; FE-emitted fields must match between PostHog
payload and `LessonViewEventRequest` body (BE-only fields like
server-resolved `persona` are allowed). Path (b) (drop FE
`capture()`, BE forwards to PostHog) explicitly rejected — marginal
architectural purity not worth §6.3 / §6.4 rewrite + new AC. §4 /
§6 / §10 / §11 stand as authored under path (a).

### OQ-5+ (placeholder)

If chat-Claude or impl-time CC surfaces additional product OQs
(e.g. "should `quiz_review_events` carry the `is_first_review` bool
explicitly rather than deriving it from progress.reps?" or "should
we add a `client_emitted_at` column to detect clock skew between FE
session_id and BE write?"), file them as OQ-5 / OQ-6 below at
spec-amendment time.
