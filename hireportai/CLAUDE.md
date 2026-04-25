# SkillForge (HirePort AI) — Claude Code Guide

## Quick Reference
- Backend: `cd hirelens-backend && source venv/bin/activate`
- Frontend: `cd hirelens-frontend`
- Tests (BE, all): `python -m pytest tests/ -v --tb=short`
- Tests (BE, CI subset): `python -m pytest tests/ -v --tb=short -m "not integration"`
- Tests (BE, integration only): `python -m pytest tests/ -v -m integration` *(needs live LLM keys)*
- Tests (FE): `npx vitest run`
- DB migrate: `alembic upgrade head`
- Start BE: `uvicorn app.main:app --reload --port 8000`
- Start FE: `npm run dev -- --port 5199`

## MUST-READ Before Any Task
1. Read `AGENTS.md` for project conventions
2. Read `SESSION-STATE.md` for current state (HEAD, test counts, active slice, drift ledger)
3. Read the relevant spec in `docs/specs/` if the prompt cites one
4. Read the relevant skill file in `.agent/skills/` (see Step 0 SOP below)

## Standing Operating Procedure (Step 0 — Run on EVERY prompt)

These steps apply to every prompt regardless of slice weight (heavy feature,
medium amendment, or light bookkeeping). Chat-Claude should NOT restate them
in prompt bodies — Claude Code is expected to run them from this SOP.

**SOP-1 HEAD confirmation.** Confirm HEAD matches the SHA the prompt
expects. Mismatch → STOP and report; do not proceed.

**SOP-2 Working tree check.** Confirm working tree is clean except known
pre-existing dirty files (track these in `SESSION-STATE.md`). Anything
unexpected → STOP and report.

**SOP-3 Test baselines.** Capture BE and FE test counts. Report actuals
against expected. Mismatch on read-only/docs slices = report and continue.
Mismatch on implementation slices = STOP unless the prompt explicitly says
continue.

**SOP-4 Skill inventory.** List `.agent/skills/` on disk. Pick which skills
apply to the current slice based on actual work. Read those skills. If no
skill clearly applies, note as a skill-inventory gap in your output. This
step is NOT exempted by slice weight — bookkeeping and docs slices run it
too.

**SOP-5 Spec reads.** Read every spec the prompt cites by number. If the
prompt cites a spec without giving the file path, find it via
`ls docs/specs/phase-*/ | grep ^NN-`. Spec citation without a spec read is
grounds to STOP.

**SOP-6 BACKLOG ID verification.** Verify every BACKLOG ID the prompt names
actually exists. New IDs the prompt says to create must NOT already exist.
Either mismatch → STOP and report; do not overwrite or invent rows.

**SOP-7 Starter-message verification.** If the session was opened with a
starter message containing SHAs, test counts, BACKLOG IDs, or state
claims, verify each claim against disk at Step 0 before acting on it.
Starter messages are notes, not gospel — they can drift from reality
between the time they were written and the time the session runs.

**SOP-8 Concurrent-session guard.** Run `git log --oneline -20` and
`git status`. Surface BACKLOG status of any rows the slice plans to
touch (the target row, any rows the prompt cites, any rows the spec
body cross-refs). If any cited row has flipped status, or if any
commit since the prompt was drafted touches files in the slice's
planned scope, STOP and report — concurrent sessions may have shipped
since prompt draft.

## During Work

**R1 Test first**: Write tests before implementation.

**R2 One thing at a time**: Each commit = one feature slice. If a prompt
has multiple steps, each step gets its own commit. Don't bundle.

**R3 Never skip auth**: All new routes need `Depends(get_current_user)`
unless the prompt explicitly says otherwise with a tracked rationale.

**R4 FSRS is server-side only**: Never put scheduling logic in frontend.

**R5 Pydantic for everything**: All API I/O uses Pydantic schemas.

**R6 Alembic for all schema changes**: Never use `CREATE TABLE` directly.

**R7 No console.log in production**: Use proper logging.

**R8 Track everything**: Every user-facing feature fires a PostHog event.

**R9 Deploy is automatic**: Push to main = production deploy. Never do
manual deploys.

**R10 🚨 AI Loop Breaker (3-Strike Rule)**: If a test fails 3 times in a
row, **STOP IMMEDIATELY**. Print the exact error, explain your hypothesis,
list 2–3 possible fixes, and wait for human intervention.

**R11 LLM calls go through the router**: Use
`generate_for_task(task=..., ...)` from `app/core/llm_router.py` for every
LLM call. Never call `get_llm_provider()` directly and never import a
provider SDK from service code. See `.agent/skills/llm-strategy.md`.

**R12 Style with design tokens**: Every color / spacing / shadow in
frontend code must come from the design tokens
(`src/styles/design-tokens.ts`) via Tailwind utilities like `bg-bg-surface`,
`text-text-primary`, `border-border-accent`. **Never hardcode a hex value.**
See `.agent/skills/design-system.md`.

