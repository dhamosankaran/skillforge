# SPEC: Mission Mode — Time-Bound Study Sprints

## Status: Draft

## Problem
Users preparing for interviews need a structured, deadline-driven study plan.
Without one, they review cards aimlessly with no pacing toward a target date.
Mission Mode gives them a countdown-based sprint: pick categories, set a date,
and let the system distribute cards across the remaining days using FSRS
priority ordering.

## Solution
A mission is a time-boxed commitment. The user chooses categories, a target
date, and the system computes a daily card target. Each day the user pulls
their mission cards (FSRS-prioritized from selected categories) and marks them
complete. The mission tracks progress per day and ends on the target date or
when all cards are covered.

---

## Data Model

### `missions` table

| Column          | Type                     | Constraints                          | Notes                                      |
|-----------------|--------------------------|--------------------------------------|--------------------------------------------|
| `id`            | `String(36)` PK          | `UUIDPrimaryKeyMixin`                |                                            |
| `user_id`       | `String(36)` FK → users  | `NOT NULL`, `ON DELETE CASCADE`, idx | One user can have multiple missions        |
| `title`         | `String(200)`            | `NOT NULL`                           | User-provided label, e.g. "Google SDE-2"   |
| `target_date`   | `Date`                   | `NOT NULL`                           | Deadline (inclusive)                        |
| `daily_target`  | `Integer`                | `NOT NULL`                           | Computed: `ceil(total_cards / days_remaining)` — recalculated on missed days |
| `status`        | `String(20)`             | `NOT NULL`, default `active`         | `active` · `completed` · `abandoned`       |
| `created_at`    | `DateTime(tz)`           | `TimestampMixin`                     |                                            |
| `updated_at`    | `DateTime(tz)`           | `TimestampMixin`                     |                                            |

**Indexes:** `ix_missions_user_id`, `ix_missions_status`

### `mission_categories` (association table)

| Column        | Type                        | Constraints                          |
|---------------|-----------------------------|--------------------------------------|
| `mission_id`  | `String(36)` FK → missions  | PK, `ON DELETE CASCADE`             |
| `category_id` | `String(36)` FK → categories| PK, `ON DELETE RESTRICT`            |

Composite PK on `(mission_id, category_id)`.

### `mission_days` table

| Column           | Type                     | Constraints                              | Notes                              |
|------------------|--------------------------|------------------------------------------|------------------------------------|
| `id`             | `String(36)` PK          | `UUIDPrimaryKeyMixin`                    |                                    |
| `mission_id`     | `String(36)` FK → missions| `NOT NULL`, `ON DELETE CASCADE`, idx    |                                    |
| `day_number`     | `Integer`                | `NOT NULL`                               | 1-based index                      |
| `date`           | `Date`                   | `NOT NULL`                               | Calendar date for this day         |
| `cards_target`   | `Integer`                | `NOT NULL`                               | Target for this specific day       |
| `cards_completed`| `Integer`                | `NOT NULL`, default `0`                  | Incremented as user reviews cards  |

**Unique:** `(mission_id, day_number)`, `(mission_id, date)`

### Alembic migration note
Single migration: `alembic revision --autogenerate -m "add missions and mission_days tables"`.
Creates all three tables. No changes to existing tables.

---

## Scheduling Algorithm

### On mission creation
1. Query total eligible cards across selected `category_ids` for this user.
2. `days_remaining = (target_date - today).days + 1` (inclusive of today and target date).
3. `daily_target = ceil(total_cards / days_remaining)`.
4. Pre-generate `mission_days` rows for every calendar day from today through `target_date`.
   Each row gets `cards_target = daily_target`.
5. Save mission with computed `daily_target`.

### Daily card pull
1. Find today's `mission_day` row.
2. Query `card_progress` for cards in the mission's categories, ordered by:
   - `due_date <= now()` first (overdue cards have top priority)
   - `state = 'new'` second (unseen cards next)
   - Ascending `due_date` (soonest-due among remaining)
3. Return up to `cards_target - cards_completed` cards for the day.
4. After each card review, increment `cards_completed` on the mission_day row.

### Rebalancing on missed days
When a user opens their mission and there are past `mission_day` rows with
`cards_completed < cards_target`:
1. Sum the deficit: `deficit = SUM(cards_target - cards_completed)` for all past incomplete days.
2. `remaining_days = days from today through target_date (inclusive)`.
3. Redistribute: `new_daily_target = ceil((remaining_cards + deficit) / remaining_days)`.
4. Update `cards_target` on all future (including today) `mission_day` rows.
5. Update `missions.daily_target` to the new value.

### Mission completion
- Status → `completed` when all cards across all categories have been reviewed
  at least once during the mission, OR when `target_date` passes.
- Status → `abandoned` only via explicit user action (DELETE/abandon endpoint).

---

## API Contract

Base path: `/api/v1/missions`
All endpoints require `Depends(get_current_user)`.

