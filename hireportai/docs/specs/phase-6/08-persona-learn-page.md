# Phase 6 — Slice 6.7: Persona-Aware Learn Page (FE Consumer of Slice 6.6 Ranker)

## Status: Drafted — §12 awaits amendment slice locking D-1..D-N from §14 OQ-1..OQ-N

| Field | Value |
|-------|-------|
| **Slice** | 6.7 |
| **Phase** | 6 (Curriculum Platform) |
| **Mode** | Mode 4 spec-author → followed by §12 amendment → impl |
| **Filed at** | `31863dd` (spec-author HEAD pin) |
| **BACKLOG row** | **B-077** 🔴 (filed by this slice) |
| **Depends on** | spec #07 (`5011518` — slice 6.6 ranker BE) ▪ spec #34 (`docs/specs/phase-5/34-persona-picker-and-home.md` — persona render-mode foundation) ▪ spec #61 (`docs/specs/phase-5/61-home-dashboard-composition-rules.md` — `StudyGapsPromptWidget` + suppression matrix) ▪ spec #62 (`docs/specs/phase-5/62-study-dashboard-source-hint.md` — `?source=last_scan` consumer) ▪ spec #09 (`docs/specs/phase-1/09-onboarding-flow.md` — `?category` filter consumer) ▪ spec #03 (slice 6.3 — `pages/Lesson.tsx` already mounts `/learn/lesson/:id`) |
| **Blocks** | none — this is the user-facing surface that activates the slice 6.6 BE in product. Slice 6.15 (cleanup) follows independently to retire the legacy cards/categories tables. |
| **Cross-refs** | scout `docs/audits/phase-6-scout.md` §6 line 945-952 (slice-by-slice 6.7 framing); curriculum.md §8 (ranker contract cliff-notes); design-system.md (R12 token-only styling); analytics.md (`home_*` event convention this slice mirrors). |

---

## 1. Problem

The Lens-ranked-deck BE primitive (slice 6.6, `5011518`) ships
`GET /api/v1/learn/ranked-decks` returning a `RankedDecksResponse`
keyed off the user's most recent ATS-scan skill gaps. Today nothing on
the frontend consumes it. `/learn` still mounts the legacy
`StudyDashboard.tsx` — a categories-grid surface built against the
Phase-5 `cards`/`categories` schema (legacy bridge in
`gap_mapping_service.py`) and unaware of the Phase-6 deck → lesson →
quiz_item domain.

The lens promise the PRD describes — "scan a JD, see your gaps, study
the lessons that close them, re-scan and watch the score climb" — has
no FE landing surface. Without this slice the slice 6.6 ranker is
dead code.

### 1.1 Step 0 audit findings

Audit reads at HEAD `31863dd` (post-SESSION-STATE compaction SHA
backfill, post-slice-6.6 implementation):

1. **`/learn` mount is `StudyDashboard.tsx`**
   (`hirelens-frontend/src/App.tsx:93`). `StudyDashboard` reads the
   Phase-5 categories grid via `useStudyDashboard()`
   (`src/hooks/useStudyDashboard.ts`); zero references to decks,
   lessons, ranking, or `RankedDecksResponse`.

2. **Slice 6.6 ranker has zero FE consumer.** `rg "/learn/ranked-decks|RankedDecks|ranked-decks"
   src/` returns no hits. The BE route is live (verified at
   `app/api/v1/routes/ranker.py` per slice 6.6 close-line) but no
   `services/api.ts` wrapper, no hook, no component invokes it.

3. **Persona-conditional rendering is the established `/home`
   pattern.** `src/pages/HomeDashboard.tsx` defines three render modes
   as **inline functions inside the page file** —
   `InterviewPrepperMode` (line 32), `CareerClimberMode` (line 65),
   `TeamLeadMode` (line 79) — branched by `user.persona` at lines
   213/227/235. Cross-cutting cross-mode concerns (the
   `StudyGapsPromptWidget` mount, `StateAwareWidgets` slot,
   `useStudyPromptEligibility` hook, suppression flags) are computed
   at the parent page level and passed as props or rendered above the
   mode children. The modes themselves are thin grids.

4. **Spec #61 widgets exist verbatim and need to survive.**
   `src/components/home/widgets/` carries `StudyGapsPromptWidget`,
   `TodaysReviewWidget`, `LastScanWidget`, `StreakWidget`,
   `WeeklyProgressWidget`, `CountdownWidget`, `InterviewTargetWidget`,
   `MissionActiveWidget`, `MissionOverdueWidget`,
   `ResumeStaleWidget`, `StreakAtRiskWidget`,
   `InactiveReturnerWidget`, `FirstSessionDoneWidget`,
   `TeamComingSoonWidget`, `InterviewPrepperChecklist`. Spec #61 §3
   suppression matrix and §4-§6 composition rules are HomeDashboard
   contracts; this slice does not amend them.

