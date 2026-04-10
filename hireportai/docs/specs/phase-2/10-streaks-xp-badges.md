# SPEC: Streaks, XP & Badges

## Status: Draft

## Problem
Daily-return habit is the single largest driver of long-term retention for a
spaced-repetition product. Without visible progress signals and loss-aversion
hooks, users churn after the novelty of the first scan wears off. We need a
gamification layer that (a) rewards every completed review, (b) makes a missed
day feel costly, and (c) gives users collectible milestones that surface social
proof and self-efficacy.

## Solution
Introduce a `gamification_stats` row per user that tracks current streak,
longest streak, total XP, and last activity date. Award XP automatically on
every review, quiz, and completed Daily 5. Increment the streak on the first
qualifying activity of each calendar day; reset on miss; allow Pro users a
weekly auto-freeze. Award badges when threshold conditions are met. Expose
read + write endpoints under `/api/v1/gamification/*`.

## Acceptance Criteria
- [ ] AC-1: Given a user reviews their first card of the day, when the review
      is persisted, then `current_streak` increments by 1 and `last_active_date`
      is set to today (UTC).
- [ ] AC-2: Given a user reviewed yesterday but not today, when the nightly
      streak job runs at 00:05 UTC, then `current_streak` is reset to 0 and a
      `streak_broken` event is fired — UNLESS the user is Pro and has an
      unused weekly freeze, in which case the streak is preserved and the
      freeze is consumed.
- [ ] AC-3: Given a user completes a card review, when XP is awarded, then
      `total_xp` increases by exactly 10 and a `gamification_stats` row exists.
- [ ] AC-4: Given a user crosses an XP or streak threshold tied to a badge,
      when stats are updated, then the badge is recorded in `user_badges` and
      a `badge_earned` event is fired exactly once.
- [ ] AC-5: `GET /api/v1/gamification/stats` returns the user's stats and the
      list of earned badges in <150ms p95.
- [ ] AC-6: `POST /api/v1/gamification/award-xp` is idempotent per
      `(user_id, source_type, source_id)` — replaying the same event does not
      double-award.
- [ ] AC-7: `longest_streak` is monotonic and equals
      `max(longest_streak, current_streak)` after every update.

## Data Model Changes

### Table: `gamification_stats`
| Column            | Type         | Notes                                  |
|-------------------|--------------|----------------------------------------|
| `user_id`         | UUID PK FK   | One row per user; FK → `users.id`      |
| `current_streak`  | INT          | Default 0, ≥ 0                         |
| `longest_streak`  | INT          | Default 0, ≥ 0                         |
| `total_xp`        | INT          | Default 0, ≥ 0                         |
| `last_active_date`| DATE         | Nullable; UTC calendar date            |
| `freezes_available` | INT        | Default 0; reset to 1 weekly for Pro   |
| `freeze_week_start` | DATE       | Monday UTC of current freeze cycle     |
| `created_at`      | TIMESTAMPTZ  | Default now()                          |
| `updated_at`      | TIMESTAMPTZ  | Default now(), updated on write        |

### Table: `user_badges`
| Column        | Type        | Notes                                       |
|---------------|-------------|---------------------------------------------|
| `id`          | UUID PK     |                                             |
| `user_id`     | UUID FK     | → `users.id`                                |
| `badge_id`    | TEXT        | One of the static badge IDs below           |
| `earned_at`   | TIMESTAMPTZ | Default now()                               |
| UNIQUE        |             | `(user_id, badge_id)` — one badge per user  |

### Table: `xp_ledger` (idempotency log)
| Column        | Type        | Notes                                       |
|---------------|-------------|---------------------------------------------|
| `id`          | UUID PK     |                                             |
| `user_id`     | UUID FK     |                                             |
| `amount`      | INT         | XP delta (positive)                         |
| `source_type` | TEXT        | `review` \| `quiz` \| `daily_complete`      |
| `source_id`   | TEXT        | Review ID, quiz ID, or `YYYY-MM-DD` for day |
| `created_at`  | TIMESTAMPTZ |                                             |
| UNIQUE        |             | `(user_id, source_type, source_id)`         |

Alembic migration creates all three tables and backfills a
`gamification_stats` row for every existing user with zeros.

## Badge Definitions
Static, code-defined catalog (no admin CRUD in this spec).

| `badge_id`         | Name              | Earn Condition                          |
|--------------------|-------------------|-----------------------------------------|
| `first_review`     | First Step        | First card review ever                  |
| `streak_3`         | On a Roll         | `current_streak` reaches 3              |
| `streak_7`         | One Week Strong   | `current_streak` reaches 7              |
| `streak_30`        | Habit Formed      | `current_streak` reaches 30             |
| `streak_100`       | Centurion         | `current_streak` reaches 100            |
| `xp_100`           | Apprentice        | `total_xp` ≥ 100                        |
| `xp_500`           | Journeyman        | `total_xp` ≥ 500                        |
| `xp_2000`          | Expert            | `total_xp` ≥ 2000                       |
| `xp_10000`         | Master            | `total_xp` ≥ 10000                      |
| `daily_5_first`    | Daily Driver      | First Daily 5 fully completed           |
| `quiz_perfect`     | Sharpshooter      | First quiz with 100% correct            |

Badges are evaluated after every stats mutation. Re-evaluation is cheap
because the catalog is small and conditions are pure functions of stats.

