# P5-S62 — StudyDashboard `?source=last_scan` Hero Hint Consumer

**Status:** Drafted, not shipped.
**Owner:** Dhamo
**Created:** 2026-04-26
**Phase:** 5D (persona-aware surface — composition follow-up)
**Depends on:** P5-S61-impl (`StudyGapsPromptWidget` ships, primary CTA emits `/learn?source=last_scan` per spec #61 LD-11)
**Implementation slice:** P5-S62-impl (BACKLOG **B-053** filed by this slice)
**BACKLOG anchor:** B-052 (filed by P5-S61-impl from spec #61 §10 OQ-4 / LD-Q4 deferral)

## 1. Context

Spec #61 LD-11 set `/learn?source=last_scan` as the primary CTA target of the new `StudyGapsPromptWidget` on `HomeDashboard`. The query param flows from home but `StudyDashboard.tsx` does not consume it today — it currently reads only `?category=<id>` (spec #09 onboarding bridge filter, `StudyDashboard.tsx:63-69`). Spec #61 §9 / §10 OQ-4 explicitly deferred consumption to a follow-up slice to keep B-051's scope contained to a single page.

This spec defines the StudyDashboard side of the contract: when the param is present, render a slim hero hint acknowledging the user arrived from their last scan; otherwise render the page unchanged.

### 1.1 Why a hint, not a behavior change

The `?source=last_scan` is **attribution metadata**, not a filter. It does not narrow the category grid, change the FSRS queue, or modify the daily review. It only shifts the hero copy briefly so the user perceives a coherent flow from "home prompt → study page" rather than an abrupt context switch.

### 1.2 Source-of-truth boundary

This spec covers `source=last_scan` only. Other future `source` values (e.g., `source=onboarding`, `source=mission_setup`) are out of scope and gated to their own specs (LD-5).

## 2. Locked Decisions

| ID | Decision | Source |
|----|----------|--------|
| **LD-1** | Spec filename `docs/specs/phase-5/62-study-dashboard-source-hint.md`. No `^62-` collision (verified at SOP-5). | LD-1 prompt |
| **LD-2** | Hero hint copy is **DEFERRED to §10 Open Questions** (§6 enumerates 3 options with trade-offs; Dhamo picks before impl). Impl slice MAY NOT ship without an explicit copy decision. | LD-2 prompt |
| **LD-3** | **Visibility / dismissal: pure component state**, not sessionStorage. App-wide grep at SOP-5 returned **zero** uses of `sessionStorage` in `hirelens-frontend/src/`; introducing it for a single banner is unjustified. Component-state matches LD-3's "navigating away from StudyDashboard" semantics exactly: the component unmounts on navigation, state is lost, the next mount re-evaluates the URL param. No persistent flag needed. (LD-3's escape-hatch language explicitly authorizes this: "if not, use a simple component-state flag tied to the param presence.") | LD-3 prompt + SOP-5 grep |
| **LD-4** | Banner placement: **between the existing `<motion.div>` header row (`StudyDashboard.tsx:114-137`, ending with the "Start Daily Review" GlowButton) and the "Your Goal" persona card (line 139)**. This slot is presently empty whitespace; banner insertion does not push the persona card down significantly. Banner is a thin row (1 line of copy + dismiss × icon, ≤56px tall on desktop). The header + persona card retain their visual prominence. | LD-4 prompt + SOP-5 read of StudyDashboard.tsx |
| **LD-5** | **Out of scope** (per LD-5 prompt + spec author judgment): A/B testing the hero copy; persisting dismissal across sessions; telemetry beyond `study_dashboard_source_hint_shown` (`_dismissed` event surfaced in §10 as Open Question); backend changes; hint variants for non-`last_scan` source values; updating `StudyDashboard`'s existing `?category` filter logic; analytics around what categories the user clicks after seeing the hint. | LD-5 prompt |
| **LD-6** | **Telemetry: minimum one new event** `study_dashboard_source_hint_shown` fires on render via `useRef` idempotency guard (matches `home_dashboard_viewed` / `paywall_hit` convention). Whether to add a second event `study_dashboard_source_hint_dismissed` is an Open Question (§10 OQ-2). Event name verified against `.agent/skills/analytics.md` conventions at SOP-5 — no name collision. | LD-6 prompt |
| **LD-7** | **AC count: 4–6 testable assertions.** Spec ships with 5 ACs (§8). Each is testable from a Vitest render assertion against the new `tests/StudyDashboard.test.tsx` file (does not exist today; impl slice creates from scratch — see §8 closing note). | LD-7 prompt |
| **LD-8** | Param-name lock: `source`. Param-value lock for this spec: `last_scan`. Other values are silently ignored (render no banner, render no event). Future spec extension may add new value handlers without breaking this contract. | Spec author judgment, parallels CountdownWidget's `surface` prop |
| **LD-9** | Banner copy MUST use design tokens (R12). No hardcoded hex. Dismiss × icon: existing `lucide-react` `X` icon (already used elsewhere in the app). | R12 + on-disk convention |

## 3. Behavior

### 3.1 Param consumption

`StudyDashboard.tsx` already calls `const [searchParams, setSearchParams] = useSearchParams()` at line 63 for the `?category` filter. Spec #62 reuses the same `searchParams` reference; no new hook call needed.

Add:
```ts
const sourceParam = searchParams.get('source')
const isLastScanSource = sourceParam === 'last_scan'
```

`isLastScanSource` becomes the primary gate for banner render. Pure read — no setter call, no URL mutation. The param stays in the URL for the duration of the StudyDashboard mount; the impl slice does NOT strip it via `setSearchParams`. Rationale: stripping would invalidate the param if the user navigates away and uses the browser back button to return; keeping it preserves the intent across in-page interactions.

### 3.2 Render branching

Banner renders when:
```
isLastScanSource && !dismissed
```

Where `dismissed` is `useState<boolean>(false)`, scoped to the `StudyDashboard` component instance.

### 3.3 Dismiss interaction

Click on the × icon → `setDismissed(true)`. Banner unmounts on the next render cycle. No page reload, no URL change. Dismissed state is lost when:
- User navigates away from `/learn` (component unmounts).
- User reloads the page (component re-mounts; reads URL fresh; if `?source=last_scan` still in URL, banner re-shows).
- User dismisses, then later clicks the home `StudyGapsPromptWidget` again (which navigates with `?source=last_scan`) — banner re-shows because the new mount has fresh component state.

This matches LD-3's spec exactly.

## 4. Visibility & dismissal

| Trigger | Banner state |
|---------|--------------|
| First mount with `?source=last_scan` in URL | **Shown** |
| First mount without `?source=last_scan` in URL | **Hidden** |
| User clicks dismiss × | **Hidden** (component-state only) |
| User navigates away then returns without param | **Hidden** (param absent on return mount) |
| User navigates away then returns with param (e.g., back button after dismiss + new home click) | **Shown** (fresh mount, fresh state) |
| User reloads page with param in URL | **Shown** (fresh mount, fresh state) |
| User reloads page after dismissing | **Shown** if param still in URL (fresh state); **Hidden** if param absent |
| Other `?source=<value>` (not `last_scan`) | **Hidden** (LD-8) |

No long-term persistence. No toast. No animation beyond a simple framer-motion fade matching the existing `motion.div` patterns in `StudyDashboard.tsx`.

## 5. Layout & placement

Insertion point in `StudyDashboard.tsx`:

```
Line 137: </motion.div>                  ← end of header row (Start Daily Review button)
Line 138: (blank)
Line 139: {/* ── Your Goal card ─── */} ← banner inserts at this line
```

Banner sits in its own `<motion.div>` between the header row and the "Your Goal" card. It is visually a single horizontal row:

```
┌────────────────────────────────────────────────────────────┐
│  [icon]  <hint copy from §6 — Dhamo's pick>          [×]  │
└────────────────────────────────────────────────────────────┘
```

Spec-locked structural elements:
- Outer container: `<motion.div>` with `initial={{ opacity: 0, y: -4 }}` + `animate={{ opacity: 1, y: 0 }}` (matches existing motion convention).
- `data-testid="study-dashboard-source-hint"` on the outer container.
- Left icon: small `lucide-react` icon (`Target` or `BookOpen` — impl picks based on which copy variant Dhamo selects).
- Body: 1-line hint copy from §6 (final pick locked at impl).
- Dismiss button: `lucide-react` `X` icon, `data-testid="study-dashboard-source-hint-dismiss"`, `aria-label="Dismiss"`, fires `onClick={() => setDismissed(true)}`.
- Margin-bottom: `mb-6` (matches the persona-card margin convention).
- Background / border: design-token-driven, low-emphasis (e.g., `border-contrast/[0.08] bg-contrast/[0.02]` matching the persona-card empty-state at line 209). Final styling decisions are an impl detail within the design-token bounds.

## 6. Copy options (Decision pending — see §10 OQ-1)

Three proposals, each tagged with the trade-offs Dhamo should weigh.

### 6.A — Neutral / acknowledging
> **"Studying gaps from your last scan."**

- **Pros:** No PII surfaced (no company name); zero tone friction with existing StudyDashboard voice ("Choose a category to study or jump into your daily review."); shortest copy.
- **Cons:** Generic; doesn't reinforce the loop the user just completed (scan→study); user could read it as filler.
- **Telemetry implication:** No company name property needed in `study_dashboard_source_hint_shown`.

### 6.B — Personalized with company name
> **"Studying gaps from your {company} scan."**
> (where `{company}` is the user's most-recent `tracker_applications_v2.company`, fetched via `fetchUserApplications()`)

- **Pros:** Strongest "we know what you're doing" signal; matches the body copy that `StudyGapsPromptWidget` already shows on home (consistent narrative); higher likelihood of user engagement.
- **Cons:** **PII surface** — company name renders on a study page that may be screen-shared or recorded; if a user has a sensitive interview target (e.g., applying secretly), they may not want it on-screen elsewhere. Also adds an async fetch dependency to first paint (the banner blocks on the same `fetchUserApplications` call the home widget made). Caching helps but doesn't eliminate the latency.
- **Telemetry implication:** `study_dashboard_source_hint_shown` should include `has_company_name: bool` so dashboards can differentiate; **company name itself MUST NOT be sent** to PostHog (per existing convention in `analytics.md` — no PII in event payloads).

### 6.C — Action-framed with time commitment
> **"5 minutes a day closes most resume gaps. Pick a category below."**

- **Pros:** Reinforces the LD-1 "5 minutes a day" framing from `StudyGapsPromptWidget`; action-oriented ("Pick a category below"); zero PII; sets expectation for the page below.
- **Cons:** Loses the explicit "from your last scan" attribution (no narrative tie-back to home); the "Pick a category below" half is borderline patronizing for users who already know how the page works.
- **Telemetry implication:** Same as 6.A — no company name needed.

**Recommendation flagged for Dhamo:** 6.A is the safest default. 6.B if you're willing to handle the PII surface and the async-fetch dependency. 6.C if you want to reinforce the home framing without the PII risk.

## 7. Telemetry

Per LD-6 + analytics catalog convention.

### 7.1 Required event

| Event | Source | Properties | Fires |
|-------|--------|------------|-------|
| `study_dashboard_source_hint_shown` | `src/pages/StudyDashboard.tsx` | `{source: 'last_scan', persona, copy_variant: 'A' \| 'B' \| 'C', has_company_name?: boolean}` — `copy_variant` records which copy choice §6 produced (impl injects the constant). `has_company_name` is included only for variant `B` and is `false` if `fetchUserApplications` returned no apps. | Once per StudyDashboard mount when `isLastScanSource && !dismissed === true`, via `useRef` idempotency guard (matches `home_dashboard_viewed` convention). |

### 7.2 Conditional event (Open Question — see §10 OQ-2)

`study_dashboard_source_hint_dismissed` would fire on the × click. Whether to add it depends on whether dismissal-rate signal is worth the event-volume cost. **Default: defer.** Surface the question in §10; impl ships without unless Dhamo locks it in.

### 7.3 Existing events touched

`study_dashboard_viewed` (already fires on data load) is unchanged. The new hint event fires alongside, not instead of.

### 7.4 Catalog update

Impl slice updates `.agent/skills/analytics.md` with the new event row(s) before code merge.

## 8. Acceptance Criteria

Per LD-7. 5 ACs. Each testable from `tests/StudyDashboard.test.tsx` (NEW test file — page has no existing tests; impl slice creates from scratch).

| AC | Surface | Trigger | Expected | Test harness |
|----|---------|---------|----------|--------------|
| **AC-1** | StudyDashboard | URL has `?source=last_scan` | Banner renders. `data-testid="study-dashboard-source-hint"` present. Banner copy matches Dhamo's §6 pick (impl-locked at OQ-1 resolution). | Vitest `MemoryRouter initialEntries={['/learn?source=last_scan']}` + `getByTestId` |
| **AC-2** | StudyDashboard | URL has no `?source` param | Banner does NOT render. | Vitest `MemoryRouter initialEntries={['/learn']}` + `queryByTestId` returns `null` |
| **AC-3** | StudyDashboard | `?source=last_scan` present, click `study-dashboard-source-hint-dismiss` button | Banner unmounts; `queryByTestId` returns `null`. URL is unchanged (no `setSearchParams` called). | Vitest `fireEvent.click` + `queryByTestId` returns `null` + `expect(window.location.search).toContain('source=last_scan')` (or equivalent param-presence assertion) |
| **AC-4** | StudyDashboard | URL has `?source=last_scan` + `?category=<id>` (both params present) | Banner renders AND existing `?category` filter still applies. The two params are orthogonal; both consumers operate independently from the same `searchParams` reference. | Vitest `MemoryRouter initialEntries={['/learn?source=last_scan&category=cat-1']}` + assert banner present + assert filtered category grid |
| **AC-5** | `study_dashboard_source_hint_shown` PostHog event | URL has `?source=last_scan`, banner mounts | Event fires exactly once with `{source: 'last_scan', persona, copy_variant}` payload via `useRef` idempotency guard. Re-render without state change does NOT re-fire. | Vitest `vi.spyOn(posthog, 'capture')` + assert single call with matching payload |

> **Test scaffolding note:** `tests/StudyDashboard.test.tsx` does not exist on disk (verified at SOP-5; only `tests/home/widgets/StudyGapsPromptWidget.test.tsx` and `tests/App.redirects.test.tsx` reference StudyDashboard). The impl slice creates this file. Mock pattern follows `tests/HomeDashboard.test.tsx` precedent: stub `useStudyDashboard`, `useAuth`, `useUsage`, `useGamification`; mock `fetchUserApplications` only if variant 6.B is locked.

## 9. Out of scope

Per LD-5, plus what surfaced during drafting:

- Implementation. Lands in P5-S62-impl (BACKLOG **B-053**, filed by this slice).
- A/B testing the hero copy (decision is Dhamo's via OQ-1; no infrastructure for variant rollout).
- Persisting dismissal across sessions. Component-state only per LD-3.
- `study_dashboard_source_hint_dismissed` event (default defer, OQ-2).
- Backend changes. None required.
- Hint variants for `?source=<other>` values. Future spec when other source values exist (LD-8).
- Updating the existing `?category` filter logic (`StudyDashboard.tsx:65-77`). Untouched.
- Analytics around what category the user clicks after dismissing or seeing the hint (existing `category_tile_clicked` covers this; no spec-#62-specific funnel).
- Stripping `?source=last_scan` from the URL after consumption. URL stays as-is for the mount lifetime (§3.1 rationale).

## 10. Open Questions

| # | Question | Default if unanswered | Why it matters |
|---|----------|------------------------|----------------|
| **OQ-1** | Hero copy choice — 6.A neutral, 6.B personalized with company name (PII risk + async dep), 6.C action-framed. **Impl slice is BLOCKED on this decision.** | **6.A neutral.** Lowest risk, simplest impl, no PII concern, no async-fetch dep. | Drives both copy and impl complexity (variant 6.B requires `fetchUserApplications` call + loading state handling). Telemetry payload also varies (`has_company_name` only for 6.B). |
| **OQ-2** | Add `study_dashboard_source_hint_dismissed` event? | **No (defer).** If dismissal-rate signal becomes interesting later, file a follow-up to add it; cost of adding now is event-volume + a new property to track in dashboards for an unproven need. | Determines whether the impl slice wires a second `capture()` call in the dismiss handler. |
| **OQ-3** | If 6.B is picked: should the banner render a placeholder ("Studying gaps from your scan.") while `fetchUserApplications` resolves, or render nothing until the company name is known? | Placeholder + swap-on-resolve. Avoids layout shift and gives the user immediate feedback. | Affects perceived first-paint. Only relevant if 6.B is OQ-1 winner. |
| **OQ-4** | Should the banner's left icon match the icon used in `StudyGapsPromptWidget` (currently none — just text + buttons), or use a distinct icon (e.g., `BookOpen` to match StudyDashboard's heading)? | `BookOpen` (matches the page's existing visual language). | Visual coherence with home prompt vs. visual coherence with destination page. |
| **OQ-5** | The B-052 row format on disk is a single-row work tracker (covers both spec + impl). Per CLAUDE.md R15, spec-author slices don't close work-tracking rows — closure happens in the impl commit. This slice files B-053 = "Implement spec #62 (closes B-052)". **Two rows now track essentially the same impl work** (B-052 = the "Q4 follow-up" framing, B-053 = the spec impl). On B-053's impl-merge, both close together. Is this duplicate-tracking acceptable, or should one be retired? | Both close together at impl-merge. B-052 retains historical attribution (where the deferral originated); B-053 carries the impl commit SHA. Acceptable per established pattern (B-045 + E-047 followed similar dual-track). | Backlog hygiene. Surface for awareness; not blocking. |

## 11. Cross-references

- **Parent spec:** `docs/specs/phase-5/61-home-dashboard-composition-rules.md` §10 OQ-4 + LD-11 (param emitter)
- **Parent BACKLOG:** B-052 (filed by P5-S61-impl `ecef895`); this spec authors the §1-§9 deliverable
- **Impl tracker:** B-053 (filed by this slice; closes on impl-merge alongside B-052 per OQ-5)
- **Audit anchor:** `docs/audit/2026-04-E-048-home-dashboard.md` (E-048 audit; spec #61 was the recommended fix; spec #62 is the LD-Q4 follow-up)
- **StudyDashboard precedent:** `?category` filter consumer (`StudyDashboard.tsx:63-77`, spec #09 onboarding bridge)

---

*End of spec #62. Implementation slice to be authored as P5-S62-impl, closes B-053 + B-052 on merge per CLAUDE.md R15.*
