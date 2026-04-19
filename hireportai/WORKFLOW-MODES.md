# Workflow Modes — How to Run Claude Code by Slice Type

> Companion to `AGENTS.md`, `CLAUDE.md`. Decides **which Claude Code pattern** to use for a given slice. The wrong mode wastes time (too cautious) or breaks production (too aggressive).
>
> **Default if uncertain:** Mode 1 (Manual Single-Session). It's never wrong, only sometimes slow.

---

## The five modes

| Mode | Name | Approval | Sessions | When |
|------|------|----------|----------|------|
| **1** | Manual single-session | Per action | 1 | Default. Anything touching production data, payments, auth, schema. |
| **2** | Auto-accept single-session | Whitelisted bash + file writes auto; reads always free; destructive always blocked | 1 | Doc-only, spec backfill, internal tooling, sandbox experiments. |
| **3** | Writer/Reviewer (sequential) | Manual on each session | 2 (sequential) | Non-trivial logic, security-sensitive code, anything where test/code drift would be expensive. |
| **4** | Spec-author + Implementer (sequential) | Manual on each session | 2 (sequential) | Net-new features. Especially when the spec is hazy or the surface area is large. |
| **5** | Parallel worktree | Per session, but isolated | 2+ (parallel, separate git worktrees) | Two genuinely independent slices that don't touch the same files. Rare for solo work. |

---

## Decision tree

Walk top to bottom. First match wins.

```
Is the slice modifying:
  - Stripe / payments / billing?              → Mode 1
  - Auth / JWT / OAuth?                       → Mode 1
  - User data, GDPR-relevant fields?          → Mode 1
  - Alembic migrations on existing tables?    → Mode 1
  - Production secrets or env vars?           → Mode 1

Is the slice doc-only?
  - Spec backfill, BACKLOG edits, README?     → Mode 2
  - SESSION-STATE / CODE-REALITY regen?       → Mode 2
  - Skill file updates?                       → Mode 2

Is the slice net-new feature with a fuzzy spec?
  - PRD says "should do X" but no AC?         → Mode 4
  - User-flow change with new screens?        → Mode 4

Is the slice security-sensitive or test-heavy?
  - Idempotency, rate limiting, validators?   → Mode 3
  - Anything where the bug is silent?         → Mode 3

Are there two independent slices in BACKLOG?
  - Different files, different subsystems?    → Mode 5
  - Otherwise                                 → Mode 1
```

---

## Mode details

### Mode 1 — Manual single-session (DEFAULT)

**Setup:** Standard `claude` in your terminal. Default permissions. Approve each tool call.

**Use for:**
- Anything in BACKLOG with priority P0
- Anything that touches: Stripe webhook handler, auth routes, User model, payment tables, Alembic migrations on existing data
- First-of-its-kind work where you're learning the shape of the problem

**Examples from current backlog:**
- B-005 — Stripe webhook idempotency
- E-013 — Subscription cancellation flow
- E-016 — Chat with AI (first time wiring per-card chat persistence)

**Why:** The 0.4% false-positive classifier rate of auto-accept becomes catastrophic when the false positive is "deleted production user data." Manual approval is cheap insurance.

---

### Mode 2 — Auto-accept single-session

**Setup:**
```bash
claude --auto-accept
# OR scope it precisely:
claude --allowedTools "Edit,Bash(git*),Bash(npx vitest*),Bash(pytest*)"
```

**Allow list (start narrow, widen with experience):**
- File reads — always
- File writes inside `docs/`, `.agent/`, `BACKLOG.md`, `SESSION-STATE.md`, `CODE-REALITY.md`
- `git add`, `git commit`, `git status`, `git log`, `git diff`
- Test runners (`pytest`, `vitest`, `tsc --noEmit`)

**Block list (never auto-approve):**
- `git push` — keep human-gated
- Anything writing to `hirelens-backend/app/` or `hirelens-frontend/src/`
- `alembic upgrade` / `alembic downgrade`
- `psql`, `redis-cli`, anything with `--force` or `-rf`
- Network calls beyond known docs hosts

