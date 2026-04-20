# P5-S18c·checklist — Interview-Prepper Onboarding Checklist

**Status:** Done — Backfilled (shipped in commit f075a64; spec cross-checked against disk 2026-04-19)
**Owner:** Dhamo
**Created:** 2026-04-19
**Phase:** 5D
**Depends on:** Spec #34 (PersonaPicker), Spec #35 (HomeDashboard + widgets), Spec #40 (state-aware home — adds `StateAwareWidgets` render slot this widget sits below)
**Source:** `claude-code-prompts-all-phases-v2.2-patch.md` §P5-S18c (chat-Claude project knowledge; not checked into repo). This spec is the audited, code-grounded amendment of that starter.

## 1. Problem Statement

A brand-new Interview-Prepper signs in, picks the persona, and lands on `/home`. Spec #35 shipped a four-widget grid for this persona (Countdown, InterviewTarget, TodaysReview, LastScan). Spec #40 layered a priority-slot state widget on top. Neither gives a first-day user a **sequence** — nothing tells them "first scan your resume, then pick a category, then set a mission, then review." The grid is a set of signals, not a path.

Empirically (and by design for the three-persona pivot), the Interview-Prepper persona has the strongest need for a linear flow: they usually have a date, a target company, and ~6 weeks to get from zero to interview-ready. A first-time user who doesn't know whether to scan or study first will bounce. A persistent checklist visible on every `/home` mount — until they complete it or skip it — removes that bounce risk without adding a full onboarding modal flow.

## 2. Goals / Non-Goals

### Goals

- Render a 5-step linear checklist on `/home` **for Interview-Prepper users only**, walking them from scan → first daily review.
- Auto-complete each step from **existing telemetry** — no new schema, no new "progress" JSON on User.
- Auto-hide 7 days after all 5 steps are done (a graduation signal, not a permanent fixture).
- Let the user opt out via a "Skip checklist" link (client-side flag — no schema).
- Widget is purely additive: no changes to the spec #35 widget grid or the spec #40 priority slot.

### Non-Goals

- **Checklists for Career-Climber or Team-Lead personas.** Only Interview-Prepper gets this sequence. Other personas have different optimal first-session paths; ship those in a separate slice if data justifies.
- **Cross-device skip sync.** The skip flag lives in `localStorage` on the device where the user clicked it. User clearing storage re-shows the checklist; acceptable trade-off for a soft-dismiss UX.
- **Step sequentiality enforcement.** A user could set a mission before picking a category (step 4 before step 3). The checklist reports the correct state either way; it does not gate steps.
- **Per-step animations / celebration confetti beyond a copy change.** One celebration state on first-complete view, then auto-hide on the next visit past the 7-day window.
- **New schema columns.** `checklist_dismissed_at`, `interview_prepper_checklist_skipped`, etc. — all rejected in Step 2 audit. Derivation + localStorage is sufficient.

## 3. Architecture Decision — State Derivation From Telemetry

The checklist state is a **pure function of existing DB state**. No new table, no new column, no new event source. Each step's completion is determined by the existence of a row in a table already written by the feature that step represents.

| # | Step | Completion signal (SQL) | Data source |
|---|---|---|---|
| 1 | Scan resume | `EXISTS(SELECT 1 FROM tracker_applications_v2 WHERE user_id=:u AND scan_id IS NOT NULL)` | `app/models/tracker.py` |
| 2 | Review gaps | **Transitive** — complete when step 3 is complete. See §3.1. | — |
| 3 | Pick a category | `EXISTS(SELECT 1 FROM card_progress WHERE user_id=:u)` | `app/models/card_progress.py` |
| 4 | Set a mission | `EXISTS(SELECT 1 FROM missions WHERE user_id=:u)` | `app/models/mission.py` |
| 5 | First daily review | `EXISTS(SELECT 1 FROM card_progress WHERE user_id=:u AND reps >= 1)` | `app/models/card_progress.py` |

Step completion is **order-independent** — a user who sets a mission on day 1 (step 4 complete) but hasn't scanned yet (step 1 incomplete) will see step 1 still open with a red dot and step 4 already checked. This is honest to the data and avoids enforcing a flow the product may not want to gate on.

### 3.1 Why step 2 is transitive

"Review gaps" means the user looked at the scan-results page showing missing skills. There is no DB signal for "visited `/prep/results`" — page views are PostHog-only and not queryable from the backend. Three options were weighed in the Step 2 audit:

- **(a) Infer from scan recency.** Rejected — "user scanned 5 minutes ago" doesn't prove they scrolled past the score.
- **(b) Add a `last_gaps_viewed_at` column to `tracker_applications_v2`.** Rejected — scope expansion for a single step's telemetry, and the column adds no value outside this checklist.
- **(c) Transitive with step 3.** Chosen. A user who picked a category to study has, by definition, seen the gap list that drove them to it. The checklist shows step 2 as "done" a touch later than it "really" happened, but the cost of that lag is a small visual annoyance, not a broken flow.

