# Process Spec #01 — LIGHT MODE reporting discipline

## §1 Status + scope

- **Status:** drafted at `b85bfd1`. D-1..D-7 locked.
- **Scope:** amends `CLAUDE.md` "Final Report (Every Slice)" section by
  appending a new "Reporting discipline (LIGHT MODE)" subsection. Does
  NOT change SOP-1..9, R-rules, N-rules, C-rules, or Q-rules. Changes
  only how slices REPORT on having run them.
- **Forward-link:** B-090 impl slice applies §4's text verbatim to
  `CLAUDE.md` and writes one example compact `Recently Completed`
  entry that itself follows the new shape.
- **Note on phase directory:** `docs/specs/process/` is a new phase
  directory (mirrors the `phase-N/` shape). This is its first spec.
  Process specs document workflow rules that span phases and have no
  product surface.

## §2 Inputs

Spec inputs come from `docs/audits/process-bloat-2026-05-01.md`
(`3d03861`), Mode 3 read-only scout across 4 corpora. The audit's
quantitative findings are the empirical basis for §4's rule.

### §2.1 Per-entry word counts (audit §2.1)

| # | Slice | Words |
|---|---|---|
| 1 | B-088 impl (`2c92f11`) | 1026 |
| 2 | §16 amendment (`13012be`) | 1168 |
| 3 | E-043 validation probe (`35350ea`) | 1785 |
| 4 | Slice 6.13 spec-author (`d6ddcb6`) | 973 |
| 5 | Slice 6.11 content quality (`95104d2`) | 1105 |
|   | **Average** | **1211** |

~20-25% of recent-entry text is structural duplicate of CLAUDE.md
SOP-1..9 + AGENTS.md content; ~250 words/entry reclaimable per audit
§2.3.

### §2.2 SOP-restatement pattern catalog (audit §3)

