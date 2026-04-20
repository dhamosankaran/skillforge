---
slice: P5-S22a (spec) + P5-S22b (impl)
base_sha: 6e126b3
drafted: 2026-04-19
locked_decisions: LD-001
---

# SPEC: Plan-Aware Missing Skills → Flashcards CTA

## Status: Draft

## Problem

The Missing Skills section on `/prep/results` currently renders a single branched CTA per skill that treats free and Pro users as a binary: Pro sees "Study this" (navigates to `/learn?category=<id>`), free sees "Upgrade to study" (opens `PaywallModal`). Three problems with that shape:

1. **Free users never experience the flashcard product before the paywall.** They hit the upgrade modal cold, with no sample of the core retention mechanic. Conversion-hostile.
2. **Pro users get a verb ("Study this") that implies a preview gate.** Minor, but lossy.
3. **Anonymous / logged-out users on `/prep/results`** (who land there via an anonymous scan per the legacy `/api/analyze` route) see a CTA that doesn't make sense — `isPro` defaults to `false`, so the free-user branch fires and the "Upgrade to study" modal pushes a signed-out user into Stripe with no account. Broken auth path for the anonymous funnel.

Missing Skills CTA needs to branch on three plan states (anonymous / free / Pro), not two (Pro / not-Pro), and the free branch needs to route users into the flashcard flow (under the free-tier 15-card budget per LD-001) rather than bouncing them straight to the paywall.

## Solution

Per Missing Skill item, render a CTA whose copy, routing, and a11y label differ by plan:

- **Anonymous user** (unauthenticated on `/prep/results`): CTA reads **"Sign in to study"** with a lock-icon visual. Click sends to `/login?return_to=/prep/results?scan_id=<id>`. PostHog plan prop = `"anonymous"`.
- **Free authenticated user**: CTA reads **"Study these cards — free preview"**. Click navigates to `/learn?category=<id>` (same URL Pro uses). The card-view side is subject to the existing 15-card-wall per LD-001 (daily review consumes the 15-card free-tier budget); no new wall logic is added in this slice. PostHog plan prop = `"free"`.
- **Pro / Enterprise user**: CTA reads **"Study these cards"**. Click navigates to `/learn?category=<id>`. No wall. PostHog plan prop = `"pro"`.

Plan detection reuses the existing `AuthContext` (`useAuth()` hook) and the existing `Subscription.plan` shape flowing through `AuthUser`. No new plan-detection mechanism is introduced in this spec.

The existing `MissingSkillsPanel` component at `src/components/dashboard/MissingSkillsPanel.tsx` is the natural home; prop surface extends from `{ isPro?: boolean; onUpgradeClick?: () => void }` to a three-state model that accepts plan explicitly and drops the upgrade-modal callback for the Missing-Skills CTA path specifically. (Upgrade-modal firing from other Results surfaces — e.g., `Results.tsx:431` — is untouched.)

## Acceptance Criteria