**Use for:**
- Spec backfill (E-021–E-027)
- BACKLOG row updates (status field flips)
- SESSION-STATE updates between slices
- CODE-REALITY regeneration
- README / playbook edits
- Skill file additions

**Examples from current backlog:**
- E-021 through E-027 (the seven spec backfills) — perfect candidates
- D-001 resolution work (doc-only)

**Why:** You've been approving 200 keystrokes per slice for documentation. Stop. Doc work is reversible via git. The risk floor is "noisy commit history" — that's it.

**Safety net:** Run only on a clean working tree. If it goes off the rails, `git reset --hard HEAD~N` and re-prompt.

---

### Mode 3 — Writer/Reviewer (sequential)

**Setup:** Two separate Claude Code sessions, one after the other. Different terminals or different times.

**Session A — "Writer of Tests":**
```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.
Read docs/specs/phase-N/NN-feature.md.
Read CODE-REALITY.md (Sections 2, 3, 4 — backend models, routes, services).

You are writing TESTS ONLY. Do not write implementation code.

Audit step 1: list every existing test file related to <feature> and
the public API surface (functions, classes) you'll be testing.

Then for each acceptance criterion in the spec, write a failing test
in tests/test_<feature>.py. Tests should fail with NotImplementedError
or by calling functions that don't exist yet.

Run: python -m pytest tests/test_<feature>.py -v
Confirm all tests fail with the expected error shapes.

Commit: docs+test(scope): failing test suite for <feature>
Stop. Do not implement.
```

**Session B — "Implementer" (fresh `claude` session, fresh context):**
```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md.
Read docs/specs/phase-N/NN-feature.md.
Read tests/test_<feature>.py (the source of truth — do not modify).

Implement <feature> until every test in tests/test_<feature>.py passes.
Do not modify the tests. If a test seems wrong, stop and ask Dhamo.

Run tests after each change. 3-strike rule applies (CLAUDE.md R10).

Commit per atomic change. Final commit closes spec.
```

**Use for:**
- B-005 (Stripe webhook idempotency) — exact archetype: silent bug if tests and impl share assumptions
- B-007 (PERSONA_CONFIG runtime breakage) — tests should encode the contract, separate session ensures the contract is met
- Anything where you'd write a regression test by reflex anyway

**Why:** When the same Claude session writes both the test and the code, it can satisfy the test by encoding the same wrong assumption in both. Fresh-context implementer can't cheat — it only sees tests + spec.

**Cost:** ~1.5x the time of Mode 1. Worth it when the bug class is silent (idempotency, race conditions, validation gaps).

---

### Mode 4 — Spec-author + Implementer (sequential)

**Setup:** Two sequential sessions like Mode 3, but the first session writes the *spec*, not tests.

**Session A — "Spec Author":**
```
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. Read BACKLOG.md.
Read docs/prd.md (relevant section only).

You are authoring docs/specs/phase-N/NN-<feature>.md against the
template in skillforge_playbook_v2.md §3.2.

Step 1: ask me up to 5 clarifying questions, one at a time, that you
need answered before the spec is unambiguous. Do not guess. Do not
write the spec until I've answered.

Step 2: draft the spec. Cross-reference relevant skill files
(.agent/skills/*) and identify which subsystem skill applies, or flag
that a new one is needed.

Step 3: list the BACKLOG IDs this spec resolves and propose any new
B-/E- IDs that need to be added.

Do NOT write code. Stop after the spec is committed.
```

**Session B — "Implementer":** (same as Mode 3 Session B, but reading the freshly-authored spec)

**Use for:**
- E-006 (state-aware home dashboard) — fuzzy "states" need interrogation
- E-018 (admin LLM-driven analytics) — surface area is large, AC unclear
- Any time the BACKLOG row is enhancement-shaped but the spec column is empty

**Examples from current backlog:**
- E-001 (master doc audit) — actually well-suited; spec it before running it
- E-006, E-018, E-019

**Why:** You've been the spec author for everything. That's slow and biases the spec toward what you already imagined. A spec-author session that *interviews you* surfaces ambiguity earlier and produces tighter ACs. The interview pattern is the SDD canonical workflow.