**8 patterns confirmed pure-duplicate** (drop unconditionally):
SOP-1 ("starter verified ✓"), SOP-2 ("N8 allowlist only ✓"), SOP-5
("ran"-marker without spec path), SOP-7 ("starter verified at HEAD
X ✓"), SOP-8 ("git log clean since X"), SOP-9 ("single CC session"),
N8 ✓-only restatement, C1 ✓-only restatement.

**7 hybrid patterns** (drop when ✓-only; keep when status changes):
SOP-3 (baselines), SOP-4 (skills loaded), SOP-6 (BACKLOG IDs), R14
(default vs exception), R15(c) (no closures vs closures), R17
(watermark unchanged vs advanced), two-commit pattern, prior-HEAD
chain.

### §2.3 sha-backfill.sh ROI (audit §5)

5/5 recent slices used the two-commit pattern with consistent
template. ~30-50 line bash script estimated; ~2-3 min/slice savings ×
~30 slices/month = ~60-90 min CC time/month. **Out of scope for this
spec — separate slice will pick up automation if prioritized.**

## §3 Locked decisions

- **D-1 — Rule home = CLAUDE.md amendment, no sidecar.** New
  "Reporting discipline (LIGHT MODE)" subsection appended below the
  existing Final Report bullet list. No new template file. A
  SESSION-STATE template sidecar would itself be process bloat.

- **D-2 — Hybrid pattern rule = report deviations, assume defaults
  silently.** Pattern: "X did Y" only when Y is not the default.
  Default-case "X ran ✓" is dropped.

- **D-3 — SOP enumeration = drop pure-duplicate restatement.** Cite
  specific SOP-N steps only when that step caught something
  (mismatch, conflict, drift). The bare line "SOP-1..9 ran clean"
  is ALSO dropped — silence is the default-met signal.

- **D-4 — N8 allowlist enumeration = drop when unchanged.** The
  canonical allowlist stays in entries-when-it-changes; not relocated
  to `CLAUDE.md` or a sidecar. Compact form: `N8 allowlist
  unchanged` (when true, single line) OR `N8 allowlist changed:
  <delta>` (when something added/removed).

- **D-5 — Prior-HEAD chain = keep one prior HEAD only.** Immediate
  predecessor with one-sentence summary. Deeper history is
  `git log` away. Drop the multi-step "Prior HEAD: X — Y; Earlier
  HEAD: Z — W; ..." pattern.

- **D-6 — Implementation surface = CLAUDE.md amendment ONLY.** No
  new template file. The B-090 impl slice's own Recently Completed
  entry is the canonical example of the new compact shape.

- **D-7 — Backward migration = none.** New shape applies forward
  from B-090 impl slice. Existing Recently Completed entries stay
  as-is — rewriting them would itself be process bloat.

## §4 CLAUDE.md amendment text (verbatim)

The B-090 impl slice appends the following subsection below the
existing Final Report bullet list in `CLAUDE.md`. Verbatim:

> ### Reporting discipline (LIGHT MODE)
>
> The Final Report bullet list above is the MAXIMUM scope of what to
> include. The MINIMUM is silence on every default-case item.
>
> **Default cases — DO NOT report:**
> - SOP-1..9 each ran clean (silence implies all 9 ran clean).
> - N8 allowlist unchanged from prior slice.
> - C1 explicit-path staging only (default; deviation is bundled
>   `git add -A`, which itself violates N8).
> - R15(c) no closures (default; deviation is closures, which
>   require the closure trail anyway).
> - R17 watermark unchanged (default; deviation is new IDs claimed).
> - Two-commit pattern followed (default; deviation is single-commit
>   or three-commit, which require explanation anyway).
>
> **Deviations and status changes — DO report:**
> - SOP step that caught something (mismatch, conflict, drift).
> - N8 allowlist delta (file added/removed from pre-existing-dirty
>   set).
> - BACKLOG status flips (with the B-### + new status).
> - R17 watermark advances (new IDs claimed with rationale).
> - JCs surfaced (info-only is fine; STOP-trigger is mandatory).
> - Skill-inventory gaps (SOP-4 close-loop).
> - CR staleness verdict change.
>
> **Prior-HEAD chain — keep the immediate predecessor only.** One
> line: "Prior HEAD: `<sha>` — <one-sentence summary>." Deeper
> history is `git log` away.
>
> When in doubt, drop. The audit at
> `docs/audits/process-bloat-2026-05-01.md` (`3d03861`) found
> ~20-25% of recent-entry text is structural duplicate. The rule
> above reclaims that surface.

## §5 Acceptance criteria (B-090 impl slice)

- **AC-1:** `CLAUDE.md` "Final Report (Every Slice)" section gains a
  new subsection "Reporting discipline (LIGHT MODE)" with §4's text
  verbatim.
- **AC-2:** `CLAUDE.md` revision history gains one dated line
  referencing this spec.
- **AC-3:** B-090 impl slice's own Recently Completed entry follows
  the new compact shape — no SOP-1..9 enumeration, no N8 allowlist
  file list (since unchanged), one prior HEAD only. This entry is
  itself the canonical example.
- **AC-4:** B-090 impl slice's Recently Completed entry is < 250
  words (current 5-entry average is ~1211 words; target ~80%
  reduction as a sanity check, not a hard line).
- **AC-5:** BACKLOG B-090 closure trail follows existing R15(c)
  convention.
- **AC-6:** No SOP-1..9 itself changes. No R-rule, N-rule, C-rule,
  or Q-rule changes. The SOP/R/N/C/Q corpus is the floor of
  behavior; LIGHT MODE is the ceiling on reporting about it.

## §6 Non-goals

- Not changing SOP-1..9 itself.
- Not adding `sha-backfill.sh` (audit §5; separate slice).
- Not retroactively rewriting old Recently Completed entries.
- Not relocating the N8 allowlist to a sidecar.
- Not changing the two-commit pattern itself.
- Not changing R15(c) closure-trail discipline.

## §7 Open questions

None — D-1..D-7 lock all decisions surfaced by the audit's §7 open
questions.

## §8 Drift watch

- After 5 slices under LIGHT MODE, sample word counts. If average
  Recently Completed entry length > 400 words, the rule may need
  sharpening. Informal watch, not a scheduled audit.
- If audit §4 cross-ref density question revisits with a 3rd
  post-impl correction amendment surfacing ≥4 R/W items, file a
  separate spec amendment to codify §16-style R/W density as
  canonical.

## §9 Cross-refs

- `docs/audits/process-bloat-2026-05-01.md` (`3d03861`) — scout
  inputs.
- `CLAUDE.md` "Final Report (Every Slice)" section — amendment
  target for B-090.
- Precedent: SOP-8 codification at `2504d6b` (single-slice
  process-rule amendment, no §12 OQ dance).

## §10 BACKLOG row

- **B-090** filed 🔴 by this slice for impl pickup. See
  `BACKLOG.md` Active backlog → Bugs (B-).

---

**Footer**

- Spec authored at: `b85bfd1` (replaced in commit 2 SHA backfill).
- HEAD at slice start: `880171e`.
- Audit input SHA: `3d03861`.
- Awaiting CODEX review per Rule 11.
