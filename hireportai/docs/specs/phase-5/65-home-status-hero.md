# P5-S65 — Status-sentence hero on `/home` for B2C personas

## Status: 🔴 Drafted (combined spec + impl this slice)

| Field | Value |
|-------|-------|
| **Slice** | P5-S65 (FE-only; combined spec-author + implementation in one slice) |
| **Phase** | 5D (persona-aware home surface) |
| **Mode** | Mode 2 — implement-to-spec; spec authored inline at Step 1, §12 carries pre-locked decisions, impl ships in the same commit. |
| **BACKLOG row (impl)** | **B-120** — filed at 🔴 by this slice and immediately flipped to ✅ in the same commit. Mirrors single-slice file+close precedent (B-105 / B-113 / B-114 / B-115 / B-116 / B-117 / B-118). R17 watermark verified at slice start: B-119 highest in-use, B-120 next-free. |
| **Closes** | **E-050** (status-sentence hero on `/home` for both B2C personas) on commit. R15(c) cascade close from B-120 ship. |
| **Depends on** | spec #34 (PersonaPicker + persona-aware HomeDashboard foundation; shipped) ▪ spec #35 / P5-S18 (HomeDashboard widget catalog; shipped `5e1f56c`) ▪ spec #40 / P5-S18b (state-aware priority slot; shipped `55ac7bd`) ▪ spec #44 (widget empty-state contract; shipped) ▪ spec #61 (composition rules; shipped `ecef895`) ▪ spec #57 (`homeState.context.next_interview` envelope; shipped `b13f410`) ▪ B-016 / B-027 (first-visit greeting fork; shipped `e792bb4`) ▪ existing `useHomeState()` hook ▪ existing `fetchDailyQueue()` + `fetchUserApplications()` API clients. |
| **Blocks** | E-051 (live loop-progress strip in AppShell — consumes the persona-driven hero pattern proven on `/home`). E-053 (CC habit ribbon + skill-radar trend block — composes BELOW this hero on CC mode). |
| **Cross-refs** | spec #34 / #35 / #40 / #44 / #61 (the four predecessor specs governing `HomeDashboard.tsx` — see §10 composition interactions) ▪ spec #64 / E-049 / B-119 (`LoopFrame` step-copy contract — orthogonal surface but shared visual language with E-051) ▪ E-053 (CC 30-day topic-trend — owns the CC trend clause this spec defers) ▪ `.agent/skills/design-system.md` (R12 token-only styling) ▪ `.agent/skills/analytics.md` (event catalog discipline) ▪ `.agent/skills/home.md` (state-aware home dashboard map). |

---

## 1. Problem

`/home` opens with the affective greeting line `"Welcome back, ${firstName}."` (B-016 / B-027). Below the greeting, three to five widgets render persona-keyed details — streak count, today's review count, last scan score, interview countdown — but no single line tells the user **where they are in the loop**. The greeting is warm; it is not informative. A first-time scanner who comes back the next day sees "Welcome back, Dhamo." and then has to scan four widget cards to assemble the same single sentence in their head: "Google interview in 12 days. 5 cards due today. Last scan was 71%."

The status hero is that one-line summary, rendered above the persona modes. It does **not** replace the greeting — the two coexist (greeting = emotional hook, hero = state summary). Suppressing widgets on the basis that the hero now restates them is forward work tracked on the BACKLOG row's §13 — this spec is additive-only.

### 1.1 What's already shipped (out of scope this spec)

- **Greeting fork** — B-016 first-visit / B-027 `useState` snapshot at `e792bb4`. The hero renders **below** the greeting; the greeting state machine is byte-untouched.
- **State-aware priority slot** — spec #40, `<StateAwareWidgets>` mounted between greeting and persona-mode JSX. The hero renders **between greeting and state slot**, NOT through the state-aware layer (state slot reserved for time-sensitive urgency signals; the hero is a steady-state ambient summary). Same layering decision as `StudyGapsPromptWidget` (spec #61 §6.3).
- **Composition suppression flags** — spec #61 §3 widget suppression. The hero does not extend the suppression matrix; it composes alongside whatever widgets the matrix decides to render.

### 1.2 What this spec ships

A single new FE component, `<HomeStatusHero>`, mounted on `/home` between the greeting `<h1>` and the existing `<StateAwareWidgets>` slot, rendering one sentence whose copy is keyed off `user.persona`. No live state subscription, no backend work, no schema changes. One new analytics event.

---

## 2. Goals

- **G-1** Render a one-line status sentence on `/home` for personas `interview_prepper` and `career_climber` that compresses the user's loop position into a single glanceable summary.
- **G-2** Reuse existing data sources (`useHomeState()`, `fetchDailyQueue()`, `fetchUserApplications()`); zero new BE endpoints.
- **G-3** Coexist with the existing greeting (`<h1>`), the state-aware priority slot, and `StudyGapsPromptWidget` without changing any of their behavior.
- **G-4** Establish the persona-driven hero pattern that E-051 (live loop strip) and E-053 (CC habit ribbon) inherit.

---

## 3. Non-goals

- Replacing the greeting line — additive only this slice; replacement is a future E-050b decision contingent on telemetry showing the hero makes the greeting redundant (§12 D-2).
- Suppressing `StreakWidget`, `TodaysReviewWidget`, `LastScanWidget`, or any other static-grid widget on the basis of multiple emphasis (BACKLOG row's §13 forward work; not extended into spec #61 §3 matrix).
- The Career-Climber 30-day topic-trend clause ("RAG up 18% this month") — owned by E-053 which carries the BE field requirement (§12 D-4).
- A `team_lead` variant (renders `null` for now; §12 D-8).
- Mobile-specific layout beyond the existing AppShell handling (one line of text, design tokens; no mobile-only branch).
- Any change to BE — no schema, no migration, no endpoint, no service, no `home_state_service` priority change.
- Any change to `HomeDashboard.tsx` outside the single insertion point (greeting `<h1>` and the three persona-mode functions stay byte-identical).

---

## 4. Architecture

Single new component at `src/components/home/HomeStatusHero.tsx`:

```
┌── HomeDashboard.tsx (existing) ────────────────────────────────┐
│  <h1>Welcome[, back] {firstName}.</h1>     ← greeting (B-016/B-027) │
│                                                                │
│  <HomeStatusHero />                        ← NEW (this spec)   │
│                                                                │
│  <StateAwareWidgets ... />                 ← spec #40 slot     │
│  <StudyGapsPromptWidget ... />             ← spec #61 §4       │
│  {persona === 'interview_prepper' && <InterviewPrepperMode/>} │
│  {persona === 'career_climber' && <CareerClimberMode/>}       │
│  {persona === 'team_lead' && <TeamLeadMode/>}                 │
└────────────────────────────────────────────────────────────────┘
```

`<HomeStatusHero>` reads from existing hooks and emits one `<p>` of text plus one PostHog event. No props.

---

## 5. Data model

No BE changes. Disk-fact references the component reads:

| Field | Source on disk | Used by |
|-------|----------------|---------|
| `user.persona` | `useAuth()` → `AuthUser.persona` (`'interview_prepper' \| 'career_climber' \| 'team_lead' \| null`) | Render gate (D-8) + copy branch |
| `homeState.data.context.next_interview.{date, company, tracker_id}` | `useHomeState()` → `HomeStateContext.next_interview: NextInterview \| null` (spec #57) | IP "company" + "Nd" clauses |
| `homeState.data.context.current_streak` | `useHomeState()` → `HomeStateContext.current_streak: number` | CC "streak" clause |
| `homeState.data.context.plan` | `useHomeState()` → `HomeStateContext.plan` | Analytics property |
| `fetchDailyQueue().total_due` | `services/api.ts` → `DailyQueueResponse.total_due: number` | "${dueCount} cards due today" / "No cards due today" clauses (both personas) |
| `fetchUserApplications()[0].ats_score` (sorted desc by `created_at`) | `services/api.ts` → `TrackerApplication.ats_score: number` | IP "Last scan was ${score}%" clause. **Note (JC #2):** §12 D-3's prompt-body wording said "from homeState.context"; on-disk `HomeStateContext` carries `last_scan_date` only (no `ats_score`). This spec uses `fetchUserApplications()` mirroring `LastScanWidget` (`src/components/home/widgets/LastScanWidget.tsx:24-40`). Same fetcher already mocked in `tests/HomeDashboard.test.tsx`. |

The component is a pure read consumer. No mutation, no state derivation that escapes the mount, no cache writes.

---

## 6. API contract

No BE endpoint changes. The component re-uses three existing API client functions: `fetchHomeState` (via `useHomeState()`), `fetchDailyQueue`, `fetchUserApplications`. None of these gain new query params or response fields.

---

## 7. Routing / nav

No route changes. Mount point is `pages/HomeDashboard.tsx` (existing route `/home`).

---

## 8. UI / UX

### 8.1 Render-gate (§12 D-8)

| Condition | Behavior |
|-----------|----------|
| `user == null \|\| user.persona == null` | `return null` (the existing `if (!user \|\| !user.persona) return null` guard in HomeDashboard already prevents the hero from mounting in this case; defensive `return null` here is belt-and-suspenders) |
| `user.persona === 'team_lead'` | `return null` |
| `user.persona === 'interview_prepper'` | Render IP branch (§8.2) |
| `user.persona === 'career_climber'` | Render CC branch (§8.3) |

### 8.2 Interview-Prepper copy template (§12 D-3)

Template clauses (joined with `' '`, omitted clauses do not contribute joining whitespace):

| Clause | Template | Renders when |
|--------|----------|--------------|
| Interview line | `${company} interview in ${days}d.` | `next_interview != null && days >= 0` AND `next_interview.company` truthy |
| Interview line (no company) | `Interview in ${days}d.` | `next_interview != null && days >= 0` AND `next_interview.company` falsy |
| (no interview clause) | — | `next_interview == null \|\| days < 0` |
| Cards-due line | `${dueCount} cards due today.` | `dueCount > 0` (after `fetchDailyQueue()` resolves) |
| Cards-due (zero) | `No cards due today.` | `dueCount === 0` (after fetch resolves) |
| Cards-due (loading/error) | — (omitted entirely until resolution; no fallback copy) | `dueCount == null` (pre-fetch or fetch failed) |
| Last-scan line | `Last scan was ${score}%.` | `latestApp != null && latestApp.ats_score != null` |
| Last-scan (none / loading) | — | otherwise |

**Examples** (rendered single line, separated by single spaces):
- All three: `Google interview in 12d. 5 cards due today. Last scan was 71%.`
- No company: `Interview in 12d. 5 cards due today. Last scan was 71%.`
- No interview: `5 cards due today. Last scan was 71%.`
- No scan: `Google interview in 12d. 5 cards due today.`
- Zero due: `Google interview in 12d. No cards due today. Last scan was 71%.`
- Cold start (no interview, no scan, fetched zero due): `No cards due today.`
- All clauses unresolved: `null` (component renders nothing — see §8.5 loading semantics).

`days` is computed from `next_interview.date` (ISO `YYYY-MM-DD`) using `Math.ceil((targetMs - todayMs) / 86400000)` rounded against today's local midnight. `days < 0` (interview in the past) suppresses the interview clause entirely.

### 8.3 Career-Climber copy template (§12 D-4)

| Clause | Template | Renders when |
|--------|----------|--------------|
| Streak line (active) | `${streak}-day streak.` | `current_streak > 0` |
| Streak line (zero) | `Start your streak today.` | `current_streak === 0` AND `homeState.data != null` (i.e. resolved with zero, not still loading) |
| Cards-due line | `${dueCount} cards due today.` | `dueCount > 0` |
| Cards-due (zero) | `No cards due today.` | `dueCount === 0` |
| Cards-due (loading/error) | — | `dueCount == null` |

**Examples:**
- Both: `14-day streak. 5 cards due today.`
- No streak: `Start your streak today. 5 cards due today.`
- Zero due, active streak: `14-day streak. No cards due today.`
- Both unresolved: `null`.

The 30-day topic-trend clause from the BACKLOG row's CC scope ("RAG up 18% this month") is **deferred to E-053** which owns the BE field requirement (§3 non-goal; §12 D-4).

### 8.4 Styling (§12 D-7)

- One `<p>` element, no nested layout.
- Font size `text-lg` (matches the existing greeting's body-line scale at `sm:text-3xl` heading and a one-step-down body line).
- Color `text-text-secondary` (intentionally one tier subordinate to the greeting's `text-text-primary` to preserve visual hierarchy: greeting first, then status).
- Spacing `mb-6` (above the existing `<StateAwareWidgets>` block; greeting has `mb-8`, hero takes a tighter gap so the two read as a paired hero block).
- All design tokens; zero hardcoded hex per R12.
- `data-testid="home-status-hero"` for test selectors.

### 8.5 Loading / error semantics

The component renders `null` when **all** clauses for the current persona are unresolved (i.e. nothing to say yet). It renders the resolved subset otherwise — partial copy is preferred to a placeholder. No skeleton card, no spinner: the hero is one line, and showing "loading…" briefly is more visual noise than the line itself.

`fetchDailyQueue` and `fetchUserApplications` failures resolve to "no clause" (matching the loading state). Errors are silent — the hero never throws and never renders an error string. The widgets below the hero own their own error UX; the hero is informational only.

---

## 9. Telemetry (§12 D-6)

### 9.1 New event

| Event | Source | Properties | Fires |
|-------|--------|------------|-------|
| `home_status_hero_rendered` | `src/components/home/HomeStatusHero.tsx` | `{persona: 'interview_prepper' \| 'career_climber', plan: 'free' \| 'pro' \| 'enterprise', clauses_shown: string[]}` | Once per mount via `useRef` idempotency guard, after at least one clause has resolved (i.e. the hero has rendered visible text). Not before — firing while the component is rendering `null` would skew "rendered" telemetry. |

`clauses_shown` enumerates the template slots that contributed visible copy on this mount. IP enum values: `'company'`, `'days'`, `'due'`, `'due_zero'`, `'score'`. CC enum values: `'streak'`, `'streak_zero'`, `'due'`, `'due_zero'`. Example: `["company", "days", "due", "score"]` for the all-clauses IP path; `["streak", "due_zero"]` for an active-streak CC user with zero cards due. The array tells us which slots had data vs which fell back to fixed copy — equivalent to the prompt's planned `home_status_hero_data_missing` second event but in one fire instead of two (D-6 collapse).

### 9.2 Existing events touched

None. `home_dashboard_viewed`, `home_state_evaluated`, `home_study_gaps_prompt_shown` all fire unchanged.

### 9.3 Catalog update

`.agent/skills/analytics.md` gains one new row inserted after the `home_study_gaps_clicked` row (line 75) and before the `loop_frame_rendered` row (line 76) to keep the home-surface events grouped.

---

## 10. Composition interactions (spec-graph)

This is the **fifth** spec governing `HomeDashboard.tsx` (after #34, #35, #40, #44, #61). What this spec extends vs preserves vs is orthogonal to:

| Predecessor | Relationship |
|-------------|--------------|
| **spec #34** (PersonaPicker + persona-aware home foundation) | **Extends** the persona-awareness contract — the hero reads `user.persona` to pick the copy variant, mirroring how the persona-mode functions (`InterviewPrepperMode` / `CareerClimberMode` / `TeamLeadMode`) branch. No change to the persona enum, no change to PersonaGate, no change to `/onboarding/persona`. |
| **spec #35** (P5-S18 widget catalog) | **Preserves** — every widget in `InterviewPrepperMode` / `CareerClimberMode` / `TeamLeadMode` continues to render. The hero is a sibling of the persona-mode JSX, not a wrapper or replacement. |
| **spec #40** (P5-S18b state-aware priority slot) | **Preserves** — `<StateAwareWidgets>` continues to mount in the same DOM position; the hero renders ABOVE it. The state slot is for time-sensitive urgency signals (mission-overdue, streak-at-risk, etc.); the hero is steady-state ambient. Two distinct layers, no shared logic, no shared state. Same layering rationale as `StudyGapsPromptWidget` per spec #61 §6.3. |
| **spec #44** (widget empty-state contract) | **Preserves** — spec #44's contract applies to widgets under `src/components/home/widgets/`. The hero lives at `src/components/home/HomeStatusHero.tsx` (one level up — sibling to `widgets/`, not inside it) and is not a `DashboardWidget` instance. Empty-state behavior in the hero is governed by §8.5 of this spec (render `null` when nothing to say) which is shape-equivalent to spec #44 rule 3(b) "hide the widget entirely." Cross-component invariant intact. |
| **spec #61** (composition rules) | **Preserves** — the §3 widget suppression matrix is unchanged. The hero does not enter the matrix. The §4 `StudyGapsPromptWidget` continues to mount per its existing predicates. The §6 plan-aware state-slot extension is unchanged. |
| **B-016 / B-027** (greeting fork) | **Preserves** — the `useState`-snapshot first-visit/return-visit fork at `HomeDashboard.tsx:183-185` plus the `markHomeFirstVisit` stamp effect plus the `<h1>` greeting are all byte-untouched. The hero renders BELOW the `<h1>`. |
| **spec #57** (`next_interview` envelope) | **Consumes** — reads `homeState.data?.context.next_interview` per the shipped contract. Same source `LoopFrame` consumes (spec #64) — single source of truth for "user's nearest interview." |
| **spec #64 / E-049** (LoopFrame on `/prep/results`) | **Orthogonal** — different surface (`/prep/results` not `/home`), different visual primitive (4-step strip not 1-line sentence). Shared visual language is locked at E-051, not here. The hero copy does not reference the loop-step labels. |

---

## 11. Acceptance criteria

| AC | Surface | Trigger | Expected behavior | Test harness |
|----|---------|---------|-------------------|--------------|
| **AC-1** | `<HomeStatusHero>` | persona=`interview_prepper`, `next_interview = {date: <today+12>, company: 'Google', tracker_id: 't-1'}`, `fetchDailyQueue` returns `{total_due: 5}`, `fetchUserApplications` returns one app with `ats_score: 71` | Renders `<p data-testid="home-status-hero">Google interview in 12d. 5 cards due today. Last scan was 71%.</p>` | Vitest render + `getByTestId('home-status-hero')` text assertion |
| **AC-2** | `<HomeStatusHero>` | persona=IP, all four data sources resolve to null/zero/empty | Renders fallback copy combining "Interview in" omitted, `No cards due today.`, no scan clause | Vitest render + text assertion (specifically `No cards due today.` only, since interview + scan clauses omit) |
| **AC-3** | `<HomeStatusHero>` | persona=IP, `next_interview = null`, daily=5, latestApp=null | Renders `5 cards due today.` only | Vitest render + text assertion |
| **AC-4** | `<HomeStatusHero>` | persona=`career_climber`, `current_streak = 14`, `fetchDailyQueue` → 5 | Renders `14-day streak. 5 cards due today.` | Vitest render + text assertion |
| **AC-5** | `<HomeStatusHero>` | persona=CC, `current_streak = 0`, daily=5 | Renders `Start your streak today. 5 cards due today.` | Vitest render + text assertion |
| **AC-6** | `<HomeStatusHero>` | persona=CC, daily=0 | Renders `No cards due today.` clause (with whatever streak clause applies) | Vitest render + text assertion |
| **AC-7** | `<HomeStatusHero>` | persona=`team_lead` | Renders nothing (`queryByTestId('home-status-hero')` returns null) | Vitest render + null assertion |
| **AC-8** | `<HomeStatusHero>` | `user.persona == null` | Renders nothing | Vitest render + null assertion |
| **AC-9** | `<HomeStatusHero>` | persona=IP, all clauses resolve | `home_status_hero_rendered` fires exactly once with `{persona: 'interview_prepper', plan: 'free', clauses_shown: ['company', 'days', 'due', 'score']}` | Vitest spy on `capture` + assert call count + props |
| **AC-10** | `HomeDashboard` regression | All existing `tests/HomeDashboard.test.tsx` cases | Pass without modification beyond a one-line `vi.mock('@/components/home/HomeStatusHero', ...)` to keep persona-mode focus | Existing suite re-run |

---

## 12. Locked Decisions

Pre-locked from the prompt before Step 1; no §12 amendment commit needed.

| ID | Decision |
|----|----------|
| **D-1** | **Mount position.** New `<HomeStatusHero>` mounts in `HomeDashboard.tsx` between the greeting `<h1>` (line 213-215) and the existing `<StateAwareWidgets>` slot (line 216). Sibling of the persona-mode JSX, NOT inside `InterviewPrepperMode` / `CareerClimberMode`. Reads persona from `useAuth()` and renders the right copy variant. |
| **D-2** | **Greeting coexistence.** B-016 first-visit/return-visit fork + B-027 `useState` snapshot are byte-untouched. Hero renders BELOW the greeting, not instead of it. Greeting = emotional hook (`text-text-primary`, `font-display`, heading); hero = state summary (`text-text-secondary`, body line). Replacing the greeting is a future E-050b decision contingent on telemetry; this slice is additive-only. |
| **D-3** | **IP copy template.** `${company} interview in ${days}d. ${dueCount} cards due today. Last scan was ${score}%.` Sources: `homeState.context.next_interview` (date + company), `fetchDailyQueue().total_due` (cards due), `fetchUserApplications()[0]` sorted desc by `created_at` (latest scan score — see JC #2 below). Each clause omits gracefully on null/zero/error per §8.2 table. **JC #2 (info-only):** prompt-body D-3 said "latest tracker ats_score from homeState.context"; on-disk `HomeStateContext` carries `last_scan_date` only, no `ats_score`. This spec uses `fetchUserApplications()` mirroring `LastScanWidget` (`src/components/home/widgets/LastScanWidget.tsx:24-40`); same fetcher already mocked in `tests/HomeDashboard.test.tsx`. |
| **D-4** | **CC copy template.** `${streak}-day streak. ${dueCount} cards due today.` Two clauses only. The 30-day topic-trend line is OUT OF SCOPE this slice — forward-filed to E-053 which owns the BE endpoint. No streak (`current_streak === 0`) → `Start your streak today.` |
| **D-5** | **Existing widgets STAY.** `StreakWidget`, `TodaysReviewWidget`, `LastScanWidget` continue rendering per spec #35 + spec #61 composition. Restatement between hero and widgets is accepted as "multiple emphasis" (minimum-viable scope per E-050 BACKLOG row's default lean). Widget suppression is forward work tracked on the row's §13. |
| **D-6** | **Analytics.** One new event `home_status_hero_rendered {persona, plan, clauses_shown: string[]}` fires once on mount via `useRef`. The `clauses_shown` array tells us which template slots contributed visible copy vs which fell back / omitted. Collapses the prompt's originally-planned second event `home_status_hero_data_missing` into the same fire — same telemetry signal, fewer events. |
| **D-7** | **Styling.** One `<p>`, `text-lg`, color `text-text-secondary`, spacing `mb-6`. Design-token-only per R12. `data-testid="home-status-hero"`. |
| **D-8** | **`team_lead` persona.** Renders `null`. Render gate: `user?.persona === 'interview_prepper' \|\| user?.persona === 'career_climber'`. |
| **D-9** | **Component location.** `src/components/home/HomeStatusHero.tsx`. Sibling to `widgets/` (not inside it — not a `DashboardWidget` instance, not bound by spec #44 contract structurally). |
| **D-10** | **Spec-graph interactions.** §10 enumerates relationships with predecessor specs (#34 / #35 / #40 / #44 / #61) and the orthogonal #64. Hero EXTENDS #34's persona-awareness; PRESERVES #35 / #40 / #44 / #61 / B-016 / B-027; CONSUMES #57 envelope; ORTHOGONAL to #64. |

---

## 13. Out of scope (forward work)

- **Greeting replacement** — additive-only this slice; replacement gated on telemetry per D-2.
- **Widget suppression** — `StreakWidget` / `TodaysReviewWidget` / `LastScanWidget` continue rendering per D-5. Future amendment to spec #61 §3 matrix if telemetry shows multiple-emphasis hurts engagement.
- **CC 30-day topic-trend clause** — owned by E-053 (BE field requirement on `quiz_review_events` aggregation).
- **`team_lead` variant** — `null` return per D-8. Future E-### if the persona graduates from "Coming soon" to a shipped surface.
- **Mobile-specific layout** — single line of text, design tokens; no mobile-only branch needed beyond AppShell's existing handling.
- **A/B test on hero placement** (above vs replacing greeting) — telemetry-driven, post-ship.
- **Hero on chromeless paths** (`/login`, `/`, `/onboarding/persona`, `/first-action`) — out of scope. Hero is bound to `/home` via mount point in `HomeDashboard.tsx`.

---

## 14. Open questions

| # | Question | Default if unanswered | Author note |
|---|----------|------------------------|-------------|
| OQ-1 | Should the hero suppress the widget restatement on IP mode in this slice (e.g., hide `LastScanWidget` when the hero shows the score)? | No — additive-only per D-5. Forward work on E-050 row's §13. | Restatement is intentional minimum-viable scope; suppression matrix is a follow-on. |
| OQ-2 | Should the score clause fetch be debounced or cached across mounts? | No — single fetch per mount, no caching. | Mirrors LastScanWidget's pattern (`src/components/home/widgets/LastScanWidget.tsx:24-40`); React Query caching is not in this codebase yet. |
| OQ-3 | Does cold-start (no clauses resolved yet) render `null` or a placeholder line? | `null` per §8.5. | Placeholder line on a one-line component is more visual noise than the line itself. |
| OQ-4 | Is `clauses_shown` the right shape for telemetry vs a flat `has_company`/`has_days`/etc. boolean set? | Array of enum strings. | Lower cardinality on the property surface (one `clauses_shown`) vs N `has_*` properties; PostHog-side filtering is identical via `clauses_shown contains 'score'`. |
| OQ-5 | Should the IP "no company" fallback say `Interview in 12d.` or `Upcoming interview in 12d.`? | `Interview in 12d.` per §8.2. | Shorter; matches the spec's lean default. |

These are author-side notes, not blockers. The default applies.

---

## 15. Test plan

Test file: `tests/components/home/HomeStatusHero.test.tsx` (new, ~9 cases).

**Coverage** (1:1 with §11 ACs unless noted):

1. AC-1 — IP all-clauses (company + days + due + score).
2. AC-2 — IP no-data (only `No cards due today.`).
3. AC-3 — IP no interview (drops interview clause; renders `5 cards due today. Last scan was 71%.`).
4. AC-3 variant — IP no scan (drops scan clause).
5. AC-2 variant — IP zero cards due (renders `No cards due today.`).
6. AC-4 — CC streak + due.
7. AC-5 — CC zero streak (`Start your streak today.`).
8. AC-7 — `team_lead` returns null.
9. AC-8 — null persona returns null.
10. AC-9 — analytics fire-once with correct `clauses_shown`.

**Regression:** `tests/HomeDashboard.test.tsx` gets a one-line `vi.mock('@/components/home/HomeStatusHero', () => ({ HomeStatusHero: () => null }))` so existing persona-mode + widget-order assertions stay focused (consistent with how `StateAwareWidgets` and `StudyGapsPromptWidget` are stubbed in that file).

**Path note:** test lives at `tests/home/HomeStatusHero.test.tsx`, mirroring the existing convention where `src/components/home/<X>.tsx` → `tests/home/<X>.test.tsx` (e.g. `StateAwareWidgets`, `DashboardWidget`). The prompt's path hint `tests/components/home/HomeStatusHero.test.tsx` does not match disk convention.

**Test-count envelope:** target +9 FE (floor +8, ceiling +11). BE unchanged.

---

*End of spec #65. Implementation ships in the same commit per Mode 2 combined slice — no separate impl-author phase.*
