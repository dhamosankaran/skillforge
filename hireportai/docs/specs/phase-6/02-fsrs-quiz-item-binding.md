# Phase 6 — Slice 6.2: FSRS Quiz-Item Binding (service + routes)

## Status: Drafted, not shipped

| Field | Value |
|-------|-------|
| Phase | 6 (Curriculum Platform) |
| Slice | 6.2 — FSRS quiz-item binding |
| Mode | 4 (spec-author) |
| Author HEAD | `50e94d6` (post-D-025 bookkeeping) |
| Spec authored | 2026-04-26 |
| Implementation slice | TBD (will follow this spec) |
| BACKLOG row | none yet — implementation slice files at execution time per R17 (next free is `B-062`; current highest in-use `B-061` per slice 6.1) |
| Spec dependencies | `docs/specs/phase-6/01-foundation-schema.md` (slice 6.1, shipped at `a989539` / `f621248`) — `quiz_items` + `quiz_item_progress` tables exist, `quiz_item_progress` is byte-identical to `card_progress` modulo FK swap (D-1 + AC-6 of slice 6.1). |
| Audit dependency | `docs/audits/phase-6-scout.md` (commit `5b0aa23`) — §1.1 card / FSRS data model, §1.2 FSRS implementation, §1.3 free-tier daily-review wall, §6.2 event taxonomy. |
| Slice dependencies | **Upstream:** slice 6.1 (foundation schema) — required, must be merged. **Downstream:** unblocks slices 6.3 (lesson-card UX, FE consumes these routes), 6.4 (admin authoring — needs quiz_item_progress write path to compute "is anyone reviewing this?"), 6.5 (three-layer quality — observes review outcomes), 6.6 (Lens-ranked deck/card ordering — re-orders the queue), 6.16 (FSRS retention dashboard — aggregates over `quiz_item_progress`). |

### Phase 6 locked decisions referenced by this spec

> Recorded in front-matter so spec readers see the relevant locks
> without chasing SESSION-STATE. Rationale lives in §11 (Decisions) below.

| ID | Decision |
|----|----------|
| **G2** | Background jobs: RQ on Redis for ingestion; Railway cron for daily Pro digest. Not consumed by this slice — review path is request-time synchronous. |
| **I1** | Events: dual-write. PostHog for funnels/retention; Postgres `quiz_review_events` + `lesson_view_events` for content-quality / retention dashboards. **Slice 6.0 owns the events table; this slice declares the contract** for `quiz_item_reviewed` and `quiz_item_progress_initialized` (the two emit points this slice introduces). |

---

## 1. Problem

Slice 6.1 shipped the four foundation tables (`decks`, `lessons`,
`quiz_items`, `quiz_item_progress`) but no consumer code reads or writes
`quiz_item_progress`. Phase 6's locked decision binds FSRS scheduling
to **quiz_items** (not lessons): substantive lesson edits do not reset
FSRS state; substantive quiz-item edits retire the row via
`retired_at` + `superseded_by_id`. To make that locked decision
operational, slice 6.2 ships the service + route layer that mirrors
today's `study_service.review_card` / `study_service.get_daily_review`
pattern (audit §1.2) against `quiz_item_progress` instead of
`card_progress`. After this slice ships, an authenticated user can pull
a daily quiz-item queue and submit reviews against quiz_items via
`/api/v1/quiz-items/...`; the legacy `/api/v1/study/...` path stays
alive in parallel until slice 6.15 cleanup.

## 2. Goals

1. Ship `app/services/quiz_item_study_service.py` — a new file (D-1) with
   `review_quiz_item(...)`, `get_daily_quiz_items(...)`, helper
   `_build_fsrs_quiz_card(...)`, helper
   `_apply_fsrs_result_to_quiz_item(...)`, plus side-effect-free
   `_compute_daily_quiz_status(...)` mirror.
2. Mount `app/api/v1/routes/quiz_items.py` with three endpoints
   (`GET /api/v1/quiz-items/daily`, `POST /api/v1/quiz-items/review`,
   `GET /api/v1/quiz-items/progress`) wired into `app/main.py`.
