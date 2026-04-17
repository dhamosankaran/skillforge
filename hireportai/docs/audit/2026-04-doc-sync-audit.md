# 3-Way Doc Sync Audit — April 2026

> **Slice**: P5-S0 (Master Doc Audit + Sync) — read-only pass, no code changes.
> **Scope**: `skillforge_playbook_v2.md` (v2.1) ↔ `claude-code-prompts-all-phases-v2.md` (+ v2.2 patch) ↔ `local-setup-guide.md` ↔ actual code at `hireportai/`.
> **Date**: 2026-04-17.
> **Outcome**: Code is ahead of the master docs in several material ways. The biggest problems are (a) spec-file numbering collisions in Phase 2/3/4, (b) Phase-1 v2.1 enhancements built but never backfilled as `11a/11b/11c/11d` specs, and (c) a stale path reference to `app/services/llm_router.py` in `SESSION-STATE.md` and the playbook even though the router lives at `app/core/llm_router.py`. Test suites are green (backend 167 passed, frontend 5 passed). No blocking issues for Phase 5 start once these doc fixes are applied.

---

## Key context found during the audit

- Master docs live **one directory above** the repo root, in `/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/`, not in `hireportai/docs/`. The playbook's own self-reference (`"in project root or docs/"`) is therefore imprecise — neither location is where the file actually sits. For this audit that's only a navigation issue, but P5-S0b should note the true location or move the file.
- The v2.2 flow-audit patch (`claude-code-prompts-all-phases-v2.2-patch.md`) exists alongside v2 and SESSION-STATE references it, but it is not yet merged into a `v2.2` top-level playbook; Phase 5 planning depends on reading both.
- `STRATEGIC-OPTIONS.md` referenced by SESSION-STATE is at `hireportai/STRATEGIC-OPTIONS.md` (correct).
- LLM router is at `app/core/llm_router.py` (confirmed by `CLAUDE.md` rule 11) — **not** `app/services/llm_router.py` (which is what the playbook and the SESSION-STATE Hard Constraints section both claim).

---

## PASS 1 — Drift Detection (Playbook vs Code, by Phase)

Severity legend: **HIGH** = docs actively mislead Claude Code or a human; **MED** = stale reference but nothing false; **LOW** = cosmetic.

### Phase 0 — Foundation + Deploy

Playbook scope: PG+pgvector migration, Alembic, auth unification, role column, skeleton deploy, CI/CD.

| Area | Playbook expects | Code shows | Severity | Notes |
|---|---|---|---|---|
| Spec numbering | `00`, `01-auth-unification`, `02-user-roles`, `02a-skeleton-deploy`, `02b-cicd-pipeline` | `00-postgresql-migration`, `01-alembic-setup`, `02-auth-unification`, `02a-skeleton-deploy`, `02b-cicd-pipeline`, `03-user-role-admin` | MED | User-role spec promoted from `02` to `03`, and `01` is now `alembic-setup` (not in playbook). Coherent but not what the playbook enumerates. |
| Alembic initial migration | Implicit | `alembic/versions/0001_initial_postgres_pgvector.py` + 17 follow-ups | LOW | Migrations exist; no drift. |
| Health route | `GET /health` → 200 | `app/main.py:113` returns `{"status":"healthy","service":"hireport-ai"}` | LOW | Response shape slightly richer than playbook's `{"status":"ok"}`; fine. |
| App title | SkillForge | FastAPI `title="HirePort AI"` in `app/main.py:63` | LOW | Branding pass (Phase 5.7) hasn't hit FastAPI metadata yet. |

### Phase 1 — Core Study Engine + ATS Bridge

Playbook scope (v2.1): 15 tasks including multi-model router (1.15), geo-pricing (1.11), IP blocking (1.14), free-tier limits (1.12), tracker auto-populate (1.13), persona picker with target_company/target_date (1.9).

