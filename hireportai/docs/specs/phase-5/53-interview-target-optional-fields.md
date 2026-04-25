# Spec #53 — Interview Target: Optional Fields + Date-Picker Reconciliation

**Status:** Draft — authored 2026-04-22, awaiting CODEX review
**Owner:** Dhamo
**Phase:** 5
**Closes (on implementation):** BACKLOG B-NNN (finding #6), B-NNN+1 (finding #7) — filed by the implementation slice, not this spec.
**Depends on:** Spec #34 (PersonaPicker + HomeDashboard foundations) — this spec amends the §Solution "Interview-Prepper card expansion" contract. Spec #44 (Widget Empty-State Contract) — Countdown + MissionMode affordances follow Rule 3(a).
**Structural template:** Spec #44 (empty-state / affordance shape), Spec #34 (persona-capture contract).

---

## 1. Problem Statement

Two findings from the 2026-04-21 E2E walkthrough converge on the same root cause: the product treats `interview_target_date` as a hard prerequisite for the Interview-Prepper experience, even though P5-S16 already made the column nullable.

### Finding #6 — "Date should be a date picker, not free text"

Confirmed by Step 1 audit: **this is already true on every current capture site.** `PersonaPicker.tsx:170`, `CountdownWidget.tsx:70-85`, and `MissionSetup.tsx:120` all use native HTML5 `<input type="date">`. No free-text date input exists in the live codebase. The finding is carried forward as a codified non-regression invariant — any future persona-edit surface (e.g., the deferred Profile-side editor under E-017) MUST use a date picker, not free text.

### Finding #7 — "Date + company should be optional"

Confirmed partially by audit. **BE is already permissive:** `schemas/user.py:27-28` defaults both `interview_target_date` and `interview_target_company` to `None`; `app/api/v1/routes/users.py:37-38` writes through whatever Pydantic validates; PersonaPicker client already strips empty values at `PersonaPicker.tsx:57-65`. A user who picks `interview_prepper` and leaves both fields blank already persists cleanly.

**The real gap is downstream.** Two surfaces coerce the no-date user:

1. **CountdownWidget Mode 1** (no date) renders an inline date-setter form with copy "Set your interview date to start the countdown." This is the "no-date state" styled as a setup gate — the widget's entire content is a date capture form, pushing the user to fill it in before they get any Interview-Prepper value from the dashboard.
2. **MissionSetup.tsx** (`/learn/mission`) hard-validates date present (`setError('Pick a target date')` at line 57). A broadly-prepping Interview-Prepper who navigates to Mission Mode gets an unsubmittable form — mild but real breakage.

Together these frame "no date" as an incomplete / invalid state rather than a first-class supported state. Users who identify with the Interview-Prepper motivation ("I'm prepping for interviews in general") but don't have a specific interview booked are shown a UI that implies they misfiled themselves. Finding #7's fix is to make no-date a first-class state, not to change the capture surface.

### Why one spec for both findings

They share a single fix-family: **"interview_target_date is optional, and every surface must degrade gracefully when it's null."** Separating them would duplicate the downstream-rendering contract across two specs. R14 admits combined specs when they share scope.

---

## 2. Scope

**In scope.**

- `PersonaPicker.tsx` — helper copy update + codification of "date picker, not free text" as a non-regression invariant.
- `CountdownWidget.tsx` — reframe Mode 1 from "date-setter form" to a lightweight "Add an interview date to unlock countdown" affordance per spec #44 Rule 3(a). The inline date input is retained (it is already a valid CTA) but the wrapper copy and visual weight shift from "required setup step" to "optional upgrade."
- `MissionMode.tsx` — new branch: when persona is `interview_prepper` AND `interview_target_date` is null, render a "Set a date to start a sprint" affordance instead of `MissionSetup`. Affordance links to the persona-edit surface (or to `PersonaPicker` fallback — see §OPEN DECISIONS).
- Telemetry: four new PostHog events covering the unlock-CTA lifecycle + the skip-at-onboarding signal.
- Regression test plan covering no-date render paths at `/home` and `/learn/mission`.

**Out of scope.**

- Schema changes. `interview_target_date` + `interview_target_company` have been nullable since P5-S16 migration `02bf7265b387`.
- New API endpoints. `PATCH /api/v1/users/me/persona` already accepts both fields optional (spec #34 §API Contract).
- **Profile-side persona-edit editor** — tracked as E-017 🔴. The "home CTA" in this spec links to whatever persona-edit path exists when implementation runs; see §OPEN DECISIONS.
- Mission Mode auto-creation from persona data — walkthrough finding #15, deferred.
- Cover-letter / Analysis / Rewrite / Interview Questions surfaces — none consume `interview_target_date` today, verified by grep.
- Persona switching UX — unchanged.
- Backfilling PostHog events for existing users.
- `InterviewTargetWidget` empty-state copy — already fixed in B-017 (commit `d835fb8`).

---

## 3. Locked Decisions

> Inputs to this spec. Not re-debated in the implementation slice.

**LD-1 — Persona model: Option β.** An `interview_prepper` without a date stays as `interview_prepper` persona. `/home` and Mission Mode degrade gracefully. The no-date state is **first-class supported**, not a setup gate. No persona reclassification, no coercive modal, no auto-switch to `career_climber`.

**LD-2 — Date input stays native HTML5 `<input type="date">`.** Audit confirmed no date-picker library is bundled (no `react-day-picker`, `react-datepicker`, `@mui/x-date-pickers`, `date-fns` in `package.json`). Native `<input type="date">` is already the convention across PersonaPicker, CountdownWidget, and MissionSetup — three sites, consistent. Adding a library for this slice is scope expansion with no user-visible benefit; native picker already delivers client-side parse validation, format enforcement, and platform-appropriate UX (calendar grid on desktop, wheel on iOS). If future findings require rich-date features (ranges, recurring, relative offsets), that's a new spec and it starts from the locked native baseline.

**LD-3 — Downstream copy for no-date state is explicit unlock framing.**
- Countdown widget: **"Add an interview date to unlock countdown"** — the word "unlock" signals the no-date state is fine on its own; the countdown is an optional upgrade, not a missing prerequisite.
- Mission Mode: **"Set a date to start a sprint"** — same framing; the sprint is an opt-in upgrade, not the only valid path.
- NO coercive CTA dominates `/home`. The Countdown widget stays the same size; only its internal content changes. All other interview_prepper tiles (InterviewPrepperChecklist, TodaysReview, LastScan, InterviewTarget) render identically for date-present and date-null users.

**LD-4 — Unlock CTA links to the current canonical persona-edit path.** In V1 (this slice's target), that is `/onboarding/persona` — see §OPEN DECISIONS for the `return_to` behaviour question. When E-017's Profile-side editor ships, the implementation slice updates the CTA target in one place. No feature flag; the change is a one-line route swap.

**LD-5 — Optional fields on PersonaPicker stay optional — codify current behaviour.** PersonaPicker's body-construction already strips empty values (`PersonaPicker.tsx:57-65`). This spec adds explicit helper copy signalling the fields are optional and adds regression tests so a future refactor cannot re-require them without tripping a red test.

---

## 4. Acceptance Criteria

All ACs are test-gated (§8 Test Plan maps each AC to a test). No live external dependencies.

- **AC-1 — PersonaPicker saves `interview_prepper` with neither date nor company.** The user picks Interview-Prepper, leaves both expansion fields blank, clicks Continue, and lands on `/first-action` (or `/home` if `first_action_seen`). `PATCH /api/v1/users/me/persona` returns 200 with `interview_target_date: null, interview_target_company: null`. No client-side validation blocks the submit; no required-field warning renders.

- **AC-2 — PersonaPicker date input is a date picker (invariant).** Grep assertion: `grep -n 'type="date"' hirelens-frontend/src/pages/PersonaPicker.tsx` matches exactly one line for the interview-target-date input, and zero `type="text"` uses on any element with a `*date*` id/testid. Regression guard against reintroducing free-text date input.

- **AC-3 — HomeDashboard for no-date interview_prepper renders the unlock affordance in the Countdown slot.** `/home` for a user with `persona === 'interview_prepper' && interview_target_date === null` renders successfully (no error boundary hit, no console.error). The Countdown widget renders the LD-3 copy "Add an interview date to unlock countdown" with a working CTA (date input OR link to persona-edit — see §FRONTEND). No Countdown ring renders.

- **AC-4 — MissionMode for no-date interview_prepper renders the set-a-date affordance.** `/learn/mission` for the same user renders an LD-3-copy ("Set a date to start a sprint") affordance **instead of** `MissionSetup`. The affordance links to the persona-edit surface. Mission is NOT auto-created. `MissionSetup` is NOT mounted (its category fetch does not fire). The existing `phase === 'completed'` / `phase === 'setup'` / `phase === 'loading'` / `phase === 'active'` branches are preserved for all other cases.

- **AC-5 — Non-countdown / non-Mission tiles render identically for date-present and date-null.** For a no-date interview_prepper, `TodaysReviewWidget`, `LastScanWidget`, `InterviewTargetWidget`, `StateAwareWidgets`, and `InterviewPrepperChecklist` render the same DOM (modulo data differences unrelated to date state) as they do for a date-present user. Asserted by render-parity test (mount both fixtures, diff the relevant subtrees).

- **AC-6 — Date-present regression guard.** An existing interview_prepper with a saved date continues to see the Countdown ring (Mode 2 of CountdownWidget) and, on `/learn/mission` with no active mission, sees `MissionSetup` as before. No change to the date-present path.

- **AC-7 — Late-adding a date upgrades the experience without persona re-pick.** Flow: date-null interview_prepper clicks the unlock CTA → reaches persona-edit → sets a date → `PATCH /api/v1/users/me/persona` returns 200 with the new date → on return to `/home`, Countdown renders Mode 2 (ring); on `/learn/mission`, MissionSetup renders. No persona field is touched on the update; no re-selection required.

---

## 5. Data Model

**No changes.** Both columns already exist and are nullable:

| Column | Type | Nullable | Since |
|--------|------|----------|-------|
| `users.interview_target_date` | `Date` | yes | P5-S16 (migration `02bf7265b387`) |
| `users.interview_target_company` | `String(100)` | yes | P5-S16 (migration `02bf7265b387`) |

No Alembic migration in the implementation slice.

---

## 6. API Contract

**No changes.** `PATCH /api/v1/users/me/persona` already accepts both fields optional per spec #34 §API Contract, and `schemas/user.py::PersonaUpdateRequest` already defaults both to `None`.

The implementation slice adds **non-regression tests** verifying:

- `POST` body `{"persona": "interview_prepper"}` with neither date nor company → HTTP 200, response has `interview_target_date: null`, `interview_target_company: null`.
- `POST` body with malformed date string (`"not-a-date"`) → HTTP 422 with `loc` pointing at `interview_target_date`.
- `POST` body with 101-char company → HTTP 422 (already covered by existing `test_interview_target_company_max_100_chars` in `tests/test_users_persona.py` — re-asserted as a sanity check, no new test needed).

---

## 7. Frontend

### 7.1 PersonaPicker (`src/pages/PersonaPicker.tsx`)

Minimal copy update. The expansion block at lines 160-199 already captures both fields optionally; the implementation slice only updates the helper text to explicitly signal "no date is fine" and adds a skip-signal PostHog event (§9).

| Element | Current | Proposed |
|---|---|---|
| Date helper copy | (none — only a label "Interview date") | Add helper: `"Optional — leave blank if you're prepping broadly."` |
| Company helper copy | `"Optional — e.g. Google in 14 days."` (line 195) | Unchanged. |
| Submit gate | Disabled until persona is selected (line 216). | Unchanged. No new required-field gate. |

Add a PostHog call-site in `handleContinue` (line 51-81) that fires `interview_target_date_skipped` with `{source: 'onboarding'}` when `selected === 'interview_prepper' && !targetDate`. Fires alongside the existing `persona_selected` event; must NOT block or delay submission.

### 7.2 CountdownWidget (`src/components/home/widgets/CountdownWidget.tsx`)

Refactor Mode 1 from "date-setter form" to "unlock affordance." The existing inline date-input mechanic is preserved so a user who wants to set a date immediately can still do so without a second navigation — but the widget's *framing* shifts.

Concrete shape (implementation-slice wires the exact JSX):

- `DashboardWidget` title stays `"Countdown"`.
- Body renders: (a) LD-3 unlock copy as primary text, (b) the existing `<input type="date">` + Save button as a secondary affordance, (c) a secondary `"Update later"` dismiss-style link that navigates to the persona-edit surface (LD-4 target). Visual weight: primary copy foregrounded, input de-emphasised (smaller, with "or" connector).
- On successful date save (the existing `updatePersona` call path), fire the existing `persona_selected` analog is NOT appropriate; fire new event `interview_target_date_added` with `{source: 'home_cta'}`.
- Mode 2 (date set) is unchanged.

Alternatively the implementation slice may decide the inline input is no longer worth its UI weight and drop it in favour of a pure "link to persona-edit" affordance. That's a tactical call and does not change acceptance — AC-3 accepts either shape as long as the LD-3 copy + a working CTA are present.

### 7.3 MissionMode (`src/pages/MissionMode.tsx`)

Add a new phase discriminator **above** the existing `phase === 'setup'` branch (line 378). When:
- `user.persona === 'interview_prepper'`, AND
- `user.interview_target_date` is null, AND
- `phase === 'setup'` (no active mission — existing predicate),

…render a new `<MissionDateGate>` affordance instead of `<MissionSetup>`. Shape: centered card with LD-3 copy "Set a date to start a sprint," a button labelled "Add interview date" that navigates to the persona-edit surface (LD-4 target), and a secondary "Browse categories instead" link to `/learn`. Fires `countdown_unlock_cta_shown` with `{surface: 'mission_mode'}` on mount and `countdown_unlock_cta_clicked` with `{surface: 'mission_mode'}` on click.

The existing `phase === 'setup'` MissionSetup render is preserved for `career_climber` / `team_lead` personas and for `interview_prepper` users who DO have a date.

### 7.4 Unlock CTA: PersonaPicker return trip (LD-4)

When the user reaches `/onboarding/persona` via the unlock CTA (Countdown or MissionMode), PersonaPicker must:

1. Pre-fill the persona card selection (`interview_prepper` — already persisted).
2. Expand the extras block automatically.
3. On save, navigate back to the origin (`/home` or `/learn/mission`) — not to `/first-action`.

PersonaPicker's `handleContinue` currently hard-codes `/home` vs `/first-action` via `first_action_seen`. The implementation slice adds a `return_to` URL-param read (URL-encoded; whitelist-checked to prevent open-redirect), falling back to the existing logic. Both call sites (CountdownWidget, MissionMode) append `?return_to=<encoded-path>`. See §OPEN DECISIONS for whether a dedicated Profile-side editor (E-017) is a gating question.

### 7.5 FirstAction (existing — no change)

`FirstAction.tsx:34-44` already handles the null-date case: `if (!interviewTargetDate) return { label: 'Browse interview prep categories', route: '/learn' }`. No edit. This spec validates the existing behaviour via AC-5 render-parity.

---

## 8. Test Plan

### 8.1 Backend

Extend `tests/test_users_persona.py`:

| Test | AC | Notes |
|---|---|---|
| `test_persona_interview_prepper_without_date_or_company` (**new**) | AC-1 | POST `/api/v1/users/me/persona` body `{"persona": "interview_prepper"}`. Assert 200, `persona == "interview_prepper"`, `interview_target_date is None`, `interview_target_company is None`, `onboarding_completed is True`. |
| `test_persona_interview_prepper_invalid_date_rejected` (**new**) | AC-1 / API §6 | POST body `{"persona": "interview_prepper", "interview_target_date": "not-a-date"}` → HTTP 422 with loc containing `interview_target_date`. |

No new BE routes, no new services, no migration. Existing tests (`test_persona_switch_preserves_onboarding_flag`, `test_empty_company_string_coerces_to_none`, `test_interview_target_company_max_100_chars`) already cover adjacent invariants and stay green.

### 8.2 Frontend

Extend existing test files; no new files needed.

| Test | AC | File |
|---|---|---|
| `persona_picker_saves_interview_prepper_without_date_or_company` (**new**) | AC-1 | `tests/PersonaPicker.test.tsx` |
| `persona_picker_date_input_type_is_date_not_text` (**new**, grep-style) | AC-2 | `tests/PersonaPicker.test.tsx` (query the input by testid, assert `.getAttribute('type') === 'date'`) |
| `home_no_date_interview_prepper_renders_countdown_unlock_affordance` (**new**) | AC-3 | `tests/home/widgets/CountdownWidget.test.tsx` — fixture with `date=null`; assert LD-3 copy present; assert no Countdown ring SVG |
| `home_no_date_interview_prepper_non_countdown_tiles_match_date_present` (**new**) | AC-5 | `tests/HomeDashboard.test.tsx` — render two fixtures, diff widget testids for the non-Countdown subtree |
| `mission_mode_no_date_interview_prepper_renders_date_gate_not_setup` (**new**) | AC-4 | `tests/pages/MissionMode.test.tsx` (new file OR extend existing) — fixture with `persona='interview_prepper'`, `interview_target_date=null`, `fetchActiveMission` returns null; assert `MissionDateGate` testid present, `MissionSetup` testid absent |
| `mission_mode_date_present_interview_prepper_still_renders_setup` (**new**) | AC-6 | Same file; fixture with a date present; assert MissionSetup testid present, MissionDateGate absent |
| `mission_mode_other_personas_still_render_setup` (**new**) | AC-6 | Same file; `career_climber` + `team_lead` fixtures; assert MissionSetup present regardless of date value |
| `countdown_late_date_add_upgrades_to_ring_mode` (**new**) | AC-7 | `tests/home/widgets/CountdownWidget.test.tsx` — mount with null date; simulate `updatePersona` success → re-render with date-present user; assert ring renders, unlock copy gone |

Existing tests in `tests/HomeDashboard.test.tsx` and `tests/home/widgets/InterviewTargetWidget.test.tsx` stay green; no modification needed.

### 8.3 Smoke / manual

Implementation-slice author runs one manual smoke at end-of-slice:

1. Fresh signup → PersonaPicker → select Interview-Prepper → leave both fields blank → Continue → FirstAction → Home.
2. Confirm `/home` renders without console errors; Countdown shows unlock affordance.
3. Navigate `/learn/mission`; confirm date-gate affordance renders.
4. Click unlock → PersonaPicker pre-fills → enter a date → save → auto-returns to origin.
5. Confirm `/home` Countdown now shows ring; `/learn/mission` now shows MissionSetup.

No production smoke required — this is a render-contract change, not an integration change.

---

## 9. Telemetry

**New PostHog events.** Added to `.agent/skills/analytics.md` in the implementation slice.

| Event | Surface | Properties | Fires when |
|---|---|---|---|
| `interview_target_date_added` | FE | `{source: 'onboarding' \| 'persona_edit' \| 'home_cta'}` | A user successfully saves a date via any capture surface. `source` disambiguates which surface triggered the save. |
| `interview_target_date_skipped` | FE | `{source: 'onboarding'}` | PersonaPicker `handleContinue` fires this when `selected === 'interview_prepper' && !targetDate`. One-shot per Continue click. |
| `countdown_unlock_cta_shown` | FE | `{surface: 'home_countdown' \| 'mission_mode'}` | On mount of either unlock affordance. Fires once per mount per surface, idempotent via `useEffect` + ref (same pattern as `paywall_hit`). |
| `countdown_unlock_cta_clicked` | FE | `{surface: 'home_countdown' \| 'mission_mode'}` | On click of the primary unlock button / link. |

**Existing events unchanged:** `persona_picker_shown`, `persona_selected`, `home_dashboard_viewed`, `first_action_viewed`.

**Operational question:** the implementation-slice author should add a PostHog cohort filter note to `analytics.md` — "interview_preppers without a date" is now a first-class segment; dashboards that break down by persona should split it further where relevant. Non-blocking; tracked as a nice-to-have in the `.agent/skills/analytics.md` update.

---

## 10. Migration / Rollout Notes

- **DB:** no migration.
- **BE:** no code change required; only additive tests.
- **FE hard-cut:** all changes land in one commit. No feature flag (LD-3 — the new copy is strictly a UX improvement; rollback is `git revert`).
- **User-facing impact for existing date-present users:** zero (AC-6 regression guard).
- **User-facing impact for existing date-null users:** Countdown widget copy changes from "Set your interview date to start the countdown" to LD-3 "Add an interview date to unlock countdown"; MissionMode renders the new date-gate instead of the unsubmittable MissionSetup. Both are strict improvements; no user-facing negative delta.
- **CODE-REALITY regen:** required if `CountdownWidget.tsx` or `MissionMode.tsx` change their top-level shape (new component mount). Implementation slice decides at end-of-slice.

---

## 11. Transfers and Non-Transfers from Adjacent Specs

| From | Transfers? | Where it lands here |
|---|---|---|
| Spec #34 — PersonaPicker capture contract (three personas, interview_prepper expansion) | **Yes** | §7.1 — amended with helper-copy update; shape is unchanged. |
| Spec #34 — "fields are accepted for all personas" server permissive-ness | **Yes** | §6 — unchanged; re-asserted via AC-1 test. |
| Spec #44 — Widget Empty-State Contract Rule 3(a) "render a CTA" | **Yes** | §7.2 — Countdown unlock affordance IS a Rule 3(a) CTA. |
| Spec #44 — Rule 3(b) "hide the widget entirely" | **No** | LD-3 explicitly rejects hiding Countdown — the affordance is the feature. |
| Spec #46 — FirstAction computeCta null-date branch | **Yes** | §7.5 — unchanged; validates via AC-5. |
| Spec #40 — state-aware priority slot | **No** | State-aware widgets are orthogonal; no `no_date` state needed. |

---

## 12. Open Decisions

**OD-1 — Profile-side editor dependency.** The unlock CTA needs a route that can edit `interview_target_date` post-onboarding. V1 per LD-4 points at `/onboarding/persona` with a `return_to` param. **But:** `/onboarding/persona` is PersonaGate's redirect target for null-persona users; PersonaGate does not currently redirect users who already have a persona (`user.persona !== null` passes through — spec #34 §PersonaGate). So a direct `navigate('/onboarding/persona')` works today, but the UX is arguably weird (a "picker" labelled for new users, edited by existing users). E-017 🔴 exists specifically for a Profile-side editor. **Decision needed from Dhamo before implementation:** (a) ship V1 pointing at PersonaPicker (ugly but functional; refactor to Profile when E-017 lands), (b) block this spec's impl behind E-017, (c) add a cheap "persona edit modal" affordance to Profile as part of this slice (expanding scope). Recommended: **(a)** — keeps the slice MEDIUM and the E-017 handoff clean.

**OD-2 — Countdown Mode 1 inline date-setter retention.** Current CountdownWidget Mode 1 (`date === null`) inlines a full `<input type="date">` + Save button. §7.2 proposes retaining it as a secondary affordance beneath the primary LD-3 copy, but the implementation author may decide the UI weight is not worth it and drop the inline input in favour of a pure "link to persona-edit" CTA. Both shapes satisfy AC-3. **Decision needed:** is the retained inline input worth the visual complexity, or prefer the simpler link-only affordance? Recommended: **link-only** for consistency with MissionMode's affordance shape (§7.3) — two surfaces with divergent interaction models for the same no-date state is inconsistency we'd regret.

**OD-3 — `return_to` whitelist.** §7.4 adds a `return_to` URL-param read to PersonaPicker. To prevent open-redirect, the implementation MUST whitelist — candidate list: `/home`, `/learn`, `/learn/mission`, `/prep/analyze`, `/prep/results`, `/prep/interview`, `/prep/rewrite`, `/prep/tracker`, `/profile`. **Decision needed:** accept the implementation slice defining the whitelist inline, or pre-lock it here? Recommended: **accept inline** — the concrete list is a matter for the code review, not the spec. R19 conflict possible if the whitelist misses a legit path; implementation flags.

---

## 13. R15

**B-NNN (finding #6) + B-NNN+1 (finding #7) are NOT closed by this spec.** Spec is the design contract; the implementation slice files both BACKLOG rows (B-NNN = "Interview-target date input invariant — must stay a picker, never regress to free-text" + B-NNN+1 = "Interview-target date + company optional end-to-end; downstream surfaces must degrade") and closes both on impl-slice merge per CLAUDE.md R15.

---

## 14. Out-of-Spec Follow-Ups

- **E-017 — Profile-side persona editor.** Unblocks LD-4's canonical edit path. This spec's LD-4 points at PersonaPicker in V1 per OD-1 recommended; when E-017 ships, the unlock CTAs (CountdownWidget §7.2, MissionMode §7.3) re-target to the Profile editor in one line. Tracked separately.
- **Walkthrough finding #15 — Mission auto-creation from persona.** Out of scope here. If revisited, it interacts with LD-1 β (first-class no-date state) — an auto-created mission would collapse the no-date state into an auto-date state, which is a different UX direction. Mission-auto-create needs its own spec.
- **"Add a date later" persona-edit UX telemetry.** `interview_target_date_added` with `source='persona_edit'` captures this once E-017 ships. Dashboards for persona-edit conversion rate land in E-017's scope.
- **Rich-date affordances** (relative offsets like "in 2 weeks", recurring, ranges). Not needed for V1. Future spec if telemetry motivates.

---

## Supersession (2026-04-25)

LD-3 / OD-2 link-only affordance is superseded for the home-countdown surface only. `/home` Countdown widget Mode 1 now opens an inline modal (see B-037, component `InterviewDateModal`). MissionDateGate retains the link-only affordance — unchanged.
