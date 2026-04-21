# P5-S15 — PersonaPicker + HomeDashboard Foundations

**Status:** Shipped
**Owner:** Dhamo
**Created:** 2026-04-17
**Phase:** 5D (persona-aware surface)
**Depends on:** P5-S13 (routes), P5-S14 (TopNav / MobileNav / AppShell)
**Downstream slices:** P5-S16 (schema + API + S16-AMEND `interview_target_company`), P5-S17 (PersonaPicker page + PersonaGate + AppShell hide-list), P5-S18 (HomeDashboard + widget catalog), P5-S18b (state-aware dashboard — v2.2 patch), P5-S18c (Interview-Prepper checklist — v2.2 patch), P5-S19 (existing-user migration)
**Related resolved decision:** SESSION-STATE.md → Resolved Decisions → **Decision 1 (persona switch is full-page reroute, 2026-04-17)**

## Problem

Post-P5-S13, authenticated users land on `/home`, which renders `HomeDashboardPlaceholder`. The surface is identical for every user regardless of intent. Per `docs/prd.md §1.3`, the product serves distinct personas with distinct primary needs:

- **Interview-Prepper** — "I have a Google interview in 14 days"
- **Career-Climber** — "I want to stay sharp and get promoted"
- **Team Lead** — "My team needs to learn agentic AI patterns"

These intents diverge sharply in IA. A single home surface cannot serve all three without becoming a feature-dump that serves none. Downstream Phase 5D slices (P5-S18 widgets, P5-S18b state-awareness, P5-S18c Interview-Prepper checklist) all key off `user.persona`, so a reliable capture step is a prerequisite for the rest of 5D.

### Current state

- `users.persona` column already exists (`String(20)`, nullable — see `app/models/user.py:20`) but nothing forces a capture. Existing `PATCH /api/v1/auth/persona` and `PATCH /api/v1/auth/onboarding` endpoints write to it but are not route-gated, so users can reach `/home` with `persona = NULL`.
- The existing enum (`VALID_PERSONAS` in `app/api/v1/routes/auth.py`) uses `("interview", "climber", "team")` — short strings that do not match the descriptive snake_case values this spec introduces. This is a breaking-but-safe change in pre-production; the P5-S16 migration rewrites any existing row to the new set.

### Why full-page, not modal

Resolved in **SESSION-STATE Decision 1 (2026-04-17)**. Summary of the rationale, reproduced here so the spec is self-contained:

- New-user flow lands fresh post-OAuth — there is no page behind a modal worth seeing.
- Existing-user migration UX (P5-S19) fits better as a full page with a top banner than as a modal with a banner-header.
- `PersonaGate` becomes a clean `<Navigate to="/onboarding/persona" replace />` — route-based gating is simpler to test than render-based overlay.
- Three fields on the surface (persona + `interview_target_date` + `interview_target_company`) argue for a page, not a modal.
- Full-screen modal on mobile ≈ full page anyway, so the pattern matters only on desktop, where page wins.

## Solution

A mandatory, non-dismissible **PersonaPicker** page at `/onboarding/persona`, followed by a persona-aware **HomeDashboard** at `/home`. Backend gains a `PATCH /api/v1/users/me/persona` endpoint and two new columns (`interview_target_date`, `interview_target_company`). Frontend gains a `PersonaGate` component that redirects null-persona users to the picker on every protected-route visit.

### PersonaPicker (`/onboarding/persona`)

- Full-page route. Nav chrome (`TopNav` on desktop, `MobileNav` on mobile) hidden via the AppShell hide-list.
- No "Skip" button. No close affordance. Cannot dismiss.
- Renders one card per persona. Card names and enum values drawn from `docs/prd.md §1.3`. Each card shows:
  - Persona name (label from PRD).
  - One-line descriptor (the "Primary Need" quote from the PRD table).
  - An illustrative icon.
- Selecting a card highlights it (active border via `border-border-accent`, `accent-primary` label per `.agent/skills/design-system.md`). No hardcoded hex.
- **Interview-Prepper card expands on selection** to reveal two optional fields:
  - `interview_target_date` — native `<input type="date">` styled per design tokens. Optional.
  - `interview_target_company` — single-line text input, `maxLength={100}`, live character counter. Optional.
  - Helper copy: "Optional — e.g. Google in 14 days."