3. Extend `app/schemas/quiz_item.py` (slice 6.1's file) with read +
   write schemas for the new endpoints (`DailyQuizItem`,
   `DailyQuizReviewResponse`, `QuizReviewRequest`, `QuizReviewResponse`,
   `QuizProgressResponse`, plus a re-export of `DailyStatus` so callers
   don't have to dual-import).
4. Mirror `study_service`'s FSRS reconstruction byte-for-byte (D-2):
   same py-fsrs `Card` / `Rating` / `Scheduler` / `State` imports, same
   module-level `_scheduler = Scheduler()` singleton, same
   `_STATE_TO_FSRS` / `_FSRS_TO_STATE` mappings, same `_build_fsrs_card`
   shape, same `_apply_fsrs_result` write-back shape. Differences are
   strictly the FK swap (`card_id` → `quiz_item_id`) and the gate
   semantics (no `Category.source='foundation'` plan gate at the service
   layer; that lives on `decks.tier` and is enforced upstream of this
   service per slice 6.4 / 6.7).
5. Declare the `quiz_item_reviewed` and
   `quiz_item_progress_initialized` analytics events the implementation
   slice will fire (slice 6.0 owns the table; this spec locks the
   payload shape).

## 3. Non-goals

- **Free-tier daily-card wall (write-side enforcement)** —
  `_check_daily_wall` (`study_service.py:175-276`) is an in-process
  Redis INCR with 402 raise. **This slice ships the read-side mirror
  only** (`_compute_daily_quiz_status`, returning `DailyStatus`); the
  write-side enforcement against quiz_items is **deferred** (D-4). The
  implementation slice for 6.2 calls `_compute_daily_quiz_status` from
  the daily endpoint but does NOT call any wall-incrementing code from
  the review endpoint. Free users in this slice can review unlimited
  quiz_items — the legacy `/api/v1/study/review` wall only enforces the
  card_progress write path; quiz_items are unwalled until a follow-up
  slice spec'd separately. (See §11 D-4 for rationale.)
- **Persona-aware ranking** — the daily-five queue uses naive
  `due_date ASC` then `created_at ASC` ordering (D-6). Lens-driven
  reordering for Interview Prepper users is slice 6.6.
- **FE consumer surface** — no `useDailyQuizQueue` hook, no
  `QuizItemViewer` page, no `QuizPanel.tsx` rewrite. Wire shapes are
  defined; FE consumption is slice 6.3 (lesson-card UX) (D-5).
- **Lesson lookups (`/api/v1/lessons/...`)** — slice 6.3 / 6.4 / 6.7.
  The daily quiz queue returns `lesson_id` + lesson title for context,
  but does not let callers fetch a full lesson via this slice's routes.
- **Admin authoring** — slice 6.4. No admin-only endpoints in 6.2.
- **Cross-model critique on review outcomes** — slice 6.5 / 6.13.5.
  Review outcomes are written to `quiz_item_progress`; a follow-up slice
  consumes them as a quality signal.
- **Schema changes** — slice 6.1 already shipped the four tables. No
  Alembic migration in this slice. (If the implementation slice
  discovers a schema gap, it STOPs and reports — N7.)
- **Gamification XP / streak award on quiz_item review** — today's
  `study_service.review_card` calls `gamification_service.award_xp`
  (`study_service.py` ~line 540) on each non-Again rating. This slice
  ships the FSRS path WITHOUT XP wiring; the `gamification_service`
  contract on quiz_item reviews is owned by a separate slice (XP
  schema reuse vs new `quiz_xp` column is its own product call). The
  implementation slice MUST NOT silently call `award_xp` to "match
  parity" — if XP-on-quiz is desired, file a BACKLOG row and pick it
  up in its own slice. (See §11 D-7.)
- **Home-state / progress dashboard wiring** — `home_state_service`
  reads `card_progress.last_reviewed`. After this slice ships, dual-read
  (CardProgress UNION QuizItemProgress) becomes possible. Out of scope
  here; slice 6.16 (retention dashboard) or a hygiene slice picks it
  up.

## 4. Service surface — `app/services/quiz_item_study_service.py`

> **D-1 (locked).** New file. **Do NOT extend `study_service.py`.**
> Rationale: clean coexistence with the legacy
> `cards`/`categories`/`card_progress` path; slice 6.15 cleanup
> becomes a `git rm app/services/study_service.py` instead of a
> conditional-branch refactor. Trade-off acknowledged: small amount of
> structurally-similar code in two places (the FSRS reconstruction
> helpers ~30 lines each); judged worth it because the gate semantics
> diverge — `study_service` uses `Category.source='foundation'`,
> `quiz_item_study_service` will eventually gate on `decks.tier` (out
> of scope for 6.2 itself per §3).

### 4.1 Module-level constants + scheduler

```python
_DAILY_GOAL = 5  # See OQ-1 below for whether 6.2 keeps this or picks differently.
_scheduler = Scheduler()  # py-fsrs singleton (same pattern as study_service.py:48)

_STATE_TO_FSRS: dict[str, State] = {
    "learning": State.Learning,
    "review": State.Review,
    "relearning": State.Relearning,
}
_FSRS_TO_STATE: dict[State, str] = {v: k for k, v in _STATE_TO_FSRS.items()}
```

The implementation slice MAY extract these to a shared module
`app/services/_fsrs_constants.py` so `study_service` and
`quiz_item_study_service` share one definition. **Optional** — picking
this up adds an out-of-slice refactor risk and slice 6.15 retires the
duplication anyway. Defer to implementation-slice judgment.

### 4.2 `_build_fsrs_quiz_card(progress: QuizItemProgress) -> FsrsCard`

Reconstruct a py-fsrs `Card` from a stored `QuizItemProgress` row.
Byte-equivalent to `_build_fsrs_card` (`study_service.py:63-80`) modulo
the `card_progress` → `quiz_item_progress` swap. Behavioral note: for
`progress.state == "new"`, return a fresh `FsrsCard()` (py-fsrs treats
new as Learning step=0, which is exactly right for the first review).

### 4.3 `_apply_fsrs_result_to_quiz_item(progress: QuizItemProgress, updated: FsrsCard, elapsed_days: float, now: datetime) -> None`

Write py-fsrs result back into the `QuizItemProgress` ORM object.
Byte-equivalent to `_apply_fsrs_result` (`study_service.py:83-104`).
Caller is responsible for `flush()`. Behavioral note: `state` is
written via `_FSRS_TO_STATE`; `stability` / `difficulty_fsrs` get
defensive `or 0.0` guards (matches existing pattern); `scheduled_days`
is fractional days from `now` to `updated.due` clamped to `>= 0`.

### 4.4 `_compute_daily_quiz_status(user: User, db: AsyncSession) -> DailyStatus`

Read-side mirror of the slice-deferred wall (D-4). Side-effect-free —
no Redis INCR. **Returns the unconditional permissive sentinel for
slice 6.2** (i.e. `cards_consumed=0`, `cards_limit=-1`, `can_review=True`,
`resets_at=<next_local_midnight>`) until the wall-enforcement slice
lands. Behavioral note: shape is byte-identical to
`study_service._compute_daily_status`'s return so FE can reuse the same
`DailyStatus` interface from `app/schemas/study.py`. The sentinel-only
behavior is locked in code (not a runtime branch on a flag) so the
follow-up wall-enforcement slice has a clear "rewrite this function"
target rather than "remove a flag." See §6 for the wire shape.

> **Why ship the read-side as a permissive stub?** Two reasons:
> (1) FE consumers (slice 6.3) can target the final
> `DailyQuizReviewResponse.daily_status` shape today instead of being
> rewritten when the wall lands; (2) the field reservation prevents a
> Pydantic schema-version churn between 6.2 and the wall slice.

### 4.5 `get_daily_quiz_items(user_id: str, db: AsyncSession, *, user: Optional[User] = None) -> DailyQuizReviewResponse`

Two-pass queue build (D-2 — byte-equivalent to
`study_service.get_daily_review`):

1. **Pass 1 — overdue progress rows.**
   `select(QuizItemProgress, QuizItem, Lesson, Deck)` joined through
   FK chain, where `QuizItemProgress.user_id == user_id`,
   `state != "new"`, `due_date <= now`. Order `due_date ASC`, limit
   `_DAILY_GOAL`. Filter retired quiz_items
   (`QuizItem.retired_at IS NULL`) and archived lessons / decks
   (`Lesson.archived_at IS NULL`, `Deck.archived_at IS NULL`).
2. **Pass 2 — fill with unreviewed quiz_items.** Subquery: quiz_item
   IDs the user already has a `quiz_item_progress` row for. Outer
   query: `select(QuizItem, Lesson, Deck)` where
   `QuizItem.id NOT IN <subquery>`, `QuizItem.retired_at IS NULL`,
   `Lesson.archived_at IS NULL`, `Deck.archived_at IS NULL`. Order
   `QuizItem.created_at ASC`, limit `_DAILY_GOAL - len(pass_1_result)`
   (D-6 — naive ordering only).

Returns `DailyQuizReviewResponse` with `quiz_items: list[DailyQuizItem]`,
`total_due: int`, `session_id: str` (UUID for the
`quiz_review_session_started` event), `daily_status: DailyStatus`
(from `_compute_daily_quiz_status`).

**Plan-gate semantics in this slice:** none. Free / Pro / Enterprise /
admin all see the same queue. Plan-gating against `decks.tier` is
slice 6.7 (Learn page composition); 6.2 is content-agnostic. The
implementation slice MUST NOT add a `decks.tier='foundation'` filter
even as a "obvious safety" — that would silently lock free users out of
quiz_items they should see during the 6.2-only window.

### 4.6 `review_quiz_item(user_id: str, quiz_item_id: str, rating: int, db: AsyncSession, time_spent_ms: int = 0, session_id: Optional[str] = None, user: Optional[User] = None) -> QuizReviewResponse`

Apply a FSRS review rating to a quiz_item. Mirrors
`study_service.review_card` (`study_service.py:514-...`) modulo:

- FK swap (card_id → quiz_item_id, card_progress → quiz_item_progress).
- Plan-gate removed (no `is_free` parameter; gating handled upstream).
- Daily-wall write side **NOT** invoked (D-4) — no Redis INCR, no 402
  raise. The `user` parameter is accepted for symmetry with
  `study_service.review_card` but only consumed for analytics
  attribution and (eventually) the wall slice.
- Retired-quiz_item guard. If `QuizItem.retired_at IS NOT NULL`, raise
  `QuizItemRetiredError(quiz_item_id)` BEFORE any FSRS or
  `quiz_item_progress` mutation. This enforces the spec 6.1 §4.3
  invariant ("a quiz_item with `retired_at IS NOT NULL` must NOT
  receive new `quiz_item_progress` rows") at the service layer where
  the error message can be informative; existing rows pointing to a
  retired quiz_item continue to receive updates (history preservation
  for analytics — only NEW progress-row creation is blocked).
- Lesson / deck archive guard. If
  `Lesson.archived_at IS NOT NULL OR Deck.archived_at IS NOT NULL`,
  raise `QuizItemForbiddenError(quiz_item_id)` (HTTP 403). Mirrors the
  legacy `card_service` plan-gate raise pattern.

Returns `QuizReviewResponse` with the post-review FSRS state
(`fsrs_state`, `stability`, `difficulty`, `due_date`, `reps`, `lapses`,
`scheduled_days`).

Raises:
- `QuizItemNotFoundError` — quiz_item_id does not exist (HTTP 404).
- `QuizItemRetiredError` — quiz_item exists but `retired_at IS NOT NULL`
  AND no progress row for `(user_id, quiz_item_id)` exists yet (HTTP
  409 — conflict; new reviews on retired items are blocked, but updates
  to existing progress rows are not). Implementation note: the
  retired-guard fires only when the path would CREATE a new
  `quiz_item_progress` row. Updates to a pre-existing row pass through
  so a user mid-review-session on a quiz_item that was retired between
  fetch and submit doesn't lose their FSRS history.
- `QuizItemForbiddenError` — lesson or deck is archived (HTTP 403).

### 4.7 `get_quiz_progress(user_id: str, db: AsyncSession) -> QuizProgressResponse`

Aggregate quiz-item study stats for the caller. Mirrors
`study_service.get_progress` (`study_service.py:~range`) byte-for-byte
modulo the table swap. Returns
`{total_reviewed, by_state: {new, learning, review, relearning}, total_reps, total_lapses}`.

### 4.8 Service errors

- `QuizItemNotFoundError(quiz_item_id: str)` — analog of
  `CardNotFoundError`.
- `QuizItemForbiddenError(quiz_item_id: str)` — analog of
  `CardForbiddenError`. Used for archived-lesson / archived-deck paths.
- `QuizItemRetiredError(quiz_item_id: str)` — new error class. No
  `study_service` analog (cards have no retired-state concept).

The `DailyReviewLimitError` analog is **not** introduced in this
slice (D-4).

## 5. Route surface — `app/api/v1/routes/quiz_items.py`

All endpoints require `Depends(get_current_user)`. All endpoints
inherit the global slowapi default (100 req/min) — no per-route
override (matches `/api/v1/study/...` precedent at `app/main.py`).

> **Path naming.** Spec adopts `/api/v1/quiz-items` as the route
> namespace. `quiz-items` (kebab-case) matches the FE-facing convention
> already established by `/api/v1/email-prefs`. Open question OQ-2
> below tracks an alternative (`/api/v1/quiz` or `/api/v1/study/v2`);
> chat-Claude / Dhamo can flip before implementation if a stronger
> precedent surfaces. The spec body uses `quiz-items` throughout for
> concreteness.

### 5.1 `GET /api/v1/quiz-items/daily`

| Field | Value |
|-------|-------|
| Method | GET |
| Path | `/api/v1/quiz-items/daily` |
| Auth | `Depends(get_current_user)` |
| Request body | none |
| Query params | none |
| Response model | `DailyQuizReviewResponse` (Pydantic v2; see §6.2) |
| Rate limit | global default 100 req/min |
| Status codes | 200 / 401 (no auth) |

Behavior: returns up to `_DAILY_GOAL` quiz_items via
`get_daily_quiz_items`. Empty list when nothing is due (never 404).
Includes `daily_status` sub-object (permissive sentinel until wall
slice — D-4).

### 5.2 `POST /api/v1/quiz-items/review`

| Field | Value |
|-------|-------|
| Method | POST |
| Path | `/api/v1/quiz-items/review` |
| Auth | `Depends(get_current_user)` |
| Request body | `QuizReviewRequest` (§6.3) |
| Response model | `QuizReviewResponse` (§6.4) |
| Rate limit | global default 100 req/min |
| Status codes | 200 / 400 (invalid rating or time_spent_ms) / 401 / 403 (lesson or deck archived) / 404 (quiz_item not found) / 409 (quiz_item retired and no existing progress row) |

Behavior: validates rating ∈ [1, 4] and `time_spent_ms` ∈ [0, 300_000]
via Pydantic Field constraints (mirrors
`schemas/study.py::ReviewRequest`). Service raises map to HTTP codes
above per FastAPI convention (HTTPException with `detail=str(exc)` for
404 / 403 / 409).

### 5.3 `GET /api/v1/quiz-items/progress`

| Field | Value |
|-------|-------|
| Method | GET |
| Path | `/api/v1/quiz-items/progress` |
| Auth | `Depends(get_current_user)` |
| Request body | none |
| Response model | `QuizProgressResponse` (§6.5) |
| Rate limit | global default 100 req/min |
| Status codes | 200 / 401 |

Behavior: aggregate stats. Quiz_items the user has never touched are
not in the counts (they appear as fresh-fill in the daily queue).

### 5.4 Wiring

`app/main.py` mounts the new router as
`app.include_router(quiz_items.router, prefix="/api/v1", tags=["quiz-items"])`.
Imports follow the existing `from app.api.v1.routes import ...,
quiz_items` pattern at `app/main.py` (existing import block). Order
inside the include_router block is alphabetical or
chronologically-by-phase — implementation slice picks per repo
convention.

## 6. Pydantic schemas — extending `app/schemas/quiz_item.py`

> Slice 6.1 shipped `app/schemas/quiz_item.py` with `QuizItemResponse`
> + the `QuizQuestionType` / `QuizDifficulty` `Literal` aliases. This
> slice extends the same file additively (D-1's "single file per
> domain" pattern from spec 6.1 §5.3 #4). No new file in
> `app/schemas/`.

### 6.1 `DailyQuizItem`

Single quiz item in the daily queue (analog of
`schemas/study.py::DailyCardItem`). Field-by-field:

| Field | Type | Source-of-truth | Notes |
|-------|------|-----------------|-------|
| `quiz_item_id` | `str` | `quiz_items.id` | UUID-as-string. |
| `lesson_id` | `str` | `lessons.id` | Forward-link for slice 6.3 lesson-card UX. |
| `lesson_title` | `str` | `lessons.title` | Cached on the queue item so FE doesn't N+1 fetch. |
| `deck_id` | `str` | `decks.id` | Slice 6.7 ranker context. |
| `deck_slug` | `str` | `decks.slug` | URL-stable identifier. |
| `question` | `str` | `quiz_items.question` | |
| `answer` | `str` | `quiz_items.answer` | |
| `question_type` | `QuizQuestionType` | `quiz_items.question_type` | `'mcq'` / `'free_text'` / `'code_completion'`. |
| `distractors` | `Optional[list[str]]` | `quiz_items.distractors` | Non-null only for `'mcq'`. |
| `difficulty` | `QuizDifficulty` | `quiz_items.difficulty` | Authored hint (NOT FSRS difficulty). |
| `fsrs_state` | `str` | `quiz_item_progress.state` OR literal `'new'` for fresh-fill | `new` / `learning` / `review` / `relearning`. |
| `due_date` | `Optional[datetime]` | `quiz_item_progress.due_date` | `None` for fresh-fill (state=`'new'` with no progress row). |
| `reps` | `int` | `quiz_item_progress.reps` | `0` for fresh-fill. |
| `lapses` | `int` | `quiz_item_progress.lapses` | `0` for fresh-fill. |

`model_config = ConfigDict(from_attributes=True)` per repo convention.

### 6.2 `DailyQuizReviewResponse`

Response for `GET /api/v1/quiz-items/daily`.

| Field | Type | Notes |
|-------|------|-------|
| `quiz_items` | `list[DailyQuizItem]` | Up to `_DAILY_GOAL` items (default 5; see OQ-1). |
| `total_due` | `int` | `len(quiz_items)`. Surfaced separately so FE doesn't recompute. |
| `session_id` | `str` | UUID; echo in `quiz_review_session_completed` analytics event. |
| `daily_status` | `DailyStatus` (re-imported from `app/schemas/study.py`) | Permissive sentinel until wall slice (D-4). Field is reserved here so 6.3 / wall-slice consumers don't churn the schema. |

> **Re-import note.** `DailyStatus` is defined at
> `app/schemas/study.py:30-45` (slice #63 / B-059). To avoid a
> Pydantic-side type duplication, slice 6.2 imports `DailyStatus` from
> `app/schemas/study` directly inside `quiz_item.py`. This creates a
> very weak coupling between the legacy and Phase-6 schema modules
> that slice 6.15 cleanup will need to resolve (likely by moving
> `DailyStatus` to a shared `app/schemas/_daily.py`); flagged in §12
> Out of Scope.

### 6.3 `QuizReviewRequest`

Request body for `POST /api/v1/quiz-items/review`. Mirrors
`schemas/study.py::ReviewRequest`.

| Field | Type | Validation | Notes |
|-------|------|------------|-------|
| `quiz_item_id` | `str` | non-empty | UUID-as-string. |
| `rating` | `int` | `Field(..., ge=1, le=4)` | Again=1, Hard=2, Good=3, Easy=4. |
| `session_id` | `str` | non-empty | Echoed from `DailyQuizReviewResponse.session_id`. |
| `time_spent_ms` | `int` | `Field(default=0, ge=0, le=300_000)` | Client-measured time on quiz; cap mirrors `ReviewRequest`. |

### 6.4 `QuizReviewResponse`

Response for `POST /api/v1/quiz-items/review`. Mirrors
`schemas/study.py::ReviewResponse`. All FSRS values reflect post-review
state.

| Field | Type | Notes |
|-------|------|-------|
| `quiz_item_id` | `str` | Echo of the request. |
| `fsrs_state` | `str` | `learning` / `review` / `relearning`. (Never `new` post-review.) |
| `stability` | `float` | py-fsrs scheduler value. |
| `difficulty` | `float` | py-fsrs `difficulty` (distinct from authored `QuizItem.difficulty`). |
| `due_date` | `datetime` | tz-aware; the next scheduled review. |
| `reps` | `int` | Post-review count. |
| `lapses` | `int` | Post-review count. |
| `scheduled_days` | `float` | Fractional days from now to `due_date`. |

### 6.5 `QuizProgressResponse`

Response for `GET /api/v1/quiz-items/progress`. Mirrors
`schemas/study.py::StudyProgressResponse`.

| Field | Type | Notes |
|-------|------|-------|
| `total_reviewed` | `int` | quiz_items with at least one review (state ≠ 'new'). |
| `by_state` | `dict[str, int]` | `{"new": n, "learning": n, "review": n, "relearning": n}`. |
| `total_reps` | `int` | Cumulative successful reviews. |
| `total_lapses` | `int` | Cumulative Again ratings. |

## 7. Daily-status read-side (D-4)

Wire shape for the `daily_status` field in `DailyQuizReviewResponse` —
byte-identical to the existing `app/schemas/study.py::DailyStatus`
(slice #63 / B-059):

```json
{
  "cards_consumed": 0,
  "cards_limit": -1,
  "can_review": true,
  "resets_at": "2026-04-27T00:00:00-07:00"
}
```

For slice 6.2:
- `cards_consumed` always `0` (no Redis read; no counter exists for
  quiz_items yet).
- `cards_limit` always `-1` (the unlimited sentinel).
- `can_review` always `true` — no quiz_item wall in this slice.
- `resets_at` computed via `_next_local_midnight(now_utc, tz)` from
  `study_service` (the helper is non-`_`-prefixed for this purpose;
  see §11 D-4 implementation note).

Field-name reuse (`cards_consumed`, `cards_limit`) is intentional: the
field is a `DailyStatus` instance, and the wall-enforcement slice may
later read these fields with quiz-counter values. Renaming to
`quiz_items_consumed` etc. would force a schema-version churn between
6.2 and the wall slice; locked to the legacy shape per the §6.2
"weak-coupling, slice 6.15 cleanup" note.

## 8. Analytics events declared by this slice

Per slice 6.1 §6 + Decision I1, every Phase 6 spec declares which
events its operations will emit. Slice 6.0 builds the events table;
this spec locks the contract for the two events the implementation
slice will fire.

| Event | Emit point | Properties | PostHog | Postgres (slice 6.0) |
|-------|------------|-----------|---------|----------------------|
| `quiz_item_progress_initialized` | BE `review_quiz_item` — fires on first review against a quiz_item (creates the progress row). | `{user_id, quiz_item_id, lesson_id, deck_id, plan, persona}` | ✓ | ✓ (powers slice 6.16's first-touch retention metric) |
| `quiz_item_reviewed` | BE `review_quiz_item` — fires on every review (including subsequent reviews of an existing progress row), AFTER the transaction commits. | `{user_id, quiz_item_id, lesson_id, deck_id, plan, persona, rating, fsrs_state_before, fsrs_state_after, reps, lapses, time_spent_ms, session_id}` | ✓ | ✓ (powers slice 6.5 retention curves + slice 6.16 dashboard) |

Idempotency: events fire from the service layer at the end of the
successful transaction (matches slice 6.1 §6 convention) — a 500
partway through leaves no PostHog / Postgres row.

The session-level event (`quiz_review_session_completed`) is
**deferred** to slice 6.3 (lesson-card UX) where the FE knows when a
session ends; this slice's BE has no signal for "session ended."

## 9. Acceptance criteria

The implementation slice (one-step follow-up) must pass:

- **AC-1** — `app/services/quiz_item_study_service.py` ships as a new
  file; `study_service.py` is unmodified by this slice (D-1).
- **AC-2** — `app/api/v1/routes/quiz_items.py` ships as a new file;
  registered in `app/main.py` under `/api/v1` prefix; the three
  endpoints (`/quiz-items/daily`, `/quiz-items/review`,
  `/quiz-items/progress`) respond 200 to authenticated calls in their
  happy-path tests.
- **AC-3** — `quiz_item_progress` schema-shape is consumed
  byte-equivalently to `card_progress` (D-2). Verified by a service
  test that constructs a `FsrsCard` from a `QuizItemProgress` row,
  feeds it to `_scheduler.review_card(...)`, and asserts the
  post-review FSRS state matches what `study_service` computes for the
  same input.
- **AC-4** — Retired-quiz_item guard. A `POST /quiz-items/review`
  against a quiz_item with `retired_at IS NOT NULL` AND no existing
  progress row returns 409. With an EXISTING progress row, the same
  call returns 200 (history preservation per §4.6).
- **AC-5** — Archived-lesson and archived-deck guards. A `POST
  /quiz-items/review` against a quiz_item whose lesson OR deck has
  `archived_at IS NOT NULL` returns 403.
- **AC-6** — Daily-status sentinel. `GET /quiz-items/daily` returns
  `daily_status.cards_limit == -1` and `can_review == true` for every
  caller (free / Pro / Enterprise / admin). Field is reserved for the
  wall-enforcement slice (D-4).
- **AC-7** — Naive ordering. The daily-five queue orders pass-1 by
  `quiz_item_progress.due_date ASC` and pass-2 by
  `quiz_items.created_at ASC`. No `decks.tier` filter, no persona
  branching (D-6).
- **AC-8** — Legacy `/api/v1/study/...` routes remain alive and
  unmodified. The legacy daily-card review wall continues enforcing
  against `card_progress` only.
- **AC-9** — `app/schemas/quiz_item.py` extended additively. The slice
  6.1 `QuizItemResponse` schema and `QuizQuestionType` /
  `QuizDifficulty` `Literal` aliases stay unchanged.
- **AC-10** — Test suite stays green. New tests run under default
  `not integration` selector (no LLM keys required).
- **AC-11** — `quiz_item_reviewed` and
  `quiz_item_progress_initialized` events fire from the service layer
  (mockable via `analytics_track`); test asserts the property keys
  match §8 verbatim.

## 10. Test plan

Implementation slice will add tests in two files (matching repo flat
layout per slice 6.1's D-024 / D-025 disposition: tests live at
`tests/test_*.py`, not in subdirs).

### 10.1 Unit tests — `tests/test_quiz_item_study_service.py`

- `test_build_fsrs_quiz_card_new_state` — fresh `QuizItemProgress`
  with `state="new"` returns a default `FsrsCard()`.
- `test_build_fsrs_quiz_card_review_state` — populated row maps to
  `FsrsCard(state=Review, step=None, stability=>0, difficulty=>0,
  due=<datetime>, last_review=<datetime>)`.
- `test_apply_fsrs_result_writes_back` — given a mock py-fsrs return,
  asserts `progress.state` / `stability` / `difficulty_fsrs` /
  `due_date` / `last_reviewed` / `elapsed_days` / `scheduled_days`
  are all written; `scheduled_days` non-negative.
- `test_get_daily_quiz_items_two_pass` — 3 overdue + 5 unreviewed in
  DB → returns 5 items (3 overdue + 2 fresh-fill); pass-1 ordered by
  `due_date ASC`, pass-2 ordered by `created_at ASC`.
- `test_get_daily_quiz_items_excludes_retired` — quiz_item with
  `retired_at IS NOT NULL` is filtered out of pass-2 fresh-fill.
- `test_get_daily_quiz_items_excludes_archived` — quiz_items whose
  lesson OR deck is archived are filtered out of both passes.
- `test_review_quiz_item_creates_progress_row` — first review against
  a quiz_item creates a `quiz_item_progress` row with the post-review
  FSRS state; `quiz_item_progress_initialized` event fires.
- `test_review_quiz_item_updates_existing` — second review updates
  the existing row; `quiz_item_progress_initialized` does NOT fire
  (only `quiz_item_reviewed`).
- `test_review_quiz_item_retired_blocks_new` — review against a
  retired quiz_item with no existing progress row raises
  `QuizItemRetiredError`.
- `test_review_quiz_item_retired_allows_existing` — review against a
  retired quiz_item with an existing progress row returns the
  post-review state (history preservation per §4.6).

### 10.2 Integration tests — `tests/test_quiz_items_api.py`

- `test_daily_endpoint_auth_required` — unauthenticated GET returns
  401.
- `test_daily_endpoint_returns_sentinel_status` — authenticated GET
  returns `daily_status.cards_limit == -1`,
  `daily_status.can_review == true`, regardless of plan.
- `test_review_endpoint_404_unknown` — POST against a
  nonexistent quiz_item_id returns 404.
- `test_review_endpoint_409_retired_no_progress` — POST against
  retired quiz_item with no existing progress row returns 409.
- `test_review_endpoint_403_archived_lesson` — POST against
  quiz_item in archived lesson returns 403.

**Target test count (this slice): +12** (10 unit + 5 integration = 15
adding cases above; trim to 12 if some collapse during impl). Spec §8
of slice 6.1 sets the precedent of a single test file per slice; this
slice splits service vs route across two files because the route
tests need the FastAPI test client fixture (which the service tests
don't). Implementation slice MAY collapse to a single
`test_phase6_quiz_items.py` if cleaner.

## 11. Decisions

> Phase-level decisions referenced here use the IDs from this slice's
> front-matter (G2, I1). Slice-local decisions are numbered D-1, D-2,
> …

### Slice-local decisions

- **D-1 — New service file `app/services/quiz_item_study_service.py`
  (do NOT extend `study_service.py`).** Rationale recorded in §4
  preamble. Trade-off: ~30 lines of structurally similar FSRS-
  reconstruction helpers duplicated across two files. Judged worth it
  because the gate semantics diverge today (legacy uses
  `Category.source`, Phase-6 uses `decks.tier` once 6.7 lands) and
  slice 6.15 cleanup retires the duplication via a `git rm` instead
  of a refactor branch.
- **D-2 — Port FSRS plumbing byte-for-byte from `study_service`.**
  Same py-fsrs imports, same module-level `_scheduler` singleton, same
  `_STATE_TO_FSRS` / `_FSRS_TO_STATE` mappings, same
  `_build_fsrs_card` shape, same `_apply_fsrs_result` write-back
  shape. Differences are FK swap and gate semantics only. Rationale:
  preserves a single mental model for FSRS behavior across the
  codebase; eases verification (AC-3); reduces blast radius if py-fsrs
  releases a v7 (one upgrade slice updates both).
- **D-3 — `_DAILY_GOAL = 5` matches today's `study_service._DAILY_GOAL`.**
  Open question OQ-1 below tracks whether Phase 6 product intent picks
  a different number. Defaulting to 5 keeps queue-size parity with
  legacy until a product decision flips it.
- **D-4 — Read-side daily-status mirror only; write-side wall
  enforcement is OUT OF SCOPE.** Slice 6.2 ships
  `_compute_daily_quiz_status` returning the permissive sentinel
  (`cards_limit=-1`, `can_review=True`) unconditionally. The
  wall-enforcement slice (deferred; spec'd separately) will rewrite
  this function to read a Redis counter and INCR on review submit.
  Rationale: (a) keeps slice 6.2 surgically scoped; (b) reserves the
  `daily_status` field on the response so 6.3 FE consumers don't
  churn when the wall lands; (c) preserves the rollback story —
  slice 6.2 can ship and stay live without the wall slice landing.
  Implementation note: the `_next_local_midnight` helper currently
  lives at `study_service.py:168` as a module-private function; the
  implementation slice for 6.2 EITHER (i) imports it via a defensive
  shim (e.g. `from app.services.study_service import _next_local_midnight as _next_local_midnight`)
  OR (ii) lifts it to a shared `app/utils/timezone.py` if the lift
  doesn't expand blast radius. Defer to implementation-slice judgment;
  flagged in OQ-3.
- **D-5 — No FE work in this slice.** Routes return wire shapes; FE
  consumption (lesson-card UX) is slice 6.3. Rationale: keeps the
  slice scope BE-only, matches slice 6.1's pattern (slice 6.1 shipped
  schemas with no consumer; 6.2 ships routes with no consumer). The
  FE shape is `QuizPanel`-equivalent but lives at slice 6.3.
- **D-6 — Naive ordering only (`due_date ASC` then `created_at ASC`).**
  No persona branching. No Lens-driven ranking. No
  `decks.tier='foundation'` filter. Rationale: slice 6.6 owns the
  ranker; slice 6.7 owns persona-aware composition; both are downstream
  of 6.2 and need 6.2's wire shapes to land first. Adding ranking here
  would couple 6.2 to the ranker spec, which is not yet authored.
- **D-7 — No XP / streak / gamification wiring on quiz_item review.**
  Today `study_service.review_card` calls `gamification_service.award_xp`
  on each non-Again rating (`study_service.py` ~line 540). Slice 6.2
  does NOT call `award_xp` from `review_quiz_item`. Rationale: the
  XP-on-quiz contract is its own product call (does quiz XP feed the
  same `gamification_stats.total_xp` as card XP, or does it get its
  own column? Does the streak count quiz reviews as activity?). Out of
  scope here; flagged in §3 Non-goals and OQ-4. Implementation slice
  MUST NOT add `award_xp` "for parity" — that would silently lock in a
  product call that hasn't been made.

## 12. Out of scope (explicit list per the prompt)

- Free-tier daily-card wall (write-side) on quiz_items — D-4.
- Persona-aware ranking on the daily queue — D-6 → slice 6.6.
- Lesson lookup endpoints (`GET /api/v1/lessons/...`) — slice 6.3.
- Admin authoring endpoints (`/admin/quiz-items/...`) — slice 6.4.
- FE consumer surface (hooks, pages, components) — D-5 → slice 6.3.
- Schema changes (any Alembic migration) — N7 STOP if a gap surfaces.
- XP / streak / gamification wiring on quiz_item review — D-7.
- Home-state / progress-dashboard dual-read against
  `quiz_item_progress` — slice 6.16 or hygiene slice.
- Cross-model critique on review outcomes — slice 6.5 / 6.13.5.
- Lifting `DailyStatus` to a shared module — slice 6.15 cleanup.
- Lifting `_next_local_midnight` to `app/utils/timezone.py` — only if
  it doesn't expand blast radius; defer to impl judgment.
- Lifting FSRS constants (`_STATE_TO_FSRS`, `_FSRS_TO_STATE`,
  `_scheduler`) to a shared module — same rationale; defer.

## 13. Open questions

> Questions the schema design surfaced but does NOT block this spec.
> Resolve in the implementation slice's pre-flight or in a follow-up.

- **OQ-1 — Daily goal value.** Today `study_service._DAILY_GOAL = 5`
  (audit §1.2). Phase 6's product intent for `_DAILY_GOAL` on quiz_items
  may differ — possible reasons to deviate: (a) lesson-card UX renders
  one quiz at a time, so 5 quiz_items could span fewer lessons than 5
  cards; (b) Phase 6 retention dashboard (slice 6.16) may want a
  different daily-volume baseline. Defaulting to 5 keeps queue-size
  parity with legacy; flag for chat-Claude / Dhamo decision before
  impl.
- **OQ-2 — Route path namespace.** Spec adopts `/api/v1/quiz-items`
  (kebab-case, mirrors `/api/v1/email-prefs`). Alternatives:
  `/api/v1/quiz` (shorter, but `quiz` could collide with future
  multi-quiz session endpoints), `/api/v1/study/v2` (signals legacy/new
  split, but `/study/v2` is awkward). No strong precedent on
  versioning sub-paths in the repo today. Defer to chat-Claude /
  Dhamo decision.
- **OQ-3 — Where to put `_next_local_midnight`.** Currently at
  `study_service.py:168` (module-private). Slice 6.2 needs it for
  `_compute_daily_quiz_status.resets_at`. Two options: (i) defensive
  shim import; (ii) lift to `app/utils/timezone.py`. (ii) is cleaner
  but expands blast radius (touches `study_service.py`). Defer to
  implementation-slice judgment; document the choice in the slice's
  final report.
- **OQ-4 — Quiz-item review XP / streak contract.** Whether quiz_item
  reviews count toward `gamification_stats.total_xp` or get a separate
  `quiz_xp` column; whether they count toward the streak. Defer; spec
  it as its own slice once Phase 6 surfaces enough quiz-item reviews
  to make the question concrete.
- **OQ-5 — Schema naming: `DailyQuizItem` vs `QuizItemQueueEntry` vs
  `DailyQuizCard`.** Spec adopts `DailyQuizItem` for symmetry with
  `DailyCardItem` (already in `app/schemas/study.py`). Alternative
  names available; defer to chat-Claude judgment if a stronger pattern
  emerges.

---

*End of slice 6.2 spec. Authored 2026-04-26 at HEAD `50e94d6`. Spec
basis: `docs/specs/phase-6/01-foundation-schema.md` + `docs/audits/phase-6-scout.md`
(commit `5b0aa23`). Next step: Mode 1 implementation slice executes
against this spec — files B-062 at execution time per R17.*
