# P5-S20·home-widget-empty-states — Home Widget Empty-State Contract + LastScan Cross-User Leak Fix

**Status:** Active — shipping this slice
**Owner:** Dhamo
**Created:** 2026-04-19
**Phase:** 5
**Depends on:** Spec #35 (HomeDashboard + widgets), Spec #40 (state-aware home), Spec #41 (Interview-Prepper checklist)
**Relates to:** Deferred Hygiene Item `[S35-flag, P5-S18]` — tracker helper path mismatch

## 1. Problem Statement

A fresh-signed-in user lands on `/home` and the **Last Scan** widget
renders "Wells Fargo · 54%" — data the user has never produced. The
user has never scanned a resume. The data is coming from somewhere it
shouldn't.

### 1.1 Root cause

`LastScanWidget` (`src/components/home/widgets/LastScanWidget.tsx`)
pulls tracker rows via `getApplications()` from `services/api.ts:204`:

```ts
export async function getApplications(): Promise<TrackerApplication[]> {
  const response = await api.get<TrackerApplication[]>('/api/tracker')
  return response.data
}
```

That URL hits the **legacy unauthenticated** route at
`app/api/routes/tracker.py:25`:

```python
@router.get("/tracker", response_model=List[TrackerApplication])
async def list_applications(db: AsyncSession = Depends(get_db)):
    return await tracker_service_v2.get_applications(db, user_id=None)
```

And `tracker_service_v2.get_applications()` at
`app/services/tracker_service_v2.py:85-94`:

```python
async def get_applications(db, user_id=None):
    stmt = select(TrackerApplicationModel).order_by(...desc())
    if user_id:
        stmt = stmt.where(TrackerApplicationModel.user_id == user_id)
    ...
```

`if user_id:` only applies the filter when `user_id` is truthy. Passing
`user_id=None` (the legacy route always does) skips the filter and
returns **every tracker row in the database across every user and every
anonymous scan**. The widget then sorts by `created_at` desc and shows
whichever row is newest — for a fresh user that's somebody else's.

This is a cross-user data leak, not a UI caching or stale-state bug.

### 1.2 Broader issue

Audit of all home widgets (`src/components/home/widgets/*`) found that
the leak is contained to `LastScanWidget`. The `DashboardWidget`
primitive's `loading/data/empty/error` contract is already wired
through every widget. However, the contract **exists in the primitive
but is not codified as a rule** — there is no written policy that says
"every home widget must branch on these four states before rendering,"
and no rule forbidding a widget from rendering data not sourced from
the authenticated current user. Spec #35 §Solution documents the
primitive's four states, but not the cross-widget policy.

## 2. Goals / Non-Goals

### Goals

- Fix the LastScan cross-user leak by pointing the widget at an
  authenticated endpoint scoped to the current user.
- Codify a **Widget Empty-State Contract** in `.agent/skills/home.md`
  so future widgets follow the rule and reviewers have something to
  cite.
- Add a regression test that asserts LastScan never renders
  placeholder data when the data source returns empty.

### Non-Goals

- **Migrate `getApplications()` globally.** The legacy helper is used
  by `Tracker.tsx` too. Changing its URL affects every consumer;
  that's listed as Deferred Hygiene Item `[S35-flag, P5-S18]` and
  gets its own slice. This slice adds a narrow, widget-scoped helper
  for the authenticated path — the old helper stays.
- **Delete or rename `/api/tracker`.** The legacy unauthenticated
  surface is still consumed by `Tracker.tsx` and the legacy
  `/api/analyze` flow. Touching it is a Phase-6 cleanup candidate.
- **FSRS daily-cap work.** The diagnostic audit done alongside this
  slice (see §11) found the "6th card accepted" report is a copy bug
  that folds into P5-S22's locked decision #1B (20-cap). Not fixed here.
- **Streak / Weekly / Interview-Target empty-state rewrites.** They
  already satisfy the contract. No changes needed.
- **Schema changes.** No migration, no new columns.

## 3. Widget Empty-State Contract

**This is the rule being codified.** It applies to every widget
under `src/components/home/widgets/` — existing and future.

### 3.1 The rule

Every home-dashboard widget MUST:

1. Accept at least one of the four states defined by
   `DashboardWidget`: `loading`, `data`, `empty`, `error`. A widget
   that fetches any async data MUST branch on all four.
2. Source all user-scoped data from an **authenticated endpoint** that
   filters by the current user's id (or from auth-derived context like
   `AuthContext` / `GamificationContext`). A widget MUST NOT read from
   a global, unfiltered, or `user_id=None` bucket.
