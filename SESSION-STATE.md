# SESSION-STATE.md

> **Purpose**: This file is the persistent memory between Claude Code sessions.
> Update it at the END of every session before committing.
> Read it at the START of every session.
>
> **Claude Code start-of-session ritual**:
> `Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.`

---

## Current Status

**Last updated**: 2026-04-16
**Phase**: 0 → 1 (Phase 0 complete, Phase 1 starting)
**Current session**: P0-S2 close-out
**Last completed slice**: P0-S2 — CI/CD pipeline ✅ DONE (GH Actions run 24544573466: 158 backend passed, 4 integration deselected, 5 frontend passed, migration rollback green)
**Next slice to run**: P1-S1 — Task 1.1: Card Data Model + JSX Extraction (spec `docs/specs/phase-1/03-card-extraction.md`)

---

## Phase Completion Tracker

| Phase | Status | Completed date | Notes |
|-------|--------|---------------|-------|
| Phase 0: Foundation | ✅ Complete | 2026-04-16 | PG migration, auth unification, skeleton deploy, CI/CD all green |
| Phase 1: Study Engine | 🔄 Starting | — | Begin with Task 1.1 (card extraction verification on new PG base) |
| Phase 2: Retention | ⬜ Not started | — | |
| Phase 3: Content/Marketing | ⬜ Not started | — | |
| Phase 4: Hardening | ⬜ Not started | — | |

**Enhancement status** (post-playbook features):

| Enhancement | Status | Notes |
|-------------|--------|-------|
| ENH-1: LLM router | ⬜ | Build in P1-S4 alongside embeddings |
| ENH-2: Geo pricing | ⬜ | Build in P1-S22 alongside Stripe |
| ENH-3: IP blocking | ⬜ | Build in P1-S19 |
| ENH-4: Card soft-delete | ⬜ | Build in P1-S2 (add deleted_at to Card model) |
| ENH-5: Design system | ⬜ | Build in P3-S3 |
| ENH-6: Free tier interview limits | ⬜ | Build in P1-S19 |
| ENH-7: Tracker auto-populate | ⬜ | Build in P1-S20 |
| ENH-8: Resume/cover letter fix | ⬜ | Build in P3-S7 |

---

## What Was Built This Session

*(Update after every session — most recent first)*

### Session: P0-S2 — CI/CD Pipeline Close-out ✅ (2026-04-16)
- GitHub Actions workflow landed and stabilised across 8 commits (996f478 → 2c1d362).
- Three jobs green on run **24544573466**:
  - `backend-tests` (Python 3.13): **158 passed, 4 deselected (integration), 0 failed**
  - `frontend-tests` (Node 20): **5 passed**
  - `migration-rollback` (Python 3.13): **success**
- Fixed along the way:
  - `fsrs` missing from `requirements.txt` (e9d38d6)
  - duplicate `mission` table creates in migration `c9863b51075d` (14fc8f3)
  - seed cards + synthetic embeddings step wired in before backend tests (11fe035)
  - migrations applied before seed to fix ordering (87e02dd)
  - card-extraction tests marked `@pytest.mark.integration` and deselected in CI (c11a4c3)
  - dropped `--cov=app` flag from pytest invocation — pytest-cov wasn't installed (2c1d362)
- Spec `docs/specs/phase-0/02b-cicd-pipeline.md` closed.
- **Phase 0 complete.**

### Session: PostgreSQL Migration (Phase 0, Task 0.1–0.3) ✅
- Migrated SQLAlchemy from SQLite → PostgreSQL
- Created Alembic migrations for all existing tables
- 30 tests green after migration
- Committed: `feat(db): migrate to PostgreSQL + pgvector`

---

## Known Issues / Blockers

*(List anything that broke, was skipped, or needs attention)*

- **Integration tests (4) are deselected in CI** — they require live LLM API keys and external services. Must be run manually in local dev before changes to card extraction code. Marker: `@pytest.mark.integration`.
- **pytest-cov not installed.** If we want `pytest --cov=app` in CI, pytest-cov must be added to `requirements-dev.txt` first. Currently NOT installed. Decision: skip coverage in CI for now — adds noise without driving behavior. Revisit if/when coverage targets become a CI gate.

---

## Decisions Made

*(Record any architectural or implementation decisions so Claude Code doesn't re-litigate them)*

| Decision | Rationale | Date |
|----------|-----------|------|
| py-fsrs 4.x (not 3.x) | API changed significantly in v4 | — |
| No Docker for local dev | Use Homebrew PostgreSQL + Redis | — |
| Soft-delete cards via `deleted_at` | Never hard-delete — preserve data integrity | — |
| LLM fallback: Gemini if provider key not set | Gemini is always configured; other providers optional | — |
| Integration tests deselected in CI via `-m "not integration"` | They need live LLM keys; running them in CI would be flaky and leak spend. Run locally before merging extractor changes. | 2026-04-16 |
| Skip coverage in CI for now | pytest-cov isn't installed; adding it adds CI noise without driving behavior. Revisit if/when coverage targets become a CI gate. | 2026-04-16 |

---

## Environment Notes

*(Record anything specific to your local setup)*

- Project root: `/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai`
- Backend: `cd hirelens-backend && source venv/bin/activate`
- Frontend: `cd hirelens-frontend`
- DB: `psql -d hireport`
- Backend port: 8000
- Frontend port: 5199
- Domain: theskillsforge.dev
- Production backend: (set when Railway URL is known)
- Production frontend: (set when Vercel URL is known)
- CI: GitHub Actions, workflow `.github/workflows/ci.yml`, three jobs (backend-tests, frontend-tests, migration-rollback)

---

## Start-of-Next-Session Prompt

Copy this exact prompt to start the next Claude Code session:

```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.

Summarize:
1. What phase and slice are we on?
2. Any known issues from last session?
3. Run: git log --oneline -5

Then continue with: P1-S1 (Task 1.1 — Card Data Model + JSX Extraction)

Full prompt:
Read AGENTS.md. Read docs/specs/phase-1/03-card-extraction.md and the `.agent/skills/card-extraction.md` skill. CI now seeds cards + synthetic embeddings; the real extractor pipeline needs verification against the new PostgreSQL base. Confirm: (a) `python scripts/extract_cards.py` is idempotent and inserts exactly 177 rows, (b) every card has a non-null `embedding`, (c) every card has a valid `category_id`. Do NOT run the real Gemini embedding step in CI (cost + keys) — integration tests remain deselected. Report what passes, what's stale, and propose the smallest next slice. Stop before writing code so I can review.
```

---

## How to Update This File

At the **end of every session**, update:
1. `Last updated` date
2. `Last completed slice`
3. `Next slice to run`
4. Add a new entry under "What Was Built This Session"
5. Add any issues or decisions
6. Update the "Start-of-Next-Session Prompt" with the actual next prompt

Then commit:
```bash
git add SESSION-STATE.md
git commit -m "chore: update session state — completed P0-SX"
git push
```

---

*This file is tracked in git so every session starts with full context.*