**R13 Integration tests are marker-gated**: Tests that require live LLM
API keys or external services must be decorated with
`@pytest.mark.integration`. CI runs `-m "not integration"` so these are
deselected automatically. Run them locally before merging changes that
touch extraction, embeddings, or LLM services. Coverage (`pytest-cov`) is
deliberately NOT installed — do not add `--cov` flags without updating
`requirements-dev.txt` and getting sign-off.

**R14 No new feature without a spec** — even small ones. Every new feature
gets a spec at `docs/specs/phase-N/NN-name.md` **before** code is written,
following the template in the playbook §3.2. Exceptions: (a) retrofits /
backfills, (b) pure bug fixes with no design surface, (c) explicit user
override. Default = spec first.

**R15 Backlog-first**: Every implementation prompt must reference the
`BACKLOG.md` item ID(s) it closes (e.g., `closes B-005, E-002`). If no
item exists, create one in `BACKLOG.md` first, then proceed. Status
updates (🔴 → 🟡 → ✅ → 🟦) are the only `BACKLOG.md` edits Claude Code
may make autonomously — priority, scope, and new rows require Dhamo
unless the prompt explicitly authorizes row creation.

**R15 closure rule (sharpened)**: Before any commit that's supposed to
close a BACKLOG ID, list every ID referenced in the slice and confirm
each is flipped 🔴→✅ with a close-line referencing the implementation
commit SHA. Pre-amend SHAs are acceptable (findable via `git log --all`).
If unsure, STOP and ask. Closure happens in the implementation commit,
not a separate slice.

**R16 Audit-scoped step 1**: Every implementation prompt's step 1 must be
an audit calibrated to the blast radius of the change. Minimum scope by
change type:
- Backend model change → audit callers + migrations + dependent services
- Frontend type change → audit the **live component graph** (which
  pages/components consume the type), not just declarations
- Route change → audit navigation graph + redirects + email deep links
- Service change → audit dependents + tests + LLM task names if
  `llm_router` is involved

Reference `CODE-REALITY.md` for the live state. If `CODE-REALITY.md` is
older than the current HEAD, regenerate it before drafting the audit.

**R17 Live BACKLOG ID check before filing new rows**: Before drafting a
commit message that references a new `B-###` or filing a new BACKLOG
row, run:

```
grep -E "^\| B-0[0-9]+" BACKLOG.md | tail -3
```

Use the next ID after the highest one returned. This check applies even
when a prompt names a specific `B-###` — chat-Claude's pre-allocated IDs
may be stale by the time the slice runs. Watermark grep is non-optional,
not a fallback. Concurrent sessions can claim IDs between when chat
drafts and when CC executes. Reference: B-037 ID-collision incident.

**R18 Pre-commit BACKLOG verification**: Before EVERY commit on a slice
that touches `BACKLOG.md`:

1. List every BACKLOG ID referenced in this slice.
2. For each closed ID: confirm 🔴→✅ flip + close-line with commit SHA
   in `BACKLOG.md`.
3. For each filed-only ID: confirm row exists with status 🔴 and any
   gating notes.

If any ID can't be confirmed, STOP and ask. R18 complements R15: R15
covers closure semantics, R18 is the multi-bucket pre-commit gate
covering both closed and filed-only IDs. Non-optional.

## Commit Hygiene

**C1 Never `git add -A`** from above `hireportai/`. Always
`git add <specific paths>`.

**C2 Pre-existing dirty files** (mode changes, dotfiles, orphan `.DS_Store`)
get unstaged — never bundle into a feat/fix commit. Report them in your
output.

**C3 Single concern per commit**: Do not mix unrelated changes. If you
discover a pre-existing bug or drift while working on a slice, log it in
`SESSION-STATE.md` drift ledger and file a BACKLOG row if appropriate;
don't silently fix it in the current commit.

**C4 Commit message format**: `type(scope): description`. When closing a
BACKLOG ID, include it in the message: e.g.
`fix(rewrite): preserve sections — closes B-001`.

**C5 No `git add -A` from above `hireportai/`**: The git root is
`SkillForge/`, parent of `hireportai/`. `git add -A` from that level
will sweep in `archive/`, sibling project files, and unrelated work.
Always `cd hireportai/` first OR stage explicit paths. When a prompt
template says `git add -A`, override it with explicit paths. The
template language is itself a footgun — pre-existing dirty files in
`SkillForge/` (above `hireportai/`) will bundle. Reference: B-034
bloated-commit incident. Sharpens C1; C1/C2/C3 override applies.

## Review Layer

**CODEX review**: All commits in every slice are reviewed by CODEX
(external review tool) after commit. Write code, commit messages, and
spec/doc edits with that in mind — clarity over cleverness, no silent
compromises. Chat-Claude no longer needs to restate this in every prompt
body; it applies always.

## R3 Push-back Rule

