# SESSION STATE — SkillForge

> **Purpose**: This is the live "where we are right now" pointer for Claude Code. Read at the start of every session. Update at the end.
> **Companion to**: AGENTS.md (how project works) + CLAUDE.md (how to behave) + spec file (what to build).
> **Update cadence**: End of every implementation slice. Drift will hurt — keep this current.

---

## Active Phase

**Phase 5: Enhancements + UX Restructure**

Phases 0–4 are complete. Phase 5 absorbs the ad-hoc enhancement work plus the UX restructure (PersonaPicker, /learn and /prep namespaces, persona-aware home dashboard) plus the v2.2 patch additions from the user-flow audit.

---

## Active Prompt Files

- `claude-code-prompts-all-phases-v2.md` (v2.1) — base of Phase 5
- `claude-code-prompts-all-phases-v2.2-patch.md` — additions from flow audit (5 new slices + 1 spec amendment)
- Always read both when planning Phase 5 work.

---

## Last Completed Slice

**P5-S14** — Shipped `TopNav` / `MobileNav` / `AppShell` at `src/components/layout/` and wired them into `src/App.tsx` (replacing the old `Navbar`). TopNav renders `Home · Learn · Prep · Profile` on `md:` and up with `Admin` appended iff `user.role === 'admin'`; MobileNav is a fixed bottom bar (`h-16`, `pb-[env(safe-area-inset-bottom)]`) with the same tabs + filled-icon active state. Active-state logic: `/home` exact-match, others startsWith. Chrome hidden on `/`, `/login`, `/pricing` by AppShell. New `nav_clicked` event (`{namespace, from_path, to_path}`) fires from every nav tap. All styling via design tokens — no hex literals. New tests: `tests/TopNav.test.tsx` (admin role + five active-state paths + /home exact-match = 8 cases) and `tests/MobileNav.test.tsx` (3 cases). The redirect block in `src/App.tsx` was not touched (P5-S13 domain). AGENTS.md Frontend Routes Table updated. Frontend test count 16 → 27.

**P5-S13 gap flagged:** the transitional `deprecated_route_hit` event defined in the spec (§Analytics) is not wired in the `<Navigate>` redirect nodes. Analytics catalog notes the gap but the backfill is out of scope for P5-S14.

---

## Next Slice

**P5-S15** — PersonaPicker + HomeDashboard prerequisite migration (User model adds `persona`, `interview_target_date`, **`interview_target_company`** fields). See Active Refactor Zones.

After P5-S9, continue in this order:
1. P5B (S10–S11) — cover letter, Generate My Experience
2. P5C (S12–S14) — route restructure
3. P5D (S15–S19, **S16-AMEND**, **S18b**, **S18c**) — PersonaPicker + HomeDashboard + state-aware + checklist
4. P5E (S20–S22) — Analysis Results improvements
5. P5F (S23–S26, **S26b**, **S26c**) — Interview storage + cancel sub + paywall dismissal + webhook idempotency
6. P5G (S27–S30) — Settings + chat AI + interview date
7. P5H (S31–S34) — Admin insights + content feed
8. P5-FINAL (S35) — verify + housekeeping

**Bold = added in v2.2 patch.**

---

## Known-Broken Features (DO NOT modify unless fixing)

These are user-visible bugs. Don't refactor around them — they have dedicated fix slices.

| Feature | Symptom | Fix slice |
|---------|---------|-----------|
| Geo-Pricing Visibility | Audit complete (P5-S8): A+C fixed. Remaining deferred gaps — B: no price on LoginPage; D: ip-api.com rate-limit fallback mis-prices Indian users under load; E: Free-plan shows `$0` even for INR users. | Deferred (post-P5B) |
| Stripe Webhook Idempotency | Possible — duplicate webhook delivery could double-grant Pro. Audit pending. | P5-S26c |

---

## Active Refactor Zones (avoid drive-by changes)

Currently none. As Phase 5 progresses, this list will grow:

