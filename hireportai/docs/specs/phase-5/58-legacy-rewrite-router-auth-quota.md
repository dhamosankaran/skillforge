---
slice: P5-S58 (spec) + P5-S58-impl (impl, separate slice)
base_sha: 71fdc39
drafted: 2026-04-23
backlog: B-033
depends_on: spec #42 (paywall dismissal — shipped `91fa915`/post-amend `354f308`), spec #56 (free-tier scan lifetime cap — spec `6242cba`, impl `2080577` post-amend `a9a4f37`), B-032 (Optimize-button gate — shipped `e93e950`, introduced `rewrite_limit` FE trigger)
amends: spec #42 LD-1 (grace carve-out for `rewrite_limit` + `cover_letter_limit` — see §7), spec #56 §4.3 (extend `/payments/usage` response with rewrite + cover-letter counters — see §5)
---

# SPEC: Legacy Rewrite Router — Auth + Quota Enforcement

## Status: Shipped (spec + impl) — closes B-033. Impl half landed 2026-04-23.

## 1. Problem

Three `reasoning`-tier LLM endpoints on the legacy rewrite router accept any
unauthenticated request and write zero usage rows:

- `POST /rewrite` → `app/api/routes/rewrite.py:45` (`rewrite_resume`). Hits
  `generate_resume_rewrite_async` via `gpt_service.py`. No `Depends`, no
  `check_and_increment`, `user_id=None` passed to analytics at lines 86 and 113.
- `POST /rewrite/section` → `app/api/routes/rewrite.py:136` (`rewrite_section`).
  Hits `generate_section_rewrite`. Same auth / quota gaps; `user_id=None` at
  `:156`.
- `POST /cover-letter` → `app/api/routes/cover_letter.py:17`
  (`generate_cover_letter`). Hits `gpt_service.generate_cover_letter`. Same
  gaps; `user_id=None` at `:28, :43`.

All three are re-exported at `/api/v1/*` by 2-line `from … import router`
shims (`app/api/v1/routes/rewrite.py`, `app/api/v1/routes/cover_letter.py`).
Both mount paths are reachable without auth today. Global rate-limit (100
req/min per IP, `app/core/rate_limit.py`) is the only defense — trivially
rotated by any attacker with multiple IPs.

The frontend `PremiumGate` at `hirelens-frontend/src/pages/Rewrite.tsx:20,427`
blocks the UI path when `!canUsePremium`; B-032 layered a `PaywallModal` on
the Optimize button (spec `e93e950`) in front of `/prep/rewrite`. **Both are
client-side.** A bypass via `curl` / Postman / any external client succeeds
today.

### 1.1 Cost framing (P0 justification)

All three endpoints dispatch to the `reasoning` tier — Gemini 2.5 Pro at
**$5.00 per 1M blended tokens** (`app/core/llm_router.py:54`).

| Endpoint | Input tokens (est.) | Output tokens (est.) | $/call | Sustained abuse (100 calls/hr × 30d) |
|---|---|---|---|---|
| `POST /rewrite` | ~6.5K (resume + JD + system prompt) | ~3K (rewritten resume) | **~$0.05** | **~$3,600/mo** |
| `POST /rewrite/section` | ~2.5K | ~500 | ~$0.015 | ~$1,080/mo |
| `POST /cover-letter` | ~6K | ~800 | ~$0.035 | ~$2,520/mo |

Baseline sustained-abuse ceiling: **~$7,200/mo of unrecoverable LLM spend**
with zero revenue attribution. This is the P0 urgency. Note the global 100
req/min IP cap does not bound the monthly total — an attacker rotating IPs
or running at just below the rate cap trivially reaches this ceiling.

### 1.2 Policy drift

`PLAN_LIMITS["free"]["rewrite"] = 0` and `PLAN_LIMITS["free"]["cover_letter"] = 0`
exist in `app/services/usage_service.py:14-36` — and are **dead code**. Grep
across `hirelens-backend/app/` for `check_and_increment("rewrite"`,
`check_and_increment("cover_letter"`, `feature_used='rewrite'`,
`feature_used='cover_letter'` returns zero matches. Same pattern as
`"analyze"` was before spec #56 impl (confirmed by spec #56 §2).
`admin_analytics_service.py:53-54` maps these feature keys to the
`reasoning` tier for LLM-spend estimation — so today's rewrite + cover-letter
spend is **silently invisible in the admin cost dashboard** because no
`usage_logs` rows exist for either feature.

## 2. Locked design decisions

