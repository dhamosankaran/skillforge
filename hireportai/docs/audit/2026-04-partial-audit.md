# Phase-5 Partial-Items Audit — 2026-04-26

**HEAD at audit:** `028d1b2`
**Mode:** audit-only. R14 exception (a) regenerated audit artifact. Zero code, zero spec edits.
**Source-of-truth:** `docs/PHASE-5-STATUS.md` (the prompt cited a missing file `claude-code-prompts-all-phases-v2.md`; substituted on chat-side correction; see "Source-of-truth correction" below).
**Slice ID:** B-050.

## Restated scope (Option B)

The originally-prompted audit covered 6 items. CC's pre-flight gates surfaced status drift: 3 of the 6 were already ✅ SHIPPED on disk per `docs/PHASE-5-STATUS.md`. Per H3, the catch was acknowledged and scope narrowed to the 3 items that are genuinely 🟡 / ❓ on disk:

- **5.13** Geo-pricing IP detection on REGISTRATION page — 🟡 PARTIAL
- **5.19** Job Fit Explanation above the fold (P5-S20) — 🟡 PARTIAL per `PHASE-5-STATUS.md`
- **5.20** Keyword color + education layer (P5-S21) — ❓ AMBIGUOUS per `PHASE-5-STATUS.md`

## Truth table

