# P5-S18 — HomeDashboard + Widget Catalog

**Status:** Draft (spec only — no code yet)
**Owner:** Dhamo
**Created:** 2026-04-18
**Phase:** 5D (persona-aware surface)
**Depends on:** P5-S17 (PersonaPicker page + PersonaGate shipped — commit `2c01cc7`; persona capture endpoint + `interview_target_*` columns shipped — commit `503cac8`)
**Downstream slices:** P5-S18b (state-aware dashboard variants — v2.2 patch), P5-S18c (Interview-Prepper guided checklist — v2.2 patch), P5-S19 (existing-user persona migration)
**Related resolved decisions:** spec #34 §Out of Scope — "Widget catalog per persona" explicitly deferred here. spec #34 §Analytics pre-registers `home_dashboard_viewed` for this slice to fire.

## Problem

`/home` currently renders `HomeDashboardPlaceholder` (8 lines: `<h1>Home</h1>` + "Coming in P5-S18"). Post-P5-S17, every authenticated user has a non-null `user.persona`, but the home surface is still identical for all three personas. Per `docs/prd.md §1.3`, the three personas have sharply divergent primary needs:

- **Interview-Prepper** — "I have a Google interview in 14 days" → urgency + daily cadence + resume fitness signal.
- **Career-Climber** — "I want to stay sharp and get promoted" → habit reinforcement + progress visibility, no deadline pressure.
- **Team Lead** — "My team needs to learn agentic AI patterns" → team visibility + curriculum oversight.

Spec #34 committed `/home` to three render modes keyed off `user.persona` but deferred the widget catalog, ordering, and empty-state behaviour to this slice (§Solution L62, §AC-5 L180). This spec defines the widget inventory, the reusable widget primitive, and the grid layout. Downstream slices P5-S18b (state-aware variants) and P5-S18c (Interview-Prepper checklist) layer on top of the structure landed here.

### Current state

- `/home` → `HomeDashboardPlaceholder` (src/pages/HomeDashboardPlaceholder.tsx). Single `data-testid="home-placeholder"`. No persona branching.
- `PersonaGate` (src/components/PersonaGate.tsx) already redirects `user.persona === null` users to `/onboarding/persona`, so this spec can assume a valid persona on every `/home` mount.
- No `home_dashboard_viewed` PostHog event is currently wired — spec #34 pre-registered the shape, this slice lands the entry in `.agent/skills/analytics.md`.

### Why a widget grid, not a persona-specific bespoke layout per mode

Three reasons:

1. Every persona shares at least one widget (`Today's Review`). A widget primitive lets us reuse the same component across render modes without per-persona duplication.
2. Downstream slices (P5-S18b state-awareness, P5-S18c IP checklist) need a consistent shape to plug into. Bespoke per-persona layouts in S18 would force S18b to re-shape everything.
3. The "three render modes" contract in spec #34 only committed to a `data-testid="home-mode-<persona>"` marker and persona-specific branching — the internal layout was deliberately left for this spec. A widget grid is the lightest structure that satisfies the contract and leaves room for later evolution.

### Team Lead caveat (up-front, not buried)

Per `docs/prd.md §1.5` Feature Priority Matrix, **Team dashboards (B2B)** are **P3 Future** — no team model, no team-member endpoint, no shared progress table exists in the codebase today. The Team Lead persona is durable (they are real users), but the data sources a "real" team dashboard would need are not built. This spec ships a Team Lead render mode with personal-study widgets (what they can actually use today) plus one "Team dashboards coming in a future release" placeholder widget. **When the Team dashboards spec is written, the Team Lead render mode gets redesigned** — this is explicit, not accidental.

## Solution

A persona-aware `HomeDashboard` page at `/home` that:

1. Reads `user.persona` from the auth context (already loaded via `/auth/me`; no extra fetch).
2. Renders a minimal greeting header.
3. Renders a responsive grid of widgets, ordered per persona, composed from a single reusable `<DashboardWidget>` primitive.
4. Fires `home_dashboard_viewed` on mount with `{persona}`.

### `HomeDashboard` page shape