## XP Award Rules
| Source             | Amount | Trigger                                            |
|--------------------|--------|----------------------------------------------------|
| Card review        | 10 XP  | Each successful review submission                  |
| Quiz answer        | 25 XP  | Each correct quiz answer                           |
| Daily 5 completion | 50 XP  | Bonus when all 5 of the day's reviews are done     |

Awards flow through `gamification_service.award_xp()`, which writes the
`xp_ledger` row first (unique constraint provides idempotency), then updates
`gamification_stats.total_xp` in the same transaction. Replays return the
existing ledger row without mutating stats.

## Streak Rules
- **Increment**: On the first XP-earning activity of a UTC calendar day,
  if `last_active_date == yesterday`, `current_streak += 1`. If
  `last_active_date < yesterday` or NULL, `current_streak = 1`. Set
  `last_active_date = today`. Update `longest_streak` if needed. Fire
  `streak_incremented`.
- **Reset**: A nightly job at 00:05 UTC scans users whose
  `last_active_date < yesterday` and `current_streak > 0`. For non-Pro users,
  set `current_streak = 0` and fire `streak_broken`. Stats are also
  lazy-checked on the next read so users who don't trigger the job still see
  the correct value.
- **Freeze (Pro only)**: At the start of each ISO week (Monday UTC), Pro
  users get `freezes_available = 1` and `freeze_week_start = monday`. When the
  reset job would otherwise break a Pro user's streak and
  `freezes_available > 0`, decrement `freezes_available`, leave the streak
  intact, and fire `streak_frozen` instead of `streak_broken`. Free users are
  unaffected by freezes.
- **Timezone**: All boundaries use UTC in v1. Per-user timezone support is
  out of scope and tracked separately.

## API Contract

### `GET /api/v1/gamification/stats`
Auth: `Depends(get_current_user)`.

Response `200`:
```json
{
  "user_id": "uuid",
  "current_streak": 7,
  "longest_streak": 14,
  "total_xp": 1240,
  "last_active_date": "2026-04-09",
  "freezes_available": 1,
  "badges": [
    { "badge_id": "streak_7", "name": "One Week Strong", "earned_at": "2026-04-08T10:12:00Z" },
    { "badge_id": "xp_500",  "name": "Journeyman",      "earned_at": "2026-04-05T18:44:00Z" }
  ]
}
```
Errors: `401` unauthenticated.

### `POST /api/v1/gamification/award-xp`
Auth: `Depends(get_current_user)`. Server-internal callers (the review and
quiz services) are the primary consumers; the route exists for explicit
client-driven awards (e.g., Daily 5 completion confirmation) and for testing.

Request:
```json
{
  "source_type": "review",          // "review" | "quiz" | "daily_complete"
  "source_id":   "review_uuid",     // or quiz_uuid, or "YYYY-MM-DD"
  "amount":      10                  // optional override; server validates against rule table
}
```
The server is the source of truth for XP amounts. If `amount` is provided
and disagrees with the rule for `source_type`, the request is rejected with
`422` to prevent client tampering.

Response `200`:
```json
{
  "awarded": 10,
  "duplicate": false,
  "stats": { "...same shape as GET stats..." },
  "newly_earned_badges": ["streak_3"]
}
```
On replay (`duplicate: true`), `awarded` is `0` and `newly_earned_badges`
is empty.

Errors:
- `401` unauthenticated
- `422` invalid `source_type` or amount/rule mismatch
- `404` `source_id` does not resolve to a real review/quiz owned by the user

## Analytics Events
- `xp_awarded` — `{ amount, source_type, total_xp_after }`
- `streak_incremented` — `{ new_length, user_id }`
- `streak_broken` — `{ previous_length, user_id }`
- `streak_frozen` — `{ length, freezes_remaining }`
- `badge_earned` — `{ badge_id, badge_name }`

## Edge Cases
- User reviews twice in the same day → streak unchanged on the second review,
  XP still awarded normally.
- User upgrades to Pro mid-week → freeze becomes available immediately and is
  valid for the remainder of the current ISO week.
- User downgrades from Pro → unused freezes are discarded; an in-flight freeze
  already consumed for this week stands.
- Clock skew / late nightly job → lazy check on next stats read fixes it.
- Backfill: existing users get a zeroed `gamification_stats` row on migration;
  no historical XP is reconstructed.
- Idempotency collision across users → impossible because the unique key
  includes `user_id`.

## Dependencies
- Phase-1 review pipeline (source of `review` XP events)
- Phase-2 quiz feature (source of `quiz` XP events) — soft dep; quiz XP can
  ship later without blocking this spec
- Stripe subscription state (to determine Pro for freeze logic) — already in
  place from Phase-1 payments work
- PostHog instrumentation — already in place

## Test Plan
- **Unit tests**:
  - `award_xp` writes ledger + updates stats; replay is a no-op
  - Streak increment/reset/freeze state machine across day boundaries
  - Badge evaluator returns correct newly-earned set for each threshold
  - Pro freeze consumes exactly one per week, resets on Monday UTC
- **Integration tests**:
  - `GET /stats` for new user returns zeros and empty badges
  - `POST /award-xp` happy path, duplicate replay, cross-user isolation
  - Auth failure (`401`) on both endpoints
  - Validation error (`422`) on bad `source_type` and amount mismatch
  - Nightly reset job: free user breaks, Pro user freezes
- **Manual verification**:
  - Review a card → stats endpoint reflects +10 XP and streak = 1
  - Skip a day on a free account → streak resets next morning
  - Skip a day on a Pro account with a freeze → streak preserved, freeze gone
  - Cross threshold for `streak_7` → badge appears in response and PostHog