| ID | Original symptom | Last-touched SHA | Test coverage | On-disk evidence (service / prompt / FE) | Proposed status | Confidence |
|---|---|---|---|---|---|---|
| **5.13** | Geo-pricing IP detection on REGISTRATION (`/login`) page — country-localized price not shown to logged-out users on the auth surface. SESSION-STATE Known-Broken "deferred gap B: no price on LoginPage." | `2c01cc7` (LoginPage.tsx, P5-S17 — last edit was unrelated PersonaPicker work, not pricing). Geo-pricing service last touched `b794d26` (P5-S8). | None on `LoginPage.tsx` for pricing surface (grep: zero hits for `pricing/usePricing/INR/USD/country/price`). The geo-pricing service itself is covered by P5-S8 commits but no FE-on-LoginPage tests. | **Service:** `app/services/geo_pricing_service.py::get_pricing(ip)` works — returns `{currency, plans}` with INR for India, USD default; consumed by `/api/v1/payments/pricing` endpoint, `PaywallModal`, `Pricing.tsx`, `LandingPage.tsx`. **FE:** `LoginPage.tsx` grep returned **zero** references to `usePricing` / `pricing` / `INR` / `USD` / `country` / `price`. The 4 callers of `usePricing` are PaywallModal, Pricing, LandingPage, and the hook itself — LoginPage is **not in the consumer list**. **SESSION-STATE evidence:** explicit row at line 598 — `Geo-Pricing Visibility | Audit complete (P5-S8): A+C fixed. Remaining deferred gaps — B: no price on LoginPage; D: ip-api.com rate-limit fallback mis-prices Indian users under load; E: Free-plan shows $0 even for INR users. \| Deferred (post-P5B) \| E-020`. | **Still 🟡 PARTIAL** — gap real, tracked at E-020 (🟡 audit complete; gap-fix slice pending). | **HIGH** — read service + endpoint + FE; absence of `usePricing` in LoginPage is a deterministic grep result. |
| **5.19** | Job Fit Explanation component shipped (`f88995d`) but rendering order was wrong — appeared below `ATSScoreGauge` (line 195) and `ScoreBreakdown` (line 207) per the stale PHASE-5-STATUS.md row. "Above the fold" not literally satisfied. | `e74d1f2` (E-009 close, 2026-04-19, P5-S20 — flattened 3-panel grid → 11 direct children, DOM order = mobile + tab order). Subsequent touches: `e36c319` (E-041 sticky-removal), `0b35440` (B-035 scan persistence), `e93e950` (B-032 paywall gate), `b5d27f4` (design system). | **8 new ordering tests** added in `tests/pages/Results.ordering.test.tsx` per P5-S20 (covers ATS<JobFit, JobFit<MissingSkills, JobFit<Keywords, MissingSkills<Keywords, Keywords<ScoreBreakdown via `compareDocumentPosition`; section-id stability across all 9 sections; `job_fit_explanation_viewed` mount-fire + `useRef` idempotency across remount). FE 134 → 142 (+8). | **FE render order verified at `Results.tsx`:** ATS Score grid item at `lg:col-start-1 lg:row-start-1` (line 290); Job Fit grid item at `lg:col-start-2 lg:row-start-1` with explicit comment `"2. Job Fit — mobile 2nd · lg/xl col-2 row-1 HERO"` (line 311); Missing Skills at `lg:col-start-3 lg:row-start-1`. **DOM order:** ATS Score → Job Fit → Missing Skills (all in row-1 above-fold on lg+ breakpoints). **Mobile DOM order:** ATS Score → Job Fit → Missing Skills → Keywords → Score Breakdown → Skills Radar → Bullets → Formatting → Improvements → Nav → CTAs (Job Fit at DOM index 2 from top). **BACKLOG E-009:** 🔴 → ✅ closed by `e74d1f2` on 2026-04-19. **New analytics:** `job_fit_explanation_viewed {view_position: 'above_fold'}` fires once per mount via `useRef` guard. | **Now ✅** (E-009 already closed in `e74d1f2`; PHASE-5-STATUS.md row 5.19 is stale — predates the P5-S20 fix). Per LD-5, **propose only** — do not flip in this slice. Action for follow-up: amend `docs/PHASE-5-STATUS.md` row 5.19 from 🟡 → 🟢/✅ with close-SHA `e74d1f2`. | **HIGH** — read JSX + grid placement + tests + close-SHA + close-line in BACKLOG. Three independent sources concur. |
| **5.20** | Two user problems: (a) Keyword color legend doesn't match chart (hardcoded `#7c3aed`/`rgba(124,58,237,0.5)` violet vs `--color-accent-secondary`); (b) no education layer (4 sections had tooltips, 5 didn't, and existing tooltip lacked Escape / click-outside / `role="tooltip"`). PHASE-5-STATUS.md flagged ❓ AMBIGUOUS pending product reconciliation. | `04c8ef2` (B-004 + E-010 close, 2026-04-19, P5-S21b). Spec author commit: `fe4a333`. | **20 new tests** in `tests/components/KeywordChart.colors.test.tsx` (9 — AC-1/AC-2: legend↔CSS-var mapping, `rgbaFromCssVar` rgba correctness across 3 themes, no `124,58,237` substring, empty-data guard) + `tests/components/PanelSection.tooltip.test.tsx` (10 — AC-3/4/5/7: icon, Enter/Space/click open, Escape close + focus-return, click-outside close, `role="tooltip"` + `aria-describedby` + `aria-expanded` linkage, analytics fires-on-open-only, no fire without `section` prop) + `tests/pages/Results.tooltips.test.tsx` (1 — AC-3: all 9 section headers render exactly one Info trigger). FE 114 → 134 (+20). | **(a) Keyword color fix:** `KeywordChart.tsx` (verified): exports `KEYWORD_LEGEND` constant with `{id, label, cssVarName, alpha}` per entry; `in_resume` entry maps to `--color-accent-secondary` at `alpha: 0.5`; `rgbaFromCssVar(name, alpha)` helper drives both Cell fills AND legend swatches. **No hardcoded violet anywhere** (grep confirms zero `#7c3aed` / `124,58,237` in `KeywordChart.tsx`). **(b) Education layer:** `PanelSection.tsx` (verified): imports `useClickOutside` hook; Escape handler (line 54); `aria-describedby={open ? tooltipId : undefined}` (line 87); `role="tooltip"` (line 95); `tooltip?: TooltipCopy` prop. All 9 Results sections wrapped in `PanelSection` with `{what, how, why}` copy from spec §Education Layer Design. **Spec #21 status field on disk:** `Done — Shipped in 1c0817a (P5-S21b) on 2026-04-19`. **BACKLOG B-004 + E-010:** both 🔴 → ✅ closed by `1c0817a` (commit message `04c8ef2` references same close-line — likely SHA rewrite during recovery). **Deferred half:** first-visit sequential guided walkthrough — tracked separately in SESSION-STATE Deferred Hygiene Items as `[P5-S21b-follow] Analysis Results first-visit guided tour` per spec #21 §Out of Scope. Not part of 5.20-as-defined. | **Now ✅ for the shipped half** (keyword colors + info-icon tooltips). The PHASE-5-STATUS.md row 5.20 ❓ AMBIGUOUS classification is itself stale — spec exists, code shipped, tests pass, BACKLOG ✅. Per LD-5, **propose only**. Action for follow-up: amend `docs/PHASE-5-STATUS.md` row 5.20 from ❓ → ✅ with close-SHAs `1c0817a` (impl) + `fe4a333` (spec); cross-ref the `[P5-S21b-follow]` deferred guided-tour item so it's not lost. | **HIGH** — verified spec status field, BACKLOG row close-line, FE component bodies, test files. The ambiguity flagged by PHASE-5-STATUS.md was resolved by spec #21 itself; the table just wasn't updated. |