3. In the `empty` state, either:
   - (a) render a CTA that invites the user to create the data
     (e.g., "Scan your resume to see your ATS score →"), OR
   - (b) hide the widget entirely (return `null` or don't mount it).
4. In the `empty` or `error` state, NEVER render company names,
   scores, dates, counts, or any other data that resembles real user
   content.
5. In the `loading` state, render a skeleton (via the primitive's
   `SkeletonCard`), not cached or stale data from a previous user.

### 3.2 Why it matters

- **Cross-user data leak prevention.** Rule 2 directly prevents the
  LastScan bug from reoccurring: any widget sourced from a
  `user_id=None`-callable endpoint is a leak waiting to happen.
- **First-session UX.** Rule 3 turns the empty state into a surfaced
  CTA instead of a blank card. A new user sees "Scan a resume" instead
  of a confused "something-should-be-here" gap.
- **Regression safety.** Rule 4 gives reviewers and tests a crisp
  check: if the widget renders a company string while the data source
  is empty, something is wrong.

### 3.3 Per-widget compliance (current)

| Widget | Data source | Loading | Empty | Error | Rule-2 pass? |
|---|---|---|---|---|---|
| `TodaysReviewWidget` | `fetchDailyQueue()` → `/api/v1/study/daily` (auth) | skeleton | "You're all caught up — no cards due today." | retry | ✓ |
| `StreakWidget` | `useGamification()` (clears on signout) | skeleton | "Start your streak — review a card today." | retry | ✓ |
| `WeeklyProgressWidget` | `useGamification()` + `ActivityHeatmap` | skeleton | "Review your first card to see your activity heatmap." | (inherits from heatmap) | ✓ |
| `LastScanWidget` | `getApplications()` → `/api/tracker` (unauth, **user_id=None**) | skeleton | "Run your first scan to see results here." | retry | **✗ — leaks cross-user** |
| `InterviewTargetWidget` | `user.interview_target_*` (AuthContext) | n/a | "Set your interview company in the Countdown widget below." | n/a | ✓ |
| `CountdownWidget` | `user.interview_target_date` + `fetchActiveMission()` (auth) | n/a | n/a (Mode 1 is date-setter; Mode 2 is always data) | n/a | ✓ |
| `TeamComingSoonWidget` | static copy | n/a | n/a | n/a | ✓ |
| State-aware widgets | `useHomeState()` → `/api/v1/home/state` (auth) | nothing (silent) | nothing | nothing | ✓ |
| `InterviewPrepperChecklist` | `useOnboardingChecklist()` → `/api/v1/onboarding/checklist` (auth, 403 for non-IP) | null | null | null | ✓ |

Only `LastScanWidget` fails Rule 2.

## 4. Solution

### 4.1 Add `fetchUserApplications()` helper

Add to `src/services/api.ts`, next to the existing `getApplications`:

```ts
// User-scoped tracker fetch used by HomeDashboard widgets.
// Hits the auth'd /api/v1/tracker surface, which filters by the
// caller's user_id via get_current_user_optional. The legacy
// getApplications() below still hits /api/tracker for Tracker.tsx
// compatibility — see Deferred Hygiene Item [S35-flag, P5-S18].
export async function fetchUserApplications(): Promise<TrackerApplication[]> {
  const response = await api.get<TrackerApplication[]>('/api/v1/tracker')
  return response.data
}
```

Rationale for a new helper rather than editing `getApplications()`:

- `getApplications()` is called by `Tracker.tsx` (post-P5-S18 audit).
  Changing its URL silently affects that page — out-of-scope scope
  expansion. The helper migration is a tracked hygiene item.
- A narrow helper makes the intent at the call site obvious
  ("user-scoped") and scopes the fix precisely.

### 4.2 LastScanWidget data source swap

Change the import at
`src/components/home/widgets/LastScanWidget.tsx:3`:

```ts
// before
import { getApplications } from '@/services/api'
// after
import { fetchUserApplications } from '@/services/api'
```

And the call at line 17. No other logic changes — the widget's
loading/data/empty/error branching is already correct.

### 4.3 Regression test

Add to `tests/home/widgets/LastScanWidget.test.tsx`:

- `renders_empty_state_and_never_a_company_when_api_returns_empty`
  — mocks `fetchUserApplications` to resolve with `[]`, asserts the
  empty CTA is present AND asserts no company/role/ATS score DOM
  nodes are rendered (a structural check, not just a text check, to
  catch any future re-introduction of placeholder data).

Existing tests already cover the happy/empty/error/retry paths against
the old mock — they get updated to mock `fetchUserApplications`.

### 4.4 Contract documentation

Add a new section "Widget Empty-State Contract" to
`.agent/skills/home.md` mirroring §3 of this spec. Future widgets get
reviewed against that section; reviewers cite the skill file.

## 5. Acceptance Criteria

- **AC-1** — A user who has never scanned a resume does NOT see
  a company name, role, or ATS score on `/home`. `LastScanWidget`
  renders the empty CTA ("Run your first scan to see results here." /
  "Scan a resume").
- **AC-2** — `LastScanWidget` fetches from `/api/v1/tracker` (user-
  scoped), not `/api/tracker`. Verified by integration test mocking
  the new helper.
- **AC-3** — When the data source returns `[]`, no DOM node rendered
  by `LastScanWidget` contains a company name, role, or percentage.
  Asserted by the new regression test in §4.3.
- **AC-4** — `.agent/skills/home.md` contains a "Widget Empty-State
  Contract" section with rules 1–5 from §3.1.
- **AC-5** — Existing S18, S18c, S18d test suites remain green. No
  regression in the widget layer, the state-aware layer, the
  interview-prepper checklist, or the dashboard page tests.

## 6. Test Plan

### Backend

No backend changes in this slice. Backend tests remain at 228 unit +
6 integration deselected.

### Frontend (`tests/home/widgets/LastScanWidget.test.tsx`)

| Test | AC | Change |
|---|---|---|
| `renders a skeleton in the loading state` | — | mock swap |
| `renders the latest app (by created_at desc) with scan_id in View results link` | — | mock swap |
| `renders the empty state when no applications exist` | AC-1 | mock swap |
| `renders the error state + retry re-fetches` | — | mock swap |
| `renders no company/role/ATS score text when api returns empty` | AC-1, AC-3 | **new** |

Expected delta: **+1 frontend test** (100 → 101).

## 7. Out of Scope

- Migrating `getApplications()` globally from `/api/tracker` →
  `/api/v1/tracker`. Tracker.tsx consumer. See Deferred Hygiene
  Item `[S35-flag, P5-S18]`.
- Removing the legacy `/api/tracker` route. Still wired to the legacy
  `/api/analyze` and `Tracker.tsx`. Phase 6 cleanup candidate.
- Fixing `tracker_service_v2.get_applications` to refuse `user_id=None`
  (would break legacy route contract; orthogonal).
- The FSRS "6th-card" daily-cap copy issue (diagnosed alongside this
  slice; see §11). Folds into P5-S22.
- New widgets, new empty-state copy beyond the existing wording, new
  PostHog events. No analytics changes this slice.
- The WeeklyProgress empty-state heuristic flagged at `[S18-flag]`.

## 8. Provenance

- User report (2026-04-19): fresh user on `/home` saw "Wells Fargo ·
  54%" on the Last Scan widget despite never scanning a resume.
- Root cause trace: `LastScanWidget → getApplications() → GET /api/tracker → tracker_service_v2.get_applications(db, user_id=None) → unfiltered select`. Confirmed in step 2 audit of this slice.
- The existing `[S35-flag, P5-S18]` Deferred Hygiene Item already
  flagged the path mismatch as an orthogonal migration risk; this
  slice takes the minimum slice needed to close the data-leak without
  triggering that migration.

## 9. Widget changes summary

| Widget | Previous behavior | New behavior |
|---|---|---|
| `LastScanWidget` | Pulled from `/api/tracker` (unauth, returned all rows across all users — rendered another user's scan as if it were the current user's) | Pulls from `/api/v1/tracker` (auth, scoped to current user). Empty state unchanged. |

All other widgets: **no change** (already contract-compliant per §3.3).

## 10. Files touched

- `docs/specs/phase-5/44-home-widget-empty-states.md` (new — this file)
- `.agent/skills/home.md` (modified — add §Widget Empty-State Contract)
- `hirelens-frontend/src/services/api.ts` (modified — add `fetchUserApplications`)
- `hirelens-frontend/src/components/home/widgets/LastScanWidget.tsx` (modified — swap import + call)
- `hirelens-frontend/tests/home/widgets/LastScanWidget.test.tsx` (modified — swap mock; add regression test)

## 11. Related: FSRS daily-cap copy-bug diagnostic

Out of scope for implementation here — this section exists so the
decision trail is captured in one place.

During the Step 2 audit of this slice we also traced the user's report
that "a 6th card was accepted past the 5-card daily limit."

**Finding:** the backend's `get_daily_review()`
(`app/services/study_service.py:121-217`) applies `LIMIT 5` per call,
not per day. `review_card()` (same file, line 249) has no
"already reviewed today" guard. On refresh after completing 5 cards,
the queue re-fills with fresh unreviewed cards. The `daily_complete`
XP bonus at line 373 uses `if reviewed_today == _DAILY_GOAL` — fires
exactly once, so no reward corruption. FSRS state is updated
correctly per review; py-fsrs is designed to accept multiple reviews
per day (Again-rated cards re-drill immediately).

**Verdict: copy bug only**, no FSRS state corruption.

**Recommended follow-up:** folds into P5-S22 (which implements locked
decision #1B in `SESSION-STATE.md` — the 20-cards-per-day HARD CAP).
That slice will add the server-side daily cap and should also re-copy
the DailyReview UI to match the true semantics. No interim fix needed
— no data-integrity risk today.