| Area | Playbook expects | Code shows | Severity | Notes |
|---|---|---|---|---|
| Card extraction → PG | 177 cards seeded | `cards` table + `card.py` model; extraction tests pass (`test_card_extraction.py`, `test_extract_cards_unit.py`) | LOW | No count verified in this pass. |
| FSRS study engine | `app/services/study_service.py` | `app/services/study_service.py` + `app/api/v1/routes/study.py` | LOW | Matches. |
| Cards API | `app/api/v1/routes/cards.py` | Exists. | LOW | Matches. |
| Onboarding flow + persona fields | `User.persona`, `User.target_company`, `User.target_date` | Migrations `d3a7e2f91c04_add_persona_and_onboarding_completed_to_users.py`, `74a6fb27a181_add_target_company_and_target_date_to_.py`. `User.onboarding_completed` serialized in `auth.py:_user_dict`. | LOW | Matches — persona already lives on User. |
| PostHog instrumentation | Backend + frontend events | `app/core/analytics.py` + PostHog captures throughout | LOW | Matches. |
| Stripe integration + geo-pricing | `app/services/geo_service.py`, INR price id | File named `app/services/geo_pricing_service.py` (not `geo_service.py`), ip-api.com + Redis cache, `STRIPE_PRO_PRICE_ID_INR` in config | MED | Feature present and correct, **but file name diverges** from playbook skill file `geo-pricing.md` and from v2.1 enhancement prompt. |
| Free-tier interview Q limit (3/mo) | `app/services/plan_limits.py`, Redis-backed | Implemented in `app/services/usage_service.py` (DB-backed, `usage_logs` table, monthly window) — no Redis counter | MED | Works (tests in `test_usage_limits.py` green), but playbook's named service and Redis key pattern don't match. |
| Free-tier 15 Foundation cards | `app/services/plan_limits.py` enforcement | Cards API gating TBD — not verified in this pass | MED | Flag for P5-S0b to confirm where the 15-card wall actually lives. |
| IP registration blocking (max 2/30d) | `app/services/registration_guard.py`, Redis TTL 30d | Implemented inline in `app/api/v1/routes/auth.py` (lines 116-156 approx.) using `RegistrationLog` DB table + 30-day window query — **no Redis**, **no separate guard service** | MED | Works (tests in `test_registration_limit.py` green) but architecture diverges from playbook spec completely. |
| Tracker auto-populate from ATS scan | `app/services/tracker_service.py` `create_from_scan()` | `app/services/tracker_service_v2.py` + `app/models/tracker.py` (`TrackerApplicationModel`, table `tracker_applications_v2`), migration `e4eab11b8e33` adds `scan_id`, `skills_matched`, `skills_missing` | LOW | Feature present; file renamed `tracker_service_v2.py`. |
| LLM multi-model router | `app/services/llm_router.py` with `TaskType` enum + `get_llm_client(task_type)` | Actual: `app/core/llm_router.py` with `generate_for_task(task, prompt, ...)` — task-name based, not enum; provider dispatch is module-level functions `_call_gemini/_call_anthropic/_call_openai` | **HIGH** | API shape and location both diverge from what the playbook prescribes. **CLAUDE.md already corrects this** (rule 11 cites `app/core/llm_router.py`), but playbook + SESSION-STATE do not. |
| Legacy LLM factory | Not documented | `app/services/llm/factory.py` + `gemini_provider.py` + `claude_provider.py` still exist alongside the router (see Pass 2). | MED | Undocumented dual system. |
| Phase-1 sub-specs (`11a`..`11d`) | Playbook Section 3.3 enumerates `11a-free-tier-limits.md`, `11b-tracker-autopopulate.md`, `11c-ip-registration-blocking.md`, `11d-llm-router.md` | **None of these spec files exist** in `docs/specs/phase-1/`. Only `03`-`11` (no a/b/c/d). | **HIGH** | Four missing spec files for features that are already in production. The backfill is queued as P5-S1..S7 but not run. |

### Phase 2 — Retention + Conversion Engine

Playbook scope: streaks/XP/badges, skill radar + heatmap, Mission Mode, daily email, email prefs.

| Area | Playbook expects | Code shows | Severity | Notes |
|---|---|---|---|---|
| Streaks/XP/badges | `app/services/gamification_service.py`, `gamification_stats`/`badges`/`user_badges` tables | Exists. Migration `802d5ba2e219_add_gamification_tables.py`. Tests in `test_gamification.py`. | LOW | Matches. |
| Skill radar + heatmap | `app/services/progress_service.py`, `/api/v1/progress` | Exists (`progress.py` route + `progress_service.py`). | LOW | Matches. |
| Mission Mode | `app/services/mission_service.py`, `missions`+`mission_days` tables | Exists. Migration `a4f1d8e73b92`. Tests green. | LOW | Matches. |
| Daily email + prefs | `app/services/reminder_service.py` + `email_service.py`, `/api/v1/email-prefs` | All three exist. Migration `c9863b51075d`. Tests in `test_email.py`. | LOW | Matches. |
| **Spec numbering** | `12`, `13-radar-heatmap`, `14-mission-mode`, `15-daily-email`, `16-email-prefs` | **Duplicates**: `13-admin-ai-generator.md` + `13-skill-radar-heatmap.md`; `14-admin-analytics.md` + `14-mission-mode.md`. Admin specs do not belong in Phase 2 per the playbook. | **HIGH** | Two pairs of duplicate numbers. Admin-CRUD/Admin-AI specs also exist in Phase 3 (`17-admin-card-crud.md`, `18-ai-card-generation.md`) → fragmentation between phase-2 and phase-3 admin docs. |
| Extraneous `14-admin-analytics.md` in phase-2 | Not in playbook | Admin insights is Phase 5 work (P5-S31..S33). An early draft apparently landed in phase-2. | **HIGH** | Misleading: file header says "Status: Done" which is false. Move to `phase-5/` or delete. |

