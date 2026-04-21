# P5-S12 — Navigation Restructure: Two-Namespace Nav (/learn + /prep)

**Status:** Shipped
**Owner:** Dhamo
**Created:** 2026-04-17
**Phase:** 5C (route restructure)
**Depends on:** P5-S13 (internal-reference sweep), P5-S14 (TopNav component)
**Related resolved decision:** SESSION-STATE.md → Resolved Decisions → Decision 3 (email deep-link coverage, 2026-04-17)

## Problem

The current top-nav is ATS-first: **Analyze → Results → Rewrite → Interview → Tracker**. This frames the product as a scanner with side features.

But the study engine (**Forge**) — daily-review, categories, Mission Mode, progress — is the retention driver and the primary subscription justification per `docs/prd.md §1.2`. Today it has **zero nav presence**: users reach `/study` only through the post-scan "recommended cards" CTA or by typing the URL. Career-Climber persona (`docs/prd.md §1.3`), whose whole value is daily habit, lands on a nav bar with no entry point to their core loop.

Compounding effects:

1. **Subscription justification is invisible.** Pro's retention value lives behind a URL users rarely see. When the monthly renewal hits, users don't remember what they're paying for.
2. **Mental model is wrong.** "Analyze" and "Study" are two fundamentally different intents; flattening them into one nav hides that distinction.
3. **Future surfaces have nowhere to live.** `/progress` (skill radar + heatmap) is already wired on the backend (`/api/v1/progress` per AGENTS.md) but has no dedicated page — it's embedded in `StudyDashboard`. New Phase 5 surfaces (PersonaPicker, HomeDashboard, CardChatPanel) need a coherent IA, not more flat routes.

## Solution

Two-namespace nav with a persona-aware home:

- **`/home`** — persona-aware dashboard (landing surface post-login; owned by P5-S18)
- **`/learn/*`** — study engine: Daily Review, Categories, Mission Mode, Progress
- **`/prep/*`** — interview prep: Analyze, Results, Rewrite, Interview, Tracker
- **`/profile`** — user settings + stats (unchanged)
- **`/admin`** — admin panel (admin role only, unchanged)

Top nav (desktop): `Home · Learn · Prep · Profile` (plus `Admin` if `user.role === 'admin'`).

Mobile: see **Mobile Behavior** below.

## Route Map

All paths currently listed in `AGENTS.md §Frontend — routes in src/App.tsx`. New paths below are the target state after P5-S14 lands the `TopNav` component and the updated `src/App.tsx`.

### Preserved (no change)

| Path | Component | Access | Rationale |
|------|-----------|--------|-----------|
| `/` | `LandingPage` | Public | Marketing surface; external links depend on it |
| `/login` | `LoginPage` | Public | OAuth redirect target |
| `/pricing` | `Pricing` | Public | Stripe checkout entry; external links depend on it |
| `/onboarding` | `Onboarding` | Protected | Persona picker entry post-signup (sits outside the two namespaces by design) |
| `/profile` | `Profile` | Protected | Settings surface; referenced widely |
| `/admin` | `AdminPanel` | Admin | Admin tool; no persona gating |
| `*` | redirect to `/` | — | Catch-all unchanged |

### Renamespaced

| Old flat path | New namespaced path | Component | Namespace |
|---------------|---------------------|-----------|-----------|
| `/analyze` | `/prep/analyze` | `Analyze` | Prep |
| `/results` | `/prep/results` | `Results` | Prep |
| `/rewrite` | `/prep/rewrite` | `Rewrite` | Prep |
| `/interview` | `/prep/interview` | `Interview` | Prep |
| `/tracker` | `/prep/tracker` | `Tracker` | Prep |
| `/study` | `/learn` (index → `/learn/categories`) | `StudyDashboard` | Learn |
| `/study/daily` | `/learn/daily` | `DailyReview` | Learn |
| `/study/category/:id` | `/learn/category/:id` | `CategoryDetail` | Learn |
| `/study/card/:id` | `/learn/card/:id` | `CardViewer` | Learn |
| `/mission` | `/learn/mission` | `MissionMode` | Learn |

### New (this spec introduces the paths; pages ship in later slices)

| Path | Component | Owning slice | Notes |
|------|-----------|--------------|-------|
| `/home` | `HomeDashboard` | P5-S18 | Persona-aware; default redirect target for authenticated users |
| `/learn/progress` | `Progress` | P5-S12 or follow-up | Lift skill radar + heatmap out of `StudyDashboard` into a standalone page |