```
┌─────────────────────────────────────────────────┐
│  Welcome back, <first name>.                    │ ← greeting header (minimal in S18)
├─────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ Widget A │ │ Widget B │ │ Widget C │         │ ← responsive grid
│  └──────────┘ └──────────┘ └──────────┘         │   (1 col mobile / 2 tablet / 3 desktop)
│  ┌──────────┐ ┌──────────┐                      │
│  │ Widget D │ │ Widget E │ ...                  │
│  └──────────┘ └──────────┘                      │
└─────────────────────────────────────────────────┘
```

- **Greeting:** `Welcome back, <user.name.split(' ')[0]>.` Static. No time-of-day logic, no persona-specific hero copy — that's P5-S18b/c territory. **Fallback:** if `user.name` is empty or undefined, render `Welcome back.` with no name — do **not** render a placeholder like `Welcome back, user.` or similar.
- **Widget grid:** Tailwind `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6`. No drag-to-reorder (out of scope per spec #34).
- **Widget order per persona:** fixed in this spec (see §Widget Catalog). Not data-driven. Not user-configurable.
- **Render-mode marker:** the outer container carries `data-testid="home-mode-<persona>"` to satisfy spec #34 AC-5.

### DashboardWidget primitive (contract)

Every widget composes this primitive. **No widget implements its own loading / empty / error UI** — that logic lives in `DashboardWidget` and each widget passes a `state` plus the matching payload.

```tsx
interface DashboardWidgetProps {
  title: string;
  testid: string;                                    // becomes data-testid="widget-<testid>"
  persona: Persona;                                  // used for analytics + a11y context
  state: 'loading' | 'data' | 'empty' | 'error';
  emptyMessage?: string;                             // required when state === 'empty'
  errorMessage?: string;                             // required when state === 'error'
  onRetry?: () => void;                              // renders "Try again" button when state === 'error'
  action?: { label: string; href?: string; onClick?: () => void };  // footer CTA; one of href/onClick
  children: ReactNode;                               // rendered only when state === 'data'
}
```

Behaviour:

- `state === 'loading'` → renders a `<SkeletonCard>` from `src/components/ui/SkeletonLoader.tsx`. No spinners. One pattern, site-wide.
- `state === 'data'` → renders `children` in the widget body; `action` (if provided) renders as a footer link/button.
- `state === 'empty'` → renders `emptyMessage` in the body with muted text styling; `action` (if provided) still renders so the empty state can CTA into the relevant flow.
- `state === 'error'` → renders `errorMessage` + a `Try again` button wired to `onRetry`.
- Visual container: reuses `AnimatedCard` from `src/components/ui/AnimatedCard.tsx` so the widget inherits the existing hover/motion treatment.
- Theme tokens only — `bg-bg-surface`, `border-contrast`, `text-text-primary`, `text-text-muted`. No hardcoded hex (CLAUDE.md §Rule 12).

**Rule:** every widget in this spec and every widget added in future slices uses `DashboardWidget`. No bespoke per-widget loading / empty / error implementations. If a widget's content doesn't fit the `children`-as-body model, the right answer is to adjust the primitive, not to bypass it.

### File layout

New directory `hirelens-frontend/src/components/home/` — **do not** reuse `components/dashboard/`, which is the ATS-scan-results domain (`ATSScoreGauge.tsx`, `MissingSkillsPanel.tsx`, `ScoreBreakdown.tsx`, etc.). Two different "dashboards" in the product → two different component folders. The spec calls this out so a future contributor reading the tree doesn't hunt for `DashboardWidget` under `components/dashboard/`.

```
hirelens-frontend/src/
├── pages/
│   └── HomeDashboard.tsx                           (new; replaces HomeDashboardPlaceholder.tsx)
└── components/
    └── home/
        ├── DashboardWidget.tsx                     (new; the primitive)
        └── widgets/
            ├── CountdownWidget.tsx                 (IP — wraps mission/Countdown + inline date-setter)
            ├── InterviewTargetWidget.tsx           (IP)
            ├── TodaysReviewWidget.tsx              (IP + CC + TL)
            ├── LastScanWidget.tsx                  (IP + CC)
            ├── StreakWidget.tsx                    (CC + TL)
            ├── WeeklyProgressWidget.tsx            (CC + TL — wraps progress/ActivityHeatmap)
            └── TeamComingSoonWidget.tsx            (TL placeholder)
```

### Widget catalog (per persona, in render order)

#### Interview-Prepper (`home-mode-interview_prepper`)

1. **Countdown** — days until `interview_target_date`. Wraps `src/components/mission/Countdown.tsx` when a date exists. When `user.interview_target_date` is null AND there is no active mission, the widget switches to an **inline date-setter**: a small `<input type="date">` + `Save` button that calls `updatePersona({ persona: user.persona, interview_target_date: <value> })` on submit and flips the widget to countdown mode on success. The `persona` field is required by the `PATCH /api/v1/users/me/persona` validator (spec #34 §API Contract); the widget passes the user's current persona unchanged to satisfy it. **Footer action (post-date-set):** once a date is set, the widget's footer CTA is conditional: if the user has no active mission (checked via `fetchActiveMission()` — existing endpoint, no new surface), the CTA reads **"Start a Mission sprint"** and links to `/learn/mission`; if an active mission already exists, the CTA reads **"View mission"** and links to the active mission. This is the organic place to surface the Mission Mode conversion prompt — after the countdown exists and the user has felt the urgency — not before.
2. **Interview Target** — displays `user.interview_target_company` + `user.interview_target_date`. **Display-only in S18. No Edit action.** When the persona-switch UX spec is written, the widget gains an Edit action wired to the new flow. A `/profile` fallback was considered and rejected because it leads users to a page that doesn't actually expose persona editing — a worse UX than display-only.
3. **Today's Review** — `fetchDailyQueue()` → `total_due`. Shows "N cards due today." Action: "Start review" → `/learn/daily`. Empty state: "You're all caught up — no cards due today."
4. **Last Scan** — derived from `getApplications()` (sorted by `created_at` desc, take first). Shows company + role + ATS score. Action: "View results" → `/prep/results?scan_id=<id>`. Empty state: "Run your first scan to see results here." → `/prep/analyze`.

#### Career-Climber (`home-mode-career_climber`)

1. **Streak** — `useGamification()` → `current_streak`, `longest_streak`. Shows current streak prominently + longest as context. Action: "View profile" → `/profile`. Empty state (`current_streak === 0`): "Start your streak — review a card today." → `/learn/daily`.
2. **Today's Review** — same contract as IP.
3. **Weekly Progress** — wraps `src/components/progress/ActivityHeatmap.tsx`. Data source: `/api/v1/progress` (existing per AGENTS.md). Empty state when the user has no review history: "Review your first card to see your activity heatmap." → `/learn/daily`.
4. **Last Scan** — same contract as IP (derived from `getApplications()`).

#### Team Lead (`home-mode-team_lead`)

1. **Today's Review** — same contract (TL users still learn personally).
2. **Streak** — same contract.
3. **Weekly Progress** — same contract.
4. **Team Coming Soon** — a static `TeamComingSoonWidget` with copy "Team dashboards are coming in a future release. For now, here's your personal learning progress." **Action: conditional on codebase state.** Before implementation, grep the repo for an existing waitlist, email capture, or notification-signup component (e.g. `WaitlistForm`, `NotifyMeForm`, or similar). If one exists, the widget's action links to it with label **"Notify me when team features ship"**. If no such component exists, the widget ships with no action and a deferred hygiene item is logged for a future demand-signal infrastructure slice. Claude Code should report which path it took during S18 implementation.

**When the Team dashboards spec (future) is written, this render mode is redesigned in that slice.** The current four-widget Team Lead layout is a bridge, not a durable design.

### Route + Gating

- `/home` — component changes from `HomeDashboardPlaceholder` to `HomeDashboard` in `src/App.tsx`. Route definition, auth guard, and `PersonaGate` placement are unchanged.
- No new routes.
- No new gating — `PersonaGate` (shipped in P5-S17) guarantees `user.persona !== null` on every `/home` mount.

## Data Model

No schema changes. Widget data comes from existing endpoints. The inline date-setter in the Countdown widget writes via the existing `PATCH /api/v1/users/me/persona` endpoint — no new API surface.

If a future widget requires persisted dashboard layout preferences (e.g. user-hidden widgets), that requires a new table and is explicitly out of scope.

## API Contract

Reuses existing endpoints only. No new routes, no new request/response shapes.

| Widget | Endpoint | Method | Source of truth |
|--------|----------|--------|-----------------|
| Countdown | — | — | `user.interview_target_date` from AuthContext |
| Countdown (active-mission check for footer CTA) | `/api/v1/missions/active` | GET (via `fetchActiveMission()`) | existing — drives "Start a Mission sprint" vs "View mission" CTA once a date is set |
| Countdown (set date) | `/api/v1/users/me/persona` | PATCH | existing — shipped in P5-S16 |
| Interview Target | — | — | `user.interview_target_company` + `user.interview_target_date` from AuthContext |
| Today's Review | `/api/v1/study/daily` | GET | existing |
| Last Scan | `/api/v1/tracker` | GET (via `getApplications()`) | existing — **no dedicated `/analyze/latest`** endpoint; the widget derives from the tracker list. This is a known trade-off (see §Resolved Decisions item 3 + §Future Widgets → Future Endpoints) |
| Streak | `/api/v1/gamification/stats` | GET (via `useGamification()`) | existing |
| Weekly Progress | `/api/v1/progress` | GET | existing |
| Team Coming Soon | — | — | static copy |

The Last Scan derivation is the only non-obvious call. An alternative — adding `GET /api/v1/analyze/latest` as a dedicated endpoint — was considered and deferred; see §Resolved Decisions item 3 + §Future Widgets → Future Endpoints for the promotion trigger.

## Acceptance Criteria

- **AC-1** — `HomeDashboard` renders three distinct render modes keyed off `user.persona`. Verified by a Vitest test that mounts `<HomeDashboard>` with each of the three persona values and asserts `queryByTestId('home-mode-interview_prepper')`, `queryByTestId('home-mode-career_climber')`, `queryByTestId('home-mode-team_lead')` each resolve in their respective render.
- **AC-2** — Every widget composes `DashboardWidget` and is driven by the `state` prop. Verified by a `DashboardWidget.test.tsx` suite: loading state renders `<SkeletonCard>`, empty state renders `emptyMessage`, error state renders `errorMessage` + `Try again` button (calls `onRetry`), data state renders `children` + `action`.
- **AC-3** — Each persona render mode includes the widgets listed in §Widget Catalog in the specified order. Verified per render mode using explicit `getByTestId` assertions (matches spec #34's plain-string testid convention; no regex matchers):

  **Interview-Prepper:**
  ```tsx
  expect(getByTestId('widget-countdown')).toBeInTheDocument();
  expect(getByTestId('widget-interview-target')).toBeInTheDocument();
  expect(getByTestId('widget-todays-review')).toBeInTheDocument();
  expect(getByTestId('widget-last-scan')).toBeInTheDocument();
  ```

  **Career-Climber:**
  ```tsx
  expect(getByTestId('widget-streak')).toBeInTheDocument();
  expect(getByTestId('widget-todays-review')).toBeInTheDocument();
  expect(getByTestId('widget-weekly-progress')).toBeInTheDocument();
  expect(getByTestId('widget-last-scan')).toBeInTheDocument();
  ```

  **Team Lead:**
  ```tsx
  expect(getByTestId('widget-todays-review')).toBeInTheDocument();
  expect(getByTestId('widget-streak')).toBeInTheDocument();
  expect(getByTestId('widget-weekly-progress')).toBeInTheDocument();
  expect(getByTestId('widget-team-coming-soon')).toBeInTheDocument();
  ```

  Order is asserted by reading the DOM node sequence (e.g. `container.querySelectorAll('[data-testid^="widget-"]')`) and comparing the resulting testid list to the expected array per persona.
- **AC-4** — Each widget handles loading → data transition. Verified by mocking each widget's API at the hook layer: initial render shows `SkeletonCard`; after resolve, the widget renders data. (One test per widget, with a shared test helper.)
- **AC-5** — Each widget renders its documented empty state when the underlying data is empty/zero. Examples:
  - `TodaysReviewWidget` when `total_due === 0` → "You're all caught up…"
  - `LastScanWidget` when `getApplications()` returns `[]` → "Run your first scan to see results here."
  - `StreakWidget` when `current_streak === 0` → "Start your streak — review a card today."
- **AC-6** — Each widget renders its documented error state with a retry action. Verified by mocking the underlying API to reject; widget renders `errorMessage` + `Try again`; clicking triggers a re-fetch.
- **AC-7** — `home_dashboard_viewed` fires exactly once on mount with `{persona: user.persona}`. Implementation must use a `useRef` idempotency guard so React Strict Mode's double-invoked `useEffect` fires the capture only once. Test asserts `posthog.capture` has been called exactly once with the correct shape, even under Strict Mode mounting.
- **AC-8** — `user.persona === null` users do not reach `HomeDashboard` — `PersonaGate` redirects them to `/onboarding/persona` first. Covered by existing `PersonaGate.test.tsx` (P5-S17) — no new test needed; the spec only requires no regression.
- **AC-9** — `CountdownWidget` with `user.interview_target_date === null` renders the inline date-setter. Submitting the date calls `updatePersona({ persona: user.persona, interview_target_date: <value> })` and, on success, flips the widget to countdown mode. `persona` is a required field on `PATCH /api/v1/users/me/persona` per spec #34 §API Contract; the widget includes the user's current persona to satisfy the validator.
- **AC-10** — Theme tokens only — no hardcoded hex values in any widget file. Verified by grep during review; not a runtime assertion.

## Test Plan

Vitest + React Testing Library. Test file structure mirrors source structure.

### New test files

1. **`tests/HomeDashboard.test.tsx`** — page-level tests. One test per persona render mode (3 cases), plus `home_dashboard_viewed` analytics assertion, plus the three-mode data-testid assertions. ~5 cases.
2. **`tests/home/DashboardWidget.test.tsx`** — primitive contract tests: loading → `SkeletonCard`, empty → `emptyMessage`, error → `errorMessage` + retry, data → `children` + `action`, testid attribute shape, accessibility (title is a heading). ~6 cases.
3. **`tests/home/widgets/*.test.tsx`** — one file per widget (7 widgets): loading → data → empty → error for each. Shared helper to mock the underlying API. ~3–4 cases each → ~24 cases across the seven widgets.

### Test count target

| Baseline (post-S17) | Delta (S18) | Target (post-S18) |
|---|---|---|
| 38 frontend | +~35 (5 + 6 + 24) | ≥ 73 frontend |

Backend test count unchanged (no backend work in this slice). Baseline 184 unit + 6 integration deselected stays.

### Visual regression

Not automated. Manual check on `/home` for all three personas (Storybook not in the stack). Spec #34's AC-6 AppShell-hide pattern stays green — nav chrome continues to render on `/home` (it's not on the hide list).

## Files Touched (planned — no code in this slice)

### Frontend

- `hirelens-frontend/src/pages/HomeDashboard.tsx` — **new**.
- `hirelens-frontend/src/pages/HomeDashboardPlaceholder.tsx` — **delete**.
- `hirelens-frontend/src/components/home/DashboardWidget.tsx` — **new**.
- `hirelens-frontend/src/components/home/widgets/CountdownWidget.tsx` — **new**.
- `hirelens-frontend/src/components/home/widgets/InterviewTargetWidget.tsx` — **new**.
- `hirelens-frontend/src/components/home/widgets/TodaysReviewWidget.tsx` — **new**.
- `hirelens-frontend/src/components/home/widgets/LastScanWidget.tsx` — **new**.
- `hirelens-frontend/src/components/home/widgets/StreakWidget.tsx` — **new**.
- `hirelens-frontend/src/components/home/widgets/WeeklyProgressWidget.tsx` — **new**.
- `hirelens-frontend/src/components/home/widgets/TeamComingSoonWidget.tsx` — **new**.
- `hirelens-frontend/src/App.tsx` — swap `HomeDashboardPlaceholder` import/usage for `HomeDashboard`.
- `hirelens-frontend/tests/HomeDashboard.test.tsx` — **new**.
- `hirelens-frontend/tests/home/DashboardWidget.test.tsx` — **new**.
- `hirelens-frontend/tests/home/widgets/*.test.tsx` — **new** (7 files).

### Docs + state

- `AGENTS.md` — Frontend Routes table: change `/home` row component from `HomeDashboardPlaceholder` to `HomeDashboard`.
- `.agent/skills/analytics.md` — add `home_dashboard_viewed` row under Frontend Events (shape pre-defined in spec #34 §Analytics).
- `SESSION-STATE.md` — end-of-slice update per §Update Protocol.

### Explicitly NOT touched

- `hirelens-backend/**` — no backend work in this slice.
- `hirelens-frontend/src/components/dashboard/` — **not** the target folder. ATS-results domain; leave alone.
- `hirelens-frontend/src/context/**` — no context changes. All widget data comes from existing contexts (Auth, Gamification) or existing fetch helpers.

## Out of Scope

- **State-aware dashboard variants** (new user / returning user / streak-at-risk / interview-imminent) — P5-S18b. S18 ships the static layout; S18b layers state detection on top.
- **Interview-Prepper guided checklist depth** — P5-S18c.
- **Drag-to-reorder or user-customized widget layout** — not planned; re-evaluate post-Phase-5 based on user research.
- **Widget-level analytics** (`widget_opened`, `widget_clicked`, etc.) — explicitly deferred. Rationale: we don't yet know what to optimize, and premature widget events pollute the catalog (per the P5-S17 lesson where two persona events had to be deprecated rather than renamed because dashboards referenced them by name). Revisit when a specific optimization question demands the data.
- **Team Lead real team dashboards** — requires the Team dashboards spec (PRD §1.5 P3 Future). When that ships, the Team Lead render mode in this spec is redesigned.
- **Persona-switch UX from `/profile`** — still deferred per spec #34 Out of Scope. Per §Resolved Decisions item 6, the `Interview Target` widget is display-only in S18 (no Edit action); the Edit affordance returns when the persona-switch UX spec ships.
- **New "Gap Coverage" / "Recent Cards" / "Recent Patterns" widgets** — see §Future Widgets.
- **Dedicated `GET /api/v1/analyze/latest` endpoint** — see §Resolved Decisions item 3 + §Future Widgets → Future Endpoints. Last Scan widget derives from `getApplications()` in S18.
- **Path rename `/auth/me` → `/users/me`** — Phase 6 cleanup (touches many frontend callers).

## Future Widgets

Three widgets were considered but deliberately omitted from the S18 catalog because their backing data sources do not exist. Listed here so the next maintainer can find them with one grep:

- **Gap Coverage (Interview-Prepper)** — Intent: show "7 of your 12 resume gaps have cards available" with a CTA into those categories. **Blocked on:** a new endpoint that joins the latest scan's `skills_missing` with available cards per category. Could reuse the onboarding gap→card bridge (`/api/v1/onboarding/recommendations`), but that endpoint keys off a specific `scan_id`, not "latest scan." **Priority: HIGH** — this widget is the visible surface of the core scan → study → rescan loop that the PRD positions as the product's flywheel (§1.1 "close the loop"). Write a follow-up spec before Phase 5 closes.
- **Recent Cards (Career-Climber)** — Intent: show the last 3–5 cards reviewed with a "review again" quick action. **Blocked on:** a recent-cards endpoint (would need `GET /api/v1/study/recent?limit=5` backed by a query on `card_progress` ordered by `updated_at`). **Priority: NICE-TO-HAVE** — not blocking the core loop; pure retention flavour.
- **Recent Patterns (Team Lead)** — Intent: surface "3 team members hit a streak milestone this week" or similar team-scoped signals. **Blocked on:** Team features being built (PRD §1.5 P3 Future). **Priority: BLOCKED** — not actionable until the Team dashboards spec is written.

### Future Endpoints

Promote Last Scan to a dedicated `GET /api/v1/analyze/latest` endpoint if the widget shows traction via a future `widget_clicked` analytics signal. The S18 client-side derivation from `getApplications()` is sufficient at current scale; a dedicated endpoint earns its keep only with evidence of use.

## Analytics

- **`home_dashboard_viewed`** — already defined in spec #34 §Analytics with `{persona: PersonaEnum}`. This slice lands the entry in `.agent/skills/analytics.md` and wires the `useEffect`-on-mount `capture` call in `HomeDashboard.tsx`. Not redefined here.
- **No widget-level events in S18.** Explicit per §Out of Scope. When a specific optimization question demands widget signal (e.g., "which widget drives the most `daily_review_started`?"), a follow-up spec adds `widget_clicked` with `{widget_id, persona}` — but not pre-emptively.

## Resolved Decisions

Design calls this spec makes that could reasonably go another way. All six were walked through and decided before this spec shipped; each entry records the question, the decision, and one-line reasoning so a future contributor knows the call was deliberate.

1. **Countdown widget empty state.** — **DECIDED: inline date-setter.** The widget renders `<input type="date">` + save → `updatePersona({ persona, interview_target_date })`, and once a date is set, the footer CTA organically offers "Start a Mission sprint" → `/learn/mission`. **Reasoning:** friction-level match — a single widget shouldn't gate on a multi-step Mission-creation flow. Mission Mode becomes the organic *next* step after the countdown exists and urgency has been felt, not a prerequisite to feeling urgency. Conversion funnel integrity preserved by the post-date CTA; friction minimized by inline entry.

2. **Widget grid breakpoints.** — **DECIDED: 1/2/3 (Tailwind standard).** `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6`. **Reasoning:** matches general dashboard convention, scales cleanly for future personas with 5–6 widgets (current max is 4), and stays legible on tablet without squeezing two widgets into a cramped row.

3. **Last Scan data source.** — **DECIDED: derive from `getApplications()` in S18.** No new backend endpoint. **Reasoning:** no evidence of traction yet for a Home-surface "last scan" card. Promote to a dedicated `GET /api/v1/analyze/latest` endpoint if a future `widget_clicked` signal justifies it (see §Future Widgets → Future Endpoints). Ship lean; earn the endpoint.

4. **Greeting copy.** — **DECIDED: static `Welcome back, <first name>.`** With empty-name fallback to `Welcome back.` (no placeholder). **Reasoning:** minimal warmth without localization complexity. Time-of-day greetings ("Good morning") require timezone logic for trivial upside; omitting the greeting entirely trades warmth for nothing. Status quo with a graceful fallback wins.

5. **Team Coming Soon placeholder action.** — **DECIDED: conditional on codebase state.** If an existing waitlist/email-capture/notify-me component is found during S18 implementation, the widget's action links to it with label "Notify me when team features ship"; otherwise the widget ships action-less and a deferred hygiene item is logged for a future demand-signal infrastructure slice. **Reasoning:** don't build a new backend surface (waitlist form, storage, email routing) for a single placeholder widget; reuse what exists. The deferral still captures the demand-signal intent without blocking S18.

6. **`Interview Target` widget "Edit" action target.** — **DECIDED: hide the action entirely in S18.** Display-only. When the persona-switch UX spec is written, the widget gains an Edit action wired to the new flow. **Reasoning:** a `/profile` fallback is a dead-end UX — it leads users to a page that doesn't expose persona editing, which is worse than no action at all. Display-only is honest; the Edit affordance returns with the persona-switch flow.

## Notes on spec #34 continuity

- Spec #34's AC-5 (render-mode branching via `data-testid="home-mode-<persona>"`) is re-asserted as AC-1 here — spec #35 doesn't weaken it.
- Spec #34 §Files Touched already pre-listed `HomeDashboard.tsx` (new), `HomeDashboardPlaceholder.tsx` (delete), `tests/HomeDashboard.test.tsx` (new) under the "P5-S18 — widget catalog owned by that spec" subsection. This spec owns those files and extends the list with the `DashboardWidget` primitive + per-widget files + per-widget tests.
- Spec #34 §Analytics pre-registered `home_dashboard_viewed`. Spec #35 does not redefine — just points to the original definition and lands the catalog entry.

---

*End of spec. No code in this slice. All §Resolved Decisions are locked; implementation begins on Dhamo's go-ahead.*
