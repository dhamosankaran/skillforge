# P5-S61 — HomeDashboard Composition Rules + Free-tier Study Surface

**Status:** Shipped (spec + impl) — closes B-051. Impl `ecef895` on 2026-04-26.
**Owner:** Dhamo
**Created:** 2026-04-26
**Phase:** 5D (persona-aware surface)
**Depends on:** P5-S18 (HomeDashboard + widget catalog, spec #35, shipped `5e1f56c`); P5-S18b (state-aware variants, spec #40, shipped `55ac7bd`); spec #44 (widget empty-state contract)
**Implementation slice:** P5-S61-impl (BACKLOG **B-051** filed by this slice)
**Audit anchor:** `docs/audit/2026-04-E-048-home-dashboard.md` (E-048 audit, 2026-04-26, commit `47b21df`)
**BACKLOG:** closes E-048 (impl half) on impl-slice merge; E-048 audit half stays ✅ (audit shipped `47b21df`).

## 1. Context

### 1.1 Predecessor state

Spec #35 (P5-S18) shipped persona-aware mode containers: `InterviewPrepperMode` / `CareerClimberMode` / `TeamLeadMode`, each a fixed widget grid. Spec #40 (P5-S18b) added a state-aware priority slot above the persona grid, rendering a single state-conditional widget (`MissionActive` / `MissionOverdue` / `StreakAtRisk` / `ResumeStale` / `InactiveReturner` / `FirstSessionDone`).

The two layers were specced independently. They render in parallel without coordination. Spec #40 §7 says "the static S18 persona grid stands alone in those cases" referring only to *empty `states[]`* — not the case where state slot and static grid both render content drawn from the same data domain.

### 1.2 E-048 audit findings (verbatim summary)

The 2026-04-26 audit (`docs/audit/2026-04-E-048-home-dashboard.md`) classified 9 cells of the `{persona × plan × has_mission × has_recent_scan × streak_state}` matrix:

- 4 🟡 contradictory: #1 Mission-in-flight + Countdown duplicate-render, #2 InterviewTarget empty alongside active Mission, #3 LastScan buried below redundant widgets, #6 `mission_active` suppressing `resume_stale` in priority order
- 3 🔴 missing: #4 no on-home study-the-gaps CTA, #5 no upgrade-to-study CTA, #7 no plan-branching surface in `_renderWidget`
- 2 ✅ correct: #8 CareerClimber composition, #9 TeamLead composition

Findings #6 and #7 were net-new beyond E-048's reported symptom; both fold into this spec's scope per the audit's PUSHBACK threshold check.

### 1.3 Reported user symptom (E-048 anchor)

Free-user-post-scan view of `/home`:

- `Mission in flight` widget says `"3 days left in your mission"` with `Open mission` CTA. `Countdown` widget says `"4 DAYS LEFT, Interview, Day 1 of 4, 0% complete"` with `View mission` CTA. Same mission framed two different ways, two CTAs pointing to the same `/learn/mission`.
- `Interview Target: No interview company set yet` empty state alongside an ACTIVE Mission widget.
- `Last Scan: JPMorgan Chase & Co. ATS score: 71%` rendered correctly but at DOM position 5 in the IP grid — buried below redundant widgets.
- For a free user who has burned their scan and has no Pro subscription, no widget foregrounds (a) "Study the gaps from your last scan" or (b) "Upgrade to unlock the study engine".

## 2. Locked Decisions

| ID | Decision | Source |
|----|----------|--------|
| **LD-1** | Free-user-post-scan **primary CTA** is **"Study the gaps from your last scan"** — pushes user into the Forge study engine via `/learn?source=last_scan` (free path, activates core scan→study→re-scan loop). **Upgrade CTA is SECONDARY**, visually subordinate (smaller, lower in hierarchy, not the primary action). Premature conversion pressure on a user who hasn't experienced Forge yet is the wrong moment; let the daily card budget be the natural upgrade trigger downstream. | Chat 2026-04-26 |
| **LD-2** | **Composition suppression rule**: when state-slot widget X and static-grid widget Y render the same data domain, X suppresses Y. The state slot is canonical; the static grid yields. Specifically (per audit #1): the state-aware Mission slot suppresses the static `CountdownWidget` Mode 2 mission CTA when both would render for the same active mission. The suppression matrix in §3 enumerates the full rule set; audit findings #2 and #6 are also suppression cases. | Audit §7 |
| **LD-3** | **InterviewTarget empty-state coexistence**: when a Mission is active, persona target data DOES flow into `InterviewTargetWidget`. The widget reads from the same persona/mission context the Mission widget reads from, not its own independent empty-state branch. Specifically: when state slot renders `MissionActiveWidget`, `InterviewTargetWidget` is suppressed (mission framing already covers the date; company gap is moot mid-mission). | Audit §6 + LD-2 corollary |
| **LD-4** | **Plan-aware state-slot extension**: state-slot logic in `_renderWidget` consumes `context.plan`. The state-aware layer currently has no plan branching (audit #7); this spec defines plan-conditional rules — primarily for the free-user-post-scan surface (LD-1) — and documents the plan × state matrix for other combinations in §6. | Audit §7 finding #7 |
| **LD-5** | Spec filename `docs/specs/phase-5/61-home-dashboard-composition-rules.md`. No collision with on-disk specs (verified at SOP-5). | LD-5 prompt |
| **LD-6** | Spec follows the structure used in spec #40 (the predecessor this extends): Status header, §1 Context, §2 Locked Decisions, §3+ implementation sections, AC table, Out of scope, Open questions. No new structural conventions. | LD-6 prompt |
| **LD-7** | All 9 audit findings (4 🟡 + 3 🔴 + 2 ✅) are addressed by exactly one section of this spec. §7 coverage table is mandatory and authoritative. | LD-7 prompt |
| **LD-8** | **Out of scope**: implementation, BE work (`home_state_service.py` priority-order changes, if needed, ship in P5-S61-impl), copy finalization beyond LD-1's primary CTA wording, A/B test infrastructure for upgrade-CTA placement. | LD-8 prompt |
| **LD-9** | AC table contains 8–12 acceptance criteria. Each AC must be testable from a Vitest render assertion (FE) or service-layer assertion (BE). | LD-9 prompt |
| **LD-10** | New free-tier surface widget is named `StudyGapsPromptWidget` (file: `src/components/home/widgets/StudyGapsPromptWidget.tsx`). Naming convention matches existing `home/widgets/*Widget.tsx` files. | Spec author judgment, follows on-disk convention |
| **LD-11** | Routing target for LD-1 primary CTA: `/learn?source=last_scan`. The base path `/learn` is the live `StudyDashboard` route (`App.tsx:86`); the `?source=last_scan` query param is added for telemetry attribution and a future "you came from your last scan" hero hint on `StudyDashboard`. The query param is **read-optional**: `StudyDashboard` does not need to consume it for the spec to ship; consumption is its own follow-on. | SOP-5 route verification |

## 3. Composition suppression rules

Covers audit findings **#1, #6, #8, #9**.

### 3.1 The suppression matrix

State slot wins. Static-grid widgets that would render content drawn from the same data domain are suppressed. The matrix:

| State slot rendering | Static-grid widget(s) suppressed | Rationale | Audit finding |
|----------------------|----------------------------------|-----------|---------------|
| `MissionActiveWidget` | `CountdownWidget` Mode 2 (the post-date countdown + mission CTA branch) — **only when the active mission's `target_date` matches `user.interview_target_date`**. If the active mission is for a different date, no suppression. | State slot already shows "X days left in your mission" + `Open mission` CTA pointing to `/learn/mission`. Static Countdown Mode 2 shows the same days-remaining + same `View mission` CTA pointing to the same URL. Two surfaces, one mission, one CTA target. | #1 |
| `MissionActiveWidget` | `InterviewTargetWidget` | Mission framing already covers the date. Company-gap empty state ("No interview company set yet.") is moot mid-mission and adds noise. See §5 for the full rule. | #2 (cross-ref to §5) |
| `MissionOverdueWidget` | `CountdownWidget` Mode 2 mission CTA — **if** the overdue mission target matches `user.interview_target_date`. Otherwise no suppression. | Same logic as `MissionActiveWidget` row — overdue framing supersedes Countdown's CTA. | extends #1 |
| `ResumeStaleWidget` | (none — no static-grid widget covers stale-scan recency) | No overlap. | n/a |
| `StreakAtRiskWidget` | (none — `StreakWidget` shows current streak, `StreakAtRiskWidget` shows the at-risk warning; complementary) | No overlap. | n/a |
| `InactiveReturnerWidget` | (none) | No overlap. | n/a |
| `FirstSessionDoneWidget` | (none) | No overlap. | n/a |

### 3.2 BE state-priority amendment (audit finding #6)

Today (`hirelens-backend/app/services/home_state_service.py:38-46`):

```
STATE_PRIORITY = (
    "mission_overdue",
    "streak_at_risk",
    "mission_active",       ← suppresses `resume_stale` for users with both
    "resume_stale",
    "inactive_returner",
    "first_session_done",
)
```

For a Pro user with an active mission AND a stale (≥21d) scan, only mission framing fires. The "your scan is stale" nudge is suppressed. For free users this is moot (re-scan blocked by spec #56 lifetime cap), but Pro users lose a useful prompt.

**Decision:** keep the priority order unchanged (mission urgency > resume staleness is the right product call), BUT the BE evaluator returns **all** active states in `states[]` (already does — verified). The FE renders only `states[0]` today (`StateAwareWidgets.tsx:48`). The impl slice may surface `resume_stale` as a *secondary* affordance inside `MissionActiveWidget` (e.g., a small "your scan is 30d old — re-scan after this mission" footer link) **for Pro users only**. Free users don't get this affordance. This is a §6 plan-aware behavior.

### 3.3 Preserved invariants (audit findings #8, #9)

- `CareerClimberMode` composition is preserved verbatim. No suppression rules apply (career_climber persona has no `interview_target_date`; Mission state slot still fires if user manually started a Mission, but no Countdown widget exists in CareerClimber grid to suppress).
- `TeamLeadMode` composition is preserved verbatim. The `[S35-flag]` waitlist gap on `TeamComingSoonWidget` is unchanged (tracked separately in SESSION-STATE Deferred Hygiene; out of scope for this spec).
- Suppression applies **only** to `InterviewPrepperMode`. The other two modes' grids render unchanged.

### 3.4 Implementation hint (non-binding for spec; for impl slice planning)

Suppression is observable via prop-drilling or context. Two viable shapes:

(a) Pass the resolved top-state from `StateAwareWidgets` down into `InterviewPrepperMode` via a new prop or shared context, and gate the Countdown / InterviewTarget renders on it.

(b) Have `StateAwareWidgets` write the active state into a small singleton context (`HomeCompositionContext`); each suppressible widget reads from it.

Impl slice picks (a) or (b) based on test ergonomics. Spec is neutral.

## 4. Free-tier study/upgrade widget surface

Covers audit findings **#3, #4, #5**.

### 4.1 New widget: `StudyGapsPromptWidget`

**File:** `src/components/home/widgets/StudyGapsPromptWidget.tsx`
**Renders when:** `plan === 'free' && !isAdmin && has_recent_scan && !has_active_mission`

The four predicates resolve as follows:

| Predicate | Source |
|-----------|--------|
| `plan === 'free'` | `useUsage()` `usage.plan` |
| `!isAdmin` | `useUsage()` `usage.isAdmin` |
| `has_recent_scan` | `fetchUserApplications()` returns ≥1 application with non-null `scan_id` (mirrors `LastScanWidget.tsx:17-46`) |
| `!has_active_mission` | `fetchActiveMission()` returns no mission with `status === 'active'` |

The widget is rendered above the persona-mode grid (above `InterviewPrepperMode`/`CareerClimberMode`/`TeamLeadMode`) and **below** the state-aware slot. When it renders, it suppresses `LastScanWidget` from the static grid (LastScan's content is rolled into this widget's body — closes audit finding #3 by promoting buried content rather than just unburying it).

### 4.2 Widget body (spec-locked)

```
[StudyGapsPromptWidget]
  Title: "Pick up where you left off"
  Body:
    "Your last scan against {company} found {N} skill gaps.
     Study them in 5 minutes a day."
  Primary CTA (button, prominent):
    "Study the gaps from your last scan" → /learn?source=last_scan
  Secondary CTA (link, de-emphasized, below primary, smaller font):
    "Or upgrade to unlock unlimited study + Pro features" → opens PaywallModal trigger="skill_gap_study"

> _Amended in B-051 impl: original `'study_engine_unlock'` did not exist in the on-disk `PaywallTrigger` union (`hirelens-frontend/src/components/PaywallModal.tsx:21-29`); substituted existing `'skill_gap_study'` trigger which has semantically closer headline ("Study skill gaps with flashcards") + subline ("Pro unlocks the full flashcard library so you can study every skill gap detected in your resume scan") copy. No PaywallTrigger union widening, no new HEADLINES/SUBLINES entries. See B-051 impl report._
```

**Copy bounds (per LD-1):** primary CTA wording is locked. Body copy and headline are tunable by the impl slice within these constraints:
- Headline must reference the user's last action (the scan).
- Body must surface the gap count if available; fallback "your last scan" wording if gap count unavailable.
- Secondary CTA must be a `<a>` or text-button, not a primary `<button>`. No same-size visual weight as primary.
- Both CTAs must use design tokens per R12.

### 4.3 Routing target (LD-11)

`/learn?source=last_scan` — base path `/learn` is the live `StudyDashboard` route (verified `App.tsx:86`). The `?source=last_scan` query param is for telemetry attribution. `StudyDashboard` consumption of the param is OPTIONAL for this spec (a future hero-banner "you came from your last scan" enhancement is its own slice).

### 4.4 Free-user-without-scan, free-user-with-mission, Pro/Enterprise

For predicate-misses, the widget does **not** render. Specifically:

- `plan === 'free'` AND no recent scan: widget hidden. User sees the existing IP/CC/TL grid unchanged. (No regression.)
- `plan === 'free'` AND active mission: widget hidden — the state-aware Mission slot is the next-action surface. (No competing CTA.)
- `plan === 'pro'` or `'enterprise'` or `isAdmin`: widget hidden. Pro users have unlimited study; the prompt is irrelevant to them.

### 4.5 Persona × widget interaction

The widget renders for **all three personas** (interview_prepper, career_climber, team_lead) when the four predicates are satisfied. The scan→study loop is persona-orthogonal — every persona benefits from a study CTA after scanning.

## 5. InterviewTarget empty-state coexistence rule

Covers audit finding **#2**.

### 5.1 Current behavior

`InterviewTargetWidget` (`src/components/home/widgets/InterviewTargetWidget.tsx:30-36`) renders three empty-state copies based on `(company, date)` pairs (B-017 fix):

- `(!company && !date)` → `'No interview target set yet.'`
- `(!company && date)` → `'No interview company set yet.'`
- `(company && !date)` → `'Set your interview date in the Countdown widget below.'`

The widget is rendered unconditionally inside `InterviewPrepperMode`. When `(!company && date)` AND a Mission is active for that date, the user sees an honest empty-state ("No interview company set yet.") next to a "Mission in flight" widget for the same date — confusing composition.

### 5.2 Specified behavior

When the state-aware slot renders `MissionActiveWidget` OR `MissionOverdueWidget`, **`InterviewTargetWidget` is suppressed entirely** in `InterviewPrepperMode`. Mission framing already provides the date context; the company gap is moot mid-mission.

When no Mission state is active in the state slot, `InterviewTargetWidget` renders per its existing B-017 three-case empty-state logic (unchanged).

### 5.3 Why suppress vs adapt copy

Two alternatives were considered:

(a) **Suppress entirely** when Mission slot fires (chosen).
(b) **Adapt the empty copy** to "Add company name to personalize cover-letter" (or similar) when Mission active.

(a) is chosen because: simpler invariant (one rule, no per-case copy decisions); composition matrix in §3 already enumerates "X suppresses Y" pairs cleanly; (b) introduces a new copy decision per state pair which doesn't scale.

The "set your company" CTA path lives at the existing `PersonaPicker` (`/onboarding/persona?return_to=/home`) — out of scope for this spec; user reaches it via Profile → Edit persona.

## 6. Plan-aware state-slot extension

Covers audit finding **#7**.

### 6.1 Current behavior

`StateAwareWidgets._renderWidget` (`src/components/home/StateAwareWidgets.tsx:15-36`) takes `state` (HomeStateName), `persona`, `context` (`HomeStateContext`). The `context` already includes `plan: 'free' | 'pro' | 'enterprise'` (spec #40 §5 line 100, verified `src/types/homeState.ts:21`). **No widget consumes `context.plan` today.**

### 6.2 Specified behavior

The impl slice extends `_renderWidget` (or per-widget logic) to consume `context.plan` for the following plan × state combinations:

| State | `context.plan` | Behavior |
|-------|----------------|----------|
| `mission_active` | `'free'` | Render `MissionActiveWidget` unchanged (free users on missions are a valid state — `daily_review` paywall fires server-side per spec #50 if they hit the wall). |
| `mission_active` | `'pro'` / `'enterprise'` | Render `MissionActiveWidget` PLUS a small "your scan is X days old — re-scan after this mission" footer affordance, IF `last_scan_date > 21d ago`. (Surfaces `resume_stale` as a secondary signal; closes audit #6 for Pro users.) |
| `resume_stale` | `'free'` | Render `ResumeStaleWidget` unchanged — but the `Re-scan` CTA must route to PaywallModal (`trigger='scan_limit'`) instead of `/prep/analyze` since spec #56 caps free at 1 lifetime scan. (Avoids the dead-end the audit flagged at §4 row #6 footnote.) |
| `resume_stale` | `'pro'` / `'enterprise'` | Render `ResumeStaleWidget` unchanged with `Re-scan` CTA → `/prep/analyze`. |
| any other state | any plan | Unchanged. |

### 6.3 The `StudyGapsPromptWidget` from §4 is NOT a state-slot widget

`StudyGapsPromptWidget` is a static composition-layer widget that renders above the persona grid (and below the state slot). It is NOT registered in the state catalog (`STATE_PRIORITY` in `home_state_service.py`). Rationale:

- The widget's predicates (free + scan-but-no-mission) are easily computed FE-side from `useUsage()` + `fetchUserApplications()` + `fetchActiveMission()` — no BE change required.
- Adding a new state name to the BE evaluator would require schema changes, a new priority slot, and BE testing — disproportionate to the surface's scope.
- The state-slot is reserved for *time-sensitive urgency* signals (overdue, at-risk, returning); the study-prompt is a *steady-state ambient* CTA. Different purpose, different layer.

The plan-aware §6 changes (the table above) are the only state-slot extensions in this spec.

## 7. Coverage table — audit-finding → spec-section mapping

Mandatory per LD-7. Each audit finding maps to **exactly one** spec section.

| Audit finding | Classification | Audit description | Spec section | Notes |
|---------------|----------------|-------------------|--------------|-------|
| **#1** | 🟡 contradictory | Mission-in-flight + Countdown duplicate-render same active mission | **§3** | Suppression rule row 1 in §3.1 matrix |
| **#2** | 🟡 contradictory | InterviewTarget empty-state alongside active Mission | **§5** | Suppression entire (LD-3); cross-ref in §3.1 matrix row 2 |
| **#3** | 🟡 contradictory | LastScan buried at DOM position 5 below redundant widgets | **§4** | Closed by promoting scan-content into `StudyGapsPromptWidget` body (4.2); LastScan suppressed when prompt widget renders (4.1) |
| **#4** | 🔴 missing | No on-home study-the-gaps CTA for free-user-post-scan | **§4** | New `StudyGapsPromptWidget` primary CTA (LD-1, §4.2) |
| **#5** | 🔴 missing | No upgrade-to-study CTA for free-user-post-scan | **§4** | Secondary CTA in `StudyGapsPromptWidget` (LD-1, §4.2) — visually subordinate |
| **#6** | 🟡 contradictory (net-new) | `mission_active` priority suppresses `resume_stale` | **§3** | Priority order preserved (§3.2); secondary affordance for Pro users surfaced via §6 plan-aware extension (Pro × mission_active row) |
| **#7** | 🔴 missing (net-new) | No plan-branching surface in state-aware layer | **§6** | Plan × state matrix in §6.2 |
| **#8** | ✅ correct | CareerClimberMode composition correct | **§3** | §3.3 preserved-invariants clause |
| **#9** | ✅ correct | TeamLeadMode composition correct | **§3** | §3.3 preserved-invariants clause |

**Verification:** 9 findings → 4 distinct sections (§3 ×4, §4 ×3, §5 ×1, §6 ×1). No double-coverage. No drops.

## 8. Acceptance Criteria

Per LD-9. Each AC is testable via Vitest (FE) or pytest (BE).

| AC | Surface | Trigger | Expected behavior | Test harness |
|----|---------|---------|-------------------|--------------|
| **AC-1** | `HomeDashboard` | persona=interview_prepper, mission active, target_date matches `user.interview_target_date`, state slot renders `MissionActiveWidget` | `CountdownWidget` does NOT render in `InterviewPrepperMode` grid | Vitest render + `queryByTestId('countdown')` returns `null` |
| **AC-2** | `HomeDashboard` | persona=interview_prepper, mission active, target_date matches, state slot renders `MissionActiveWidget` | `InterviewTargetWidget` does NOT render in `InterviewPrepperMode` grid | Vitest render + `queryByTestId('interview-target')` returns `null` |
| **AC-3** | `HomeDashboard` | persona=interview_prepper, no mission active OR mission target_date ≠ `user.interview_target_date` | Both `CountdownWidget` and `InterviewTargetWidget` render per pre-spec behavior | Vitest render + both `getByTestId` pass |
| **AC-4** | `StudyGapsPromptWidget` | plan=free, isAdmin=false, recent scan exists, no active mission, any persona | Widget renders. Primary CTA text = "Study the gaps from your last scan". Primary CTA `href` = `/learn?source=last_scan`. Secondary CTA is a link or de-emphasized button (assertable via DOM tag or a `data-emphasis="secondary"` marker), copy contains "upgrade". | Vitest render + `getByText` + `getByRole('link', { name: /Study the gaps/ })` `href` assertion + secondary-CTA tag assertion |
| **AC-5** | `StudyGapsPromptWidget` | plan=free AND active mission (any persona, scan exists) | Widget does NOT render | Vitest render + `queryByTestId('study-gaps-prompt')` returns `null` |
| **AC-6** | `StudyGapsPromptWidget` | plan=pro OR plan=enterprise OR isAdmin (any other predicate state) | Widget does NOT render | Vitest render + `queryByTestId('study-gaps-prompt')` returns `null` |
| **AC-7** | `StudyGapsPromptWidget` | plan=free, no recent scan (any persona) | Widget does NOT render | Vitest render + `queryByTestId('study-gaps-prompt')` returns `null` |
| **AC-8** | `LastScanWidget` | `StudyGapsPromptWidget` renders (i.e., AC-4 conditions met) | `LastScanWidget` does NOT render in the static grid (its content is rolled into the prompt widget) | Vitest render + `queryByTestId('last-scan')` returns `null` |
| **AC-9** | `_renderWidget` (state-slot) | state=`mission_active`, `context.plan='pro'`, `context.last_scan_date > 21d ago` | `MissionActiveWidget` renders WITH the secondary "your scan is X days old — re-scan after this mission" footer affordance | Vitest render + `getByText(/scan is.*days old/)` |
| **AC-10** | `_renderWidget` (state-slot) | state=`resume_stale`, `context.plan='free'` | `ResumeStaleWidget` renders; `Re-scan` CTA opens `PaywallModal` (`trigger='scan_limit'`) instead of navigating to `/prep/analyze` | Vitest render + click `Re-scan` + `getByRole('dialog')` shows paywall copy |
| **AC-11** | `home_dashboard_viewed` PostHog event | Any HomeDashboard mount where `StudyGapsPromptWidget` would render per AC-4 predicates | Existing `home_dashboard_viewed` event fires once on mount (unchanged behavior — guard against regression). NEW event `home_study_gaps_prompt_shown {plan, persona}` fires once on `StudyGapsPromptWidget` mount via `useRef` idempotency guard. | Vitest with `vi.spyOn(posthog, 'capture')` — assert both events fire exactly once |
| **AC-12** | `home_study_gaps_clicked` PostHog event | Click primary CTA on `StudyGapsPromptWidget` | NEW event `home_study_gaps_clicked {plan, persona, cta: 'primary'}` fires before navigation. Secondary CTA fires `home_study_gaps_clicked {plan, persona, cta: 'secondary_upgrade'}` before opening PaywallModal. | Vitest click + spy assertion |

## 9. Out of scope

Per LD-8, plus what surfaced during spec drafting:

- Implementation. Lands in P5-S61-impl (BACKLOG B-051, filed by this slice).
- BE changes to `home_state_service.py` priority order — kept unchanged per §3.2; only FE composition rules change.
- Copy finalization beyond the LD-1 primary CTA and AC-4 wording bounds. Body copy and secondary-CTA copy land in impl slice within §4.2 constraints.
- A/B test infrastructure for upgrade-CTA placement / wording. The LD-1 secondary-CTA shape is locked here; A/B comes later if data warrants.
- `StudyDashboard` consumption of the `?source=last_scan` query param (LD-11). Spec ships without it; param is for telemetry attribution and a future hero-banner enhancement.
- The `[S35-flag]` `TeamComingSoonWidget` waitlist gap (tracked separately in SESSION-STATE Deferred Hygiene).
- The `[5.17-follow]` tracker `jd_hash` dedupe gap (orthogonal).
- A net-new state name in the BE state catalog (`STATE_PRIORITY`). The §6 plan-aware extension consumes existing `context.plan`; no new state.
- The first-visit guided-tour deferred from spec #21 (`[P5-S21b-follow]`) — orthogonal.

## 10. Open questions

| # | Question | Why it matters | Default if unanswered |
|---|----------|----------------|------------------------|
| OQ-1 | When `StudyGapsPromptWidget` renders, should it render **above** or **below** the state-aware slot? §4.1 says "above the persona-mode grid; below the state-aware slot" — confirm this is the right hierarchy. | Affects mobile DOM order; affects which widget is the user's top-of-screen attention. | Below state-slot, above persona grid (per §4.1). |
| OQ-2 | If a user has `plan=free`, recent scan, no active mission, AND `interview_target_date` set (interview_prepper persona pre-mission), does `StudyGapsPromptWidget` still render? Per §4.1 yes; but it composes oddly with `CountdownWidget` Mode 2 (countdown progress + study prompt). | Composition coherence for the IP user who scanned but hasn't started a Mission. | Render both; they're complementary (countdown = urgency, study = action). Confirm with Dhamo. |
| OQ-3 | The §6 Pro × mission_active footer affordance ("your scan is X days old — re-scan after this mission") — should it suppress the `resume_stale` state slot from firing later, or are they independent surfaces? | If both fire, user sees the same nudge twice across mounts. | Independent. Footer is a within-mount affordance; state slot fires post-mission. Confirm. |
| OQ-4 | LD-11 `?source=last_scan` query param — should `StudyDashboard` consume it in this slice (small hero hint) or defer to a follow-on? | Spec author leaned defer; leaves room for clean impl slice scope. | Defer to follow-on. |
| OQ-5 | The `home_study_gaps_clicked` `cta` enum — is `'secondary_upgrade'` the right enum value, or should it be `'upgrade'`? | Telemetry naming convention. | `secondary_upgrade` (preserves the visual-hierarchy intent in the property name). |

## 11. Telemetry

Two NEW PostHog events (per LD-9 / AC-11 / AC-12). Both follow the existing `home_*` convention catalogued in `.agent/skills/analytics.md`.

| Event | Source | Properties | Fires |
|-------|--------|------------|-------|
| `home_study_gaps_prompt_shown` | `src/components/home/widgets/StudyGapsPromptWidget.tsx` | `{plan: 'free', persona: 'interview_prepper'\|'career_climber'\|'team_lead'}` | Once per mount via `useRef` idempotency guard (matches `home_dashboard_viewed` / `paywall_hit` convention) |
| `home_study_gaps_clicked` | `src/components/home/widgets/StudyGapsPromptWidget.tsx` | `{plan: 'free', persona, cta: 'primary' \| 'secondary_upgrade'}` | On primary CTA click before navigation; on secondary CTA click before opening PaywallModal |

Existing events touched by this spec:

| Event | Source | Change |
|-------|--------|--------|
| `home_dashboard_viewed` | `src/pages/HomeDashboard.tsx` | Unchanged. Guard against regression in AC-11. |
| `home_state_widget_clicked` | state-slot widgets | Unchanged. (`MissionActiveWidget` retains existing `{state, cta}` props; the §6 Pro footer affordance, if it links to a route, fires its own variant per impl judgment.) |

The impl slice updates `.agent/skills/analytics.md` to catalogue the two new events.

---

*End of spec #61. Implementation slice to be authored as P5-S61-impl, closes B-051 + E-048 (impl half) on merge per CLAUDE.md R15.*