- (P5-S13 landed): `src/App.tsx` carries the nine `/learn/*` + `/prep/*` namespaced routes and a ten-entry transitional redirect block. The redirect block is P5-S13's domain — do not edit it as part of unrelated work.
- (P5-S14 landed): `src/components/layout/TopNav.tsx`, `MobileNav.tsx`, `AppShell.tsx` are the nav source of truth. The legacy `src/components/layout/Navbar.tsx` is no longer imported by `App.tsx` but still sits on disk — delete it when we're sure no other callers exist (Phase 6 cleanup candidate).
- (After P5-S15 spec): User model gaining `persona`, `interview_target_date`, **`interview_target_company`** fields — coordinate with that migration.

---

## Recently Completed (last 5)

1. P5-S14 — `TopNav` / `MobileNav` / `AppShell` shipped and wired into `src/App.tsx` (replacing `Navbar`). Four tabs (Home/Learn/Prep/Profile) + Admin for admins. `nav_clicked` event (`{namespace, from_path, to_path}`) fires on every tap. MobileNav is a fixed bottom bar with safe-area padding. All colors via design tokens — no hex literals. Tests: `TopNav.test.tsx` + `MobileNav.test.tsx`; frontend count 16 → 27. Flagged: transitional `deprecated_route_hit` event from the nav spec is not wired in the redirect block (P5-S13 gap, backfill out of scope).
2. P5-S13 — Route restructure + internal-reference sweep: `/learn/*` and `/prep/*` namespaces live in `src/App.tsx`, 10-entry `<Navigate replace>` redirect block covers the old flat paths, post-login target now `/home`, `HomeDashboardPlaceholder` added, daily-reminder email deep-link → `/learn/daily`. Sweep proof at `docs/audit/2026-04-p5-s13-sweep-proof.txt`. Frontend tests 5 → 16 (new `App.redirects.test.tsx`); backend 174/174.
3. P5-S11 — Generate My Experience fix (max_tokens 500→2048, moved to FAST tier, empty-response 503 guard, Gemini empty-text WARNING log; +2 regression tests)
4. P5-S10 — Cover letter fix (prompt rewritten for business-letter format: headers/greeting/signature consistent)
5. P5-S9 — AI Resume Rewrite fix (removed 4k-char input truncation; full resume now reaches LLM)

---

## Open Decisions Awaiting Dhamo

| Decision | Context | Blocking? | Decide by |
|----------|---------|-----------|-----------|
| Free-tier interview question limit value | Implemented but value not validated against business model. P5-S6 will flag the current value for confirmation. | No | End of Phase 5 |
| Cancellation win-back flow (50% off 3 months) | Mentioned in P5-S26 spec as optional. | No | Before P5-S26 |
| Existing-user persona migration (auto-default vs force-pick) | Recommendation in P5-S19: force-pick. Confirm. | Yes | Before P5-S19 |
| **Daily review: counts toward free 15-card budget or not?** | If yes, Career-Climber free hits wall in 3 days. If no, daily review is unlimited for free users. Affects monetization curve. | Yes | Before P5-S22 |
| **Auto-save scan to tracker: automatic or "Save?" prompt?** | Existing-user flow implies automatic. P5-S5 spec needs this clarified. | No | Before P5-S5 |
| **Strategic path to $100M ARR**: B2B pivot, adjacent expansion, or geo-volume play? | See `STRATEGIC-OPTIONS.md`. Affects every Phase 6+ decision. | Not yet | Before Phase 6 planning |

---

## Resolved Decisions

### Decision 1 — Persona switch UX (resolved 2026-04-17)

**Resolution:** Full-page reroute to `/onboarding/persona`, not modal.

**Rationale:**
- New-user flow lands fresh; no page behind a modal worth seeing.
- Existing-user migration UX (P5-S19) fits better as a page with banner than as a modal with banner-header.
- PersonaGate becomes a clean `<Navigate to="/onboarding/persona" replace />` redirect — route-based gating is simpler to test than render-based overlay.
- Three fields on the surface (persona + `interview_target_date` + `interview_target_company` per v2.2 S16-AMEND) argue for page not modal.
- Mobile: full-screen modal ≈ full page, so the pattern matters on desktop where page wins.

