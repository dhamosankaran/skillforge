---
slice: P5-S65 (spec author — backfill consolidation)
base_sha: 244e043
drafted: 2026-04-26
backlog: E-020 (audit row, stays 🟡), E-023 (backfill row, closes ✅ this merge)
locked_decisions: LD-1..LD-9 (in-spec, §3)
template: spec #60 (Analyze pre-flight gate) — most recent Mode-4 phase-5 spec at slice start
depends_on: none (consolidation of on-disk reality + audit findings)
unblocks: three follow-up impl slices sketched in §11 (Gap B / Gap D / Gap E fixes — BACKLOG IDs filed at impl-slice time per R17)
---

# SPEC #27 — Geo-Based Pricing (USD / INR) — Behavior Contract + Deferred-Gap Fix Anchors

**Status:** Draft
**Owner:** Dhamo
**Created:** 2026-04-26
**Phase:** 5
**Closes:** E-023 (backfill spec). E-020 audit row stays 🟡 — gaps B / D / E still need impl slices anchored at §7 / §5 / §6 respectively.

## §1 Status / Provenance

Authored 2026-04-26 consolidating three on-disk artifacts into one canonical behavior contract:

- **`.agent/skills/geo-pricing.md`** — implementation patterns (ip-api integration shape, Redis cache key/TTL, `usePricing()` consumer list, "never hardcode a price" rule). Skill remains authoritative for *how* to implement; this spec is authoritative for *what* the behavior must be.
- **`docs/audit/2026-04-E-020-geo-pricing.md`** (commit `4aaeda4`, slice B-054) — re-verification of E-020's three deferred gaps (B / D / E) against HEAD `bd9f662`. Audit findings + Finding 0 (phantom-spec path) drove this spec into existence.
- **`docs/PHASE-5-STATUS.md`** rows 5.3 + 5.13 + line 100 — phase-5 status-table enumeration of the three deferred gaps. PHASE-5-STATUS becomes derivative of this spec on merge; the rows can be flipped to ✅ once the per-gap impl slices ship (not this slice).

**Why a spec, not just a skill amendment.** The audit surfaced product-judgment surface (especially Gap E Free-plan rendering) that the skill's "Used by" list and "never hardcode" rule cannot adjudicate. A spec is the right home for AC-anchored behavior contracts; the skill stays the right home for implementation patterns.

**Closes Finding 0** (audit doc): spec #27 path was stale on E-020 + E-023 rows since filing (file did not exist on disk). Both rows can now cite this file by exact path.

**Template:** spec #60 (`docs/specs/phase-5/60-analyze-page-preflight-gate.md`) — section shape replicated; content domain-specific.

## §2 Context & Problem Statement

Pro pricing is geo-localized: Indian visitors see ₹999/mo billed in INR; everyone else sees $49/mo billed in USD. The mapping is served by a single backend endpoint backed by `ip-api.com` and Redis, and read by `usePricing()` on the frontend. The system shipped in P5-S8 (commits `b794d26`, `02d7cc8`) and has been live in production since.

The audit at `docs/audit/2026-04-E-020-geo-pricing.md` confirmed three gaps still open at HEAD `bd9f662`:

- **Gap B** — `LoginPage.tsx` does not consume `usePricing()`. A logged-out Indian user landing on `/login` sees no country-localized price; the auth surface is treated as marketing-adjacent on every other entry surface (Pricing, Landing, PaywallModal) but not Login. **HIGH confidence, CONFIRMED-STILL-OPEN.**
- **Gap D** — `geo_pricing_service.py` caches failure-fallback results (USD when ip-api returned None) at the same 24-hour TTL as success results. A transient ip-api rate-limit on an Indian IP's first lookup locks that IP to USD pricing for 24h. Note: USD-on-fallback itself is **by-design** per skill line 23 — only the failure-cache TTL is the bug. **HIGH confidence, REFINEMENT (partial-design / partial-bug).**
- **Gap E** — Free-plan price renders as literal `$0` on both `Pricing.tsx` and `LandingPage.tsx`, regardless of detected currency. INR users on `/pricing` see mixed-currency rendering: `$0` (Free) next to `₹999/mo` (Pro) on the same page. **HIGH confidence, CONFIRMED-STILL-OPEN.**

This spec resolves all three at the contract level so per-gap impl slices have unambiguous AC to land against.