- Other persona cards do **not** show expansion fields. They submit with only the persona value.
- **Continue** button at the page bottom — disabled until a persona is selected; enabled as soon as one is chosen. Click calls `PATCH /api/v1/users/me/persona` then `navigate("/home", { replace: true })`. On API error, surface an inline error message; keep selection state intact.

### HomeDashboard (`/home`)

- Reads `user.persona` from the auth context (already loaded via `/auth/me`; no extra fetch).
- Renders one of **three render modes, one per persona** (Interview-Prepper, Career-Climber, Team Lead). Each mode renders a distinguishable marker (`data-testid="home-mode-<persona>"`) so AC-5 can assert render-mode branching without depending on widget content.
- If `user.persona === null` (shouldn't happen with `PersonaGate` in place, but defensive): redirect to `/onboarding/persona`.

**Widget catalog per persona is explicitly out of scope for this spec.** P5-S18 owns the widget inventory, ordering, and empty-state behaviour. This spec commits only to the render-mode branching structure.

### PersonaGate (implemented in P5-S17)

Wraps the protected-route subtree in `src/App.tsx`. Pseudocode:

```tsx
function PersonaGate({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const EXEMPT = ["/", "/login", "/onboarding/persona"];
  if (!user) return children;                               // higher-level auth guard handles unauth
  if (user.persona !== null) return children;               // already picked — pass through
  if (EXEMPT.includes(pathname)) return children;           // avoid redirect loop
  return <Navigate to="/onboarding/persona" replace />;
}
```

Ordering in `App.tsx`: `PersonaGate` sits **inside** the auth guard (so unauthenticated users go to `/login`, not `/onboarding/persona`) and **outside** the route components (so the redirect fires before page code runs).

## Data Model

Schema changes live in the Alembic migration created by **P5-S16**. `hirelens-backend/app/models/user.py`:

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `persona` | `String(20)` | yes | **Already declared** on the model. This spec starts *writing* to it and narrows the allowed values. The P5-S16 migration rewrites any existing `("interview", "climber", "team")` row to the new `("interview_prepper", "career_climber", "team_lead")` set. |
| `interview_target_date` | `Date` | yes | Renamed from legacy `target_date` in the P5-S16 migration. Type narrowed from `DateTime` to `Date`. |
| `interview_target_company` | `String(100)` | yes | Renamed from legacy `target_company` in the P5-S16 migration. Length cap narrowed from 255 to 100 (P5-S16 must truncate any existing value longer than 100 chars — pre-prod expected to be non-issue). |

`PersonaEnum` (new, in `app/schemas/user.py`) — string-based Python enum shared by request/response schemas. Values use `snake_case` per CLAUDE.md §Rule 8:

| Enum value | Display label (from PRD §1.3) |
|------------|-------------------------------|
| `interview_prepper` | Interview-Prepper |
| `career_climber` | Career-Climber |
| `team_lead` | Team Lead |

Persona storage stays as `String(20)` (not a PostgreSQL enum type) so adding a value later is a trivial migration. Validation lives in the Pydantic layer.

The legacy `target_company` (`String(255)`, nullable) and `target_date` (`DateTime`, nullable) columns — written by the now-deleted `/auth/onboarding` endpoint — are renamed and retyped in the P5-S16 migration:

- `target_company` → `interview_target_company` (`String(255)` → `String(100)`, via `op.alter_column`).
- `target_date` → `interview_target_date` (`DateTime` → `Date`, via `op.alter_column`).

Alembic `alter_column` preserves existing row data. P5-S16 must run a pre-migration diagnostic (`SELECT COUNT(*) FROM users WHERE target_company IS NOT NULL OR target_date IS NOT NULL`) to confirm the row count before the migration runs. Pre-production is expected to be zero, but the check is cheap.

## API Contract

### `PATCH /api/v1/users/me/persona` (new in P5-S16)

- **Auth:** required (`Depends(get_current_user)` per CLAUDE.md §Rule 3).
- **Rate limit:** `10/minute` per user, matching other mutating auth-adjacent endpoints (`slowapi`).
- **Request body** (Pydantic `PersonaUpdateRequest`):
  ```json
  {
    "persona": "interview_prepper",
    "interview_target_date": "2026-05-01",
    "interview_target_company": "Google"
  }
  ```
- **Validation:**
  - `persona` — required, must be a `PersonaEnum` value → else HTTP 422.
  - `interview_target_date` — optional; Pydantic `date` (ISO `YYYY-MM-DD`); no range check (past dates allowed — user's choice, we don't enforce "future").
  - `interview_target_company` — optional; trimmed; `max_length=100`; empty string after trim coerced to `None`.
  - Date + company fields are accepted for **all** personas (not enforced Interview-Prepper-only on the server). The UI only surfaces them for Interview-Prepper; the server is permissive so a future persona switch can preserve already-typed context without a second round trip.
- **Side effects:** update `users.persona`, `users.interview_target_date`, `users.interview_target_company`. If previous `persona` was `NULL`, also set `users.onboarding_completed = True` to keep the legacy column coherent (cleanup deferred to Phase 6).
- **Response:** `200` with the updated `UserRead` body (same shape as `GET /api/v1/auth/me`, minus the `subscription` subtree — callers refresh that via their existing `/auth/me` flow).

### `GET /api/v1/auth/me` (existing — extended, not replaced)

- Already returns `persona`, `target_company`, `target_date`, `onboarding_completed` (see `app/api/v1/routes/auth.py`).
- After this spec: `_user_dict` serialiser extends the response with `interview_target_date` and `interview_target_company`.
- **Schema-change impact:** additive only (two new nullable fields). No breaking change for existing consumers. Frontend `services/api.ts` `User` type gains the new fields.
- **Path rename** `/auth/me` → `/users/me` is **out of scope** for this spec (touches many frontend callers — Phase 6 cleanup).

### Legacy endpoints to remove in P5-S16

- `PATCH /api/v1/auth/onboarding` — folded into the new `/users/me/persona`.
- `PATCH /api/v1/auth/persona` — folded into the new `/users/me/persona`.

Pre-production; no user traffic lost. Removal in the same PR that adds the new endpoint.

## Route + Gating

### New frontend route

| Path | Component | Access | Slice |
|------|-----------|--------|-------|
| `/onboarding/persona` | `PersonaPicker` | Protected (auth required) | P5-S17 |

The existing `/onboarding` route (gap-to-card mapping) is unrelated and unchanged. `/onboarding/persona` is a sibling path, not a nested one.

### AppShell nav-chrome hide list

Update `src/components/layout/AppShell.tsx` hide list (per P5-S14):

- **Before:** `/`, `/login`, `/pricing`
- **After:** `/`, `/login`, `/pricing`, `/onboarding/persona`

### PersonaGate placement in `src/App.tsx` (P5-S17)

Wrap the protected-route subtree. See pseudocode under §Solution. Exempt paths (`/`, `/login`, `/onboarding/persona`) bypass the gate to avoid redirect loops.

### Post-submission behaviour

After a successful `PATCH /api/v1/users/me/persona`:

1. Update the auth-context user object with the new persona + interview fields (avoids a refetch).
2. `navigate("/home", { replace: true })` — `replace` so the picker is not in the back-button history (prevents a stale re-submit).

## Acceptance Criteria

- **AC-1** — Unauthenticated user visiting `/onboarding/persona` redirects to `/login`. The existing auth guard enforces this; `PersonaGate` is a no-op for unauthenticated users. Verified by a Vitest test that mounts the app in `MemoryRouter` at `/onboarding/persona` with `user === null` and asserts the router lands on `/login`.
- **AC-2** — Authenticated user with `user.persona === null` visiting any protected path other than `/onboarding/persona`, `/login`, or `/` redirects to `/onboarding/persona`. Verified by a parameterised Vitest test driving `MemoryRouter` through `/home`, `/learn`, `/learn/daily`, `/prep/analyze`, `/profile` and asserting redirect.
- **AC-3** — Authenticated user with `user.persona !== null` is never redirected to `/onboarding/persona`. Verified by the inverse Vitest case across the same five paths as AC-2 with `user.persona = "career_climber"`.
- **AC-3b** — Selecting the Interview-Prepper card expands the card to reveal the `interview_target_date` picker and `interview_target_company` text input (optional, `maxLength={100}`, live character counter). Selecting Career-Climber or Team Lead does **not** reveal those inputs. Verified by a Vitest test that clicks each card and asserts field visibility.
- **AC-4** — The **Continue** button is disabled on initial render (no persona selected); becomes enabled on selection; click calls `PATCH /api/v1/users/me/persona` with the chosen persona (plus optional Interview-Prepper fields); on `2xx`, navigates to `/home` with `replace: true`. Verified by a Vitest test with a mocked API client.
- **AC-5** — `/home` renders a persona-specific widget surface corresponding to `user.persona`. Each persona branches to a distinguishable render mode (assertable via `data-testid="home-mode-<persona>"`). **Widget content is deferred to P5-S18** — this AC only requires the render-mode branching to be in place.
- **AC-6** — Nav chrome (`TopNav`, `MobileNav`) is **not rendered** on `/onboarding/persona`. Verified by a Vitest test that mounts `<AppShell>` at `/onboarding/persona` and asserts `queryByTestId("top-nav")` and `queryByTestId("mobile-nav")` both return `null`. Piggybacks on the AppShell hide-list test pattern from P5-S14.
- **AC-7** — Existing users with `persona === NULL` (pre-migration or backfill state) see the picker on their next authenticated navigation. End-to-end verification owned by P5-S19. This spec only requires that `PersonaGate`'s redirect logic fires for `persona === null` regardless of `onboarding_completed`'s value (covers the case where a legacy user completed `/auth/onboarding` but ends up with `persona === null` after the P5-S16 enum-value migration).

## Test Plan

### Backend (P5-S16)

New file `hirelens-backend/tests/test_users_persona.py`:

1. `test_set_persona` — authenticated PATCH with `{ persona: "career_climber" }` returns 200; DB row shows `persona = "career_climber"`, `onboarding_completed = True`.
2. `test_set_persona_with_date` — Interview-Prepper + `interview_target_date: "2026-05-01"` persists the date.
3. `test_set_persona_with_company` — Interview-Prepper + `interview_target_company: "Google"` persists the value.
4. `test_company_max_length_enforced` — 101-char company string → HTTP 422 with field-specific error.
5. `test_persona_enum_rejects_invalid` — `persona: "not_a_real_persona"` → HTTP 422.
6. `test_auth_required_on_persona_patch` — unauthenticated PATCH → HTTP 401.

**Backend minimum:** 5 new cases (target from slice prompt). Delivered: 6.

### Frontend (P5-S17)

New file `hirelens-frontend/tests/PersonaPicker.test.tsx`:

1. Renders one card per PRD persona.
2. `Continue` is disabled on mount.
3. Selecting a card enables `Continue`.
4. Selecting the Interview-Prepper card reveals the date picker + company input.
5. Selecting Career-Climber or Team Lead does **not** reveal those inputs.
6. `Continue` click calls the mocked `PATCH /api/v1/users/me/persona` with the right body and navigates to `/home` with `replace: true`.

New file `hirelens-frontend/tests/PersonaGate.test.tsx`:

7. `persona === null` at `/home` → redirects to `/onboarding/persona`.
8. `persona !== null` at `/home` → renders the route (no redirect).
9. `persona === null` at `/login`, `/`, `/onboarding/persona` → no redirect (exempt paths).

**Frontend minimum:** 8 new cases (target from slice prompt). Delivered: 9.

### Running test-count target (through S16–S19)

Current baseline (SESSION-STATE §Last Completed Slice): **27 frontend**, **174 backend unit**. After S16 + S17 ship: **≥ 36 frontend** (27 + 9), **≥ 180 backend** (174 + 6). Additional tests in S18 / S18b / S18c / S19 build on this baseline.

## Files Touched (planned — no code in this slice)

### Backend (P5-S16)

- `hirelens-backend/app/models/user.py` — add `interview_target_date` and `interview_target_company`; narrow `persona` to `PersonaEnum` in the Pydantic layer (column type stays `String(20)`).
- `hirelens-backend/alembic/versions/<new>_persona_and_interview_targets.py` — new migration: (1) renames `target_company` → `interview_target_company` (truncate to `String(100)`); (2) renames `target_date` → `interview_target_date` (cast `DateTime` → `Date`); (3) migrates existing `persona` values from legacy `('interview', 'climber', 'team')` to `('interview_prepper', 'career_climber', 'team_lead')`. Pre-flight: run `SELECT COUNT(*) FROM users WHERE target_company IS NOT NULL OR target_date IS NOT NULL` to confirm expected-zero row count before running the migration.
- `hirelens-backend/app/schemas/user.py` — add `PersonaEnum`, `PersonaUpdateRequest`; extend `UserRead` to include the two new fields.
- `hirelens-backend/app/api/v1/routes/users.py` — **new file**; `PATCH /me/persona` handler.
- `hirelens-backend/app/api/v1/routes/auth.py` — delete `/auth/onboarding` and `/auth/persona` handlers + their request models + `VALID_PERSONAS`; update `_user_dict` to include the two new fields.
- `hirelens-backend/app/main.py` — register the new users router at prefix `/api/v1/users`.
- `hirelens-backend/tests/test_users_persona.py` — new.

### Frontend (P5-S17)

- `hirelens-frontend/src/pages/PersonaPicker.tsx` — **new**.
- `hirelens-frontend/src/components/PersonaGate.tsx` — **new**.
- `hirelens-frontend/src/components/layout/AppShell.tsx` — add `/onboarding/persona` to the nav-chrome hide list.
- `hirelens-frontend/src/App.tsx` — add `/onboarding/persona` route; wrap protected subtree in `<PersonaGate>`.
- `hirelens-frontend/src/services/api.ts` — extend `User` type with the new fields; add `updatePersona(body)` wrapper around `PATCH /users/me/persona`.
- `hirelens-frontend/src/types/` (or equivalent) — add `Persona` type literal.
- `hirelens-frontend/tests/PersonaPicker.test.tsx` — new.
- `hirelens-frontend/tests/PersonaGate.test.tsx` — new.

### Frontend (P5-S18 — widget catalog owned by that spec)

- `hirelens-frontend/src/pages/HomeDashboard.tsx` — replaces `HomeDashboardPlaceholder` in `App.tsx`.
- `hirelens-frontend/src/pages/HomeDashboardPlaceholder.tsx` — delete.
- `hirelens-frontend/tests/HomeDashboard.test.tsx` — new.

### Docs + state

- `AGENTS.md` — Frontend Routes Table: replace `HomeDashboardPlaceholder` row with `HomeDashboard`; add `/onboarding/persona` row; Models table entry for `User` updated with new columns.
- `SESSION-STATE.md` — end-of-slice update per §Update Protocol.
- `.agent/skills/analytics.md` — add the three new events (see §Analytics) when P5-S17 / P5-S18 ship.

## Out of Scope

- Building `PersonaPicker`, `PersonaGate`, or `HomeDashboard` — this spec defines the shape; P5-S17 (picker + gate) and P5-S18 (dashboard) implement.
- **Widget catalog per persona** — full inventory, ordering, and empty-state behaviour is P5-S18's scope. This spec commits only to "three render modes, one per persona".
- State-aware dashboard logic (new user / returning user / streak-at-risk / etc.) — P5-S18b (v2.2 patch).
- Interview-Prepper guided checklist depth — P5-S18c (v2.2 patch).
- Existing-user migration UX banner (for legacy users who hit the picker post-deploy) — P5-S19.
- **Persona-switch UX from `/profile`** — post-spec follow-up. When a user wants to change persona after the initial pick, they should be able to from `/profile`. Not specced here because the picker flow ships first; the switch UX can reuse the same page via a query param (e.g. `/onboarding/persona?mode=switch`). Flagged in SESSION-STATE when P5-S17 lands so the implementer doesn't add a "change persona" link on the picker itself.
- Path rename `/auth/me` → `/users/me` — Phase 6 cleanup (touches many frontend callers).
- Persona-aware paywall copy — distinct concern, not blocking this spec.

## Analytics

Three new events to add to `.agent/skills/analytics.md` **when P5-S17 / P5-S18 ship** (do NOT add to analytics.md as part of this spec):

| Event | Side | Properties | Fired from |
|-------|------|------------|------------|
| `persona_picker_shown` | frontend | `{ is_new_user: boolean }` — `true` when the previous persona was `null` (first pick); `false` for legacy-user migration hits (P5-S19) or a future persona switch. | `PersonaPicker` `useEffect` on mount. |
| `persona_selected` | frontend | `{ persona: PersonaEnum, has_target_date: boolean, has_target_company: boolean }` | `PersonaPicker` Continue-click handler, after the API returns `2xx`. |
| `home_dashboard_viewed` | frontend | `{ persona: PersonaEnum }` | `HomeDashboard` `useEffect` on mount (P5-S18). |

All three use `snake_case` per CLAUDE.md §Rule 8. No backend analytics changes.

---

*End of spec. No code in this slice. Implementation begins at P5-S16 (schema + endpoint).*
