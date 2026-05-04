# P5-S66 — Live loop-progress strip in AppShell (Interview-Prepper)

## Status: 🔴 Drafted

| Field | Value |
|-------|-------|
| **Slice** | P5-S66 (FE-led + 1 small BE endpoint; spec-author this slice) |
| **Phase** | 5D (persona-aware surface) |
| **Mode** | Mode 4 spec-author → followed by §12 amendment slice → impl slice (B-122 forward-filed) |
| **Filed at** | `<this-slice>` (spec-author commit) |
| **BACKLOG row (impl, forward-filed)** | **B-122** 🔴 — filed at status 🔴 by this slice for the future implementation slice per R15(c). R17 watermark verified at filing: B-121 highest in-use, B-122 next-free per disk. |
| **Closes** | **E-051** on impl-slice merge. |
| **Depends on** | spec #34 (PersonaPicker + persona-aware home; shipped) ▪ spec #57 (`homeState.context.next_interview` envelope; shipped `b13f410`) ▪ spec #63 / E-043 (`tracker_application_scores` + `useScoreHistory`; shipped `4aab0bf`) ▪ spec #64 / B-119 (`<LoopFrame>` static visual contract; shipped `b58a42d`) ▪ spec #65 / B-120 (status-hero pattern + persona gating + once-on-mount analytics; shipped `58bb9a9`) ▪ B-086a / B-086b (`tracker_application_score_service.write_score_row`; shipped) ▪ existing `AppShell.tsx` chromeless-paths convention. |
| **Blocks** | none direct. E-053 (CC habit ribbon) is orthogonal — different persona, different surface. |
| **Cross-refs** | spec #64 / E-049 / B-119 (LoopFrame primitive — this spec EXTENDS) ▪ spec #65 / E-050 / B-120 (status-hero pattern — analogous additive composition) ▪ spec #61 (composition rules — strip is NOT a state-slot widget; lives in AppShell layer above HomeDashboard) ▪ spec #57 (NextInterview envelope) ▪ spec #63 (score history + rescan loop) ▪ `.agent/skills/design-system.md` (R12 token-only styling) ▪ `.agent/skills/analytics.md` (event catalog discipline). |

---

## 1. Problem