If anything genuinely surprises you OR the prompt contradicts on-disk
reality, STOP and ask. Don't silently reconcile. Minor judgment calls
inside a slice — make the call, log it in your final report.

Examples of "genuine surprise" that warrant STOP:
- Prompt names a BACKLOG ID that doesn't exist on disk
- Prompt asks you to create a row that already exists
- HEAD doesn't match what the prompt expects
- Test counts mismatch on an implementation slice
- Working tree has unexpected dirty files suggesting mid-flight work
- Spec the prompt cites conflicts with the prompt's own instructions
- Slice would require creating a new BACKLOG row and prompt didn't
  authorize it

## Final Report (Every Slice)

Your final output at the end of a slice MUST include, in one scannable block:
- Every commit SHA in order
- Test counts before / after (BE and FE)
- Skills loaded (from SOP-4) and any skill-inventory gaps
- Spec citations confirmed read (from SOP-5)
- Any judgment calls made in flight (SOP violations, scope additions,
  workarounds) with a one-sentence rationale each
- Any new drift flags logged in `SESSION-STATE.md`
- Any BACKLOG IDs touched (closed or newly created)

## Things That Are NEVER Okay

**N1** Naming a BACKLOG ID in a commit message or spec citation that
doesn't exist on disk. Verify at SOP-6.

**N1-SUPPLEMENT — Pre-flight existence verification**

Before Step 1 of any slice, for every skill and spec file cited
in the prompt:

1. Verify the file exists on disk. If the prompt names it by exact
   path, test with `ls <path>`. If the prompt names it by slug
   ("llm-strategy.md"), find it with `ls .agent/skills/` and
   confirm the slug is in the list.

2. For each existing skill file, verify it has a `description:`
   frontmatter field. Skills without it may be silently skipped by
   discovery tooling.

3. If ANY cited file is missing or malformed, STOP before Step 1
   and report:
   - Which file is missing
   - Whether the absence looks intentional (new work) or
     accidental (drift)
   - A one-line proposal: "create as part of this slice" vs
     "needs its own spec-author/skill-author slice first"

Never create a stub skill or spec mid-slice to unblock. Either
the slice's scope expands (with user approval) to include creating
it, or the slice stops until a dedicated slice authors it.

**N2** Citing a spec you didn't read. Read it at SOP-5.

**N3** Skipping skill inventory because you classified the slice as
"light." SOP-4 runs regardless of slice weight.

**N4** Bundling unrelated changes (mode changes, pre-existing dirty files,
off-topic fixes) into a feat commit. See C2, C3.

**N5** Re-running a slice that's already shipped. Check HEAD, check
BACKLOG status, refuse if duplicate. Report the duplicate with the
existing commit SHA.

**N6** Inventing test results, repro evidence, or LLM behavior. If you
can't verify without running it, say "needs manual repro" and stop short
of guessing.

**N7** Silently reconciling conflicts between prompt instructions and
on-disk reality. Flag the conflict, STOP, ask.

**N8 SESSION-STATE.md preserve-and-coexist**: If `SESSION-STATE.md` has
pre-authored content from another session at the start of your slice,
do NOT overwrite it. Add your slice's entry alongside. If your slice
does not need to write to `SESSION-STATE.md`, leave it untouched and
surface the concurrent edit as a drift flag in the final report.
Reference: D-019, D-022 class incidents.

## How to Add a Feature
1. Check spec exists in `docs/specs/`
2. Create/update backend models in `app/models/`
3. Create Alembic migration: `alembic revision --autogenerate -m "description"`
4. Apply: `alembic upgrade head`
5. Create Pydantic schemas in `app/schemas/`
6. Write tests in `tests/`
7. Implement service in `app/services/`
   - **If LLM-powered:** pick the tier (fast vs reasoning), add the task
     name to `app/core/llm_router.py` if new, then call
     `generate_for_task(task="...", ...)`
8. **Add a PostHog event** — name it in snake_case, pick frontend vs
   backend, and add it to `.agent/skills/analytics.md` so the catalog
   stays current
9. Create API route in `app/api/routes/` or `app/api/v1/routes/`
10. Register route in `app/main.py`
11. Run: `python -m pytest tests/ -v`
12. Implement frontend (page → component → hook → API client)
    - **Style with theme tokens only** — no hardcoded colors
13. Add PostHog `capture()` on user interactions
14. Run: `npx vitest run`
15. Push to main (CI/CD auto-deploys)

## Environment
- Python 3.13, Node 20, PostgreSQL 16 + pgvector, Redis 7
- Backend: FastAPI, SQLAlchemy 2.0 async, py-fsrs, google-genai
- Frontend: React 18, TypeScript 5, Vite 5, Tailwind, Framer Motion
- Analytics: PostHog (instrumented from Phase 1)
- Email: Resend (from Phase 2)
- Deploy: Vercel + Railway (continuous from Phase 0)
- DB URL: `postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport`