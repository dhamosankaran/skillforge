# SkillForge Backlog

> Single source of truth for all work items: bugs, enhancements, and tech debt.
> Spec files in `docs/specs/` describe the *what* and *how*. This file tracks the *what's-next* and *what's-done*.

## Rules
- **IDs are immutable.** Once assigned, a B-### or E-### never changes, never gets reused.
- **One row per item.** Don't split, don't merge. Spawn a new ID if scope splinters.
- **Status is the only field Claude Code may flip autonomously** (🔴 → 🟡 → ✅). All other fields require human edit.
- **Closing an item:** status → ✅ + append a one-liner to Notes: `closed by <commit-sha> on <YYYY-MM-DD>`.
- **Priority is a product decision.** Set by Dhamo only.
- **Spec column is the on-disk path** (`docs/specs/phase-N/NN-name.md`). Empty if no spec exists yet — create one before implementation.

## Status legend
- 🔴 Pending (not started)
- 🟡 In progress / partial / blocked
- ✅ Done
- ⚪ Won't do / deferred indefinitely
- 🟦 Back-burner — scoped out, awaiting activation gate (e.g., telemetry threshold). Not worked on until the gate trips.

## Priority legend
- **P0** — broken in production, blocking users, blocking next milestone
- **P1** — committed for this phase
- **P2** — wanted, not committed
- **P3** — someday / nice-to-have

---

## Active backlog

### Bugs (B-)

| ID | Area | Title | Priority | Status | Spec | Source slice | Notes |
|----|------|-------|----------|--------|------|--------------|-------|
| B-001 | ats-scanner | AI resume rewrite drops original sections (work history, education) | P0 | 🔴 | | P5-S9 | Output is a summary, not a full rewrite. Suspect prompt or token limit. |
| B-002 | interview | Cover letter generation format malformed (headers, paragraphs, signature block) | P0 | 🔴 | | P5-S10 | Free-form output. Move to structured JSON response. |
| B-003 | profile | "Generate My Experience" button non-functional on Profile page | P0 | 🔴 | | P5-S11 | Trace: button wiring → API → service. May need empty-state for users with no study history. |
| B-004 | results | Keyword Frequency Analysis colors don't match the legend | P1 | ✅ | docs/specs/phase-5/21-analysis-results-improvements.md | P5-S21 (part) | Closed by 1c0817a on 2026-04-19 (P5-S21b; spec #21 AC-1/AC-2 passing — `KEYWORD_LEGEND` + `rgbaFromCssVar` drive both chart cells and legend swatches; no hardcoded hex remains in `KeywordChart.tsx`). |
| B-006 | settings | Existing registered users may lose settings when new fields are added | P1 | 🔴 | | P5-S27 | Audit migrations for backfill defaults; integration test for round-trip. |
| B-008 | nav | `deprecated_route_hit` not wired in 10 Navigate redirect nodes | P2 | 🔴 | | (post-P5-S13) | Tracked in deferred hygiene. Telemetry on legacy URL hits. |
| B-009 | docs | AGENTS.md:95 contradicts CLAUDE.md Rule 13 | P2 | 🔴 | | | Doc-only conflict. Pick one and align. |
| B-010 | frontend | Orphan `Navbar.tsx` still in repo after TopNav migration | P3 | 🔴 | | | Dead code. Delete after confirming zero imports. |
| B-011 | docs | Spec numbering on disk diverges from v2.1 doc | P2 | 🔴 | | | Captured in deferred hygiene; resolve during next doc sync pass. |
| B-012 | playbook | v2.1 doc-bug audit pending | P2 | 🔴 | | | Several known errors in v2.1 prompts. Audit + patch in v2.3. |
| B-013 | docs | Repo-root ambiguity in AGENTS.md + CLAUDE.md + prompt templates | P2 | 🔴 | | (from D-004) | AGENTS.md directory diagram and git-command examples implicitly treat `hireportai/` as repo root, but actual git root is parent. Audit and either (a) document the monorepo layout explicitly, or (b) add a "CWD vs git-path" note to CLAUDE.md. |

### Enhancements (E-)

