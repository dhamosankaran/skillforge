# P5-S18b — State-Aware HomeDashboard Variants

**Status:** Draft (spec only — no code yet; implementation lands as P5-S18c)
**Owner:** Dhamo
**Created:** 2026-04-18
**Phase:** 5D (persona-aware surface)
**Depends on:** P5-S18 (HomeDashboard + widget catalog shipped — commit `5e1f56c`, spec #35)
**Downstream slice:** P5-S18c (implementation of this spec; Interview-Prepper guided checklist layers on top)
**Related locked decisions:** 2026-04-18 daily-review cap (`_DAILY_LIMIT=20` post-S22) is unrelated to state evaluation and not referenced here.
**Source:** `claude-code-prompts-all-phases-v2.2-patch.md` §P5-S18b (chat-Claude project knowledge; not checked into repo). This spec is the audited, code-grounded amendment of that starter.

## 1. Problem Statement

P5-S18 shipped a persona-aware home with a fixed widget grid per persona. Every Interview-Prepper sees the same four widgets in the same order, regardless of whether their interview is in 14 days or yesterday; every Career-Climber sees the same four widgets, regardless of whether their streak is 47 days or they haven't reviewed a card in two weeks. The widget content adapts (`total_due`, `current_streak`) but the layout is blind to user state — the urgency surface is wasted when the primary call-to-action is not the most time-sensitive action the user could take.

S18b adds a state-detection layer so the top render slot on `/home` surfaces the single most time-sensitive signal available — a streak about to break, a mission past its target date, a resume that's gone stale since the last scan. The persona-driven widget grid from S18 remains as the secondary layout; state-awareness promotes one widget (or inserts a new one) into a priority slot above it.

S18 left three things incomplete that this spec resolves: (a) no backend endpoint serves home-page state — every widget fetches its own data; (b) no priority ordering exists, so when two conditions are true (e.g., mission_overdue + streak_at_risk) there's no deterministic answer for which renders first; (c) no cache layer means a naive state evaluator would fan out to 6+ services on every `/home` mount.

## 2. Goals / Non-Goals

### Goals

- Evaluate a user's home-page state on a single backend call and return a priority-ordered list of active states.
- Promote one widget into a priority slot based on the top state, above the S18 persona grid.
- Keep the S18 static persona grid as the secondary layout — no state-awareness redesign of existing widgets.
- Cache state evaluation so `/home` remains under a performance budget (see §6).
- Fall back silently to the S18 layout on any state-evaluator failure — the home page must not white-screen on a state-eval 500.

### Non-Goals

- **Catch-up mode** for FSRS backlog — deferred per 2026-04-18 locked decision (Phase 6 pending data).
- **Persona switch UX** — deferred per spec #34 §Out of Scope; S18 `InterviewTargetWidget` stays display-only.
- **Team features waitlist component** — deferred per S18-flag; `TeamComingSoonWidget` stays action-less.
- **Widget-level analytics** (`widget_opened`, etc.) — still deferred per spec #35 §Out of Scope.
- **State-aware redesign of S18 widgets** — this spec *adds* a priority slot; existing widgets' empty/loading/error contracts are unchanged.
- **Time-of-day or localized greeting copy** — static `Welcome back, <first name>.` from S18 is unchanged.
- **User-configurable state thresholds** (e.g., "notify me when streak < 10h") — not planned.
- **Email/push notification side-effects** from state evaluation — state eval is read-only.

## 3. State Catalog

Six states, audited against current schema. (Two additional states — `new_pro_member` and `needs_persona_refresh` — were considered and deferred to spec #41; see §10.)

| State | Trigger (precise predicate) | Data needed | Priority | Widget | Mutually exclusive with |
|---|---|---|---|---|---|
| `mission_overdue` | `mission_service.get_active_mission()` returns a mission AND `mission.target_date < today_utc()` | Mission row (existing) | **1** | `MissionOverdueWidget` (new) | `mission_active` |
| `streak_at_risk` | `GamificationStats.current_streak >= 3` AND `MAX(CardProgress.last_reviewed) < now - 18h` | GamificationStats + CardProgress aggregate | **2** | `StreakAtRiskWidget` (new) | — |
| `mission_active` | `mission_service.get_active_mission()` returns a mission AND `target_date >= today_utc()` | Mission row (existing) | **3** | Reuses S18 `CountdownWidget` (promoted to priority slot) | `mission_overdue` |
| `resume_stale` | `MAX(TrackerApplicationModel.created_at WHERE user_id=X) < now - 21d` AND at least one scan exists (i.e., non-null MAX) | TrackerApplicationModel aggregate | **4** | `ResumeStaleWidget` (new) | — |
| `inactive_returner` | `GamificationStats.last_active_date` between `today - 30d` and `today - 7d` (inclusive) AND `GamificationStats.longest_streak >= 1` (i.e., had prior activity). **Note:** the suppress-on-recent-reminder-email refinement originally proposed in Q3 is deferred — no email-send timestamp column exists today (see §11 Q3). | GamificationStats (existing) | **5** | `WelcomeBackWidget` (new) | `first_session_done` |
| `first_session_done` | User has the `first_review` badge AND `SUM(CardProgress.reps) <= 3` across all cards (newly active, not fully ramped) | `UserBadge WHERE badge_id='first_review'` + `SUM(CardProgress.reps)` | **6** | `FirstSessionWidget` (new) | `inactive_returner` |

**Notes:**
- Priority 1 (highest) renders in the priority slot. Lower-priority states that are also active are returned in `states[]` but do not render widgets in this spec — they are available for future slices (e.g., a toast layer, or a secondary-priority slot).
- Mutually-exclusive pairs are enforced in the evaluator — if both conditions would match, only the higher-priority one is emitted. This is deterministic and testable.
- `mission_overdue` beats `streak_at_risk` on priority because a missed interview date is a harder fail than a soft streak break.
- The `inactive_returner` window is bounded at 30 days so users who have been gone for months (different cohort — likely churned) do not trigger a "welcome back" widget; they fall through to the S18 static layout.

## 4. Priority + Conflict Resolution

When multiple states are active, they are returned in `states[]` sorted by priority (lowest number = highest priority = first in array). The frontend renders the widget for `states[0]` in the priority slot; `states[1..]` are exposed but do not drive UI in S18c.

**Full priority order (1 = highest):**

1. `mission_overdue`
2. `streak_at_risk`
3. `mission_active`
4. `resume_stale`
5. `inactive_returner`
6. `first_session_done`

**Mutual-exclusion rules (enforced in the evaluator):**

- `mission_active` ⊕ `mission_overdue` — a single mission is either active-and-on-track or active-and-overdue; never both. The evaluator checks `target_date` after confirming an active mission exists and emits exactly one.
- `inactive_returner` ⊕ `first_session_done` — both are "welcome-back / onboarding" flavors; they overlap when a barely-started user goes dormant. If both match, the higher-priority `inactive_returner` wins (re-engaging a lapsed user is more urgent than celebrating a first session that's already history).

**Empty-state:** if no state is active, `states[]` is empty and the frontend renders the S18 static layout with no priority slot. This is the common case for an engaged user in the middle of a streak.

## 5. API Contract

New endpoint.

**`GET /api/v1/home/state`**

- **Auth:** required (`Depends(get_current_user)` — existing pattern).
- **Rate limit:** follows global default (100 req/min) — no custom limit.
- **Response body:**

```ts
{
  persona: "interview_prepper" | "career_climber" | "team_lead",
  states: string[],  // ordered by priority, highest first; empty array if no states active
  context: {
    current_streak: number,
    last_review_at: string | null,          // ISO-8601 UTC
    active_mission_id: string | null,
    mission_target_date: string | null,     // ISO-8601 date (no time)
    last_scan_date: string | null,          // ISO-8601 UTC
    plan: "free" | "pro" | "enterprise",
    last_activity_at: string | null         // ISO-8601 UTC; computed as GREATEST(last_review_at, last_scan_date)
  }
}
```

- **Error handling:**
  - On any data-source failure, the endpoint returns **HTTP 200** with `states: []` and a partial `context` populated with whatever fields resolved successfully (nulls for the rest). The failure is logged (Sentry) but not surfaced to the client.
  - On auth failure, standard 401 (no body change).
  - Frontend treats `states: []` identically to "no states active" — renders S18 layout.
- **Caching:** see §6.

**Response contract notes:**

- `context` fields are always present in the response shape (never omitted), but values may be null if the underlying data doesn't exist or failed to resolve. This keeps TypeScript types stable.
- The response shape is additive — fields required by future state additions (e.g., `plan_changed_at` when spec #41 ships `new_pro_member`) will be added without removing existing fields.

## 6. Performance + Caching

**Locked two-tier budget** (resolves v2.2-patch's flat 100ms AC, which was unachievable on a cold path with 5–6 aggregate queries):

- **Warm-cache p95: ≤ 100ms** (Redis hit; the common case).
- **Cold-cache p95: ≤ 250ms** (first request per user per TTL window).

The two-tier budget still meets the user-perceived "no spinner on /home" bar because the home page renders the S18 static layout during fetch (the priority slot is absent until the response resolves).

**Cold-request query cost (no cache):**

1. `GamificationStats` by user_id — 1 indexed lookup (~2ms).
2. `MAX(CardProgress.last_reviewed) WHERE user_id=X` — indexed aggregate (~5ms; `card_progress.user_id` indexed).
3. `mission_service.get_active_mission()` — existing call (~3ms).
4. `MAX(TrackerApplicationModel.created_at) WHERE user_id=X` — indexed aggregate (~3ms).
5. `Subscription` by user_id — 1 indexed lookup (~2ms, for `plan` field in response context).
6. `UserBadge WHERE user_id=X AND badge_id='first_review'` EXISTS + `SUM(CardProgress.reps)` — 2 lookups (~5ms combined).

Cold-path upper bound: ~20ms of DB + serialization + eval logic → ~80–120ms typical. 250ms p95 has comfortable headroom for tail-latency queries.

**Redis cache:**

- **Key:** `home_state:{user_id}` (scoped per user; no query-param variation).
- **Value:** serialized JSON of the full response body.
- **TTL:** 60 seconds.
- **Rationale for 60s:** state transitions are driven by user actions — all of which fire cache-invalidation events (below). The 60s TTL is the floor for "something changed externally and no event fired" (e.g., a clock tick advancing "last_review 17h ago" to "last_review 18h+ ago" could flip `streak_at_risk`; the next fetch ≤60s later picks it up).

**Cache-invalidation sites (enumerated by file path — implementation slice must touch all five):**

| Event | File | Trigger point | Call |
|---|---|---|---|
| `card_reviewed` | `hirelens-backend/app/services/study_service.py` | End of `review_card()` after DB flush, alongside existing `award_xp` call | `home_state_service.invalidate(user_id)` |
| `mission_lifecycle` | `hirelens-backend/app/services/mission_service.py` | End of `create_mission()` (line ~211) and `complete_mission_day()` (line ~470). (No `abandon_mission` function exists in the codebase as of commit 55ac7bd; if one is added, mirror the hook.) | same |
| `scan_completed` | `hirelens-backend/app/api/routes/analyze.py` (line ~234) | After successful scan, alongside existing auto-tracker upsert (post spec #5 amendment). (`hirelens-backend/app/api/v1/routes/analyze.py` is a re-export shim — hook lives with the actual handler.) | same |
| `plan_changed` | `hirelens-backend/app/services/payment_service.py` | Inside `_handle_checkout_completed()` and `_handle_subscription_deleted()` after plan flip | same (useful for future plan-dependent states even though no current state reads plan-change timestamp) |
| `persona_updated` | `hirelens-backend/app/api/v1/routes/users.py` (line ~46) — the `PATCH /users/me/persona` handler | After successful persona mutation | same (useful for future persona-dependent states) |

Implementation pattern: a small `home_state_service.invalidate(user_id: str, redis: Redis) -> None` helper called from each site. **Do not** try to recompute on invalidate — just delete the key; the next `GET /home/state` recomputes. Each call is fire-and-forget; failure is logged but does not block the primary operation.

**Cache miss rate target:** < 30% steady-state (a user hitting `/home` twice in a minute should hit cache the second time). Monitor via PostHog `home_state_evaluated` event's `cache_hit: bool` property.

## 7. Frontend Architecture

### New components

- **`src/hooks/useHomeState.ts`** — fetches `GET /api/v1/home/state` on mount; exposes `{ states, context, isLoading, error }`. React Query pattern, consistent with existing fetches. Cached per-session in React Query; falls back to a single in-flight promise if `HomeDashboard` and any child widget happen to request the same data (shouldn't happen in S18c, but defensive).
- **`src/components/home/StateAwareWidgetSlot.tsx`** — renders the widget for `states[0]` or nothing. Props: `state: string | null, context: HomeStateContext`. Single switch on `state` that maps to the new widgets listed below.
- **`src/components/home/widgets/StreakAtRiskWidget.tsx`** — "Your N-day streak ends in X hours. [Review now]" → `/learn/daily`.
- **`src/components/home/widgets/MissionOverdueWidget.tsx`** — "Your mission's target date has passed. [Review mission] [End mission]" → `/learn/mission`.
- **`src/components/home/widgets/ResumeStaleWidget.tsx`** — "Your last scan was N days ago. [Run a scan]" → `/prep/analyze`.
- **`src/components/home/widgets/WelcomeBackWidget.tsx`** — "Welcome back — you've been away for N days. Your next card is ready." → `/learn/daily`.
- **`src/components/home/widgets/FirstSessionWidget.tsx`** — "Nice start — keep going. Review 3 more cards to lock in your progress." → `/learn/daily`.

All new widgets compose the existing `DashboardWidget` primitive from S18. Loading/empty/error contracts from spec #35 §Solution are unchanged.

### `HomeDashboard.tsx` changes

- Call `useHomeState()` at the top.
- Render `<StateAwareWidgetSlot state={states[0] ?? null} context={context} />` above the existing persona grid.
- Pass-through: if `useHomeState()` is loading or errored, render only the S18 static layout (no slot, no placeholder skeleton). Rationale: the static layout is a valid home page; a priority-slot skeleton that might resolve to nothing is visual noise.
- **Do not** remove or re-order S18 widgets. The priority slot is purely additive.

### Backend architecture

- New file: `hirelens-backend/app/services/home_state_service.py` — pure state evaluator. Signature: `async def evaluate_state(user_id: str, db: AsyncSession, redis: Redis) -> HomeStateResponse`. Handles cache lookup, delegates to `_compute_state_uncached()` on miss, writes result, returns.
- New file: `hirelens-backend/app/api/v1/routes/home.py` — thin route, one endpoint, delegates to the service.
- Register router in `app/main.py` with prefix `/api/v1/home`.
- New Pydantic schemas: `hirelens-backend/app/schemas/home.py` with `HomeStateResponse` + `HomeStateContext`.

### Loading / error UX

- **Loading:** S18 static layout renders immediately (persona is in AuthContext already). Priority slot is absent during fetch. No skeleton for the slot. This is spec'd behavior — see AC-10.
- **Error:** silent fallback to S18 layout. Log to Sentry (backend already handles). Fire PostHog `home_state_evaluation_failed` (backend) with `{error_code}`. Frontend fires nothing — the user experience is indistinguishable from "no states active."

## 8. Acceptance Criteria

Copied from v2.2-patch where fit, tightened from audit.

- **AC-1** — `GET /api/v1/home/state` returns a response matching the schema in §5 for every authenticated user (free, pro, enterprise; every persona).
- **AC-2** — The evaluator correctly identifies each of the six states: `mission_overdue`, `streak_at_risk`, `mission_active`, `resume_stale`, `inactive_returner`, `first_session_done`. Verified by one unit test per state seeding the trigger condition and asserting the state name appears in the response.
- **AC-3** — Mutually-exclusive states never appear together in `states[]`. Specifically: `mission_active` ⊕ `mission_overdue`; `inactive_returner` ⊕ `first_session_done`. Verified by unit tests that seed overlapping trigger data and assert only the higher-priority state is emitted.
- **AC-4** — Priority order in `states[]` is deterministic — given the same DB state, two sequential calls return identical `states[]` arrays (same elements, same order). Verified by a unit test that seeds a user with 3 active states and asserts the exact expected ordered list.
- **AC-5** — Locked two-tier perf budget: **warm-cache p95 ≤ 100ms, cold-cache p95 ≤ 250ms**. Verified by a backend benchmark test (`tests/perf/test_home_state_perf.py`, marker-gated `@pytest.mark.perf` so CI can skip). Measured against a seeded user with all six states evaluable; the test runs both a cold-path request (pre-cleared cache) and a warm-path request, asserting each tier independently.
- **AC-6** — Cache invalidation works end-to-end. Verified by an integration test that: (a) warms the cache via `GET /home/state`, (b) triggers each invalidation event (card review, mission create, scan complete, plan change, persona update), (c) asserts the next `GET /home/state` recomputes (cache miss logged).
- **AC-7** — Falling back to the S18 static layout on evaluator failure does not break the page. Verified by a frontend test that mocks `useHomeState()` to return `error`, renders `<HomeDashboard>`, and asserts all S18 widgets still render + no error toast appears + no white-screen.
- **AC-8** — Loading state shows the S18 static layout (no priority slot, no placeholder skeleton). Verified by a frontend test that mocks `useHomeState()` in loading state and asserts the priority slot is absent + all S18 widgets render.
- **AC-9** — `home_state_evaluated` PostHog event fires on successful state fetch with `{persona, states: string[], state_count: int, cache_hit: bool}`. Verified by a frontend test asserting capture shape.
- **AC-10** — Theme tokens only — no hardcoded hex in any new widget file. Verified by review-time grep (not a runtime assertion; matches spec #35 AC-10).

## 9. Test Plan

### Backend

**Unit tests** (`tests/test_home_state_service.py`):

- `test_mission_overdue_when_target_date_passed` — seed active mission with `target_date = today - 1d`, assert `"mission_overdue"` in states, `"mission_active"` absent.
- `test_mission_active_when_target_date_future` — seed active mission with `target_date = today + 5d`, assert `"mission_active"` in states, `"mission_overdue"` absent.
- `test_streak_at_risk_when_18h_elapsed` — seed `GamificationStats.current_streak=5`, `MAX(CardProgress.last_reviewed) = now - 19h`, assert `"streak_at_risk"` in states.
- `test_streak_not_at_risk_when_recent_review` — seed streak=5, last review 2h ago, assert `"streak_at_risk"` NOT in states.
- `test_resume_stale_when_scan_old` — seed tracker entry with `created_at = now - 22d`, assert `"resume_stale"` in states.
- `test_inactive_returner_when_within_window` — seed `last_active_date = today - 8d`, `longest_streak = 10`, assert `"inactive_returner"` in states.
- `test_inactive_returner_suppressed_beyond_window` — seed `last_active_date = today - 45d`, assert `"inactive_returner"` NOT in states (outside 7–30d window).
- `test_first_session_done_when_badge_present_and_low_reps` — seed `UserBadge(first_review)` + `SUM(CardProgress.reps)=1`, assert `"first_session_done"` in states.
- `test_first_session_done_suppressed_when_reps_exceed_cap` — seed badge + reps=5, assert `"first_session_done"` NOT in states.
- `test_states_ordered_by_priority_deterministic` — seed user with 3 simultaneous active states, assert exact ordered list.
- `test_mutually_exclusive_mission_states` — seed an active overdue mission, assert only `"mission_overdue"` emitted.
- `test_mutually_exclusive_welcome_states` — seed an inactive-returner user who also qualifies for first_session_done (badge present, low reps, 10d gap), assert only `"inactive_returner"` emitted (higher priority).
- `test_empty_states_for_engaged_user` — seed a user mid-streak who reviewed 3h ago, assert `states == []`.

**Integration tests** (`tests/integration/test_home_state_endpoint.py`):

- `test_home_state_endpoint_requires_auth` — no JWT → 401.
- `test_home_state_endpoint_returns_schema_shape` — authenticated → response matches schema exactly (all `context` keys present, correct types).
- `test_home_state_cache_hit_sets_flag` — two sequential calls, second call has `cache_hit: true` in logs.
- `test_home_state_cache_invalidation_on_card_review` — prime cache, review a card, next call recomputes.
- (Marker-gated) `test_home_state_perf` in `tests/perf/test_home_state_perf.py` with `@pytest.mark.perf` — asserts p95 under budget. Excluded from CI default; run pre-merge.

### Frontend

**Component tests** (`tests/home/StateAwareWidgetSlot.test.tsx` + per-widget):

- `test_renders_top_priority_state_widget` — pass `states=["mission_overdue","streak_at_risk"]`, assert `MissionOverdueWidget` renders, `StreakAtRiskWidget` does not.
- `test_renders_nothing_when_states_empty` — pass `states=[]`, assert slot renders no children.
- One test per new widget (5 widgets × 1 happy-path test = 5 tests): mount with the relevant context values, assert headline text + CTA href.

**Page-level tests** (`tests/HomeDashboard.test.tsx` additions):

- `test_renders_state_slot_above_static_grid` — mock `useHomeState` returning `states=["streak_at_risk"]`, assert `StreakAtRiskWidget` appears before S18 persona grid in DOM order.
- `test_falls_back_to_static_on_api_error` — mock `useHomeState` error, assert S18 widgets render + no `StreakAtRiskWidget`.
- `test_loading_state_hides_slot_shows_static` — mock `useHomeState` loading, assert priority slot absent + S18 widgets present.

### Analytics verification

- Manual: PostHog `home_state_evaluated` fires on every `/home` mount with correct shape.
- Manual: `home_state_evaluation_failed` fires on backend when a data source errors (force by temporarily breaking a query in staging).

### Test count target

| Baseline (post-S18) | Delta (S18c impl) | Target |
|---|---|---|
| BE 184 unit + 6 integration | +~13 unit + ~4 integration + 1 perf (marker-gated) | ≥ 197 unit + ≥ 10 integration |
| FE 78 | +~10 (slot + 5 per-widget + 3 page-level + edge cases) | ≥ 88 |

## 10. Out of Scope / Deferred

- **`new_pro_member` and `needs_persona_refresh` states** — deferred pending **spec #41 (state-evaluation prerequisites)**. Spec #41 is a small, scoped slice: `Subscription.plan_changed_at` column + `User.persona_changed_at` column + 2 Alembic migrations + service hooks in `_handle_checkout_completed` / `_handle_subscription_deleted` / `PATCH /users/me/persona` to populate the timestamps on the relevant mutations. After spec #41 ships, amend spec #40 to re-add these two states into §3, §4, §5 (context fields), §7 (widget files), §8 (ACs), §9 (tests). Spec #41 is drafted separately — do not create it in this slice.
- **`inactive_returner` suppression on recent daily-reminder email** — originally proposed but deferred: the Phase-2 reminder service (`app/services/reminder_service.py:141-149`) fires a PostHog `email_sent` event but **does not persist the send timestamp to the database**. `EmailPreference` has no `last_reminder_sent_at` column. Adding one is a small follow-up slice; until then, `WelcomeBackWidget` renders unconditionally when the state matches (see §11 Q3).
- **Secondary-priority slot rendering** — `states[1..]` are exposed in the API but drive no UI in S18c. If a future slice wants a toast layer or a second slot, the data is already there.
- **State-driven email triggers** — state evaluation is read-only; no side effects. If a future slice wants "streak_at_risk triggers a push notification," it lives in a separate scheduled job, not in `/api/v1/home/state`.
- **User-configurable state thresholds** — the 18h / 7d / 21d / 30d thresholds are constants in code, not user settings.
- **Backfill of historical state transitions** — no event log of "user entered streak_at_risk at T." State is evaluated point-in-time, not historied.
- **Admin override** — no admin tool to force a state on a user. State is purely derived.

## 11. Resolved Questions

All questions resolved during the 2026-04-18 chat-Claude amendment pass. Each item is kept as a record of the decision so a future contributor knows why the spec looks the way it does.

### Q1 — `new_pro_member` state requires `Subscription.plan_changed_at`

**RESOLVED:** state is **dropped from this spec**. Schema prerequisite — `Subscription.plan_changed_at` column + population hooks in `_handle_checkout_completed` / `_handle_subscription_deleted` — is tracked in **spec #41 (state-evaluation prerequisites)**. After #41 ships, amend spec #40 to re-add `new_pro_member`.

### Q2 — `needs_persona_refresh` state requires `User.persona_changed_at`

**RESOLVED:** state is **dropped from this spec**. Schema prerequisite — `User.persona_changed_at` column + population hook in `PATCH /api/v1/users/me/persona` — is bundled into the same **spec #41**. After #41 ships, amend spec #40 to re-add `needs_persona_refresh`.

### Q3 — `inactive_returner` vs Phase-2 daily reminder email

**RESOLVED (with limitation):** the preferred variant was "suppress `inactive_returner` if a daily reminder email was sent within the last 24h." **However, the prerequisite data source does not exist.** `reminder_service.send_daily_reminders()` at `hirelens-backend/app/services/reminder_service.py:141-149` fires a PostHog `email_sent` event but does not persist a send timestamp to the database; `EmailPreference` has no `last_reminder_sent_at` column. Adding one is a small follow-up slice (one column + a write in `send_daily_reminders`).

**Fallback applied:** Option A — render `WelcomeBackWidget` unconditionally when `inactive_returner` matches. The 7–30d window in §3 still applies (users gone longer than 30d don't trigger the state at all). Recorded in §10 Out of Scope as a follow-up.

### Q4 — `first_session_done` derivation choice

**RESOLVED:** Option A — `UserBadge WHERE badge_id='first_review'` AND `SUM(CardProgress.reps) <= 3`. Leverages the existing badge-award pipeline; the `reps` cap ensures the state expires naturally once the user is past the "just starting" window.

### Q5 — Perf budget revision from v2.2-patch's flat 100ms

**RESOLVED:** two-tier budget accepted and locked in §6 — warm-cache p95 ≤ 100ms, cold-cache p95 ≤ 250ms. AC-5 in §8 verifies both tiers independently.

### Q6 — `.agent/skills/home.md` skill file

**RESOLVED:** yes, add during **P5-S18c implementation** (not this spec). Tracked as a line item in S18c's Files Touched when that slice's prompt is drafted. Keeps spec #40 scoped to the behavioural contract; implementation slice owns the skill-file sync.

---

*End of spec. No code in this slice. All questions resolved; P5-S18c implementation may proceed on Dhamo's go-ahead.*