**Discipline note:** Resist the urge to skip Step 1 (the questions). The 5 questions are the whole point. If Claude Code drafts without asking, stop it and re-prompt: "Step 1 first. Questions only."

---

### Mode 5 — Parallel worktree (rare for solo work)

**Setup:**
```bash
# From repo root
git worktree add ../skillforge-slice-a feature/slice-a
git worktree add ../skillforge-slice-b feature/slice-b

# Terminal 1
cd ../skillforge-slice-a && claude

# Terminal 2 (different terminal window)
cd ../skillforge-slice-b && claude
```

**Use for:** Two slices that touch entirely separate files. Examples that would qualify:
- E-019 (Content Feed Flow — admin UI) **+** E-021 (LLM router spec backfill — doc only) — zero overlap.
- B-010 (delete orphan Navbar.tsx) **+** any backend slice — frontend vs backend, different trees.

**Don't use for:** Anything where the slices touch the same files, schemas, or types. The merge will be your problem, not Claude Code's.

**Why:** You have one human review cycle per session. Two sessions = two review cycles. Past 2 parallel sessions, you're context-switching faster than reviewing carefully. Anthropic engineers run 4–6 in parallel because they have 4–6 hours of work queued. You usually don't.

---

## Choosing a mode by current BACKLOG item

Worked example for the items most likely to come up next:

| Backlog ID | Slice | Recommended mode | Why |
|------------|-------|------------------|-----|
| B-005 | Stripe webhook idempotency | **Mode 3** (Writer/Reviewer) | Silent bug class, test/impl drift expensive |
| E-001 | Master doc audit + sync | **Mode 4 → Mode 2** (spec it, then auto-accept the doc fixes) | Audit is doc-only; spec it first to scope it |
| E-002 | /learn/* and /prep/* restructure | **Mode 1** (manual) | Routes touch every page; high blast radius |
| E-006 | State-aware home dashboard | **Mode 4** | Fuzzy spec (what counts as "state"?) |
| E-013 | Subscription cancellation | **Mode 1** | Stripe + user data |
| E-014 | Paywall dismissal + win-back | **Mode 3** | Counter logic + email scheduling — test-able, drift-prone |
| E-016 | Chat with AI on flashcards | **Mode 1** first time, **Mode 3** for iteration | First-of-its-kind in this codebase |
| E-018 | Admin LLM-driven analytics | **Mode 4** | Five sections, fuzzy ACs |
| E-021–E-027 | Spec backfills | **Mode 2** (auto-accept) | Doc-only, fully reversible |
| B-010 | Delete orphan Navbar.tsx | **Mode 2** | Trivial reversible change |
| D-001 resolution | Update SESSION-STATE for shipped slices | **Mode 2** | Doc-only, mechanical |

---

## Mode usage discipline

**At slice start**, the first line of your prompt to Claude Code should declare the mode:

```
Mode 3 — Writer/Reviewer. This is Session A (Writer of Tests).
Read AGENTS.md. Read CLAUDE.md. ...
```

This makes the choice explicit, surfaces it in commit history, and lets future-you audit which modes pay off.

**At slice end**, log the mode in SESSION-STATE.md "Recently Completed":
```
1. P5-S26c — Stripe webhook idempotency [Mode 3] — closes B-005
```

After 10 slices, you'll have data on which modes work for which slice types in *your* codebase, not generic advice.

---

## What we're explicitly NOT doing yet

These are valid Anthropic-internal patterns that don't fit your scale:

- **Headless agentic SDLC** (Claude runs end-to-end without supervision). Requires sandbox infra and a classifier safety net you don't have.
- **Agent teams** (orchestrator agent spawning specialized subagents on shared tasks). Overhead exceeds benefit for solo work on one product.
- **`.claude/agents/` directory with named subagents** (`spec-author.md`, `reviewer.md`, etc.). Worth setting up after you've used Modes 3 and 4 enough times by hand to know what each role's prompt should look like. Premature otherwise.

Add these later when the friction of doing them by hand exceeds the friction of setting them up.

---

*Authored 2026-04-19. Update when a new mode emerges from practice or when a recommended mode in the backlog table proves wrong in retrospect.*