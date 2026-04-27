---
slice: P5-S61 (spec) + P5-S61-impl (implementation, separate slice)
base_sha: 56afd99
drafted: 2026-04-25
backlog: E-047, B-045 (impl)
locked_decisions: LD-1..LD-7 (in-spec, §3)
depends_on: spec #42 (paywall dismissal — shipped `91fa915`), spec #55 (B-030 sibling — shipped `5c20d53`), spec #56 (B-031 BE quota — shipped `2080577`), spec #58 (UsageContext extension precedent — shipped `4922333`)
unblocks: P5-S61-impl (B-045)
---

# SPEC #60 — `/prep/analyze` Pre-Flight Gate for Free-Tier Scan Exhaustion

**Status:** Shipped (spec + impl) — closes B-045. Impl `3c962d8` on 2026-04-25.
**Owner:** Dhamo
**Created:** 2026-04-25
**Phase:** 5
**Closes:** spec-authoring half of E-047. Implementation half is P5-S61-impl (B-045).

## §1 Context & Motivation

BACKLOG E-047 (filed 2026-04-25 from chat UX audit, P1 🔴):

> Free user post-scan-limit lands on `/prep/analyze` with no working upgrade path. Banner reads `"1/1 free scans used — Upgrade for more"`, but `"Upgrade for more"` is plain text — no `href`, no CTA. Upload form + `Analyze Resume` button remain enabled; user can fill the form and only discover they're walled on submit. No inline nudge to `/pricing`. No "scan limit reached" state.

