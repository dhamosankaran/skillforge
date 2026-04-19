---
description: State-aware home dashboard — priority slot, state evaluator, Redis cache, invalidation
---
# Home Skill

## Overview
The home dashboard at `/home` renders a static persona-keyed widget
grid (P5-S18, spec #35) and — added in P5-S18c (spec #40) — a
**state-aware priority slot above the grid** that surfaces the single
most time-sensitive widget for the current user.

A backend evaluator computes the user's active states on demand,
returns them priority-ordered, and caches the result in Redis. The
frontend renders the top-priority widget; if no state is active,
the slot is silent and the static layout stands alone.

## Key Files

### Backend
- `app/services/home_state_service.py` — pure state evaluator.
  `evaluate_state(user_id, db, redis)` returns a `HomeStateResponse`.
  Per-state predicate functions: `_check_streak_at_risk`,
  `_check_mission_active`, `_check_mission_overdue`,
  `_check_resume_stale`, `_check_inactive_returner`,
  `_check_first_session_done`. `invalidate(user_id, redis)` deletes
  the per-user cache key.
- `app/api/v1/routes/home.py` — `GET /api/v1/home/state` endpoint.
  Auth required, returns the evaluator output. Partial-failure path
  returns `states=[]` + partial context (HTTP 200) per spec §5.
- `app/schemas/home.py` — `HomeStateResponse` + `HomeStateContext`
  Pydantic models matching the §5 contract exactly.

### Frontend
- `src/hooks/useHomeState.ts` — React Query wrapper around
  `GET /api/v1/home/state`. Returns `{persona, states, context,
  isLoading, error}`.
- `src/components/home/StateAwareWidgets.tsx` — single-switch
  renderer; mounts the widget for `states[0]` or nothing.
- `src/components/home/widgets/StreakAtRiskWidget.tsx` —
  "Your N-day streak is at risk" → `/learn/daily`.
- `src/components/home/widgets/MissionActiveWidget.tsx` —
  "Mission: <company>. <N> days left" → `/learn/mission`.
- `src/components/home/widgets/MissionOverdueWidget.tsx` —
  "Mission overdue by <N> days" → `/learn/mission`.
- `src/components/home/widgets/ResumeStaleWidget.tsx` —
  "Last scan was <N> days ago" → `/prep/analyze`.
- `src/components/home/widgets/InactiveReturnerWidget.tsx` —
  "Welcome back" → `/learn/daily`.
- `src/components/home/widgets/FirstSessionDoneWidget.tsx` —
  celebration — "Nice start" → `/learn/daily`.
- `src/types/homeState.ts` — TS types matching the response schema.

## State Catalog

Six states, priority-ordered (1 = highest). Full predicates and
mutual-exclusion rules in [spec #40 §3](../../docs/specs/phase-5/40-home-dashboard-state-aware.md).

| Priority | State | One-line trigger |
|---|---|---|
| 1 | `mission_overdue` | active mission AND `target_date < today_utc` |
| 2 | `streak_at_risk` | `current_streak >= 3` AND last review > 18h ago |
| 3 | `mission_active` | active mission AND `target_date >= today_utc` |
| 4 | `resume_stale` | last tracker scan > 21d ago AND ≥1 scan exists |
| 5 | `inactive_returner` | `last_active_date` in [today-30d, today-7d] AND `longest_streak >= 1` |
| 6 | `first_session_done` | `first_review` badge present AND `SUM(reps) <= 3` |

Mutually exclusive pairs (evaluator emits only the higher-priority one):
`mission_active ⊕ mission_overdue`; `inactive_returner ⊕ first_session_done`.

## Cache Strategy

- **Key:** `home_state:{user_id}` — per-user, no query-param variation.
- **Value:** serialized JSON of the full response body.
- **TTL:** 60 seconds (floor for "something changed externally and no
  event fired" — e.g., the 18h streak threshold ticking over).

### Invalidation sites
The implementation slice wires `home_state_service.invalidate(user_id, redis)`
at all five mutation points. Fire-and-forget; failure is logged but
does not block the primary operation.

| Event | File | Trigger |
|---|---|---|
| `card_reviewed` | `app/services/study_service.py` | end of `submit_review()` after DB flush |
| `mission_lifecycle` | `app/services/mission_service.py` | end of `create_mission()`, `record_day_completion()`, `abandon_mission()` |
| `scan_completed` | `app/api/v1/routes/analyze.py` | after successful scan, alongside auto-tracker upsert |
| `plan_changed` | `app/services/payment_service.py` | inside `_handle_checkout_completed()` and `_handle_subscription_deleted()` |
| `persona_updated` | `app/api/v1/routes/auth.py` | after `PATCH /api/v1/users/me/persona` mutation |

### Performance budget (spec §6)
- Warm-cache p95: ≤ 100ms (the common case).
- Cold-cache p95: ≤ 250ms (first request per user per TTL window).

## Analytics Events

| Event | Source | Properties |
|---|---|---|
| `home_state_evaluated` | `useHomeState.ts` (FE) | `{persona, states: string[], state_count, cache_hit}` — fires on successful fetch |
| `home_state_widget_clicked` | each widget (FE) | `{state, cta}` — fires on widget CTA click |
| `home_state_evaluation_failed` | `home_state_service.py` (BE) | `{user_id, error_code}` — fires on data-source failure |

All three are added to `.agent/skills/analytics.md` in this slice.

## Loading / Error UX

- **Loading:** `<StateAwareWidgets>` renders nothing. The S18 static
  layout shows behind it; the slot simply does not appear until the
  fetch resolves. No skeleton — a placeholder that may resolve to
  nothing is visual noise.
- **Error / empty `states[]`:** silent fallback — render nothing.
  The S18 static layout is a valid home page.

## Widget Empty-State Contract

Codified in [spec #44](../../docs/specs/phase-5/44-home-widget-empty-states.md).
Applies to every widget under `src/components/home/widgets/` — existing
and future. Reviewers cite this section.

**The rule.** Every home-dashboard widget MUST:

1. Accept at least one of the four states defined by
   `DashboardWidget`: `loading`, `data`, `empty`, `error`. A widget
   that fetches any async data MUST branch on all four.
2. Source all user-scoped data from an **authenticated endpoint** that
   filters by the current user's id (or from auth-derived context like
   `AuthContext` / `GamificationContext`). A widget MUST NOT read from
   a global, unfiltered, or `user_id=None` bucket. The `/api/tracker`
   legacy route is one such bucket — do not consume it from a widget.
3. In the `empty` state, either:
   - (a) render a CTA that invites the user to create the data
     (e.g., "Scan your resume to see your ATS score →"), OR
   - (b) hide the widget entirely (return `null` or don't mount it).
4. In the `empty` or `error` state, NEVER render company names,
   scores, dates, counts, or any other data that resembles real user
   content.
5. In the `loading` state, render a skeleton (via the primitive's
   `SkeletonCard`), not cached or stale data from a previous user.

**Why.** Rule 2 prevents the cross-user data leak that motivated spec
#44 (the LastScan "Wells Fargo · 54%" report on a user who never
scanned). Rule 3 turns empty states into first-session CTAs instead
of blank cards. Rule 4 gives tests a crisp structural check.

### Per-widget compliance (current)

| Widget | Data source | Rule-2 (auth-scoped)? |
|---|---|---|
| `TodaysReviewWidget` | `fetchDailyQueue()` → `/api/v1/study/daily` | ✓ |
| `StreakWidget` | `useGamification()` (clears on sign-out) | ✓ |
| `WeeklyProgressWidget` | `useGamification()` + `ActivityHeatmap` | ✓ |
| `LastScanWidget` | `fetchUserApplications()` → `/api/v1/tracker` | ✓ |
| `InterviewTargetWidget` | `user.interview_target_*` (AuthContext) | ✓ |
| `CountdownWidget` | `user.interview_target_date` + `fetchActiveMission()` | ✓ |
| `TeamComingSoonWidget` | static copy | n/a |
| State-aware widgets (6) | `useHomeState()` → `/api/v1/home/state` | ✓ |
| `InterviewPrepperChecklist` | `useOnboardingChecklist()` → `/api/v1/onboarding/checklist` | ✓ |