### Phase 3 — Content Pipeline + Marketing

Playbook scope: admin CRUD + soft-delete, AI card gen, landing, onboarding polish, My Experience, per-card feedback + NPS, design system + 3 themes, resume-rewrite + cover-letter fix.

| Area | Playbook expects | Code shows | Severity | Notes |
|---|---|---|---|---|
| Admin CRUD + soft-delete | `Card.deleted_at`, filter on queries | `b1674f79f780_add_cards_deleted_at_for_soft_delete.py` + `d16ca29a5d08_add_categories_tags_cards_partial_index_.py`. Model column present. | LOW | Matches. |
| AI card generation | `app/services/ai_card_service.py` | Exists. | LOW | Matches. |
| Landing page | `src/pages/LandingPage.tsx` | Exists. | LOW | Matches. |
| Onboarding polish (persona picker + target fields) | Phase-1 delivered persona picker; Phase-3 polish layer | Persona picker is a `components/onboarding/PersonaPicker.tsx` that `ProtectedRoute` invokes in `App.tsx:39` when `onboarding_completed` is false. | LOW | Matches but note: picker is a component, not a `pages/PersonaPicker.tsx` as Phase-5 spec S17 anticipates. |
| My Experience | `app/services/experience_service.py`, `src/pages/Profile.tsx` button | Service exists; Profile page exists. **Known-broken per SESSION-STATE** (P5-S11 fix queued). | LOW | Drift is a known bug, not a doc issue. |
| Feedback + NPS | `card_feedback` table, `feedback` route | Exists (migration `e5b2c8d4a1f7`, `test_feedback_api.py`). | LOW | Matches. |
| Design system + 3 themes | `src/styles/themes.css`, `src/hooks/useTheme.ts`, `src/components/settings/ThemePicker.tsx` | `src/styles/design-tokens.ts` + `design-tokens.css` (no `themes.css`); theme state in `src/context/ThemeContext.tsx` (no `useTheme.ts` hook); `ThemePicker.tsx` present at the expected path. | **HIGH** | Two named files from the playbook's design-system skill do not exist. Implementation uses design-tokens + context pattern instead. Skill file `design-system.md` needs to be rewritten to match reality. |
| Resume rewrite + cover letter fix | Spec `20c-resume-cover-letter-fix.md` | No such spec. Rewrite bug still open (P5-S9, P5-S10 queued). | MED | Spec referenced by playbook never written; feature not fixed. |
| **Spec numbering** | `17-admin-crud`, `18-ai-cards`, `19-landing`, `20-onboarding`, `20a-my-experience`, `20b-design-system-themes`, `20c-resume-cover-letter-fix`, `21-feedback` | **Duplicates**: `17-admin-card-crud.md` + `17-mission-mode-api.md`; `18-ai-card-generation.md` + `18-mission-mode-ui.md`; `19-feedback-nps-system.md` + `19-landing-page.md`. **Missing**: `20a/20b/20c`. **Misplaced**: `15-ats-scorer-upgrade.md` and `16-experience-generator-api.md` landed in phase-3 instead of phase-1/phase-3 boundaries the playbook draws. Mission-mode specs in phase-3 duplicate the phase-2 mission-mode spec. | **HIGH** | Three pairs of duplicate numbers + three missing specs + phase-boundary ambiguity. Worst directory in the repo for navigation. |

### Phase 4 — Hardening + Observability

Playbook scope: Sentry, PostHog dashboards, performance audit, rate limiting, webhook idempotency, backup/DR, custom domain + SSL + Stripe go-live runbook.

