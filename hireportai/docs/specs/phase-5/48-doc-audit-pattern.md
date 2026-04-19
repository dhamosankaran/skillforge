# Spec #48 — Doc-Audit Reconciliation Pattern

**Status:** Shipped alongside v2.1 item 5.9 closure (this slice)
**Owner:** Dhamo
**Created:** 2026-04-19
**Phase:** 5 (housekeeping / doc-sync)

## 1. Why this pattern exists

Two kinds of documentation live in this project:

1. **On-disk docs** — `AGENTS.md`, `CLAUDE.md`, `SESSION-STATE.md`, `docs/specs/phase-N/*.md`, `.agent/skills/*.md`. Claude Code and reviewers read these every session. Updating them is part of the slice.
2. **Chat-side project knowledge** — `skillforge_playbook_v2.md`, `claude-code-prompts-all-phases-v2.md` (v2.1), `claude-code-prompts-all-phases-v2.2-patch.md`. These live in chat-Claude's project workspace and cannot be edited from this terminal.

The chat-side artifacts are authored, sliced, and shipped from — then they **freeze**. The repo keeps moving. After every 5–10 slices the chat-side status tables are out of date:

- v2.1 items marked 🔴 PENDING that actually shipped.
- v2.2-patch items whose spec numbers changed.
- Post-playbook slices (e.g., S44–S47) that never appear in either artifact.

This drift is low-cost per slice but compounds. Chat-Claude's priority calls start to rely on stale tables; Claude Code's Step-2 audits re-derive the same truth every time. The cheapest fix is a reconciliation pattern that produces an authoritative on-disk status document (`docs/PHASE-5-STATUS.md` for Phase 5, analogous files for future phases).

## 2. The pattern

### 2.1 Trigger — when to run a reconciliation slice

Run when **any one** holds:

- Chat-Claude's next-slice priority call "feels wrong" — i.e. names a pending item you're reasonably sure already shipped.
- 5–10 slices have shipped since the last reconciliation.
- A new phase (P6+) is about to kick off and the previous phase's status needs to be locked before planning.
- A Step-2 audit on some individual item keeps surfacing more general drift ("this v2.1 entry is wrong … and so are the next three").

Not a reason to run:

- Post-slice housekeeping where you could just update the one row you touched. Update in place; don't spawn an audit slice.

### 2.2 Method

Follow the same Step-0..Step-6 shape the other v2.2 prompts use. Key constraints:

1. **3-minute per-item budget.** Good-enough beats perfect. Ambiguity is signal — mark ❓ AMBIGUOUS and move on.
2. **Touch no product code.** This is a doc slice. Tests must not change (CLAUDE.md Rule 2). If the audit surfaces broken code, log to `SESSION-STATE.md` Deferred Hygiene and move on.
3. **Evidence, not assertion.** Every ✅ SHIPPED row needs a spec number (if any), a file path, and a commit SHA (discoverable via `git log --oneline --grep=<keyword>`). Rows with just "✅ SHIPPED" and nothing else fail the quality gate.
4. **Trust the repo over the playbook.** If v2.1 says "PENDING" and code exists, code wins — update the status doc, not the code.
5. **Record surprises explicitly.** Items where disk reality diverged from chat-Claude's table go in a "Surprises / drift" section so the next sync knows what to propagate back.

### 2.3 Deliverables

- **`docs/PHASE-N-STATUS.md`** — the authoritative status document. Structure: v2.x table → post-playbook slices → pending list → ambiguous list → surprises. See `docs/PHASE-5-STATUS.md` as the template.
- **Ops Log entry in `SESSION-STATE.md`** — one line closing the v2.x doc-audit item for this phase.
- **Locked Decision in `SESSION-STATE.md`** — pins the status doc as the source of truth so future slices know where to update.
- *(Optional)* a spec-backfill cross-referencing the pattern if this is the first time it's run for a phase — this spec is that cross-reference for Phase 5.

## 3. Acceptance Criteria

- **AC-1** — `docs/PHASE-N-STATUS.md` exists and every row has:
  (a) a status marker (✅ / 🟡 / 🔴 / ❓ / ⚫),
  (b) at least one evidence breadcrumb (spec number, file path, or commit SHA),
  (c) a one-line note when the status is anything other than ✅ SHIPPED.
- **AC-2** — Every PENDING item has a clear one-line definition of done usable as the next slice's starting brief (e.g. "Pair `hash_jd` with a new `interview_generations` table keyed on `(user_id, jd_hash)`; return cached on hit.").
- **AC-3** — Every AMBIGUOUS item has a one-line "what's unclear" question, not a guess. Acceptable form: "Is 'above the fold' a hard product requirement or satisfied by 'prominently rendered'?". Unacceptable form: "Might be shipped."
- **AC-4** — The audit itself changed no product code. BE test count unchanged, FE test count unchanged, tsc clean.
- **AC-5** — A "Surprises / drift" section lists items where disk reality diverged from the pre-audit chat-side expectation. If zero surprises, state so explicitly — don't omit the section.

## 4. Out of Scope

- **Editing chat-side project knowledge.** That happens manually outside the terminal. This pattern produces the on-disk truth; chat-Claude syncs project knowledge from it later.
- **Fixing the drift itself.** If an item should have shipped but didn't, the next slice fixes it with a normal spec+code+test flow. The reconciliation slice just tells the truth about status.
- **Retroactive spec backfill for every SHIPPED-without-spec item.** The status doc can cite a commit as evidence. Only backfill a spec when the feature will be touched again soon and needs a contract to protect (CLAUDE.md Rule 14 applies to *future* work, not every historical artifact).
- **Coverage beyond the current phase.** Don't audit closed phases (P0–P4) unless specifically asked; status drift there is much lower and rarely blocks work.

## 5. Provenance

First run for Phase 5: this slice, 2026-04-19. Produced `docs/PHASE-5-STATUS.md` from v2.1 (26 items), v2.2-patch (5 items), and 4 post-playbook slices (S44–S47). Caught three AMBIGUOUS items (5.19, 5.20, 5.23), confirmed four PENDING items (5.17, 5.24, 5.25, 5.26), and surfaced the numbering drift between v2.1 item 5.22 and spec #36 frontmatter (P5-S26a vs P5-S26b). Closes v2.1 item 5.9.