All ten decisions below are locked by Dhamo 2026-04-23 in the authoring
prompt. Restated here so the spec is self-contained.

- **LD-1 — Hybrid bucket mapping.** `/rewrite` and `/rewrite/section` share
  a single `"rewrite"` quota bucket (same user-visible feature: "AI
  Rewrite"). `/cover-letter` gets its own `"cover_letter"` bucket (UX-
  distinct feature; generated artifact is separate). Plan limit rows:
  `PLAN_LIMITS["free"]["rewrite"] = 0`, `PLAN_LIMITS["free"]["cover_letter"] = 0`;
  Pro / Enterprise = `-1` (unlimited). Admin = bypass via
  `paywall_service.py:168`-style in-helper role check.
- **LD-2 — Pro-only, hard gate.** Free tier = 0 uses for both buckets
  (LD-1 values). Matches the PRD framing ("Rewrite = Pro feature") and
  the existing `PremiumGate` behavior. No "N free rewrites" path; no
  quota-window question.
- **LD-3 — Hard auth (`get_current_user`).** All three handlers gain
  `Depends(get_current_user)`. Anonymous callers receive `401`. Per
  Step-0 finding #4, no frontend surface breaks — every call site is
  inside `<ProtectedRoute>` (`App.tsx:95`) and axios auto-injects the
  Bearer token on every request (`api.ts:46-51`). Breaking-change blast
  radius is external clients only (curl / Postman / abusers). No
  integration tests, Postman collections, or external docs reference
  these endpoints.
