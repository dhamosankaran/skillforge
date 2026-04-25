# Phase 5 Status — Authoritative

_Last audited: 2026-04-19 via slice that closes v2.1 item 5.9 (this commit)_

## How to use this file

- This file is the **on-disk source of truth** for Phase 5 status. If any chat-side playbook (v2.1, v2.2-patch, or the `skillforge_playbook_v2.md` Phase-5 status table) disagrees with this file, **trust this file** — the chat artifacts are frozen snapshots and are not updated after ship.
- Chat-Claude syncs project knowledge from this file manually; treat any divergence as drift that should be reconciled back toward this document, not the other way around.
- Update this file at the end of every slice that ships a v2.1 or v2.2-patch item (or closes/obsoletes one). Commit the update alongside the slice so status and code move together.
- Status legend:
  - ✅ **SHIPPED** — working on `main`, with spec (or retroactive spec) + evidence path.
  - 🟡 **PARTIAL** — primary path shipped; named gap(s) deferred. Deferred gaps listed in SESSION-STATE.md under Deferred Hygiene / Known-Broken.
  - 🔴 **PENDING** — not implemented.
  - ❓ **AMBIGUOUS** — evidence unclear after ≤3-minute audit; one-line question recorded. Ambiguity is signal, not failure — reconcile in a follow-up slice.
  - ⚫ **OBSOLETE** — in the playbook but superseded, removed, or moot. See rationale.

## Canonical E2E Flow

_Locked 2026-04-21 (Path A decision by Dhamo)_. This is the product-authoritative happy path through the app. Specs, flows, and test plans must reconcile to this.

**Funnel shape: auth-first.** `/` is a marketing landing page for anonymous visitors; product value is gated behind login.

