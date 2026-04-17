# SkillForge — Claude Code Prompts (All Phases) — v2.1

> **How to use**: Copy-paste each prompt into Claude Code **one at a time**.
> Wait for completion, review output, then proceed.
> Start a **new Claude Code session** at every `--- NEW SESSION ---` marker.
> Each session should stay under 5 slices to avoid context degradation.
>
> **Standard prompt header for every slice**:
> `Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-N/NN-feature.md.`
>
> - **AGENTS.md** = how this project works (stack, conventions, deploy)
> - **CLAUDE.md** = how to behave (rules, 3-strike, test gates)
> - **SESSION-STATE.md** = where we are right now (last slice, broken features, active refactors)
> - **spec file** = what to build right now
>
> **Status tags**: ✅ DONE / 🟡 PARTIAL / 🔴 PENDING / 🆕 NEW

---

# ═══════════════════════════════════════════
# IMPLEMENTATION STATUS SUMMARY
# ═══════════════════════════════════════════

| Phase | Original Scope | Status | Notes |
|-------|----------------|--------|-------|
| Phase 0 | Foundation + Deploy | ✅ DONE | PG migration, auth, roles, deploy, CI/CD all green |
| Phase 1 | Study Engine + ATS Bridge | ✅ DONE | All 23 slices complete, tests passing |
| Phase 2 | Retention + Conversion | ✅ DONE | Streaks, XP, badges, Mission Mode, daily email |
| Phase 3 | Content + Marketing | ✅ DONE | Admin CRUD, AI cards, landing page, onboarding |
| Phase 4 | Hardening + Observability | ✅ DONE | Sentry, PostHog dashboards, rate limiting, custom domain |
| **Phase 5** | **Enhancements + UX Restructure** | 🟡 **MIXED** | **See Phase 5 status table below** |

## Phase 5 Status (the new work tracked here)