| ID | Area | Title | Priority | Status | Spec | Source slice | Notes |
|----|------|-------|----------|--------|------|--------------|-------|
| E-001 | docs | Master doc audit + sync (playbook ↔ codebase) | P0 | 🔴 | | P5-S0, P5-S0b | Mandatory before more enhancement work. Output: `docs/audit/2026-04-doc-sync-audit.md`. |
| E-002 | nav | Restructure routes to `/learn/*` and `/prep/*` namespaces | P0 | 🔴 | docs/specs/phase-5/33-navigation-restructure.md | P5-S12, S13, S14 | Includes 301 redirects from old flat paths + new TopNav. Unblocks E-003 and E-004. |
| E-004 | persona | Add `interview_target_company` field to User model | P1 | 🔴 | docs/specs/phase-5/34-persona-picker-and-home.md | P5-S16-AMEND | Amends E-003 spec. New-user flow promises company + date capture. |
| E-005 | home | Persona-aware HomeDashboard at `/home` | P1 | 🔴 | docs/specs/phase-5/34-persona-picker-and-home.md | P5-S18 | Depends on E-003. |
| E-006 | home | State-aware widget logic on HomeDashboard | P1 | ✅ | docs/specs/phase-5/40-home-dashboard-state-aware.md | P5-S18b | Closed by 55ac7bd on 2026-04-19 (backfill; feature shipped, BACKLOG status was stale). Layered on top of E-005. |
| E-007 | home | Interview-Prepper guided 5-step checklist widget | P1 | ✅ | docs/specs/phase-5/41-interview-prepper-checklist.md | P5-S18c | Closed by f075a64 on 2026-04-19 (backfill; feature shipped, BACKLOG status was stale). Depends on E-005. |
| E-008 | persona | Existing-user PersonaPicker migration UX (banner + opt-in) | P1 | 🔴 | docs/specs/phase-5/34-persona-picker-and-home.md | P5-S19 | Don't auto-default. |
| E-009 | results | Move Job Fit Explanation above the fold | P1 | ✅ | | P5-S20 | Closed by e74d1f2 on 2026-04-19 (P5-S20; flattened 3-panel grid → 11 direct grid children; DOM order = mobile + tab order; `results_tooltip_opened` 9-value enum preserved; new `job_fit_explanation_viewed {view_position: "above_fold"}` event). |
| E-010 | results | Add education layer (info icons + first-visit guided tour) | P1 | ✅ | docs/specs/phase-5/21-analysis-results-improvements.md | P5-S21 (part) | Closed by 1c0817a on 2026-04-19 (P5-S21b; info-icon tooltip layer on all 9 section headers with hardened `PanelSection` — Escape, click-outside, `role="tooltip"`, `aria-describedby`, `aria-expanded`; `results_tooltip_opened` PostHog event wired). Guided-tour half deferred per spec §Out of Scope and tracked in Deferred Hygiene Items. |
| E-011 | results | Plan-aware "missing skills → flashcards" CTA | P1 | ✅ | docs/specs/phase-5/22-plan-aware-missing-skills-cta.md | P5-S22 | Closed by `fd4ca3d` on 2026-04-20 (P5-S22b). Three-state CTA on `MissingSkillsPanel.tsx`: anonymous → "Sign in to study" → `/login?return_to=...`; free → "Study these cards — free preview" → `/learn?category=<id>`; pro → "Study these cards" → same URL. New `missing_skills_cta_clicked` PostHog event; `gap_study_clicked` deprecated. Disabled CTA + "No matching study content yet" tooltip for unmatched skills. No backend changes. Wall (spec #50) now live so free-preview routing lands on a real daily-card budget. |
| E-012 | interview | Persist generated interview question sets per (user, JD hash) | P1 | 🔴 | docs/specs/phase-5/35-interview-question-storage.md | P5-S23, S24, S25 | Free-tier counter applies to fresh generations only, not cache hits. |
| E-013 | billing | Subscription cancellation flow (with reason picker) | P1 | 🔴 | docs/specs/phase-5/36-subscription-cancellation.md | P5-S26 | `cancel_at_period_end=true`. Optional win-back modal. |
| E-014 | billing | Paywall dismissal flow (win-back deferred → E-031) | P1 | 🟡 | docs/specs/phase-5/42-paywall-dismissal.md | P5-S26b | (spec ✅ / BE-dismissal-only ✅ / BE-winback DEFERRED → E-031 / FE 🔴 pending) Dismissal logged; re-prompt only after 3 attempts per trigger; win-back email DEFERRED. [2026-04-20] Win-back email re-scoped out of this slice to back-burner row E-031 — no wall-hit telemetry yet to justify building it. `user.downgraded_at` column + `customer.subscription.deleted` webhook wire-up retained in this slice (decision B1) for future churn-guard correctness; the column is impossible to backfill later. BE dismissal + grace + Pro bypass shipped in P5-S26b-impl-BE. FE wiring pending in P5-S26b-impl-FE. |
| E-015 | settings | Settings persistence audit + harden | P1 | 🔴 | | P5-S27 | Pairs with B-006. |
| E-016 | study | Chat with AI on flashcards (per-card chat panel) | P2 | 🔴 | docs/specs/phase-5/37-chat-with-ai-flashcards.md | P5-S28, S29 | Free-tier daily message cap. Uses LLM router → Pro. |
| E-017 | persona | Verify interview date picker + add Profile-side editor | P1 | 🔴 | docs/specs/phase-5/34-persona-picker-and-home.md | P5-S30 | Depends on E-003. |
| E-018 | admin | LLM-driven analytics insights dashboard | P2 | 🔴 | docs/specs/phase-5/38-admin-analytics.md | P5-S31, S32, S33 | Five sections: metrics, performance, behavior, enhancement signal, feedback themes. |
| E-019 | admin | Content Feed Flow (bulk topic → AI draft → review queue) | P2 | 🔴 | docs/specs/phase-5/39-content-feed-flow.md | P5-S34 | Lowest user impact, ship last in Phase 5. |
| E-020 | results | Audit geo-pricing visibility on signup vs checkout | P1 | 🟡 | docs/specs/phase-5/27-geo-pricing.md | P5-S8 | Audit-only first; fix gaps in follow-up. |
| E-021 | docs | Backfill spec — Multi-model LLM router | P3 | 🔴 | docs/specs/phase-5/25-llm-router.md | P5-S1 | Spec backfill for already-shipped feature. Optional. |
| E-022 | docs | Backfill spec — Three-theme design system | P3 | 🔴 | docs/specs/phase-5/26-design-system.md | P5-S2 | Optional. |
| E-023 | docs | Backfill spec — Geo-based pricing | P3 | 🔴 | docs/specs/phase-5/27-geo-pricing.md | P5-S3 | Optional. |
| E-024 | docs | Backfill spec — Anti-abuse registration block | P3 | 🔴 | docs/specs/phase-5/28-anti-abuse-registration.md | P5-S4 | Optional. |
| E-025 | docs | Backfill spec — Job tracker auto-populate from ATS | P3 | 🔴 | docs/specs/phase-5/29-tracker-autopopulate.md | P5-S5 | Optional. |
| E-026 | docs | Backfill spec — Free-tier interview question limits | P3 | 🔴 | docs/specs/phase-5/30-free-tier-interview-limits.md | P5-S6 | Optional. Verify the actual limit value matches intent. |
| E-027 | docs | Backfill spec — Branding + Midnight Forge landing page | P3 | 🔴 | docs/specs/phase-5/31-branding-skillforge.md, docs/specs/phase-5/32-landing-page-midnight-forge.md | P5-S7 | Optional. |
| E-028 | infra | Create `.agent/skills/backend.md` for infra slices with no domain skill | P2 | 🔴 | | (deferred hygiene) | Currently no fallback skill for pure-infra slices. |
| E-029 | learn | Lift `/learn/progress` out of Profile into its own page | P2 | 🔴 | | (deferred hygiene) | Skill radar + heatmap currently live inside Profile. |
| E-030 | payments | Free-tier daily-card review wall (enforces LD-001) | P1 | ✅ | docs/specs/phase-5/50-free-tier-daily-card-wall.md | P5-S22-WALL | Closed by `ebef7da` on 2026-04-20 (P5-S22-WALL-b). Counter = Redis INCR, keyed by `daily_cards:<user_id>:<YYYY-MM-DD>` in user-local tz, 48h TTL. Fail-open on Redis outage. Returns 402 with `{error, trigger, cards_consumed, cards_limit, resets_at}`. Reuses existing `PaywallModal` `daily_review` trigger scaffold + `EmailPreference.timezone` (UTC fallback). New `app/utils/timezone.py::get_user_timezone` helper; new `study_service._check_daily_wall` + `DailyReviewLimitError`. Analytics: `daily_card_submit` (backend) + `daily_card_wall_hit` (frontend). Unblocks E-011 / spec #22 (P5-S22b) and E-014 / spec #42 (P5-S26b). |
| E-031 | billing | Paywall win-back email (deferred from E-014) | P2 | 🟦 | docs/specs/phase-5/42-paywall-dismissal.md (§5.5, §6, §9) | (parent: P5-S26b) | Win-back email triggered at 3 dismissals in 30 days, 30% off via Stripe coupon. Synchronous Resend send. Deferred from E-014 pending wall-hit telemetry. **Activation gate:** when `paywall_dismissed` PostHog event volume is sufficient to validate the 3-in-30 threshold — suggest minimum **50 dismissal events across distinct users**. **Already satisfied prereqs (shipped with E-014 BE):** `paywall_dismissals` table, `user.downgraded_at` column + `customer.subscription.deleted` webhook wire-up. **Outstanding work:** Stripe coupon creation (test + live) + `STRIPE_WINBACK_COUPON_ID` env + `app/core/config.py` Settings field; `paywall_service.is_winback_eligible` + `send_winback_email`; `app/templates/paywall_winback.html`; dismissal endpoint amendment (add `win_back_eligible` to response, add eligibility + send call-out); `GET /should-show-paywall` amendment (add `win_back_offered` to response shape); 5+ test cases (eligibility, fresh-churner exclusion, Pro short-circuit, send-time plan re-check, failure non-raising); PostHog events `winback_email_sent`/`winback_email_clicked`/`winback_converted`. Parent: E-014. Dependency: paywall dismissal telemetry. |
| E-032 | billing | Post-checkout redirect lands on /pricing instead of a celebratory welcome page | P3 | 🔴 | | (P5-S26b-impl-BE smoke) | Stripe `success_url` in `create_checkout_session` currently points at `/pricing`. User lands on Pricing seeing "Currently Active" on the Pro tile — functionally correct but misses the welcome moment. Fix: either add a `/welcome` route (celebratory state) or use `/profile?upgraded=true` with a conditional banner. Effort: small (<1h). Surfaced during P5-S26b-impl-BE smoke testing. |
| E-033 | billing | Manage Subscription button fails with "Couldn't open billing portal" | P1 | 🔴 | | (P5-S26b-impl-BE smoke) | **Launch blocker — Pro users cannot manage subscription.** Clicking "Manage Subscription" on `/profile` as a Pro user shows error toast "Couldn't open billing portal. Please try again." Likely root cause: webhook handler for `customer.subscription.created` (or the `checkout.session.completed` branch) flips user plan but does not persist `stripe_customer_id` on the Subscription row, so the billing-portal endpoint is called with `customer=None`. **Diagnostic:** `SELECT stripe_customer_id FROM subscriptions WHERE plan='pro'` — if NULL, confirmed. **Fix:** webhook handler persists customer ID; backfill any existing Pro users missing it. Must fix before launch. Effort: small-to-medium (<0.5d if diagnosis correct). Cross-reference: related to E-035 Stripe audit. |
| E-034 | ux | Generic error toasts don't give users actionable recovery paths | P3 | 🔴 | | (P5-S26b-impl-BE smoke) | Billing portal failure surfaces as "Couldn't open billing portal. Please try again." — no guidance on what to try or what went wrong. Pattern likely repeats elsewhere. After E-033 fix lands, audit error-surface sites and establish a recovery-copy pattern (e.g., "Subscription management is temporarily unavailable. Contact support."). Effort: small-to-medium depending on audit scope. Dependency: after E-033. Out of scope: replacing all toasts with inline banners — that is larger UX work. |
| E-035 | billing | Stripe integration audit — full-lifecycle code review before launch | P2 | 🔴 | | (P5-S26b-impl-BE smoke) | Read-only audit (Mode 1) of checkout creation, webhook handling (all Stripe event types), billing portal session creation, `stripe_customer_id` persistence on Subscription, price/coupon ID resolution. **Deliverable:** report listing bugs, missing handlers, silent-drift risks. Surfaced by three Stripe issues hit during P5-S26b-impl-BE smoke (two env-var mistakes — price ID was product ID, account mismatch between API key and dashboard — plus the real E-033 code bug). **Effort:** half-day audit, no code changes. **Trigger:** run before any public launch OR before E-031 (win-back email) activation since that path also touches Stripe — whichever is first. |

---

## Closed (most recent first)

| ID | Title | Closed by | Date | Notes |
|----|-------|-----------|------|-------|
| B-005 | Stripe webhook handler is non-idempotent — duplicate delivery risk | f615eb6 | 2026-04-19 | spec docs/specs/phase-5/43-stripe-webhook-idempotency.md — closed by f615eb6 on 2026-04-19 — spec backfilled retroactively; idempotency was shipped prior to backlog creation (original impl 43d40d9 on 2026-04-10). |
| E-003 | Mandatory PersonaPicker on first login + persona model | 2c01cc7 | 2026-04-18 | P5-S17 full FE migration. closed by 2c01cc7 on 2026-04-18 |
| B-007 | StudyDashboard PERSONA_CONFIG undefined for snake_case persona values | 2c01cc7 | 2026-04-18 | Closed alongside E-003. closed by 2c01cc7 on 2026-04-18 |

---

## Open decisions awaiting Dhamo

These block specific items. Mirrors the v2.2 patch list — keep both in sync.

| Decision | Affects | Default if not decided |
|----------|---------|------------------------|
| Persona switch UX: full-page reroute or modal? | E-003 (P5-S17) | Full-page reroute (current spec) |
| Daily review consumes 15-card free budget, or browse-only? | E-011, Phase 1 paywall logic | Browse-only (more generous) |
| Auto-save scan to tracker — automatic or "Save?" prompt? | E-025 (P5-S5 spec) | Automatic (current behavior) |
| Old Phase 2 email deep links — covered by P5-S13 redirects? | E-002 (P5-S13) | Yes, must be covered |

---

*Last updated: 2026-04-19. Initial seed from v2.1 Phase 5 status table + v2.2 patch + known bugs in memory.*