The closed-loop differentiator (`Scanned → Studying → Re-scan → Interview`) ships today as a **static** visual on `/prep/results` (E-049 / spec #64 / B-119) and as a one-line **status sentence** on `/home` (E-050 / spec #65 / B-120). Both surfaces are **per-page** — the user has to be on Results or Home to see the loop. As soon as they navigate to `/learn/daily` to study, or `/prep/tracker` to manage applications, the loop is invisible.

This is the differentiator that justifies $49/mo over Jobscan's $29 — and today it surfaces only twice. E-051 makes it persistent in **AppShell**: every authenticated, non-chromeless page for an Interview-Prepper with an upcoming interview shows a thin live strip with the user's current loop position. Click step 3 (when unlocked) to re-scan; otherwise read-only.

The strip's **liveness** distinguishes it from spec #64's static frame: per-step state is computed from shipped infrastructure (E-042 next_interview + E-043 score history + B-086b reviewed-card counts via a new gap-progress endpoint) and updates as the user makes progress.

### 1.1 What's already shipped (out of scope this spec)

- **`<LoopFrame>` static four-step visualization** — spec #64 / B-119 at `src/components/dashboard/LoopFrame.tsx`. Accepts `surface: 'results'`, `currentStep: 1|2|3|4`, score / gapCount / interviewDate / plan props. Step labels locked verbatim ("Scanned" / "Studying" / "Re-scan" / "Interview") so this spec inherits without drift. **This spec extends LoopFrame** rather than duplicating its labels — see §4.1 LoopFrame Refactor Decision.
- **`useScoreHistory(tracker_id)` hook** — spec #63 / B-086b at `src/hooks/useScoreHistory.ts`. Returns `ScoreHistoryResponse { tracker_application_id, history: ScoreHistoryEntry[], delta }`; `history` is oldest-first.
- **`homeState.context.next_interview`** — spec #57. `NextInterview { date, company, tracker_id }` or null.
- **`AppShell.tsx` chromeless-paths convention** — `CHROMELESS_PATHS = {'/', '/login', '/onboarding/persona', '/first-action'}` plus the `/pricing` guest-only carve-out. The strip uses the SAME predicate (`showChrome`) — wherever TopNav/MobileNav render, the strip is eligible to render too.
- **B-027 first-visit/return-visit greeting fork** — orthogonal. Strip lives in AppShell, not HomeDashboard; greeting state is `/home`-local.

### 1.2 What this spec ships

A new FE component `<LoopProgressStrip>` mounted in `AppShell.tsx` between `<TopNav />` and `<main>`, rendering the four-step loop with **per-step live state** and an optional click-through on step 3 (Re-scan). One small new BE endpoint `GET /api/v1/learn/loop-progress?tracker_id={id}` returning the gap-card review progress for step 2. Four new analytics events. Backward-compatible extension to `<LoopFrame>` adding optional `stepStates` + `onStepClick` props (see §4.1).

---

## 2. Goals

- **G-1** Render a live four-step strip in AppShell for Interview-Prepper users with an upcoming interview, persistent across `/home`, `/learn/*`, `/prep/*`.
- **G-2** Reuse the visual contract from spec #64 / `<LoopFrame>` — single source of truth for step labels, ordering, base styling.
- **G-3** One new BE endpoint to compute gap-card review progress for step 2 ("Studying"). No new tables, no migrations.
- **G-4** Click-through on step 3 (when unlocked) deep-links to `/prep/tracker?focus={tracker_id}&action=rescan` — consumes the rescan flow shipped at E-043 / B-086b.
- **G-5** Coexist with the existing AppShell chrome (TopNav, MobileNav) and the chromeless-path pattern; render exactly when chrome renders AND persona-IP AND next_interview != null.

---

## 3. Non-goals

- Career-Climber variant of the strip — owned by **E-053** (habit ribbon + skill-radar trend; different persona, different surface).
- Team Lead variant — `team_lead` returns null in the strip's render gate.
- Animations / step-change transitions — static state changes only this slice (Framer Motion entrance is a follow-on).
- Click-through on steps 1, 2, 4 — only step 3 is interactive (see §8.4).
- Strip on chromeless paths (`/`, `/login`, `/pricing` guest, `/onboarding/persona`, `/first-action`) — gated off by the same predicate as TopNav.
- Mobile-specific compact layout beyond responsive breakpoint (icon-only at <md, full labels + sublines at md+).
- Any change to the existing `<LoopFrame>` Results.tsx call site — backward-compatible extension (§4.1).
- Any change to `<HomeStatusHero>` from spec #65 — orthogonal layer.
- Suppression rules between strip and on-page surfaces (Results LoopFrame, HomeStatusHero) — `next_interview != null` + persona-IP user sees both today's surfaces AND the strip; multiple-emphasis is intentional minimum-viable scope (mirrors E-050 D-5 default lean).
- A "dismissed for this session" affordance — out of scope.
- Any change to home-state Redis cache invalidation strategy beyond what spec #40 already wires.

---

## 4. Architecture

### 4.1 LoopFrame refactor decision

The BACKLOG row asked: (a) extract shared primitive, (b) duplicate labels (drift risk), (c) import as-is and extend via state props.

**Decision: hybrid (a)+(c) — extend `<LoopFrame>` in place with optional new props; current Results.tsx call site stays byte-identical.**

Today `LoopFrame` derives per-step state from a single `currentStep` prop: index < currentStep → done (✓); index === currentStep → current (●); index > currentStep → future (○). This is sufficient for Results (one snapshot per scan) but insufficient for AppShell (step 3 has locked-vs-unlocked-but-not-current distinction; step 4 has overdue alert).

**Extension shape** (backward compatible — see §8.2 for full prop list):

| New prop | Type | Behavior |
|----------|------|----------|
| `surface` | widen `'results'` → `'results' \| 'appshell'` | Used only as analytics-event property (already cited in `analytics.md` row for E-051's planned widening). Visual rendering identical regardless of surface. |
| `stepStates?` | `Partial<Record<LoopFrameStep, StepState>>` where `StepState = 'done' \| 'current' \| 'locked' \| 'future' \| 'alert'` | When provided, OVERRIDES the linear `currentStep` derivation per step. When omitted, current behavior preserved (Results.tsx unchanged). |
| `onStepClick?` | `(step: LoopFrameStep) => void` | When provided, the rendered step becomes a `<button>` instead of a `<div>`; only steps with `stepStates[step] !== 'locked'` AND `stepStates[step] !== 'future'` are clickable (handler gated internally). |
| `compact?` | `boolean` (default `false`) | When `true`, hides sublines and reduces padding for the AppShell strip's tighter vertical budget. Results.tsx omits → default false → today's layout. |

Results.tsx call site (line N in spec #64 §8.1) **does not change** — it omits `stepStates` / `onStepClick` / `compact`, surface stays `'results'`. R12 token-only styling already in place; backward-compatibility verified by the existing `tests/components/LoopFrame.test.tsx` regression set (9 tests).

**Why hybrid not pure (a):** A clean refactor (move shared primitive to `components/dashboard/LoopFrame.tsx` and have a new `LoopFrameStrip` and `LoopFrameStatic` consume it) introduces 3+ new files and rewrites Results.tsx. Q1 simplicity prevails — extend in place.

**Why not pure (c):** LoopFrame today has no concept of "locked" or "alert" steps; the linear `currentStep` model can't express the AppShell strip's nuanced states. Adding `stepStates` + `onStepClick` is the minimum extension that captures the new use case.

### 4.2 Component composition

```
┌── AppShell.tsx (existing) ────────────────────────────────────┐
│  {showChrome && <TopNav />}                                   │
│  {showChrome && <LoopProgressStrip />}     ← NEW (this spec)  │
│  <main>{children}</main>                                      │
│  {showChrome && <MobileNav />}                                │
└────────────────────────────────────────────────────────────────┘

┌── LoopProgressStrip.tsx (new) ─────────────────────────────────┐
│  - Reads useAuth() → persona                                   │
│  - Reads useHomeState() → next_interview, last_scan_date, plan │
│  - Reads useScoreHistory(next_interview?.tracker_id) → score   │
│  - Reads useLoopProgress(next_interview?.tracker_id) → step 2  │
│  - Computes stepStates from the four data sources              │
│  - Returns null if persona !== 'interview_prepper' OR          │
│    next_interview == null OR all data sources unresolved       │
│  - Renders <LoopFrame surface="appshell"                       │
│              stepStates={...} onStepClick={...} compact />     │
│  - Fires `loop_strip_rendered` once on mount via useRef        │
│  - Fires `loop_strip_rescan_unlocked` once when step 3         │
│    flips locked → unlocked (useRef guard on prior state)       │
│  - Fires `loop_strip_step_completed` once per step that flips  │
│    to 'done' (per-step useRef map)                             │
└────────────────────────────────────────────────────────────────┘
```

### 4.3 Why AppShell, not a per-page mount

The strip is **persistent across pages** — that's the spec's core value proposition. Per-page mounts would (a) duplicate the component on every page and (b) risk drift between pages. AppShell is the single mount point that covers `/home`, `/learn/*`, `/prep/*` plus any future authenticated route.

### 4.4 Mount note (JC #1 — disk-vs-prompt drift)

Prompt body said "mounted in `AppShell.tsx` between `TopNav` and `<Outlet />`". Disk reality (`src/components/layout/AppShell.tsx:9-23`) shows AppShell takes `{children}` (NOT `<Outlet />`). Mount is between `<TopNav />` and `<main>{children}</main>`. Same DOM position as the prompt intended; only the React Router idiom differs. No spec-side concern.

---

## 5. Data model

No BE schema changes. Disk-fact references the strip reads (BE side):

| Source | Provides |
|--------|----------|
| `homeState.context.next_interview` (spec #57) | `{date, company, tracker_id}` for the upcoming interview's tracker |
| `homeState.context.last_scan_date` (spec #40) | ISO date of the most recent scan across all trackers — fallback for "days since last scan" |
| `homeState.context.plan` | `'free' \| 'pro' \| 'enterprise'` for analytics |
| `tracker_application_scores` table (spec #63 / B-086a) | Score history per tracker — read via `fetchScoreHistory(tracker_id)` |
| `tracker_applications_v2.skills_missing` (existing) | List of missing skill names from the latest scan; consumed by the new gap-progress endpoint |
| `cards` table (Phase 1) | Cards mapped to skill gaps via category lookup |
| `card_progress` table (Phase 1 + FSRS) | User's review state per card; consumed by the new gap-progress endpoint |

**No new columns. No new tables. No migrations.**

---

## 6. API contract

### 6.1 New endpoint: `GET /api/v1/learn/loop-progress`

**Purpose:** compute gap-card review progress for step 2 ("Studying") of the loop strip — the percentage of cards mapped to a tracker's skill gaps that the user has reviewed at least once.

**Auth:** required (`Depends(get_current_user)` per CLAUDE.md R3).

**Rate limit:** standard 100 req/min (no override).

**Query params:**
- `tracker_id` — required, UUID. Must belong to the authenticated user; 404 otherwise.

**Response shape:**
```python
class LoopProgressResponse(BaseModel):
    tracker_application_id: str
    total_gap_cards: int       # Cards mapped to skills_missing on the latest scan
    reviewed_gap_cards: int    # Of those, how many have ≥1 review (card_progress row exists)
    percent_reviewed: float    # reviewed_gap_cards / total_gap_cards × 100, 0 when total = 0
    days_since_last_scan: int | None  # From the latest score-history entry; null if no history
```

**Edge cases:**
- `total_gap_cards == 0` (no skill gaps mapped to cards) → `percent_reviewed = 0.0`, `reviewed_gap_cards = 0`. Step 2 renders as "future" (no work to do).
- Tracker has no scans → `days_since_last_scan = None`; step 1 renders as "future" (shouldn't fire if `next_interview != null`, but defensive).
- Tracker not owned by user → 404.

**Service location:** new method `compute_loop_progress(user_id, tracker_id, db)` in `app/services/learning_progress_service.py` (new file). Mapping logic: read `skills_missing` from latest `tracker_applications_v2` row → look up cards in matching categories OR cards with matching tags (locked at §14 OQ-3) → count + intersect with `card_progress.user_id`.

**Caching:** none this slice (in-process compute is cheap; ~50ms for typical 10 gap × 5 cards/gap = 50 cards). Future Redis cache mirrors `home_state_service` pattern if needed.

### 6.2 No other endpoint changes

- `GET /api/v1/home/state` (spec #40) — unchanged, consumed as-is for `next_interview` + `last_scan_date` + `plan`.
- `GET /api/v1/tracker/scores/{tracker_id}` (spec #63 / B-086b) — unchanged, consumed as-is for step 1 score + step 3 days-since-last-scan.

---

## 7. Routing / nav

No route changes. The strip is gated to render only when AppShell's existing `showChrome` predicate returns true (i.e., NOT on `/`, `/login`, `/pricing`-as-guest, `/onboarding/persona`, `/first-action`).

### 7.1 Chromeless-path interaction

The strip's render predicate is a **strict subset** of AppShell's `showChrome`:

```ts
const showStrip = showChrome
  && persona === 'interview_prepper'
  && nextInterview != null
```

When `showChrome` is false the strip is unconditionally false. This guarantees zero strip render on `/`, `/login`, `/pricing` guest, `/onboarding/persona`, `/first-action` — same paths where TopNav/MobileNav are hidden. Co-evolution: any future addition to `CHROMELESS_PATHS` automatically hides the strip.

### 7.2 TopNav height interaction

TopNav today is `~56px` (`md:` and up) with `pb-20 md:pb-0` margin on `<main>`. The strip adds `~64px` (md+) or `~48px` (<md) height **between** TopNav and `<main>`. No `<main>` padding-top change required because the strip is in normal document flow, not absolute-positioned. Spec §8 locks the strip's exact height for predictable layout.

### 7.3 Click-through deep link

Step 3 click → `navigate('/prep/tracker?focus=' + tracker_id + '&action=rescan')`. This deep-link consumes the `?focus={tracker_id}&action=rescan` handler shipped in `Tracker.tsx` at E-043 / B-086b. No new route, no new query-param contract.

---

## 8. UI / UX

### 8.1 Render gate (§3 + §7.1)

```
if !showChrome → null (chromeless path)
if !user || !user.persona → null (unauth or pre-persona)
if user.persona !== 'interview_prepper' → null
if !homeState.data?.context.next_interview → null
otherwise render <LoopFrame surface="appshell" stepStates={...} onStepClick={...} compact />
```

The **render gate is conservative** — partial-data states (e.g., `useScoreHistory` still loading) render the strip with `stepStates` filled in for resolved steps and `'future'` for unresolved. The strip never renders a placeholder skeleton; cold-start shows step 4 (Interview, days computed from `next_interview.date`) plus whatever else is resolved.

### 8.2 Step-state derivation table

| Step | Source | State logic |
|------|--------|-------------|
| 1 — **Scanned** | `useScoreHistory(next_interview.tracker_id)` | If history is empty → `'future'`. Otherwise → `'done'` with subline `"<latest_score>%"` (latest = `history[history.length - 1].overall_score`). |
| 2 — **Studying** | `useLoopProgress(next_interview.tracker_id)` (new hook wrapping new endpoint) | If `total_gap_cards === 0` OR step 1 is `'future'` → `'future'`. Else if `percent_reviewed < 50` → `'current'` with subline `"<reviewed>/<total>"`. Else → `'done'`. |
| 3 — **Re-scan** | derived from step 2 state + `days_since_last_scan` | If step 2 is not `'done'` OR `days_since_last_scan == null` OR `days_since_last_scan < 3` → `'locked'`. Else if a re-scan has not happened since the last lock-flip → `'current'` (clickable). Else → `'done'` (a fresh score row exists post-unlock; deciding "post-unlock" requires comparing `history[history.length - 1].scanned_at` with the slice's last unlock-time. Locked at §14 OQ-1.) |
| 4 — **Interview** | `next_interview.date` | Compute `days = ceil((targetMidnightUtc - todayMidnightUtc) / 86400000)`. If `days < 0` → `'alert'` with subline `"Overdue"`. Else if `days <= 7` → `'current'` with subline `"in <days>d"`. Else → `'future'` with subline `"in <days>d"`. (Step 4 is never `'done'` until the interview date passes; per design, a passed interview becomes `'alert'` not `'done'` because the user did not mark the interview complete — capture is forward-filed to E-052/E-053 territory.) |

### 8.3 Visual rendering (compact mode)

When `compact={true}`, LoopFrame:
- Reduces vertical padding from `p-4` to `p-2` (≈64px → ≈48px total height at md+).
- On `<md`: hides sublines, shows icon + step label only, vertically stacked compresses to `~48px` per step total ≈ 192px on mobile (acceptable per §14 OQ-2).
- At `md+`: keeps sublines (sublines are short — score%, gap-count, "in Nd").

`alert` state (step 4 overdue): icon + label rendered with `text-danger` + `border-border-danger`. New token mapping if `border-border-danger` does not exist (verify in design-tokens.ts at impl); fallback to `border-danger`.

`locked` state (step 3 not yet unlocked): rendered with the existing `'future'` styling (text-text-muted, border-border) plus a small lock icon (lucide-react `Lock`, size 12) inline next to the step label. No interactive affordance.

### 8.4 Click behavior

Only step 3 is clickable, and only when `stepStates[3] === 'current'`. Click handler:

```ts
function handleStepClick(step: LoopFrameStep) {
  if (step !== 3) return  // defense; LoopFrame internal gate already prevents
  capture('loop_strip_step_clicked', {
    step: 3,
    current_step: deriveCurrentStep(stepStates),
    plan: homeState.data?.context.plan ?? 'free',
  })
  navigate(`/prep/tracker?focus=${tracker_id}&action=rescan`)
}
```

`deriveCurrentStep`: returns the lowest index whose state is `'current'`, or `'alert'` if step 4 is alert and no other current. Used in analytics only.

### 8.5 Loading / error semantics

- `useHomeState` loading → strip renders null until resolution (cheap; <100ms typical per `home_state_service` cache).
- `useScoreHistory` loading → step 1 renders `'future'` until resolution.
- `useLoopProgress` loading → step 2 renders `'future'` until resolution.
- Any of those errors → silent fallback to `'future'` for the unresolved step. The strip never renders an error string; failure is invisible (consistent with `<HomeStatusHero>` §8.5 + `<StateAwareWidgets>` empty-states pattern).

---

## 9. Telemetry

### 9.1 Four new events

| Event | Fires | Payload |
|-------|-------|---------|
| `loop_strip_rendered` | Once per mount via `useRef` after `stepStates` resolves with at least step 4 known. | `{persona: 'interview_prepper', plan, current_step: 1\|2\|3\|4, has_overdue: boolean, days_until_interview: number}` |
| `loop_strip_step_clicked` | Step 3 click only (other steps non-clickable). | `{step: 3, current_step, plan}` |
| `loop_strip_rescan_unlocked` | Once per session when step 3 transitions `'locked'` → `'current'`. Per-mount `useRef<boolean>` tracks prior-locked state; fires when prior=locked AND new=current. | `{plan, days_since_last_scan, percent_reviewed}` |
| `loop_strip_step_completed` | Once per step per session when a step transitions to `'done'`. Per-step `useRef<Set<LoopFrameStep>>` tracks fired-set. | `{step: 1\|2\|3, plan, days_in_step: number \| null}` |

`days_in_step` is null on first observation (no prior timestamp); future Phase 6 work could thread durations through if telemetry shows it useful. Step 4 is never `'done'` so no `loop_strip_step_completed` fire for it.

### 9.2 Existing events unchanged

- `loop_frame_rendered` (spec #64) — continues firing on Results.tsx mount with `surface: 'results'`. New `surface: 'appshell'` value is **available** in the union but `<LoopFrame>` will NOT fire `loop_frame_rendered` from the AppShell mount — the strip fires its own `loop_strip_rendered` event instead. To prevent double-counting, LoopProgressStrip uses LoopFrame's existing `surface` prop for layout but **suppresses** the `loop_frame_rendered` analytics fire when `surface === 'appshell'`. (Implementation note: gate the `useEffect` analytics fire on `surface !== 'appshell'`.) See §14 OQ-4 for the alternative.
- `home_status_hero_rendered` (spec #65) — unchanged.
- `home_state_evaluated` (spec #40) — unchanged.

### 9.3 Catalog updates

`.agent/skills/analytics.md` gains 4 new rows after `loop_frame_rendered` (line 76). The existing `loop_frame_rendered` row's note about "E-051 will widen `surface` to 'appshell'" is updated to reflect the §9.2 decision (suppress `loop_frame_rendered` when `surface==='appshell'`; the AppShell mount fires `loop_strip_rendered` instead).

---

## 10. Tests

### 10.1 Test envelope (FE)

| Surface | Test count target | Range |
|---------|-------------------|-------|
| `LoopProgressStrip` render gates (4 conditions) | 4 | 4-5 |
| Step-state derivation × 4 steps × resolved/unresolved | 8 | 7-10 |
| Click-through (step 3 only when current) | 2 | 2-3 |
| Analytics × 4 events × fire-once invariants | 4 | 4-5 |
| LoopFrame extension regression (existing 9 + 2 new for `stepStates` + `onStepClick`) | 2 net-new | 2-3 |
| AppShell mount integration (chromeless path + persona suppression) | 2 | 2-3 |
| **Total FE** | **~22** | **+18..+25** |

### 10.2 Test envelope (BE)

| Surface | Test count |
|---------|-----------|
| `learning_progress_service.compute_loop_progress` (4 cases: empty gaps, partial review, complete review, tracker-not-owned) | 4 |
| `GET /api/v1/learn/loop-progress` route (200 / 401 / 404 / 422) | 4 |
| **Total BE** | **+8** |

### 10.3 Test files

- New `tests/components/LoopProgressStrip.test.tsx` (~+18 FE tests)
- Extend `tests/components/LoopFrame.test.tsx` (+2 — `stepStates` override; `onStepClick` button-mode)
- Extend `tests/AppShell.test.tsx` (+2 — strip render gate × chromeless suppression)
- New `tests/test_learning_progress_service.py` (+4 BE)
- New `tests/test_loop_progress_route.py` (+4 BE)

### 10.4 Regression invariants

- `tests/components/LoopFrame.test.tsx` 9 existing tests stay green (backward-compatibility from §4.1).
- Results.tsx call site renders unchanged (no DOM diff in `tests/pages/Results.ordering.test.tsx` ordering invariant).
- `tests/AppShell.test.tsx` existing chromeless-suppression tests stay green; strip respects same paths.

---

## 11. Acceptance criteria

| AC | Surface | Trigger | Expected |
|----|---------|---------|----------|
| **AC-1** | `LoopProgressStrip` | persona=`interview_prepper`, `next_interview != null`, all data resolved, `showChrome=true` | Renders inside AppShell between TopNav and main; `loop_strip_rendered` fires once. |
| **AC-2** | `LoopProgressStrip` | persona=`career_climber` OR `team_lead` | Returns null. |
| **AC-3** | `LoopProgressStrip` | persona=`interview_prepper`, `next_interview = null` | Returns null. |
| **AC-4** | `LoopProgressStrip` | path in CHROMELESS_PATHS OR `/pricing` as guest | Returns null (gated by AppShell `showChrome`). |
| **AC-5** | Step 1 | `useScoreHistory` returns history with at least 1 entry | State='done', subline shows latest `overall_score%`. |
| **AC-6** | Step 2 | `useLoopProgress` returns `percent_reviewed < 50` AND step 1 is done | State='current', subline shows `"<reviewed>/<total>"`. |
| **AC-7** | Step 3 | step 2 done AND `days_since_last_scan >= 3` | State='current' (clickable). `loop_strip_rescan_unlocked` fires once. |
| **AC-8** | Step 3 click | state='current' | Navigates to `/prep/tracker?focus={tracker_id}&action=rescan`; `loop_strip_step_clicked` fires before navigation with `step=3`. |
| **AC-9** | Step 4 | `next_interview.date` < today | State='alert', subline `"Overdue"`. |
| **AC-10** | Step 4 | `days <= 7` | State='current', subline `"in Nd"`. |
| **AC-11** | LoopFrame backward-compat | Results.tsx render | No DOM diff vs pre-spec; `loop_frame_rendered` fires (analytics unchanged because surface='results'). |
| **AC-12** | LoopFrame extension | LoopFrame mounted with `surface='appshell'` | `loop_frame_rendered` does NOT fire from inside LoopFrame (suppressed per §9.2). |
| **AC-13** | BE `loop-progress` 200 | authed user's tracker, 10 gap cards, 4 reviewed | Returns `total_gap_cards=10, reviewed_gap_cards=4, percent_reviewed=40.0`. |
| **AC-14** | BE `loop-progress` 404 | authed user, tracker_id belongs to a different user | 404. |

---

## 12. Locked Decisions

*(EMPTY — placeholder for §12 amendment slice mirroring slice 6.0/6.4.5/6.5/6.6/6.7/6.14/6.15/spec-#64 precedent. The §12 amendment slice locks D-1..D-N from the §14 OQs after Dhamo disposition. Impl slice picks up post-amendment.)*

---

## 13. Out of scope (forward work)

- **Career-Climber variant** — E-053 owns the CC moat-device equivalent (habit ribbon + skill-radar trend).
- **Team Lead variant** — `null` return; future when the persona graduates from coming-soon.
- **Animations / transitions** — static state changes only this slice.
- **Click-through on steps 1, 2, 4** — only step 3 interactive. Future could add step 4 → `/prep/tracker?focus={tracker_id}&action=set-date` (capture path) but not this slice.
- **Strip dismissal / "hide for this session"** — no dismissal affordance.
- **A/B test on strip placement** (above TopNav vs below) — telemetry-driven, post-ship.
- **Caching of `loop-progress` endpoint** — no Redis cache this slice.
- **Step 4 'done' state after interview-completed mark** — capture-path is E-052 / E-053 territory.
- **Phase 6 read consolidation** (e.g., merge `loop-progress` into `home_state_service`) — deferred.
- **Multi-interview support** (user with 2+ upcoming interviews) — strip shows the **nearest** interview only, per `homeState.context.next_interview` selection rule (spec #57 §2.2).
- **`loop_strip_step_completed` step duration tracking** (`days_in_step`) — null on first observation; future enhancement could thread per-step timestamps through.

---

## 14. Open questions

| # | Question | Author hint / default |
|---|----------|------------------------|
| OQ-1 | How does the strip know step 3 has been "completed" (re-scan happened post-unlock) vs "still current"? Proposal: compare `history[history.length - 1].scanned_at` with the timestamp of the step-3 unlock event. Alternative: count score-history rows; if `>= 2` AND `percent_reviewed >= 50`, step 3 is done. | Default = score-history-row-count heuristic (≥2 rows AND step 2 done = step 3 done). Cleaner; doesn't require persistence of unlock-time. |
| OQ-2 | Mobile strip layout: 4 steps stacked vertically (~48px each = ~192px viewport take) vs single-row icon-only with truncated label (~56px take)? | Default = icon-only single-row at <md, full-card stacked at md+. 192px on mobile is too aggressive; 56px is acceptable. |
| OQ-3 | Gap-card mapping: skill-name → category lookup OR skill-name → card-tag lookup OR both? | Default = category lookup matches the live `MissingSkillsPanel` precedent (spec #22); card-tag lookup is forward work. Implementer should verify the live mapping at impl Step 1. |
| OQ-4 | Suppress `loop_frame_rendered` when `surface='appshell'` (§9.2) vs let both events fire vs rename `loop_frame_rendered` to `loop_strip_rendered` only on appshell surface? | Default = suppress per §9.2. Two events with overlapping semantics dilutes funnels. |
| OQ-5 | Step 3 unlock predicate constants — `MIN_DAYS_SINCE_SCAN=3` and `MIN_PERCENT_REVIEWED=50` — env-tunable (per `d19103c` precedent) or hardcoded constants? | Default = hardcoded for v1; env-tunable post-launch if telemetry shows they're wrong. |
| OQ-6 | Step 4 "alert" styling — does `border-border-danger` token exist? If not, add to design-tokens.ts vs use existing `border-danger`. | Verify at impl Step 1; add token only if mostly used elsewhere. |
| OQ-7 | If the user's `next_interview` flips (different tracker becomes nearest), does the strip refire `loop_strip_rendered` for the new tracker? Or is once-per-mount enough? | Default = once per mount, `useRef` keyed on `tracker_id` so navigation away/back DOES refire (mount-level). |
| OQ-8 | Should `LoopProgressStrip` mount inside `<TopNav>` (so it inherits z-index / sticky behavior) or as a sibling below it? | Default = sibling below (per §4.2). TopNav is ARIA-labelled `nav`; embedding a non-nav strip inside breaks semantics. |
| OQ-9 | When step 1 is `'future'` (no scan exists for `next_interview.tracker_id`) but `homeState.context.last_scan_date` is non-null (a scan exists for a DIFFERENT tracker), should the strip render at all? | Default = render with step 1 as 'future' anyway. The strip is per-interview; a scan on another tracker doesn't help this interview. The user is funnel-pushed back to `/prep/analyze` via the future state. |
| OQ-10 | Is `loop_strip_rendered`'s `current_step` property always the lowest non-future index, or the lowest non-locked-non-future, or the highest done+1? | Default = lowest index whose state is `'current'`, falling back to `'alert'` if step 4 alert and no other current, falling back to step 4 index `4` if everything else is `'done'`. Locked in §8.4 `deriveCurrentStep`. |
| OQ-11 | Does `LoopFrame.compact` warrant a separate prop or could it be implied by `surface === 'appshell'`? | Default = explicit `compact` prop. Keeps surface a pure analytics-marker; layout decisions stay layout-driven. |
| OQ-12 | `loop_strip_step_completed` per-step `useRef<Set>` — how does it interact with React Strict Mode's double-invoked effects in dev? | Default = same pattern as `home_status_hero_rendered`'s `useRef<boolean>` — per-step useRef boolean OR a single `useRef<Set<step>>`. Idempotent under double-invoke. |
| OQ-13 | New BE endpoint URL: `GET /api/v1/learn/loop-progress` (`/learn` namespace) or `GET /api/v1/tracker/{tracker_id}/loop-progress` (RESTful nesting)? | Default = `/learn/loop-progress?tracker_id={id}` flat with query param; matches `/api/v1/learn/dashboard` precedent (spec #09 phase-6 dashboard). |
| OQ-14 | If `useLoopProgress` errors (BE 500), step 2 falls back to `'future'`. Does that prevent step 3 from ever unlocking? | Default = yes, by design — without progress data we can't safely unlock step 3. User can refresh to retry. Documented as known limitation. |

---

## 15. Test plan summary

Test files (see §10.3):
- `tests/components/LoopProgressStrip.test.tsx` — new (~+18 FE)
- `tests/components/LoopFrame.test.tsx` — extend (+2 FE)
- `tests/AppShell.test.tsx` — extend (+2 FE)
- `tests/test_learning_progress_service.py` — new (+4 BE)
- `tests/test_loop_progress_route.py` — new (+4 BE)

**Test count envelope:** **+22 FE (floor +18, ceiling +25)** + **+8 BE (floor +6, ceiling +10)**.

**Regression set:** existing `LoopFrame.test.tsx` 9 tests stay green; `tests/pages/Results.ordering.test.tsx` ordering invariant unchanged; `tests/AppShell.test.tsx` chromeless-suppression baseline preserved.

---

*End of spec #66. Implementation begins after §12 amendment slice locks D-1..D-N from the §14 OQs (mirrors slice 6.0/6.4.5/6.5/6.6/6.7/6.14/6.15/spec-#64 precedent).*