**Affected slices:** P5-S15 (spec describes full-page UX), P5-S17 (PersonaGate implemented as redirect, not overlay), P5-S19 (existing-user banner sits at top of page).

### Decision 2 — Persona count (resolved 2026-04-17)

**Resolution:** Stay at 3 personas: Interview-Prepper, Career-Climber, Team Lead. No "New User" persona.

**Rationale:**
- PRD §1.3 lists 3. Playbook v2 lines 36-40, 207, 1231 consistent. v2.2 patch consistent.
- v2.1 P5-S15 prompt's "4 personas including New User" was a documentation bug — conflated the no-persona state with a persona value.
- "New User" is a state (no activity yet), not a durable intent. Handled by P5-S18b state-aware dashboard logic, not by a persona enum value.

**Affected slices:** P5-S15 spec (amended), P5-S16 (PersonaEnum has 3 values), P5-S17 (picker has 3 cards), P5-S18 (widget catalog has 3 modes).

### Decision 3 — Resolved 2026-04-17
Email deep-link coverage: App is pre-production, no legacy user traffic exists.
AC-5 reframed as internal-reference sweep (email templates, PostHog config,
hardcoded links) rather than external-facing 301 redirects. P5-S13 owns
executing the sweep.

### Decision 4 — Legacy `target_*` column overlap (resolved 2026-04-17)

**Resolution:** Rename in the P5-S16 migration. `target_company → interview_target_company` (String(255) → String(100)); `target_date → interview_target_date` (DateTime → Date). Via `op.alter_column`.

**Rationale:**
- Pre-production; row-data risk ≈ zero. `alter_column` preserves data regardless.
- Duplicate schema is tech debt "Phase 6 cleanup" will never actually reach.
- Small surface: model, migration, `/auth/me` serialiser. No legacy frontend UX reads the columns.

**Affected slices:** P5-S15 spec (amended — rename rather than keep-separate), P5-S16 (migration does rename + retype, with a pre-flight row-count diagnostic).

---

## Hard Constraints (current sprint)

These rules apply across Phase 5. Add or remove as the sprint changes.

- **Routes**: All new routes go under `/learn/*` or `/prep/*`. **No new flat routes.** (Reaffirmed at P5-S14 — `TopNav` / `MobileNav` only surface `/home`, `/learn`, `/prep`, `/profile`, `/admin`; any new flat path would have no nav home.)
- **Env vars**: Any new env var requires `.env.example` update in the same commit.
- **LLM calls**: All LLM calls go through the LLM router (`app/core/llm_router.py`, entry point `generate_for_task(task=..., ...)`). Don't bypass it. Pro for reasoning (rewrite, cover letter, gap analysis, chat-with-AI, admin insights). Flash for fast tasks (extraction, classification, simple Q&A).
- **PostHog events**: Every new user-facing feature fires at least one event. snake_case naming.
- **Backward compatibility**: Phase 5 cannot break existing user data. Migrations need defaults that backfill existing rows.
- **Persona gating**: Once PersonaPicker is shipped (P5-S17), all `/learn/*` and `/prep/*` and `/home` routes require `user.persona` to be set. Exception: `/profile`.
- **Stripe**: All webhook handlers must be idempotent (P5-S26c). No new webhook events without idempotency check.
- **Frontend test coverage**: Every new page added in Phase 5 (`HomeDashboard`, `PersonaPicker` page, `CardChatPanel`, `AdminInsights`, etc.) must ship with at least one Vitest test. Current frontend test count is **5** (only `PaywallModal`) — this number must grow with every Phase 5 UI slice.

---

## Deferred Hygiene Items