### 3.2 `completed_at` derivation

When all 5 steps are complete, the backend computes:

```
completed_at = max(
  scan_row.created_at,                    -- step 1
  earliest_card_progress_row.created_at,  -- steps 2 + 3
  mission_row.created_at,                 -- step 4
  first_reviewed_progress_row.last_reviewed  -- step 5
)
```

This is the timestamp of the last-completing step. Before all 5 are done, `completed_at` is `null`. The frontend uses `completed_at` for the 7-day auto-hide window.

## 4. API Contract

### `GET /api/v1/onboarding/checklist`

**Auth:** required (standard `Depends(get_current_user)`).

**Authorisation:** Interview-Prepper only. Users whose `persona != 'interview_prepper'` receive **403**. Users with `persona=null` (shouldn't happen — PersonaGate intercepts — but defensively) receive 403 as well. This keeps Career-Climber and Team-Lead clients from fetching a widget that would never render for them.

**Response:**

```json
{
  "steps": [
    {
      "id": "scan_resume",
      "title": "Scan your resume",
      "description": "Get your ATS score and skill gaps.",
      "complete": true,
      "link_target": "/prep/analyze"
    },
    {
      "id": "review_gaps",
      "title": "Review your gaps",
      "description": "See which skills to focus on.",
      "complete": true,
      "link_target": "/prep/results"
    },
    {
      "id": "pick_category",
      "title": "Pick a study category",
      "description": "Start with the gap that matters most.",
      "complete": false,
      "link_target": "/learn"
    },
    {
      "id": "set_mission",
      "title": "Set a mission",
      "description": "Commit to a date-bound study sprint.",
      "complete": false,
      "link_target": "/learn/mission"
    },
    {
      "id": "first_review",
      "title": "Do your first daily review",
      "description": "The habit that compounds.",
      "complete": false,
      "link_target": "/learn/daily"
    }
  ],
  "all_complete": false,
  "completed_at": null
}
```

- `steps` is a fixed-length array of 5 objects, always in the same order.
- `complete` per step reflects the telemetry check in §3.
- `all_complete` is `true` iff every `steps[i].complete` is `true`.
- `completed_at` is an ISO-8601 string when `all_complete`, otherwise `null`.

**Error cases:**
- `401` — no/invalid bearer token.
- `403` — authenticated user's `persona != 'interview_prepper'`.

**No caching.** The endpoint reads four cheap queries (EXISTS checks). Adding Redis caching would complicate invalidation (scan completion, first review, mission create all need to bust it) for a sub-50ms endpoint. If profiling later shows it's hot, revisit.

## 5. Frontend

### 5.1 Hook — `src/hooks/useOnboardingChecklist.ts`

Thin fetch hook returning `{data, isLoading, error}`. **Only fires** when `user?.persona === 'interview_prepper'`; for other personas it returns `{data: null, isLoading: false}` without hitting the network. Mirrors the `useHomeState` pattern from S18c.

### 5.2 Widget — `src/components/home/widgets/InterviewPrepperChecklist.tsx`

Placement: rendered inside `InterviewPrepperMode` in `src/pages/HomeDashboard.tsx`, **above** the existing four-widget grid. Widget owns all visibility logic — HomeDashboard only decides "interview_prepper branch renders it".

**Render conditions** (all must hold for the widget to show):

- `user.persona === 'interview_prepper'` (defensive — HomeDashboard already branches)
- `localStorage.getItem('interview_prepper_checklist_skipped') !== 'true'`
- Fetch succeeded and returned data
- If `all_complete` is true: `now - completed_at ≤ 7 days` (inclusive — 7.00000 days still shows to prevent edge-case flicker)

When all hold, render:

- Card shell styled with design-tokens (`rounded-2xl border border-contrast/[0.08] bg-bg-surface/60 p-5`).
- Header: "Your next steps" (pro version — celebration state) or "Get started" (incomplete state).
- Progress bar: "`N` of 5 done" text + a bar (`bg-accent-primary/40`). Uses existing design-system tokens; no new color.
- 5 step rows. Each row: circle check icon (filled when complete), title (strikethrough when complete), description (muted), right-arrow link. Clicking the row navigates to `link_target` and fires `checklist_step_clicked` with `{step_id}`.
- "Skip checklist" muted text button at the bottom → sets localStorage flag, fires `checklist_skipped`, component re-renders null.

**Celebration state** (one visit): when `all_complete` transitions to `true` and the widget is still within the 7-day window, the title becomes "🎉 You're all set." and the 5 rows all show checkmarks. The "Skip" affordance becomes "Dismiss". On a subsequent visit past the 7-day window, the widget returns null.

### 5.3 HomeDashboard wiring

Add one line to `InterviewPrepperMode` above the grid:

```tsx
<InterviewPrepperChecklist />
```

No branching in HomeDashboard itself — the widget returns null for every reason it shouldn't show.

## 6. Auto-hide behaviour

**Trigger 1: skip click.** User clicks "Skip" → `localStorage.setItem('interview_prepper_checklist_skipped', 'true')` → widget re-renders null for every subsequent `/home` mount on that device. Reversible only by clearing storage (intentional — soft dismiss).

**Trigger 2: graduation.** All 5 steps complete AND 7 days have elapsed since `completed_at` → widget returns null. No localStorage write needed — telemetry is stable (a user cannot "un-scan" their resume), so the condition will keep evaluating true on every subsequent visit.

**Neither trigger writes to server-side state.** The backend always returns the same derivation; the frontend applies the hide rules. This means a user could sign in on a new device and briefly see the checklist again within the 7-day window — acceptable trade-off for not adding a `User.checklist_dismissed_at` column.

## 7. Analytics

| Event | Source | Properties |
|---|---|---|
| `checklist_shown` | `InterviewPrepperChecklist.tsx` — on first render with data | `{complete_count, all_complete}` |
| `checklist_step_clicked` | per step row click | `{step_id}` |
| `checklist_completed` | when `all_complete` flips `true` (client-side detection via ref) | `{completed_at}` |
| `checklist_skipped` | on "Skip" click | `{complete_count}` |

All four are added to the frontend events table in `.agent/skills/analytics.md` in this slice.

## 8. Acceptance Criteria

- **AC-1** — Widget renders on `/home` for an Interview-Prepper with at least one incomplete step.
- **AC-2** — Each step shows a correct complete/incomplete marker derived from the telemetry in §3.
- **AC-3** — Clicking a step navigates to its `link_target`.
- **AC-4** — Clicking "Skip" sets the localStorage flag and hides the widget; a page reload keeps it hidden.
- **AC-5** — When all 5 steps are complete within the last 7 days, the widget shows the celebration state; past 7 days it returns null.
- **AC-6** — Widget never renders for `career_climber` or `team_lead` users. `GET /api/v1/onboarding/checklist` returns 403 for them.
- **AC-7** — No changes to spec #35 widget grid or spec #40 priority slot. Existing `StateAwareWidgets` and persona-grid tests pass unchanged.
- **AC-8** — Backend endpoint requires auth (401 on unauth) and is read-only (no DB writes).

## 9. Test Plan

### Backend (`tests/test_onboarding_checklist.py`)

| Test | AC |
|---|---|
| `test_step_scan_resume_complete_when_tracker_row_exists` | AC-2 |
| `test_step_pick_category_complete_when_card_progress_exists` | AC-2 |
| `test_step_review_gaps_transitively_tracks_pick_category` | AC-2 |
| `test_step_set_mission_complete_when_mission_exists` | AC-2 |
| `test_step_first_review_complete_when_reps_gte_one` | AC-2 |
| `test_checklist_all_complete_with_completed_at_set` | AC-2, AC-5 |
| `test_checklist_incomplete_returns_completed_at_null` | AC-2 |
| `test_checklist_403_for_career_climber` | AC-6 |
| `test_checklist_403_for_team_lead` | AC-6 |
| `test_checklist_401_for_unauth` | AC-8 |

Expected delta: **+10 backend tests** (217 → 227).

### Frontend (`tests/home/widgets/InterviewPrepperChecklist.test.tsx`)

| Test | AC |
|---|---|
| `renders_for_interview_prepper_with_incomplete_steps` | AC-1 |
| `shows_correct_progress_count` | AC-2 |
| `step_click_navigates_to_link_target` | AC-3 |
| `skip_click_sets_localstorage_and_hides` | AC-4 |
| `shows_celebration_when_all_complete_within_7d` | AC-5 |
| `hides_when_all_complete_past_7d` | AC-5 |

Expected delta: **+6 frontend tests** (94 → 100).

S18c regression coverage: no changes to state-layer code, so the existing home-state + widget tests must remain green unchanged.

## 10. Out of Scope

- Checklists for non-Interview-Prepper personas.
- Cross-device skip sync.
- Server-side completion/dismissal timestamps.
- Per-step nudge emails / push notifications.
- A/B test infrastructure for checklist copy.
- Analytics dashboard for checklist funnel — PostHog has the raw events; dashboarding is a separate slice.

## 11. Provenance

- Step definitions and auto-hide/skip semantics are from the v2.2-patch P5-S18c description (held in chat-Claude project knowledge). This spec is the on-disk, code-grounded version.
- The step 2 transitive-derivation choice was made during the Step 2 audit of this slice; options (a) infer-from-scan-recency and (b) add-column were rejected and are documented in §3.1 for future-audit reference.
- Step 4's data source is `missions` (not `mission_categories` or `mission_days`) — any mission row (active, completed, abandoned) satisfies the signal. Abandoned missions counting as "set a mission" is intentional; the step is about "did you ever commit to a sprint", not "are you currently running one".