- **AC-1** — For a free authenticated user on `/prep/results`, each Missing Skill CTA renders with the free-preview copy (`"Study these cards — free preview"`), free-preview aria-label (`"Study cards for <skill>, free-tier preview"`), and the Lucide `BookOpen` icon. Verified by a Vitest test that mounts `MissingSkillsPanel` with `plan="free"` and asserts `getByRole('button', { name: /free-tier preview/i })`.
- **AC-2** — For a Pro user, each Missing Skill CTA renders with Pro copy (`"Study these cards"`), Pro aria-label (`"Study cards for <skill>"`), and `BookOpen` icon. Verified by a Vitest test with `plan="pro"`.
- **AC-3** — For an anonymous user (no auth session), each Missing Skill CTA renders with sign-in copy (`"Sign in to study"`), sign-in aria-label (`"Sign in to study cards for <skill>"`), and the Lucide `LogIn` icon. Verified by a Vitest test with `plan="anonymous"`.
- **AC-4** — Clicking the CTA for a free OR Pro user navigates to `/learn?category=<categoryId>` where `categoryId` is the first `matching_categories[0].category_id` from the `GapMapping` whose `gap` matches the skill (case-insensitive) and whose `match_type !== 'none'`. Verified by a Vitest test with a mocked `useNavigate()`; assert `navigate` called with the exact URL for both `plan="free"` and `plan="pro"`.
- **AC-5** — A free user's card-view is subject to the existing 15-card-wall per LD-001. No new paywall logic is added in this slice; the CTA routes into the existing flow. Verified by negative assertion: the Vitest free-user CTA click path must NOT open the `PaywallModal` synchronously on click (the wall is owned by the card-view route, not this component).
- **AC-6** — A Pro user clicking the CTA routes to the same URL with no wall. Covered by AC-4 (same URL) plus a negative assertion that the Pro click path does not fire `paywall_hit` from this component.
- **AC-7** — PostHog event `missing_skills_cta_clicked` fires on every CTA click with props `{ plan: "free" | "pro" | "anonymous", skill: <string>, category_id: <string | null> }`. For anonymous sign-in clicks, `category_id` is the resolved category (or `null` if no `GapMapping` matched). Verified by a Vitest test that stubs `capture` and asserts the exact payload across all three plan states. No rendering-side event is added (click is sufficient).
- **AC-8** — Anonymous user click routes to `/login?return_to=%2Fprep%2Fresults%3Fscan_id%3D<id>` (URL-encoded) when a `scan_id` is available in the current URL; if no `scan_id` is available, the `return_to` is `/prep/results` with no query. Verified by a Vitest test with a mocked `useNavigate()` and two URL-state scenarios.
- **AC-9** — Section-ID preservation: the Missing Skills section keeps its `id="missing-skills"` anchor. The 9-value `results_tooltip_opened` section enum from P5-S21b (`ats-score`, `score-breakdown`, `job-fit`, `keywords`, `skills`, `bullets`, `missing-skills`, `formatting`, `improvements`) is not changed. Verified by a grep-style Vitest test that asserts `document.getElementById('missing-skills')` is not null after mount and that `PanelSection`'s analytics-section prop remains `"missing-skills"`.

## API Contract

No new backend endpoints. The CTA uses existing client-side data and routes:

- **Plan info** — already read from `AuthContext.user.subscription?.plan` (same surface `MissingSkillsPanel`'s current `isPro` derivation uses in the Results page consumer). Anonymous = `user === null`.
- **Skill → category mapping** — already flows into `MissingSkillsPanel` as the `gapMappings: GapMapping[]` prop, populated by the existing `/api/v1/analyze` (authed) and `/api/analyze` (legacy anon) responses. The `gap_mapping` LLM task that produces these mappings is untouched.
- **Navigation target** — existing `/learn` route with `?category=<id>` query param. Already handled by `StudyDashboard` and `CategoryDetail` per the `src/App.tsx` routes table.

## Data Model Changes

None.

## Plan Detection

Read from the existing `useAuth()` hook (or equivalent context consumer already used elsewhere on `/prep/results`). Branches:

```
user === null                              → plan = "anonymous"
user.subscription?.plan === "pro"          → plan = "pro"
user.subscription?.plan === "enterprise"   → plan = "pro"   // treat as unwalled
otherwise                                   → plan = "free"
```

The plan value is computed at the `Results.tsx` consumer level and passed into `MissingSkillsPanel` as a prop (`plan: "anonymous" | "free" | "pro"`). This keeps `MissingSkillsPanel` plan-agnostic below the prop boundary and testable without mounting `AuthContext`. Implementation MUST NOT introduce a new plan-detection helper — if a shared derivation is useful, use the existing `isProPlan` helper (or whatever the live codebase exposes at P5-S22b implementation time; the P5-S22b audit will confirm).

## Copy

| Plan | Button label | Aria-label | Icon |
|------|--------------|------------|------|
| Anonymous | `Sign in to study` | `Sign in to study cards for <skill>` | Lucide `LogIn` |
| Free | `Study these cards — free preview` | `Study cards for <skill>, free-tier preview` | Lucide `BookOpen` |
| Pro | `Study these cards` | `Study cards for <skill>` | Lucide `BookOpen` |

Copy is final. Do not paraphrase in implementation; Vitest matchers assert these strings.

## UI/UX

- CTA renders inline beneath each missing-skill item, in the existing grid cell layout (`src/components/dashboard/MissingSkillsPanel.tsx` grid of `grid-cols-1 sm:grid-cols-2`).
- Button uses the existing design-system primitive (no new variant). Follow `.agent/skills/design-system.md` — **no hardcoded hex values** (Rule 12). If a button-style token is needed, introduce it in the design-tokens file in the same commit as the implementation; do not inline a color.
- On mobile, the CTA label wraps below the skill name if needed. MUST NOT truncate — the "free preview" suffix is semantically important and must remain visible.
- Icon + label spacing matches the existing `gap-1` from the live component.
- Keyboard: button is focusable; Enter/Space triggers click. Focus outline is whatever the design-system button primitive provides.
- The CTA does not open `PaywallModal`. The upgrade-modal firing from other Results surfaces (e.g., the top-level "Upgrade" button on `Results.tsx`) is untouched.

### Mobile-first layout note

The skill name and the CTA MUST stack on narrow viewports without overlapping. The existing `min-w-0 flex-1` around the skill-name line must be preserved; the CTA sits in `mt-2` below it.

### No new design tokens expected

The existing `text-accent-primary`, `text-text-muted`, `bg-bg-surface`, `border-border-accent` tokens should cover this CTA. If P5-S22b's audit finds a missing token, stop and add it to `design-tokens.ts` in the same slice (Rule 12 compliance).

## Analytics Events

- **`missing_skills_cta_clicked`** — fires on CTA click only (no render event). Props:
  - `plan`: `"free" | "pro" | "anonymous"` — required.
  - `skill`: string — the exact `gap.skill` value; required.
  - `category_id`: string | null — the resolved category id from `gapMappings`, or `null` if no `GapMapping` matched.

Add to `.agent/skills/analytics.md` in the same commit as P5-S22b implementation. This event replaces the existing `gap_study_clicked` (`user_plan` prop) fire on the P5-S22b cutover — `gap_study_clicked` is deprecated at that time and moved to the "Deprecated Frontend Events" section of the analytics catalog with a commit-SHA marker, following the pattern established in P5-S17 for `persona_changed` / `onboarding_persona_selected`. No render-side event is added in this slice.

## Edge Cases

- **Missing skill has no matching category** (`gapMappings` returns no `match_type !== 'none'` entry for this skill) → CTA renders as **disabled** with a tooltip reading `"No matching study content yet"`. Reuse the `PanelSection` tooltip primitive from P5-S21b. The disabled state still emits `missing_skills_cta_clicked` with `category_id: null` on keyboard-triggered activation attempts? **No** — disabled buttons do not fire click. No event on disabled.
- **User upgrades mid-session** (free → Pro via Stripe webhook + `AuthContext` refresh) → plan detection is reactive via context subscription; the CTA re-renders with Pro copy on next render cycle. No special handling required in this slice.
- **Free user has already consumed today's 15 cards** → CTA still renders with free-preview copy and still routes to `/learn?category=<id>`. The paywall fires on the card-view side per LD-001 (existing 15-card-wall logic — whose implementation is itself a future slice, as the 2026-04-19 audit confirms no card-view counter exists in `app/services/usage_service.py` today). This spec does NOT pre-empt the paywall from the CTA surface; the CTA's job is to route, not gate.
- **Anonymous user lands on `/prep/results` with no `scan_id` query** → CTA sign-in branch routes to `/login?return_to=%2Fprep%2Fresults` (no `scan_id`). Verified by AC-8.
- **`gapMappings` is empty** (all skills unmatched) → All CTAs render disabled per the first edge case. Component does not crash.

## Dependencies

- **LD-001** (2026-04-19) — free-tier daily-review budget consumes the 15-card budget (α). Referenced in frontmatter. This spec depends on α being locked; if α is ever reversed, this spec's free-user copy "— free preview" loses meaning and the routing-into-daily-review behavior would need rethinking.
- **Existing 15-card-wall mechanism** — MUST be functional when P5-S22b ships. P5-S22b's Step 1 audit MUST verify. Current reality (2026-04-19): the wall is NOT implemented in backend — `app/services/usage_service.py::PLAN_LIMITS` has no `card_view` or `daily_review` feature entry; `app/services/study_service.py::get_daily_review` and `::review_card` gate only on `Category.source == "foundation"` and do not increment a per-user card counter. **This is a blocker for P5-S22b if user-perceived gating is expected on day one of ship.** Two paths: (a) build the 15-card counter in a prerequisite slice before P5-S22b ships, or (b) ship P5-S22b on top of a known-missing wall and flag the gap as a Deferred Hygiene Item for a follow-up paywall-wiring slice. P5-S22b's Step 1 audit owns this decision and must surface it explicitly rather than silently pushing free users into a non-existent wall.
- **Missing Skills section ID stability** — `id="missing-skills"` anchor MUST remain (P5-S21b enum coupling per AC-9).
- **`gap_mapping` LLM task output shape** — `GapMapping[]` with `{ gap: string, match_type: string, matching_categories: { category_id: string, name: string }[] }` structure MUST NOT change. If it does, this spec's AC-4 category-resolution logic breaks.
- **`BACKLOG.md` E-011** — this spec closes E-011 at P5-S22b ship time. Notes column updated in this slice (P5-S22a) to point at this spec; status flip 🔴 → ✅ + `closed by <sha>` line happens in the P5-S22b implementation commit per Rule 15.

## Test Plan

### Vitest (to be written in P5-S22b BEFORE implementation per Rule 1)

- `test_missing_skill_cta_renders_free_copy_for_free_user` — AC-1.
- `test_missing_skill_cta_renders_pro_copy_for_pro_user` — AC-2.
- `test_missing_skill_cta_renders_signin_copy_for_anonymous` — AC-3.
- `test_cta_routes_to_correct_category_for_free_user` — AC-4, free branch.
- `test_cta_routes_to_correct_category_for_pro_user` — AC-4, Pro branch.
- `test_cta_routes_to_signin_with_return_to_for_anonymous_with_scan_id` — AC-8, scan_id present.
- `test_cta_routes_to_signin_with_return_to_for_anonymous_without_scan_id` — AC-8, no scan_id.
- `test_cta_does_not_open_paywall_on_free_user_click` — AC-5 negative assertion.
- `test_cta_disabled_when_no_matching_category` — first edge case.
- `test_cta_disabled_when_gap_mappings_empty` — fifth edge case.
- `test_cta_click_fires_posthog_with_plan_free` — AC-7, `plan: "free"`.
- `test_cta_click_fires_posthog_with_plan_pro` — AC-7, `plan: "pro"`.
- `test_cta_click_fires_posthog_with_plan_anonymous` — AC-7, `plan: "anonymous"`.
- `test_section_id_missing_skills_preserved` — AC-9.

Expected test count delta at P5-S22b ship: **+14** (142 → 156, assuming baseline unchanged between P5-S22a and P5-S22b).

### Manual post-deploy verification

- Sign in as a **free** user, run a scan, land on `/prep/results`, click each Missing Skills CTA, verify free-preview copy + routing to `/learn?category=<id>`. Verify the card-view page renders (paywall behavior at that layer is out of scope for this spec).
- Sign in as a **Pro** user, same flow — verify Pro copy + routing.
- Log out, do an **anonymous** scan via the landing-page path, land on `/prep/results?scan_id=<id>`, click a CTA, verify sign-in routing with `return_to` URL-encoding intact. On sign-in completion, verify return to `/prep/results?scan_id=<id>` preserves the scan view.

## Out of Scope / Follow-ups

- **Any paywall UX changes** — owned by P5-S26b (paywall dismissal). This spec does not touch `PaywallModal`.
- **Category-gated free-tier logic** — e.g., "free users can only see Foundation categories in the Missing-Skills study target" — needs its own Locked Decision and spec.
- **Skill → category mapping quality improvements** — uses the existing `gap_mapping` LLM task output as-is. Improvements (LLM prompt, match-type scoring) are their own slice.
- **Inline upgrade prompt on the CTA itself** — e.g., a micro-copy "upgrade for more" row adjacent to the free-preview CTA. Add only if PostHog data shows free-preview clicks converting below a threshold; defer for now.
- **`gap_study_clicked` event deprecation** — formal catalog move to "Deprecated Frontend Events" happens at P5-S22b implementation time, not this spec.
- **15-card-wall implementation** — today's code has no card-view counter; wiring the actual wall per LD-001 is a separate future slice (needs its own spec per Rule 14). Flagged as a P5-S22b-blocker or as Deferred Hygiene by P5-S22b's Step 1 audit.
- **`daily_review` paywall trigger cleanup** — `PaywallModal.tsx` defines the `daily_review` union-type value but no consumer in `src/` fires it. Dead code; cleanup (or wire-up, depending on the wall slice outcome) happens in the wall-implementation slice, not here.
