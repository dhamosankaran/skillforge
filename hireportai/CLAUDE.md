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

## Before Any Task
Run SOP-1..9 below. Spec, skill, and state reads happen there.

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

*Skill-gap close-loop* (added 2026-04-28 for B-073 cohort item 2): if your
final-report draft is going to mention a skill-inventory gap (a missing
skill that would have shortened audit time), check whether the same gap
has been flagged before:

- `rg -l "skill-inventory gap" SESSION-STATE.md` → read the matching
  Recently Completed entries from the last 5 (newest-first).
- If the same skill name appears as a gap-flag in any of those entries,
  this is flag #2+. Auto-file a BACKLOG row at status 🟦 in the same
  commit as the slice's other BACKLOG operations (R15 close-line, etc.).
  Use the next-free ID per R17 watermark.
- If the skill name is NOT in the last-5 entries, this is flag #1. Note
  in final report only. No row file.

The 🟦 status means parked, not blocking. Chat-Claude triages activation
per existing cohort discipline.

Why: per B-073 origin, `backend.md` was flagged 5 times before resolution
(slices 6.0 / 6.4.5 / B-070 regen / B-072 prompt-draft / B-072 impl). Five
flags is four too many. The auto-file at flag #2 caps unresolved gap-life
at one slice cycle. False negatives (gap flagged 6+ slices ago) are
acceptable — the search bound is "last 5", not "all history", to keep
SOP-4 cheap. False positives (re-surfacing a stale gap) are bounded by
🟦 status — non-blocking, chat-Claude can decline to activate.

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

**SOP-8 Concurrent-session detection.** Run `git log --oneline -20` and
`git status`. Surface BACKLOG status of any rows the slice plans to
touch (the target row, any rows the prompt cites, any rows the spec
body cross-refs). If any cited row has flipped status, or if any
commit since the prompt was drafted touches files in the slice's
planned scope, STOP and report — concurrent sessions may have shipped
since prompt draft.

**SOP-9 No concurrent CC sessions on one tree.** Do not run two Claude
Code sessions against the same working tree simultaneously. If a second
session is required, the second session must operate on a separate
branch. Concurrent same-tree sessions race on staging — confirmed via
reflog in D-019, D-021a, D-022. SOP-8 detects it at execution; SOP-9
prevents it upfront.

## Chat-Claude ↔ Claude Code Handoff

These rules apply to the chat-Claude side of the workflow (prompt
drafting). They are stated here so Claude Code can recognize and reject
prompts that violate them.

**H1 Drafted prompts are thin.** A drafted CC prompt contains: goal,
mode (audit / spec-author / implementation), specs by number+path,
BACKLOG references with R17 caveat, close-line format, expected test
counts, current HEAD SHA. It does NOT restate SOP-1..9, R-rules, N-rules,
or the Review Layer. Restating creates drift between disk and prompt
when CLAUDE.md changes.

**H2 SOP is the verification layer.** Chat-Claude does not add literal
verify blocks (`ls docs/specs/`, `grep -n BACKLOG.md`, etc.) to prompt
bodies. SOP-5, SOP-6, SOP-7 already perform these checks at execution
time, regardless of prompt content. Adding them to the prompt body
duplicates the safety net.

**H3 CC stops on phantoms — that is correct.** When CC catches a phantom
spec number, BACKLOG ID, or SHA via SOP-5/6/7 and stops, that is the
safety net working as designed. It is not a chat-side failure to
prevent. The correct chat-side response is to acknowledge the catch,
fix the citation, and re-issue the prompt — not to add defensive rules
to prevent it next time.

**H4 BACKLOG IDs in drafted prompts use the R17 caveat.** Chat-Claude
may reference an existing BACKLOG ID by number, but for new rows the
prompt should say "file the next available B-### at execution time per
R17 watermark" rather than hardcoding an ID. Pre-allocated IDs collide
with concurrent sessions (B-037 incident).

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

**R14 No new feature without a spec**. Every new feature gets a spec at
`docs/specs/phase-N/NN-name.md` **before** code is written, following
the template in the playbook §3.2. Exceptions: (a) retrofits / backfills,
(b) pure bug fixes with no design surface, (c) explicit user override.
Default = spec first.

**R15 Backlog-first (closure + filing in one rule)**.

(a) Reference required: every implementation prompt must reference the
`BACKLOG.md` item ID(s) it closes (e.g., `closes B-005, E-002`). If no
item exists, create one in `BACKLOG.md` first, then proceed.

(b) Status updates (🔴 → 🟡 → ✅ → 🟦) are the only `BACKLOG.md` edits
Claude Code may make autonomously. Priority, scope, and new rows
require Dhamo unless the prompt explicitly authorizes row creation.