`/home` replaces the current behaviour of sending authenticated users to `/` or `/study` after login. The post-login redirect target becomes `/home`.

## Redirect Strategy — client-side only

Per **SESSION-STATE.md Resolved Decision 3 (2026-04-17)**: the app is pre-production and has no legacy user traffic to preserve, so **no server-side 301s are required**.

Implementation (in `src/App.tsx`, `react-router-dom` v6):

```tsx
<Route path="/analyze"         element={<Navigate to="/prep/analyze" replace />} />
<Route path="/results"         element={<Navigate to="/prep/results" replace />} />
<Route path="/rewrite"         element={<Navigate to="/prep/rewrite" replace />} />
<Route path="/interview"       element={<Navigate to="/prep/interview" replace />} />
<Route path="/tracker"         element={<Navigate to="/prep/tracker" replace />} />
<Route path="/study"           element={<Navigate to="/learn" replace />} />
<Route path="/study/daily"     element={<Navigate to="/learn/daily" replace />} />
<Route path="/study/category/:id" element={<Navigate to="/learn/category/:id" replace />} />
<Route path="/study/card/:id"  element={<Navigate to="/learn/card/:id" replace />} />
<Route path="/mission"         element={<Navigate to="/learn/mission" replace />} />
```

Rules:

- Use `replace` so old paths don't pollute browser history.
- Dynamic segments (`:id`) preserved in the redirect target — React Router threads the param through automatically.
- Redirect routes live **alongside** the new namespaced routes, not inside them, so the render tree stays flat.
- These are **transitional**. Tech Debt log: remove this redirect block in Phase 6 cleanup once we confirm no internal references or bookmarks hit the old paths (add a PostHog event `deprecated_route_hit` on each redirect node to measure, then drop the block when the 30-day rolling count is zero).

## Nav Component — location + scope

- **File:** `src/components/layout/TopNav.tsx` (new, ships in P5-S14)
- **Mobile counterpart:** `src/components/layout/MobileNav.tsx` (new, ships in P5-S14)
- **Layout wrapper:** `src/components/layout/AppShell.tsx` (new or updated to host `TopNav` on desktop and `MobileNav` on mobile)
- Theming: every color/spacing/shadow via design tokens (`bg-bg-surface`, `text-text-primary`, `border-border-accent`, etc.) per `.agent/skills/design-system.md`. **No hex literals.** Active-state highlight uses `accent-primary`.
- Analytics: emit `nav_clicked` with `{namespace, from_path, to_path}` on every top-nav click (snake_case, per CLAUDE.md rule 8). Add to the catalog at `.agent/skills/analytics.md` when the component ships.

## Mobile Behavior — bottom bar (decision)

**Pattern chosen:** bottom bar (fixed, `position: fixed; bottom: 0;`).

Rationale:

1. **Exactly four primary destinations** (Home / Learn / Prep / Profile) fits a bottom bar cleanly — each tab gets ~25% width and a thumb-reachable target. Admin renders as a fifth tab only when `user.role === 'admin'`.
2. **Discoverability beats density.** A drawer hidden behind a hamburger is the exact failure mode this spec is fixing for `/study` — putting `Learn` back behind a tap defeats the purpose of promoting it.
3. **Daily-habit product.** Career-Climber persona uses this app every day from mobile (daily review). A persistent bottom bar is the standard pattern for daily-use apps (Duolingo, Anki, Instagram) and matches users' muscle memory.
4. **Active-namespace state is always visible.** Drawer closes itself; bottom bar shows the current namespace at all times, reinforcing the IA.

Rejected — **drawer**: better for >5 primary destinations or for products with settings-heavy secondary nav. Neither applies here.

Implementation notes for P5-S14:

- Bottom bar height `64px`, safe-area padding for iOS notch devices (`pb-[env(safe-area-inset-bottom)]`).
- Icons + labels (not icons alone) — icon-only bars hurt first-time discoverability.
- Active tab: filled icon + `accent-primary` label; inactive: outlined icon + `text-secondary`.
- Hide on `/` and `/login` and `/pricing` (public surfaces don't want authenticated nav chrome).

## Active-State Logic

Active-state detection uses `useLocation().pathname.startsWith(namespacePrefix)`:

- `/home` → Home active (exact match)
- `/learn` or `/learn/...` → Learn active
- `/prep/...` → Prep active
- `/profile` → Profile active
- `/admin` → Admin active

Edge cases:

- `/onboarding` — no tab active (persona picker is a modal-style interrupt, not part of the main IA).
- Transitional old paths (`/analyze`, `/study`, etc.) — redirect fires before render, so active state reflects the **target** path.

## Internal-Reference Sweep (P5-S13 checklist)

Per SESSION-STATE Resolved Decision 3, P5-S13 owns the sweep. AC-5 is this list. **No external 301s required** — every target is internal code or config.

### 1. Email templates

- `hirelens-backend/app/services/email/` — any template builder that interpolates absolute frontend URLs.
- Specifically audit:
  - Daily-reminder email (from P2 Resend integration) — if it links to `/study/daily`, update to `/learn/daily`.
  - Streak-milestone emails — any deep link into `/study/*`.
  - Unsubscribe email — confirm it targets `/profile` or a dedicated `/email-prefs/unsubscribe/:token` (unchanged).
- Grep target: `/analyze` `/results` `/rewrite` `/interview` `/tracker` `/study` `/mission` as string literals inside `hirelens-backend/app/services/email/`.

### 2. PostHog configuration

- Event properties that carry a path string: `$current_url`, `$pathname`, and any custom `target_path` / `route_clicked` fields.
- PostHog dashboards/insights that filter on `pathname = '/study/daily'` or similar — these live in the PostHog UI, not the repo. Action: after the new nav ships, update PostHog insights manually (tracked as a post-P5-S14 followup; not blocking).
- Instrumented points in `hirelens-frontend/src/services/analytics.ts` (if present) or inline `posthog.capture(...)` calls — grep `posthog.capture` for any call that embeds an old path.

### 3. Hardcoded frontend links

Grep targets in `hirelens-frontend/src/`:

- `to="/analyze"`, `to="/results"`, `to="/rewrite"`, `to="/interview"`, `to="/tracker"` (all `<Link>` props).
- `to="/study"`, `to="/study/daily"`, `to="/study/category/"`, `to="/study/card/"`, `to="/mission"`.
- `navigate("/analyze")` and every other `navigate("/…")` call with one of the above prefixes.
- `href="/study/..."` in any legacy `<a>` tag.
- Template literals: `` `/study/category/${id}` `` and similar.

Use `rg` with all ten old prefixes as alternations in one pass; cross-reference against the Route Map table above so nothing is missed.

### 4. Redirect constants / config

- `VITE_` env var defaults: `.env.example` — confirm no hardcoded post-login target references old paths.
- Stripe checkout success/cancel URLs — currently built from `FRONTEND_URL` + a relative path in `hirelens-backend/app/services/payments/`. Audit the relative path; if it targets `/study` or `/analyze`, update.
- Login redirect target (post-OAuth) — currently defaults to `/` or `/onboarding` depending on `onboarding_completed`. After this spec, authenticated + onboarded → `/home`.

### 5. Onboarding deep links

- Post-onboarding redirect target in `src/pages/Onboarding.tsx` — update to `/home`.
- Persona-picker completion in P5-S17 → route into `/home`.
- "Scan your resume" CTA on LandingPage (if any) → update to `/prep/analyze`.

### 6. Test fixtures

- `hirelens-frontend/tests/` — mock URLs, `MemoryRouter initialEntries={["/study/daily"]}` style test setup.
- `hirelens-backend/tests/` — any assertion that checks a response body for an absolute URL containing an old path (unlikely but worth one grep).

### Sweep proof artefact

P5-S13 must produce (and commit, or link in PR description) the output of the grep pass for each of sections 1, 3, 4, 6 showing **zero matches** for the ten old prefixes after the sweep. That output is the acceptance evidence for AC-5.

## Acceptance Criteria

- **AC-1** — Top nav renders `Home · Learn · Prep · Profile` on desktop, plus `Admin` iff `user.role === 'admin'`. Verified by a Vitest snapshot or role-matrix test against `TopNav`.
- **AC-2** — Every row in the Renamespaced table above: visiting the old path redirects (via `<Navigate replace>`) to the new path and the new path renders the expected component. Verified by a parameterised Vitest test that drives `MemoryRouter` through each old path and asserts the eventual rendered component's `data-testid`.
- **AC-3** — Active-state highlight: on `/learn/daily` → Learn tab shows accent; on `/prep/rewrite` → Prep tab shows accent; on `/home` → Home tab shows accent. Verified by a Vitest test that mounts `TopNav` inside `MemoryRouter` at each representative path and asserts the active tab's class set.
- **AC-4** — Mobile: bottom bar renders fixed at `bottom: 0` with safe-area padding, four tabs visible, active namespace highlighted. Verified by a Vitest test at a mobile viewport width (`matchMedia` mock) and a Playwright or manual smoke check on iOS Safari.
- **AC-5** — Internal-reference sweep: zero grep matches for any of the ten old prefixes in `hirelens-frontend/src/` (excluding the intentional `<Navigate>` redirect block in `App.tsx`) **and** in `hirelens-backend/app/services/email/`. Grep output committed with P5-S13 or attached to the PR description. **No external 301 redirects required** per SESSION-STATE Resolved Decision 3.

## Test Plan

- **New Vitest tests** (in P5-S14 alongside `TopNav`):
  1. `TopNav.test.tsx` — renders correct tabs for `user.role === 'admin'` vs non-admin.
  2. `TopNav.test.tsx` — active-state highlight for each namespace.
  3. `App.redirects.test.tsx` — parameterised over the ten old paths; each redirects to the new path and renders the right component.
  4. `MobileNav.test.tsx` — renders at mobile viewport with the four tabs and safe-area class.
- **Backend:** no backend test changes — no backend routes move. Full suite `python -m pytest tests/ -v --tb=short -m "not integration"` must still pass.
- **Frontend suite:** `cd hirelens-frontend && npx vitest run` must pass. Current frontend test count is 5 (per SESSION-STATE §Hard Constraints). This slice + P5-S14 should push that to at least 9.
- **Grep-proof** (AC-5): commit the sweep output with P5-S13 or include in the PR body.
- **Manual smoke** (post-deploy to staging):
  1. Log in fresh — land on `/home`.
  2. Click every top-nav tab — correct page renders, active state correct.
  3. Hit each old path directly in the address bar — redirects to new path, browser history shows only the new entry (the `replace` check).
  4. Mobile viewport (Chrome DevTools iPhone 14) — bottom bar visible, thumb-reachable, safe-area respects the notch.
  5. Click the landing page "Scan your resume" CTA — lands on `/prep/analyze`.

## Out of Scope

- Building `HomeDashboard` — owned by P5-S18.
- Building `/learn/progress` as a standalone page (lifting skill radar + heatmap out of `StudyDashboard`) — tracked as a P5-S12 follow-up or new slice; not blocking the nav restructure.
- Updating PostHog dashboard filters in the PostHog UI — post-ship follow-up, not a code change.
- Any server-side 301 redirect middleware — explicitly out of scope per SESSION-STATE Resolved Decision 3.
- Persona gating of `/learn/*` and `/prep/*` — owned by P5-S17 (`user.persona` requirement). This spec only handles paths and nav chrome; gating logic is added when PersonaPicker ships.
- i18n of nav labels — deferred to Phase 6.

## Analytics

New event (to add to `.agent/skills/analytics.md` when P5-S14 ships):

- `nav_clicked` — frontend — properties `{namespace: "home"|"learn"|"prep"|"profile"|"admin", from_path: string, to_path: string}`. Captured in `TopNav.tsx` and `MobileNav.tsx` on tap.

Transitional event (remove in Phase 6 when the redirect block is dropped):

- `deprecated_route_hit` — frontend — properties `{old_path: string, new_path: string}`. Captured in each of the ten `<Navigate>` redirect nodes so we can measure when the old paths stop receiving hits and safely drop the block.

No backend analytics changes.

## Files Touched (planned — no code in this slice)

- `src/App.tsx` — new route tree with two namespaces + redirect block (P5-S13)
- `src/components/layout/TopNav.tsx` — new (P5-S14)
- `src/components/layout/MobileNav.tsx` — new (P5-S14)
- `src/components/layout/AppShell.tsx` — new or updated (P5-S14)
- `hirelens-frontend/tests/TopNav.test.tsx` — new (P5-S14)
- `hirelens-frontend/tests/MobileNav.test.tsx` — new (P5-S14)
- `hirelens-frontend/tests/App.redirects.test.tsx` — new (P5-S13)
- Internal-reference updates across `hirelens-frontend/src/` and `hirelens-backend/app/services/email/` — P5-S13 sweep
- `AGENTS.md` — Frontend Routes Table updated (P5-S14)
- `SESSION-STATE.md` — slice pointer, Active Refactor Zones update, Hard Constraints "no new flat routes" reaffirmed (P5-S14)
- `.agent/skills/analytics.md` — add `nav_clicked` and `deprecated_route_hit` (P5-S14)
- `docs/specs/phase-5/12-navigation-restructure.md` — this file (P5-S12 draft, today)
