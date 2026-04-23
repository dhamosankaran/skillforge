---
slice: P5-S56 (spec) + P5-S56-impl (impl, separate slice)
base_sha: ebd0415
drafted: 2026-04-23
backlog: B-031
depends_on: spec #42 (paywall dismissal — shipped `91fa915`/post-amend `354f308`), spec #55 (B-030 Re-Analyse gate — shipped `ebd0415`)
amends: spec #42 LD-1 (grace carve-out for `scan_limit` — see §6)
---

# SPEC: Free-Tier ATS Scan Lifetime Cap

## Status: Draft

## 1. Problem

Two production regressions, one policy, one code-reality:

1. **No backend scan quota exists today.** `/api/analyze` and `/api/v1/analyze` (`app/api/routes/analyze.py:46-47`, re-exported from `app/api/v1/routes/analyze.py:2`) accept any authenticated request without checking `usage_logs`, `usage_service.check_and_increment`, or any plan-aware guard. The `PLAN_LIMITS["free"]["analyze"] = 3` literal in `app/services/usage_service.py:13` has **zero consumers** — grep across `hirelens-backend/app/` for `check_and_increment("analyze")` / `check_usage_limit("analyze")` / `feature="analyze"` returns nothing. The entry is dead config.
2. **The only quota the product enforces today is client-side.** `hirelens-frontend/src/context/UsageContext.tsx:40,62` keys `maxScans: 3` off a `localStorage["skillforge_usage"]` record. Any user who opens DevTools, clears site data, or switches browser gets a fresh `scansUsed: 0`. The cap is cosmetic.
3. **Policy drift.** The number `3` has no spec ancestry. `skillforge_playbook_v2.md` Phase 1.12 (line 132, verbatim) covers card + interview-Q caps only; the user journey at line 141 describes the ATS scan as *"Upload resume (free)"* with the paywall downstream at the 15-card wall, not on scans. `docs/prd.md` §1 has no scan cap. The `3` was a code decision, not a product decision.

**Locked policy (Dhamo, 2026-04-23):**
- Free tier = **exactly one full ATS analysis per user, lifetime.**
- Pro / Enterprise = unlimited.
- Admin = bypass.
- Dismissal grace: **none.** Every attempt past the first re-opens the modal. This is a carve-out from spec #42 LD-1/LD-3 which granted 3-attempt grace by default.

This spec does NOT "tighten 3 → 1." It **establishes server-side enforcement for the first time** and **sets the lifetime cap to 1** in the same slice.

## 2. Audit summary (Step-0 findings, accepted)

Step-0 report was delivered and accepted on 2026-04-23 before this spec was drafted; re-stating the load-bearing facts:

- **BE quota enforcement on `/analyze`: none.** `PLAN_LIMITS["free"]["analyze"] = 3` is dead; the only live consumers of `usage_service` are `interview_storage_service.py:60` (`interview_prep`) and `app/api/v1/routes/resume.py:78` (`resume_optimize`).
- **FE counter: lifetime-window localStorage, defeatable.** `UsageContext.tsx:40/46/79` hardcodes `maxScans: 3`; increment at `useAnalysis.ts:17`.
- **BE counter semantics: monthly window today.** `check_and_increment` filters by `created_at >= first-of-month` (`usage_service.py:108-118`). This spec's "analyze" feature needs **lifetime** window — impl slice picks between branching the existing helper on feature name vs. introducing a `check_and_increment_lifetime` helper (impl detail; contract stated in §4.2).
- **`UsageLimit` model does not exist.** `PLAN_LIMITS` is a Python dict constant. No schema change is required for the cap; only a literal change and new route wiring.
- **B-030 Re-Analyse gate is plan-based (`canUsePro`).** It does NOT read `canScan` or `scansUsed`. It remains correct under the 1-lifetime policy: Pro always flows through; Free is always walled. No test change in `tests/pages/Results.reanalyze.test.tsx` (AC-10).
- **Admin-bypass pattern** is established: `paywall_service.py:168` uses `getattr(user, "role", "user") == "admin"`. `User.role` column exists (`app/models/user.py:17`). This spec follows the same pattern.
- **Paywall trigger**: reuse existing `scan_limit`. B-030 already opens `scan_limit` for Re-Analyse; consolidating initial-scan + Re-Analyse onto one trigger keeps the PostHog funnel coherent. No new trigger type in `PaywallTrigger` union.

## 3. Locked design decisions