- **LD-4 — Paywall triggers:**
  - **Reuse `rewrite_limit`** (introduced by B-032 for the FE Optimize-
    button plan-check). Its semantics **widen** from "FE plan-check only"
    to "BE-authoritative quota trigger AND FE plan-check." Same user-
    visible modal, same copy, same Stripe-checkout flow. **Not a rename.**
  - **Introduce a new `PaywallTrigger` value `cover_letter_limit`** —
    cover letter is a UX-distinct artifact from resume rewrite; users
    should see cover-letter-specific copy on the paywall modal. Adding
    the new enum value forces `Record<PaywallTrigger, string>` exhaustive
    maps in `PaywallModal.tsx` HEADLINES / SUBLINES and
    `src/components/__tests__/PaywallModal.test.tsx` to be extended (see
    §10 blast radius).
  - **Disambiguation prop `attempted_action`** on analytics events (spec
    #56 precedent with `scan_limit`) distinguishes sub-surfaces within a
    single trigger (e.g., `rewrite_limit` fires for both `/rewrite` and
    `/rewrite/section`; the prop preserves funnel granularity).
- **LD-5 — Hard-wall carve-out (no dismissal grace).** Both `rewrite_limit`
  and `cover_letter_limit` bypass spec #42 §5.3's default 3-attempt grace.
  `paywall_service.should_show_paywall(user, trigger='rewrite_limit', …)`
  and `…'cover_letter_limit'…` always return `{show: True, attempts_until_next: 0}`
  for free users regardless of `paywall_dismissals` rows. Pro / Enterprise /
  admin continue to short-circuit to `{show: False}` per spec #42 LD-7.
  Dismissals are still logged (LD-6 + win-back telemetry; see §7).
  Rationale: Pro-only features have no legitimate "browse" surface to
  soften; silencing the wall would defeat the policy. Same shape as spec
  #56 §6 carved out `scan_limit`.
- **LD-6 — FE `UsageContext` hydrates from extended `/payments/usage`.**
  The response is extended with rewrite + cover-letter counters (§5).
  FE `canUsePremium` stays the canonical plan-check for `PremiumGate`
  rendering (LD-7); counters from `/payments/usage` are display-only for
  any "N of M rewrites used" UI if added later — under LD-2 Pro-only
  values are always 0-of-0 for free, -1-of-(-1) for Pro/Enterprise/admin.
- **LD-7 — `PremiumGate` on `Rewrite.tsx` stays as defense-in-depth.**
  BE gate is canonical. FE `PremiumGate` is a fast client-side shortcut
  that renders the upgrade CTA without waiting for a 402 round-trip. Not
  replaced by `PaywallModal` in this slice — a UX-consistency slice to
  converge `PremiumGate` → `PaywallModal` is separate follow-up work
  (see §13).
- **LD-8 — Cover letter has no dedicated FE page.** Cover letter is
  generated from a tab inside `Rewrite.tsx` via
  `useRewrite.ts:30::generateCoverLetter`, rendered by
  `components/rewrite/CoverLetterViewer.tsx`. The single `PremiumGate`
  on `Rewrite.tsx:427` already walls both feature surfaces. No new FE
  gate mount required.
- **LD-9 — Implicit grandfathering.** No data migration. `usage_logs` has
  zero rows for `feature_used='rewrite'` or `feature_used='cover_letter'`
  today (LD-2 pre-flight confirmed). Under LD-2 (Pro-only) this is moot
  — free tier = 0 uses regardless of history. Noted for completeness so
  a future reader does not re-open the grandfather question.
- **LD-10 — `CODE-REALITY.md` regen required at impl time.** Three route
  rows change (auth column: none → `get_current_user`), new quota
  branches, `/payments/usage` shape extension. Not blocking spec
  authoring; flagged as an impl-slice closeout item.

## 3. Step-0 audit summary (accepted)

Re-verified at HEAD `71fdc39`:

- **BE auth on `/rewrite`, `/rewrite/section`, `/cover-letter`: none.**
  Confirmed `rewrite.py:45, 136` + `cover_letter.py:17` have no `Depends`
  and pass `user_id=None` to analytics.
- **V1 re-exports are 2-line shims.** `app/api/v1/routes/rewrite.py` and
  `app/api/v1/routes/cover_letter.py` `from … import router`. Single
  source of truth = legacy files.
- **`PLAN_LIMITS["free"]["rewrite"] = 0` and `…["cover_letter"] = 0`
  already exist** in `usage_service.py:14-36` as dead seed values. No
  `section_rewrite` key.
- **Frontend `PremiumGate`** present at `Rewrite.tsx:20,427` gating on
  `useUsage().canUsePremium`. Cover letter shares the same gate (LD-8).
- **Every FE caller is authed.** `api.ts:46-51` auto-injects Bearer.
  `useRewrite.ts` is consumed from `Rewrite.tsx` which sits under
  `<ProtectedRoute>` (`App.tsx:95`). No anonymous FE call paths.
- **No Postman collections / external docs / integration tests reference
  these endpoints.** Breaking change surface = external abusers only.
- **Admin-analytics side effect.** `admin_analytics_service.py:53-54`
  maps rewrite + cover_letter to `"reasoning"` for spend estimation. Zero
  rows today → invisible spend. First `log_usage` firing (post-impl)
  retroactively surfaces the category in the cost dashboard. See §12.
- **`rewrite_limit` trigger history.** B-032 (`e93e950`) added
  `rewrite_limit` to `PaywallTrigger` union + HEADLINES + SUBLINES in
  `PaywallModal.tsx` for the Optimize-button FE plan-check. This spec
  widens the key's semantics to BE-authoritative (LD-4). **Not a
  rename.** `cover_letter_limit` is new in this spec.

## 4. Solution overview

Three moving parts:

### 4.1 Backend — auth + quota enforcement

For each of `rewrite_resume`, `rewrite_section`, `generate_cover_letter`:

1. Add `current_user: User = Depends(get_current_user)` to the route
   signature (import from `app.core.deps`).
2. Add `db: AsyncSession = Depends(get_db)` (import from
   `app.db.session`).
3. At the top of the handler, before any parsing / LLM work, call:
   ```python
   usage = await check_and_increment(
       current_user.id, "<feature>", db, window="monthly"
   )
   if not usage["allowed"]:
       raise HTTPException(
           status_code=402,
           detail={
               "error": "pro_feature_required",
               "trigger": "<rewrite_limit|cover_letter_limit>",
               "feature": "<rewrite|cover_letter>",
               "plan": usage["plan"],
           },
       )
   ```
4. Replace `user_id=None` in analytics calls with `user_id=current_user.id`.

`check_and_increment` short-circuits on `plan in {"pro", "enterprise"}`
and on `role == "admin"` inside the helper (per spec #56 LD-5 impl at
`usage_service.py`). Free plan hits `PLAN_LIMITS["free"]["rewrite"] = 0`
or `…["cover_letter"] = 0` and returns `allowed: False` on the **first**
call — no dismissal grace (LD-5).

**402 status** chosen to match spec #56 / spec #50 convention (paywall-
bearing HTTP status). FE interceptor already pass-through unwraps 402
`detail` objects (`api.ts:105-120` refresh path; direct `detail` access
on other paths).

**Window**: `"monthly"` is the default and is a no-op under LD-2 (Pro-
only) — `0` rows vs a `"lifetime"` window vs a `"monthly"` window makes
no observable difference when the limit is `0`. Using `"monthly"` stays
consistent with `interview_prep` / `resume_optimize` callers so no
helper code-path gets `"lifetime"` for a non-`analyze` feature.

