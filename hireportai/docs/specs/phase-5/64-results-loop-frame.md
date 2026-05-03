# P5-S64 — Static Loop Frame on `/prep/results`

## Status: 🔴 Drafted

| Field | Value |
|-------|-------|
| **Slice** | P5-S64 (FE-only; spec-author this slice) |
| **Phase** | 5 |
| **Mode** | Mode 4 spec-author → followed by impl slice (B-120 forward-filed) |
| **Filed at** | `<this-slice>` (filing/spec-author commit) |
| **BACKLOG row (spec-author)** | this slice — closes E-049 spec-author half on commit; status flip happens at impl per R15(c) |
| **BACKLOG row (impl, forward-filed)** | **B-119** 🔴 (filed at status 🔴 by this slice for the future implementation slice per R15(c)). R17 watermark verified at filing: B-118 highest in-use at slice start; B-119 claimed (next-free per disk). Prompt body originally cited B-120 — corrected per starter-line R19 STOP + H4 watermark-grep precedence. |
| **Closes** | **E-049** part (b) on impl-merge. Part (a) (Pro upsell button on missing-skills) was already shipped as **E-011 ✅** (`fd4ca3d`, spec #22). |
| **Depends on** | spec #21 (Results-page education layer + 11-child grid; shipped) ▪ spec #22 (`MissingSkillsPanel` three-state CTA + `id="missing-skills"` anchor; shipped at `fd4ca3d`) ▪ spec #57 (`homeState.context.next_interview` envelope; shipped at `b13f410`) ▪ existing `useHomeState()` hook ▪ existing `AnalysisResponse` shape (`overall_score`, `missing_skills`). |
| **Blocks** | **E-051** (live loop-progress strip in AppShell) — consumes the visual contract this spec establishes (step copy, step order, component primitive). |
| **Cross-refs** | spec #21 / spec #22 (Results page predecessors) ▪ E-011 ✅ (Pro upsell on missing-skills, `fd4ca3d`) ▪ E-051 (forward-link, live wired version) ▪ E-050 (orthogonal — status-sentence hero on `/home`) ▪ `.agent/skills/design-system.md` (R12 token-only styling) ▪ `.agent/skills/analytics.md` (event catalog discipline). |

---

## 1. Problem

The Missing Skills upsell on `/prep/results` (E-011, spec #22) is
shipped: free users see "Study these cards — free preview", Pro users
see "Study these cards", and the CTA routes into `/learn?category=<id>`.
What the surface lacks is **visual context for why studying matters**.
A first-time scanner sees a list of gaps + a "study" CTA with no frame
that this scan is *step 1 of a closed loop* (scan → study → re-scan →
interview). Without that frame, the CTA is a flat invitation to study
flashcards; with it, the CTA is the obvious next step in a sequence the
user just started by scanning their resume.

The closed loop (`Scanned → Studying → Re-scan → Interview`) is the
PRD's killer flywheel (playbook 1.8) and the differentiator that
justifies $49/mo over Jobscan's $29 (BACKLOG row E-049). E-051 will
make this loop *live* (real progress, click-through, AppShell
persistence). This spec ships the *static* frame first — the visual
contract that E-051 inherits — so the upsell on Results gains its
reason-to-exist in one fast slice with no BE work.

### 1.1 What's already shipped (out of scope this spec)

- **Pro upsell button on missing-skills** — E-011 ✅ (`fd4ca3d`, spec
  #22). Three-state CTA (anonymous / free / pro) routes into
  `/learn?category=<id>`. Fires `missing_skills_cta_clicked`.
  **This spec does not touch `MissingSkillsPanel.tsx` or its CTA.**
- **`?source=last_scan` hint banner on `/learn`** — spec #62 ✅
  (downstream of the Pro CTA's navigation target).

### 1.2 What this spec ships

A single new FE component, `<LoopFrame>`, mounted on `/prep/results`
above the missing-skills section, rendering 4 labeled steps. No live
state, no animation, no click-through, no BE work.

---

## 2. Goals

- **G-1** — Render a static four-step visualization on the Results
  page that reads:
  `✓ Scanned (score) → ● Studying (N gaps) → ○ Re-scan → ○ Interview (Nd or "Set a date")`
- **G-2** — Establish the visual contract (step copy verbatim, step
  order, component primitive name) that E-051 will consume without
  drift. The four step labels are part of the contract.
- **G-3** — Zero backend work. Zero new endpoints. Zero new schemas.
  Zero new DB columns.
- **G-4** — Single new component file. No edits to `MissingSkillsPanel`,
  `PaywallModal`, or any other shared primitive.

---

## 3. Non-goals

- Live state on the loop frame (E-051 owns this).
- Animation between steps (E-051 owns).
- Click-through on any step (E-051 owns the click-through on step 3
  "Re-scan" → tracker rescan).
- AppShell-level mount that persists across pages (E-051 owns).
- Persona variants of the frame (the frame is persona-agnostic on
  Results — every signed-in scanner sees it).
- Any change to the missing-skills CTA, its copy, its analytics event,
  or its routing (E-011 territory).
- Any change to `tracker_application_scores` reads or any history-aware
  step progression (E-051 / E-053 territory).
- New `PaywallTrigger` values. The existing `skill_gap_study` trigger
  (already in the union per `PaywallModal.tsx:21-29`) covers any
  future upsell hook from this surface.
- Mobile-specific data variants (the frame's data sources don't change
  by viewport — only its layout does, see §8.2).

---

## 4. Architecture

### 4.1 Component shape

A new presentational component:

```
src/components/dashboard/LoopFrame.tsx
```

Co-located with `MissingSkillsPanel`, `PanelSection`, and the other
Results-page primitives (matches §14 OQ-4 hint and the existing
`components/dashboard/` organization — see `ls
hirelens-frontend/src/components/dashboard/`).

Pure presentational; no data fetching inside the component. The
consumer (Results.tsx) reads `homeState` + `result` and passes the
required values down as props.

### 4.2 Mount point

In `src/pages/Results.tsx`, between the Job Fit section
(`id="job-fit"`, lg-col-2 row-1) and the Missing Skills section
(`id="missing-skills"`, lg-col-span-2 row-5 / xl-col-3 row-1).

Mounted as a *new direct grid child* of the `motion.div` grid
container at `Results.tsx:281-286` (the 11-child flattened grid from
spec #21 / E-009 / P5-S20). The frame spans the full grid width on
all breakpoints:

```
className="lg:col-span-2 lg:col-start-1 xl:col-span-3 xl:col-start-1"
```

This makes it the **12th direct grid child** (was 11; spec #21's
flattened-grid count is amended by +1, see §13.3). Section ID is
`loop-frame` — explicitly NOT in the spec #21 9-value
`results_tooltip_opened` enum (this surface has no tooltip). The new
ID does not change the tooltip enum and is asserted as additive in
test plan §10.

### 4.3 Component contract

```tsx
// src/components/dashboard/LoopFrame.tsx — FINAL EXPORT SHAPE

export type LoopFrameSurface = 'results' // E-051 will widen to | 'appshell'

export type LoopFrameStep = 'scanned' | 'studying' | 'rescan' | 'interview'

export interface LoopFrameProps {
  /** Which surface is mounting this frame. Drives the analytics
   *  event property; no visual change in this slice. E-051 widens
   *  the union without breaking this caller. */
  surface: LoopFrameSurface
  /** Which step the user is currently on. Always 'studying' on
   *  Results today (the user just finished scanning, study is the
   *  next action). Prop is passed in (not hardcoded) so E-051 can
   *  reuse the component with live state. */
  currentStep: LoopFrameStep
  /** ATS score (0-100) shown on step 1. Required when currentStep
   *  is past 'scanned'; rendered as "Scanned · 71%". */
  scoreDisplay: number
  /** Missing-skill count shown on step 2. Renders as "N gaps". */
  gapCount: number
  /** Days until next interview, sourced from
   *  homeState.context.next_interview.date. `null` triggers the
   *  fallback copy "Set a date" on step 4. Negative values clamp
   *  to 0 ("today"). */
  daysUntilInterview: number | null
  /** Optional plan prop for the analytics payload (see §9). */
  plan: 'anonymous' | 'free' | 'pro'
}
```

### 4.4 Render contract (visual, design-token-only)

A horizontal strip on `lg+` viewports (4 cells side-by-side connected
by a thin connector line); a vertical stack on mobile (`<lg`, 4 rows
with the connector becoming a vertical divider). Each step is a small
card with:

- **Status indicator** (left): `✓` filled circle (token
  `bg-success`) for `scanned`; `●` filled accent circle (token
  `bg-accent-primary`) for the active step (matches `currentStep`);
  `○` outlined neutral circle (token `border-border`) for upcoming.
- **Step label** (verbatim, locked at §14 OQ-2): "Scanned",
  "Studying", "Re-scan", "Interview".
- **Sub-line** (small, `text-text-muted`): step-specific data
  (score, gap count, fallback ellipsis, days-until or "Set a date").

No hex values. No inline `style={{ color: '...' }}`. All colors via
Tailwind utilities backed by design tokens per `.agent/skills/design-system.md`
R12. Connector line uses `border-border` between cells.

### 4.5 Data wiring (Results.tsx consumer)

`Results.tsx` already calls `useAnalysisContext()` and renders the
hydrated `result: AnalysisResponse`. It does NOT currently call
`useHomeState()`. This spec wires `useHomeState()` into Results.tsx
specifically to read `homeState.data?.context.next_interview.date`.

Wiring shape (impl reference, exact lines locked at impl):

```tsx
// In Results.tsx, near the existing useAnalysisContext() call:
const homeState = useHomeState()
const nextInterview = homeState.data?.context.next_interview ?? null
const daysUntilInterview = nextInterview
  ? Math.max(0, daysBetween(new Date(), parseISO(nextInterview.date)))
  : null
```

`daysBetween` and `parseISO` are existing utilities in
`src/utils/date.ts` (or equivalent — impl Step 0 audit confirms exact
helper name). If neither exists, impl uses `date-fns` directly (already
a project dep; verified at impl Step 0).

The `homeState.isLoading` and `homeState.error` cases render the loop
frame with `daysUntilInterview = null` (treats unknown as no-date) —
the frame is best-effort and never blocks the page render. This is
asserted at AC-5.

`gapCount` is `result.skill_gaps.length` (NOT `missing_keywords` —
gaps are the same data the missing-skills section consumes). When
`skill_gaps.length === 0`, the frame still renders but step 2 reads
"0 gaps" (covered as edge case in §10).

### 4.6 Plan source

`Results.tsx` already derives `missingSkillsPlan: 'anonymous' | 'free' |
'pro'` for `MissingSkillsPanel` (per spec #22). The same value is passed
into `<LoopFrame>`. No new plan-detection is introduced.

---

## 5. Schemas

None. FE-only component; props are the contract; types live in
`LoopFrame.tsx` (exported).

---

## 6. Backend

None. No endpoint changes. No service changes. No model changes.

---

## 7. Migrations

None.

---

## 8. Frontend

### 8.1 New file

- `src/components/dashboard/LoopFrame.tsx` — props + step-cell render
  + connector line + analytics fire-on-mount via `useRef` idempotency
  guard (matches `home_dashboard_viewed` / `paywall_hit` /
  `home_study_gaps_prompt_shown` convention).

### 8.2 Edits to `Results.tsx`

1. Import `useHomeState` + `LoopFrame`.
2. Read `homeState` and compute `daysUntilInterview`.
3. Insert one `<motion.div>` grid child between Job Fit (line ~310)
   and Missing Skills (line ~334) with `id="loop-frame"` and the
   full-width column-span classes from §4.2. Inside, render
   `<LoopFrame ... />`.

The existing 11 grid children (per spec #21 / E-009) become 12. DOM
order: ATS Score (1) → Job Fit (2) → **LoopFrame (3, NEW)** → Missing
Skills (4) → Keywords (5) → Skills Radar (6) → Bullets (7) → Score
Breakdown (8) → Formatting (9) → Improvements (10) → top-strengths
sidebar (11) → CTAs sidebar (12).

The Missing Skills section keeps `id="missing-skills"` and its
`lg:col-span-2 lg:col-start-1 lg:row-start-5` classes — explicit grid
positioning means inserting LoopFrame between Job Fit and Missing
Skills in DOM order does NOT shift Missing Skills' grid position.
This is asserted at AC-9 (regression on the spec #21 ordering test).

### 8.3 No edits to:

- `MissingSkillsPanel.tsx` (E-011 territory, locked).
- `PaywallModal.tsx` (no new trigger; existing `skill_gap_study`
  remains the upsell hook).
- `PanelSection.tsx` (LoopFrame is a peer of `<PanelSection>`, NOT
  rendered inside one — it has no info-icon tooltip).
- Any `pages/HomeDashboard.tsx` surface (E-050 / E-051 territory).
- Any AppShell file (E-051 territory).
- `App.tsx`, routes, redirects.

### 8.4 Responsive behavior

- `<lg` (mobile): 4-step vertical stack, each step a full-width row
  with a 12-px-tall connector below it. Last step has no connector.
- `lg+`: 4-step horizontal strip, equal-width cells with a 24-px
  connector between cells. The strip spans the full grid width
  (`lg:col-span-2 xl:col-span-3`).

Locked at §14 OQ-3 hint (vertical stack on mobile, not 2×2 grid, not
horizontal scroll — readability over compactness).

### 8.5 Empty / fallback states

- **No interview date** (`nextInterview === null`): step 4 reads
  "Interview" + sub-line "Set a date" (no countdown). No CTA
  (click-through is E-051's job).
- **`skill_gaps.length === 0`**: step 2 still renders with sub-line
  "0 gaps". The missing-skills section below the frame separately
  renders its own "no gaps detected" empty state (existing behavior
  per `MissingSkillsPanel.tsx:85-94`).
- **`homeState` still loading or errored**: treat as no-date case.
  Frame renders without blocking on the home-state fetch.
- **Anonymous user** (`plan === 'anonymous'`): frame renders
  identically to free / pro. No special copy. Analytics event still
  fires with `plan: 'anonymous'`.

---

## 9. Analytics

### 9.1 New event

| Event | Source file | Properties |
|-------|-------------|-----------|
| `loop_frame_rendered` | `components/dashboard/LoopFrame.tsx` | `{surface: 'results', current_step: 'scanned' \| 'studying' \| 'rescan' \| 'interview', has_interview_date: boolean, plan: 'anonymous' \| 'free' \| 'pro'}` |

Fires **once on mount** via `useRef` idempotency guard (matches
`home_dashboard_viewed` / `paywall_hit` / `home_study_gaps_prompt_shown`
convention — see `.agent/skills/analytics.md` lines 71, 74, 76).

### 9.2 Why a render-event, not a click-event

There are no clickable steps in this slice (§3 non-goal). Conversion
attribution flows through the existing `missing_skills_cta_clicked`
event from E-011 — the frame's job is to *frame* the upsell, not to
own the click. The render event tells us how often free users on
Results see the loop pitch, which is the leading indicator on the
funnel from "saw the loop" → "clicked study cards" → "hit the wall" →
"upgraded".

### 9.3 Catalog update

`.agent/skills/analytics.md` gains a new row in the Frontend events
table (alphabetical-by-source ordering preserved — insert near
existing `home_*` rows). Row text:

```
| `loop_frame_rendered` | `components/dashboard/LoopFrame.tsx` | `{surface: 'results', current_step: 'scanned' | 'studying' | 'rescan' | 'interview', has_interview_date: boolean, plan: 'anonymous' | 'free' | 'pro'}` — fires once per mount via `useRef` idempotency guard. `surface` is `'results'` on this slice; E-051 widens to `'appshell'` for the live loop strip. The four `current_step` values are locked verbatim per §14 OQ-2 (E-049 spec #64) so E-051 can join the funnel without drift (spec #64). |
```

Catalog row added in the same impl commit as the event-fire wiring
(per analytics.md discipline — events ship with their catalog row).

### 9.4 Existing events — not touched

- `missing_skills_cta_clicked` (E-011) — unchanged. Conversion
  attribution still flows through it.
- `paywall_hit` — unchanged; no new `surface` enum value introduced
  by this spec (the loop frame doesn't open a paywall; the
  missing-skills CTAs do, via E-011).
- `results_tooltip_opened` 9-value section enum — unchanged. The
  loop frame has no tooltip. Asserted at AC-9.

---

## 10. Test plan

### 10.1 New Vitest file

`tests/components/LoopFrame.test.tsx` (new file). Mocks PostHog
`capture` and tests:

1. **AC-1 / AC-2 baseline render** — renders 4 step labels in DOM
   order: "Scanned", "Studying", "Re-scan", "Interview".
2. **AC-2 current-step indicator** — `currentStep="studying"` →
   step 2 has the active-state class set (assert on a stable
   `data-testid` like `loop-step-studying` having `data-current="true"`).
3. **AC-4 score display** — `scoreDisplay={71}` → step 1 sub-line
   contains "71".
4. **AC-4 gap count display** — `gapCount={5}` → step 2 sub-line
   contains "5 gaps". `gapCount={0}` → "0 gaps".
5. **AC-5 no-date fallback** — `daysUntilInterview={null}` → step 4
   sub-line reads "Set a date" (verbatim).
6. **AC-5 days-until display** — `daysUntilInterview={7}` → step 4
   sub-line contains "7" (and a units-of-time string; impl picks
   between "7d", "7 days" — locked at §14 OQ-5).
7. **AC-6 mount-once analytics** — `loop_frame_rendered` fires
   exactly once after `render()`; payload matches §9.1 contract;
   re-render of the same component instance does NOT re-fire (useRef
   guard); fresh mount via second `render()` call DOES fire (matches
   `Results.ordering.test.tsx` "Strict-Mode-like remount" pattern at
   `tests/pages/Results.ordering.test.tsx:165-183`).
8. **AC-6 plan prop in payload** — three sub-tests (one per plan
   value `anonymous` / `free` / `pro`).
9. **R12 design-tokens compliance** — snapshot or class-list assert
   that no inline `style.color` / `style.background` exists on any
   rendered element. (Pattern: `container.querySelectorAll('[style]')`
   filtered for color-ish props.)

### 10.2 New Vitest case in `tests/pages/Results.ordering.test.tsx`

Single new ordering invariant added to the existing 8-test file:

10. **AC-9 LoopFrame ordering** — `assertBefore('job-fit', 'loop-frame')`
    AND `assertBefore('loop-frame', 'missing-skills')`. Existing 8
    invariants unchanged. The 9-value `results_tooltip_opened` enum
    in `test_section_ids_unchanged` stays at 9 values (loop-frame
    explicitly excluded).

### 10.3 Regression set (must stay green)

The following test files run unchanged before/after and must stay
green at impl Step 4:

- `tests/pages/Results.ordering.test.tsx` (8 → 9; added invariant
  per §10.2; existing 8 unchanged).
- `tests/pages/Results.layout.test.tsx` (3 tests; sticky-class
  guards + skills-radar single-row + improvements-two-rows).
- `tests/pages/Results.tooltips.test.tsx` (1 test; every section
  renders an info icon — loop-frame is exempt as it has no
  PanelSection wrapper, so the test list of expected sections is
  unchanged).
- `tests/pages/Results.reanalyze.test.tsx` (4 tests; AC-1..AC-4 of
  spec #55 paywall on re-analyze — orthogonal).
- `tests/pages/Results.optimize.test.tsx` (5 tests; spec for
  Optimize button — orthogonal).
- `tests/pages/Results.hydration.test.tsx` (7 tests; AnalysisContext
  hydration — orthogonal).
- `tests/components/MissingSkillsPanel.cta.test.tsx` (E-011 CTA
  coverage — orthogonal; this spec does not edit the panel).

### 10.4 Test-count envelope

Estimated **+9 FE** (8 in new `LoopFrame.test.tsx` + 1 in
`Results.ordering.test.tsx`). Floor `+7`, ceiling `+11`, target `+9`.
BE unchanged. Final delta locked at impl Step 4 close-trail.

### 10.5 Manual post-deploy verification

- Sign in as a free user, run a scan, land on `/prep/results`,
  visually verify the 4-step strip renders above missing skills with
  current-step = Studying. Score and gap count match the page's
  other widgets.
- Set an interview date via Tracker (`/prep/tracker?new=1`), reload
  Results, verify step 4 shows the day count.
- Clear the interview date, reload, verify step 4 shows "Set a date".
- Toggle the three themes (dark / light / midnight-blue) and verify
  the frame respects each theme's tokens (no hardcoded colors).

---

## 11. Acceptance Criteria

- **AC-1** — `<LoopFrame>` renders 4 labeled step cells in DOM order:
  "Scanned", "Studying", "Re-scan", "Interview" (verbatim).
- **AC-2** — The cell matching `currentStep` is visually distinct
  (active-state class set on a stable `data-testid` selector); other
  cells use `done` (for past steps) or `upcoming` (for future steps)
  state classes.
- **AC-3** — The mount in `Results.tsx` spans the full grid width:
  `lg:col-span-2 lg:col-start-1 xl:col-span-3 xl:col-start-1` (or
  whatever the impl audit confirms is the equivalent — locked at
  impl Step 0 against the live grid template).
- **AC-4** — Step 1 sub-line shows the ATS score from
  `result.ats_score`; step 2 sub-line shows the gap count from
  `result.skill_gaps.length`.
- **AC-5** — When `homeState.data?.context.next_interview === null`
  (or homeState is loading / errored), step 4 sub-line reads "Set a
  date" verbatim. When non-null, step 4 sub-line shows the day count
  to the interview date (negative clamps to 0).
- **AC-6** — `loop_frame_rendered` fires exactly once per component
  mount (useRef-guarded), with payload `{surface: 'results',
  current_step, has_interview_date, plan}` matching §9.1.
- **AC-7** — Zero backend changes: no new files in `app/`, no
  alembic migrations, no `pyproject.toml` / `requirements*.txt`
  edits.
- **AC-8** — `tsc --noEmit` clean. No new ESLint warnings introduced.
- **AC-9** — Spec #21 / spec #22 regression set stays green
  (file list in §10.3). The `results_tooltip_opened` 9-value section
  enum is unchanged. The Missing Skills section keeps
  `id="missing-skills"` and its existing grid-position classes
  (`lg:col-span-2 lg:col-start-1 lg:row-start-5 xl:col-start-3
  xl:col-span-1 xl:row-start-1`).
- **AC-10** — R12 design-tokens compliance: every color in
  `LoopFrame.tsx` comes from a Tailwind utility backed by a token in
  `design-tokens.ts` (no `style={{ color: '...' }}`, no `#`-prefixed
  hex literals, no `rgb(...)` literals).
- **AC-11** — The frame is mounted on `/prep/results` only. No mount
  on `/home`, `/learn/*`, AppShell, or any other route. Asserted by
  a `grep`-style test that searches `App.tsx` and `AppShell.tsx` for
  `LoopFrame` and finds zero matches (LoopFrame's only consumer is
  `Results.tsx`).

---

## 12. Locked Decisions

*(Empty at spec-author. Populated by §12 amendment slice or by impl
slice's Step 2 SCOPE GATE per Phase-6 amendment-slice precedent. The
14 §14 OQs below carry author hints to guide the lock; if all hints
are accepted as-is at impl Step 0, no separate amendment slice is
needed.)*

---

## 13. Out of scope

### 13.1 Owned by E-051

- Live state on the frame (real progress dots derived from
  `tracker_application_scores` history).
- Click-through on step 3 ("Re-scan") to open the tracker rescan
  modal.
- Animation between steps when state changes.
- Mount in `AppShell.tsx` so the frame persists across `/home`,
  `/learn/*`, `/prep/*` for Interview-Prepper users with an
  `next_interview` set.
- Render gate based on persona + chromeless paths (B-057 / B-058
  pattern).
- Step-completion telemetry (`loop_strip_step_completed`,
  `loop_strip_rescan_unlocked`).

### 13.2 Owned by E-011 (already shipped)

- The Pro upsell button on missing skills.
- The `missing_skills_cta_clicked` event.
- The `MissingSkillsPanel` three-state CTA branching.

### 13.3 Spec #21 ordering invariant

Spec #21 §UI codifies "11 direct grid children flatten to mobile/tab
order". This spec inserts a 12th direct child between Job Fit and
Missing Skills. The spec #21 ordering test
(`tests/pages/Results.ordering.test.tsx::test_section_ids_unchanged`)
keeps its 9-value `results_tooltip_opened` enum at 9 (loop-frame is
not a tooltip section). The grid-child count is amended +1 — this
spec is the amendment.

### 13.4 Persona variants of the frame

Out of scope. The frame on Results is persona-agnostic — every
signed-in scanner sees the same 4 steps. E-051's persona-IP gate
applies only to the AppShell mount.

### 13.5 Step copy variants / A/B testing

Out of scope. The four step labels ("Scanned", "Studying", "Re-scan",
"Interview") are LOCKED VERBATIM at §14 OQ-2 hint. E-051 inherits
them. A/B testing of the labels is forward work for a future slice
(no row filed today; would need a JC at the time it's proposed).

### 13.6 Tooltip on the loop frame

Out of scope. Adding a tooltip would require extending the
`results_tooltip_opened` enum, which couples to spec #21's section
enum. If a tooltip becomes useful (post-launch user feedback), it's
a separate slice with its own enum amendment.

---

## 14. Open Questions (with author hints)

### OQ-1 — Mount position relative to existing Results grid

**Question:** Where in the Results page DOM does the loop frame
mount?

**Options:**
- (a) Above the entire grid (between page header and grid container).
- (b) **As a new direct grid child between Job Fit and Missing
  Skills, full-width spanning all columns.**
- (c) Above the ATS Score / Job Fit row (i.e., as a "row 0" before
  any of the 11 existing children).

**Author hint:** **(b)**. Above-grid (a) breaks the consistent
container styling. Above the score (c) competes with the score widget
visually and pushes the most-actionable content (Job Fit) below the
fold on mobile. Between Job Fit and Missing Skills (b) places the
frame *immediately above the upsell it is framing* — the visual
sequence reads "you scanned (top), here's why (Job Fit), here's where
this fits (loop), here's what to do (Missing Skills)".

### OQ-2 — Step copy

**Question:** Are the four step labels "Scanned / Studying / Re-scan
/ Interview" locked verbatim, or open to alternatives?

**Options:**
- (a) **Lock verbatim — "Scanned" / "Studying" / "Re-scan" /
  "Interview". E-051 depends on this.**
- (b) Allow impl-time copy variants ("Scanning" instead of "Scanned",
  "Apply" instead of "Interview").
- (c) Defer copy to a separate copy-author slice.

**Author hint:** **(a)**. E-049's BACKLOG row and the prompt for this
spec both call out "lock the four-step copy verbatim so E-051 doesn't
drift". Single source of truth lives in this spec. Any future change
requires a §12 amendment that flows through E-051 in lockstep.

### OQ-3 — Mobile responsive layout

**Question:** How does the 4-step strip lay out on mobile (`<lg`)?

**Options:**
- (a) **Vertical stack — 4 rows, full-width, with a vertical
  connector. Same step content, just stacked.**
- (b) 2×2 grid (Scanned / Studying on top row, Re-scan / Interview
  on bottom).
- (c) Horizontal scroll (4 cells, scroll horizontally if they don't
  fit).

**Author hint:** **(a)**. Vertical stack matches the rest of the
Results page mobile pattern (everything stacks). 2×2 grid (b)
implies a non-linear sequence — visually wrong for a loop. Horizontal
scroll (c) hides 2-3 steps off-screen, defeating the
"see-the-whole-loop-at-once" goal.

### OQ-4 — Component file location

**Question:** Where does `LoopFrame.tsx` live?

**Options:**
- (a) **`src/components/dashboard/LoopFrame.tsx`** (alongside
  `MissingSkillsPanel`, `PanelSection`, `JobFitExplanation`, etc.).
- (b) `src/components/layout/LoopFrame.tsx` (with `AppShell`,
  `TopNav`).
- (c) `src/components/results/LoopFrame.tsx` (new directory).

**Author hint:** **(a)**. `dashboard/` is the existing home for
Results-page primitives — the surface this slice ships on. `layout/`
is for AppShell-level chrome — E-051 may relocate or re-export when
it mounts in AppShell, but on this surface today the component is a
Results primitive. `results/` (c) introduces a new directory for one
file — premature abstraction.

E-051 follow-up note: when the live version mounts in AppShell, the
right move is likely to keep the file in `dashboard/` and have
AppShell import it (cross-directory imports are already standard in
this codebase — `App.tsx` imports from every directory). E-051 owns
that decision.

### OQ-5 — Day-count format

**Question:** When `daysUntilInterview = 7`, does step 4 sub-line
read "7d", "7 days", or "in 7d"?

**Options:**
- (a) **"in 7d"** (matches `CountdownWidget` precedent — see
  `components/home/widgets/CountdownWidget.tsx` for the
  established convention).
- (b) "7 days" (more literal, less compact).
- (c) "7d" (compact, no preposition).

**Author hint:** **(a) "in 7d"**. Matches the existing
`CountdownWidget` copy on `/home` so users don't see two different
formats for the same data across surfaces. Impl Step 0 audit
confirms exact CountdownWidget format string.

### OQ-6 — `homeState.error` UX

**Question:** When `useHomeState()` returns an error (network
failure, 5xx), how does the loop frame render?

**Options:**
- (a) **Render with `daysUntilInterview = null` (no-date fallback;
  step 4 reads "Set a date").**
- (b) Don't render the frame at all (return null from `<LoopFrame>`).
- (c) Render with an error state on step 4 ("Couldn't load — try
  reload").

**Author hint:** **(a)**. The frame is best-effort context — it
must NEVER block the Results page render or crash the user's scan
flow. Treating an errored homeState as "no date" is identical UX to
the genuinely-no-date case, which is fine: the user sees the frame
and can act on it. Hiding the frame (b) loses the value-prop on every
homeState hiccup. Showing an error (c) advertises an internal
problem on a surface where it's not actionable.

### OQ-7 — Zero-gap render

**Question:** When `result.skill_gaps.length === 0`, does the loop
frame render at all?

**Options:**
- (a) **Render normally, step 2 sub-line reads "0 gaps".**
- (b) Render but suppress step 2 (collapse to a 3-step strip).
- (c) Don't render the frame at all when there are no gaps.

**Author hint:** **(a)**. The loop is the loop regardless of how
many gaps the user has — a 0-gap user is still in the loop and might
re-scan a different JD next, or pick up the cards anyway. Suppressing
step 2 (b) breaks the visual contract E-051 inherits (always 4
steps). Hiding the frame (c) loses the framing for the rest of the
funnel and creates an empty-state mismatch with the missing-skills
section right below it (which renders its own "no gaps detected"
state).

### OQ-8 — Anonymous-user render

**Question:** Does the loop frame render for anonymous users on
`/prep/results`?

**Options:**
- (a) **Yes, render identically to free / pro. Plan prop in
  analytics is `'anonymous'`.**
- (b) No — only render for authed users.

**Author hint:** **(a)**. The loop frame's job is to *frame* the
upsell. An anonymous user seeing it gets the same value: "this scan
is one step in a loop". If the frame helps them sign up, that's the
funnel working. Hiding it from anonymous users would be the same
mistake spec #22 fixed for the missing-skills CTA (E-011's
`anonymous` branch). Consistent with E-011's decision.

### OQ-9 — `tsc` clean policy under existing pre-existing warnings

**Question:** The codebase has a known pre-existing
`ScoreDeltaWidget.tsx` unused-import warning (mentioned in
SESSION-STATE Recently Completed entries). Does AC-8 require
*zero* warnings, or just *no new* warnings?

**Options:**
- (a) **No NEW warnings introduced by this slice; pre-existing
  warnings carry forward.**
- (b) Zero warnings at impl Step 4 close (would require fixing the
  pre-existing warning, violating C3).

**Author hint:** **(a)**. C3 single-concern is the binding rule.
Pre-existing dirt stays pre-existing. Impl Step 4 verifies *no new*
warnings.

### OQ-10 — Connector style (visual contract for E-051)

**Question:** Is the connector between step cells a thin line, a
chevron arrow, or no connector at all?

**Options:**
- (a) **Thin line (`border-border` token), 24-px gap on desktop,
  vertical 12-px line on mobile.**
- (b) Chevron arrow (`>` between cells).
- (c) No connector — cells are visually grouped by proximity only.

**Author hint:** **(a)**. Thin line is the simplest, most
theme-portable, and reads as a sequence without committing to
directionality the way chevrons do (some users may parse the loop
right-to-left in RTL locales — out of current scope but worth not
hardcoding). E-051 inherits this; if E-051 wants to add motion/glow
on the active connector, it's an additive change, not a rework.

### OQ-11 — `current_step` value on Results

**Question:** What value does `currentStep` take when LoopFrame is
mounted on Results?

**Options:**
- (a) **`'studying'` always (the user just finished step 1
  "scanned" by virtue of being on Results — step 2 is the next
  action they should take, which is the missing-skills CTA right
  below the frame).**
- (b) `'scanned'` (frame the user as currently in step 1, study is
  upcoming).
- (c) Derive from data (if the user has reviewed cards from this
  scan's gap-set, advance to a later step).

**Author hint:** **(a)**. (b) makes "Scanned" both the most recent
*and* current state, which is visually confusing (you'd want a
filled-and-active indicator, breaking the 4-state visual semantics).
(c) is exactly what E-051 owns — live state derivation; this spec is
explicitly static. (a) keeps the visual semantics clean: ✓ Scanned
done, ● Studying active, ○ Re-scan upcoming, ○ Interview upcoming.

### OQ-12 — Component prop required-ness

**Question:** Are `scoreDisplay` and `gapCount` required props, or
optional with defaults?

**Options:**
- (a) **Required. Pass-through only. Forces the consumer to wire
  them.**
- (b) Optional with `undefined` → render the step without sub-line
  data.

**Author hint:** **(a)**. Results.tsx already has both values
trivially (`result.ats_score` and `result.skill_gaps.length`).
Optional props invite drift — E-051's AppShell consumer will have
different data sources but should still pass real values, not omit.
TypeScript-required props document the contract.

### OQ-13 — `surface` enum value

**Question:** What's the `LoopFrameSurface` union shape?

**Options:**
- (a) **`'results'` only this slice. E-051 will widen to `'results'
  | 'appshell'`.**
- (b) Lock both values now (`'results' | 'appshell'`) so E-051
  doesn't have to re-edit the type.

**Author hint:** **(a)**. YAGNI. E-051 will edit the union when it
needs the value. Locking now means a value with no consumer for
weeks/months — a reader of the code today would wonder why
`'appshell'` exists. (a) is an additive change at E-051 ship time
with zero migration cost.

### OQ-14 — Where does the test file live?

**Question:** New Vitest file path?

**Options:**
- (a) **`tests/components/LoopFrame.test.tsx`** (matches existing
  `tests/components/MissingSkillsPanel.cta.test.tsx`,
  `tests/components/KeywordChart.colors.test.tsx` precedent).
- (b) `tests/components/dashboard/LoopFrame.test.tsx` (mirrors
  source dir).

**Author hint:** **(a)**. The existing `tests/components/` flat
structure is the precedent. `tests/components/dashboard/` would be a
new sub-directory for one file.

---

## 15. Forward links

- **E-051** — Live loop-progress strip in AppShell for
  Interview-Prepper. Consumes `<LoopFrame>` with `surface='appshell'`
  and live `currentStep` derived from
  `tracker_application_scores` history. The visual contract (step
  copy, step order, primitive name) locked here is consumed there
  without renegotiation. E-051 widens `LoopFrameSurface` and adds
  click-through, animation, and persona-IP render gate.
- **E-050** — Status-sentence hero on `/home`. Orthogonal surface
  (different page, different data). Both ship in any order; no
  ordering dependency between them.
- **E-053** — Career-Climber habit ribbon + skill-radar trend on
  `/home`. Orthogonal surface (CC persona, /home, different data).
  Cohort-gated activation (≥50 CC users).

---

*End of spec #64.*
