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

**P5-S8** — Geo-pricing coverage gaps A+C closed. Pricing page Pro CTA now calls Stripe with geo-aware currency (was local-state "demo mode"); backend `/payments/checkout` gained an IP-based currency fallback when the client omits it. Backend 169/169 green (+2 new tests), frontend 5/5 green. Gaps B (no price on LoginPage), D (ip-api.com rate-limit fallback), E (Free-plan `$0` symbol consistency) deferred — not blocking.

---

## Next Slice

**P5-S9** — Fix AI Resume Rewrite (first known-broken feature); see `docs/specs/phase-3/20c-resume-cover-letter-fix.md` placeholder + `.agent/skills/ats-scanner.md`.

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
| AI Resume Rewrite | Drops sections from original (work history, education) — produces summary instead of full rewrite | P5-S9 |
| Cover Letter Generation | Format inconsistent — wrong headers, missing greeting/signature blocks | P5-S10 |
| Generate My Experience (Profile) | Button doesn't work — silent failure | P5-S11 |
| Geo-Pricing Visibility | Audit complete (P5-S8): A+C fixed. Remaining deferred gaps — B: no price on LoginPage; D: ip-api.com rate-limit fallback mis-prices Indian users under load; E: Free-plan shows `$0` even for INR users. | Deferred (post-P5B) |
| Stripe Webhook Idempotency | Possible — duplicate webhook delivery could double-grant Pro. Audit pending. | P5-S26c |

---

## Active Refactor Zones (avoid drive-by changes)

Currently none. As Phase 5 progresses, this list will grow:

- (After P5-S12 spec): Routes about to change — avoid drive-by edits to `src/App.tsx` until P5-S14 lands.
- (After P5-S15 spec): User model gaining `persona`, `interview_target_date`, **`interview_target_company`** fields — coordinate with that migration.

---

## Recently Completed (last 5)

1. P5-S8 — Geo-pricing gaps A+C closed (Pricing page now Stripe-wired, backend checkout has IP fallback; gaps B/D/E deferred)
2. P5-S0b — applied 10 doc-sync fixes from audit (path corrections, spec dedup, 9 placeholder specs, Tech Debt log)
3. P5-S0 — 3-way doc sync audit (backend 167/167 green, frontend 5/5 green; 6 duplicate-number pairs + 9 missing specs surfaced for P5-S0b)
4. P4-S4 — Custom domain + SSL + final Phase 4 verification
5. P4-S3 — Rate limiting + performance audit

---

## Open Decisions Awaiting Dhamo

| Decision | Context | Blocking? | Decide by |
|----------|---------|-----------|-----------|
| Free-tier interview question limit value | Implemented but value not validated against business model. P5-S6 will flag the current value for confirmation. | No | End of Phase 5 |
| Cancellation win-back flow (50% off 3 months) | Mentioned in P5-S26 spec as optional. | No | Before P5-S26 |
| Existing-user persona migration (auto-default vs force-pick) | Recommendation in P5-S19: force-pick. Confirm. | Yes | Before P5-S19 |
| **Persona switch UX: modal or full-page reroute?** | Existing-user flow shows modal. P5-S17 currently says reroute. Modal is lighter; reroute is consistent. | Yes | Before P5-S17 |
| **Daily review: counts toward free 15-card budget or not?** | If yes, Career-Climber free hits wall in 3 days. If no, daily review is unlimited for free users. Affects monetization curve. | Yes | Before P5-S22 |
| **Auto-save scan to tracker: automatic or "Save?" prompt?** | Existing-user flow implies automatic. P5-S5 spec needs this clarified. | No | Before P5-S5 |
| **Email deep-link redirects: do P5-S13 redirects cover Phase 2 daily-email URLs?** | Old emails point at /study/daily etc. Need 301s. | Yes | Before P5-S13 |
| **Strategic path to $100M ARR**: B2B pivot, adjacent expansion, or geo-volume play? | See `STRATEGIC-OPTIONS.md`. Affects every Phase 6+ decision. | Not yet | Before Phase 6 planning |

---

## Hard Constraints (current sprint)

These rules apply across Phase 5. Add or remove as the sprint changes.

- **Routes**: All new routes go under `/learn/*` or `/prep/*`. No new flat routes.
- **Env vars**: Any new env var requires `.env.example` update in the same commit.
- **LLM calls**: All LLM calls go through the LLM router (`app/core/llm_router.py`, entry point `generate_for_task(task=..., ...)`). Don't bypass it. Pro for reasoning (rewrite, cover letter, gap analysis, chat-with-AI, admin insights). Flash for fast tasks (extraction, classification, simple Q&A).
- **PostHog events**: Every new user-facing feature fires at least one event. snake_case naming.
- **Backward compatibility**: Phase 5 cannot break existing user data. Migrations need defaults that backfill existing rows.
- **Persona gating**: Once PersonaPicker is shipped (P5-S17), all `/learn/*` and `/prep/*` and `/home` routes require `user.persona` to be set. Exception: `/profile`.
- **Stripe**: All webhook handlers must be idempotent (P5-S26c). No new webhook events without idempotency check.
- **Frontend test coverage**: Every new page added in Phase 5 (`HomeDashboard`, `PersonaPicker` page, `CardChatPanel`, `AdminInsights`, etc.) must ship with at least one Vitest test. Current frontend test count is **5** (only `PaywallModal`) — this number must grow with every Phase 5 UI slice.

---

## Tech Debt (living log — tackle during P6 cleanup unless it escalates)

| Item | Detail |
|---|---|
| Legacy LLM provider factory | `app/services/llm/factory.py` + `claude_provider.py` + `gemini_provider.py` run parallel to the real router at `app/core/llm_router.py`. Not currently breaking. Do not extend the legacy factory — route all new LLM calls through `generate_for_task()`. Consolidate in Phase 6 cleanup. Surfaced by the 2026-04-17 audit. |
| Registration IP-blocking is DB-based, not Redis | `app/api/v1/routes/auth.py` inlines the limit check against the `registration_logs` table (30-day window query). The original playbook skill described a Redis counter. Both approaches work. Kept for P5-S4 backfill; no behavioural change planned. |

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