### POST `/` — Create Mission

**Request:**
```json
{
  "title": "Google SDE-2 Prep",
  "target_date": "2026-04-24",
  "category_ids": ["uuid-1", "uuid-2"]
}
```

**Response:** `201 Created`
```json
{
  "id": "mission-uuid",
  "title": "Google SDE-2 Prep",
  "target_date": "2026-04-24",
  "category_ids": ["uuid-1", "uuid-2"],
  "daily_target": 12,
  "total_cards": 168,
  "days_remaining": 14,
  "status": "active",
  "created_at": "2026-04-10T10:00:00Z"
}
```

**Errors:**
- `400` — `target_date` in the past, no `category_ids`, categories have 0 cards
- `409` — User already has an active mission (limit: 1 active mission at a time)

---

### GET `/` — List User's Missions

**Response:** `200 OK`
```json
{
  "missions": [
    {
      "id": "mission-uuid",
      "title": "Google SDE-2 Prep",
      "target_date": "2026-04-24",
      "daily_target": 12,
      "status": "active",
      "progress_pct": 35.7,
      "days_remaining": 10,
      "created_at": "2026-04-10T10:00:00Z"
    }
  ]
}
```

---

### GET `/{mission_id}` — Mission Detail

**Response:** `200 OK`
```json
{
  "id": "mission-uuid",
  "title": "Google SDE-2 Prep",
  "target_date": "2026-04-24",
  "category_ids": ["uuid-1", "uuid-2"],
  "daily_target": 12,
  "total_cards": 168,
  "days_remaining": 10,
  "status": "active",
  "progress_pct": 35.7,
  "days": [
    {
      "day_number": 1,
      "date": "2026-04-10",
      "cards_target": 12,
      "cards_completed": 12
    },
    {
      "day_number": 2,
      "date": "2026-04-11",
      "cards_target": 12,
      "cards_completed": 8
    }
  ],
  "created_at": "2026-04-10T10:00:00Z"
}
```

**Errors:** `404` — mission not found or not owned by user

---

### GET `/{mission_id}/today` — Daily Card Pull

Triggers rebalancing if missed days exist, then returns today's cards.

**Response:** `200 OK`
```json
{
  "mission_id": "mission-uuid",
  "day_number": 5,
  "date": "2026-04-14",
  "cards_target": 14,
  "cards_completed": 3,
  "cards": [
    {
      "id": "card-uuid",
      "question": "Explain CAP theorem",
      "answer": "...",
      "category": "System Design",
      "difficulty": "medium"
    }
  ]
}
```

**Errors:** `404`, `410 Gone` — mission already completed/abandoned

---

### PATCH `/{mission_id}` — Update Mission

Only `title` and `target_date` are mutable. Changing `target_date` triggers
rebalancing.

**Request:**
```json
{
  "title": "Updated Title",
  "target_date": "2026-04-28"
}
```

**Response:** `200 OK` (full mission detail)

**Errors:** `400` — new `target_date` in the past, `404`, `409` — mission not active

---

### DELETE `/{mission_id}` — Abandon Mission

Sets `status = 'abandoned'`. Does not delete data (needed for analytics).

**Response:** `200 OK`
```json
{
  "id": "mission-uuid",
  "status": "abandoned"
}
```

**Errors:** `404`, `409` — mission already completed/abandoned

---

## Analytics Events (PostHog)

| Event                    | Properties                                        |
|--------------------------|---------------------------------------------------|
| `mission_created`        | `days`, `categories`, `total_cards`, `daily_target`|
| `mission_day_completed`  | `day_number`, `cards_done`, `days_remaining`       |
| `mission_completed`      | `total_days`, `coverage_pct`                       |
| `mission_abandoned`      | `day_abandoned`, `reason`                          |

---

## Edge Cases
- **1-day mission:** `daily_target = total_cards`. Valid but warn in UI.
- **0 eligible cards:** Reject with `400` at creation.
- **All cards already mastered:** Still include them; FSRS will schedule review.
- **User adds cards to a category mid-mission:** Next rebalance picks them up
  automatically (total_cards is recomputed from live DB).
- **target_date is today:** Valid; single-day sprint.
- **Concurrent review sessions:** `cards_completed` increment uses
  `UPDATE ... SET cards_completed = cards_completed + 1` (atomic).

## Dependencies
- Spec #05 (FSRS daily review) — card_progress table and FSRS scheduling
- Spec #06 (category CRUD) — categories table
- Spec #10 (streaks/XP) — mission card reviews should award XP and count
  toward daily streaks

## Test Plan
- **Unit tests:** Scheduling algorithm (daily_target calculation, rebalancing,
  deficit redistribution), mission lifecycle state transitions
- **Integration tests:** Create → pull → review → complete flow,
  rebalancing after missed days, 409 on duplicate active mission
- **Manual verification:** Create a 7-day mission, review for 3 days,
  skip 1 day, verify rebalancing, complete mission