(c) Pre-commit gate: before EVERY commit on a slice that touches
`BACKLOG.md`, list every BACKLOG ID referenced in the slice. For each
closed ID, confirm 🔴→✅ flip with a close-line referencing the
implementation commit SHA. For each filed-only ID, confirm row exists
with status 🔴 and any gating notes. Pre-amend SHAs are acceptable
(findable via `git log --all`). Closure happens in the implementation
commit, not a separate slice. If any ID can't be confirmed, STOP and
ask. Non-optional. (Formerly R18; merged into R15(c) on 2026-04-26.)

(d) BACKLOG row note budget (added 2026-04-28 for B-073 cohort item 2):
`BACKLOG.md` rows are an index, not a slice log. Row notes follow this
shape:

- *Closed rows*: `Closed <date> by <sha>. <one-line why this matters>.`
  Examples that hold this shape: B-061, B-062, B-063.
- *Forward-filed rows* ("scope when picked up"): bullet what +
  dependencies + `see spec <path>` if the spec exists. DO NOT inline
  scope detail that belongs in the spec body.

Backstops (soft, R19-trigger if exceeded):

- Closed row notes: ~200 words.
- Forward-filed row notes: ~300 words.

Slice details (file inventory, JCs, drift surfacing, R-rule fires, audit
findings, working-tree state, SOP gates) live in `SESSION-STATE.md`
Recently Completed, NOT in the BACKLOG row. The BACKLOG row points at
the slice's commit SHA; SESSION-STATE owns the narrative.

This rule applies to NEW rows from this slice forward. Pre-existing
sprawling rows are NOT retroactively edited (would churn git history for
zero functional gain). They stay as-is until naturally touched.

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

**R19 Push-back rule**: If anything genuinely surprises you OR the prompt
contradicts on-disk reality, STOP and ask. Don't silently reconcile.
Minor judgment calls inside a slice — make the call, log it in your
final report.

Examples of "genuine surprise" that warrant STOP:
- Prompt names a BACKLOG ID that doesn't exist on disk
- Prompt asks you to create a row that already exists
- HEAD doesn't match what the prompt expects
- Test counts mismatch on an implementation slice
- Working tree has unexpected dirty files suggesting mid-flight work
- Spec the prompt cites conflicts with the prompt's own instructions
- Slice would require creating a new BACKLOG row and prompt didn't
  authorize it

(Formerly the second R3; renamed to R19 on 2026-04-26 to resolve ID
collision with R3 "Never skip auth".)

## Code Quality

**Q1 Simplicity first**: Minimum code that solves the slice goal. No
speculative abstractions, no configurability that wasn't asked for, no
error handling for impossible scenarios. If you wrote 200 lines and it
could be 50, rewrite. Test: "would a senior engineer say this is
overcomplicated?" If yes, simplify before commit.

**Q2 Surgical changes**: Touch only what the slice requires. Don't
"improve" adjacent code, comments, or formatting. Match existing style
even when you'd write it differently. Pre-existing dead code → log in
`SESSION-STATE.md` drift ledger and file a BACKLOG row if appropriate;
don't delete in the current commit. (Pairs with C3 single-concern.)

**Q3 State assumptions, don't pick silently**: If the prompt has
multiple valid interpretations, name them and ask before Step 1.
Surfacing ambiguity up-front is cheaper than a re-roll. Distinct from
R19 (which fires on prompt-vs-disk conflict) and N7 (which fires on
silent reconciliation): Q3 fires on prompt ambiguity *before* code is
written.

**Q4 Verifiable goal before code**: Restate the slice's success
condition as a check you can run (a test passing, a route returning the
expected status, output matching a shape). Weak goals ("make it work")
require constant clarification; strong goals let R10's loop-breaker fire
cleanly. (Pairs with R1 test-first.)

## Commit Hygiene

**C1 Never `git add -A` from above `hireportai/`**: The git root is
`SkillForge/`, parent of `hireportai/`. `git add -A` from that level
will sweep in `archive/`, sibling project files, and unrelated work.
Always `cd hireportai/` first OR stage explicit paths. When a prompt
template says `git add -A`, override it with explicit paths. The
template language is itself a footgun — pre-existing dirty files in
`SkillForge/` (above `hireportai/`) will bundle. Reference: B-034
bloated-commit incident. (Merges former C5 — sharpening text folded
in 2026-04-26.)

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

## Review Layer

**CODEX review**: All commits in every slice are reviewed by CODEX
(external review tool) after commit. Write code, commit messages, and
spec/doc edits with that in mind — clarity over cleverness, no silent
compromises. Chat-Claude does not need to restate this in prompt bodies;
it applies always. (See H1.)

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

### Reporting discipline (LIGHT MODE)

The Final Report bullet list above is the MAXIMUM scope of what to
include. The MINIMUM is silence on every default-case item.