5. **`?source=last_scan` consumer is in `StudyDashboard.tsx:78-111`.**
   Component-state dismissal (no sessionStorage), idempotent
   `study_dashboard_source_hint_shown` event with `copy_variant: '6A'`,
   neutral hint copy ("Studying gaps from your last scan."). This
   surface must be preserved — the home `StudyGapsPromptWidget`
   primary CTA emits `/learn?source=last_scan` (spec #61 LD-11), so a
   consumer is part of the contract.

6. **`?category` consumer is in `StudyDashboard.tsx:65-77`** (filter
   pill surface at lines 295-313). Owned by spec #09 onboarding
   bridge — gap-card click navigates to `/learn?category=<id>` and
   filters the categories grid down to that single category. The
   filter is a legacy-cards surface (operates on `Category.id`, not
   on Phase-6 deck slugs).

7. **PaywallTrigger union for free-tier deck-locked CTAs.** Spec #61
   B-051 LD-S6/LD-S7 amendment substituted the originally-proposed
   `'study_engine_unlock'` trigger for the existing
   `'skill_gap_study'` (`src/components/PaywallModal.tsx:21-29`
   union) — semantically closer headline + subline copy, no union
   widening. This slice REUSES that trigger; no new
   `PaywallTrigger` value.

8. **Slice 6.6 `RankedDecksResponse.cold_start: true`** triggers a
   "scan to personalise" UX hint per §12 D-15 (spec #07 §4.4). The
   BE returns `cold_start: true` only — copy lives FE-side. The
   ranker's premium-decks-filtered-for-free behaviour (§12 D-10)
   means free users never see a "locked deck" surface inside the
   ranked list — premium decks simply don't appear. Free-tier
   upsell on deck-click belongs to non-Phase-6 surfaces (e.g., a
   browse-all view that includes premium slugs as a marketing
   nudge — out of scope here).

9. **`/learn/lesson/:id` is mounted to `pages/Lesson.tsx`** at
   `App.tsx:97` (slice 6.3). Deck-card clicks from the new ranker
   surface route into the existing lesson reader; no new deck-detail
   FE in this slice.

10. **Mission Mode** lives at `/learn/mission` → `pages/MissionMode.tsx`
    (`App.tsx:98`). Active-mission countdown surfacing on the
    interview-prepper Learn render mode reads from the existing
    mission service; no UX changes in this slice.

### 1.2 Why this matters

- Without this slice, slice 6.6 is dead code and the lens loop has no
  product surface. Free Interview Preppers (the conversion-driving
  persona per the PRD §1.3 framing) land on a categories grid that
  doesn't reflect their last scan.
- The spec #34 + spec #61 persona render-mode pattern has proven
  itself on `/home` — its absence on `/learn` is an inconsistency
  reviewers flagged as "two pages with two different IA philosophies
  for the same user". Adopting it on `/learn` closes the consistency
  gap.
- Career-Climbers (whose retention loop is "5 minutes a day daily
  review") get the wrong landing today — the legacy categories grid
  buries the daily-review CTA inside the "Your Goal" header card.
  A habit-mode framing surfaces the daily review as the spine.
- Team-Leads land on the same grid as everyone else with no signal
  that the assigned-decks-and-cohort-progress B2B surface is in the
  pipeline (PRD §1.5 P3). A v1 stub keeps the persona reachable
  without delivering the B2B surface that hasn't been specced.

Slice 6.7 ships the FE composition that activates slice 6.6 + closes
the consistency gap with HomeDashboard's persona-mode IA.

---

## 2. Goals

| # | Goal |
|---|------|
| G-1 | **Three-mode persona-conditional rendering on `/learn`.** `LearnInterviewMode` / `LearnHabitMode` / `LearnTeamMode` branched by `user.persona`, mirroring the on-disk HomeDashboard inline-function pattern (NOT separate component files — see §5 + §14 OQ-5). G-1 is the foundational architectural lock; the architecture itself is NOT a §14 OQ. |
| G-2 | **Ranked decks consumed in `LearnInterviewMode`** (and `LearnTeamMode` v1 stub which inherits IP behaviour). New `useRankedDecks` hook calls `GET /api/v1/learn/ranked-decks`; new `RankedDeckList` renders the response. |
| G-3 | **Spec #61 widgets preserved verbatim.** `StudyGapsPromptWidget` / `TodaysReviewWidget` / `LastScanWidget` and their composition rules (spec #61 §3-§6) survive within the appropriate Learn render mode without copy or behaviour changes. |
| G-4 | **Legacy category grid retires from the `LearnInterviewMode` landing.** The `?category=<id>` filter surface (spec #09) survives where it appears — `LearnHabitMode` keeps a "Browse categories" section at the bottom for the free-form-explore use case; `LearnInterviewMode` drops it entirely (Interview-Preppers don't browse categories). Deep links into `/learn/category/:id` keep working unchanged. |
| G-5 | **Cold-start UX.** `RankedDecksResponse.cold_start: true` triggers an inline "Take a scan to personalize" CTA inside `LearnInterviewMode`. Career-Climbers don't need the cold-start hint (their spine is TodaysReview). Team-Lead inherits IP behaviour in v1. |
| G-6 | **Zero new BE.** No new routes, no new schemas, no new analytics events on the BE side. No Alembic migrations. The slice consumes existing BE primitives. |

---

## 3. Non-goals (out-of-scope this slice)

- **No new BE routes.** Slice 6.6 already shipped `GET
  /api/v1/learn/ranked-decks`. No additional ranker variants, no
  per-lesson ranking endpoint, no admin tunable-weights surface.
- **No FE for legacy-card retirement.** The `Category` /
  `cards.tags` schema and the `gap_mapping_service.py` legacy bridge
  remain on disk through Phase 6. Slice 6.15 (cleanup) decides the
  retire-or-keep timing. This slice survives the legacy `/learn/card/:id`
  + `/learn/category/:id` mounts unchanged.
- **No team-lead B2B surface.** `LearnTeamMode` is a stub
  (inherits the IP deck-browse behaviour for v1). The
  assigned-decks + cohort-progress surface fires when team-lead
  activation gates flip post-Phase-6 per PRD §1.5 P3 — its own
  spec then.
- **No new `PaywallTrigger`.** The free-tier deck-locked CTA reuses
  the existing `'skill_gap_study'` trigger per spec #61 B-051
  LD-S6/LD-S7. No new headline/subline entries in
  `PaywallModal.HEADLINES` / `SUBLINES`.
- **No deck-detail FE.** `pages/Lesson.tsx` (slice 6.3) already
  serves `/learn/lesson/:id`. Deck-card clicks from the ranked list
  navigate into the existing lesson reader. No new deck-detail
  page.
- **No Mission Mode changes.** `/learn/mission` →
  `pages/MissionMode.tsx` stays unchanged. Active-mission
  countdown surfacing inside `LearnInterviewMode` is read-only —
  no mission CRUD, no spec changes to `mission-mode.md` skill or
  Mission Mode specs.
- **No analytics overhaul.** Three new events ship per §9; existing
  `study_dashboard_*` events stay live for the duration of the
  legacy-page survival per non-goal #2 above. Renaming or
  deprecating existing events is out of scope.
- **No embedding-based ranking surface change.** Slice 6.6b
  (hypothetical) would change the BE ranker shape, not the FE
  consumer; this slice is silent on it.
- **No homepage (HomeDashboard) changes.** Spec #34 / spec #61
  composition is unaltered; the home `StudyGapsPromptWidget`
  primary CTA still emits `/learn?source=last_scan` per spec #61
  LD-11.

---

## 4. Composition matrix

This is the deliverable shape. Three columns enumerate what each Learn
render mode mounts, which data primitives drive each section, and
which gates suppress it. The matrix is the §3-§6-of-spec-#61
analogue for Learn.

### 4.1 Per-mode section table

| Section | `LearnInterviewMode` (interview_prepper) | `LearnHabitMode` (career_climber) | `LearnTeamMode` (team_lead — v1 stub) |
|---------|------------------------------------------|-----------------------------------|---------------------------------------|
| Page header | "Your study path" + persona-aware subline | "Today's practice" + streak chip | "Team study" + "Browse-only — assigned decks coming" hint |
| `?source=last_scan` hint banner | **Renders** (spec #62 component-state-only consumer, copy variant `'6A'`) | Renders (same component) | Renders (same component) |
| State-slot widget (`StateAwareWidgets`) | Suppressed — Mission countdown surfaces inside the ranked-decks header instead (see "Mission countdown" row below) | Suppressed — habit-mode spine is TodaysReview | Suppressed — v1 stub |
| `StudyGapsPromptWidget` | Suppressed — prompt's purpose (push the user into the study engine) is moot when the user IS already on the study engine | Suppressed — same reason | Suppressed |
| Cold-start CTA card (§6) | **Renders** when `RankedDecksResponse.cold_start: true` | Suppressed — no ranker dependency | Renders (inherits IP) |
| Mission countdown (read-only) | **Renders** above the ranked deck list when an active Mission exists for `user.interview_target_date` | Suppressed | Suppressed |
| `RankedDeckList` (the new spine of IP) | **Renders** — the spine of the page; deck cards from the slice 6.6 response | Renders below TodaysReview as a "Curriculum suggestions" secondary section (collapsed-vs-expanded TBD §14 OQ-4) | Renders inheriting IP behaviour |
| `TodaysReviewWidget` | Renders inline below the ranked decks (secondary spot — IP's primary action is "study a ranked deck", not "do today's review") | **Renders** at the top — the spine of habit-mode | Renders (same component) |
| `LastScanWidget` | Suppressed when ranker has cold_start=false (the matched-gap chips on each ranked deck card already convey the scan-context); otherwise renders inside the cold-start CTA | Renders | Renders |
| Browse-categories grid (legacy `?category` filter consumer) | Suppressed | **Renders** at the bottom — habit-mode's free-form-explore surface keeps the legacy categories grid for the user who wants to wander | Suppressed in v1 (the "Browse all decks" affordance lives inside the ranked-deck section header) |
| Streak / weekly progress chrome | Suppressed (IP has interview-target framing instead) | Renders (`StreakWidget` + `WeeklyProgressWidget`) | Renders (`StreakWidget` + `WeeklyProgressWidget`) |
| `TeamComingSoonWidget` | Suppressed | Suppressed | **Renders** at the top — sets B2B-coming expectation alongside the inherited browse-only deck list |

### 4.2 Cross-cutting composition rules

These rules apply across all three modes and are computed at the
parent `Learn.tsx` level (mirroring HomeDashboard's
`useStudyPromptEligibility` + suppression-flag pattern in
`src/pages/HomeDashboard.tsx:96-159`):

- The `?source=last_scan` consumer is owned by `Learn.tsx` (the
  mount point), not by individual modes. Same component-state
  dismissal as `StudyDashboard.tsx:84-86`.
- The `?category` filter param consumer is also owned by
  `Learn.tsx` and routed only to `LearnHabitMode`; the other two
  modes ignore it. Deep links into `/learn?category=X` for an
  interview_prepper user render `LearnInterviewMode` with the
  param silently ignored (no error, no banner — the modes don't
  surface a "you're filtered" UX when they don't show categories).
- The slice 6.6 ranker call (`useRankedDecks`) fires only when
  `user.persona ∈ {interview_prepper, team_lead}` — career_climber
  doesn't need the call (TodaysReview is the spine). The hook
  returns idle / loading / success / cold-start / error states.

---

## 5. Component graph

### 5.1 New files

- `hirelens-frontend/src/pages/Learn.tsx` — **new**. Replaces
  `StudyDashboard.tsx` as the `/learn` mount per §7.1. Mirrors
  `HomeDashboard.tsx`'s structure: three persona render-modes as
  **inline functions inside the page file** (NOT extracted to
  separate component files — see §14 OQ-5 + JC #1 in the
  spec-author final report). Inline functions:
  `LearnInterviewMode`, `LearnHabitMode`, `LearnTeamMode`. Plus a
  small `useLearnPageEligibility` hook (parallel to
  `useStudyPromptEligibility` at `HomeDashboard.tsx:96`) that
  computes any cross-mode suppression flags Learn needs. Spec
  #61 widgets are imported verbatim from
  `src/components/home/widgets/`; no copies, no re-exports.
- `hirelens-frontend/src/components/learn/RankedDeckList.tsx` —
  **new**. Consumes `RankedDecksResponse.decks`. Renders the deck
  cards (visual treatment is §14 OQ-1 — compact list vs card grid).
  Empty state and cold-start branch are §14 OQ-2 / §6.
- `hirelens-frontend/src/hooks/useRankedDecks.ts` — **new**.
  React Query (or `useEffect`-backed — match the existing
  convention used by `useStudyDashboard.ts`) wrapper around the
  new `services/api.ts::fetchRankedDecks(...)` helper. Returns
  `{data, isLoading, error, isColdStart}`. Cold-start derived
  from `data.cold_start` for caller convenience.
- `hirelens-frontend/src/services/api.ts` — **modified**. Add
  `fetchRankedDecks(opts?: {lookback_days?: number; max_scans?:
  number})` that hits `GET /api/v1/learn/ranked-decks` with the
  optional query params per slice 6.6 §6.2 and returns the
  typed `RankedDecksResponse`. Add a `RankedDecksResponse` /
  `RankedDeck` / `ScoreBreakdown` type literal mirroring
  `app/schemas/ranker.py` field-for-field per the curriculum
  skill §9 convention.

### 5.2 Modified files

- `hirelens-frontend/src/App.tsx` — **modified**. The `/learn`
  route at line 93 swaps `<StudyDashboard />` for `<Learn />`.
  Remaining `/learn/*` routes (`/learn/daily`,
  `/learn/category/:id`, `/learn/card/:id`, `/learn/lesson/:id`,
  `/learn/mission`) stay unchanged. The transitional `/study →
  /learn` redirects (lines 130-134) stay unchanged.
- `hirelens-frontend/src/pages/StudyDashboard.tsx` — **disposition
  decided in §14 OQ-3** (delete vs keep-as-shell-export). Author
  hint (a) DELETE — `Learn.tsx` absorbs all its content via the
  habit-mode section. The page has no other importers
  (App.tsx is the only mount).

### 5.3 Reused widgets — explicit import map

Spec #61 widgets render INSIDE the persona modes (not at the
top-level `Learn.tsx`). This mirrors the HomeDashboard pattern at
`src/pages/HomeDashboard.tsx:213-235`. No prop-drilling refactor —
widgets self-fetch via their existing context dependencies
(`UsageContext`, `AuthContext`, `GamificationContext`).

| Widget | Mode(s) using it | Import path |
|--------|------------------|-------------|
| `TodaysReviewWidget` | All three modes (spine of HabitMode; inline secondary in IP/Team) | `@/components/home/widgets/TodaysReviewWidget` |
| `LastScanWidget` | HabitMode + TeamMode + cold-start branch of IP | `@/components/home/widgets/LastScanWidget` |
| `StreakWidget` | HabitMode + TeamMode | `@/components/home/widgets/StreakWidget` |
| `WeeklyProgressWidget` | HabitMode + TeamMode | `@/components/home/widgets/WeeklyProgressWidget` |
| `TeamComingSoonWidget` | TeamMode | `@/components/home/widgets/TeamComingSoonWidget` |

`StudyGapsPromptWidget` is intentionally NOT reused on the Learn
page — its purpose (push user from `/home` into `/learn`) is moot
when the user is already on `/learn`. Per §4.1 it is suppressed in
all three Learn modes.

### 5.4 Existing widgets explicitly NOT touched

The HomeDashboard composition (`src/pages/HomeDashboard.tsx`
lines 32-88) is unchanged by this slice. `InterviewPrepperMode`
on `/home` keeps its `CountdownWidget` + `InterviewTargetWidget`
+ `LastScanWidget` composition (and the spec #61 suppression
flags). The new `LearnInterviewMode` on `/learn` is a separate
inline function in a separate page file — no shared component
file, no shared name conflict.

---

## 6. Cold-start UX

When `useRankedDecks().data.cold_start === true`, the Learn page
behaves as follows per render mode:

- **`LearnInterviewMode`:** the `RankedDeckList` swaps its
  matched-gap-chips header for an inline CTA card:

  ```
  ┌──────────────────────────────────────────────────────────────┐
  │  [icon]  Take a scan to personalize your learning path.      │
  │          We'll rank the lessons that close your skill gaps.  │
  │          [Scan resume →]   (routes to /prep/analyze)         │
  └──────────────────────────────────────────────────────────────┘
  ```

  Below the cold-start card, the ranked list still renders — but
  ordered by `decks.display_order ASC` only (per slice 6.6 §4.4).
  No matched-gap chips. The `LastScanWidget` ALSO renders below
  the cold-start card so the user has secondary context for "what
  scan you did last" (which in cold-start is "none").

- **`LearnHabitMode`:** no cold-start CTA. Habit-mode spine is
  TodaysReview, which has its own empty state ("No cards due
  today" via the existing widget). Ranked-deck section, if it
  renders at all (§4.1 row), shows a single inline hint: "Scan a
  resume to personalize curriculum suggestions." No card.

- **`LearnTeamMode`:** inherits `LearnInterviewMode` behaviour
  for v1.

The cold-start CTA copy is locked at §14 OQ-7 (one of three copy
variants); the routing target `/prep/analyze` is locked here. The
`fetchRankedDecks` call ALWAYS fires for IP/Team (cold-start is a
response-shape branch, not a fetch-skip branch).

---

## 7. Routing & migration

### 7.1 `/learn` mount swap

| Path | Before this slice | After this slice |
|------|-------------------|------------------|
| `/learn` | `<StudyDashboard />` (`App.tsx:93`) | `<Learn />` |
| `/learn/daily` | `<DailyReview />` | `<DailyReview />` (unchanged) |
| `/learn/category/:id` | `<CategoryDetail />` | `<CategoryDetail />` (unchanged — legacy survival per §3 non-goal #2) |
| `/learn/card/:id` | `<CardViewer />` | `<CardViewer />` (unchanged) |
| `/learn/lesson/:id` | `<Lesson />` (slice 6.3) | `<Lesson />` (unchanged — deck-card clicks land here) |
| `/learn/mission` | `<MissionMode />` | `<MissionMode />` (unchanged) |

The transitional `<Navigate replace>` redirects from `/study/*`
(`App.tsx:130-134`) stay unchanged — they redirect into `/learn/*`
and pick up the new mount automatically.

### 7.2 Query-param contract

| Param | Owned by | Routed to | Behaviour |
|-------|----------|-----------|-----------|
| `?source=last_scan` | `Learn.tsx` parent (mirrors `StudyDashboard.tsx:78-111`) | All three modes (banner is mode-agnostic) | Spec #62 verbatim — component-state dismissal, idempotent `study_dashboard_source_hint_shown` event with `copy_variant: '6A'` (existing event NAME preserved for dashboard continuity per spec #62 §7.4 — see §9 + §14 OQ-8) |
| `?category` | `Learn.tsx` parent | Routed only to `LearnHabitMode` for the legacy categories grid | Spec #09 verbatim. Other two modes silently ignore. |

### 7.3 Legacy `StudyDashboard.tsx` disposition

§14 OQ-3, author hint (a) DELETE. Rationale: `Learn.tsx` absorbs
the legacy categories-grid behaviour into `LearnHabitMode`'s
"Browse categories" section; both `?source=last_scan` and
`?category` consumers are re-implemented at the `Learn.tsx` parent
level. No other importer of `StudyDashboard.tsx` exists (`rg "from
'@/pages/StudyDashboard'\|from '\\./StudyDashboard'"` returns only
`App.tsx`). Test file `tests/pages/StudyDashboard.test.tsx` (if it
exists today) is removed alongside; new test files cover the new
surface.

---

## 8. FE composition note

Spec #61 widgets (`StudyGapsPromptWidget`, `TodaysReviewWidget`,
`LastScanWidget`, etc.) render INSIDE the Learn persona modes per
the §4.1 matrix — NOT at the top-level `Learn.tsx`. This mirrors
the on-disk pattern in `src/pages/HomeDashboard.tsx`:

- HomeDashboard mounts `StateAwareWidgets` and
  `StudyGapsPromptWidget` at the parent level (lines 206-212);
  per-persona widgets render inside the mode children
  (lines 213-235).
- Learn does NOT mount `StateAwareWidgets` (per §4.1 row — the
  state-slot is suppressed) and does NOT mount
  `StudyGapsPromptWidget` (per §4.1 row — the prompt is moot
  on the destination page).
- Per-mode widgets render inside the inline mode functions —
  same composition shape as HomeDashboard's mode functions.

No prop-drilling refactor is needed. Widgets self-fetch via
their existing context dependencies. This is a deliberate match
to spec #34's ACR-5 ("each persona branches to a distinguishable
render mode") + spec #61 §3.4's "implementation hint
(non-binding)" allowing context- or prop-based composition flags.

The on-disk HomeDashboard precedent is **inline mode functions in
the page file**, not separate `components/home/{Mode}.tsx` files.
This slice mirrors that. See §14 OQ-5 if a future refactor wants
to extract them — non-blocking for v1.

---

## 9. Analytics

Three new events ship with this slice. All follow the existing
`home_*` / `study_dashboard_*` `useRef`-idempotent convention
catalogued in `.agent/skills/analytics.md`.

| Event | Source | Properties | Fires |
|-------|--------|------------|-------|
| `learn_page_viewed` | `src/pages/Learn.tsx` | `{persona: 'interview_prepper'\|'career_climber'\|'team_lead', plan: 'free'\|'pro'\|'enterprise', mode: 'interview'\|'habit'\|'team', has_ranked_decks: boolean, cold_start: boolean}` — `has_ranked_decks` is `true` iff the ranker call returned ≥1 deck (false when `cold_start` AND `decks.length === 0`); `cold_start` mirrors `RankedDecksResponse.cold_start` (false for HabitMode which doesn't call the ranker) | Once per Learn mount via `useRef` idempotency (matches `home_dashboard_viewed` / `study_dashboard_viewed` convention). Fires AFTER the ranker call resolves (or immediately for HabitMode where the call doesn't fire). |
| `learn_deck_clicked` | `src/components/learn/RankedDeckList.tsx` | `{deck_slug: string, deck_position: int (1-indexed `rank` from RankedDeck), persona, plan, score: float, matched_gap_count: int, is_cold_start: boolean}` | On every deck-card click before the `/learn/lesson/:lesson_id` navigation. (Deck-card click routes to the deck's first lesson; lesson-id selection logic is impl-time — author hint: first published, non-archived lesson by `display_order ASC`.) |
| `learn_mode_rendered` | `src/pages/Learn.tsx` (inside each mode's render branch) | `{mode: 'interview'\|'habit'\|'team', persona}` | §14 OQ-6 — once-per-mount default vs once-per-session. Author hint (a) once-per-mount via `useRef` (matches the rest of the family). |

### 9.1 Event-volume sanity check

`learn_page_viewed` fires once per page mount; `learn_deck_clicked`
fires per deck card click; `learn_mode_rendered` fires once per
mount. Combined per-session impact at typical visit cadence (1
visit/day × 1-2 deck clicks): ~3-4 events per active user per
day from this surface. Well within PostHog free-tier event budget;
no risk-of-overflow note required.

### 9.2 Existing events touched

| Event | Source | Change |
|-------|--------|--------|
| `study_dashboard_viewed` | `src/pages/StudyDashboard.tsx` | Stops firing when this slice deletes `StudyDashboard.tsx` per §7.3. Existing PostHog data is preserved (deprecation pattern per `analytics.md` §Conventions); no rename. New `learn_page_viewed` carries the equivalent funnel. |
| `study_dashboard_source_hint_shown` | `src/pages/Learn.tsx` (was `src/pages/StudyDashboard.tsx`) | Source file moves; event name + payload + `copy_variant: '6A'` lock unchanged per spec #62 §7.4. Existing PostHog dashboards continue to work without migration. |
| `category_tile_clicked` | `src/pages/Learn.tsx` (`LearnHabitMode` only — fired from the legacy categories grid) | Source file moves; event unchanged. |
| `locked_tile_clicked` | `src/pages/Learn.tsx` (`LearnHabitMode` only) | Source file moves; event unchanged. |

The impl slice updates `.agent/skills/analytics.md` with the three
new event rows + the four moved-source rows in the SAME commit per
the `home_*` precedent.

### 9.3 Catalog discipline

No PostHog event renames; deprecate, don't rename
(`analytics.md` §Conventions). The only deprecation here is
`study_dashboard_viewed` — surfaced in §9.2 above for visibility,
catalog row gets a `(DEPRECATED slice 6.7)` tag at impl time.

---

## 10. Test plan

Four new FE Vitest test files. Zero BE tests (zero BE files
touched). Estimated **+25 to +40 FE cases** total.

### 10.1 `tests/pages/Learn.test.tsx` — page-level tests

Estimated **~10-12 tests**:

| # | Test | Purpose |
|---|------|---------|
| 1 | `renders LearnInterviewMode for interview_prepper persona` | Mode-routing AC. |
| 2 | `renders LearnHabitMode for career_climber persona` | Mode-routing AC. |
| 3 | `renders LearnTeamMode for team_lead persona` | Mode-routing AC. |
| 4 | `null persona redirects to /onboarding/persona via PersonaGate` | PersonaGate compatibility regression (per spec #34 AC-2). |
| 5 | `interview_prepper + cold_start: true renders cold-start CTA card` | Cold-start branch AC (§6). |
| 6 | `interview_prepper + cold_start: false renders ranked deck list with matched gaps` | Happy-path AC. |
| 7 | `?source=last_scan renders the spec #62 banner` | Param-consumer regression (banner moved file but behaviour unchanged). |
| 8 | `?source=last_scan dismiss button hides banner without URL mutation` | Spec #62 §3.3 regression. |
| 9 | `?category=<id> filters categories grid in HabitMode only` | Spec #09 regression in the new mount. |
| 10 | `?category=<id> ignored silently in InterviewMode (no error, no banner)` | Spec #09 cross-mode behaviour per §7.2. |
| 11 | `learn_page_viewed fires once via useRef even on Strict-Mode double-render` | Event idempotency (matches `home_dashboard_viewed` precedent). |
| 12 | `learn_page_viewed payload includes persona + plan + mode + has_ranked_decks + cold_start` | Event payload regression. |

### 10.2 `tests/components/learn/LearnInterviewMode.test.tsx` — IP composition

Estimated **~6-8 tests**:

| # | Test | Purpose |
|---|------|---------|
| 1 | `mounts RankedDeckList when ranker returns >0 decks` | Spine render. |
| 2 | `mounts cold-start CTA card when cold_start=true` | Cold-start composition. |
| 3 | `does NOT mount StudyGapsPromptWidget` | §4.1 suppression. |
| 4 | `does NOT mount StateAwareWidgets` | §4.1 suppression. |
| 5 | `does NOT mount the legacy ?category browse grid` | §4.1 suppression. |
| 6 | `mounts TodaysReviewWidget below ranked decks (secondary spot)` | §4.1 row ordering. |
| 7 | `mission countdown surfaces above RankedDeckList when active mission matches user.interview_target_date` | §4.1 + §3 mission-read-only. |
| 8 | `LastScanWidget suppressed when cold_start=false; renders inside cold-start card otherwise` | §4.1 + §6. |

### 10.3 `tests/components/learn/LearnHabitMode.test.tsx` — habit composition

Estimated **~5-7 tests**:

| # | Test | Purpose |
|---|------|---------|
| 1 | `mounts TodaysReviewWidget at top (spine)` | §4.1. |
| 2 | `mounts StreakWidget + WeeklyProgressWidget` | §4.1. |
| 3 | `mounts legacy categories browse grid at bottom` | §4.1 — habit-mode keeps the explore surface. |
| 4 | `?category=<id> filter pill renders inside habit-mode browse grid` | Spec #09 regression in habit-mode scope. |
| 5 | `does NOT call useRankedDecks (career_climber spine has no ranker dependency)` | §4.2 cross-cutting rule. |
| 6 | `mounts ranked-decks "Curriculum suggestions" section if §14 OQ-4 author hint (b) expanded-by-default` | OQ-4 placeholder; impl-time decision. |
| 7 | `does NOT mount StudyGapsPromptWidget` | §4.1 suppression. |

### 10.4 `tests/components/learn/RankedDeckList.test.tsx` — deck list

Estimated **~6-8 tests**:

| # | Test | Purpose |
|---|------|---------|
| 1 | `renders one card per RankedDeck` | Happy path. |
| 2 | `cold_start=true + decks=[] renders cold-start CTA only (no list)` | §6. |
| 3 | `cold_start=true + decks=[…display_order order] renders both` | §6 second cold-start branch (BE returns display-order-ordered list when no scan). |
| 4 | `matched_gap chips render per RankedDeck.matched_gaps` | Diagnostic display. |
| 5 | `does NOT render any deck with deck.tier === 'premium' for free user` | Defensive — slice 6.6 D-10 already filters at BE; FE re-asserts (no leak). |
| 6 | `deck-card click fires learn_deck_clicked with rank, deck_slug, persona, plan` | Event regression. |
| 7 | `deck-card click navigates to /learn/lesson/<first_lesson_id>` | Navigation behaviour. |
| 8 | `empty list (decks=[] AND cold_start=false) renders empty-state copy from §14 OQ-2` | OQ-2 placeholder; impl-time copy. |

### 10.5 Regression set must stay green

- All existing FE tests (375 baseline). Particular attention to:
  - `tests/HomeDashboard.test.tsx` — HomeDashboard composition is
    unchanged, but the new shared widgets (`TodaysReviewWidget`,
    etc.) render in two pages now.
  - `tests/App.redirects.test.tsx` — `/study → /learn` redirects
    must keep landing on the new `<Learn />` mount.
  - `tests/components/home/widgets/StudyGapsPromptWidget.test.tsx` —
    the home prompt's primary CTA still emits
    `/learn?source=last_scan`; the consumer side moves but the
    contract is preserved.

### 10.6 Integration tests

None. The slice 6.6 BE is already covered by
`tests/test_deck_ranker_service.py` + `tests/test_ranker_routes.py`
(per slice 6.6 §10). FE consumer tests use mocked
`fetchRankedDecks` — no live LLM call, no integration marker.

---

## 11. Acceptance criteria

| AC | Surface | Trigger | Expected behavior | Test harness |
|----|---------|---------|-------------------|--------------|
| **AC-1** | `/learn` mount | persona=interview_prepper | Renders `LearnInterviewMode` (assertable via `data-testid="learn-mode-interview"`) | Vitest render |
| **AC-2** | `/learn` mount | persona=career_climber | Renders `LearnHabitMode` (`data-testid="learn-mode-habit"`) | Vitest render |
| **AC-3** | `/learn` mount | persona=team_lead | Renders `LearnTeamMode` (`data-testid="learn-mode-team"`) | Vitest render |
| **AC-4** | `/learn` mount | persona=null | Redirects to `/onboarding/persona` (PersonaGate per spec #34) | Vitest `MemoryRouter` |
| **AC-5** | `useRankedDecks` hook | persona ∈ {interview_prepper, team_lead}, mount | `GET /api/v1/learn/ranked-decks` is called once | Vitest `vi.spyOn(fetchRankedDecks)` |
| **AC-6** | `useRankedDecks` hook | persona = career_climber, mount | `fetchRankedDecks` is NOT called | Same |
| **AC-7** | `LearnInterviewMode` | `RankedDecksResponse.cold_start === true` | Cold-start CTA card renders inline above the ranked list; CTA href = `/prep/analyze` | Vitest |
| **AC-8** | `RankedDeckList` | `RankedDecksResponse.cold_start === false`, `decks.length > 0` | One card per deck rendered, ordered by `decks` array (server-sent), each card showing `matched_gaps` chips | Vitest |
| **AC-9** | `LearnHabitMode` | mount | `TodaysReviewWidget` renders before `StreakWidget` and before the legacy categories grid (DOM order assertable via `getByTestId(...).compareDocumentPosition(...)`) | Vitest |
| **AC-10** | `?source=last_scan` consumer | URL has `?source=last_scan` | `study-dashboard-source-hint` banner renders inside the Learn page (any mode) with copy variant `6A` | Vitest |
| **AC-11** | `?category` consumer | URL has `?category=<id>` AND persona = career_climber | Categories grid in HabitMode filters to that single category; filter pill renders | Vitest |
| **AC-12** | `?category` consumer | URL has `?category=<id>` AND persona = interview_prepper | No banner, no error, no filter pill — IP page renders normally; param silently ignored | Vitest |
| **AC-13** | Free-tier deck-card click | `RankedDeck` with locked behaviour (defensive — slice 6.6 D-10 means this should not happen but impl test asserts the FE doesn't leak) | If a premium-tier deck somehow surfaces in the response (BE bug regression), clicking it opens `<PaywallModal trigger="skill_gap_study" />` per spec #61 LD-S6/LD-S7 | Vitest |
| **AC-14** | `tsc --noEmit` | Post-impl baseline | Type-check passes; new types in `services/api.ts` mirror BE `app/schemas/ranker.py` field-for-field per curriculum.md §9 | `npm run typecheck` |
| **AC-15** | All existing FE tests | Post-impl baseline | 375 baseline passing tests still pass; ~+25 to +40 net new (final count locked at impl) | `npx vitest run` |

---

## 12. Decisions

> Empty at spec-author. Locked via §12 amendment slice mirroring
> slice 6.0 / 6.4.5 / 6.5 / 6.6 precedent (`e8eecdd` / `df58eaf` /
> `acba7ed` / `fb92396`). Each D-N below resolves the like-numbered
> §14 OQ; §14 retains the question + RESOLVED pointer back here for
> traceability.
>
> *(filled at amendment SHA `<amendment-sha>`)*

---

## 13. Out of scope (deferred to other slices)

- **Legacy categories-grid full retirement.** Slice 6.15
  (cleanup) decides whether to drop `Category` /
  `cards.tags` / `gap_mapping_service.py` / `/learn/category/:id`
  / `/learn/card/:id` once the Phase-6 ranked-deck surface is
  proven out. This slice retains the legacy mounts.
- **Mission Mode UX changes.** `/learn/mission` →
  `pages/MissionMode.tsx` is unchanged. Mission countdown surfaces
  inside `LearnInterviewMode` are read-only.
- **Team-Lead B2B activation.** Assigned-decks + cohort-progress
  surface for team_lead persona ships in its own spec post-Phase-6
  per PRD §1.5 P3. v1 stub only.
- **New PaywallTriggers.** `'skill_gap_study'` reused per spec #61
  LD-S6/LD-S7. No widening.
- **Embedding-based ranking surface change.** Slice 6.6b
  (hypothetical) is BE-only — would change the BE ranker
  ordering without touching the FE consumer.
- **Deck-detail page.** `pages/Lesson.tsx` (slice 6.3) covers
  `/learn/lesson/:id` already.
- **Admin tunable weights for the ranker.** Constants live in
  `app/services/deck_ranker_service.py`; admin UI is out of scope
  per slice 6.6 §3.
- **Ranked-deck pagination.** §14 OQ-6 documents the question;
  author hint (a) renders all (the 12-deck universe is small
  per slice 6.6 §1.1).
- **Cross-deck lesson ranking.** Slice 6.6 D-5 deferred this to
  the hypothetical 6.6b; no FE consumer here.
- **A/B test infrastructure for cold-start copy.** Spec locks
  one variant via §14 OQ-7 selection; no rollout-tooling
  scope.

---

## 14. Open questions

> Surface-level OQs only. Architecture (G-1 three-mode persona
> rendering; HomeDashboard-inline-function pattern reuse; spec #61
> widgets preserved verbatim; PaywallTrigger reuse) is locked in
> §1-§5 and is NOT a §14 OQ. Each OQ carries an author hint to
> minimize §12 amendment-slice churn.

**OQ-1 — Deck-card visual treatment (compact list vs card grid).**
The slice 6.6 response carries up to 12 decks per response. A
compact list (one row per deck, ~64px tall, dense matched-gap
chips inline) keeps more decks above the fold; a card grid
(2-col on desktop, ~160px tall, larger matched-gap chips +
score breakdown) gives more visual weight per deck.

(a) Compact list — denser, scan-friendly.
(b) Card grid — visual-weight parity with HomeDashboard widgets.

Author hint: **(b) card grid** — matches the existing visual
language of HomeDashboard widgets and the
spec #61 `StudyGapsPromptWidget` body framing. The 12-deck
universe is small enough that scrolling isn't punishing.

**OQ-2 — `RankedDeckList` empty-state copy.** When ranker
returns `decks=[]` AND `cold_start=false` (a corner case that
should not happen given slice 6.6 §3 non-goal #6 "decks scoring
0 still appear at the bottom" — but defensive copy is required
in case of BE regression).

(a) "No decks match your scan yet — try re-scanning a different JD."
(b) "No curriculum decks available right now — check back soon."

Author hint: **(a)** — actionable, points at the user's lever
(re-scan), avoids the "we have a bug" reading of (b).

**OQ-3 — Legacy `StudyDashboard.tsx` file disposition.**

(a) DELETE — `Learn.tsx` absorbs all behaviour;
    `StudyDashboard.tsx` has no other importer.
(b) Keep as a shell that re-exports `Learn` for backwards
    compatibility against any unimported test file or future
    spec that references it by name.

Author hint: **(a) delete** — no other importer (`rg` confirmed
in §7.3); shell-export is dead-code prevention theatre.

**OQ-4 — `LearnHabitMode` ranked-deck section default state.**
The "Curriculum suggestions" section in HabitMode (per §4.1) is
secondary to TodaysReview. Render expanded by default or
collapsed-with-toggle?

(a) Collapsed-by-default with "Show curriculum suggestions" toggle.
(b) Expanded-by-default.

Author hint: **(b) expanded** — collapsed-by-default would
under-surface the slice 6.6 ranker for the career_climber
persona (which is half the user base per the PRD §1.3 split).
The toggle adds a click that gates value with no clear win.

**OQ-5 — Mode files: inline functions vs separate component
files.** The on-disk HomeDashboard pattern is inline functions
(per §1.1 finding #3 + §5.1). Should `Learn.tsx` mirror that
exactly, or extract `LearnInterviewMode` / `LearnHabitMode` /
`LearnTeamMode` to `src/components/learn/{LearnInterviewMode,…}.tsx`?

(a) Inline functions in `Learn.tsx` (mirror HomeDashboard
    on-disk precedent).
(b) Extract to separate files in `src/components/learn/`.

Author hint: **(a) inline** — matches established on-disk
pattern. If a future refactor extracts both pages' modes
together (consistency win), it's a separate cleanup slice
applied to both pages — not a per-slice judgment call.

**OQ-6 — `learn_mode_rendered` event firing cadence.**

(a) Once per mount via `useRef` (matches family convention).
(b) Once per session via sessionStorage flag.

Author hint: **(a) once-per-mount** — every other event in the
`home_*` / `study_dashboard_*` family uses `useRef`-mount
idempotency; sessionStorage adds a new pattern for marginal
deduplication value.

**OQ-7 — Cold-start CTA copy variant.** Three proposals (each
zero PII, design-token only):

(a) "Take a scan to personalize your learning path. We'll rank
    the lessons that close your skill gaps."
(b) "Scan a resume to see which decks close your gaps fastest."
(c) "Personalize this list — scan a JD and we'll rank the most
    impactful decks first."

Author hint: **(a)** — verbose but most specific; ties
"learning path" to the page's spine framing without requiring
the user to know what a JD is. (b) is shortest but loses the
learning-path framing. (c) leans on "JD" which non-technical
readers may not recognize.

**OQ-8 — `study_dashboard_source_hint_shown` event rename or
preserve.** When `StudyDashboard.tsx` deletes and the consumer
moves to `Learn.tsx`, the event source file changes but the
contract (idempotent `useRef`, payload `{source, persona,
copy_variant}`) is unchanged.

(a) Preserve event name; just update the source-file column in
    `analytics.md`.
(b) Deprecate `study_dashboard_source_hint_shown` and add
    `learn_source_hint_shown` with identical payload.

Author hint: **(a) preserve** — spec #62 §7.4 explicitly notes
this event is dashboard-coupled; renaming breaks PostHog
funnels for zero gain (per `analytics.md` §Conventions
"deprecate, don't rename" rule, applied here as "don't
rename when contract is identical").

---

## 15. Implementation slice forward-link

Implementation row: **B-077** 🔴 (filed by this slice).

Forward dependencies before impl can start:

1. **§12 amendment slice** locking D-1..D-N from §14 OQ-1..OQ-8
   (mirrors slice 6.0 / 6.4.5 / 6.5 / 6.6 pattern at
   `e8eecdd` / `df58eaf` / `acba7ed` / `fb92396`). Spec body
   `<amendment-sha>` placeholder fills at amendment commit.
2. No BE prerequisite — slice 6.6 (B-074, `5011518`) shipped the
   ranker. Slice 6.5 (B-072, `930a6a2`) shipped the read-time
   invariants the ranker re-orders.

Impl slice expected scope:

- New file `src/pages/Learn.tsx` (~250-350 lines, mirrors
  `HomeDashboard.tsx`'s structure including inline mode
  functions).
- New file `src/components/learn/RankedDeckList.tsx` (~80-120
  lines).
- New file `src/hooks/useRankedDecks.ts` (~30-50 lines).
- `src/services/api.ts` modifications: `fetchRankedDecks` helper +
  `RankedDecksResponse` / `RankedDeck` / `ScoreBreakdown` type
  literals (~30 lines added).
- `src/App.tsx` modification: `/learn` mount swap
  `StudyDashboard` → `Learn` (1 line change + 1 import update).
- `src/pages/StudyDashboard.tsx` deletion (per §14 OQ-3 (a)).
- 4 new test files per §10.1-§10.4.
- `.agent/skills/analytics.md` update: 3 new event rows + 4
  moved-source rows + `study_dashboard_viewed` deprecation tag.
- BACKLOG B-077 closure with impl SHA.
- SESSION-STATE Recently Completed entry.
- CODE-REALITY targeted regen at impl close (new page +
  components + hook + types delta + `/learn` mount swap).

Impl test envelope: BE 636 unchanged; FE **375 → 400..415**
(`+25..+40`).