| Area | Playbook expects | Code shows | Severity | Notes |
|---|---|---|---|---|
| Sentry | `SENTRY_DSN` init in `app/main.py` | `app/main.py:56-60` initializes Sentry when DSN set, `traces_sample_rate=0.1`. | LOW | Matches. |
| Rate limiting | slowapi, 100/min global, 10/min auth, 5/min admin gen | `app/core/rate_limit.py` + `auth.py:@limiter.limit("10/minute")` + admin routes. | LOW | Matches. |
| Webhook idempotency | `stripe_events` table, dedupe in `payment_service.handle_webhook` | `app/models/stripe_event.py` + migration `83a02cb65464`. | LOW | Matches but **no dedicated spec** (folded into `22-error-monitoring.md`/`23-error-monitoring.md`). Playbook lists it as spec `24a`. |
| Runbooks | `docs/runbooks/` for backup, stripe, domain | `docs/runbooks/backup-restore.md`, `stripe-go-live.md`, `custom-domain.md` | LOW | All three present. |
| Custom domain + SSL | Spec `25-custom-domain-golive.md` | **Does not exist.** P4-S4 marked done in SESSION-STATE but never had a spec — only a runbook. | MED | Completed work with no retrospective spec. |
| **Spec numbering** | `22-error-monitoring`, `23-posthog-dashboards`, `24-performance-hardening`, `24a-webhook-idempotency`, `25-custom-domain-golive` | **Duplicates**: `22-error-monitoring.md` + `22-landing-page.md`; `22-error-monitoring.md` + `23-error-monitoring.md` are near-duplicates of each other (first says "Status: Done", second says "Status: Complete"). **Missing**: `24a-webhook-idempotency.md`, `25-custom-domain-golive.md`. **Stray**: `20-ai-feedback-digest.md` (status "Deferred") + `22-landing-page.md` (status "Deferred") belong somewhere else or should be deleted. | **HIGH** | Phase-4 has near-duplicate error-monitoring specs, a stray "landing page" spec (status Deferred) that belongs in phase-3, and a stray `20-ai-feedback-digest.md` that isn't tracked in the playbook at all. |

---

## PASS 2 — Undocumented Features (built ad-hoc, need backfilled specs)

### Backend

| Feature | Where it lives | Why undocumented | Backfill target |
|---|---|---|---|
| **Multi-model LLM router (actual impl)** | `app/core/llm_router.py` | Built but location + API shape differ from playbook's `app/services/llm_router.py` + `TaskType` enum. Envisioned spec `11d-llm-router.md` never written. | `docs/specs/phase-5/` backfill (P5-S1). Update `.agent/skills/llm-strategy.md` at the same time. |
| **Legacy LLM provider factory** | `app/services/llm/factory.py` + `claude_provider.py` + `gemini_provider.py` | Parallel abstraction that predates the router. `gpt_service.py:7` still imports `generate_for_task` from the router, but the `llm/` factory is reachable via `get_llm_provider()` — which `CLAUDE.md` rule 11 forbids calling. No spec documents either the legacy path or the sunset plan. | Flag for deletion or documentation in P5-S0b. If kept, write a one-paragraph "legacy provider factory — do not use" note into `llm-strategy.md`. |
| **Geo-pricing service** | `app/services/geo_pricing_service.py` (module-level `get_pricing(ip)` function) | Exists; spec `11-stripe-integration.md` covers Stripe checkout but not the ip-api.com + Redis cache path and currency mapping. | P5-S3 backfill already queued; confirm it captures the 24h Redis cache TTL (`_GEO_CACHE_TTL = 86_400`) and the default-to-USD fallback. |
| **IP registration blocking** | `app/api/v1/routes/auth.py` (inline) using `RegistrationLog` DB table, 30-day window, max-2 constant `_MAX_REGISTRATIONS_PER_IP = 2` | No service module, no spec. Not in playbook's Phase-0 architecture notes either. | P5-S4 backfill queued; note the DB-based (not Redis) implementation. |
| **Free-tier interview Q gate** | `app/services/usage_service.py` (`usage_logs` table, monthly window query) | Playbook calls this `plan_limits.py`; no spec `11a-free-tier-limits.md` exists. | P5-S6 backfill. |
| **Resume template catalog** | `app/services/resume_templates.py` | Not mentioned anywhere in playbook. | Decide in P5-S0b: spec-backfill or delete. |
| **Formatter check** | `app/services/formatter_check.py` | Not mentioned in playbook; likely feeds ATS formatting issues panel. | Decide in P5-S0b. |
| **Bullet analyzer** | `app/services/bullet_analyzer.py` + `BulletAnalyzer.tsx` | ATS-scanner extension; not spec'd separately. | Low-priority backfill. |
| **Persona-onboarding flow details** | `User.onboarding_completed` + `ProtectedRoute` branching in `App.tsx` | Onboarding-flow spec exists but doesn't describe the "gate until onboarding_completed" logic in the frontend router. | Amend `09-onboarding-flow.md`. |
| **v1 duplicate routers (`/api/*`)** | 5 legacy routers (`analyze`, `rewrite`, `cover_letter`, `interview`, `tracker`) mounted in `app/main.py:119-123` alongside their v1 siblings | Playbook does not explicitly sanction the parallel surface. AGENTS.md does (routes table), but the sunset/deprecation plan is unwritten. | Decide in P5-S0b: document the legacy surface in AGENTS.md (already partially there), add a sunset ADR, or delete. |

### Frontend

| Feature | Where it lives | Why undocumented | Backfill target |
|---|---|---|---|
| **Design-token system** | `src/styles/design-tokens.ts` + `design-tokens.css` + Tailwind integration (`bg-bg-surface`, `text-text-primary`, etc. per `CLAUDE.md` rule 12) | Playbook's `design-system.md` skill describes a different implementation (`themes.css` + `useTheme.ts`). Reality is token-first with Tailwind utilities; themes live in `context/ThemeContext.tsx`. | P5-S2 backfill + rewrite of `.agent/skills/design-system.md` to match the token+context implementation. |
| **"Midnight Forge" landing design** | `LandingPage.tsx` + landing-specific styles | Playbook enhancement #5.8 marks it Done, but no spec exists. | P5-S7 backfill queued. |
| **Persona picker as component (not page)** | `src/components/onboarding/PersonaPicker.tsx` | Phase-5 spec S15/S17 anticipates a `pages/PersonaPicker.tsx`; reality is a component used inside `ProtectedRoute` when `onboarding_completed` is false. | P5-S15 spec needs to reconcile: either migrate to page or update the spec to match the component pattern. |
| **UI primitives** | `src/components/ui/` (AnimatedCard, GlowButton, ProgressBar, ScoreBadge, SkeletonLoader, Tooltip, UpgradeModal) | Never spec'd; live alongside the design tokens. | No backfill needed — document alongside design-system spec. |
| **Upload + dashboard clusters** | `src/components/upload/` (JDInput, ResumeDropzone), `src/components/dashboard/` (ATSScoreGauge, JobFitExplanation, MissingSkillsPanel, KeywordChart, ScoreBreakdown, SkillOverlapChart, FormattingIssues, ImprovementSuggestions, BulletAnalyzer) | Phase-5 spec P5-S20/S21 wants to reorganize the results page; none of these components are inventoried anywhere. | Mention in P5-S20 spec as the surface being reordered. |

---

## PASS 3 — Docs That Reference Non-Existent Files

Scope: `skillforge_playbook_v2.md`, `claude-code-prompts-all-phases-v2.md`, `claude-code-prompts-all-phases-v2.2-patch.md`, `local-setup-guide.md`, `SESSION-STATE.md`, `AGENTS.md`, `CLAUDE.md`.

| Reference | Referenced in | Reality | Severity |
|---|---|---|---|
| `app/services/llm_router.py` | `skillforge_playbook_v2.md` §4.2 + §4.4; `SESSION-STATE.md` Hard Constraints line | Code is at `app/core/llm_router.py`. `CLAUDE.md` rule 11 already has the correct path. | **HIGH** — SESSION-STATE is loaded every slice; this misleads Claude Code. |
| `app/services/registration_guard.py` | `skillforge_playbook_v2.md` §4.5 + §9 enhancement prompt | No such file; logic inlined in `app/api/v1/routes/auth.py`. | MED |
| `app/services/plan_limits.py` | `skillforge_playbook_v2.md` §4.5 + §9 enhancement prompt | No such file; logic in `app/services/usage_service.py`. | MED |
| `app/services/geo_service.py` | `skillforge_playbook_v2.md` §9 enhancement prompt + `.agent/skills/geo-pricing.md` | Named `app/services/geo_pricing_service.py`. | MED |
| `src/styles/themes.css` | `skillforge_playbook_v2.md` §4.6; `.agent/skills/design-system.md` | No such file; design tokens in `design-tokens.ts` + `design-tokens.css`. | MED |
| `src/hooks/useTheme.ts` | `skillforge_playbook_v2.md` §4.6 + §9 | No such file; theme state in `src/context/ThemeContext.tsx`. | MED |
| `docs/specs/phase-1/11a-free-tier-limits.md` | Playbook §3.3 | Missing. | **HIGH** |
| `docs/specs/phase-1/11b-tracker-autopopulate.md` | Playbook §3.3 | Missing. | **HIGH** |
| `docs/specs/phase-1/11c-ip-registration-blocking.md` | Playbook §3.3 | Missing. | **HIGH** |
| `docs/specs/phase-1/11d-llm-router.md` | Playbook §3.3 + §9 | Missing. | **HIGH** |
| `docs/specs/phase-3/20a-my-experience.md` | Playbook §3.3 | Missing (My Experience spec is at `22-my-experience.md` in phase-3). | MED |
| `docs/specs/phase-3/20b-design-system-themes.md` | Playbook §3.3 + §9 enhancement prompt | Missing. | **HIGH** |
| `docs/specs/phase-3/20c-resume-cover-letter-fix.md` | Playbook §3.3 + §9 enhancement prompt | Missing. | **HIGH** |
| `docs/specs/phase-4/24a-webhook-idempotency.md` | Playbook §3.3 | Missing (idempotency folded into `22-error-monitoring.md`). | MED |
| `docs/specs/phase-4/25-custom-domain-golive.md` | Playbook §3.3 | Missing (only runbook `docs/runbooks/custom-domain.md` exists). | MED |
| `docs/specs/phase-1/02-user-roles.md` | Playbook §3.3 | Missing — promoted to `phase-0/03-user-role-admin.md`. | LOW |
| `claude-code-prompts-all-phases.md` (v1) | H.3 housekeeping in v2 prompts | Exists at `/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/claude-code-prompts-all-phases.md`. Archive copy also at `archive/claude-code-prompts-all-phases.md`. Both present — H.3 can run. | LOW |
| `ClaudeSkillsforge_sessiontext.docx` | SESSION-STATE.md inventory + H.1 | Not on disk (not required — this lives in Anthropic "Project knowledge", outside the repo). Remove from the on-disk inventory or label it explicitly as external. | LOW |
| `STRATEGIC-OPTIONS.md` | SESSION-STATE.md Project File Inventory (no path prefix) | Actually at `hireportai/STRATEGIC-OPTIONS.md`. Correct but untracked in git. | LOW |
| `skillforge_playbook_v2.md` "in project root or docs/" | Playbook P5-S0 prompt | File lives one level above `hireportai/` (at SkillForge/). Neither location is right. | LOW |
| `scripts/health_check.sh` | `local-setup-guide.md` §13 | Does not exist in `hireportai/scripts/` (which contains `dev-start.sh`, `dev-stop.sh`, `dev-status.sh`, `start.sh`, `stop.sh`). | MED |
| `hireport-frontend/tests/` scaffold | `local-setup-guide.md` §4 | Actual test dir is `hirelens-frontend/src/test/setup.ts` (single setup file) + colocated `__tests__/` folders. Doc's `hirelens-frontend/tests/` does not exist. | LOW |
| `app/templates/` scaffold | `local-setup-guide.md` §4 | Not present under `hirelens-backend/app/`. | LOW |

---

## PASS 4 — Spec File Inventory

### Phase 0 (`docs/specs/phase-0/`, 6 files)

| File | Number | Status | Notes |
|---|---|---|---|
| `00-postgresql-migration.md` | 00 | Done | OK |
| `01-alembic-setup.md` | 01 | Done | Not in playbook numbering |
| `02-auth-unification.md` | 02 | Done | OK |
| `02a-skeleton-deploy.md` | 02a | Done | OK |
| `02b-cicd-pipeline.md` | 02b | Done | OK |
| `03-user-role-admin.md` | 03 | Done | Playbook put this at `02`; number drifted |

No duplicates. One gap relative to playbook (playbook had `02-user-roles`, code has it at `03`).

### Phase 1 (`docs/specs/phase-1/`, 9 files)

| File | Number | Status | Notes |
|---|---|---|---|
| `03-card-extraction.md` | 03 | Partially Done (gaps in P1-S1) | Crosses phases — numbered `03` in phase-1 directory |
| `04-cards-api.md` | 04 | Done | OK |
| `05-fsrs-daily-review.md` | 05 | *(no Status header)* | OK |
| `06-study-dashboard-ui.md` | 06 | *(no Status header)* | OK |
| `07-card-viewer-ui.md` | 07 | *(no Status header)* | OK |
| `08-ats-card-mapping.md` | 08 | *(no Status header)* | OK |
| `09-onboarding-flow.md` | 09 | *(no Status header)* | OK |
| `10-posthog-analytics.md` | 10 | *(no Status header)* | OK |
| `11-stripe-integration.md` | 11 | *(no Status header)* | Geo-pricing work happens here but not explicitly spec'd |

**Duplicates**: none.
**Gaps vs playbook**: missing `11a`, `11b`, `11c`, `11d` (the v2.1 enhancement specs).
**Status headers absent** on 7 of 9 specs — hard to tell from the file which are Done.

### Phase 2 (`docs/specs/phase-2/`, 9 files)

| File | Number | Status | Notes |
|---|---|---|---|
| `10-streaks-xp-badges.md` | 10 | Done | OK |
| `11-gamification-ui.md` | 11 | Done | OK |
| `12-admin-card-crud.md` | 12 | Done | **Playbook puts admin in Phase 3** |
| `13-admin-ai-generator.md` | 13 | Done | **Playbook puts admin in Phase 3**; **duplicate number** with `13-skill-radar-heatmap.md` |
| `13-skill-radar-heatmap.md` | 13 | *(no Status header)* | **Duplicate number with `13-admin-ai-generator.md`** |
| `14-admin-analytics.md` | 14 | Done | **Does not belong in Phase 2** (admin insights is Phase 5 scope); **duplicate number** with `14-mission-mode.md` |
| `14-mission-mode.md` | 14 | Done | **Duplicate number with `14-admin-analytics.md`** |
| `15-daily-email.md` | 15 | Done | OK |
| `16-email-preferences.md` | 16 | Done | OK |

**Duplicates**: 2 pairs (`13`, `14`).
**Misfiled**: `12`/`13-admin-ai-generator`/`14-admin-analytics` belong in later phases.

### Phase 3 (`docs/specs/phase-3/`, 11 files)

| File | Number | Status | Notes |
|---|---|---|---|
| `15-ats-scorer-upgrade.md` | 15 | Done | Phase-boundary ambiguity (ATS bridge is Phase 1/3) |
| `16-experience-generator-api.md` | 16 | Done | OK |
| `17-admin-card-crud.md` | 17 | Done | **Duplicate of phase-2/12-admin-card-crud.md content**; **duplicate number with `17-mission-mode-api.md`** |
| `17-mission-mode-api.md` | 17 | Done | **Mission Mode belongs in Phase 2**; **duplicate number with `17-admin-card-crud.md`** |
| `18-ai-card-generation.md` | 18 | Done | **Duplicate number with `18-mission-mode-ui.md`** |
| `18-mission-mode-ui.md` | 18 | Done | **Mission Mode belongs in Phase 2**; **duplicate number** |
| `19-feedback-nps-system.md` | 19 | Done | **Duplicate number with `19-landing-page.md`** |
| `19-landing-page.md` | 19 | *(no Status header — file starts with `# Spec #19`)* | **Duplicate number** |
| `20-onboarding-polish.md` | 20 | *(no Status header)* | OK |
| `21-card-feedback.md` | 21 | Done | Possibly duplicates `19-feedback-nps-system.md` scope |
| `22-my-experience.md` | 22 | Done | Number drifted — playbook had this at `20a` |

**Duplicates**: 3 pairs (`17`, `18`, `19`).
**Missing**: `20a`, `20b-design-system-themes`, `20c-resume-cover-letter-fix`.
**Scope overlap**: feedback appears in both `19-feedback-nps-system` and `21-card-feedback`.

### Phase 4 (`docs/specs/phase-4/`, 6 files)

| File | Number | Status | Notes |
|---|---|---|---|
| `20-ai-feedback-digest.md` | 20 | Deferred | Stray — not in playbook; should move or delete |
| `22-error-monitoring.md` | 22 | Done | **Duplicate number with `22-landing-page.md`**; **near-duplicate content with `23-error-monitoring.md`** |
| `22-landing-page.md` | 22 | Deferred | **Duplicate number**; should be in phase-3 and is already superseded by `phase-3/19-landing-page.md` |
| `23-error-monitoring.md` | 23 | Complete | **Near-duplicate of `22-error-monitoring.md`**; `23` should be PostHog dashboards per playbook |
| `24-posthog-dashboards.md` | 24 | Complete | OK |
| `25-performance-hardening.md` | 25 | Complete | OK but playbook's `25` is "custom-domain-golive" — mismatch |

**Duplicates**: `22` (two files), `22`/`23` near-duplicate content.
**Missing**: `24a-webhook-idempotency`, `25-custom-domain-golive` (work is done; only runbooks exist).
**Stray**: `20-ai-feedback-digest.md`.

### Phase 5 (`docs/specs/phase-5/`)

Directory **does not exist yet**. Every backfill slice (P5-S1..S7) and every new spec (P5-S15, S23, S26, S28, S31, S34) will need to create it.

### Summary