## §3 Architecture (defers to skill for patterns; spec owns the contract)

The skill `.agent/skills/geo-pricing.md` is the authoritative implementation reference. This section restates only the contract surface; do not duplicate skill content here.

### §3.0 Locked Decisions

- **LD-1** Country-to-currency mapping is binary: `IN → INR`; everything else → `USD`. No third currency in scope (see §10).
- **LD-2** Geolocation source is `ip-api.com` free tier (45 req/min, no API key). Single provider; no fallback geolocation source in scope.
- **LD-3** Successful country resolution is cached for 24h (86,400s) under key `geo_pricing:{ip_address}` per skill §Redis Caching. **(Unchanged from skill.)**
- **LD-4** Failure-fallback (ip-api timeout / rate-limit / parse error → `_lookup_country` returns `None` → USD result built) is cached for **60s** under the same key. **(NEW — resolves Gap D. See §5.)**
- **LD-5** Pro pricing always routes through `usePricing()` on the frontend. Hardcoding Pro prices in any frontend component is forbidden per skill rule (line 73-74). **(Unchanged from skill.)**
- **LD-6** Free-plan price is rendered as the literal string `Free` (no currency symbol, no zero) on every surface. **(NEW — resolves Gap E. See §6.)**
- **LD-7** Every entry surface that displays Pro pricing MUST consume `usePricing()`. Auth surfaces (`LoginPage.tsx`, `RegisterPage.tsx`) count as entry surfaces. **(NEW — resolves Gap B. See §7.)**
- **LD-8** Stripe Checkout currency is governed by the Stripe price ID, which `usePricing()` returns alongside the display values. Frontend passes `pricing.currency` to `createCheckoutSession()`; the BE picks the correct price ID from env. **(Unchanged from skill.)**
- **LD-9** PostHog `payment_completed` and `checkout_started` events emit `currency` as a property. **(Unchanged from existing telemetry — see Pricing.tsx:147, Pricing.tsx:169.)**

### §3.1 Country → currency mapping

Single function in `geo_pricing_service.get_pricing(ip_address: str) -> dict`. Maps `country == "IN"` → INR pricing dict; everything else → USD pricing dict. Pricing dicts defined in `_PRICING` constant in the same module. Adding a third currency requires (a) new `_PRICING` entry, (b) new `STRIPE_PRO_PRICE_ID_<CCY>` env var, (c) new branch in `get_pricing`, (d) skill update — out of scope here per LD-1.

### §3.2 Cache key and TTL

- Success-path: `setex("geo_pricing:{ip}", 86_400, json)`. **Per LD-3.**
- Failure-path: `setex("geo_pricing:{ip}", 60, json)`. **Per LD-4.** Distinguished from success-path by the `country` resolution outcome — see §5.

### §3.3 Stripe price ID routing

`get_pricing` returns `stripe_price_id` populated from `settings.stripe_pro_price_id_inr` (when `country == "IN"`) or `settings.stripe_pro_price_id` (otherwise). `usePricing()` exposes this on the hook return; `createCheckoutSession()` passes `pricing.currency` to the BE which selects the same price ID via the same env mapping. Single source of truth for the IN/USD split is the `country == "IN"` check.

## §4 API Contract

### §4.1 `GET /api/v1/payments/pricing`

**Auth:** none — public endpoint.

**Request:** no body, no query params. Client IP is read from `request.client.host` (or `X-Forwarded-For` first hop in deployed envs).

**Response shape (200 OK):**

```json
{
  "currency": "inr" | "usd",
  "price": 999 | 49,
  "price_display": "₹999/mo" | "$49/mo",
  "stripe_price_id": "price_..."
}
```

`price` is the numeric major-unit value for Pro. `price_display` is the rendered string Pro consumers should display. `currency` is the Stripe-API-compatible currency code. `stripe_price_id` is the Stripe price ID for the Pro tier in the resolved currency.

**The response shape carries Pro-tier values only.** Free-plan rendering does not consume this endpoint per LD-6 / §6.

**Failure modes:** the endpoint never raises; on Redis outage or ip-api failure it returns the USD pricing dict with a fresh-from-source `_lookup_country` attempt. See §5.

### §4.2 Frontend hook contract — `usePricing()`

