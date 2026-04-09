# SPEC: FSRS Daily Review

**Spec #:** 05  
**Phase:** 1  
**Status:** Draft  
**Branch:** `feature/p1-05-fsrs-daily-review`

---

## Problem

Cards are in the database (spec #03) and readable via the API (spec #04), but there
is no mechanism to schedule, surface, or record individual user review sessions.
Without per-user scheduling state, the spaced-repetition promise of the product
cannot be delivered — every user would see every card every day with no memory of
what they already know.

---

## Solution

Introduce a `card_progress` table that stores per-user, per-card FSRS state.
Two new endpoints power the Daily 5 loop:

- `GET /api/v1/study/daily` — returns up to 5 cards due for the authenticated user
- `POST /api/v1/study/review` — accepts a user's rating for one card and advances
  its FSRS state

FSRS scheduling runs server-side via the `py-fsrs` library. The frontend receives
only the resulting `due_date` and state label; it never computes intervals.

---

## Acceptance Criteria

- [ ] **AC-1:** `GET /api/v1/study/daily` returns at most 5 cards whose
  `due_date <= NOW() UTC` for the authenticated user, ordered by `due_date ASC`
  (most overdue first). Cards the user has never touched appear as if their
  `due_date` is epoch zero (always due).

- [ ] **AC-2:** Free-plan users only receive cards from `category.source =
  "foundation"` in the daily queue. Pro/enterprise users receive cards from all
  categories. Plan-gate logic is identical to spec #04.

- [ ] **AC-3:** `POST /api/v1/study/review` with a valid `card_id` and `rating`
  (1–4) creates a `card_progress` row on first review, or updates the existing
  row, and returns the new FSRS state including the next `due_date`.

- [ ] **AC-4:** Rating `1` (Again) resets the card to `Learning` state and sets
  `due_date` to at most 10 minutes from now (governed by the FSRS learning step).

- [ ] **AC-5:** Rating `3` (Good) on a card in `Review` state increases
  `stability` and sets `due_date` to at least tomorrow.

- [ ] **AC-6:** Each successful call to `POST /api/v1/study/review` fires the
  PostHog event `card_reviewed` with `{ card_id, rating, state_after, time_spent_ms }`.

- [ ] **AC-7:** After all 5 daily cards are reviewed, the service fires the
  PostHog event `daily_review_completed` with `{ cards_reviewed, session_id }`.

- [ ] **AC-8:** `GET /api/v1/study/daily` returns `401` when the bearer token
  is absent or invalid. `POST /api/v1/study/review` returns `401` under the
  same condition.

- [ ] **AC-9:** `POST /api/v1/study/review` with a `card_id` belonging to a
  category the caller's plan does not permit returns `403`.

- [ ] **AC-10:** `POST /api/v1/study/review` with a non-existent `card_id`
  returns `404`.

---

## Data Model Changes

### New table: `card_progress`

One row per `(user_id, card_id)` pair. Created on first review; updated on
every subsequent review.

```sql
CREATE TABLE card_progress (
    id            VARCHAR(36)      PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id       VARCHAR(36)      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    card_id       VARCHAR(36)      NOT NULL REFERENCES cards(id) ON DELETE CASCADE,

    -- FSRS scheduler state (managed by py-fsrs)
    state         VARCHAR(20)      NOT NULL DEFAULT 'new',
                                   -- 'new' | 'learning' | 'review' | 'relearning'
    stability     FLOAT            NOT NULL DEFAULT 0.0,
    difficulty    FLOAT            NOT NULL DEFAULT 0.0,
    elapsed_days  FLOAT            NOT NULL DEFAULT 0.0,
    scheduled_days FLOAT           NOT NULL DEFAULT 0.0,
    reps          INTEGER          NOT NULL DEFAULT 0,
    lapses        INTEGER          NOT NULL DEFAULT 0,
    last_review   TIMESTAMP WITH TIME ZONE,
    due_date      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Metadata
    created_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_card_progress_user_card UNIQUE (user_id, card_id)
);

CREATE INDEX idx_card_progress_user_due
    ON card_progress (user_id, due_date ASC)
    WHERE state != 'new';

CREATE INDEX idx_card_progress_user_id ON card_progress (user_id);
```

**Column notes:**

| Column | Source | Description |
|--------|--------|-------------|
| `state` | `py-fsrs` `State` enum | Maps to: `State.New` → `"new"`, `State.Learning` → `"learning"`, `State.Review` → `"review"`, `State.Relearning` → `"relearning"` |
| `stability` | `py-fsrs` `Card.stability` | Expected days of memory half-life |
| `difficulty` | `py-fsrs` `Card.difficulty` | Intrinsic difficulty [1–10] |
| `elapsed_days` | `py-fsrs` `Card.elapsed_days` | Days since last review |
| `scheduled_days` | `py-fsrs` `Card.scheduled_days` | Days the scheduler targeted for this interval |
| `reps` | `py-fsrs` `Card.reps` | Total successful reviews |
| `lapses` | `py-fsrs` `Card.lapses` | Times the card was rated `Again` (1) |
| `last_review` | Set on write | UTC timestamp of the most recent review |
| `due_date` | `py-fsrs` `Card.due` | Next review datetime (UTC); drives the daily queue |

### Migration

Create via Alembic:
```
alembic revision --autogenerate -m "add card_progress table"
alembic upgrade head
```

No changes to existing `cards`, `categories`, `users`, or `subscriptions` tables.

---

## FSRS State Machine

The `py-fsrs` library drives all transitions. The service layer must never
compute intervals directly — it calls `fsrs.review_card(card, rating, now)` and
persists the returned `Card` object.

```
                            Rating: Again (1)
         ┌──────────────────────────────────────────────────────┐
         │                                                      │
         ▼                                                      │
      ┌─────┐  Any rating (first review)  ┌──────────┐         │
      │ New │ ─────────────────────────► │ Learning │         │
      └─────┘                             └──────────┘         │
                                               │               │
                                 Rating: Good  │               │
                                 or Easy       │               │
                                 (after step   ▼               │
                                  graduation) ┌────────┐       │
                                              │ Review │ ──────┘
                                              └────────┘
                                                   │
                                     Rating: Again │
                                                   ▼
                                           ┌────────────┐
                                           │ Relearning │
                                           └────────────┘
                                                   │
                                     Rating: Good  │
                                     or Easy       │
                                                   ▼
                                              ┌────────┐
                                              │ Review │
                                              └────────┘
```

**Transitions governed by `py-fsrs`:**

| From state | Rating | To state | `due_date` delta |
|------------|--------|----------|-----------------|
| `new` | Any | `learning` | ≤ 10 min (first learning step) |
| `learning` | Again (1) | `learning` | ≤ 10 min (reset step) |
| `learning` | Hard (2) | `learning` | ≤ 10 min (current step) |
| `learning` | Good (3) | `review` | ≥ 1 day (graduation) |
| `learning` | Easy (4) | `review` | ≥ 4 days (early graduation) |
| `review` | Again (1) | `relearning` | ≤ 10 min |
| `review` | Hard (2) | `review` | Shorter than Good interval |
| `review` | Good (3) | `review` | Interval × ~2–3 |
| `review` | Easy (4) | `review` | Longer than Good interval |
| `relearning` | Again (1) | `relearning` | ≤ 10 min |
| `relearning` | Good (3) or Easy (4) | `review` | Reduced interval |

The exact multipliers are internal to `py-fsrs` and must not be hardcoded in
application code. Always use the library return value.

---

## API Contract

### Auth

All endpoints require `Authorization: Bearer <access_token>` (JWT from
`/api/v1/auth/google`). Missing or invalid tokens return `401 Unauthorized`.

### Plan Gate Logic

Identical to spec #04:
```
is_free  := user.subscription is None
            OR user.subscription.status != "active"
            OR user.subscription.plan == "free"

allowed_category(category) :=
    NOT is_free  OR  category.source == "foundation"
```

---

### 1. `GET /api/v1/study/daily`

Return up to 5 cards that are due for review for the authenticated user.

**Request**

| Parameter | In     | Type   | Required | Description |
|-----------|--------|--------|----------|-------------|
| —         | header | string | yes      | `Authorization: Bearer <token>` |

**Behaviour**

1. Determine plan gate for the caller.
2. Fetch `card_progress` rows where `user_id = caller` AND `due_date <= NOW() UTC`
   AND the associated card's category passes the plan gate.
   Order by `due_date ASC`. Limit 5.
3. For cards the user has never reviewed (no `card_progress` row), they are
   implicitly always due. Fetch up to `5 - len(existing_due)` unreviewed cards
   from plan-accessible categories, ordered by `cards.created_at ASC`. This
   fills the queue when no overdue cards exist (bootstrapping new users).
4. Return the merged list (existing due first, then new cards), capped at 5.

**Response 200**

```json
{
  "cards": [
    {
      "card_id":      "<UUID>",
      "question":     "What is the CAP theorem?",
      "answer":       "CAP theorem states that a distributed system...",
      "difficulty":   "medium",
      "tags":         ["distributed-systems", "databases"],
      "category_id":  "<UUID>",
      "category_name": "System Design",
      "fsrs_state":   "review",
      "due_date":     "2026-04-09T08:00:00Z",
      "reps":         4,
      "lapses":       0
    }
  ],
  "total_due": 5,
  "session_id": "<UUID>"
}
```

`session_id` is a server-generated UUID for this batch; the client echoes it
in the `daily_review_completed` analytics event. For new cards (never reviewed),
`fsrs_state` is `"new"`, `due_date` is omitted (null), `reps` is 0, `lapses`
is 0.

**Empty queue**

```json
{
  "cards": [],
  "total_due": 0,
  "session_id": "<UUID>"
}
```

Returns `200`, never `404`.

**Error codes**

| Status | Condition |
|--------|-----------|
| 401    | Missing or invalid token |

**PostHog event fired on success (non-empty queue):**  
`daily_review_started` — `{ total_due, session_id }`

---

### 2. `POST /api/v1/study/review`

Submit a review rating for one card. Advances the card's FSRS state and
persists the result.

**Request body** (JSON)

```json
{
  "card_id":       "<UUID>",
  "rating":        3,
  "session_id":    "<UUID>",
  "time_spent_ms": 4200
}
```

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `card_id` | UUID string | yes | must exist in `cards` | Card being reviewed |
| `rating` | integer | yes | 1–4 | Again=1, Hard=2, Good=3, Easy=4 |
| `session_id` | UUID string | yes | — | Session ID from `GET /study/daily`; used for analytics grouping |
| `time_spent_ms` | integer | no | ≥ 0, ≤ 300_000 | Milliseconds spent on this card |

**Behaviour**

1. Validate `card_id` exists → 404 if not.
2. Check plan gate for caller against `card.category` → 403 if not allowed.
3. Load or create `card_progress` row for `(user_id, card_id)`.
4. If the row does not exist, create a new `py-fsrs` `Card()` in state `New`.
5. Call `fsrs.review_card(fsrs_card, Rating(rating), review_datetime=now_utc)`.
6. Map the returned `py-fsrs` `Card` fields back to `card_progress` columns.
7. Persist the updated `card_progress` row.
8. Fire PostHog event `card_reviewed`.
9. Return the updated FSRS state.

**Response 200**

```json
{
  "card_id":        "<UUID>",
  "fsrs_state":     "review",
  "stability":      6.21,
  "difficulty":     5.03,
  "due_date":       "2026-04-15T08:00:00Z",
  "reps":           5,
  "lapses":         0,
  "scheduled_days": 6
}
```

| Field | Type | Description |
|-------|------|-------------|
| `card_id` | UUID string | Echoed from request |
| `fsrs_state` | string | `"new"` \| `"learning"` \| `"review"` \| `"relearning"` |
| `stability` | float | Memory stability (days) |
| `difficulty` | float | Intrinsic card difficulty |
| `due_date` | ISO-8601 UTC | Next review datetime |
| `reps` | integer | Cumulative successful reviews |
| `lapses` | integer | Cumulative Again (1) ratings |
| `scheduled_days` | float | Interval the scheduler selected for this review |

**Error codes**

| Status | Condition |
|--------|-----------|
| 400    | `rating` not in [1, 4] |
| 400    | `time_spent_ms` < 0 or > 300,000 |
| 401    | Missing or invalid token |
| 403    | Card exists but belongs to a category caller's plan does not permit |
| 404    | No card with the given `card_id` |
| 422    | `card_id` is not a valid UUID format |

**PostHog event fired on success:**  
`card_reviewed` — `{ card_id, rating, state_after, time_spent_ms, session_id }`

---

## File Map

| File | Role |
|------|------|
| `app/models/card_progress.py` | SQLAlchemy ORM model for `card_progress` |
| `app/schemas/study.py` | Pydantic request/response schemas |
| `app/services/study_service.py` | FSRS logic; calls `py-fsrs`, persists results |
| `app/api/routes/study.py` | Route handlers; auth + plan gate; delegates to service |
| `alembic/versions/<hash>_add_card_progress_table.py` | Migration |
| `tests/test_study_service.py` | Unit tests for FSRS scheduling logic |
| `tests/test_study_api.py` | Integration tests for both endpoints |

---

## Edge Cases

- **No `card_progress` row yet:** treated as `state = "new"`, `due_date =
  epoch`. The card is always included in the daily queue until first reviewed.
- **User has reviewed fewer than 5 cards total:** the queue fills with
  unreviewed cards up to the 5-card limit so new users always get a queue.
- **All accessible cards reviewed and not yet due:** `GET /study/daily` returns
  `[]`. The UI must handle this gracefully ("Come back tomorrow").
- **Concurrent reviews of the same card:** the `UNIQUE(user_id, card_id)`
  constraint prevents duplicate rows. The last writer wins (no optimistic lock
  in this spec; contention is unlikely in a single-user context).
- **`time_spent_ms` omitted:** treated as 0 for analytics; does not affect
  FSRS scheduling.
- **Rating `1` (Again) on a brand-new card:** `py-fsrs` handles this correctly
  — it keeps the card in `Learning` state with a short step. Do not special-case
  this in the service.
- **Free-plan user whose subscription row is missing:** treat as free. Guard:
  `if user.subscription is None or user.subscription.status != "active"`.
- **`due_date` in the past by more than 30 days (very overdue card):** still
  returned normally; FSRS handles fuzz internally. No truncation needed.
- **`py-fsrs` version mismatch:** `py-fsrs>=3.0.0` is required. The `Rating`
  enum values are: `Again=1, Hard=2, Good=3, Easy=4`. Verify on upgrade.

---

## Dependencies

| Spec | Status |
|------|--------|
| #00 — PostgreSQL + pgvector | Done |
| #02 — Auth unification (`get_current_user`) | Done |
| #03 — User role + admin | Done |
| #03-card-extraction — Card + Category models, seeded data | Done |
| #04 — Cards API (plan gate logic) | Must be done first |
| `py-fsrs>=3.0.0` in `requirements.txt` | Must be added |

---

## Test Plan

### Unit tests — `tests/test_study_service.py`

All tests use an in-memory or test-database `card_progress` row and call the
service layer directly, **not** through HTTP. Mock `posthog.capture` to avoid
side effects.

**TC-01 — Good rating advances to Review state**
- Setup: `card_progress` row with `state="learning"`, `reps=2`.
- Action: call `study_service.submit_review(user_id, card_id, rating=3, ...)`.
- Assert: returned state is `"review"`, `due_date > now + timedelta(hours=23)`,
  `reps == 3`.

**TC-02 — Again rating on Review card moves to Relearning**
- Setup: `card_progress` row with `state="review"`, `stability=10.0`, `reps=5`.
- Action: call with `rating=1`.
- Assert: returned state is `"relearning"`, `due_date <= now + timedelta(minutes=11)`,
  `lapses == previous_lapses + 1`.

**TC-03 — First-ever review creates card_progress row**
- Setup: no `card_progress` row for `(user_id, card_id)`.
- Action: call with `rating=3`.
- Assert: a new `card_progress` row exists in the database, `reps == 1`,
  `state != "new"`.

**TC-04 — Daily queue returns at most 5 cards**
- Setup: 10 `card_progress` rows with `due_date` in the past for `user_id`.
- Action: call `study_service.get_daily_cards(user_id, plan="pro")`.
- Assert: returned list has exactly 5 items.

**TC-05 — Daily queue respects free-plan gate**
- Setup: 3 due cards in `source="foundation"` category, 3 due cards in a
  premium category, for `user_id`.
- Action: call `study_service.get_daily_cards(user_id, plan="free")`.
- Assert: all returned cards belong to `source="foundation"` categories; list
  length ≤ 3.

**TC-06 — New user queue fills with unreviewed cards**
- Setup: user has 0 `card_progress` rows; 20 cards exist in accessible
  categories.
- Action: call `study_service.get_daily_cards(user_id, plan="pro")`.
- Assert: 5 cards returned, all with `fsrs_state="new"`.

**TC-07 — Easy rating produces longer interval than Good**
- Setup: `card_progress` row with `state="review"`, same initial conditions,
  reviewed twice (once with `rating=3`, once with `rating=4`), comparing the
  two resulting `scheduled_days`.
- Action: run two separate calls from an identical starting state.
- Assert: `scheduled_days` from `rating=4` > `scheduled_days` from `rating=3`.

**TC-08 — Again rating on Review card resets due_date to near-future**
- Setup: `card_progress` row with `state="review"`, `due_date` yesterday.
- Action: call with `rating=1`.
- Assert: new `due_date` is within 15 minutes of `now`.

**TC-09 — PostHog card_reviewed event is fired with correct payload**
- Setup: mock `posthog.capture`.
- Action: call `study_service.submit_review(user_id, card_id, rating=3,
  time_spent_ms=2500, session_id=session_uuid)`.
- Assert: `posthog.capture` called once with event `"card_reviewed"` and
  properties `{ "card_id": card_id, "rating": 3, "state_after": "review",
  "time_spent_ms": 2500 }`.

**TC-10 — review on non-existent card raises 404-equivalent**
- Setup: no card with given UUID in `cards` table.
- Action: call `study_service.submit_review(...)`.
- Assert: service raises `CardNotFoundError` (or equivalent) that the route
  handler maps to HTTP 404.

### Integration tests — `tests/test_study_api.py`

Use `httpx.AsyncClient` against the full FastAPI app with a test database.

- **`test_daily_unauthenticated`**: `GET /api/v1/study/daily` without token → 401.
- **`test_review_unauthenticated`**: `POST /api/v1/study/review` without token → 401.
- **`test_daily_empty_for_new_user`**: new user with no cards due → 200, but queue
  fills with unreviewed cards (not empty for first-time users).
- **`test_review_invalid_rating`**: `rating=5` → 400.
- **`test_review_free_user_premium_card`**: free-plan user submits review for a
  card in a non-foundation category → 403.

### Manual verification

1. Seed a free-plan user and a pro-plan user in the test DB.
2. `GET /api/v1/study/daily` with free token — confirm only foundation-category
   cards appear.
3. `POST /api/v1/study/review` with `rating=3` — confirm returned `due_date` is
   tomorrow or later.
4. `POST /api/v1/study/review` with `rating=1` — confirm returned `due_date` is
   within 10 minutes.
5. Submit 5 reviews in sequence — confirm PostHog receives `card_reviewed` ×5
   and `daily_review_completed` ×1.
6. Call `GET /api/v1/study/daily` again after all 5 cards reviewed — confirm
   queue returns 0 cards (or new unreviewed cards if queue was filled with new
   cards previously).