- `deprecated_route_hit` PostHog event not wired in the 10 `<Navigate>` redirect nodes in `src/App.tsx`. Defined in spec #12 §Analytics but deferred from P5-S13. Blocks Phase 6 redirect-block cleanup (no signal to confirm when old paths stop receiving hits).

---

## Tech Debt (living log — tackle during P6 cleanup unless it escalates)

| Item | Detail |
|---|---|
| Legacy LLM provider factory | `app/services/llm/factory.py` + `claude_provider.py` + `gemini_provider.py` run parallel to the real router at `app/core/llm_router.py`. Not currently breaking. Do not extend the legacy factory — route all new LLM calls through `generate_for_task()`. Consolidate in Phase 6 cleanup. Surfaced by the 2026-04-17 audit. |
| Registration IP-blocking is DB-based, not Redis | `app/api/v1/routes/auth.py` inlines the limit check against the `registration_logs` table (30-day window query). The original playbook skill described a Redis counter. Both approaches work. Kept for P5-S4 backfill; no behavioural change planned. |
| Email-preferences API path mismatch | Frontend `hirelens-frontend/src/services/api.ts:314,321` calls `/api/v1/email-preferences`, but the backend router is mounted at `/api/v1/email-prefs` (`app/main.py`, confirmed in `AGENTS.md:187`). The endpoints currently 404 in production. Surfaced by the 2026-04-17 P5-S11 trace. Fix in a future slice — pick one canonical path (recommend the longer `/email-preferences` to match the spec at `docs/specs/phase-2/16-email-preferences.md`) and update both ends together. |

---

## Test Suite Status

- **Backend**: All tests passing (last run: end of Phase 4)
- **Frontend**: All tests passing (last run: end of Phase 4)
- **Note**: Run full suites at the start of P5-S0 to establish a baseline before Phase 5 changes begin.

---

## Project File Inventory (canonical references)

### In repo (Claude Code reads these)

| File | Purpose |
|------|---------|
| `AGENTS.md` | How this project works (stack, conventions, deploy) |
| `CLAUDE.md` | How Claude Code should behave (rules, 3-strike, test gates) |
| `SESSION-STATE.md` | THIS FILE — live state pointer |
| `STRATEGIC-OPTIONS.md` | $100M ARR strategic options analysis. Read before Phase 6 planning. |
| `docs/prd.md` | Product requirements |
| `docs/specs/phase-N/NN-feature.md` | Per-feature specs |

### In Claude Project knowledge (Claude in chat reads these)

| File | Purpose |
|------|---------|
| `skillforge_playbook_v2.md` | Master phased plan (v3 due after P5-S35) |
| `claude-code-prompts-all-phases-v2.md` | v2.1 — slice-by-slice prompts (active) |
| `claude-code-prompts-all-phases-v2.2-patch.md` | v2.2 patch — flow-audit additions |
| `local-setup-guide.md` | Local dev setup (refresh due at P5-S35) |
| `ClaudeSkillsforge_sessiontext.docx` | Conversation transcript — **archive after Phase 5** per H.1 |

---

## Update Protocol

At the end of every slice:
1. Move the just-completed slice into "Recently Completed" (top of list, drop oldest).
2. Update "Last Completed Slice" and "Next Slice".
3. If a feature was fixed: remove from "Known-Broken Features".
4. If a refactor zone is now stable: remove from "Active Refactor Zones".
5. If a new constraint or decision emerged: add to the right section.
6. Commit SESSION-STATE.md alongside the slice's other files.

If you ever feel SESSION-STATE.md is out of sync with reality, run the contingency prompt:
> *"Read SESSION-STATE.md. Run git log --oneline -20 and read the last 5 commit messages and any docs/specs/phase-5/ files added recently. Compare to SESSION-STATE.md. Report drift and propose updates. Do NOT modify the file until I approve."*

---

*Last hand-edit: 2026-04-17 by Dhamo (added v2.2 patch references + flow audit decisions + STRATEGIC-OPTIONS.md reference)*
