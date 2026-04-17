# SESSION STATE — SkillForge

> **Purpose**: This is the live "where we are right now" pointer for Claude Code. Read at the start of every session. Update at the end.
> **Companion to**: AGENTS.md (how project works) + CLAUDE.md (how to behave) + spec file (what to build).
> **Update cadence**: End of every implementation slice. Drift will hurt — keep this current.

---

## Active Phase

**Phase 5: Enhancements + UX Restructure**

Phases 0–4 are complete. We're now in Phase 5 which absorbs the ad-hoc enhancement work (multi-model router, geo-pricing, anti-abuse, branding, landing page) plus the UX restructure (PersonaPicker, /learn and /prep namespaces, persona-aware home dashboard).

---

## Last Completed Slice

**P5-S9** — AI Resume Rewrite fix. Removed 4k-char input truncation in `gpt_service.py` + `ai_service.py` (raised to 40k), raised `max_tokens` to 8000, added `resume_rewrite_generated` PostHog event, added regression test `tests/services/test_resume_rewrite.py`. Spec: `docs/specs/phase-5/09-resume-rewrite-fix.md`.

---

## Next Slice

**P5-S10** — Cover Letter Generation format fix. Broken today: wrong headers, missing greeting/signature blocks. Start with a diagnosis pass (mirror P5-S9 approach).

After P5-S10, proceed in this order:
1. P5B remainder (S11) — Generate My Experience fix
2. P5C (S12–S14) — route restructure
3. P5D (S15–S19) — PersonaPicker + HomeDashboard
4. Continue per the execution order in claude-code-prompts-all-phases-v2.md

---

## Known-Broken Features (DO NOT modify unless fixing)

These are user-visible bugs. Don't refactor around them — they have dedicated fix slices in Phase 5B.

| Feature | Symptom | Fix slice |
|---------|---------|-----------|
| Cover Letter Generation | Format inconsistent — wrong headers, missing greeting/signature blocks | P5-S10 |
| Generate My Experience (Profile) | Button doesn't work — silent failure | P5-S11 |

---

## Active Refactor Zones (avoid drive-by changes)

Currently none. As Phase 5 progresses, this list will grow:

- (After P5-S12 spec): Routes about to change — avoid drive-by edits to `src/App.tsx` until P5-S14 lands.
- (After P5-S15 spec): User model gaining `persona` and `interview_target_date` fields — coordinate with that migration.

---

## Recently Completed (last 5)

1. P5-S9 — AI Resume Rewrite fix (removed 4k-char input truncation, raised max_tokens, added PostHog event + regression test)
2. P5-S8 — Geo-pricing visibility + Stripe checkout wiring on pricing page + server-side currency fallback
3. P4-S4 — Custom domain + SSL + final Phase 4 verification
4. P4-S3 — Rate limiting + performance audit
5. P4-S2 — PostHog dashboards

---

## Open Decisions Awaiting Dhamo

| Decision | Context | Blocking? |
|----------|---------|-----------|
| Free-tier interview question limit value | Implemented but value not validated against business model. P5-S6 will flag the current value for confirmation. | No, but should resolve before Phase 5 ends |
| Cancellation win-back flow (50% off 3 months) | Mentioned in P5-S26 spec as optional. Decide before that slice. | No |
| Existing-user persona migration (auto-default vs force-pick) | Recommendation in P5-S19: force-pick. Dhamo to confirm. | Yes, before P5-S19 |

---

## Hard Constraints (current sprint)

These rules apply across Phase 5. Add or remove as the sprint changes.

- **Routes**: All new routes go under `/learn/*` or `/prep/*`. No new flat routes.
- **Env vars**: Any new env var requires `.env.example` update in the same commit.
- **LLM calls**: All LLM calls go through the LLM router (`app/services/llm_router.py`). Don't bypass it. Pro for reasoning (rewrite, cover letter, gap analysis, chat-with-AI, admin insights). Flash for fast tasks (extraction, classification, simple Q&A).
- **PostHog events**: Every new user-facing feature fires at least one event. snake_case naming.
- **Backward compatibility**: Phase 5 cannot break existing user data. Migrations need defaults that backfill existing rows.
- **Persona gating**: Once PersonaPicker is shipped (P5-S17), all `/learn/*` and `/prep/*` and `/home` routes require `user.persona` to be set. Exception: `/profile`.

---

## Test Suite Status

- **Backend**: All tests passing (last run: end of Phase 4)
- **Frontend**: All tests passing (last run: end of Phase 4)
- **Note**: Run full suites at the start of P5-S0 to establish a baseline before Phase 5 changes begin.

---

## Project File Inventory (canonical references)

| File | Purpose |
|------|---------|
| `AGENTS.md` | How this project works (stack, conventions, deploy) |
| `CLAUDE.md` | How Claude Code should behave (rules, 3-strike, test gates) |
| `SESSION-STATE.md` | THIS FILE — live state pointer |
| `docs/prd.md` | Product requirements |
| `docs/specs/phase-N/NN-feature.md` | Per-feature specs |
| `skillforge_playbook_v2.md` | Master phased plan (v3 due after P5-S35) |
| `claude-code-prompts-all-phases-v2.md` | Slice-by-slice prompts (THIS is the active version, v1 will move to archive at P5-S35) |
| `local-setup-guide.md` | Local dev setup (refresh due at P5-S35) |
| `ClaudeSkillsforge_sessiontext.docx` | Conversation transcript — **archive after Phase 5** per H.1 housekeeping item |

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

*Last hand-edit: 2026-04-17 — P5-S9 closed; next up P5-S10*