1. **Anonymous visit** → `/` renders `LandingPage.tsx` (Midnight Forge design). All CTAs point to `/login`. No scan surface is exposed to anonymous users.
2. **Sign up / sign in** → `/login` (Google OAuth). On success, `PersonaGate` evaluates `user.persona`:
   - `null` → redirect to `/onboarding/persona` (mandatory PersonaPicker, spec #34).
   - set → redirect to `/home`.
3. **Persona capture** → `PersonaPicker.tsx` (full-page; 3 cards: Interview-Prepper / Career-Climber / Team Lead). Interview-Prepper expands with date + company fields. `PATCH /api/v1/users/me/persona` persists and sets `interview_target_*` columns. Continue → `/home`.
4. **Home dashboard** → `HomeDashboard.tsx` (persona-aware, state-aware widgets, spec #35 + #40 + #41).
5. **Scan flow (Lens)** → user navigates to `/prep/analyze` (from home widget or nav). Upload resume + paste JD → `POST /api/v1/analyze` → `/prep/results`.
6. **Results** → `Results.tsx` with Job Fit, Score Breakdown, Missing Skills CTA (plan-aware three-state per spec #22). Free users see "Study these cards — free preview"; Pro users see direct link; anonymous state never reaches this page under Path A.
7. **Free daily-review wall** → user opens `/learn/daily` or similar, submits via `QuizPanel`; 16th review returns 402 (spec #50) → `PaywallModal` with `trigger="daily_review"`.
8. **Paywall dismissal** → "Not now" / X / backdrop fires `paywall_dismissed` + POST `/paywall-dismiss`. `QuizPanel` tracks `attempts_since_dismiss` and branches modal-vs-nudge per Strategy A (spec #42, P5-S26b).
9. **Stripe checkout** → `/pricing` → `POST /api/v1/payments/checkout` → Stripe hosted checkout → webhook flips subscription to Pro.
10. **Post-upgrade** → Pro user bypasses the wall (`_check_daily_wall` short-circuits for non-free plans); Forge study + Mission Mode fully accessible.

**Anon-scan funnel deferred per 2026-04-21 decision** — backend supports it (`/api/v1/analyze` uses `get_current_user_optional`) but no FE surface exposes anon scan on `/`. Tracked as BACKLOG row **E-038** (🟦 deferred, no priority). See `docs/status/E2E-READINESS-2026-04-21.md` §5 for the readiness audit that surfaced the decision.

## v2.1 Phase 5 status (5.1 – 5.26)

| # | Feature | Status | Spec | Evidence | Notes |
|---|---------|--------|------|----------|-------|
| 5.1 | Multi-model LLM router (Flash / Pro) | ✅ SHIPPED | — (see `.agent/skills/llm-strategy.md`) | `app/core/llm_router.py`, `generate_for_task()` entry point | Commit `776194d`. Legacy `app/services/llm/factory.py` is parallel tech debt (P6 cleanup). |
| 5.2 | Design system — three themes / CSS tokens | ✅ SHIPPED | — (see `.agent/skills/design-system.md`) | `hirelens-frontend/src/styles/design-tokens.ts`, `ThemePicker.tsx`, `ThemeContext.tsx` | Commit `b5d27f4`. Rule 12 enforces token-only styling. |
| 5.3 | Geo-based pricing (USD/INR + Redis) | 🟡 PARTIAL | — (see `.agent/skills/geo-pricing.md`) | `app/services/geo_pricing_service.py`, `/api/v1/payments/pricing` | Commits `b794d26`, `02d7cc8` (P5-S8). Deferred gaps B/D/E in SESSION-STATE Known-Broken. No Redis layer — uses `ip-api.com` with server-side fallback. |
| 5.4 | Anti-abuse — duplicate registration block by IP | ✅ SHIPPED | — | `app/api/v1/routes/auth.py` (inline 30-day window check against `registration_logs`), `RegistrationLog` model | Commit `9a9b299`. DB-based, not Redis; tech debt noted in SESSION-STATE Tech Debt. |
| 5.5 | Job tracker auto-populate from ATS scan | ✅ SHIPPED | `docs/specs/phase-1/11b-tracker-autopopulate.md` | `app/services/tracker_service_v2.py`, auto-create in `/api/v1/analyze` route, PostHog `tracker_auto_created_from_scan` | Commit `1b9f0ec`. Decision locked 2026-04-18 (JD-gated + `(user_id, jd_hash)` dedupe) — see SESSION-STATE Locked Decisions. |
| 5.6 | Free-tier limit on interview-question generation | ✅ SHIPPED | — | `app/api/routes/interview.py:24-34` → `check_and_increment(user.id, "interview_prep", db)` with 403 `LIMIT_REACHED` on breach | Implementation in place; the *limit value* is an Open Decision awaiting Dhamo (SESSION-STATE). |
| 5.7 | HirePort → SkillForge branding pass | ✅ SHIPPED | — | Brand strings in `LandingPage.tsx`, nav, marketing copy | Commit `16e5f6f chore(ui): complete branding cleanup + visual/functional audit`. |
| 5.8 | "Midnight Forge" landing-page redesign | ✅ SHIPPED | — | `hirelens-frontend/src/pages/LandingPage.tsx:10` file header literally reads `"Midnight Forge" Theme`; 709-line design-token-driven page | Commit `b5d27f4`. Dark-first palette per design tokens. |
| 5.9 | Doc audit + sync | ✅ SHIPPED | `docs/PHASE-5-STATUS.md` (this file) + spec #48 | This slice | Previous partial audits: `docs/audit/2026-04-doc-sync-audit.md` (commits `e649648`, `8707991`). This slice closes the authoritative-on-disk-status part. |
| 5.10 | Navigation restructure (`/learn/*` + `/prep/*`) | ✅ SHIPPED | `docs/specs/phase-5/12-navigation-restructure.md` | `src/App.tsx` (namespaced routes + redirect block), `src/components/layout/{TopNav,MobileNav,AppShell}.tsx` | Commits `d237485` (P5-S13), `81ed96d` (P5-S14). Deferred: `deprecated_route_hit` event not wired (SESSION-STATE Deferred Hygiene). |
| 5.11 | Persona-aware `/home` | ✅ SHIPPED | `docs/specs/phase-5/35-home-dashboard-and-widgets.md`, `40-home-dashboard-state-aware.md` | `src/pages/HomeDashboard.tsx`, `src/components/home/widgets/*.tsx`, `DashboardWidget.tsx` primitive | Commits `5e1f56c` (P5-S18), `55ac7bd` (P5-S18b). Six state variants + seven widgets. |
| 5.12 | Mandatory PersonaPicker on first login | ✅ SHIPPED | `docs/specs/phase-5/34-persona-picker-and-home.md` | `src/pages/PersonaPicker.tsx`, `src/components/PersonaGate.tsx` (redirect null-persona → `/onboarding/persona`), backend `PATCH /api/v1/users/me/persona` | Commits `503cac8` (backend), `2c01cc7` (frontend). |
| 5.13 | Geo-pricing IP detection on REGISTRATION page | 🟡 PARTIAL | — | Pricing endpoint detects country from IP; Pricing page wired | Deferred gap B in SESSION-STATE Known-Broken table: "no price on LoginPage." `/login` still shows no country-localized price. |
| 5.14 | Interview date picker on persona select | ✅ SHIPPED | `docs/specs/phase-5/34-persona-picker-and-home.md` | `src/pages/PersonaPicker.tsx` — Interview-Prepper card expands with `<input type="date">` for `interview_target_date`; 100-char company field; PATCHed via `updatePersona()` | Commit `2c01cc7`. S16 migration renamed/retyped columns (`target_date`→`interview_target_date Date`). |
| 5.15 | AI resume rewrite — missing original content | ✅ SHIPPED | `docs/specs/phase-5/09-resume-rewrite-fix.md`, `47-resume-rewrite-content-preservation.md` | `app/services/gpt_service.py::generate_resume_rewrite` (`[:40000]` / `max_tokens=8000`), `tests/services/test_resume_rewrite.py` (AC-1 + AC-2) | Commits `602ea20` (P5-S9), `f1bcf94` (spec #47 prompt-contract guard). Closed 2026-04-19. |
| 5.16 | Cover-letter generation — format issues | ✅ SHIPPED | `docs/specs/phase-5/10-cover-letter-format-fix.md` | `app/services/gpt_service.py::generate_cover_letter` — business-letter format prompt, tone honored, 20k/10k caps | Commit `696b176` (P5-S10). |
| 5.17 | Interview Prep — store generated questions per JD | ✅ SHIPPED | `docs/specs/phase-5/49-interview-question-storage.md` | Backend (commit `a2a79d5`): `interview_question_sets` table (migration `f3350dcba3a5`), `app/models/interview_question_set.py`, `app/services/interview_storage_service.py::generate_or_get_interview_set`, `app/utils/text_hash.py::hash_jd`, route `app/api/routes/interview.py` serves cached on `(user_id, jd_hash)` hit and skips `check_and_increment` on cache hits. Tests in `tests/services/test_interview_storage.py` pin AC-1..AC-5b. Frontend (this slice, 5.17b): `services/api.ts::generateInterviewPrep(_, _, {forceRegenerate})` + `useInterview` pass-through + `pages/Interview.tsx` cached chip / fresh free-usage chip / window.confirm() on free-tier regenerate; tests in `tests/Interview.test.tsx`. | **Note**: the `hash_jd` primitive did not previously exist on the scan-tracker path despite prior wording — spec #49 created the shared util at `app/utils/text_hash.py`; tracker can adopt it later (see [5.17-follow] in SESSION-STATE). |
| 5.18 | Generate My Experience — fix | ✅ SHIPPED | `docs/specs/phase-5/11-generate-experience-fix.md` | `app/services/experience_service.py`, fast-tier routing, empty-response guard | Commit `66c1814` (P5-S11). |
| 5.19 | Job Fit Explanation — above the fold | ✅ SHIPPED | — | `src/components/dashboard/JobFitExplanation.tsx` rendered at `Results.tsx` `lg:col-start-2 lg:row-start-1` with explicit `// 2. Job Fit — mobile 2nd · lg/xl col-2 row-1 HERO` annotation; row-1 above-fold on lg+ breakpoints | ✅ shipped `e74d1f2` (P5-S20, E-009 close, 2026-04-19) — flattened the 3-panel grid into 11 direct grid children so DOM order = mobile + tab order; new `job_fit_explanation_viewed {view_position: 'above_fold'}` event; 8 ordering tests in `Results.ordering.test.tsx`. Verified by B-050 audit (`docs/audit/2026-04-partial-audit.md`) on 2026-04-26. |
| 5.20 | Analysis Results — education display + keyword color fix | ✅ SHIPPED | `docs/specs/phase-5/21-analysis-results-improvements.md` | `KeywordChart.tsx` uses `KEYWORD_LEGEND` + `rgbaFromCssVar('--color-accent-secondary', 0.5)` (no hardcoded violet); `PanelSection.tsx` has Escape + click-outside + `role="tooltip"` + `aria-describedby` + `aria-expanded`; all 9 Results sections wrapped with `{what, how, why}` tooltip copy from spec §Education Layer Design | ✅ shipped `1c0817a` (P5-S21b impl, B-004 + E-010 close, 2026-04-19) + `fe4a333` (spec #21 author). 20 new tests across `KeywordChart.colors.test.tsx` (9), `PanelSection.tooltip.test.tsx` (10), `Results.tooltips.test.tsx` (1). Verified by B-050 audit (`docs/audit/2026-04-partial-audit.md`) on 2026-04-26. (guided-tour half deferred per spec §Out of Scope: see `[P5-S21b-follow]` in SESSION-STATE Deferred Hygiene.) |
| 5.21 | Pro-gating: missing skills → flashcards | ✅ SHIPPED | — | `src/components/dashboard/MissingSkillsPanel.tsx` builds `gapCategoryMap` from `GapMapping[]`; `isPro` prop gates Pro link; PostHog `gap_study_clicked` + `gap_card_clicked` fire; backend `app/services/gap_mapping_service.py` + `gap_mapping` LLM task | Commit `f88995d feat(analyze): free limits + results page UX + gap-to-cards linking`. |
| 5.22 | Stripe — subscription cancellation flow | ✅ SHIPPED | `docs/specs/phase-5/36-subscription-cancellation.md` | `app/services/payment_service.py:153::create_billing_portal_session`, `app/api/routes/payments.py:99`, Profile "Manage subscription" button | Commit `115e2d6` (P5-S26a, closes spec #36). Uses Stripe hosted billing portal. |
| 5.23 | Settings persistence for existing users | ❓ AMBIGUOUS | — | `Profile.tsx` imports `EmailPreferences` + `ThemePicker` from `@/components/settings/`; `ThemeContext` persists theme; `PATCH /api/v1/users/me/persona` persists persona. Legacy users moot — SESSION-STATE Obsolete Slices (P5-S19) rationale: dev DB wiped 2026-04-19, Railway never had real traffic. | The "for existing users" framing is effectively obsolete; core settings surfaces exist. Needs product reconciliation on whether this bullet is closed-by-obsolescence or still has a specified gap. Also: `email-prefs` vs `email-preferences` path mismatch (SESSION-STATE Tech Debt) may silently 404 today. |
| 5.24 | Chat with AI during flashcard study | 🔴 PENDING | — | No `CardChatPanel`, `ChatWithAI`, `card_chat`, or `chat_with_ai` referenced in `src/`. SESSION-STATE Frontend-test-coverage hard constraint *names* `CardChatPanel` as a future page, confirming not-yet-shipped. | Flagged as a P5-S27-ish slice in v2.1; unscheduled. |
| 5.25 | Admin LLM-driven analytics dashboard | 🔴 PENDING | `docs/specs/phase-5/01-admin-analytics-early-draft.md` (early draft only) | Admin routes in `app/api/v1/routes/admin.py` cover card CRUD + registration logs + card-draft generation only. No `AdminInsights`, `admin_insights`, or analytics-dashboard surface. | Spec exists as early draft; not implemented. |
| 5.26 | Admin content-feed flow | 🔴 PENDING | — | No `ContentFeed`, `content_feed`, or admin content-feed surface in code. | Not specced, not implemented. |

## v2.2-patch status

| ID | Feature | Status | Spec | Evidence | Notes |
|----|---------|--------|------|----------|-------|
| P5-S16-AMEND | `interview_target_company` on User model | ✅ SHIPPED | Folded into `docs/specs/phase-5/34-persona-picker-and-home.md` | User model + migration `02bf7265b387` rename `target_*` → `interview_target_*`, retype `target_date DateTime → interview_target_date Date`, widen `String(255)→String(100)` for company | Commit `503cac8`. SESSION-STATE Resolved Decision #4. |
| P5-S18b | State-aware HomeDashboard | ✅ SHIPPED | `docs/specs/phase-5/40-home-dashboard-state-aware.md` | 6 state variants + cache invalidation in `app/services/home_state_service.py`; widgets `StreakAtRiskWidget`, `InactiveReturnerWidget`, `FirstSessionDoneWidget`, `ResumeStaleWidget`, `TeamComingSoonWidget`, `CountdownWidget` | Commit `55ac7bd` (closes spec #40). |
| P5-S18c | Interview-Prepper 5-step checklist | ✅ SHIPPED | `docs/specs/phase-5/41-interview-prepper-checklist.md` | `app/services/onboarding_checklist_service.py`, checklist widget in home dashboard for Interview-Prepper persona | Commit `f075a64` (closes spec #41, Phase 5D). |
| P5-S26b | Paywall dismissal + win-back | 🟡 PARTIAL | Partially in `docs/specs/phase-5/36-subscription-cancellation.md` (cancellation side); win-back explicitly deferred | `src/components/PaywallModal.tsx` has dismiss via `onClose` (line 31, 68, 121, 142, 211) — dismissal shipped. Win-back flow ("50% off for 3 months") deferred per spec #36 §11 and SESSION-STATE Open Decisions. | No cancellation volume yet to justify win-back A/B — deferred by product decision, not tech debt. |
| P5-S26c | Stripe webhook idempotency | ✅ SHIPPED | `docs/specs/phase-5/43-stripe-webhook-idempotency.md` | `app/services/payment_service.py:174-204` SELECT-first dedup + `stripe_events` table; `test_duplicate_webhook_is_idempotent`, `test_handler_exception_rolls_back_stripe_event_row` | Commit `f615eb6` (retroactive spec + AC-4 test). INSERT-first concurrent-delivery refactor deferred `[S26c-defer]`. |
| P5-S22-WALL | Free-tier daily-card review wall (LD-001 enforcement) | ✅ SHIPPED | `docs/specs/phase-5/50-free-tier-daily-card-wall.md` | Backend: `app/services/study_service.py::_check_daily_wall` + `DailyReviewLimitError`, `app/utils/timezone.py::get_user_timezone`, `app/api/v1/routes/study.py` 402 branch. Frontend: `src/components/study/QuizPanel.tsx` 402→PaywallModal wiring. Tests: `tests/test_wall.py` (11), `tests/components/QuizPanel.wall.test.tsx` (5). Analytics: `daily_card_submit` (BE) + `daily_card_wall_hit` (FE) catalogued in `.agent/skills/analytics.md`. | Commit `ebef7da` (P5-S22-WALL-b). Unblocks P5-S22b (free-preview CTA) and P5-S26b (paywall dismissal). Counter = Redis INCR `daily_cards:{user_id}:{YYYY-MM-DD}` in user-local tz, 48h TTL, fail-open on Redis outage. |
| P5-S22b | Plan-aware Missing Skills CTA | ✅ SHIPPED | `docs/specs/phase-5/22-plan-aware-missing-skills-cta.md` | `src/components/dashboard/MissingSkillsPanel.tsx` rewritten to three-state CTA (anonymous/free/pro); `src/pages/Results.tsx` derives plan via `useAuth + useUsage` and reads `scan_id` from `useSearchParams`. Tests: `tests/components/MissingSkillsPanel.cta.test.tsx` (14 — all spec §Test Plan rows). Analytics: `missing_skills_cta_clicked` added; `gap_study_clicked` deprecated per P5-S17 precedent. | Commit `fd4ca3d` (P5-S22b). Closes E-011 / spec #22. No backend changes. Free-preview CTA now lands on the live 15-card wall shipped in P5-S22-WALL-b. Unblocks P5-S26b (paywall dismissal — the full free→wall→paywall flow is now routable end-to-end). |

## Post-v2.2 slices (shipped outside the playbook)

| Slice | Feature | Spec | Commit |
|-------|---------|------|--------|
| S44 | Widget empty states + cross-tenant leak patch | `docs/specs/phase-5/44-home-widget-empty-states.md` | `3a1ca95` |
| S45 | Legacy `/api/tracker` removal + v1 tracker hardened (`user_id` required) | `docs/specs/phase-5/45-legacy-route-cleanup.md` | `71e71c6` |
| S46 | Post-persona first-action CTA (`/first-action`) | `docs/specs/phase-5/46-post-persona-first-action.md` | `fc933d1` |
| S47 | Resume-rewrite content-preservation prompt-contract regression test | `docs/specs/phase-5/47-resume-rewrite-content-preservation.md` | `f1bcf94` |

## Genuinely pending (🔴) — next-slice candidates

Listed in rough priority. This is the authoritative "what's left for v2.1".

1. **5.24 — Chat-with-AI during flashcard study (`CardChatPanel`).** No code surface yet. New LLM task (`card_chat`, reasoning tier), new side-panel UI on `/learn/card/:id`, Pro-gated. Scope is a single new route + component + LLM task. SESSION-STATE Frontend-test-coverage constraint already names this file as a future addition.
2. **5.25 — Admin LLM-driven analytics dashboard.** Spec exists as early draft (`01-admin-analytics-early-draft.md`). Promote to full spec, build on existing admin routes. Could be paired with 5.26.
3. **5.26 — Admin content-feed flow.** No spec. Define before implementation per CLAUDE.md Rule 14.

Deferred-but-not-pending (tracked elsewhere, not in priority list above):

- Geo-pricing gap B (LoginPage price) / D (rate-limit fallback for India) / E ($0 vs INR for free plan) — SESSION-STATE Known-Broken.
- `deprecated_route_hit` PostHog event wiring in redirect block — SESSION-STATE Deferred Hygiene.
- Win-back flow (50% off 3 months) — waiting on cancellation volume data.

## Ambiguous — need deeper audit

| # | Item | What's unclear |
|---|------|---------------|
| 5.23 | Settings persistence for existing users | "Existing users" framing is moot (SESSION-STATE Obsolete Slices P5-S19: dev DB wiped, Railway never had real traffic). Core settings (theme, email prefs, persona) all persist. Is the intent "close as obsolete" or "there's a specific setting still missing"? Also: email-prefs path mismatch may 404 silently today — not an ambiguity about this item but worth noting. |

> **5.19 + 5.20 resolved 2026-04-26** — both ✅ SHIPPED per B-050 audit (`docs/audit/2026-04-partial-audit.md`); rows above this table updated with closing-commit citations. Original ambiguity-table entries dropped to prevent self-contradiction.

## Surprises / drift from expected status

- **5.17 surprise (resolved this slice)**: the 2026-04-19 audit reported "no storage code and no dedicated spec file" for 5.17, and inferred `hash_jd` existed on the scan-tracker path. The subsequent slice (spec #49) audit confirmed `hash_jd` did **not** exist anywhere in the backend — the scan-tracker Locked Decision specs it but was never implemented. Spec #49 creates the shared util at `app/utils/text_hash.py` and consumes it for interview storage; tracker auto-populate can adopt it later.
- **5.22 surprise**: v2.1 entry labelled this as S26, but the implementation commit (`115e2d6`) + spec #36 frontmatter both labelled this "P5-S26b / shipping with P5-S26b." Status is SHIPPED either way; just flagging the numbering drift between the v2.1 table, spec #36 frontmatter, and reality.
- **5.19 surprise (resolved 2026-04-26 via B-050 audit + earlier P5-S20 fix)**: original playbook framing "above the fold" did not match `Results.tsx` ordering at the time of v2.1 reconciliation. P5-S20 (`e74d1f2`, 2026-04-19) flattened the 3-panel grid so Job Fit lives at `lg:col-start-2 lg:row-start-1` (HERO position); the audit at `docs/audit/2026-04-partial-audit.md` confirmed the on-disk fix. Status table updated this slice.
- **S45/S46/S47 were shipped outside the playbook entirely** — they're real work ≤48 h old that chat-Claude's v2.1/v2.2 tables don't mention. Recorded in the "Post-v2.2 slices" section so reconciliation back to chat-Claude captures them.
