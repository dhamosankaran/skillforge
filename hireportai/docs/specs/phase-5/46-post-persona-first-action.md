# P5-S22·post-persona-first-action — One-CTA First-Action Page After PersonaPicker

**Status:** Active — shipping this slice
**Owner:** Dhamo
**Created:** 2026-04-19
**Phase:** 5
**Depends on:** Spec #34 (PersonaPicker flow), Spec #35 (HomeDashboard widget catalog)
**Relates to:** Spec #40 (state-aware home), Spec #41 (Interview-Prepper checklist) — both continue to drive the dashboard after the first-action page fires once

## 1. Problem Statement

A user who just completed PersonaPicker lands on `/home` with a widget
grid but no clear next step. The Interview-Prepper checklist (spec #41)
is present but doesn't surface as a primary CTA — it sits inside the
grid beside six other widgets. Career-Climbers and Team Leads have no
equivalent nudge at all. Net effect: first-session bounce rate is
higher than necessary because the user opens the app, sees a
multi-widget dashboard, and can't tell "what do I do first?"

## 2. Goals / Non-Goals

### Goals

- Insert a lightweight **one-CTA** page at `/first-action` between the
  PersonaPicker save and `/home`. Renders once per device, per user.
- Compute the CTA label + destination route from the persona the user
  just picked and, for Interview-Preppers, their target date + company.
- Offer a secondary "Take me to the dashboard instead" escape so the
  page never feels like a forced interstitial.
- Persist the "seen" state in `localStorage` only. No schema change.
  No new User field. No backend endpoint.

### Non-Goals

- **No context capture.** This page does not ask for years of
  experience, focus areas, skill level, or resume upload. Those belong
  to a future onboarding-depth slice if ever.
- **No mission auto-creation.** The Interview-Prepper CTA links to
  `/learn/mission`; the MissionSetup form there already handles
  creation. This page navigates; it does not mutate.
- **No cross-device sync.** localStorage is device-local by design. A
  user who sets up on desktop and opens mobile will see the page once
  more — acceptable given the single CTA is low-friction.
- **No `User.onboarding_completed_at` or `User.first_action_seen_at`
  field.** The AuthUser already has `onboarding_completed: boolean`
  (flipped by the backend when persona is set); overloading that to
  mean "seen first-action" would conflate two concepts. Deliberate
  non-addition — if future work needs cross-device sync, it becomes
  its own slice with a PRD justification.
- **No admin funnel analytics.** The three new PostHog events (§4.4)
  are enough signal to measure bounce vs. click-through without a new
  admin view.

## 3. Solution

### 3.1 Route + chromeless shell

- New route: `/first-action` — wrapped in `ProtectedRoute` +
  `PersonaGate` like every other private route. The gate still sends
  `persona === null` users to `/onboarding/persona`, which satisfies
  AC-7 without any first-action-specific logic.
- `AppShell.CHROMELESS_PATHS` gains `/first-action`. The page renders
  full-screen with no TopNav/MobileNav, matching the PersonaPicker
  pattern.

### 3.2 CTA matrix

| Persona | Condition | Primary CTA label | Route |
|---|---|---|---|
| `interview_prepper` | `interview_target_date` set AND `interview_target_company` set | `Start your {N}-day Mission to {company}` | `/learn/mission` |
| `interview_prepper` | `interview_target_date` set, no company | `Start your {N}-day Mission` | `/learn/mission` |
| `interview_prepper` | no date | `Browse interview prep categories` | `/learn` |
| `career_climber` | any | `Start your first Daily Review` | `/learn/daily` |
| `team_lead` | any | `Browse the card library` | `/learn` |

**Note on `/learn` vs `/learn/categories`:** an earlier draft used
`/learn/categories`. That route does not exist in `src/App.tsx`; the
category browser is `/learn` (rendered by `StudyDashboard`). The spec
uses `/learn` directly — no new route is required.

**`N`** is `Math.max(0, Math.ceil((targetDate - today) / 86400000))`
computed natively. No new date library. A target date in the past
renders as `Start your 0-day Mission`; clamping rather than hiding
keeps the CTA stable in the edge case where a user doesn't update
their target date after interviewing.

### 3.3 Secondary action

Always rendered: `Take me to the dashboard instead` as a subtle text
link under the primary button. Routes to `/home`. Also sets the
`first_action_seen` flag — both paths flip the same bit.

### 3.4 First-view-only persistence

- Key: `localStorage.setItem('first_action_seen', 'true')`.
- Set on both primary-CTA click and secondary-link click, before the
  `navigate(...)`.
- On mount: if `localStorage.getItem('first_action_seen') === 'true'`,
  the page immediately redirects to `/home` (handles the direct-URL
  case from AC-6).
- `PersonaPicker.handleContinue` now branches on the flag: present →
  `/home` (current behavior preserved for returning users), absent →
  `/first-action` (new default for first-session).

### 3.5 PostHog events

Three new events added to `.agent/skills/analytics.md`:

- `first_action_viewed` — `{persona}` — fires once per mount on the
  page. Guarded by a `useRef` idempotency flag so React Strict Mode's
  double-invoked effect does not double-capture (same pattern as
  `home_dashboard_viewed`).
- `first_action_primary_clicked` — `{persona, cta_route}` — fires on
  the primary CTA click before navigation.
- `first_action_secondary_clicked` — `{persona}` — fires on the
  secondary dashboard link click before navigation.

## 4. Acceptance Criteria

- **AC-1.** A user completing PersonaPicker (no `first_action_seen`
  flag) is routed to `/first-action`, NOT `/home`.
- **AC-2.** `/first-action` renders the correct primary-CTA label per
  the §3.2 matrix based on `user.persona`, `interview_target_date`,
  `interview_target_company`.
- **AC-3.** Clicking the primary CTA sets
  `localStorage['first_action_seen'] = 'true'` AND navigates to the
  correct route per the matrix.
- **AC-4.** Clicking the secondary link sets the flag AND navigates
  to `/home`.
- **AC-5.** A user whose `first_action_seen` flag is already set goes
  PersonaPicker → `/home` directly (e.g., a persona-switch scenario
  once that UX lands).
- **AC-6.** Direct navigation to `/first-action` when the flag is
  already set redirects to `/home`.
- **AC-7.** Direct navigation to `/first-action` when
  `user.persona === null` is redirected to `/onboarding/persona` by
  the existing `PersonaGate` (no first-action-specific logic).
- **AC-8.** Interview-Prepper with `interview_target_date` 14 days
  out and `interview_target_company = "Google"` renders
  `Start your 14-day Mission to Google`.
- **AC-9.** Interview-Prepper with no `interview_target_date` renders
  `Browse interview prep categories` and navigates to `/learn`.
- **AC-10.** Zero regression: `PersonaPicker.test.tsx`, `PersonaGate`,
  `HomeDashboard`, widget tests, state-aware widget tests, and the
  Interview-Prepper checklist all continue to pass. The
  existing `PersonaPicker` navigation test is updated (not broken) to
  reflect the new default destination; a second test verifies the
  flag-set shortcut path.
- **AC-11.** `AppShell` hides the nav chrome on `/first-action` so the
  page lands as a full-screen interstitial.

## 5. Test Plan

New test file: `hirelens-frontend/tests/FirstAction.test.tsx` (follows
the mocked-`useAuth` + mocked-`useNavigate` + mocked-`localStorage`
pattern used by `PersonaPicker.test.tsx`).

1. `test_first_action_renders_for_interview_prepper_with_date_and_company` — CTA reads `Start your 14-day Mission to Google` (AC-8).
2. `test_first_action_renders_for_interview_prepper_with_date_no_company` — CTA reads `Start your 14-day Mission`.
3. `test_first_action_renders_for_interview_prepper_without_date` — CTA reads `Browse interview prep categories`, routes to `/learn` (AC-9).
4. `test_first_action_renders_for_career_climber` — CTA reads `Start your first Daily Review`, routes to `/learn/daily`.
5. `test_first_action_renders_for_team_lead` — CTA reads `Browse the card library`, routes to `/learn`.
6. `test_primary_cta_sets_flag_and_navigates` — primary click sets localStorage flag AND calls `navigate` with the matrix route (AC-3).
7. `test_secondary_cta_sets_flag_and_navigates_to_home` — secondary click sets flag AND calls `navigate('/home')` (AC-4).
8. `test_first_action_redirects_to_home_when_flag_set_on_mount` — mount-time redirect path (AC-6).
9. `test_first_action_captures_viewed_event_once` — `first_action_viewed` fires exactly once despite Strict Mode double-invoke.

Plus test updates in `hirelens-frontend/tests/PersonaPicker.test.tsx`:

- Existing test `submits selected persona and navigates to /home with replace:true` → renamed and re-asserted: navigates to `/first-action` when flag absent (this becomes the default case).
- New test: `submits selected persona and navigates to /home when first_action_seen flag is present` (AC-5).

### 5.1 Expected test counts

- BE baseline: 241 passed, 6 deselected. **No backend changes → 241 unchanged.**
- FE baseline: 101 passing across 26 files. After this slice:
  - +9 new tests in `FirstAction.test.tsx` (new file, +1 file)
  - +1 net test in `PersonaPicker.test.tsx` (1 existing updated in place, 1 new added)
  - **FE: 101 + 9 + 1 = 111 passing across 27 files.**

### 5.2 Manual verification

- Clear localStorage, log in, pick Interview-Prepper with target date
  14 days out and `Google`. Expect `/first-action` with `Start your
  14-day Mission to Google`. Click → lands on `/learn/mission`.
- Log out, clear localStorage, log in as Career-Climber. Expect
  `/first-action` with `Start your first Daily Review`.
- Click the secondary link. Expect `/home`. Navigate back to
  `/first-action` manually — expect instant redirect to `/home`.

## 6. Security Note

No backend surface, no new auth dependency, no new endpoint. The page
reads only fields already present on the authenticated user object
(`AuthContext`). The `PersonaGate` redirect and `ProtectedRoute`
wrapper carry the existing auth contract.

localStorage is the correct persistence layer here: the state is
device-local UX bookkeeping, not security-sensitive, and its worst-case
failure mode (user clears storage → sees the CTA once more) is benign.

## 7. Out of Scope

- Context capture at onboarding (YoE, focus areas, target role, resume
  upload).
- Mission auto-creation (user still clicks through the MissionSetup
  form on `/learn/mission`).
- Cross-device sync of the seen flag (would require a new User field
  or a new endpoint — both excluded from this slice).
- Admin analytics funnel view for first-action.
- Adding a "Change persona / reset onboarding" affordance (the
  persona-switch UX is still a separate post-spec slice —
  SESSION-STATE.md "Deferred Hygiene Items").

## 8. Rollout

Pure frontend change. Vercel deploy on push-to-main. Railway (backend)
is a no-op. Every logged-in user — existing and new — will see
`/first-action` once on their next session, because nobody has the
flag yet. Acceptable and intended.

Rollback: `git revert <commit>` restores `PersonaPicker → /home`
direct-navigate behavior. No data cleanup required; the localStorage
key becomes orphaned but benign.

## 9. Files Touched

- `hirelens-frontend/src/pages/FirstAction.tsx` — new
- `hirelens-frontend/src/App.tsx` — new `/first-action` route
- `hirelens-frontend/src/pages/PersonaPicker.tsx` — branch on flag in `handleContinue`
- `hirelens-frontend/src/components/layout/AppShell.tsx` — add `/first-action` to `CHROMELESS_PATHS`
- `hirelens-frontend/tests/FirstAction.test.tsx` — new, 9 tests
- `hirelens-frontend/tests/PersonaPicker.test.tsx` — update existing navigate assertion, add one flag-set test
- `.agent/skills/analytics.md` — add 3 new events
- `AGENTS.md` — add `/first-action` row to the Frontend Routes table; extend the chromeless-paths sentence
- `docs/specs/phase-5/46-post-persona-first-action.md` — this spec