```ts
export interface Pricing {
  currency: string         // 'inr' | 'usd'
  price: number            // 999 | 49
  price_display: string    // '₹999/mo' | '$49/mo'
  stripe_price_id: string  // 'price_...'
}

export function usePricing(): { pricing: Pricing; isLoading: boolean }
```

`pricing` defaults to USD shape until the fetch resolves (no placeholder flicker). On fetch failure, USD defaults are kept. **No Free-plan fields on this interface per LD-6.** The hook stays Pro-tier-only.

### §4.3 No schema changes, no new endpoints, no migrations

Spec is fully covered by existing endpoint + existing hook. Per-gap impl slices are FE-only (Gaps B, E) or BE-internal-only (Gap D — TTL constant change in `geo_pricing_service.py`).

## §5 Failure Handling — Gap D Resolution

The audit (`docs/audit/2026-04-E-020-geo-pricing.md` Gap D row) identified the bug shape with line-cites:

- **`geo_pricing_service.py:49-61`** — `_lookup_country(ip)` catches every exception path (timeout, rate-limit, malformed response) and returns `None`. **This is the documented contract per skill line 23 and stays unchanged.**
- **`geo_pricing_service.py:64-94`** — `get_pricing` builds USD result when `country != "IN"`, including the `country is None` branch. **This is by-design per skill and stays unchanged.**
- **`geo_pricing_service.py:97-101`** — `r.setex(cache_key, _GEO_CACHE_TTL, json.dumps(result))` fires UNCONDITIONALLY after country resolution, including when `country` was `None`. **THIS IS THE BUG.** The 86,400s TTL means a transient ip-api hiccup locks the affected Indian IP to USD pricing for 24 hours.

**Per LD-3 hard-lock from this spec's prompt:** USD-on-rate-limit fallback is by-design and stays. Cache-poisoning of failure results at the same 86,400s TTL as success is the bug.

### §5.1 Locked behavior

- When `_lookup_country` returns a non-None country, cache the result under `geo_pricing:{ip}` with TTL = **86_400s (24h)**. **(Unchanged.)**
- When `_lookup_country` returns `None`, cache the USD-fallback result under `geo_pricing:{ip}` with TTL = **60s**. **(NEW.)**
- Both cache writes use the same key; the second write supersedes the first when the TTL expires and a fresh lookup succeeds (or fails again).

### §5.2 Per-IP cache architecture (anchors the TTL tradeoff)

The Redis cache is **keyed by client IP**, not by ip-api response volume. Successful lookups cache 24h per IP and **do not re-call ip-api** within that window. The ip-api 45 req/min rate-limit is a property of the **backend egress IP**, not per user — every cache miss across all SkillForge users contributes to the same per-minute budget. The TTL on failure-cached entries therefore governs only:

1. How long a USD-fallbacked Indian user waits before the system retries country resolution for them.
2. The marginal increase in cache-miss volume from failure-IPs cycling more frequently than success-IPs.

At 60s failure-TTL, an Indian user on a transient rate-limit returns to INR pricing within one minute (next page-load, next `usePricing()` mount, etc.). The marginal cache-miss volume from failure-IPs is bounded by the failure rate — at expected scale this is well under the 45 req/min ip-api budget. **Per LD-4 and DD-2 chat-side decision (60s wins on user-experience grounds; cost is acceptable at expected scale).**

### §5.3 No retry inside `_lookup_country`

Per skill — `_lookup_country` is single-attempt. Adding HTTP-level retries inside the function would change the latency profile of the `/payments/pricing` endpoint and is out of scope here. The 60s failure-TTL achieves retry semantics at the cache layer instead.

## §6 Free-Plan Rendering — Gap E Resolution

The audit (`docs/audit/2026-04-E-020-geo-pricing.md` Gap E row) identified the bug shape with line-cites:

- **`Pricing.tsx:245`** — `priceSymbol = plan.planKey === 'pro' && pricing.currency === 'inr' ? '₹' : '$'`. The rupee symbol is gated on plan-being-Pro; Free always gets `$`.
- **`Pricing.tsx:240-243`** — only the Pro plan gets `pricing.price` swapped in; Free uses the static `price: 0` literal.
- **`Pricing.tsx:335`** — renders `{priceSymbol}{plan.price}` → `$0` for Free, regardless of detected currency.
- **`LandingPage.tsx:498`** — literal hardcoded `$0` for the Free card. Not routed through `usePricing()` at all.

Net effect for an INR-detected user on `/pricing`: `$0` (Free) next to `₹999/mo` (Pro) on the same surface. Mixed-currency rendering is the actual UX bug.

**Per LD-4 hard-lock from this spec's prompt and DD-1 chat-side decision (option A):**

### §6.1 Locked behavior — render literal `Free`

- Free-plan price display on `Pricing.tsx`: render the literal string `Free` in place of `{priceSymbol}{plan.price}`. Drop the `priceSymbol` ternary entirely for the Free card; drop the numeric `0` render.
- Free-plan price display on `LandingPage.tsx`: render the literal string `Free` in place of the hardcoded `$0`.
- Period text (`/forever` on LandingPage; empty on Pricing) is locked to whatever copy is currently on disk for the Free card. No copy change in the period field.

### §6.2 Why literal `Free` (rationale anchor)

Zero is currency-invariant: there is no semantic difference between `$0`, `₹0`, and `Free` for a tier with no charge. The actual UX bug is mixed-currency rendering on the same page (Free=`$0` next to Pro=`₹999/mo`), which the literal `Free` resolves by removing the currency-symbol render entirely from the Free path. The `usePricing()` hook stays Pro-tier-only per §4.2; extending it with a Free-tier shape would over-couple the hook to a tier that has no currency-routing requirement.

### §6.3 Explicitly rejected variant — `Free (no charge)`

Adds words for no clarity gain. The literal `Free` is unambiguous in context (sits inside a card titled "Free" with feature bullets and CTA). **Do not ship this variant.**

### §6.4 Surfaces enumerated

The audit found exactly two surfaces hardcoding `$0` for Free:

- `hirelens-frontend/src/pages/Pricing.tsx` (line 245 priceSymbol gate + line 335 render)
- `hirelens-frontend/src/pages/LandingPage.tsx` (line 498 literal `$0`)

If a third surface is discovered during impl, it ships as part of the same impl slice — no separate row.

## §7 Entry-Surface Coverage — Gap B Resolution

The audit (Gap B row) confirmed `LoginPage.tsx` returns ZERO matches for `usePricing|pricing|INR|USD|country|price` against current HEAD. Re-verified against the B-050 prior audit (commit `f7e4c0b`, 2026-04-26) — finding holds.

### §7.1 Locked behavior — usePricing on every entry surface

Per LD-7, every entry surface that displays Pro pricing MUST consume `usePricing()`. Auth surfaces count as entry surfaces:

| Surface | File | Currently consumes `usePricing`? | Required by this spec? |
|---|---|---|---|
| Landing | `src/pages/LandingPage.tsx` | ✅ (line 6, 34) | ✅ (no change) |
| Pricing | `src/pages/Pricing.tsx` | ✅ (line 10, 130) | ✅ (no change) |
| Paywall modal | `src/components/PaywallModal.tsx` | ✅ (line 18, 81) | ✅ (no change) |
| Login | `src/pages/LoginPage.tsx` | ❌ — **ADD** | ✅ — **NEW** |
| Register | (audit did not enumerate; impl slice verifies on disk) | ❓ | ✅ if exists on disk; no-op if not |

### §7.2 Placement on `LoginPage.tsx`

Spec is neutral on exact placement — impl slice picks based on existing layout. Acceptable shapes:

- A small inline price hint near the sign-in CTA ("Pro: ₹999/mo" / "Pro: $49/mo").
- A footer chip below the auth form.
- Whatever fits the existing visual rhythm — Dhamo product call at impl time.

What's mandatory: `LoginPage.tsx` consumes `usePricing()` and renders `pricing.price_display` somewhere visible above the fold. Pure import-without-render does not satisfy LD-7.

### §7.3 Register page

Audit did not enumerate a separate Register page. Impl slice greps for any `/register` or `/signup` route component on disk. If found, same rule applies. If not (i.e., LoginPage handles both sign-in and sign-up), no-op.

## §8 Acceptance Criteria

### Cluster B — Gap B (LoginPage)

- **AC-B-1** `LoginPage.tsx` imports `usePricing` from `@/hooks/usePricing`.
- **AC-B-2** `LoginPage.tsx` renders `pricing.price_display` somewhere in the rendered JSX (visible above the fold, not behind a conditional that hides it on the default render).
- **AC-B-3** No hardcoded price strings (`$49`, `₹999`, etc.) anywhere in `LoginPage.tsx`. Grep returns zero matches for `\$49|₹999|\\u20b9999`.
- **AC-B-4** Vitest test renders `LoginPage` with `usePricing` mocked to return INR shape; asserts `₹999/mo` appears in the rendered output. Symmetric test for USD shape asserts `$49/mo`.

### Cluster D — Gap D (failure-cache TTL)

- **AC-D-1** `geo_pricing_service.py` defines a new constant `_GEO_FAIL_CACHE_TTL = 60` (seconds) alongside the existing `_GEO_CACHE_TTL = 86_400`.
- **AC-D-2** `get_pricing` cache-write step branches on country resolution outcome: success-path uses `_GEO_CACHE_TTL`; failure-path (country resolved as `None`) uses `_GEO_FAIL_CACHE_TTL`.
- **AC-D-3** New pytest case in `tests/test_geo_pricing.py::TestRedisCache` asserts `setex` is called with TTL `60` when `_lookup_country` returns `None`, and TTL `86_400` when `_lookup_country` returns `"IN"` or `"US"`.
- **AC-D-4** Existing `TestGeoAPIFailure::test_api_failure_defaults_to_usd` continues to pass — USD-on-fallback semantics unchanged.

### Cluster E — Gap E (Free literal)

- **AC-E-1** `Pricing.tsx` renders the literal string `Free` in place of `{priceSymbol}{plan.price}` for the Free card. The `priceSymbol` ternary is removed or short-circuited for `plan.planKey === 'free'`.
- **AC-E-2** `LandingPage.tsx` renders the literal string `Free` in place of the previous hardcoded `$0` for the Free card.
- **AC-E-3** Vitest test renders `Pricing` with `usePricing` mocked to INR; asserts the rendered output contains literal `Free` AND does NOT contain `$0`, `₹0`, or any digit-followed-by-currency-symbol for the Free card region.
- **AC-E-4** Symmetric Vitest test for `LandingPage`.
- **AC-E-5** No regression in the Pro card — `Pricing.tsx` and `LandingPage.tsx` continue to render `pricing.price_display` for Pro under both INR and USD mocks.

### Cluster Cross — spec-wide

- **AC-X-1** `.agent/skills/geo-pricing.md` is updated to reference this spec at the top (one-line cross-ref). Skill stays the implementation pattern reference; spec is the behavior contract reference.
- **AC-X-2** `docs/PHASE-5-STATUS.md` rows 5.3 + 5.13 + line 100 are updated to cite this spec — flip rows from 🟡 PARTIAL to ✅ once all three impl-slice clusters ship (not before; tracked at row level by impl slices).

## §9 Open Questions

**None.** DD-1 (literal `Free`), DD-2 (60s failure-TTL), DD-3 (Out-of-Scope confirmation including new item (e) Stripe-hosted checkout) all resolved chat-side at slice start. §10 reflects DD-3.

## §10 Out of Scope

Per DD-3 chat-side confirmation:

- **(a)** Anonymous-scan abuse paths (playbook 1.14) — orthogonal surface, separate scope.
- **(b)** Plan-tier-specific pricing logic beyond the existing USD/INR routing — single Pro tier, no annual / team / enterprise tiers in scope here.
- **(c)** Currency support beyond USD + INR — no EUR / GBP / CAD / etc. Adding a third currency is a new spec.
- **(d)** Backfilling historical PostHog data with currency dimension — `currency` property is forward-only; existing events without it stay as-is.
- **(e)** Stripe-hosted checkout pages — currency display in Stripe Checkout is governed by the Stripe price ID, not by SkillForge code. Stripe's UI is out of this spec's scope; not a bug to fix here.

## §11 Rollout — Three Follow-Up Impl Slices

**Per LD-7 from the slice prompt: this spec does not name BACKLOG IDs for the impl slices.** IDs are filed at impl-slice time per R17 watermark check. The sketches below are scope guidance only.

### §11.1 Gap B impl slice — `LoginPage.tsx` `usePricing` consumer

- Mode 2 (impl-to-existing-spec, this spec).
- Files: `src/pages/LoginPage.tsx` (add import + hook call + render); test file (new or existing).
- AC anchor: §8 Cluster B (AC-B-1..AC-B-4).
- Effort: small (~half-day).
- Optional: `src/pages/RegisterPage.tsx` if it exists on disk per §7.3.

### §11.2 Gap D impl slice — failure-cache TTL refinement

- Mode 2 (impl-to-existing-spec).
- Files: `hirelens-backend/app/services/geo_pricing_service.py` (add `_GEO_FAIL_CACHE_TTL` constant + branch cache-write); `hirelens-backend/tests/test_geo_pricing.py` (add TTL-on-failure test); `.agent/skills/geo-pricing.md` (one-line caching-section amend distinguishing success vs failure TTL).
- AC anchor: §8 Cluster D (AC-D-1..AC-D-4).
- Effort: small (~half-day).

### §11.3 Gap E impl slice — Free literal on Pricing + Landing

- Mode 2 (impl-to-existing-spec).
- Files: `src/pages/Pricing.tsx` (Free card render path); `src/pages/LandingPage.tsx` (Free card price line); test files (one per surface).
- AC anchor: §8 Cluster E (AC-E-1..AC-E-5).
- Effort: small (~half-day).

### §11.4 Phase-5-status sweep slice (after all three above ship)

- Mode 1 (doc-only).
- Files: `docs/PHASE-5-STATUS.md` rows 5.3 + 5.13 + line 100; flip 🟡 → ✅; cite the three impl SHAs.
- E-020 row Notes column: append closing summary; flip 🟡 → ✅.
- Effort: tiny.

The three impl slices are independent and can land in any order. The phase-5-status sweep is the final gate that flips E-020 ✅.

## §12 References

### Originating BACKLOG rows (verbatim quotes)

> **E-020** | results | Audit geo-pricing visibility on signup vs checkout | P1 | 🟡 | docs/specs/phase-5/27-geo-pricing.md | P5-S8 | Audit-only first; fix gaps in follow-up. **Re-verified 2026-04-26 (`4aaeda4`): see `docs/audit/2026-04-E-020-geo-pricing.md` (slice B-054).** … (truncated; full row in `BACKLOG.md` line 116)

> **E-023** | docs | Backfill spec — Geo-based pricing | P3 | 🔴 | docs/specs/phase-5/27-geo-pricing.md | P5-S3 | Optional. *(Closes ✅ on this slice's merge — this spec IS the backfill it tracked.)*

### Cited audit (verified on disk)

- `docs/audit/2026-04-E-020-geo-pricing.md` (commit `4aaeda4`) — re-verified Gap B + D + E + Finding 0 against HEAD `bd9f662`.

### Cited skill (verified on disk)

- `.agent/skills/geo-pricing.md` — implementation pattern reference. Stays authoritative for *how*; this spec is authoritative for *what*.

### Cited PHASE-5-STATUS rows

- `docs/PHASE-5-STATUS.md` row 5.3 (geo-based pricing — 🟡 PARTIAL).
- `docs/PHASE-5-STATUS.md` row 5.13 (geo-pricing on REGISTRATION page — 🟡 PARTIAL).
- `docs/PHASE-5-STATUS.md` line 100 — explicit enumeration of gaps B / D / E.

### Cited source files (verified on disk)

- `hirelens-backend/app/services/geo_pricing_service.py` — `_lookup_country` (line 49-61), `get_pricing` (line 64-103), cache-write (line 97-101).
- `hirelens-backend/tests/test_geo_pricing.py` — `TestGeoAPIFailure::test_api_failure_defaults_to_usd` (line 50-58), `TestRedisCache::test_pricing_cached_in_redis` (line 64-92).
- `hirelens-frontend/src/hooks/usePricing.ts` — hook contract (line 18-38).
- `hirelens-frontend/src/pages/Pricing.tsx` — Free render path (line 240-245, line 335).
- `hirelens-frontend/src/pages/LandingPage.tsx` — Free hardcoded `$0` (line 498).
- `hirelens-frontend/src/pages/LoginPage.tsx` — current zero `usePricing` consumption.

### Related BACKLOG rows

- **B-054** (closed `4aaeda4`, 2026-04-26) — audit slice that produced this spec's input.
- **B-050** (closed `f7e4c0b`, 2026-04-26) — prior phase-5 partial-items audit; first verified Gap B HIGH-confidence.
- **B-031** (closed `2080577`, 2026-04-23) — free-tier scan lifetime cap. Tangential (different surface, same `Pricing.tsx` consumer).

### Drift / amendments

*(None at authoring. Future amendments append below this line in their own subsection per spec #60 §9 convention.)*