**Shared-bucket mapping (LD-1 + impl decision):**

> **Recommended (Option a):** Both `/rewrite` and `/rewrite/section`
> handlers pass `"rewrite"` as the feature key to
> `check_and_increment` — single `PLAN_LIMITS` row, single
> `usage_logs.feature_used='rewrite'` column value. No duplicate config.
>
> **Alternative (Option b):** Add `PLAN_LIMITS["free"]["section_rewrite"] = 0`
> (and Pro/Enterprise mirrors); handlers pass their own key. Preserves
> per-endpoint telemetry granularity in `usage_logs.feature_used`, at
> the cost of PLAN_LIMITS drift risk.
>
> **Spec recommendation = Option a.** Telemetry granularity is preserved
> via the `attempted_action: 'full' | 'section'` prop on the
> `rewrite_limit_hit` event (§8) — so the `usage_logs` column stays the
> clean "this user consumed one rewrite from their bucket" ledger, and
> the event stream carries the sub-surface. Impl slice finalizes the
> call; if it picks Option b, it must update LD-1 via in-commit amendment
> and document in `.agent/skills/analytics.md`.

### 4.2 Backend — `/payments/usage` response extension

Extend the existing `UsageResponse` schema on
`app/api/routes/payments.py` (shipped by spec #56 impl, `a9a4f37`) with
flat additive counters for rewrite + cover letter. Exact shape in §5.

Hydration reads `PLAN_LIMITS["<plan>"]["rewrite"]` and `…["cover_letter"]`,
counts `usage_logs` rows per feature in the monthly window, applies
admin / Pro / Enterprise bypass sentinels (`-1`), and returns. A new
helper alongside `get_analyze_usage(user_id, db)` (or a generalized
`get_feature_usage(user_id, feature, db, window)`) is the natural shape;
impl slice picks.

### 4.3 Backend — `paywall_service` carve-out (LD-5)

Extend `paywall_service.should_show_paywall` with branches for
`trigger in {"rewrite_limit", "cover_letter_limit"}` that short-circuit
to `{show: True, attempts_until_next: 0, win_back_offered: <existing>}`
for free users regardless of `paywall_dismissals` history. Pro /
Enterprise / admin continue to short-circuit to `{show: False}` per
spec #42 LD-7. Same shape as spec #56 §6 did for `scan_limit`.

### 4.4 Frontend — PaywallModal trigger + copy

- `PaywallTrigger` union (`PaywallModal.tsx:21-27`) gains
  `cover_letter_limit`.
- `HEADLINES[cover_letter_limit]` / `SUBLINES[cover_letter_limit]`
  added (see §9 copy).
- `src/components/__tests__/PaywallModal.test.tsx` `Record<PaywallTrigger, string>`
  exhaustive maps gain the new key (tsc catches this; surfaced by B-032
  regression pattern, §10).
- `rewrite_limit` copy unchanged (B-032 HEADLINE "AI Rewrite is a Pro
  feature" / SUBLINE "Upgrade to Pro to get ATS-optimized resume
  rewrites, tailored cover letters, and PDF export.").

### 4.5 Frontend — no new PaywallModal mount in this slice

Under LD-7, the `PremiumGate` on `Rewrite.tsx:427` stays. There is no
"free user submits from a Pro page and catches a 402" flow in the live
UI today — the page is un-enterable by free users. The 402 handling is
defense-in-depth for external-client scenarios. A follow-up UX slice
(§13) replaces `PremiumGate` with an inline `PaywallModal` pattern;
that slice adds a 402 unwrap + modal-open in `useRewrite.ts` paralleling
`useAnalysis.ts` (spec #56 impl). **Out of scope here.**

## 5. `/payments/usage` response shape — spec #56 §4.3 amendment

Spec #56 §4.3 (as amended in its impl commit to add `is_admin`) returns:

```
{
  "plan": "free" | "pro" | "enterprise",
  "scans_used": int,
  "scans_remaining": int,   // -1 = unlimited
  "max_scans": int,         // -1 = unlimited
  "is_admin": bool
}
```

This spec **extends the shape additively** (flat, no nesting, no
breaking renames):

```
{
  "plan": "free" | "pro" | "enterprise",
  "is_admin": bool,

  // spec #56
  "scans_used": int,
  "scans_remaining": int,         // -1 = unlimited
  "max_scans": int,               // -1 = unlimited

  // spec #58 — new
  "rewrites_used": int,
  "rewrites_remaining": int,      // -1 = unlimited
  "rewrites_max": int,            // -1 = unlimited
  "cover_letters_used": int,
  "cover_letters_remaining": int, // -1 = unlimited
  "cover_letters_max": int        // -1 = unlimited
}
```

Admin bypass (spec #56 §4.3 amendment): `is_admin=true` + all
`*_remaining` and `*_max` return `-1` regardless of plan. Plan field
stays the actual subscription plan for clean downgrade semantics.

Pro / Enterprise: all `*_remaining` and `*_max` return `-1`; `*_used`
returns the true count (Pro users see "n used" but "unlimited" — ops
visibility, not gating).

Free: `rewrites_max = 0`, `rewrites_remaining = 0`, `rewrites_used = 0`
(no rows exist per LD-9). Same for cover letters.

**Nested `features.*` shape deferred** (D1a locked flat). Nested would
force all current `/payments/usage` consumers to re-structure; flat is
non-breaking additive. If a future slice adds a 4th feature and the
flat shape becomes unwieldy, a nested rewrite is a separate migration
slice.

## 6. Acceptance Criteria

- **AC-1** — Anonymous `curl POST /api/rewrite` (or `/api/v1/rewrite`)
  returns `401 Unauthorized`. Same for `/rewrite/section` and
  `/cover-letter` under both mount prefixes. Verified by a pytest
  integration-deselected test that uses `TestClient` without
  Authorization header; asserts status `== 401`.
- **AC-2** — Free-plan authenticated user `POST /api/v1/rewrite` returns
  `402` with body
  `{error: "pro_feature_required", trigger: "rewrite_limit", feature: "rewrite", plan: "free"}`.
  No row is added to `usage_logs`. Verified by pytest.
- **AC-3** — Pro-plan authenticated user `POST /api/v1/rewrite` returns
  `200` with a `RewriteResponse` body. Exactly one new row in
  `usage_logs` with `feature_used='rewrite'`. Repeated calls continue to
  return `200` (unlimited). Verified by pytest.
- **AC-4** — Admin user (`User.role='admin'`) on free subscription
  `POST /api/v1/rewrite` returns `200` regardless of `usage_logs` history.
  Verified by pytest; mirrors spec #56 AC-4.
- **AC-5** — Free-plan `POST /api/v1/rewrite/section` returns `402` with
  `trigger: "rewrite_limit"`, `feature: "rewrite"` (shared bucket per
  LD-1 + §4.1 Option a). Verified by pytest.
- **AC-6** — Free-plan `POST /api/v1/cover-letter` returns `402` with
  body
  `{error: "pro_feature_required", trigger: "cover_letter_limit", feature: "cover_letter", plan: "free"}`.
  Verified by pytest.
- **AC-7** — Pro user `POST /api/v1/cover-letter` returns `200` with
  `CoverLetterResponse` body. One new row in `usage_logs` with
  `feature_used='cover_letter'`. Verified by pytest.
- **AC-8** — `GET /api/v1/payments/usage` for a free user returns the
  extended shape (§5) with
  `rewrites_used=0, rewrites_remaining=0, rewrites_max=0, cover_letters_used=0, cover_letters_remaining=0, cover_letters_max=0`
  alongside the spec #56 scan fields. Verified by pytest extending
  `test_payments_usage_route.py`.
- **AC-9** — `GET /api/v1/payments/usage` for a Pro user returns
  `rewrites_used=<count>, rewrites_remaining=-1, rewrites_max=-1,
  cover_letters_used=<count>, cover_letters_remaining=-1, cover_letters_max=-1`.
  Verified by pytest.
- **AC-10** — `GET /api/v1/payments/usage` for an admin on free plan
  returns `is_admin=true`, all `*_max`/`*_remaining` fields `= -1`, and
  `plan='free'` (plan stays the actual subscription, per spec #56
  amendment). Verified by pytest.
- **AC-11** — `paywall_service.should_show_paywall(user, trigger='rewrite_limit', attempts_since_dismiss=N)`
  returns `{show: True, attempts_until_next: 0}` for a free user for
  every `N >= 0`, regardless of `paywall_dismissals` rows. Same for
  `trigger='cover_letter_limit'`. Other triggers (e.g., `daily_review`)
  retain the 3-attempt grace — verified by a negative-case test.
  Verified by pytest extending `test_paywall_service.py`.
- **AC-12** — `PaywallTrigger` union (`PaywallModal.tsx`) exhaustive
  `Record<PaywallTrigger, string>` in HEADLINES / SUBLINES /
  `PaywallModal.test.tsx` includes `cover_letter_limit`. `tsc --noEmit`
  clean. Verified by the existing Vitest + tsc suite passing unchanged.
- **AC-13** — No regression: B-030 `tests/pages/Results.reanalyze.test.tsx`
  (4/4) and B-032 `tests/pages/Results.optimize.test.tsx` (5/5) pass
  unchanged. Regression pins.
- **AC-14** — B-015 error-interceptor behavior: FE axios pass-through of
  402 `detail` objects continues to work for the new `pro_feature_required`
  envelope. No FE hook change required in this slice (402 never reaches
  the live UI per LD-7 / §4.5). If the follow-up UX slice (§13) lands,
  that slice's ACs cover the 402 → `<PaywallModal trigger='rewrite_limit'>`
  wire-up.

## 7. Spec #42 carve-out (LD-5 amendment)

Spec #42 LD-1 established: *"Schema accepts any `trigger: VARCHAR(64)`;
backend endpoints accept any string; frontend wiring, ACs, and tests cover
`trigger='daily_review'` only. Other `PaywallTrigger` values … reuse the
same endpoints when they later wall — zero backend change needed."*

Spec #56 §6 amended LD-1 for `scan_limit` specifically (hard wall, no
grace). This spec extends the amendment to **`rewrite_limit` AND
`cover_letter_limit`**:

- `POST /api/v1/payments/paywall-dismiss` — unchanged. Dismissals for
  `rewrite_limit` and `cover_letter_limit` are logged normally; rows
  remain useful for win-back telemetry (E-031 / §13 out-of-scope).
- `GET /api/v1/payments/should-show-paywall?trigger=<rewrite_limit|cover_letter_limit>`
  — impl slice modifies `paywall_service.should_show_paywall` so that
  for these triggers on a free user, the handler short-circuits to
  `{show: True, attempts_until_next: 0, win_back_offered: <existing>}`
  regardless of `paywall_dismissals` history. Pro / Enterprise / admin
  continue to short-circuit to `{show: False}` per spec #42 LD-7.
- Rationale: Pro-only features (LD-2) have no legitimate
  "browse-one-more" surface where silencing the wall is user-friendly.
  Silencing would defeat the policy. Different UX contract per trigger
  is by design (spec #56 §6 precedent).

No schema change. No new column. `paywall_service.should_show_paywall`
gains two additional trigger keys in the same branch previously carved
out for `scan_limit`.

## 8. Analytics

**New events (frontend-fired, defense-in-depth + server-telemetry
follow-up):**

- **`rewrite_limit_hit`** — fires from the backend on 402 from
  `/rewrite` or `/rewrite/section`, and/or from the frontend (if the
  follow-up UX slice wires 402 unwrap in `useRewrite.ts`). Properties:
  `{attempted_action: 'full' | 'section', plan: 'free', auth_status: 'authed' | 'anonymous'}`.
  `attempted_action` distinguishes `/rewrite` (`'full'`) from
  `/rewrite/section` (`'section'`). Note: in this spec's impl, only BE
  fires are landed (no FE catch, per LD-7); FE firing becomes possible
  when the UX-consistency slice (§13) lands. Catalogued in
  `.agent/skills/analytics.md` at impl time.
- **`cover_letter_limit_hit`** — fires from the backend on 402 from
  `/cover-letter`. Properties: `{plan: 'free', auth_status: 'authed' | 'anonymous'}`.
  (`attempted_action` omitted — single entry point.) Catalogued at impl
  time.

**Reused events (no shape break):**

- **`paywall_hit`** — fires from `PaywallModal.tsx` on modal open with
  `{trigger: 'rewrite_limit' | 'cover_letter_limit', …}` when the
  follow-up UX slice wires the modal mount. Existing catalog entry in
  `.agent/skills/analytics.md` covers the new trigger values
  (schema-accepts-any-string per spec #42 LD-1).
- **`paywall_dismissed`** — same, for `rewrite_limit` /
  `cover_letter_limit` dismissals. LD-5 guarantees dismiss rows are
  logged even though they do not silence the next attempt.

**Backend analytics fix (byproduct):**

- `rewrite_succeeded`, `rewrite_failed`, `cover_letter_succeeded`,
  `cover_letter_failed` events currently fire with `user_id=None`
  (`rewrite.py:86, 113, 156`; `cover_letter.py:28, 43`). Impl slice
  replaces `None` with `current_user.id`. Not a new event; a fix to
  existing analytics signal.

## 9. PaywallModal copy (LD-4 frontend)

`rewrite_limit` — **unchanged** from B-032 (`e93e950`):
- HEADLINE: *"AI Rewrite is a Pro feature"*
- SUBLINE: *"Upgrade to Pro to get ATS-optimized resume rewrites, tailored cover letters, and PDF export."*

`cover_letter_limit` — **new in this spec**:
- HEADLINE: *"Cover letters are a Pro feature"*
- SUBLINE: *"Upgrade to Pro to generate tailored cover letters, ATS-optimized resume rewrites, and PDF export."*

Copy intentionally mirrors `rewrite_limit` shape so the upgrade-value
proposition stays consistent across Pro features.

## 10. Impl-slice blast radius (reference, non-binding)

| Area | Files touched (approximate) |
|---|---|
| Backend — auth | `app/api/routes/rewrite.py` (add `Depends(get_current_user)` on two handlers; replace `user_id=None` with `current_user.id`), `app/api/routes/cover_letter.py` (same on one handler) |
| Backend — quota | `app/services/usage_service.py` (confirm admin bypass path covers `"rewrite"` and `"cover_letter"` features — helper-level; no new key unless Option b at §4.1), `app/api/routes/rewrite.py` (add `check_and_increment` + 402 envelope), `app/api/routes/cover_letter.py` (same), `app/api/routes/payments.py` + `UsageResponse` schema (extend shape per §5; new helper in `usage_service.py` or generalize `get_analyze_usage`) |
| Backend — dismissal | `app/services/paywall_service.py` (`rewrite_limit` + `cover_letter_limit` branches in `should_show_paywall` — copy the `scan_limit` pattern from spec #56 §6 impl) |
| Frontend — trigger surface | `src/components/PaywallModal.tsx` (extend `PaywallTrigger` union with `cover_letter_limit`; add HEADLINES + SUBLINES entries), `src/components/__tests__/PaywallModal.test.tsx` (`Record<PaywallTrigger, string>` exhaustive map gains the new key — **tsc will fail without this**; B-032 regression pattern), `src/services/api.ts` (extend `UsageResponse` interface with six new fields), `src/context/UsageContext.tsx` (consume new counters if display is wired — otherwise just widen the type) |
| Tests | `tests/test_rewrite_quota.py` (**new** — AC-1..AC-5), `tests/test_cover_letter_quota.py` (**new** — AC-6, AC-7), `tests/test_payments_usage_route.py` (extend — AC-8, AC-9, AC-10), `tests/services/test_paywall_service.py` (extend — AC-11 for both new triggers), existing `tests/pages/Results.optimize.test.tsx` (B-032 regression pin, AC-13 unchanged), existing `tests/pages/Results.reanalyze.test.tsx` (B-030 regression pin, AC-13 unchanged), existing `PaywallModal.test.tsx` (AC-12 tsc clean) |
| Analytics | `.agent/skills/analytics.md` (new rows: `rewrite_limit_hit`, `cover_letter_limit_hit`; note on `paywall_hit` / `paywall_dismissed` trigger-value extension) |
| Docs | `CODE-REALITY.md` §1 endpoint-count delta (3 routes gain auth column change), §3 flat endpoint table (auth column + 402 branch notes for `/rewrite`, `/rewrite/section`, `/cover-letter` × 2 mount prefixes = 6 row updates), §4 `paywall_service.py` row extended with `rewrite_limit` + `cover_letter_limit` carve-outs, `UsageResponse` shape line updated |

**Regression guardrail (AC-12):** the `Record<PaywallTrigger, string>`
exhaustive map in `src/components/__tests__/PaywallModal.test.tsx`
caught B-032's impl in-flight — tsc complained of a missing key the
moment `PaywallTrigger` grew. Impl slice MUST add the `cover_letter_limit`
key to that map (and to `HEADLINES` / `SUBLINES` in `PaywallModal.tsx`)
before the tsc pass will succeed. Flagged here so the impl slice does
not rediscover this mid-commit.

## 11. API Contract (reference — impl slice locks final shapes)

| Method | Path | Change | Auth |
|---|---|---|---|
| `POST` | `/api/rewrite`, `/api/v1/rewrite` | Add `get_current_user`; add quota check → 402 on free | **new: `get_current_user`** |
| `POST` | `/api/rewrite/section`, `/api/v1/rewrite/section` | Add `get_current_user`; add quota check (shared `"rewrite"` bucket per §4.1 Option a) → 402 on free | **new: `get_current_user`** |
| `POST` | `/api/cover-letter`, `/api/v1/cover-letter` | Add `get_current_user`; add quota check → 402 on free | **new: `get_current_user`** |
| `GET` | `/api/v1/payments/usage` | Response extended with rewrite + cover-letter counters (§5) | unchanged: `get_current_user` |
| `GET` | `/api/v1/payments/should-show-paywall?trigger=rewrite_limit` | Branch: always `{show: True}` for free (LD-5) | unchanged: `get_current_user` |
| `GET` | `/api/v1/payments/should-show-paywall?trigger=cover_letter_limit` | Branch: always `{show: True}` for free (LD-5) | unchanged: `get_current_user` |

## 12. Admin analytics side-benefit

`admin_analytics_service.py:53-54` maps `"rewrite": "reasoning"` and
`"cover_letter": "reasoning"` for LLM-spend estimation. Today no
`usage_logs` rows exist for either feature, so all rewrite + cover-letter
spend is invisible in the admin cost dashboard — the category appears
empty.

Post-impl, every Pro rewrite / cover-letter call writes a row through
`log_usage` inside `check_and_increment`, and the admin dashboard
retroactively surfaces the spend. **No explicit retrofit needed.**
Documented here so future-you reading the spec in isolation does not
treat the sudden "new" category as a bug.

No schema change. No migration. The cost-dashboard column is already
wired; the data source simply starts populating.

## 13. Out of Scope

- **`GET /rewrite/templates` auth** (`api.ts:218`). Read-only static list;
  no LLM cost. Separate hardening slice if ever needed.
- **Rate-limit tightening on rewrite/cover-letter endpoints** (e.g.,
  dedicated slowapi limit below the global 100/min). Different defense
  layer; pairs with auth rather than blocks on it. Separate slice.
- **Win-back email for `rewrite_limit` / `cover_letter_limit`
  dismissals** (spec #42 §5.5 win-back pattern). Gated by real dismissal
  data — follow-up slice when telemetry exists.
- **`PremiumGate` → `PaywallModal` UX consistency slice.** LD-7 keeps
  `PremiumGate` as defense-in-depth. Converging `Rewrite.tsx`'s inline
  lock screen to the canonical `PaywallModal` + Stripe-checkout flow is
  a separate UX-consistency slice (mirrors B-030 / B-032's pattern on
  `Results.tsx`). That slice also wires 402 unwrap + modal-open in
  `useRewrite.ts` paralleling spec #56 impl of `useAnalysis.ts`.
- **Anonymous-abuse prevention beyond auth.** IP-level attack mitigation
  (slowapi tighter limits, IP blocking via `registration_log.py` pattern)
  is the security-skill's domain; this spec's `get_current_user` closes
  the unauthenticated-cost-leak path but does not defend against an
  attacker with N stolen tokens. Separate slice.
- **Legacy `/api/*` prefix deprecation.** The 2-line `/api/v1/*` shims
  are preserved this slice (minimum-blast-radius change); deprecating
  the legacy mount path is a separate cleanup slice.
- **`user_id=None` → `current_user.id` in analytics for other endpoints.**
  Grep the codebase for other `analytics_track(user_id=None, …)` call
  sites — out of scope here; this spec scopes to the three endpoints in
  B-033. A repo-wide sweep is a separate hygiene slice.

## 14. Dependencies

- **Spec #42** (paywall dismissal) — shipped. This spec **amends** LD-1
  for `rewrite_limit` and `cover_letter_limit` (§7), mirroring the
  mechanism spec #56 §6 used for `scan_limit`.
- **Spec #56** (free-tier scan lifetime cap) — shipped. This spec
  **amends** §4.3 `/payments/usage` response (§5). The
  `check_and_increment` helper already supports the `window` param +
  admin bypass (spec #56 impl, `a9a4f37`); no further helper changes
  required.
- **B-032** (`e93e950`) — shipped. Introduces `rewrite_limit`
  `PaywallTrigger` for FE plan-check. This spec widens the key's
  semantics to BE-authoritative (LD-4). Not a rename. In-code
  cross-reference comment on the FE + BE branches at impl time.
- **No new migration.** `usage_logs`, `paywall_dismissals`, `PLAN_LIMITS`
  (Python constant) already cover storage needs. Literal edits to
  `usage_service.py` at impl time are sufficient.

## 15. R14 classification

New feature (server-side auth + quota where none existed) layered with
a security fix (public LLM-cost leak). Spec-first per R14 default, not
an exception.