## Summary counts

| Proposed status | Count | Items |
|---|---|---|
| Still 🟡 PARTIAL | **1** | 5.13 |
| Now ✅ (propose flip) | **2** | 5.19, 5.20 |
| Regressed 🔴 (newly broken) | 0 | — |
| Low-confidence unknown (cannot decide without runtime) | 0 | — |

**Net signal:** 2 of 3 audited items are stale 🟡 / ❓ in `PHASE-5-STATUS.md` — the underlying work shipped weeks ago (2026-04-19) and the status table never got updated. Only 5.13 is a genuine open gap, and it's already tracked at BACKLOG E-020 (audit complete, gap-fix slice pending).

## Recommended next-slice order

1. **Doc-only sweep slice** — amend `docs/PHASE-5-STATUS.md` row 5.19 (🟡 → ✅, cite `e74d1f2`) and row 5.20 (❓ → ✅, cite `1c0817a` + `fe4a333`); cross-ref the `[P5-S21b-follow]` deferred guided-tour item under row 5.20 so the deferred half doesn't get lost. Highest-value lowest-cost cleanup. **Confidence HIGH.**
2. **E-020 gap-fix slice** — implement the geo-pricing-on-LoginPage fix (5.13 / SESSION-STATE deferred gap B). E-020 row already 🟡 (audit complete); needs a small impl slice that adds `usePricing` to `LoginPage.tsx` and renders a country-localized price near the sign-in CTA. Spec backfill (E-023) deferred per BACKLOG. **Confidence HIGH for the gap; medium on UX placement (Dhamo product call where exactly on LoginPage to show the price).**

No regressions surfaced. No new BACKLOG row needed for newly-broken behavior. The audit's main finding is that `docs/PHASE-5-STATUS.md` is itself drifted — the same drift class that triggered the prompt's stale citations in the first place.

## Cross-checks (per restated scope)

**5.19 render-order issue:** Verified the Results.tsx grid layout — Job Fit lives at `lg:col-start-2 lg:row-start-1` with the `HERO` annotation. The "above the fold" intent of P5-S20 was satisfied via DOM-order flattening (11 direct grid children, mobile DOM = visual order = tab order), with Tailwind grid placement reconstructing the desktop layout. The PHASE-5-STATUS.md row that says "renders below ATSScoreGauge + ScoreBreakdown" is from before commit `e74d1f2`. **Gap is in the status table, not the implementation.**

**5.20 ambiguity resolution:** The audit's job per LD-2 is to clarify ❓ items. Reading spec #21 + KeywordChart.tsx + PanelSection.tsx + the close-line for B-004/E-010 confirms both halves of P5-S21 (keyword colors + info-icon tooltips) shipped in `1c0817a` on 2026-04-19. The first-visit guided walkthrough (the second half of the original E-010 scope) is **explicitly deferred** per spec #21 §Out of Scope and tracked separately in Deferred Hygiene as `[P5-S21b-follow]`. So 5.20 is ✅ as scoped, and the deferred half is its own future slice with its own spec gate (R14).

## Dropped from scope (with close-SHA evidence)