A free user who has burned their one lifetime scan (per spec #56 / B-031) and revisits `/prep/analyze` today sees a fully-open form: dropzone accepts uploads, JD textarea accepts paste, the `Analyze Resume` button is enabled. The "1/1 free scans used — Upgrade for more" chip renders, but `"— Upgrade for more"` is a plain `<span>` (Analyze.tsx:122-126) — no `href`, no button, no click handler. The user fills the form, clicks Analyze, and only then encounters the gate via `useAnalysis.runAnalysis()`'s pre-flight `canScan` check + the BE 402 fallback. The wasted-fill path is the bug.

This is the page-load equivalent of the wasted-click bug fixed for `/prep/interview` in P5-S60 / spec #49 §3.4 (commit `56afd99`). Same fix shape: surface the existing usage signal pre-flight; replace the form with a wall when at cap; preserve the modal escape hatch unchanged.

## §2 Goals & Non-Goals

### Goals
- Pre-flight render a wall card in place of the upload form when a free user is at the lifetime scan cap (`canScan === false && plan === 'free' && !isAdmin`). The dropzone, JD textarea, and Analyze button are **not rendered** — the user cannot fill a form they cannot submit.
- Surface `scansRemaining: number` on `UsageState`, mirroring the `interviewPrepsRemaining` shape introduced by P5-S60 (commit `56afd99`). Folds in the `UsageState`-vs-`UsageResponse` asymmetry flagged during this slice's audit (BE already returns `scans_remaining`; FE drops it during `fromResponse()` mapping). Cheap fold-in.
- Fire a pre-flight gate-render telemetry event (existing `paywall_hit` event with new `surface` property, additive — see §3.5) so the funnel-math denominator captures wall-shown semantics for this hard-wall trigger at page-load (parallel to the modal-open semantics it already captures elsewhere).

### Non-Goals
- Refactoring `WallInlineNudge.tsx` to be trigger-aware or card-shape. **B-042 owns that work.** This spec uses an inline gate card composed locally in `Analyze.tsx`, not a generalized `WallInlineNudge` extension.
- Retro-fitting the `/prep/results` Re-analyze sibling (spec #55 / B-030) to a pre-flight pattern. Today the Re-analyze button is left clickable and gates at click-time via `setShowPaywall(true)`. Whether to extend the pre-flight pattern to that surface is tracked separately as a 🟦 follow-up row filed by this slice (see §7).
- Adding a new `PaywallTrigger` value (e.g. `ats_scan_exhausted`). Reuse `scan_limit` per LD-1.
- Touching `paywall_service.py` hard-wall set, `should_show_paywall` logic, or any backend route. No backend code changes.
- Win-back wiring (E-031 🟦 — separate activation gate).

## §3 Behavior Specification

### §3.0 Locked Decisions

The seven LDs below are locked in this spec's authoring prompt. Restated here so reviewers do not have to chase the prompt.

- **LD-1 — Reuse `PaywallModal trigger="scan_limit"`.** Do NOT add `ats_scan_exhausted` to the trigger catalog. Do NOT refactor `WallInlineNudge` for this slice — B-042 owns that work separately.
- **LD-2 — Pre-flight gate the form.** When `!canScan && plan === 'free' && !isAdmin`, the resume upload + JD textarea + Analyze button are NOT RENDERED. In their place renders a single card: headline + body + one primary CTA "Upgrade to Pro" that opens `PaywallModal trigger="scan_limit"`. Form fields not just disabled — absent.
- **LD-3 — Quota chip stays.** The existing `{scansUsed}/{maxScans} free scans used` chip (Analyze.tsx:111-128) remains visible above the gate card as a quota signal. The dead `— Upgrade for more` `<span>` at Analyze.tsx:122-126 is removed (replaced by the gate card itself).
- **LD-4 — Surface `scansRemaining`.** Add `scansRemaining: number` to `UsageState` mirroring the `interviewPrepsRemaining` shape from P5-S60 (commit `56afd99`). Derived as `Math.max(0, max_scans - scans_used)` in `fromResponse`, with the `-1` unlimited sentinel preserved for Pro / Enterprise / admin (matches `interviewPrepsRemaining` mapping in `UsageContext.tsx`). `UsageContext.tsx` and consumers consume `scansRemaining` where they currently inline-derive.
- **LD-5 — Telemetry on render.** Fire a pre-flight gate-render event when the wall card renders (not on the click — on the render). Event name is `paywall_hit` (existing event per `.agent/skills/analytics.md:41`); a new optional `surface: 'analyze_page_load'` property additively distinguishes this fire from the modal-open fire. Props minimum: `{ trigger: 'scan_limit', surface: 'analyze_page_load', plan: 'free' }`. See §3.5 for the full schema.
- **LD-6 — Pro / admin / Enterprise bypass.** These cohorts see the form unchanged. `canScan` returns true for them via the existing `canUsePro || maxScans === -1` short-circuit at `UsageContext.tsx:117`. No new branch.
- **LD-7 — Submit-time fallback stays.** The existing `useAnalysis.runAnalysis()` 402-catch (`useAnalysis.ts:60-74`) and BE 402 envelope (`analyze.py:86`) remain wired — defense in depth in case `canScan` goes stale between page-load and submit (e.g., user opens two tabs, exhausts in one, submits in the other).

### §3.1 Free user at cap (`canScan === false && plan === 'free' && !isAdmin`)

The gate card renders in place of the 2-column upload grid (Analyze.tsx:132-144). Form fields are **absent** from the DOM, not disabled. Header text + the existing usage chip (LD-3) remain above the gate card.

**Card content (locked copy — do NOT defer to impl):**

- **Headline:** `"You've used your free ATS scan"`
- **Body:** `"Upgrade to Pro for unlimited scans and full study features."`
- **Primary CTA label:** `"Upgrade to Pro"`
- **Primary CTA action:** `setShowUpgradeModal(true)` (from `useUsage()`) opens the app-root `<UpgradeModal>` wrapper mounted in `main.tsx`, which internally renders `<PaywallModal trigger="scan_limit">`. Modal copy is provided by `PaywallModal.tsx` HEADLINES/SUBLINES (already on disk, verbatim):
  - HEADLINES["scan_limit"]: `"You've hit your free scan limit"`
  - SUBLINES["scan_limit"]: `"You've used all your free ATS scans. Upgrade to Pro for unlimited scans and the full study library."`
- **No secondary CTA.** No "Not now" button. The user closes via the existing PaywallModal X / backdrop / "Not now" inside the modal (which already POSTs `/payments/paywall-dismiss` per spec #42 §5.4 — that path stays unchanged). Page itself has no "Not now" affordance because the gate IS the page state — there is nothing to dismiss back to.

**Design tokens (R12, no hex):** the card uses `bg-bg-surface/50`, `border-contrast/[0.06]`, `rounded-2xl`, `text-text-primary`, `text-text-secondary` to match the existing form-tile aesthetic on the page. The primary CTA uses `<GlowButton>` matching the canonical CTA pattern elsewhere in the page.

**Layout:** the card occupies the same vertical space the 2-column grid would have occupied (single centered card, max-width matching the existing grid container). Header above stays unchanged.

### §3.2 Free user with scans available (`canScan === true && plan === 'free'`)

The form renders unchanged. Quota chip renders in current state ("0/1 free scans used"). No gate card. No telemetry event from this spec fires.

### §3.3 Pro / admin / Enterprise (`canScan === true` via `canUsePro || maxScans === -1`)

The form renders unchanged. Quota chip is hidden by the existing `usage.plan === 'free' && !usage.isAdmin && usage.maxScans > 0` guard at `Analyze.tsx:111`. No gate card. No telemetry event from this spec fires.

### §3.4 Submit-time fallback (LD-7 defense in depth)

The existing two-layer submit-time gate stays wired:

1. **FE pre-flight at submit** (`useAnalysis.ts:30-45`): `if (!canScan)` fires `free_scan_cap_hit {attempted_action: 'initial', scans_used_at_hit}` + `setShowUpgradeModal(true)`. With this spec landed, this path effectively becomes unreachable for free users (they cannot submit a form that does not exist) — but the code stays as defense-in-depth for the cross-tab race noted in LD-7.
2. **BE 402 catch** (`useAnalysis.ts:60-74`): `extractScanLimitDetail` unwraps the `app/api/routes/analyze.py:86` 402 envelope (`{error: "free_tier_limit", trigger: "scan_limit", scans_used, scans_limit, plan}`) and fires `free_scan_cap_hit {attempted_action: 'initial', scans_used_at_hit: detail.scans_used}` + `setShowUpgradeModal(true)`. Same defense-in-depth role.

Neither path is removed by this spec. The pre-flight gate is added in front of them.

### §3.5 Telemetry — `paywall_hit` with new `surface` property

Per LD-5, fire on render (not on click). Event name: `paywall_hit` (the existing event per `.agent/skills/analytics.md:41` line; convention §15 forbids renaming).

**Schema (additive — no break to existing consumers):**

| Property | Value | Notes |
|---|---|---|
| `trigger` | `'scan_limit'` | Existing required prop. |
| `surface` | `'analyze_page_load'` | **New optional prop.** Distinguishes the page-load wall fire from the existing modal-open fire (which omits `surface`). Naming convention matches existing `surface?: 'home_countdown'` on `interview_target_date_added` (analytics.md:77). |
| `plan` | `'free'` | **New optional prop** so funnel queries can filter without joining identify-time props. Always `'free'` for this fire (Pro/admin do not render the gate per §3.3). |
| `category_name?` | omitted | Existing optional prop on `paywall_hit` — N/A for this surface. |
| `cards_viewed?` | omitted | Existing optional prop — N/A for this surface. |

**Fire condition:** once on mount of the gate card (use `useRef` idempotency guard matching the `home_dashboard_viewed` / `first_action_viewed` convention so React Strict-Mode's double-invoked effect captures once). Re-mounting the page (navigation away + back) re-fires.

**Note on spec #42 §6 LD-6 divergence:** spec #42 §6 LD-6 says "the silent inline nudge does NOT fire `paywall_hit`." That rule was authored for the soft-wall `daily_review` case, where the nudge is a SUBSTITUTE for the modal during grace and counting it would inflate the funnel denominator. For hard-wall triggers like `scan_limit` (per `paywall_service.py:180`), there is no grace and the gate IS the wall — every page-load equals a wall-shown event, semantically identical to a modal-open. Firing `paywall_hit` here is the correct funnel-math semantics, not a violation of LD-6. **This spec does NOT amend spec #42** — the hard-wall vs soft-wall distinction is documented in `paywall_service.py:171-181` and is the implicit gating signal.

**Catalog update:** the `paywall_hit` row in `.agent/skills/analytics.md:41` gains a note documenting the new `surface` property as part of the impl-slice (P5-S61-impl) commit, per the P5-S21b convention (catalog updated alongside event introduction).

## §4 Data Surface

### §4.1 `UsageState` extension (FE-only)

Add `scansRemaining: number` to `UsageState` in `hirelens-frontend/src/context/UsageContext.tsx`, mirroring the `interviewPrepsRemaining` shape from P5-S60.

```ts
interface UsageState {
  // … existing fields unchanged …
  // spec #56 LD-1 — 1 lifetime scan for free; -1 sentinel = unlimited.
  scansUsed: number
  scansRemaining: number   // NEW — derived from BE response, mirrors interviewPrepsRemaining
  maxScans: number
  // …
}
```

Mapping in `fromResponse`:

```ts
function fromResponse(r: UsageResponse): UsageState {
  return {
    // …
    scansUsed: r.scans_used,
    scansRemaining: r.scans_remaining,   // BE already sends this — see §4.2
    maxScans: r.max_scans,
    // …
  }
}
```

`DEFAULT_STATE` gets `scansRemaining: 1` (matches `maxScans: 1` free default; BE overwrites on hydrate). `loadDisplayCache()` maps `parsed.scansRemaining ?? 1` for write-through cache compatibility.

`upgradePlan()` extends to set `scansRemaining: isPaid ? -1 : Math.max(0, 1 - prev.scansUsed)` matching the `interviewPrepsRemaining` precedent.

**No consumer of this spec required to use `scansRemaining`** — `Analyze.tsx`'s gate decision still reads `canScan` (the canonical boolean derived at `UsageContext.tsx:117`). The new field is surfaced because (a) BE already sends it, (b) the asymmetry vs `interviewPrepsRemaining` is a small drift that should not persist, and (c) future consumers (e.g., a "0 scans remaining this month" copy variant) can read it without re-deriving.

### §4.2 No BE changes

`UsageResponse` (the `/payments/usage` endpoint response) already returns `scans_remaining: number` per `app/api/routes/payments.py:150` — added by spec #56 §4.3. The FE just consumes what the BE already sends. No route change, no schema change, no migration.

### §4.3 No schema changes, no new endpoints

This spec adds zero database columns, zero tables, zero endpoints. All work is FE behavior + one additive `UsageState` field + one new `surface` property on an existing PostHog event.

## §5 Acceptance Criteria

- **AC-1 — Gate renders pre-flight for free-at-cap.** A free user with `usage.plan === 'free'`, `usage.isAdmin === false`, `usage.canScan === false` who navigates to `/prep/analyze` sees the gate card (per §3.1) in the DOM. The `<ResumeDropzone>` and `<JDInput>` components are NOT in the DOM (asserted absent by `queryByTestId` / `queryByRole`).

- **AC-2 — Form absent (not just disabled).** Vitest assertion: `screen.queryByRole('button', { name: /Analyze Resume/i })` returns null when AC-1's preconditions hold. `screen.queryByText(/upload your resume/i)` (or whatever the dropzone's placeholder is) returns null. The form is gone, not greyed out.

- **AC-3 — Primary CTA opens correct modal.** Clicking the gate card's "Upgrade to Pro" button calls `setShowUpgradeModal(true)` and the app-root `<UpgradeModal>` wrapper opens its inner `<PaywallModal trigger="scan_limit">`. PaywallModal HEADLINE renders as `"You've hit your free scan limit"` (verbatim from `PaywallModal.tsx:39`).

- **AC-4 — Pro user unaffected.** A user with `usage.plan === 'pro'` (or `'enterprise'`, or `usage.isAdmin === true` regardless of plan) who navigates to `/prep/analyze` sees the form normally (`<ResumeDropzone>` + `<JDInput>` + `<GlowButton>` all present). No gate card. No `paywall_hit {surface: 'analyze_page_load'}` event fires.

- **AC-5 — Free user with scans remaining unaffected.** A free user with `usage.scansUsed === 0` and `usage.maxScans === 1` (`canScan === true`) sees the form normally. No gate card. No event fires.

- **AC-6 — Quota chip stays visible at cap.** When AC-1's preconditions hold, the `{scansUsed}/{maxScans} free scans used` chip (currently at `Analyze.tsx:111-128`, minus the dead `— Upgrade for more` span removed in this spec) renders **above** the gate card. Verified by Vitest asserting both the chip text `1/1 free scans used` and the gate card headline are present in the same render. The dead `<span className="text-warning font-medium ml-1">— Upgrade for more</span>` is removed entirely.

- **AC-7 — Telemetry fires once per page-load when gated.** When the gate card mounts, `capture('paywall_hit', { trigger: 'scan_limit', surface: 'analyze_page_load', plan: 'free' })` fires exactly once. Re-renders within the same mount do not re-fire (idempotency via `useRef`). Vitest asserts the event fired exactly once across the entire `renderInterview()`-equivalent for `/prep/analyze`.

- **AC-8 — Submit-time 402 fallback still wired.** Verified by NOT adding any test that asserts the `useAnalysis.ts:60-74` 402-catch path is removed. The path remains in code; the cross-tab-race correctness invariant from LD-7 is preserved by the absence of a removal-PR for that block. (Unverifiable as a positive test; called out as a code-review checkpoint.)

- **AC-9 — `scansRemaining` derived correctly.** Vitest pin on `fromResponse`:
  - Input `{scans_used: 0, scans_remaining: 1, max_scans: 1, ...}` → output `{scansUsed: 0, scansRemaining: 1, maxScans: 1, ...}`.
  - Input `{scans_used: 1, scans_remaining: 0, max_scans: 1, ...}` → output `{scansUsed: 1, scansRemaining: 0, maxScans: 1, ...}`.
  - Input `{scans_used: 5, scans_remaining: -1, max_scans: -1, ...}` (Pro) → output `{scansUsed: 5, scansRemaining: -1, maxScans: -1, ...}`.

## §6 Testing Plan

### §6.1 FE Vitest (impl-slice)

Add to `tests/Analyze.gate.test.tsx` (new file, parallel to existing `tests/pages/Analyze.gate.test.tsx` from B-031 — pick the path the impl-slice audit confirms is the canonical `Analyze.tsx` test home; if duplicate-folder ambiguity surfaces during impl, consolidate).

| Test | AC | Stub shape |
|---|---|---|
| `renders gate card and hides form when free user is at cap` | AC-1, AC-2, AC-6 | `useUsage` stub: `{plan:'free', isAdmin:false, scansUsed:1, scansRemaining:0, maxScans:1, canScan:false, ...}` |
| `Upgrade CTA opens PaywallModal with scan_limit trigger` | AC-3 | Same stub + click the Upgrade button + assert PaywallModal headline visible |
| `renders form for Pro user regardless of scansUsed` | AC-4 | `useUsage` stub: `{plan:'pro', isAdmin:false, scansUsed:99, scansRemaining:-1, maxScans:-1, canScan:true, ...}` |
| `renders form for free user with scans available` | AC-5 | `useUsage` stub: `{plan:'free', isAdmin:false, scansUsed:0, scansRemaining:1, maxScans:1, canScan:true, ...}` |
| `renders form for admin on free plan` | AC-4 | `useUsage` stub: `{plan:'free', isAdmin:true, scansUsed:1, scansRemaining:-1, maxScans:-1, canScan:true, ...}` |
| `paywall_hit fires once with surface='analyze_page_load' on gate render` | AC-7 | At-cap stub + spy on `capture` + assert exactly one matching call |
| `paywall_hit does NOT fire when form renders normally` | AC-7 negative | Pro stub + assert zero `paywall_hit` calls with `surface='analyze_page_load'` |

Add to `tests/context/UsageContext.hydration.test.tsx` (existing) — note the file currently has 5 pre-existing failures from a prior uncommitted working-tree edit; impl-slice should fix or work around per session-state baseline. Three new pin tests for AC-9:

| Test | Input | Expected |
|---|---|---|
| `fromResponse derives scansRemaining for free with quota` | `{scans_used:0, scans_remaining:1, max_scans:1}` | `scansRemaining:1` |
| `fromResponse derives scansRemaining for free at cap` | `{scans_used:1, scans_remaining:0, max_scans:1}` | `scansRemaining:0` |
| `fromResponse preserves -1 sentinel for Pro` | `{scans_used:5, scans_remaining:-1, max_scans:-1}` | `scansRemaining:-1` |

**Expected FE test count delta at P5-S61-impl ship:** ~ +7-10 (Analyze.gate) + 3 (UsageContext.fromResponse). Impl-slice locks the actual delta.

### §6.2 BE pytest

**None required.** No BE changes. Existing `test_payments_usage_route.py` already pins `scans_remaining` shape (per spec #56 + P5-S60's pinned-shape extension). Existing `test_analyze_quota.py` already pins the 402 envelope (per spec #56 / B-031). Existing `test_paywall_service.py` already pins the `scan_limit` hard-wall behavior (per spec #56).

### §6.3 Manual smoke (post-deploy)

1. **Free user post-scan, cold load:** sign in as a free test user with `scans_used >= 1`, navigate to `/prep/analyze` directly (or via TopNav). Verify: gate card visible, dropzone absent, JD textarea absent, Analyze button absent, quota chip `1/1 free scans used` visible above the gate. Click "Upgrade to Pro" → PaywallModal opens with the `scan_limit` headline. Click X / Not now → modal closes, gate card stays visible.
2. **Pro user:** sign in as Pro, navigate to `/prep/analyze`. Verify: form renders normally, no chip (Pro hides it), no gate card.
3. **Admin on free plan:** sign in as admin (Google email matches `ADMIN_EMAILS`) on the free plan. Verify: form renders normally, no chip, no gate card.
4. **Telemetry:** open PostHog Live Events, repeat scenario 1, verify exactly one `paywall_hit` event with `{trigger: 'scan_limit', surface: 'analyze_page_load', plan: 'free'}`.
5. **Cross-tab race (LD-7):** open `/prep/analyze` in tab A while at `scans_used: 0`, run a scan in tab B to exhaust quota, then submit the form in tab A. Verify: BE 402 catch in `useAnalysis.ts:60-74` fires, `free_scan_cap_hit` event captures, app-root `<UpgradeModal>` opens. (This proves the defense-in-depth path stays wired.)

## §7 Out of Scope (explicit list with row references)

- **WallInlineNudge generalization** — tracked as **B-042** 🟦 (filed by P5-S60, activation gate = batched all-4-triggers paywall-grace pass). Do not generalize for this spec; compose the gate card locally in `Analyze.tsx`.
- **`/prep/results` Re-analyze sibling retro-fix.** Today (per spec #55 / B-030, commit `5c20d53`) the Re-analyze button on `/prep/results` is left clickable and gates at click-time via `setShowPaywall(true)`. Whether to retro-fit it to the same pre-flight pattern (disable / replace the button when `canScan === false`) is filed as a 🟦 follow-up by this spec — see B-046 below (filed in this slice's commit).
- **New `PaywallTrigger` value** (`ats_scan_exhausted`) — explicitly rejected per LD-1. The `scan_limit` trigger already covers this conceptual surface.
- **`paywall_service.py` changes** — no hard-wall set edits, no `should_show_paywall` logic changes.
- **Win-back email wiring** — tracked as **E-031** 🟦 (50-dismissals-across-distinct-users activation gate per spec #42 §5.5). Dismissal rows from this surface still feed E-031's eventual gate via the existing `POST /payments/paywall-dismiss` path (already wired by `PaywallModal.tsx:121-136`).
- **`scan_age_days` on `scan_rehydrated`** — orthogonal telemetry gap tracked as **B-036** 🟦.
- **Other paywall surfaces** — `/prep/interview` (closed by P5-S60 / spec #49 §3.4), `/prep/rewrite` (closed by spec #58), `/learn/daily` (closed by spec #50). Not this spec.
- **Cold-load `?scan_id` hydration on `/prep/analyze`** — no analogous deep-link surface; the page is upload-first by design. (`/prep/interview` cold-load hydration is tracked separately as **B-041** 🟦 and is a different concern.)
- **Anonymous-user behavior on `/prep/analyze`** — the page is auth-protected (per `App.tsx` `<ProtectedRoute>`). Anonymous-scan funnel is tracked as **E-038** 🟦.

## §8 Open Questions

**None — all decisions locked in §3 LD-1..LD-7 above.**

The spec author considered but rejected the following as open questions because each has a confident default in §3:

- *"Should the gate card include a 'Browse cards' or 'Go home' secondary CTA?"* — No. The page-level navigation already provides those exits (TopNav, MobileNav). A secondary CTA on the gate card would compete with the primary "Upgrade to Pro" intent and dilute conversion.
- *"Should the chip text change from 'free scans used' to 'free scans (limit reached)' when at cap?"* — Out of scope for this spec; the chip already conveys the same information (`1/1`). Copy refinement is a UX-polish slice, not blocking.
- *"Should `surface: 'analyze_page_load'` be `surface: 'prep_analyze'` to match the `interview_target_date_added` `surface: 'home_countdown'` route-naming convention?"* — Considered. Decided `'analyze_page_load'` over `'prep_analyze'` because the meaningful telemetry signal is **the moment of fire** (page-load) not just **the route**, and `'analyze_page_load'` distinguishes it cleanly from a hypothetical future `'analyze_submit_attempt'` fire site. If the impl-slice owner judges `'prep_analyze'` better-aligned with the existing `surface` convention, they may adjust — flag in commit message.

## §9 References

### Originating BACKLOG row (verbatim quote)

```
| E-047 | payments/ux | Free user post-scan-limit lands on `/prep/analyze` with no working upgrade path | P1 | 🔴 | | (from 2026-04-25 chat UX audit, screenshot of `localhost:5199/prep/analyze`) | **Symptom (verbatim from audit):** banner reads `"1/1 free scans used — Upgrade for more"`, but `"Upgrade for more"` is plain text — no `href`, no CTA. Upload form + `Analyze Resume` button remain enabled; user can fill the form and only discover they're walled on submit (or worse — verify in audit slice whether the scan succeeds and double-charges the budget). No inline nudge to `/pricing`. No "scan limit reached" state. **Expected (decision deferred to spec slice):** either (a) `"Upgrade for more"` becomes a link to `/pricing`, OR (b) the page renders a `WallInlineNudge` (per spec #42 pattern) when `usage.scans_used >= usage.scans_limit`, hiding/disabling the upload form and showing a single "Upgrade to Pro" CTA. **Cross-refs:** spec #42 (paywall dismissal — `WallInlineNudge.tsx` is the canonical inline-nudge component); `paywall_service.should_show_paywall` (likely needs a `trigger="ats_scan_exhausted"` catalog entry, or reuse `scan_limit` per B-031 hard-wall semantics); B-030 (`Re-Analyze` paywall on `/prep/results`, closed `5c20d53`) — same shape, different surface; B-031 (free-tier scan lifetime cap, closed `2080577`) — BE 402 enforcement already in place; this row is the FE page-level UX fix on top of the existing BE quota. **Next slice:** spec-author (Mode 4) to decide gate-vs-link, then implement-to-spec. **Out of scope this row:** any code change. R14 default (UX fix on revenue surface; spec-first). |
```

This spec resolves the "(decision deferred to spec slice)" branch from E-047 by selecting a hybrid of (a)+(b): the dead text is removed (a), and the upload form is replaced with a gate card (b), but composed inline rather than via `WallInlineNudge` (which today is a different shape — see B-042 for generalization).

### Cited specs (all verified on disk)

- `docs/specs/phase-5/42-paywall-dismissal.md` — paywall trigger pattern, hard-wall set, dismissal grace counter, `should_show_paywall` semantics. Spec #42 §6 LD-6 is the source of the "silent inline nudge does NOT fire `paywall_hit`" rule that this spec explicitly reasons through and diverges from for hard-wall (§3.5).
- `docs/specs/phase-5/55-reanalyse-paywall-gate.md` — B-030 sibling pattern. Provides the `setPaywallTrigger('scan_limit') + setShowPaywall(true)` mount + handler shape this spec extends to a pre-flight surface.
- `docs/specs/phase-5/56-free-tier-scan-lifetime-cap.md` — B-031 BE quota enforcement. Provides `PLAN_LIMITS["free"]["analyze"] = 1` (lifetime), the 402 envelope shape (`{error: "free_tier_limit", trigger: "scan_limit", scans_used, scans_limit, plan}`), and the `scan_limit` hard-wall membership in `paywall_service.py:180`. Also introduced the `UsageResponse` `scans_remaining` field this spec consumes.
- `docs/specs/phase-5/58-legacy-rewrite-router-auth-quota.md` — `UsageContext` extension precedent (rewrites_used / rewrites_remaining / rewrites_max). This spec mirrors the same flat-additive pattern for `scansRemaining`.
- `docs/specs/phase-5/49-interview-question-storage.md` — referenced via P5-S60's `interviewPrepsRemaining` extension; that field is the direct precedent for the LD-4 `scansRemaining` addition (commit `56afd99`).

### Cited source files (all verified on disk)

- `hirelens-frontend/src/pages/Analyze.tsx` — lines 86 (`useUsage()` consumption), 111-128 (quota chip + dead `— Upgrade for more` span), 132-144 (2-column upload grid that gets replaced), 153-162 (Analyze button gated only on form-completeness today).
- `hirelens-frontend/src/pages/Results.tsx` — lines 60-93 (B-030 sibling handler shape), 264-272 (CTA wiring), 556-560 (PaywallModal mount with state-driven `paywallTrigger`). Cross-reference for the inline-mount pattern this spec extends.
- `hirelens-frontend/src/context/UsageContext.tsx` — lines 8-30 (`UsageState` shape), 50-70 (`DEFAULT_STATE`), 92-119 (`fromResponse` mapping), 117 (`canScan` derivation — unchanged by this spec), 134-180 (`upgradePlan` optimistic update path that gets `scansRemaining` extension).
- `hirelens-frontend/src/services/api.ts` — lines 569-588 (`UsageResponse` interface; `scans_remaining` already typed; no extension needed in this file).
- `hirelens-frontend/src/hooks/useAnalysis.ts` — lines 14, 25 (scan_limit extraction), 30-45 (FE pre-flight gate at submit), 60-74 (BE 402 catch). Defense-in-depth paths preserved per LD-7.
- `hirelens-frontend/src/components/PaywallModal.tsx` — lines 21-29 (`PaywallTrigger` union), 38-47 (HEADLINES), 49-66 (SUBLINES). `scan_limit` copy verified appropriate verbatim (§3.1).
- `hirelens-backend/app/services/paywall_service.py` — lines 137-181 (`should_show_paywall` + hard-wall set). Unchanged by this spec.
- `hirelens-backend/app/services/usage_service.py` — line 16 (`PLAN_LIMITS["free"]["analyze"] = 1`). Unchanged by this spec.
- `hirelens-backend/app/api/routes/payments.py` — lines 136-159 (`UsageResponse` Pydantic; `scans_remaining: int` already on the wire from spec #56 §4.3). Unchanged.
- `hirelens-backend/app/api/routes/analyze.py` — lines 74-86 (BE 402 envelope). Unchanged. AC-7 (LD-7 fallback) verifies this path stays wired.

### Cited skill files

- `.agent/skills/payments.md` — paywall trigger conventions, scan-limit pattern (line 104).
- `.agent/skills/analytics.md` — line 41 (`paywall_hit` event source-of-truth), line 16 (snake_case + flat-primitives convention), line 20 (every user-facing feature must fire an event), line 22 (deprecate-don't-rename rule applied to the additive `surface` property choice).

### Related BACKLOG rows

- **E-047** (this spec resolves the spec-author half; impl half = B-045 below).
- **B-045** (filed by this slice — implementation row).
- **B-046** (filed by this slice — `/prep/results` Re-analyze sibling retro-fix, 🟦, see §7).
- **B-031** (closed `2080577`, spec #56) — BE quota enforcement that this spec depends on but does not modify.
- **B-030** (closed `5c20d53`, spec #55) — `/prep/results` Re-analyze pattern this spec extends/diverges from.
- **B-042** (🟦 — `WallInlineNudge` generalization; this spec deliberately does NOT consume it, see §2 non-goals).
- **E-031** (🟦 — win-back email; this spec's surface contributes to the dismissal-volume activation gate via the existing dismiss path).
- **E-038** (🟦 — anonymous-scan funnel; this spec covers the auth-protected `/prep/analyze` only).

### Cross-spec impacts

- `.agent/skills/analytics.md:41` — the impl-slice (P5-S61-impl) commit MUST update the `paywall_hit` row to document the new optional `surface` property. Per the P5-S21b convention (catalog updated alongside event introduction).
- No spec-source amendments to spec #42 / #55 / #56 / #58 are required by this slice. The hard-wall vs soft-wall reasoning that drives §3.5's `paywall_hit` fire decision is documented inline here (not in spec #42).

### Drift / amendments

- **2026-04-25 (post-impl `3c962d8`):** §3.1 line 66 + §5 AC-3 originally said the primary CTA called `setShowPaywall(true)` and opened "the existing `<PaywallModal>` mounted on the page." On-disk reality is `setShowUpgradeModal(true)` from `useUsage()` opening the app-root `<UpgradeModal>` wrapper (`main.tsx:81`), which internally renders `<PaywallModal trigger="scan_limit">`. Same UX outcome, same `scan_limit` trigger, same modal copy — only the function name + mount-point wording differed. Reconciled in this slice; spec text now matches the impl. Cross-ref: B-045 close notes already flagged this drift as non-blocking.
