# E-020 Geo-Pricing Deferred Gaps Re-Verification — 2026-04-26

**HEAD at audit:** `bd9f662`
**Mode:** audit-only (Mode 3). R14 exception (a) regenerated audit artifact. Zero code, zero spec edits, zero status flips on E-020 or any other row.
**Source-of-truth:** trio substitution per Option A — `.agent/skills/geo-pricing.md` + `docs/PHASE-5-STATUS.md` rows 5.3 + 5.13 + line 100 + `SESSION-STATE.md` Known-Broken table (line 598). Spec `docs/specs/phase-5/27-geo-pricing.md` does not exist on disk; substitution made per B-050 precedent (`docs/audit/2026-04-partial-audit.md`).
**Slice ID:** B-054.

## Pre-flight notes

- **HEAD `bd9f662`** matches the `ffd66f7 → bd9f662` chain in the prompt.
- **R17 watermark:** B-053 highest in-use → B-054 free.
- **Working-tree dirt:** `.DS_Store`, `Enhancements.txt`, `hirelens-backend/scripts/wipe_local_user_data.py` (long-standing modified set; untouched per C2). Untracked `.agent/skills/{stripe-best-practices,stripe-projects,upgrade-stripe}/` already surfaced under B-049 §10 finding; remaining untracked items (`.gitattributes`, `docs/audits/`, `docs/status/E2E-READINESS-2026-04-21.md`, `skills-lock.json`) are bookkeeping debris from concurrent sessions, outside this slice's blast radius — paper-trailed here only, not logged to the SESSION-STATE drift ledger per slice-prompt direction.
- **SOP-8 concurrent-session check:** no commits between `bd9f662` and slice start.
- **N1-SUPPLEMENT (spec #27):** caught at SOP-5 → STOP issued → Option A authorized by chat-side → trio substituted. Recovery shape mirrors B-050.

## Finding 0 — spec #27 path stale on E-020 row since filing (HIGH confidence drift)

**Symptom.** `BACKLOG.md` E-020 row Spec column reads `docs/specs/phase-5/27-geo-pricing.md`. The file does not exist on disk. Phase-5 spec numbering jumps from `22-plan-aware-missing-skills-cta.md` to `34-persona-picker-and-home.md` — the 23-33 range is empty. The same phantom path is referenced from the E-023 backfill-spec row (`Backfill spec — Geo-based pricing | docs/specs/phase-5/27-geo-pricing.md`).

**Verdict.** HIGH-confidence drift. The path has been aspirational since the row was filed; both the audit-tracker E-020 row and the backfill-tracker E-023 row reference the same non-existent file.

**Recommended close shape.** Two paths, not mutually exclusive:

- **(a) Author spec #27 in a follow-up Mode 4 slice** that consolidates the trio (skill + PHASE-5-STATUS + SESSION-STATE) plus this audit's findings into a single canonical spec. Closes E-023 by construction. Then the gap-B / gap-D / gap-E follow-up slices can cite spec #27 §X cleanly.
- **(b) Amend E-020's spec citation** to point at `.agent/skills/geo-pricing.md` as authoritative for now (skill is on-disk and accurate; spec is missing). Defers E-023 closure; cheaper as a one-line BACKLOG edit but leaves the source-of-truth split between skill + audit doc + PHASE-5-STATUS.

**Confidence:** HIGH (verified by `ls docs/specs/phase-5/` + `grep 27-geo BACKLOG.md` — two stale citations on disk).

## Truth table

| Gap | Original symptom (verbatim from prompt + SESSION-STATE line 598) | On-disk evidence | Verdict | Confidence |
|---|---|---|---|---|
| **B** | "no price on LoginPage" | **`hirelens-frontend/src/pages/LoginPage.tsx`:** grep returns ZERO matches for `usePricing\|pricing\|INR\|USD\|country\|price` against the 118-line file. **`usePricing` consumers (full list):** `src/hooks/usePricing.ts` (definition), `src/components/PaywallModal.tsx:18`, `src/pages/Pricing.tsx:10`, `src/pages/LandingPage.tsx:6`. LoginPage is not in the consumer list. **Cross-check:** B-050 audit (commit `f7e4c0b`, 2026-04-26) already established this finding with HIGH confidence; re-verified against current HEAD `bd9f662`, no commits to `LoginPage.tsx` since. **PHASE-5-STATUS.md row 5.13:** explicitly carries this gap as 🟡 PARTIAL with the same symptom language. | **CONFIRMED-STILL-OPEN.** Gap real on current HEAD. Tracked at E-020 deferred gap B. | HIGH — deterministic grep + B-050 prior verification + PHASE-5-STATUS row 5.13 carrying the same wording. Three independent sources concur. |
| **D** | "ip-api.com rate-limit fallback mis-prices Indian users under load" | **`hirelens-backend/app/services/geo_pricing_service.py`:** `_lookup_country` (line 49-61) catches every exception path (timeout, rate-limit, malformed response) and returns `None`. `get_pricing` (line 64-103) builds `result` from `_PRICING["inr"]` only when `country == "IN"` (line 85-89); every other branch — including `None` — falls through to `_PRICING["usd"]` (line 90-94). This is consistent with the `.agent/skills/geo-pricing.md` line 23 rule: *"Failure modes (timeout, rate limit, bad IP) → fall through to USD."* **CRITICAL secondary finding:** the cache write at line 97-101 fires UNCONDITIONALLY after country resolution — including when `country` was `None`. The USD-on-failure result gets `setex`'d into Redis under `geo_pricing:{ip}` with the same 86,400s (24h) TTL as a success result. So a transient ip-api rate-limit on an Indian IP's first request locks that IP to USD pricing for 24 hours, even after rate-limit clears. **Test coverage:** `hirelens-backend/tests/test_geo_pricing.py::TestGeoAPIFailure::test_api_failure_defaults_to_usd` (line 50-58) explicitly tests the USD-on-None fallback as expected behavior; `TestRedisCache::test_pricing_cached_in_redis` (line 64-92) tests success-path caching, but no test covers the failure-path-cache-poison case. | **REFINEMENT, not a single bug.** The framing is partially mislabeled: (a) USD-on-fallback is **BY DESIGN** per skill + test — the symptom misreads it as a bug, when it's the spec'd contract. **(b) The actual latent failure mode is cache-poisoning of failure results** — failure results get a 24h TTL, so a transient ip-api hiccup degrades the experience for the affected Indian IP for the full TTL. The fix space is "don't cache failure results" or "use a short TTL on fallback path" or "double-resolve country on cache hit before serving USD" — NOT "stop falling back to USD." | HIGH — read service + test + skill rule; cache-write line is unconditional on country resolution success. Three independent code-path reads concur. |
| **E** | "Free-plan shows `$0` even for INR users" | **`hirelens-frontend/src/pages/Pricing.tsx`:** `plans` array (line 68-116) declares Free with `price: 0, period: ''` as a static literal. Render-time override (line 240-243) only swaps in `pricing.price + '/mo'` for Pro; Free uses the base literal. `priceSymbol` (line 245) is keyed off `plan.planKey === 'pro' && pricing.currency === 'inr' ? '₹' : '$'` — i.e., the rupee symbol is gated on plan-being-Pro. Free-plan render at line 335 (`{priceSymbol}{plan.price}`) ALWAYS renders `$0`, regardless of `pricing.currency`. **`hirelens-frontend/src/pages/LandingPage.tsx`:** Free plan rendering at line 498 hardcodes literal `$0` followed by `/forever` — not routed through `usePricing` at all. **Substantive, not cosmetic:** for an INR-detected user on `/pricing`, the page renders `$0` (Free) next to `₹999/mo` (Pro) — mixed currency on the same surface. On `/` (LandingPage), the Free card is `$0` regardless. **Free-plan currency rendering is not addressed anywhere in the on-disk substitute trio:** geo-pricing skill names only Pro pricing rules; PHASE-5-STATUS row 5.3 enumerates the gap as deferred without prescribing fix; SESSION-STATE Known-Broken describes the symptom only. | **CONFIRMED-STILL-OPEN.** Gap real and reproduces on TWO surfaces (Pricing.tsx + LandingPage.tsx); both hardcode `$` for Free. Net effect for INR users on `/pricing` is mixed-currency rendering (Free=`$0`, Pro=`₹999/mo`) on the same page. | HIGH — read both render sites + the priceSymbol gating expression; reproduction is deterministic from code. |

## Per-gap recommendations

### Gap B recommendation

- **LD-5(i) coverage in trio:** `.agent/skills/geo-pricing.md` line 17 names the consumers ("Used by: `src/pages/LandingPage.tsx`, `src/components/PaywallModal.tsx`") and line 73-74 establishes the rule *"Never hardcode a price in the frontend or in any marketing component — always go through `usePricing()`."* PHASE-5-STATUS row 5.13 explicitly carries the gap as 🟡 PARTIAL. The skill does NOT mandate LoginPage as a pricing consumer, so the gap is a missing-coverage call (auth surface = marketing surface for logged-out flow), not a violation of the skill's existing rules.
- **LD-5(ii) spec amendment vs existing prescription:** the trio does NOT prescribe LoginPage entry-surface pricing display. Either spec #27 needs authoring (and would naturally include this surface) or the skill's "Used by" list needs an additive entry.
- **LD-5(iii) recommended mode:** **Mode 4 spec-amend-then-impl** if the team wants spec #27 authored before the fix; otherwise **Mode 2 impl-to-existing-skill** with a one-line skill amendment. Lean: Mode 4 (folds Finding 0 into the same slice).

### Gap D recommendation

- **LD-5(i) coverage in trio:** `.agent/skills/geo-pricing.md` line 23 explicitly establishes USD-on-failure as the contracted fallback. The cache-poison sub-finding is NOT covered — the skill's "Redis Caching" section (line 42-47) describes TTL and key shape but does NOT distinguish success-cache vs failure-cache TTL semantics.
- **LD-5(ii) spec amendment vs existing prescription:** the USD-on-failure rule is documented; the cache-poison failure mode is undocumented. A spec amendment IS needed before fixing the cache-poison sub-finding, otherwise the fix would silently change the on-disk-documented contract for "what's cached and for how long."
- **Reconciliation note (per slice-prompt LD-5 amendment):** the original symptom is partially mislabeled — Indian-user-sees-USD-on-rate-limit is **(a) the intended behavior the symptom mislabels as a bug** for the immediate request, AND **(b) a separate failure mode beyond the documented fallback** for the next 24h of cache-served requests from the same IP. The audit reports both verdicts; the fix decision is product's call.
- **LD-5(iii) recommended mode:** **Mode 4 spec-amend-then-impl** — amend the skill's caching section to distinguish success-TTL from fallback-TTL, then ship the cache-key/TTL refinement.

### Gap E recommendation

- **LD-5(i) coverage in trio:** **NONE.** As authorized by the slice prompt, LD-5(i) is relaxed for Gap E. The geo-pricing skill explicitly addresses only Pro pricing (line 6-11, line 25-40); Free-plan rendering is outside its scope. PHASE-5-STATUS row 5.3 enumerates the gap symptom but prescribes no fix. SESSION-STATE Known-Broken states the symptom only.
- **LD-5(ii) spec amendment vs existing prescription:** **No on-disk artifact covers Free-plan currency rendering; needs spec authoring or amendment before fix.** The fix space includes product judgment (literal "Free" vs `₹0` for INR vs `$0` everywhere) that the skill cannot adjudicate.
- **LD-5(iii) recommended mode:** **Mode 4 spec-author candidate, not Mode 2 impl.** The product question (does Free render as a price-formatted "₹0" / "$0" routed through `usePricing`, OR as a literal "Free" with no numeric price, OR as "Free / Always" copy?) is genuine design surface, not a refactor-of-existing-prescription. Spec #27 (per Finding 0 path (a)) should cover this OR a focused spec authored per LD-5(iii).

## Summary counts

| Verdict | Count | Items |
|---|---|---|
| CONFIRMED-STILL-OPEN | **2** | Gap B, Gap E |
| REFINEMENT (partial-design / partial-bug) | **1** | Gap D |
| RESOLVED-ON-DISK | 0 | — |
| Drift findings (above the truth table) | **1** | Finding 0 (spec #27 phantom path) |
| Newly-surfaced gaps with HIGH confidence beyond B/D/E | 0 | — |

**Net signal:** Three gaps reproduce as filed; one (Gap D) needs framing reconciliation between symptom and on-disk contract. No fourth USD-hardcoded surface surfaced beyond the two already enumerated under Gap E (Pricing.tsx + LandingPage.tsx — both Gap E, not net-new). Per LD-4, no additional BACKLOG row beyond B-054 is filed.

## Recommended next-slice order

1. **Mode 4 spec-author slice** for spec #27 — consolidate the trio + this audit's findings into a single canonical spec. Closes Finding 0; provides clean LD-5(i) anchors for B/D/E follow-up. **Confidence HIGH.** Effort: medium (~1 day).
2. **Gap B impl slice** (after spec #27) — `Mode 2 impl-to-spec`. Add `usePricing` consumer to `LoginPage.tsx`; render country-localized price near the sign-in CTA per spec #27 §X. Test count delta: small. **Confidence HIGH on the gap; medium on UX placement** (Dhamo product call where exactly on LoginPage to show the price). Could fold into spec #27 slice if scope tolerates.
3. **Gap D impl slice** (after spec #27 amends the caching section) — refine `geo_pricing_service.py` to either skip caching on `country is None` OR cache fallback results with a short TTL (60-300s). Add a regression test against `tests/test_geo_pricing.py`. **Confidence HIGH on the diagnosis and fix space; medium on TTL value** (Dhamo product call).
4. **Gap E impl slice** — gated on spec #27 prescribing the Free-plan rendering shape (literal "Free" vs `₹0` vs other). Touches both `Pricing.tsx` (line 245 priceSymbol gate + line 240-243 plan-override) and `LandingPage.tsx` (line 498 hardcoded `$0`). **Confidence HIGH on reproduction; recommendation depends on spec.**

If spec #27 authoring is judged too heavy for the immediate ROI, Finding 0 path (b) (one-line E-020 spec citation amend to point at the skill) unblocks Gaps B + D as Mode 2 slices; Gap E still needs spec authoring before impl.

## SOP gates passed at slice start

- SOP-1 ✅ HEAD `bd9f662` matched prompt.
- SOP-2 ⚠️ working-tree dirt is the long-standing modified set; untracked items outside the long-standing list paper-trailed here per slice-prompt direction (no SESSION-STATE drift-ledger edit).
- SOP-3 — N/A (audit-only, no test runs).
- SOP-4 — `geo-pricing.md` skill loaded; `payments.md` available but not directly cited (geo-pricing scope only).
- SOP-5 ❌→ **recovered**: cited file `docs/specs/phase-5/27-geo-pricing.md` missing; chat-side substituted the trio (skill + PHASE-5-STATUS + SESSION-STATE) per B-050 precedent (Option A). LD-5(i) relaxed for Gap E.
- SOP-6 / R17 ✅ B-053 highest in-use, B-054 free at slice start.
- SOP-8 ✅ no concurrent commits since `bd9f662`.
- SOP-9 ✅ single CC session on this tree.
- N1-SUPPLEMENT ❌→ **recovered**: spec #27 missing-on-disk caught at SOP-5; STOP issued; Option A authorized by chat-side; substitute trio loaded.
- R19 ✅ stops invoked correctly at scope-divergence catch.

## Files touched

- `docs/audit/2026-04-E-020-geo-pricing.md` (new file, this artifact).
- `BACKLOG.md` — E-020 Notes column update (audit-complete marker + findings summary + audit-doc path); B-054 row filed in main table as ✅; B-054 Closed-table entry. Per LD-1, **E-020 status NOT flipped** (stays 🟡); only the Notes column is amended per LD-3(a).

Doc-only; no code; no spec; no tests run. R14 exception (a) regenerated audit artifact. Two-commit pattern (impl + SHA backfill) per R15(c) precedent (B-039 / B-045 / B-048 / B-049 / B-050 / B-051 / B-053).

---

*Audit complete. No code changed. No status flipped on E-020 (per LD-1, propose-only). Next: chat-Claude to review per-gap recommendations and either (a) green-light Mode 4 spec-author slice for spec #27, (b) green-light Finding-0 path-(b) one-line BACKLOG amend + Gap-B/D Mode 2 slices, or (c) confirm a different disposition.*