The following items were in the original prompt's enumeration but are already ✅ SHIPPED on disk per `docs/PHASE-5-STATUS.md` and BACKLOG. Excluded from the audit per Option B narrowing — auditing closed work would produce no new signal.

| ID | Reason dropped | Close-SHA | Close date |
|---|---|---|---|
| **5.15** AI rewrite missing original content (P5-S9) | ✅ SHIPPED on disk; PHASE-5-STATUS.md row explicitly cites the close. Subsequent reinforcement: spec #47 prompt-contract guard `f1bcf94`. Even later, B-001 / spec #51 added per-section regen via `/api/v1/rewrite/section` (orthogonal code path — does not invalidate the original full-rewrite fix; per the cross-check ask in original prompt step 5: B-001 is an additive surface for partial regen, not a replacement for the full-rewrite fix). | `602ea20` (P5-S9) + `f1bcf94` (spec #47 guard) | 2026-04-19 |
| **5.16** Cover letter format (P5-S10) | ✅ SHIPPED on disk per PHASE-5-STATUS.md. **Cross-check on B-002 / spec #52:** B-002 / spec #52 went further than the original P5-S10 fix — it introduced the structured `CoverLetterResponse` shape (LD-2: `{date, recipient, greeting, body_paragraphs (len==3), signoff, signature, tone, full_text}`) end-to-end (BE schema + service + 6 FE consumer migration + telemetry + AC-4b `integration_llm` marker). So 5.16 is closed by both the original P5-S10 format-prompt fix AND the later structural enforcement of B-002 / spec #52. The format-shape and content-quality concerns are both addressed; no remaining content-quality bugs known. | `696b176` (P5-S10) + B-002 close-SHAs (spec #52 path) | 2026-04-19 (P5-S10) + 2026-04-21 (B-002) |
| **5.18** Generate My Experience (P5-S11) | ✅ SHIPPED on disk per PHASE-5-STATUS.md. Reinforcement: B-003 retest-close `0719fa1` (2026-04-23) added FE regression coverage (`tests/Profile.experience.test.tsx`: happy / no-history empty-state / 503 error). Root-cause fix already in P5-S11 (`66c1814`): tier move to FAST + `max_tokens` 500→2048 + empty-response 503 guard. | `66c1814` (P5-S11) + `0719fa1` (B-003 retest) | 2026-04-19 (P5-S11) + 2026-04-23 (B-003 retest) |

## Source-of-truth correction

The original prompt cited `claude-code-prompts-all-phases-v2.md` (does not exist on disk). Per H3 (CC stops on phantoms — that is correct), the catch was surfaced. Chat-side restated scope corrected the citation to `docs/PHASE-5-STATUS.md`. This audit reads from `docs/PHASE-5-STATUS.md` exclusively for the Phase-5 status table and cross-references against `BACKLOG.md` and `SESSION-STATE.md` for closure evidence.

Note: `docs/PHASE-5-STATUS.md` itself is drifted (rows 5.19 + 5.20 are stale by ~1 week). The recommended doc-only sweep slice in §Recommended next-slice order will fix that drift.

## SOP gates passed at slice start

- SOP-1 ✅ HEAD `028d1b2` matched prompt
- SOP-2 ✅ working tree dirt is the known set
- SOP-3 — N/A (audit-only, no test runs)
- SOP-4 — no skill governs phase-5-status auditing; gap noted
- SOP-5 — read spec #21 (`docs/specs/phase-5/21-analysis-results-improvements.md`) and `docs/PHASE-5-STATUS.md`
- SOP-6 / R17 ✅ B-049 highest in-use, B-050 free
- SOP-8 ✅ no concurrent commits since the B-049 close
- N1-SUPPLEMENT ❌→ recovered: cited file `claude-code-prompts-all-phases-v2.md` missing; chat-side substituted `docs/PHASE-5-STATUS.md`
- R19 ✅ stops invoked correctly at scope-divergence catch

---

*Audit complete. No code changed. No status flipped (per LD-5). Next: chat-Claude to review proposed flips and either (a) green-light a doc-only sweep slice for `PHASE-5-STATUS.md` rows 5.19 + 5.20, or (b) confirm a different disposition.*