- **LD-1 — Cap: 1 lifetime.** Free plan: exactly one `usage_logs` row with `feature_used='analyze'` over the user's entire account history. Pro / Enterprise: no check. Admin: bypass regardless of plan.
- **LD-2 — BE authoritative; FE is optimistic display.** The backend's `usage_logs` is the source of truth. Frontend `UsageContext` hydrates from a new `GET /api/v1/payments/usage` (or equivalent; impl-slice confirms) on mount and after each scan completion. `localStorage` becomes read-through cache only; clearing it never grants an extra scan.
- **LD-3 — Window: lifetime for `analyze`.** The current `check_and_increment` counts rows per-month. For `analyze`, counting is lifetime (no `created_at >= X` filter). Impl picks shape: (a) branch `check_and_increment` on feature name, (b) introduce `check_and_increment_lifetime`. Either is acceptable; the contract is lifetime semantics for `feature_used='analyze'`.
- **LD-4 — No dismissal grace for `scan_limit`.** Amends spec #42 LD-1. The `scan_limit` trigger is carved out from the default 3-attempt grace. `paywall_service.should_show_paywall(user, trigger='scan_limit', …)` **always returns `{show: True, attempts_until_next: 0}` for free users**, regardless of any `paywall_dismissals` rows. Dismissal is logged (for win-back telemetry under E-031), but does not silence the next attempt. See §6.
- **LD-5 — Grandfathering: implicit.** No data migration. Existing free users start the new rule with zero `usage_logs` rows where `feature_used='analyze'` (because the feature was never logged before). Every existing free user effectively gets one fresh scan under the new rule. This is an accepted bounded leak: (existing_free_user_count × 1 free scan). No retroactive block, no announcement email, no grace window. Documented here so the revenue-leakage question does not resurface later without an explicit re-decision.
- **LD-6 — Trigger reuse: `scan_limit`.** No new `PaywallTrigger` union value. Existing copy on `PaywallModal.tsx:37,46` (*"You've hit your free scan limit"* / *"You've used all your free ATS scans…"*) fits the 1-lifetime semantic verbatim. Frontend passes a new `attempted_action: "initial" | "reanalyze"` property on the event telemetry only (§7); no copy variant is added.
- **LD-7 — Upgrade is plan-first.** Upon free→Pro upgrade mid-session, the gate is removed immediately (`check_and_increment` short-circuits on `plan == "pro"` at `usage_service.py:103`). No counter reset needed and none performed. Dismissal rows are retained (spec #42 LD-7).

## 4. Solution

### 4.1 Backend — wire quota enforcement on analyze

Add a call to `check_and_increment(user_id, "analyze", db)` (or the new lifetime helper) at the top of `analyze_resume` in `app/api/routes/analyze.py:47` **before** any parsing, LLM, or persistence work. Structure:

```
# pseudocode — impl slice writes real code
usage = await check_and_increment(user.id, "analyze", db, window="lifetime")
if not usage["allowed"]:
    raise HTTPException(
        status_code=402,
        detail={
            "error": "free_scan_cap_hit",
            "trigger": "scan_limit",
            "scans_used": usage["used"],
            "scans_limit": usage["limit"],
            "plan": usage["plan"],
        },
    )
```

Admin bypass follows the existing `paywall_service.py:168` pattern: `if getattr(user, "role", "user") == "admin": return {allowed: True, remaining: -1, limit: -1, plan: plan}` — placed at the top of the helper for consistency.

**402 was chosen over 403** to match spec #50's daily-card wall convention (`study_service._check_daily_wall` raises 402 with paywall payload). FE interceptor already unwraps 402 `detail` objects (B-015 fix; `api.ts` pass-through for walls).

### 4.2 Backend — lifetime window semantics

`check_and_increment` today filters by `created_at >= first-of-month` (`usage_service.py:108-118`). For `feature_used='analyze'`, drop the date filter — count ALL rows. Impl slice picks:

- **Option A (recommended):** add `window: Literal["monthly", "lifetime"] = "monthly"` param; analyze route passes `window="lifetime"`.
- **Option B:** new `check_and_increment_lifetime` helper; existing helper untouched.

Either is acceptable. Contract that matters here: for `feature_used='analyze'`, one row anywhere in the user's history is enough to wall the next attempt.

`PLAN_LIMITS["free"]["analyze"]` is updated from `3` to `1` as part of the impl slice. `PLAN_LIMITS["pro"]["analyze"]` and `["enterprise"]["analyze"]` remain `-1` (unlimited).

### 4.3 Backend — new GET /api/v1/payments/usage endpoint

Scope: read-only snapshot used by the FE to render remaining-scan text and decide whether to pre-gate the Analyze button. Lives on the existing `/api/v1/payments` router (`app/api/routes/payments.py`) per spec #42 §2.2 convention (keep billing-adjacent surface on one router; no new `/billing/*` router).

**Request:** `GET /api/v1/payments/usage` — auth = `Depends(get_current_user)`.

**Response (200):**
```
{
  "plan": "free" | "pro" | "enterprise",
  "scans_used": int,      // lifetime count from usage_logs
  "scans_remaining": int, // max(0, limit - used); -1 for unlimited plans
  "max_scans": int        // PLAN_LIMITS["<plan>"]["analyze"]; -1 for unlimited
}
```

**Errors:** `401` on missing/invalid JWT (auth dependency). No other errors.

Admin bypass: returns `{plan: "<actual plan>", scans_used: N, scans_remaining: -1, max_scans: -1}` so the FE reads admin as unlimited while still showing the real count for audit-friendly UX.

Impl may reuse `get_usage_summary` (`usage_service.py:129`) as a starting point; that helper today returns a monthly breakdown across all features. The new endpoint scopes to `analyze` and uses lifetime window.

### 4.4 Frontend — UsageContext hydrated from BE

`UsageContext.tsx` changes (impl slice):
- Remove hardcoded `maxScans: 3` at lines 40/46/79.
- On provider mount (and after each successful scan), `fetch` `GET /api/v1/payments/usage`; store result. Expose `maxScans`, `scansUsed`, `scansRemaining` derived from BE response.
- `localStorage` stays for display-smoothness (pre-paint hydration) but is non-authoritative; BE response overwrites on every response.
- `canScan` remains the same expression shape (`plan !== 'free' || scansUsed < maxScans`) but operands come from BE.

`Analyze.tsx:116` currently renders the literal `"{scansUsed}/3 free scans used"`. Impl slice replaces `3` with `{maxScans}` from the hydrated state.

### 4.5 Frontend — 402 handler on Analyze submit

`useAnalysis.ts` currently increments `scansUsed` optimistically on successful submit (`:17`). Impl slice:
- On 402 from `/api/v1/analyze` with `detail.trigger === 'scan_limit'`, surface the existing `PaywallModal` with `trigger='scan_limit'`. The Analyze page is the mount site; the B-030 pattern applies (state-driven `paywallTrigger` on the modal).
- Fire `free_scan_cap_hit` PostHog event (§7).
- Do NOT increment `scansUsed` client-side on 402.

### 4.6 Frontend — B-030 Re-Analyse gate stays

`Results.tsx:60-71` (`handleReanalyzeClick`) remains plan-based via `canUsePro`. No change in this slice's impl. AC-10 pins this regression guard.

## 5. Acceptance Criteria

- **AC-1** — Free user with zero `usage_logs` rows where `feature_used='analyze'` can successfully `POST /api/v1/analyze` and receives a `200` with an `AnalysisResponse` body. Verified by a pytest integration-deselected test that seeds a free-plan subscription, POSTs a valid payload, asserts `response.status_code == 200`, and asserts exactly one new row in `usage_logs` with `feature_used='analyze'`.
- **AC-2** — Free user with ≥1 existing `usage_logs` row where `feature_used='analyze'` receives `402` from `/api/v1/analyze` with body `{error: "free_scan_cap_hit", trigger: "scan_limit", scans_used: 1, scans_limit: 1, plan: "free"}`. No new `usage_logs` row is written on the 402 path. Frontend test (Vitest): mocking a 402 response, clicking Analyze opens `<PaywallModal trigger="scan_limit" />` and the headline *"You've hit your free scan limit"* renders.
- **AC-3** — Pro user (with `Subscription.plan='pro'`, `status='active'`) POSTs `/api/v1/analyze` N+1 times (where N > 1) and every call returns `200`. No `usage_logs` count check is performed. Verified by pytest.
- **AC-4** — Admin user (`User.role='admin'`) with `Subscription.plan='free'` and an existing `usage_logs` row for `analyze` POSTs `/api/v1/analyze` and receives `200`. Admin bypass precedes plan check. Verified by pytest.
- **AC-5** — Free user with an existing `usage_logs` row for `analyze` upgrades via the standard `checkout.session.completed` webhook → `Subscription.plan='pro'`. The very next `POST /api/v1/analyze` returns `200` without any counter reset and without deleting the historical `usage_logs` row. Verified by pytest integration-deselected test that walks: 402 → webhook → 200.
- **AC-6** — `check_and_increment(user_id, "analyze", db, window="lifetime")` counts rows across the user's entire history. No `created_at >= X` filter is applied for `feature_used='analyze'`. Verified by a unit test that inserts a `usage_logs` row with `created_at` backdated to 365 days ago and asserts the cap still fires.
- **AC-7** — FE `localStorage["skillforge_usage"]` is clearable by the user without granting an extra scan. Verified by a Vitest test that: (a) hydrates `UsageContext` from a BE mock returning `{scans_used: 1, max_scans: 1, plan: 'free'}`, (b) clears `localStorage`, (c) re-renders the provider, (d) asserts `canScan === false` (BE-mock value drives state).
- **AC-8** — Free user dismissing the `scan_limit` `PaywallModal` via "Not now" or X logs a `paywall_dismissals` row AND closes the modal, but the **next** Analyze-submit attempt reopens the modal with `show: true`. `paywall_service.should_show_paywall(user, 'scan_limit', attempts_since_dismiss=N)` returns `{show: True, attempts_until_next: 0}` for every N. Verified by pytest (direct service test) + Vitest (QuizPanel-style flow test scoped to Analyze.tsx).
- **AC-9** — Existing free user with *no* `usage_logs` rows for `analyze` at deploy time (the current reality for every user) gets exactly one successful scan under the new rule. Verified by the natural running of AC-1 against any user created before the deploy — no data migration is executed; no grandfather-exemption flag is added to `User`.
- **AC-10** — `tests/pages/Results.reanalyze.test.tsx` (B-030 Vitest suite, 4 tests) passes unchanged. No new test; this is a regression pin. The Re-Analyse button's `canUsePro`-based gate is orthogonal to the usage-log-based gate on `/api/v1/analyze` — both must fire correctly side-by-side: Re-Analyse paywalls free users *before* the network call; a Pro user whose plan transitioned mid-session would be caught by the BE check on navigate.

## 6. Spec #42 carve-out (LD-4 amendment)

Spec #42 LD-1 established: *"Schema accepts any `trigger: VARCHAR(64)`; backend endpoints accept any string; frontend wiring, ACs, and tests cover `trigger='daily_review'` only. Other `PaywallTrigger` values (`scan_limit`, `card_limit`, …) reuse the same endpoints when they later wall — zero backend change needed."*

This spec amends that promise for `scan_limit` specifically:

- `POST /api/v1/payments/paywall-dismiss` — unchanged. Dismissals for `scan_limit` are logged normally; the row carries trigger-agnostic information and remains useful for win-back telemetry (E-031).
- `GET /api/v1/payments/should-show-paywall?trigger=scan_limit` — **impl slice modifies the handler** so that for `trigger == 'scan_limit'` on a free user, the handler short-circuits to `{show: True, attempts_until_next: 0, win_back_offered: <existing>}` regardless of `paywall_dismissals` history. Pro/Enterprise/admin continue to short-circuit to `{show: False, …}` per spec #42 LD-7 (unchanged).
- Spec #42 test `test_should_show_paywall` must gain a new case: free user with 1+ `scan_limit` dismissals still receives `{show: True, attempts_until_next: 0}`. Other triggers (`daily_review`, etc.) retain the 3-attempt grace.

Rationale: daily-card review is a browse-one-more-card flavor where silencing is user-friendly; the 1-lifetime scan cap is a hard revenue gate where silencing would defeat the policy. Different UX contract per trigger.

No schema change. No new column. No new event. The amendment is a single-branch change inside `paywall_service.should_show_paywall`.

## 7. Analytics

**Extended events (no shape break):**
- `paywall_hit` — already catalogued at `.agent/skills/analytics.md:41`. `PaywallModal.tsx:80-85` already fires this on modal open with `{trigger, category_name?, cards_viewed?}`. Impl slice adds an optional `attempted_action: 'initial' | 'reanalyze'` property **from the Analyze-submit call site and the Results Re-Analyse call site**, passed to `<PaywallModal context={{attemptedAction: ...}}>` or directly via a new optional `attempted_action?: string` in the event-fire block. Existing event rows in PostHog continue to be valid (new prop = nullable extension).
- `paywall_dismissed` — already catalogued at `.agent/skills/analytics.md` (spec #42 §6). For `trigger='scan_limit'` dismissals, it fires normally per LD-4 above. Impl slice adds the same `attempted_action` optional prop for funnel attribution.

**New event:**
- `free_scan_cap_hit` — fires from `useAnalysis.ts` (FE) on 402 response from `/api/v1/analyze`. Properties: `{attempted_action: 'initial' | 'reanalyze', scans_used_at_hit: int}`. Fires once per 402 (no retry). Catalogued in `.agent/skills/analytics.md` as part of the impl slice.

`attempted_action` enum:
- `'initial'` — user clicked Analyze on `/prep/analyze` directly.
- `'reanalyze'` — user was redirected from `/prep/results` Re-Analyse (the Pro→Free plan-transition edge case, where B-030's FE gate wouldn't fire but BE would catch on the next submit).

The two values cover every path into `POST /api/v1/analyze`. No third value is anticipated.

## 8. API Contract (reference — impl slice locks final shapes)

| Method | Path | Change | Auth |
|--------|------|--------|------|
| `POST` | `/api/analyze`, `/api/v1/analyze` | Add quota check → 402 on cap hit | `get_current_user` (existing) |
| `GET`  | `/api/v1/payments/usage` | **New** — read-only usage snapshot | `get_current_user` |
| `POST` | `/api/v1/payments/paywall-dismiss` | Unchanged shape; accepts `trigger='scan_limit'` | `get_current_user` |
| `GET`  | `/api/v1/payments/should-show-paywall?trigger=scan_limit` | Branch for `scan_limit` → always `show: True` for free | `get_current_user` |

## 9. Data Model Changes

None. `usage_logs` already exists with the right columns (`feature_used`, `created_at`, `user_id`); we're simply writing rows for a new `feature_used` value and reading them with a different window. `PLAN_LIMITS` is a Python dict constant — the change is a literal edit, not a migration.

## 10. Out of Scope

- **Optimize button paywall gate** (`/prep/results` → `/prep/rewrite`). Same revenue-surface concern, separate slice (Prompt C).
- **Announcement email** to existing free users about the policy change. Explicitly declined via LD-5 (implicit grandfathering).
- **Counter-reset on downgrade.** Per spec #42 LD-7 (Pro history retained), we don't clear `usage_logs` when a Pro user downgrades. A downgraded user who already used their one lifetime free scan *as a free user* stays capped; if they used scans only *as Pro*, those rows still count against free lifetime. The impl slice may refine this (e.g., count only rows created while `plan='free'` at the time) but the default behavior is "all rows count" — simpler and matches the policy language *"1 full ATS analysis per user, lifetime."*
- **Anonymous (logged-out) scan paths.** `/api/analyze` has an anonymous surface per the legacy route (see `docs/specs/phase-5/22-plan-aware-missing-skills-cta.md:18`). Out of scope; anonymous scans are governed by a separate abuse-prevention strategy (IP blocking, playbook 1.14). This spec scopes to authenticated free users.

## 11. Dependencies

- **Spec #42** (paywall dismissal) — shipped. This spec **amends** LD-1 for `scan_limit` (§6).
- **Spec #55 / B-030** (Re-Analyse gate) — shipped (`ebd0415`). AC-10 pins that regression.
- **No new migration.** `paywall_dismissals` table (spec #42), `usage_logs` table (Phase 1) already cover the storage needs.

## 12. Impl-slice blast radius (reference, non-binding)

| Area | Files touched (approximate) |
|------|------------------------------|
| Backend — quota | `app/services/usage_service.py` (lifetime branch + admin bypass), `app/api/routes/analyze.py` (add check), `app/api/routes/payments.py` (new `GET /usage`) |
| Backend — dismissal | `app/services/paywall_service.py` (scan_limit branch in `should_show_paywall`) |
| Frontend — gating | `src/context/UsageContext.tsx` (BE-sourced), `src/pages/Analyze.tsx` (dynamic cap text + 402 → paywall), `src/hooks/useAnalysis.ts` (402 handling + `free_scan_cap_hit` fire), `src/services/api.ts` (new `getUsage`) |
| Tests | `tests/test_usage_limits.py` (+lifetime, +grandfather, +admin), new `tests/test_analyze_quota.py` (or similar), `tests/services/test_paywall_service.py` (scan_limit grace carve-out), `tests/pages/Analyze.gate.test.tsx` (402 → modal), `tests/pages/Results.reanalyze.test.tsx` (regression guard, unchanged) |
| Analytics | `.agent/skills/analytics.md` (new row for `free_scan_cap_hit`; `attempted_action` note on `paywall_hit` / `paywall_dismissed`) |

## 13. R14 classification

Not an exception — this is a new feature (server-side quota where none existed) layered with a policy change. Spec-first per R14 default.