**Default cases — DO NOT report:**
- SOP-1..9 each ran clean (silence implies all 9 ran clean).
- N8 allowlist unchanged from prior slice.
- C1 explicit-path staging only (default; deviation is bundled
  `git add -A`, which itself violates N8).
- R15(c) no closures (default; deviation is closures, which
  require the closure trail anyway).
- R17 watermark unchanged (default; deviation is new IDs claimed).
- Two-commit pattern followed (default; deviation is single-commit
  or three-commit, which require explanation anyway).

**Deviations and status changes — DO report:**
- SOP step that caught something (mismatch, conflict, drift).
- N8 allowlist delta (file added/removed from pre-existing-dirty
  set).
- BACKLOG status flips (with the B-### + new status).
- R17 watermark advances (new IDs claimed with rationale).
- JCs surfaced (info-only is fine; STOP-trigger is mandatory).
- Skill-inventory gaps (SOP-4 close-loop).
- CR staleness verdict change.

**Prior-HEAD chain — keep the immediate predecessor only.** One
line: "Prior HEAD: `<sha>` — <one-sentence summary>." Deeper
history is `git log` away.

When in doubt, drop. The audit at
`docs/audits/process-bloat-2026-05-01.md` (`3d03861`) found
~20-25% of recent-entry text is structural duplicate. The rule
above reclaims that surface. Sidecar rows that mirror compacted
content (e.g., a "prior, kept for archaeology" row alongside a
compact form) are themselves bloat — git history is the archaeology.

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

## Long-lived file maintenance

**Drift-archive cut rule** (added 2026-04-28 for B-073 cohort item 2):
`SESSION-STATE.md` `## Drift flags` table cuts ✅ RESOLVED rows to
`docs/drift-archive.md` when the active table reaches 30 rows.

Mechanism:

- At end of any slice, count rows in `SESSION-STATE.md` `## Drift flags`
  table. If count ≥ 30, cut all ✅ RESOLVED rows (status starts with
  `✅ RESOLVED`) to `docs/drift-archive.md`, appending under a new
  dated heading `## Cut <YYYY-MM-DD> from <slice-SHA>`.
- Active rows (🟡 PARTIAL / 🟡 PENDING / 🟡 OPEN) stay in
  `SESSION-STATE.md`.
- The cut runs as part of the closing slice's commit (NOT a separate
  slice).

Archive file shape:

- Top of file: one-paragraph header explaining what it is.
- Each cut: `## Cut <date> from <SHA>` heading + the rows verbatim
  (preserve table format).
- Append-only. No re-shaping, no de-duplication, no re-ordering.

False positives (cut a row that turned out to be relevant): re-fetch
from git history. Archive is a denormalization for scannability, not a
source-of-truth.

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

## This file is working if

- Diffs touch fewer files than the slice strictly requires (C3 + Q2
  holding)
- Clarifying questions arrive before Step 1, not after the first
  failed test (Q3 holding)
- 3-strike halts (R10) are rare; surprise-STOPs (R19) are common and
  resolve quickly
- No commit re-runs a shipped slice (N5 holding)
- Skill-inventory gaps surface in final reports rather than going
  unmentioned (SOP-4 holding)

## Revision history
- 2026-05-01: Added LIGHT MODE reporting discipline subsection
  per docs/specs/process/01-light-mode-reporting.md (B-090). Codifies
  the "default-silent / report-deviations" rule + one-prior-HEAD-only
  + sidecar-rows-are-bloat addendum (Step 2(b) — captures the
  spec-author slice's experimental sidecar JC). R14 exception (b) —
  pure rule codification, no design surface, no tests run.
- 2026-04-28: Added R15(d) BACKLOG row note budget (close/forward-filed
  shape + ~200/~300-word backstops). Appended SOP-4 skill-gap
  close-loop (auto-file 🟦 on flag #2 within last-5 Recently Completed
  entries). Added "Long-lived file maintenance" section with the
  drift-archive cut rule (30-row threshold, append-only
  `docs/drift-archive.md`). R14 exception (b) — pure SOP codification,
  no design surface, no tests run. Reference: B-073 cohort item 2
  (closed by `b468025`).
- 2026-04-27: Added Code Quality section (Q1–Q4) and "This file is
  working if" self-check block. R14 exception (b) — pure rule
  codification, no design surface. Reference: B-### (this slice).
- 2026-04-26: R18 (filed by B-039 on 2026-04-25) merged into R15(c).
  R3 "Push-back rule" renamed to R19 to resolve ID collision with R3
  "Never skip auth". Added Chat-Claude ↔ CC Handoff section (H1–H4)
  and SOP-9 "No concurrent CC sessions on one tree" (alongside
  existing SOP-8 detection). Removed redundant MUST-READ section
  (duplicated SOP). Merged C5 sharpening text into C1. N1-SUPPLEMENT
  promotion to N9 deferred (6 callsites). Reference: B-048 (closed by `e2714b4`).