- **Total spec files**: 41 across phases 0-4.
- **Duplicate-number pairs**: 7 (`phase-2`:2, `phase-3`:3, `phase-4`:2).
- **Missing specs referenced by playbook**: at least 9 (`phase-1`:4, `phase-3`:3, `phase-4`:2).
- **Specs with no `## Status` line**: 10 (mostly phase-1 and phase-3).
- **Misplaced by phase**: 4 (`phase-2/12`, `phase-2/13-admin-ai`, `phase-2/14-admin-analytics`, `phase-4/22-landing-page`).

---

## PASS 5 — Test Suite Baseline

**Command (backend)**: `cd hirelens-backend && python -m pytest tests/ --tb=no -q -m "not integration"`
**Command (frontend)**: `cd hirelens-frontend && npx vitest run --reporter=dot`
**Run at**: 2026-04-17 09:30 local (pre-Phase-5 baseline).

### Backend

- **Total collected**: 173 tests (31 test files).
- **Deselected (integration marker)**: 6.
- **Passed**: **167**.
- **Failed**: 0.
- **Warnings**: 8 (all `datetime.utcnow()` deprecations in `usage_service.py` + two test files, plus one FastAPI `HTTP_422_UNPROCESSABLE_ENTITY` deprecation in `test_feedback_api.py`).
- **Runtime**: 5.79s.

### Frontend

- **Test files**: 1 (`src/components/__tests__/PaywallModal.test.tsx`).
- **Tests**: 5.
- **Passed**: **5**.
- **Failed**: 0.
- **Runtime**: 1.40s.

### Baseline notes

- Backend coverage is broad (auth, cards, study, mission, gamification, payments, geo-pricing, llm_router, rate-limit, registration-limit, usage-limits, etc.) and green. Safe to start Phase 5.
- Frontend suite is thin — only `PaywallModal` has tests. Phase 5 slices that introduce `PersonaPicker`, `HomeDashboard`, `TopNav`, `CardChatPanel`, etc. should each add a component test so this number grows from 5 toward the 80% target in AGENTS.md.
- The 8 `utcnow()` deprecation warnings are not urgent but will become errors on Python 3.14. Worth a one-line cleanup during the first touch of `usage_service.py`.
- Integration-marker tests (6) are gated out of CI by design per `CLAUDE.md` rule 13. They require live LLM keys; run locally before any slice that touches extraction, embeddings, or LLM services.

---

## Recommended P5-S0b Fix List (sorted by severity)

**HIGH — fix first**:

1. Correct `SESSION-STATE.md` Hard Constraints: `app/services/llm_router.py` → `app/core/llm_router.py`.
2. Rewrite `.agent/skills/llm-strategy.md` and the playbook enhancement prompt to match the actual router (`generate_for_task` task-name API, `app/core/llm_router.py` path, FAST_TASKS / REASONING_TASKS frozensets).
3. Resolve spec-number collisions in `phase-2` (2 pairs), `phase-3` (3 pairs), `phase-4` (1 pair + 1 near-duplicate). Renumber newer files to the next free number per phase and update any cross-references.
4. Move the four "misfiled" admin/mission specs out of the wrong phase directories.
5. Backfill or delete the 9 missing-but-referenced specs (`phase-1/11a..d`, `phase-3/20a..c`, `phase-4/24a`, `phase-4/25`).
6. Rewrite `.agent/skills/design-system.md` to match the design-tokens + ThemeContext implementation (no `themes.css`, no `useTheme.ts`).

**MED — fix during P5 housekeeping**:

7. Rename `geo_pricing_service.py` references in docs (or rename the file — whichever is less disruptive; doc fix is simpler).
8. Note in AGENTS.md / a new `runbooks/llm-legacy-factory.md` that `app/services/llm/factory.py` is deprecated; plan removal.
9. Create `scripts/health_check.sh` to match `local-setup-guide.md §13`, or update the setup guide to reflect the actual `scripts/dev-*.sh` family.
10. Move `phase-4/20-ai-feedback-digest.md` and `phase-4/22-landing-page.md` (both Deferred) to a `docs/specs/deferred/` directory or delete.

**LOW — cosmetic, batch with next doc edit**:

11. Fix playbook's "project root or docs/" self-reference to the actual location under `SkillForge/`.
12. Fix `SESSION-STATE.md` inventory to label `ClaudeSkillsforge_sessiontext.docx` as "external — Claude Project knowledge, not on disk".
13. Add `## Status:` headers to the 10 specs that lack them.

No code changes anywhere in P5-S0b — this is a documentation sync only.