| # | Feature | Status |
|---|---------|--------|
| 5.1 | Multi-model LLM router (Flash vs Pro) | ✅ DONE |
| 5.2 | Design system — three themes with CSS tokens | ✅ DONE |
| 5.3 | Geo-based pricing (USD/INR via ip-api.com + Redis) | ✅ DONE |
| 5.4 | Anti-abuse — duplicate registration block by IP | ✅ DONE |
| 5.5 | Job tracker auto-populate from ATS scan | ✅ DONE |
| 5.6 | Free tier limit on interview question generation | ✅ DONE |
| 5.7 | HirePort → SkillForge branding pass | ✅ DONE |
| 5.8 | "Midnight Forge" landing page redesign | ✅ DONE |
| 5.9 | Doc audit + sync (master playbook ↔ codebase) | 🔴 PENDING |
| 5.10 | Navigation restructure (/learn/* and /prep/*) | 🔴 PENDING |
| 5.11 | Persona-aware home dashboard at /home | 🔴 PENDING |
| 5.12 | Mandatory PersonaPicker on first login | 🔴 PENDING |
| 5.13 | Geo-pricing IP detection on registration page | 🟡 PARTIAL — verify it shows on signup, not just checkout |
| 5.14 | Interview date picker (optional) on persona select | 🔴 PENDING |
| 5.15 | AI resume rewrite — fix missing original content | 🟡 PARTIAL — known broken |
| 5.16 | Cover letter generation — fix format issues | 🟡 PARTIAL — known broken |
| 5.17 | Interview Prep — store generated questions per JD | 🔴 PENDING |
| 5.18 | "Generate My Experience" on Profile — fix | 🟡 PARTIAL — known broken |
| 5.19 | Job Fit Explanation — move above the fold | 🔴 PENDING |
| 5.20 | Analysis Results education + keyword color fix | 🔴 PENDING |
| 5.21 | Pro-gating: missing skills → flashcards (Pro), upsell (Free) | 🔴 PENDING |
| 5.22 | Stripe — subscription cancellation flow | 🔴 PENDING |
| 5.23 | Settings persistence for existing registered users | 🔴 PENDING |
| 5.24 | Chat with AI during flashcard study | 🔴 PENDING |
| 5.25 | Admin LLM-driven analytics dashboard | 🔴 PENDING |
| 5.26 | Content Feed Flow (admin) | 🔴 PENDING |

---

# ═══════════════════════════════════════════
# FUTURE / HOUSEKEEPING TODO
# ═══════════════════════════════════════════

These are not slices — they're project hygiene reminders that don't fit into any phase. They're tracked here so they don't get lost. P5-S35 (Final Verification) executes these as part of Phase 5 closeout.

| # | Item | When | Why |
|---|------|------|-----|
| H.1 | **Archive `ClaudeSkillsforge_sessiontext.docx`** from project knowledge | After Phase 5 completes | The transcript captures all our prior conversations — useful for AI-assisted recall during active development, but adds noise once Phase 5 docs are stable. It'll have served its purpose. |
| H.2 | Roll up Phase 5 learnings into Playbook v3 | After P5-S35 verify passes | Promote Phase 5 from "appendix" to first-class phase. Update Bootstrap Protocol, refresh persona journey tables, integrate doc-sync workflow. |
| H.3 | Move `claude-code-prompts-all-phases.md` (v1) to `archive/` | Same time as H.2 | Keep for historical reference, but remove from project knowledge to prevent confusion between v1 and v2.1. |
| H.4 | Audit `local-setup-guide.md` for v3 changes | Same time as H.2 | New env vars from Phase 5 (chat-with-AI rate limits, admin insights cache TTL, persona migration flags) need to land here. |
| H.5 | Create `RUNBOOK.md` for prod incidents | Phase 6 / first month post-launch | Captures: how to roll back, how to flush Redis cache, how to revoke a session, how to manually reconcile a Stripe subscription. |

---

# ═══════════════════════════════════════════
# PHASE 0: Foundation Surgery + Skeleton Deploy ✅ DONE
# ═══════════════════════════════════════════
# All slices complete. Skip unless re-verifying.
# Original prompts preserved in v1 for reference.

---

# ═══════════════════════════════════════════
# PHASE 1: Core Study Engine + ATS Bridge ✅ DONE
# ═══════════════════════════════════════════
# All 23 slices complete. Skip unless re-verifying.

---

# ═══════════════════════════════════════════
# PHASE 2: Retention + Conversion Engine ✅ DONE
# ═══════════════════════════════════════════
# All 11 slices complete. Skip unless re-verifying.

---

# ═══════════════════════════════════════════
# PHASE 3: Content Pipeline + Marketing ✅ DONE
# ═══════════════════════════════════════════
# All 7 slices complete. Skip unless re-verifying.

---

# ═══════════════════════════════════════════
# PHASE 4: Hardening + Observability ✅ DONE
# ═══════════════════════════════════════════
# All 4 slices complete. Skip unless re-verifying.

---

# ═══════════════════════════════════════════
# PHASE 5: Enhancements + UX Restructure 🆕
# ═══════════════════════════════════════════
# This is the new work. Run prompts in order.
# Slices marked DONE are documented for spec/test-coverage backfill.
# Slices marked PENDING or PARTIAL are what you actually need to execute.
# Every slice ends with "Update SESSION-STATE.md" so the live state stays accurate.

## --- NEW SESSION --- Phase 5-PRE: Doc Sync + Codebase Audit (CRITICAL — RUN FIRST)

### P5-S0: Master Doc Audit + Sync 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/prd.md.

I need a 3-way sync audit between the master docs and the actual codebase BEFORE we start any new feature work. Do NOT change any code. Output a single audit report only.

PASS 1 — DRIFT DETECTION
1. Read skillforge_playbook_v2.md (in project root or docs/).
2. Read claude-code-prompts-all-phases-v2.md.
3. Read local-setup-guide.md.
4. For each phase (0-4), list what the playbook says vs what actually exists in:
   - hirelens-backend/app/models/
   - hirelens-backend/app/services/
   - hirelens-backend/app/api/routes/
   - hirelens-backend/alembic/versions/
   - hirelens-frontend/src/pages/
   - hirelens-frontend/src/components/
5. Flag every drift with: file path, what playbook expects, what code shows, severity (high/med/low).

PASS 2 — UNDOCUMENTED FEATURES
List every backend service or frontend page that exists in the code but is NOT mentioned in the playbook. These are the features built ad-hoc that need backfilled specs.

PASS 3 — DOCS THAT REFERENCE NON-EXISTENT FILES
grep through the master docs for every file path reference. Mark any that point to files that don't exist on disk.

PASS 4 — SPEC FILE INVENTORY
List every file in docs/specs/. For each: phase, spec number, status field value, last modified date. Flag duplicates (e.g., 04-09 appearing twice) and gaps in numbering.

OUTPUT: a single report at docs/audit/2026-04-doc-sync-audit.md with all four passes. Do NOT modify any other file. Stop after the report is written so I can review.

After report is written, append a one-line entry to SESSION-STATE.md under "Last Completed Slice".
```

### P5-S0b: Apply Doc Sync Fixes 🔴 PENDING (run after reviewing P5-S0 report)

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/audit/2026-04-doc-sync-audit.md.

Now apply the fixes I've approved from the audit report. For each approved item:

1. If it's a doc-only fix (master doc says X, code does Y, code is right): update the master doc.
2. If it's a missing spec: create the spec file in docs/specs/phase-N/ using the spec template, marking it as "Status: Done — Backfilled".
3. If it's a duplicate spec number: rename the newer one to the next available number and update any references.
4. If it's a broken file reference: either fix the path or remove the reference.
5. Do NOT change any code. Doc sync only.

Run: ls docs/specs/phase-*/ to verify clean numbering.

Update SESSION-STATE.md: mark P5-S0b done, set next slice.

Commit: git add docs/ SESSION-STATE.md && git commit -m "docs: sync master docs with codebase per audit"
```

---

## --- NEW SESSION --- Phase 5A: DONE Features — Spec Backfill (Optional)

> Skip this session if you don't need formal specs for completed work. Run it if you want spec coverage for compliance/handoff.

### P5-S1: Backfill Spec — Multi-Model LLM Router ✅ DONE (spec backfill)

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

The multi-model LLM router is already built in app/services/llm_router.py (or similar — find it). Backfill the spec.

1. Read the actual implementation: app/services/llm_router.py and any tests/test_llm_router.py.
2. Create docs/specs/phase-5/25-llm-router.md with:
   - Problem: single-model usage was either too slow (Pro for everything) or too weak (Flash for everything).
   - Solution: route by task type — Flash for fast tasks (card extraction, simple Q&A), Pro for complex reasoning (resume rewrite, gap analysis, cover letter).
   - Acceptance Criteria (reverse-engineered from code).
   - The actual model-to-task mapping table.
   - Cost/latency tradeoffs per route.
   - Test plan (existing tests).
   - Status: Done — Backfilled.
3. Do NOT change code. Spec only.

Update SESSION-STATE.md.
Commit: git add docs/specs/phase-5/ SESSION-STATE.md && git commit -m "docs(spec): backfill LLM router spec — closes spec #25"
```

### P5-S2: Backfill Spec — Design System (Three Themes) ✅ DONE (spec backfill)

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

The three-theme design system is in src/styles/ (or wherever CSS variable tokens live). Backfill the spec.

1. Read every CSS variable file and theme switcher component.
2. Create docs/specs/phase-5/26-design-system.md with: token catalog (color, spacing, typography), theme names + use cases, dark-mode-first rule, the three theme variants and what differs between them, accessibility notes (contrast ratios), component-level usage examples.
3. Status: Done — Backfilled.

Update SESSION-STATE.md.
Commit: git add docs/specs/phase-5/ SESSION-STATE.md && git commit -m "docs(spec): backfill design system spec — closes spec #26"
```

### P5-S3: Backfill Spec — Geo-Based Pricing ✅ DONE (spec backfill)

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

Geo-based pricing is built — find the geolocation service and the pricing logic.

1. Read app/services/geo_service.py (or equivalent) and the Redis caching layer for IP lookups.
2. Read the pricing component on the frontend and the Stripe integration.
3. Create docs/specs/phase-5/27-geo-pricing.md with: ip-api.com integration, Redis cache key strategy + TTL, fallback when IP lookup fails (default to USD), country-to-currency mapping, Stripe price ID mapping per currency, edge cases (VPN, IP changes mid-session).
4. Status: Done — Backfilled.

Update SESSION-STATE.md.
Commit: git add docs/specs/phase-5/ SESSION-STATE.md && git commit -m "docs(spec): backfill geo-pricing spec — closes spec #27"
```

### P5-S4: Backfill Spec — Anti-Abuse Registration Block ✅ DONE (spec backfill)

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

The duplicate-registration-by-IP block is built. Backfill the spec.

1. Read the registration handler and the IP-tracking logic.
2. Create docs/specs/phase-5/28-anti-abuse-registration.md with: the rule (max N registrations per IP per time window), the data model (or Redis key) tracking attempts, the user-facing error message, bypass procedure for shared-IP edge cases (corporate networks, college dorms), test plan.
3. Status: Done — Backfilled.
4. Note in the spec any known false-positive risk.

Update SESSION-STATE.md.
Commit: git add docs/specs/phase-5/ SESSION-STATE.md && git commit -m "docs(spec): backfill anti-abuse spec — closes spec #28"
```

### P5-S5: Backfill Spec — Job Tracker Auto-Populate ✅ DONE (spec backfill)

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

The job tracker auto-populate from ATS scan is built. Backfill the spec.

1. Read the ATS scan result handler and the job tracker creation flow.
2. Create docs/specs/phase-5/29-tracker-autopopulate.md with: which fields are auto-extracted (company, role, JD text, scan date, ATS score, key gaps), the user confirmation step (or auto-create), edit-after-create behavior, test plan.
3. Status: Done — Backfilled.

Update SESSION-STATE.md.
Commit: git add docs/specs/phase-5/ SESSION-STATE.md && git commit -m "docs(spec): backfill tracker auto-populate spec — closes spec #29"
```

### P5-S6: Backfill Spec — Free Tier Interview Question Limits ✅ DONE (spec backfill)

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

Free tier limits on interview question generation are in place. Backfill the spec.

1. Read the interview question generator service and the gating logic.
2. Create docs/specs/phase-5/30-free-tier-interview-limits.md with: the exact limit (N generations per day/week/month), the counter storage (DB column or Redis), the paywall trigger UX, the upgrade-to-Pro flow, test plan.
3. Status: Done — Backfilled.
4. **Verify the actual limit value matches what we want** — note in the spec what the current limit is and flag if it should change.

Update SESSION-STATE.md.
Commit: git add docs/specs/phase-5/ SESSION-STATE.md && git commit -m "docs(spec): backfill interview question free limits — closes spec #30"
```

### P5-S7: Backfill Spec — Branding + Landing Page ✅ DONE (spec backfill)

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

1. Create docs/specs/phase-5/31-branding-skillforge.md documenting: product name (SkillForge), tagline, three engines (Lens/Forge/Mission), color rules, logo usage, the HirePort retention in legal footer only.
2. Create docs/specs/phase-5/32-landing-page-midnight-forge.md documenting: the 8-section layout, "Midnight Forge" design tokens (#06060A base, three accent colors per engine), conversion hierarchy, CTA copy.
3. Status on both: Done — Backfilled.

Update SESSION-STATE.md.
Commit: git add docs/specs/phase-5/ SESSION-STATE.md && git commit -m "docs(spec): backfill branding + landing page specs"
```

---

## --- NEW SESSION --- Phase 5B: Verify + Fix PARTIAL Features

### P5-S8: Verify Geo-Pricing Shows on Signup Page 🟡 PARTIAL

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-5/27-geo-pricing.md.

The geo-pricing logic exists but I'm not sure it surfaces correctly at every entry point. Audit:

1. List every page/component that displays a price: signup, pricing section on landing, checkout, paywall modal, profile (if shown), email templates.
2. For each, check whether it uses the geo-pricing service or hardcodes USD.
3. Report findings as a table: | Location | Uses geo-pricing? | Default if no IP | Notes |.
4. Do NOT change code yet. Stop after the audit so I can decide which gaps to close.

After my approval, fix the gaps in a follow-up prompt and update SESSION-STATE.md.
```

### P5-S9: Fix — AI Resume Rewrite Missing Original Content 🟡 PARTIAL

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read .agent/skills/ats-scanner.md (and any rewrite-related skill).

Bug: when user clicks "Rewrite Resume" in AI Optimization, the rewritten version drops sections from the original (work history, education, etc.). The output should be the FULL resume rewritten, not a summary.

1. Read the resume rewrite service: app/services/resume_rewrite_service.py (or similar).
2. Read the prompt template sent to Gemini Pro.
3. Identify whether the issue is:
   a. Prompt asking for rewrite but not enforcing full-document output
   b. Token limit truncating the response
   c. Frontend display dropping sections
   d. Original resume parsing dropping sections before rewrite
4. Report findings + proposed fix. Do NOT change code yet.

After my approval:
5. Apply the fix.
6. Write a regression test: tests/test_resume_rewrite.py — feed a 3-page resume with all standard sections, assert all sections present in output.
7. Run: python -m pytest tests/test_resume_rewrite.py -v
8. Manual test: scan a real resume, click rewrite, confirm all sections preserved.

Update SESSION-STATE.md (remove from known-broken list).
Commit: git add -A && git commit -m "fix(rewrite): preserve all original resume sections in AI rewrite"
```

### P5-S10: Fix — Cover Letter Generation Format 🟡 PARTIAL

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

Bug: cover letter generation produces output that doesn't match the expected format (headers wrong, paragraphs malformed, missing greeting/signature blocks).

1. Read app/services/cover_letter_service.py and the prompt template.
2. Read the frontend component that renders the result.
3. Define the EXPECTED format explicitly: header block (date, recipient), greeting line, 3 body paragraphs (hook, fit, close), signature block.
4. Identify whether the issue is in: the LLM prompt, the response parsing, or the rendering.
5. Report findings + proposed fix. Do NOT change code yet.

After my approval:
6. Apply the fix using a structured response (JSON with named fields, then assembled in Python or React) instead of free-form text.
7. Write tests asserting each section is present.
8. Manual test: generate 3 cover letters for different JDs, verify format consistent.

Update SESSION-STATE.md (remove from known-broken list).
Commit: git add -A && git commit -m "fix(cover-letter): enforce structured format with named sections"
```

### P5-S11: Fix — "Generate My Experience" on Profile 🟡 PARTIAL

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

Bug: the "Generate My Experience" button on the Profile page is not working.

1. Read src/pages/Profile.tsx and the button's onClick handler.
2. Read app/services/experience_service.py (added in P3-S7).
3. Read POST /api/v1/study/experience.
4. Trace the failure: is the button wired? does the API return? does it crash silently? does it require study history that the user doesn't have?
5. Report root cause + proposed fix.

After my approval:
6. Apply the fix.
7. Add an empty-state if user has insufficient study history ("Study at least 10 cards to generate your experience").
8. Add error toast on failure.
9. Manual test: works for user with study history, shows empty state for new user, shows error on simulated failure.

Update SESSION-STATE.md (remove from known-broken list).
Commit: git add -A && git commit -m "fix(profile): repair Generate My Experience flow"
```

---

## --- NEW SESSION --- Phase 5C: UX Restructure — Foundation

### P5-S12: Spec — Navigation Restructure 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/prd.md.

Create docs/specs/phase-5/33-navigation-restructure.md with the spec template:

Problem: Current nav is ATS-first (Analyze, Results, Rewrite, Interview, Tracker). The study engine — the daily retention driver and subscription justification — has no nav presence and is buried.

Solution: Two-namespace nav.
- /learn/* — study engine: Daily Review, Categories, Mission Mode, Progress
- /prep/* — interview prep: Analyze, Results, Rewrite, Interview, Tracker
- /home — persona-aware dashboard
- /profile — user settings + stats

Acceptance Criteria:
- AC-1: Top nav shows Home / Learn / Prep / Profile (and Admin if admin role).
- AC-2: All old flat routes (e.g. /analyze, /results) redirect to their new namespaced paths (/prep/analyze, /prep/results).
- AC-3: Active nav state highlights the correct namespace.
- AC-4: Mobile nav uses a drawer or bottom bar — namespace switcher visible.
- AC-5: Deep links from old emails/PostHog still work via redirects.

Include: full route map (old → new), redirect strategy (server-side 301 or client-side), nav component location, mobile behavior, test plan (every old route resolves).

Add to SESSION-STATE.md "Active Refactor Zones": "Routes about to change — avoid drive-by edits to src/App.tsx".

Do NOT write code yet. Stop after the spec.
```

### P5-S13: Implement — Route Restructure (Backend-friendly redirects + new routes) 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-5/33-navigation-restructure.md.

1. In src/App.tsx (or your router config), add new routes:
   - /home → HomeDashboard (placeholder for now)
   - /learn/daily → DailyReview (move from existing path)
   - /learn/categories → Categories
   - /learn/mission → MissionMode
   - /learn/progress → Progress (skill radar + heatmap)
   - /prep/analyze → AnalyzeResume
   - /prep/results → AnalysisResults
   - /prep/rewrite → AIOptimization
   - /prep/interview → InterviewPrep
   - /prep/tracker → JobTracker
2. Add redirects from every old flat path to the new namespaced path.
3. Update every internal Link/navigate() call across the codebase to use the new paths.
4. Do NOT touch the nav component yet (next slice).
5. Run: npx tsc --noEmit and fix any type errors from broken imports.
6. Run: npx vitest run.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(routes): restructure to /learn/* and /prep/* namespaces — closes spec #33 (routes)"
```

### P5-S14: Implement — New Top Nav Component 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-5/33-navigation-restructure.md.

1. Create src/components/layout/TopNav.tsx with: logo (links to /home), Home / Learn / Prep links, profile dropdown, admin link (if user.role === "admin").
2. Active link highlighting based on URL namespace (matches /learn/* or /prep/*).
3. Mobile: hamburger → drawer with same items.
4. Replace the old navbar everywhere it's rendered.
5. Add PostHog captures: nav_clicked with { namespace, destination }.
6. Manual test: every link works on desktop + mobile, active state updates correctly.

Update SESSION-STATE.md (remove "Active Refactor Zones: routes" once stable).
Commit: git add -A && git commit -m "feat(nav): new namespaced top nav — closes spec #33 (UI)"
```

---

## --- NEW SESSION --- Phase 5D: Persona Picker + Home Dashboard

### P5-S15: Spec — Persona Picker + Home Dashboard 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/prd.md (personas section).

Create docs/specs/phase-5/34-persona-picker-and-home.md:

Problem: We have 4 personas (Interview-Prepper, Career-Climber, Team Lead, New User) but no UX surface that adapts to them. Every user lands on the same generic page.

Solution:
- Mandatory PersonaPicker on first login. Cannot dismiss. Stores user.persona enum + optional interview_target_date.
- /home renders a persona-specific dashboard:
  - Interview-Prepper: countdown, today's mission cards, ATS score progress, next study session
  - Career-Climber: current streak, daily review CTA, skill radar snapshot, recent badge
  - Team Lead: card library quick-browse, share-with-team CTA, team usage stats placeholder
  - New User (no persona yet): redirect to PersonaPicker
- All other routes (/learn/*, /prep/*) gated behind persona being set.

Acceptance Criteria:
- AC-1: New user with no persona is redirected to PersonaPicker on first login regardless of where they land.
- AC-2: PersonaPicker has 4 cards. Selecting one calls POST /api/v1/users/me/persona.
- AC-3: Interview-Prepper card prompts for an optional target date (date picker).
- AC-4: After persona save, user is redirected to /home.
- AC-5: /home renders the right widget set for the user's persona.
- AC-6: Existing users (registered before this feature) do NOT lose their data — they see the picker once on next login, or have a default applied.

Include: data model change (User.persona enum, User.interview_target_date nullable), API contract, frontend component tree, test plan, migration strategy for existing users.

Do NOT write code yet.
```

### P5-S16: Backend — Persona Field + API 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-5/34-persona-picker-and-home.md.

1. Add to User model:
   - persona: Mapped[str | None] = mapped_column(String(30), nullable=True)
   - interview_target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
2. Alembic migration: alembic revision --autogenerate -m "add persona and interview_target_date to users"
3. Apply: alembic upgrade head
4. Test rollback: alembic downgrade -1 && alembic upgrade head
5. Add API endpoints in app/api/routes/users.py:
   - PATCH /api/v1/users/me/persona — body: { persona: str, interview_target_date?: date }
   - GET /api/v1/users/me — returns persona + interview_target_date in response
6. Validate persona is one of: interview_prepper, career_climber, team_lead.
7. If persona == "interview_prepper" and date is provided, validate it's in the future (max 365 days out).
8. Tests: test_set_persona_valid, test_set_persona_invalid_value, test_interview_date_validation, test_get_me_includes_persona.
9. Run: python -m pytest tests/test_users.py -v

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(users): persona field + API — closes spec #34 (backend)"
```

### P5-S17: Frontend — PersonaPicker Component + Gating 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-5/34-persona-picker-and-home.md.

1. Create src/pages/PersonaPicker.tsx — full-screen, no nav, 4 cards.
2. Each card: icon, name, one-line value prop, "Select" button.
3. Interview-Prepper card expands to show a date picker (optional, "I'll decide later" link to skip).
4. On select → call PATCH /api/v1/users/me/persona → navigate to /home.
5. Create a useRequirePersona() hook or wrap routes in a PersonaGate component:
   - On any /learn/* or /prep/* or /home route, if user.persona is null, redirect to /persona.
   - Exception: /profile is reachable so users can change persona later.
6. Add /persona route.
7. Add "Change Persona" button on Profile page that re-routes to /persona.
8. PostHog captures: persona_picker_shown, persona_selected (with persona value), interview_date_set.
9. Manual test: new user lands on PersonaPicker → cannot navigate away until selected → after selection lands on /home.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(persona): PersonaPicker + gating — closes spec #34 (UI)"
```

### P5-S18: Frontend — HomeDashboard with Persona Widgets 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-5/34-persona-picker-and-home.md.

1. Create src/pages/HomeDashboard.tsx — reads user.persona, renders the right widget set.
2. Create src/components/home/widgets/:
   - InterviewPrepperWidgets.tsx (countdown, today's mission, ATS progress, next study)
   - CareerClimberWidgets.tsx (streak, daily review CTA, radar snapshot, recent badge)
   - TeamLeadWidgets.tsx (card library, share CTA, team usage placeholder)
3. Each widget pulls data from existing endpoints — DO NOT create new APIs unless absolutely needed.
4. If a data source is missing for a widget, render a tasteful empty state with a link to the relevant flow.
5. Add /home route and make it the default redirect after login (was probably /analyze or /study before).
6. PostHog captures: home_viewed (with persona), home_widget_clicked (with widget name).
7. Manual test: switch personas via /profile → /persona → confirm /home re-renders correctly for each.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(home): persona-aware HomeDashboard — closes spec #34 (home)"
```

### P5-S19: Migration — Existing Users Get Persona Picker 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-5/34-persona-picker-and-home.md.

For users registered before persona was a thing:
1. Their User.persona will be NULL after the migration in P5-S16.
2. The PersonaGate from P5-S17 will redirect them to /persona on next login.
3. Add a one-time banner on /persona: "Welcome back! We've added personalization. Pick the option that fits you best — you can change this anytime."
4. PostHog event: existing_user_persona_set (with persona) so we can measure how the existing base distributes.
5. Do NOT auto-assign a default — make them choose. Auto-defaults skew the data and rob the user of agency.
6. Manual test: log in as a user with persona=NULL → see banner + picker → select → land on /home.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(persona): existing user migration UX — closes spec #34 (migration)"
```

---

## --- NEW SESSION --- Phase 5E: Analysis Results Page Improvements

### P5-S20: Move Job Fit Explanation Above the Fold 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

User feedback: Job Fit Explanation is the most useful section but it's buried below score, gaps, keywords. Move it up.

1. Read src/pages/AnalysisResults.tsx (now at /prep/results).
2. Reorder sections:
   1. ATS Score (small, top-left)
   2. Job Fit Explanation (HERO — large, top of page)
   3. Skill Gaps + Pro CTA / Flashcard CTA
   4. Keyword Frequency Analysis
   5. Detailed breakdown
3. Keep responsive behavior — Job Fit Explanation should be the first thing visible on mobile too.
4. PostHog capture: job_fit_explanation_viewed (with view_position: "above_fold" so we can A/B later).
5. Manual test: results page renders with Job Fit on top on desktop + mobile.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(results): move Job Fit Explanation above the fold"
```

### P5-S21: Analysis Results Education + Keyword Color Fix 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

Two issues on Analysis Results:
A. Users don't understand what they're looking at — no education layer.
B. Keyword Frequency Analysis has color coding that doesn't match the legend (mismatch reported).

1. Audit the keyword color coding:
   - Read the keyword display component.
   - List every color used and what it's supposed to mean (matched vs missing vs partial).
   - Identify the mismatch (likely a swapped variable or a className that doesn't match the legend).
   - Report findings before fixing.

2. After approval, fix the color logic and verify against the legend.

3. Education layer:
   - Add an "i" info icon next to each major section header.
   - Hover/tap → tooltip with: "What this means", "How to act on it", "Why it matters".
   - For first-time visitors, show a one-time guided tour (3-4 tooltip steps using a lib like Intro.js or homemade).
   - Persist dismissal in user.onboarding_flags.results_tour_seen.

4. PostHog: results_tour_started, results_tour_step_completed, results_tour_finished, results_info_tooltip_opened (with section name).

5. Manual test: first-time user sees tour, second visit doesn't, info tooltips work on every section.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "fix+feat(results): keyword color fix + education layer"
```

### P5-S22: Pro-Gating — Missing Skills → Flashcards 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

Currently the missing skills section in Analysis Results doesn't link anywhere. Wire it up with plan-aware behavior.

1. For each missing skill in the gap list:
   - If user.plan === "pro": show "Study these cards →" linking to /learn/categories filtered by that skill (or /learn/daily if cards already exist for that gap).
   - If user.plan === "free": show "Unlock with Pro to study these gaps" with the upgrade CTA.

2. Re-use the existing ATS-card-bridge mapping (from Phase 1 P1-S17). If a missing skill has no matching cards, show "No cards yet for this skill — request one" with a feedback hook.

3. PostHog: missing_skill_clicked (with skill name, plan), upgrade_cta_from_results (with skill name).

4. Manual test: free user sees upgrade CTAs, pro user lands on filtered cards.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(results): plan-aware flashcard linking from missing skills"
```

---

## --- NEW SESSION --- Phase 5F: Interview Prep Storage + Subscription Mgmt

### P5-S23: Spec — Interview Question Storage 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

Currently generated interview questions are not persisted — user regenerates every visit. Fix.

Create docs/specs/phase-5/35-interview-question-storage.md:

Problem: Questions are regenerated on every visit, losing the user's prep history and wasting LLM cost.

Solution: Store generated questions per (user, job_description_hash). Reuse on revisit.

Data model:
- interview_question_sets table: id, user_id, jd_hash (SHA256 of normalized JD), jd_text (full text), questions (JSON array of {question, category, difficulty, suggested_answer}), generated_at, model_used.
- Index on (user_id, jd_hash).

API:
- POST /api/v1/interview/generate — body: { job_description }. If a set exists for the hash, return it. Else generate, store, return.
- GET /api/v1/interview/sets — list user's stored sets with JD preview + date.
- GET /api/v1/interview/sets/{id} — full set.
- DELETE /api/v1/interview/sets/{id}.

Free tier limit: respect existing limit (from spec #30) — counts only fresh generations, not cache hits.

Test plan: cache hit, cache miss, free tier limit, JD normalization (whitespace, casing).

Do NOT write code yet.
```

### P5-S24: Implement — Interview Question Storage 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-5/35-interview-question-storage.md.

1. Create app/models/interview_question_set.py — InterviewQuestionSet model.
2. Alembic migration. Apply.
3. Create app/services/interview_storage_service.py:
   - hash_jd(text) — normalize + SHA256
   - get_or_generate(user_id, jd_text) — checks cache, generates if needed (uses existing interview question service + LLM router for Pro model)
   - list_sets(user_id) → [{id, jd_preview, generated_at}]
   - get_set(user_id, set_id)
   - delete_set(user_id, set_id)
4. Update existing interview generation route to delegate to this service.
5. Add new routes for list/get/delete.
6. Tests: test_cache_hit_no_generation, test_cache_miss_generates, test_jd_normalized_for_hash, test_free_tier_limit_only_counts_generations, test_user_cannot_access_others_sets.
7. Run: python -m pytest tests/test_interview_storage.py -v

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(interview): question storage + cache — closes spec #35"
```

### P5-S25: Frontend — Interview Prep History 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-5/35-interview-question-storage.md.

1. Update src/pages/InterviewPrep.tsx (now at /prep/interview):
   - Show "Your prep sets" sidebar/list with stored sets.
   - Click a set → loads it instantly (no regeneration).
   - "New prep" button → enter JD → generate (or hit cache).
2. Add delete button per set with confirm.
3. Show free-tier counter: "X generations remaining this month" with upgrade CTA at 0.
4. PostHog: interview_set_loaded_from_cache, interview_set_generated, interview_set_deleted.
5. Manual test: generate set → reload page → set still there → click → loads instantly.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(interview): prep history UI — closes spec #35 (UI)"
```

### P5-S26: Spec + Implement — Subscription Cancellation 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read .agent/skills/payments.md.

Create docs/specs/phase-5/36-subscription-cancellation.md, then implement:

Spec:
- "Cancel subscription" button on Profile page (Pro users only).
- Click → confirmation modal: "You'll keep Pro access until [period end]. Are you sure?"
- Confirm → call Stripe Subscription.modify(cancel_at_period_end=True).
- User stays Pro until period_end, then auto-downgrades to free.
- Cancellation reason picker (optional): too expensive / not using / found alternative / other.
- Win-back: 50% off for 3 months offer modal before final cancel (optional, low pri).
- Re-subscribe button if cancelled but still in grace period.

Backend:
1. POST /api/v1/billing/cancel — Stripe modify, store reason.
2. POST /api/v1/billing/reactivate — Stripe modify, cancel_at_period_end=False.
3. Webhook handler for customer.subscription.deleted — set user.plan = "free".
4. Tests for both flows.

Frontend:
5. Cancel button + modal + reason picker on Profile.
6. PostHog: cancel_initiated, cancel_completed (with reason), cancel_aborted, reactivated.

Manual test: cancel → confirm in Stripe dashboard → period_end passes → user is free.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(billing): subscription cancellation — closes spec #36"
```

---

## --- NEW SESSION --- Phase 5G: Settings Persistence + Chat with AI + Interview Date

### P5-S27: Spec + Implement — Settings Persistence Audit 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

User concern: existing registered users may lose settings when new fields are added (persona, interview_target_date, theme, etc.). Verify and harden.

PASS 1 — AUDIT (no code changes):
1. List every field on the User model and every per-user setting (theme, email prefs, notification opts, persona).
2. For each, check the migration: does it have a sensible DEFAULT? Does it backfill existing rows?
3. List every settings UI surface and verify it reads + writes the right field.
4. Report gaps.

PASS 2 — FIX (after my approval):
5. For any field missing a default: add an Alembic data migration to backfill existing users.
6. For any settings UI that doesn't persist: fix it.
7. Add an integration test: create a user → set every setting → log out → log in → assert all settings preserved.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "fix(settings): audit + harden settings persistence"
```

### P5-S28: Spec — Chat with AI During Flashcard Study 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

Create docs/specs/phase-5/37-chat-with-ai-flashcards.md:

Problem: User reads a card, doesn't understand the answer, no way to ask follow-up. They leave.

Solution: "Ask AI" button on every card during study. Opens a side panel chat scoped to that card's question + answer. LLM has the card content as context.

UX:
- Side panel slides in from right (mobile: full screen).
- Pre-filled context: "You're studying: [Q]. The answer is: [A]. Ask anything to deepen understanding."
- Chat history persisted per (user, card) so re-opening shows past chat.
- Free tier limit: N messages per day across all cards.
- Pro: unlimited.
- Uses LLM router → Pro model for quality answers (this is a high-value retention feature).

Data model:
- card_chat_messages table: id, user_id, card_id, role (user/assistant), content, created_at.
- Index on (user_id, card_id, created_at).

API:
- POST /api/v1/cards/{id}/chat — body: { message }. Returns assistant reply.
- GET /api/v1/cards/{id}/chat — returns chat history.

Test plan: send message → reply persisted, reload → history loads, free tier limit enforced.

Do NOT write code yet.
```

### P5-S29: Implement — Chat with AI Backend + Frontend 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-5/37-chat-with-ai-flashcards.md.

Backend:
1. Create CardChatMessage model + migration.
2. Create app/services/card_chat_service.py: send_message(user_id, card_id, message) → uses LLM router (Pro), persists user + assistant msgs, returns reply.
3. Routes: POST + GET /api/v1/cards/{id}/chat.
4. Free tier limit check (re-use existing free-tier counter pattern).
5. Tests.

Frontend:
6. Create src/components/study/CardChatPanel.tsx — slide-in side panel with chat UI.
7. Add "Ask AI" button to CardViewer.
8. Use useQuery for history, useMutation for send.
9. PostHog: chat_opened, chat_message_sent (with msg_count), chat_limit_hit.

Manual test: open card, ask question, get reply, close + reopen → history loads, hit free limit → upgrade CTA.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(study): chat with AI on flashcards — closes spec #37"
```

### P5-S30: Verify Interview Date Picker Lives in Persona Picker 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

The interview date picker (optional) should already be in the PersonaPicker from P5-S17 under the "Interview-Prepper" card. Verify and patch any gaps:

1. Confirm the date picker is present, optional, and validates (future date, max 365 days).
2. Confirm it's stored on User.interview_target_date.
3. Confirm /home (Interview-Prepper widgets) uses this date for the countdown.
4. If the user picked Interview-Prepper without a date, /home should prompt: "Add your interview date for a personalized countdown" with an inline date picker.
5. Add an "Update Interview Date" control on Profile.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(persona): interview date picker integration verified"
```

---

## --- NEW SESSION --- Phase 5H: Admin LLM-Driven Analytics + Content Feed

### P5-S31: Spec — Admin LLM-Driven Analytics Dashboard 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read .agent/skills/analytics.md.

Create docs/specs/phase-5/38-admin-analytics.md:

Problem: We have PostHog dashboards, but interpreting them requires manual analysis. Admins want LLM-summarized insights: "What changed this week? What should I fix? Who's churning?"

Solution: Admin-only /admin/insights page. LLM-driven summaries built on top of PostHog + DB queries.

Sections:
1. **Right metrics** — north-star metric (DAU/MAU, paying users, retention curve), week-over-week deltas, anomalies.
2. **Application performance** — error rate (Sentry), p95 latency (PostHog or Sentry), slowest endpoints.
3. **User behavior** — top funnels, drop-off points, time-to-value (sign up → first card review).
4. **Future enhancement signal** — features used most/least, search queries with no results, feedback themes.
5. **User feedback themes** — clusters NPS comments + per-card feedback into 3-5 themes per week using LLM.

Tech approach:
- Backend: app/services/insights_service.py pulls raw data from PostHog API + DB, sends to Gemini Pro for summarization.
- Caching: 1 hour TTL in Redis (insights don't need to be real-time, and LLM calls are expensive).
- Output: structured JSON (per section) → frontend renders cards.

Acceptance Criteria:
- AC-1: Admin-only route, returns 403 for non-admins.
- AC-2: Each section returns within 5s on cache hit, 30s on cache miss.
- AC-3: Insights are date-bounded (last 7 / 30 / 90 days selectable).
- AC-4: Each insight links to the underlying PostHog query/dashboard for verification.

Do NOT write code yet.
```

### P5-S32: Implement — Admin Insights Backend 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-5/38-admin-analytics.md.

1. Create app/services/insights_service.py with one method per section:
   - get_metrics_summary(period_days)
   - get_performance_summary(period_days)
   - get_behavior_summary(period_days)
   - get_enhancement_signal(period_days)
   - get_feedback_themes(period_days)
2. Each method:
   - Pulls raw data (PostHog API for events, Sentry API for errors, DB for DB-side data, card_feedback table for feedback).
   - Sends to Gemini Pro via LLM router with a structured-output prompt.
   - Caches result in Redis with key like insights:metrics:7d, TTL 3600s.
3. Create routes in app/api/routes/admin_insights.py — all gated by Depends(require_admin):
   - GET /api/v1/admin/insights/metrics?period=7
   - same shape for performance, behavior, enhancement, feedback
4. Tests: mock PostHog + Gemini, assert structured output, assert cache hit, assert 403 for non-admin.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(admin): LLM-driven insights backend — closes spec #38 (backend)"
```

### P5-S33: Implement — Admin Insights UI 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read docs/specs/phase-5/38-admin-analytics.md.

1. Create src/pages/AdminInsights.tsx at /admin/insights.
2. Period selector: 7 / 30 / 90 days.
3. 5 section cards: Metrics, Performance, Behavior, Enhancement Signals, Feedback Themes.
4. Each card: LLM summary at top, supporting numbers below, "View raw" link to PostHog.
5. Loading skeleton per card (since cache misses are slow).
6. Manual refresh button (force cache invalidation).
7. PostHog: admin_insights_viewed, admin_insights_section_expanded.
8. Manual test as admin: load page, switch periods, verify all sections render.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(admin): insights dashboard UI — closes spec #38 (UI)"
```

### P5-S34: Spec + Implement — Content Feed Flow (Admin) 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

Create docs/specs/phase-5/39-content-feed-flow.md, then implement:

Problem: Admin-driven card creation is one-at-a-time. We want a "feed" pipeline: admin pastes a list of topics or links → AI generates draft cards → admin reviews queue → publishes in batch.

Solution: /admin/content-feed page.

Backend:
1. content_feed_items table: id, source_type (topic/url/jd), source_text, status (queued/draft_ready/approved/rejected), draft_card_json, created_at, processed_at.
2. Service:
   - submit_to_feed(source_type, source_text) → queues
   - process_queue() → for each queued, calls AI card gen (re-uses Phase 3 service via LLM router → Pro), updates to draft_ready
   - approve(id) → creates real Card from draft, marks approved
   - reject(id) → marks rejected
3. Background job (Celery / Railway cron / manual trigger button) runs process_queue.
4. Admin routes for all of the above.

Frontend:
5. /admin/content-feed page with three tabs: Inbox (queued), Drafts (ready for review), History.
6. Bulk submit form: textarea for topics (one per line) or URLs.
7. Drafts tab: list of draft cards with approve/edit/reject actions.
8. PostHog: feed_item_submitted, feed_item_approved, feed_item_rejected.

Tests + manual verification.

Update SESSION-STATE.md.
Commit: git add -A && git commit -m "feat(admin): content feed flow — closes spec #39"
```

---

## --- NEW SESSION --- Phase 5 Final: Verify + Housekeeping

### P5-S35: Phase 5 Final Verification + Housekeeping 🔴 PENDING

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

Final verification + housekeeping for Phase 5:

VERIFICATION:
1. Run the full backend test suite: python -m pytest tests/ -v --tb=short
2. Run the full frontend test suite: cd hirelens-frontend && npx vitest run
3. Verify on production (or staging):
   - New user signup → PersonaPicker → /home renders for chosen persona
   - Existing user login → PersonaPicker once → /home
   - All old routes redirect to /learn/* or /prep/*
   - Resume rewrite preserves all sections
   - Cover letter has correct format
   - Generate My Experience works
   - Interview question sets persist + reload from cache
   - Cancel subscription works (test mode)
   - Chat with AI on a card works
   - Admin insights page loads for admin, 403 for non-admin
   - Geo-pricing shows INR for India IP, USD elsewhere
4. Update all Phase 5 spec statuses to Done.

HOUSEKEEPING (executes the Future TODO list at top of this file):
5. **H.2 — Roll up Phase 5 into Playbook v3**: update skillforge_playbook_v2.md → skillforge_playbook_v3.md with Phase 5 promoted to a first-class phase. Update Bootstrap Protocol to mention SESSION-STATE.md.
6. **H.3 — Archive v1 prompts**: move claude-code-prompts-all-phases.md to archive/claude-code-prompts-all-phases-v1.md.
7. **H.4 — Refresh local-setup-guide.md**: add new env vars introduced in Phase 5 (chat-with-AI rate limit constants, admin insights cache TTL, persona migration flags).
8. **H.1 — Archive transcript** (manual step for Dhamo): remove ClaudeSkillsforge_sessiontext.docx from project knowledge in claude.ai. Save a local copy in archive/ for posterity. The transcript has served its purpose — Phase 5 docs now capture all the decisions.

FINAL STATE:
9. Update SESSION-STATE.md:
   - Active Phase: maintenance / Phase 6 planning
   - Last Completed Slice: P5-S35
   - Phase 5 status: COMPLETE
   - Open Decisions: (carry forward anything Phase 6 needs to decide)
10. Tag the release: git tag v1.0-phase5-complete && git push --tags

Commit: git add -A && git commit -m "chore: phase 5 complete — UX restructure + enhancements + housekeeping 🚀" && git push
```

---

# ═══════════════════════════════════════════
# REFERENCE: Updated Session Strategy (v2.1)
# ═══════════════════════════════════════════

| Session | Slices | Phase | Focus | Status |
|---------|--------|-------|-------|--------|
| P0-Auth | S1–S4 | 0 | Auth + roles | ✅ DONE |
| P0-Deploy | S5–S8 | 0 | Deploy + CI/CD + verify | ✅ DONE |
| P1A–P1F | S1–S23 | 1 | Study engine + ATS bridge | ✅ DONE |
| P2A–P2D | S1–S11 | 2 | Gamification + Mission + email | ✅ DONE |
| P3A–P3B | S1–S7 | 3 | Admin + landing + onboarding | ✅ DONE |
| P4A | S1–S4 | 4 | Sentry + perf + domain | ✅ DONE |
| **P5-PRE** | **S0–S0b** | **5** | **Doc audit + sync** | 🔴 **DO FIRST** |
| P5A | S1–S7 | 5 | Spec backfill (DONE features) | Optional |
| P5B | S8–S11 | 5 | Verify + fix PARTIAL features | 🔴 PENDING |
| P5C | S12–S14 | 5 | Route restructure + new nav | 🔴 PENDING |
| P5D | S15–S19 | 5 | PersonaPicker + HomeDashboard | 🔴 PENDING |
| P5E | S20–S22 | 5 | Analysis Results improvements | 🔴 PENDING |
| P5F | S23–S26 | 5 | Interview storage + cancel sub | 🔴 PENDING |
| P5G | S27–S30 | 5 | Settings + chat AI + interview date | 🔴 PENDING |
| P5H | S31–S34 | 5 | Admin insights + content feed | 🔴 PENDING |
| P5-FINAL | S35 | 5 | Phase 5 verify + housekeeping (incl. transcript archive) | 🔴 PENDING |

**Phase 5 total: 36 slices across 9 sessions.**

---

# ═══════════════════════════════════════════
# REFERENCE: Recommended Execution Order
# ═══════════════════════════════════════════

If you're running v2.1 fresh, this is the order I'd suggest:

1. **P5-PRE (S0, S0b)** — doc sync. Non-negotiable.
2. **P5B (S8–S11)** — fix the broken stuff first. User-visible bugs eating trust.
3. **P5C (S12–S14)** — route restructure. Unblocks every other UX change.
4. **P5D (S15–S19)** — PersonaPicker + HomeDashboard. The big UX win.
5. **P5E (S20–S22)** — Analysis Results improvements. High-leverage conversion fixes.
6. **P5F (S23–S26)** — Interview question storage + Stripe cancel.
7. **P5G (S27–S30)** — Settings persistence audit, chat with AI, interview date.
8. **P5H (S31–S34)** — Admin insights + content feed. Lowest user impact, ship last.
9. **P5A (S1–S7)** — spec backfill. Optional, do only if you need formal coverage.
10. **P5-FINAL (S35)** — verify + housekeeping (transcript archive, Playbook v3, v1 prompts archive).

---

# ═══════════════════════════════════════════
# REFERENCE: Contingency Prompts
# ═══════════════════════════════════════════

**If Claude Code drifts or gets confused:**
```
Stop. Re-read docs/specs/phase-N/NN-feature.md. Focus only on [specific AC]. Do not touch any other files.
```

**If a test fails 3+ times:**
```
Stop. Do not attempt another fix. Print the exact error, explain your hypothesis for the root cause, and list 2-3 possible fixes. Wait for me to decide.
```

**If you need to verify DB state:**
```
Connect to the hireport database with psql and run: \dt to list tables, \d table_name to describe a specific table, \dx to list extensions. Show me the output.
```

**If you need to verify production:**
```
curl -s https://yourdomain.com/health and show me the response. Then curl one API endpoint to verify data is flowing.
```

**If a slice is taking too long (>15 min of Claude thinking):**
```
Stop. You're overcomplicating this. Break the current task into 2 smaller pieces. Tell me what those pieces are, and I'll tell you which one to do first.
```

**If you need to reset after a bad session:**
```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. List the files you changed in the last session. Run git diff --stat to show me what's modified. Run the full test suite. Tell me what's broken and what's working.
```

**If SESSION-STATE.md is out of sync with reality:**
```
Read SESSION-STATE.md. Run git log --oneline -20 and read the last 5 commit messages and any docs/specs/phase-5/ files added recently. Compare to SESSION-STATE.md. Report drift and propose updates. Do NOT modify the file until I approve.
```

---

# ═══════════════════════════════════════════
# CHANGELOG
# ═══════════════════════════════════════════

**v2.1 (April 2026)**
- Added `Read SESSION-STATE.md` to every slice's prompt header (4-file standard: AGENTS / CLAUDE / SESSION-STATE / spec).
- Added "Future / Housekeeping TODO" section near the top with 5 hygiene items including archiving the session transcript after Phase 5.
- Every slice now ends with "Update SESSION-STATE.md" so the live state stays current.
- P5-S35 (Final Verification) renamed "Verify + Housekeeping" — now executes the housekeeping TODO list (archive transcript, roll into Playbook v3, archive v1 prompts, refresh setup guide).
- Added contingency prompt for when SESSION-STATE.md drifts from reality.

**v2 (April 2026)**
- Tagged every existing phase/slice with implementation status (DONE/PARTIAL/PENDING/NEW).
- Added Implementation Status Summary table at the top.
- Added Phase 5 Status table covering 26 enhancement items.
- Added Phase 5: Enhancements + UX Restructure (36 slices, 9 sessions).
- Added P5-PRE doc audit + sync as mandatory first step.
- Added recommended execution order for Phase 5.
- Phases 0-4 prompts kept by reference — see v1 for full text. They're complete.

**v1 (April 2026)**
- Original 55 slices across Phases 0-4.
