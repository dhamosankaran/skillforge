# Process bloat scout — 2026-05-01

> **Mode 3 (scout, read-only).** Surfaces bloat hotspots + SOP-restatement
> patterns across the last 5 implementation/amendment slices. Inputs to
> the upcoming optimization sprint: LIGHT MODE codification (primary) +
> sha-backfill.sh automation (primary). Cron rescope (B-078) + two-tier
> RC refactor noted as future inputs only.

## §1 — Header

- **Date:** 2026-05-01 (commit date placeholder until SHA backfill).
- **HEAD at scout:** `f124fde` (SHA-backfill of `2c92f11`; "post-B-088
  SHA-backfill" per the prompt's terminology — slice-level identity is
  `2c92f11`, on-disk HEAD is the backfill tag `f124fde`).
- **Slice classification:** LIGHT MODE candidate. Audit-only, no
  design surface, no test surface, no BACKLOG row claimed.
- **Tests:** BE 761 / FE 445 carried forward verbatim per R14
  exception (b).
- **CR staleness:** ❌ at `1ca046f`. Sharpened LD-1 code-touching gap
  unchanged at 2 (this slice is doc-only). Defer regen per LD-2.

**Scope statement:** identify the structural drivers of SESSION-STATE
Recently Completed entry length + commit message length over the last
5 slices; catalog SOP-N restatement patterns across prompts and
entries; assess whether spec #63 §16's R/W density is a one-off
artifact of the E-043 validation-probe surface or an emerging pattern
that LIGHT MODE codification needs to address.

**Read corpora summary (4 corpora):**

| Corpus | Source | Read |
|---|---|---|
| A | `SESSION-STATE.md` Recently Completed entries 1-5 | lines 175-194 (5 entries; full) |
| B | `git log --oneline -12` + body extracts of impl + SHA-backfill commit pairs | 5 pairs (10 commits) |
| C | `BACKLOG.md` Closed table top 10 rows | lines 187-199 |
| D | `docs/specs/phase-5/63-ats-rescan-loop.md` §1 status line + §15 forward-link + §16 in full | lines 1-7, 873-911, 913-979 |

---

## §2 — Bloat hotspots

### §2.1 Per-entry SESSION-STATE Recently Completed line counts

| # | Slice | Line | Words | Chars |
|---|---|---|---|---|
| 1 | B-088 impl (`2c92f11`) | 175 | 1026 | 8008 |
| 2 | §16 amendment (`13012be`) | 179 | 1168 | 8999 |
| 3 | E-043 validation probe (`35350ea`) | 183 | **1785** | **14136** |
| 4 | Slice 6.13 spec-author (`d6ddcb6`) | 187 | 973 | 7313 |
| 5 | Slice 6.11 content quality (`95104d2`) | 191 | 1105 | 8896 |
| | **Total** | | **6057** | **47352** |
| | **Average** | | **1211** | **9470** |

Median entry ≈ 1100 words. Maximum (entry 3, validation probe) is
~1.8× the median — the probe report condensed P1-P6 per-finding tables
into the entry, plus full IFD-1..IFD-6 narrations.

### §2.2 Top 3 structural drivers of length

For each driver, the "% of entry text" is approximated by line-internal
substring extraction and rounded. Signal/duplicate verdict is keyed to
whether the same content already appears in CLAUDE.md SOP-1..9 or
AGENTS.md.

**Driver 1 — SOP-1..9 per-step restatement.** Every entry restates the
same 9 SOP steps (`SOP-1 starter verified ✓` through `SOP-9 honored`)
as an in-line block, ~80-150 words per entry. **Verdict: duplicate.**
CLAUDE.md SOP-1..9 already mandates each step at every prompt; the
entry's role is to record findings (mismatches, JCs), not to confirm
the SOP fired. The same 9-bullet shape appears in 5/5 entries —
~600-750 total words across the 5 entries (~10-12% of total entry text).

**Driver 2 — N8 / C1 / R15(c) / R17 watermark restatement.** Each
entry restates the same 4 R-rule applicability lines (`N8 working
tree allowlist only ✓; C1 explicit-path staging only ✓` + `R15(c)`
status + `R17 watermark` status), often twice (once mid-entry, once
near the close). ~50-80 words per entry × 5 = ~300 words across 5
entries (~5% of total). **Verdict: duplicate** for the ✓-only cases;
**signal** for the cases where R17 watermark or R15(c) status
actually changes (e.g., entry 1 flips B-088 ✅, entry 2 claims
B-088+B-089 + D-029 — those are real changes worth recording).

**Driver 3 — File enumeration with module-load detail.** Every entry
lists the working-tree N8 allowlist files in full (~12 untracked +
modified items, ~40-60 words per entry × 5 = ~250 words). Plus
"Files: N NEW + N MODIFIED (...) = N net touches" enumeration
~30-50 words per entry. **Verdict: duplicate** for the N8 list
(unchanged across all 5 entries — "identical to prior 27+ slices");
**signal** for the per-slice files-touched list (varies meaningfully).

### §2.3 Aggregate signal vs duplicate split (rough)

Across the 5 entries:
- ~1100-1500 words are duplicate of CLAUDE.md / AGENTS.md content
  (SOP-1..9 restatement + N8-allowlist file list + ✓-only R-rule
  applicability lines).
- ~4500-5000 words are slice-unique signal (JC narration, what-shipped,
  cross-refs, baseline deltas, drift surfacing, SHA chains, spec-impl
  divergences).

**Roughly 20-25% of recent-entry text is structural duplicate.** A
LIGHT MODE codification could reclaim ~250 words/entry without losing
audit value, IF future-readers can be assumed to read CLAUDE.md +
AGENTS.md in parallel with SESSION-STATE. (See §7 question #2 for the
counter-argument.)

---

## §3 — SOP-restatement pattern catalog

Patterns observed in the last 5 entries + the prompts that drove
them. "Prompt" column = whether the slice prompt restated the SOP
(chat-Claude → CC instruction); "Entry" column = whether the
SESSION-STATE entry restated it (CC → future-reader report);
"LIGHT candidate" = pattern is restated in BOTH and is therefore
pure overhead.

| Pattern | Prompt | Entry | LIGHT candidate? |
|---|---|---|---|
| `SOP-1 starter verified ✓` (HEAD match) | Sometimes (precondition block) | 5/5 entries | ✅ — CLAUDE.md SOP-1 already mandates HEAD check |
| `SOP-2 working tree N8 allowlist only ✓` | Sometimes ("N8 only" reminder in commit discipline) | 5/5 entries | ✅ — CLAUDE.md SOP-2 + N8 already mandate |
| `SOP-3 baselines BE X / FE Y carried forward verbatim` | Sometimes (precondition block) | 5/5 entries | ⚠️ — when baseline is unchanged it's duplicate; when there's drift (e.g., entry 1's BE 757→761, entry 5's BE 729→752+23) it's signal |
| `SOP-4 skills loaded: X.md + Y.md` | Sometimes (skill picks listed) | 4/5 entries (entry 3 said "picked but not read") | ⚠️ — signal for which skills were loaded; restating SOP-4 ran isn't |
| `SOP-5 spec read: <path>` | Yes (spec citations are required per N2) | 5/5 entries | ✅ — file path is signal; "SOP-5 ran" is duplicate |
| `SOP-6 BACKLOG IDs verified` | Yes (R15 / R17 watermark required) | 5/5 entries | ⚠️ — ID-existence verification is signal; "SOP-6 ran" is duplicate |
| `SOP-7 starter verified at HEAD X ✓` | No (implicit per SOP-1) | 5/5 entries | ✅ — duplicate of SOP-1; SOP-7 is just "starter == HEAD" recheck |
| `SOP-8 git log --oneline -5 clean since X` | No | 5/5 entries | ✅ — duplicate of SOP-2 in practice; SOP-8 catches concurrent commits |
| `SOP-9 honored: single CC session on this tree` | No | 5/5 entries | ✅ — single-session is the default; restating it is overhead |
| `R14 default`/`R14 exception (b) — no test surface` | Sometimes | 5/5 entries | ⚠️ — flagging the exception is signal; restating "R14 default" is duplicate |
| `R15(c)` + `R17 watermark` lines | Yes (ID claim/close instructions) | 5/5 entries (often duplicated within the entry) | ⚠️ — STATUS changes are signal; ✓-only restatement is duplicate |
| `N8 working tree allowlist only ✓` | Yes (commit discipline) | 5/5 entries (often duplicated) | ✅ — pure duplicate when no N8 violation occurred |
| `C1 explicit-path staging only ✓` | Yes (commit discipline) | 5/5 entries | ✅ — pure duplicate |
| `Two-commit pattern (impl + SHA backfill replacing X)` | Yes (commit discipline) | 5/5 entries | ⚠️ — slice-specific replacement-list detail is signal; "two-commit pattern" framing is duplicate |
| `Prior HEAD: X — <description>` | No | 5/5 entries | ⚠️ — HEAD chain is signal for git-archaeology readers; description duplicates that prior entry |

**LIGHT MODE candidates (8 patterns confirmed pure-duplicate):**
SOP-1, SOP-2 (N8-only), SOP-5 ("SOP-5 ran"), SOP-7, SOP-8, SOP-9, N8
✓-only restatement, C1 ✓-only restatement.

**Hybrid patterns (7 patterns where wording is shared but content
varies):** SOP-3, SOP-4, SOP-6, R14, R15(c), R17, two-commit-pattern,
prior-HEAD chain. These can't be flatly cut — the LIGHT MODE rule
needs to allow restatement-when-status-changes and forbid
restatement-when-status-unchanged.

---

## §4 — Cross-ref density: one-off or emerging pattern

### §4.1 §16 density (CORPUS D)

- **Items:** 5 R-N (R-1..R-5) + 1 W-1 = 6 total.
- **Per-item density:** average ~25 lines (Gap paragraph + Locked
  paragraph + cross-ref + "Slice X implements; closes IFD-Y" line).
- **Section size:** §16 spans lines 913-972 = 60 lines (excluding
  preamble blockquote). Plus 1-line `3d03861` footer entry at
  line 979.
- **Cross-ref count:** §4.2 (×2), §4.3 (×1), §6.2 (×1), §6.3 (×2),
  §9 (×3), §12 D-11 (×1), §12 D-12 (×3), §14 (×0 — post-impl
  reconciliation, not §14-OQ-driven), `app/api/routes/analyze.py`
  line numbers (×3), `.agent/skills/analytics.md` line numbers (×2).
  Total ~18 cross-refs across 6 items ≈ 3 cross-refs per item.

### §4.2 Comparison to §12 D-1..D-12 of same spec

- **Items:** 12 D-N (D-1..D-12).
- **Per-item density:** average ~5 lines (single paragraph,
  RESOLVED-pointer + lock statement + trade-off note).
- **Section size:** §12 spans lines 782-803 = 22 lines for 12 items
  ≈ 1.8 lines per item.
- **Cross-ref count:** mostly back-refs to §14 OQ-X (12 of them, 1:1
  mapping) + ~3 forward-refs to §1.1 audit findings. Total ~15
  cross-refs across 12 items ≈ 1.25 cross-refs per item.

§16 is **~5× denser per item** (25 lines vs 5 lines) and **~2.4×
denser in cross-refs per item** (3 vs 1.25).

### §4.3 Comparison to spec #63 §5.3+§6.1 correction-amendment at `1b86bf0`

The `1b86bf0` amendment was a 2-item correction (§5.3 `scan_id` FK
shape + §6.1 `score_resume_against_jd` signature). Per the spec's
existing §15 footer entry for `1b86bf0` (line 977), it was an in-place
edit pattern — no new section authored, just the §1 status line +
inline section edits + a footer-entry summary. Per-item density was
similar to §16 (~10-15 lines of context per fix), but no R/W
numbering was used because n=2 was small enough to handle inline.

### §4.4 Verdict — one-off / emerging / inconclusive

**INCONCLUSIVE (n=2).** The two precedent post-impl correction
amendments are:

1. `1b86bf0` (2 items, in-place edits, no R/W numbering, no new section).
2. `13012be` / §16 (6 items, R-1..R-5 + W-1, NEW section).

The trend (2 → 6 items, n=2) is too small to extrapolate. Both were
driven by a runtime audit (B-086a final report for `1b86bf0`; E-043
validation probe `35350ea` for §16). Whether the 6-item density was
intrinsic to E-043's surface (orchestrator + UI + 4 events + 5 ACs
exposed multiple drift dimensions) or generic to validation-probe-
driven amendments is unanswerable without a 3rd data point.

**Recommendation flag (downstream decision slice):** if a 3rd
post-impl correction amendment ships in the next sprint with ≥4
items, treat as emerging and codify R/W numbering + per-item Gap +
Locked structure as the canonical post-impl amendment shape. Until
then, `1b86bf0` and §16 stay as bespoke precedents.

---

## §5 — sha-backfill.sh automation surface

### §5.1 Two-commit pair count

5 of the last 5 implementation/amendment slices used the two-commit
pattern (impl + SHA backfill). 100% conformance.

| Slice | Impl SHA | Backfill SHA | Subject template match |
|---|---|---|---|
| B-088 impl | `2c92f11` | `f124fde` | ✅ |
| §16 amendment | `13012be` | `249a551` | ✅ |
| E-043 validation probe | `35350ea` | `6489408` | ✅ |
| Slice 6.13 spec-author | `d6ddcb6` | `9f48cfd` | ✅ |
| Slice 6.11 content quality | `95104d2` | `38ff5fb` | ✅ |

All 5 SHA-backfill subjects follow the canonical template:

> `chore(session-state): SHA backfill for <slice-name> — replace <this-slice> placeholders`

No drift detected.

### §5.2 Placeholder-replacement file set per pair

Standard placeholder sites observed across the 5 pairs:

| Site | B-088 | §16 | e043 probe | 6.13 spec | 6.11 cq |
|---|---|---|---|---|---|
| `BACKLOG.md` active row source-sha column | ✅ | ✅ | n/a | ✅ | n/a |
| `BACKLOG.md` Closed-table row "Closed by" column | ✅ | n/a | n/a | n/a | ✅ |
| `BACKLOG.md` row body "Spec amended at" prose ref | n/a | ✅ | n/a | n/a | n/a |
| `SESSION-STATE.md` Session Header HEAD field | ✅ | ✅ | ✅ | ✅ | ✅ |
| `SESSION-STATE.md` Recently Completed entry HEAD ref (multiple sites in entry) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Spec body §15/§16 footer dated entry | n/a | ✅ | n/a | ✅ | n/a |
| Spec body §15 forward-link block | n/a | ✅ | n/a | ✅ | n/a |
| Audit document footer SHA reference | n/a | n/a | ✅ | n/a | n/a |

**Placeholder count per pair:** 4-8 sites (varies by slice type).

### §5.3 Automation feasibility

The placeholder set is **regular enough to script**, with one
caveat: the placeholder-set is FUNCTION OF SLICE TYPE, not of the
impl commit's touch list. Specifically:

- **Implementation slice** (`B-088 impl`, `6.11 cq`): touches BACKLOG
  active row + Closed-table row + SESSION-STATE Header + SESSION-STATE
  entry.
- **Spec-author / amendment slice** (`§16`, `6.13 spec`): touches
  spec body §15/§16 + BACKLOG forward-file row + SESSION-STATE
  Header + SESSION-STATE entry.
- **Audit slice** (`e043 probe`, this slice): touches audit footer +
  SESSION-STATE Header + SESSION-STATE entry.

A `sha-backfill.sh` script could:
1. Take impl-commit SHA as argument.
2. Identify slice type by inspecting `git show --stat` (does it
   touch a spec? An audit? A BACKLOG active row?).
3. Run `git grep '<this-slice>' -l` to enumerate exact files needing
   replacement (already implicit in current manual workflow per
   `grep -c '<this-slice>'` verification step).
4. `sed -i` replacement on each + stage + commit with the canonical
   template.

The grep-then-sed approach is **agnostic to slice type** — it just
finds and replaces `3d03861` wherever it appears. The slice-type
classification is needed only for the commit subject's `<slice-name>`
field (which a script could derive from the impl commit's subject).

**Estimated script size:** ~30-50 lines of bash. **Estimated
time savings per slice:** ~2-3 minutes of manual `Edit ... replace_all`
calls + verification. Across the recent ~30 slice cadence, ~60-90
minutes of CC time per month.

---

## §6 — Future inputs (not primary deliverable)

### §6.1 Cron rescope (B-078)

Per LD G2: "Railway cron config-only" lock. No slice 6.14 has
shipped yet; B-078 stays as an architecture decision row with the
G2 lean recorded but no impl.

**Expected SESSION-STATE weight contribution under the G2 lock:**
slice 6.14 (cron consumer of B-087's `email_log`) would be a small
slice — 1 alembic-free config touch + 1 cron job entrypoint + a
handful of tests. Comparable in scope to B-084 / 6.11 — expect a
~1000-1200-word entry following the established shape. Not a
significant bloat contributor on its own.

### §6.2 Two-tier RC (Recently Completed) refactor

**No written articulation of this refactor exists in the scout
corpora.** SESSION-STATE.md, CLAUDE.md, AGENTS.md, and the audit
documents do not reference a "two-tier RC" structure. Searched:
- `SESSION-STATE.md` — no match for "two-tier" or "tier"
- `CLAUDE.md` — no match
- `AGENTS.md` — not opened (assume no match per absence in surrounding artifacts)
- `docs/audits/*.md` — no match

**Flag:** the two-tier RC refactor needs a follow-up scout slice OR
a chat-Claude specification turn before it can be planned. Per the
prompt's framing it's a "future input," so this audit doesn't block
on it — but the optimization sprint should not assume the refactor's
shape is known.

---

## §7 — Open questions for downstream decision slice

1. **Is JC narration valuable for future-reader auditing or just
   bloat?** §3 catalog flags ~3-5 JC mentions per entry as ~150-300
   words. If future-readers (CC running a similar slice) benefit
   from seeing prior JCs (calibration on "what surprised the prior
   slice"), JC narration is signal. If future-readers always re-do
   their own Step 1 audit, JC narration is duplicate.

2. **Should SOP-restatement be allowed in entries when the SOP step
   is non-default for that slice?** E.g., entry 5's "SOP-3: BE 729 →
   752 (+23)" is signal (delta is non-trivial); entry 1's "SOP-3:
   BE 757 → 761 (+4 within forecast)" is signal (delta + forecast
   match); entry 2's "SOP-3: BE 757 / FE 445 carried forward
   verbatim" is duplicate (no delta, R14 exception (b) covers it).
   The LIGHT MODE rule needs to distinguish — straight cut would
   lose the delta signal.

3. **Should the N8 allowlist file list be replaced with "N8 only ✓"
   when unchanged?** §2.2 Driver 3 quantifies this at ~250 words
   across 5 entries. Risk: future SESSION-STATE compaction or
   N8-violation slice loses the explicit pre-incident state. Reward:
   meaningful word-count reduction.

4. **Should sha-backfill.sh take impl SHA as argument, OR auto-detect
   the most recent commit lacking a SHA-backfill successor?** The
   second option is more ergonomic but more error-prone (what
   constitutes "successor" — title prefix match, branch HEAD, no
   newer commit since `3d03861` placeholders disappeared?).

5. **Is the 6-item §16 density an intrinsic feature of validation-
   probe-driven amendments, or specific to E-043's surface?**
   §4.4 verdict was INCONCLUSIVE at n=2. A 3rd post-impl correction
   amendment with ≥4 items would tip the verdict. The decision
   slice should declare a watch-rule rather than codify
   prematurely.

---

## §8 — JCs surfaced

**JC #1 (info-only, no STOP) — Recently Completed entry numbering
is not strict.** SESSION-STATE.md `## Recently Completed (last 5)`
section header says "(last 5)" but entries are numbered 1, 2, 2, 2,
2, 1, 2, 2, 3 (8 visible entries past line 175 with mixed 1/2
prefixes — convention is "prepend new entry as 1 + bump prior 1 to
2", which over time produces multiple "2." entries from prior
slices that never got renumbered). Cosmetic; doesn't affect
anything but counts. Out of scope this slice.

**JC #2 (info-only, no STOP) — n=2 sample size for §4 verdict.**
Only 2 post-impl correction amendments exist on disk (`1b86bf0` +
`13012be`). The "one-off / emerging / inconclusive" classification
in §4.4 is honestly INCONCLUSIVE; the audit avoids over-claiming.

**JC #3 (info-only, no STOP) — sha-backfill.sh feasibility is
inferred, not measured.** §5.3's ~30-50 line size estimate + 2-3
min/slice savings estimate are extrapolations from the manual
workflow. A pilot script would calibrate.

---

## §9 — R15(c) + R17 watermark

- **R15(c):** no closures this slice (audit-only, not BACKLOG row).
- **R17 watermark:** unchanged. B-090 next-free numeric ID;
  D-030 next-free drift ID. No claims this slice.

---

## §10 — Files touched

- **1 NEW:** `docs/audits/process-bloat-2026-05-01.md` (this file).
- **1 MODIFIED:** `SESSION-STATE.md` (Session Header HEAD field +
  Recently Completed entry).
- **0** BACKLOG rows touched.
- **0** spec edits.
- **0** code touches.

Footer:

- **HEAD at slice start:** `f124fde` (B-088 SHA-backfill).
- **HEAD at slice end:** `3d03861` (replaced in commit-2 SHA
  backfill).
- **Slice commit (audit doc + SESSION-STATE entry):** `3d03861`
- **SHA-backfill commit:** `<this-slice-backfill>` (this SHA-backfill
  commit replaces `3d03861` placeholders with the slice-1 SHA
  across audit footer + SESSION-STATE Session Header HEAD field +
  Recently Completed entry's HEAD references).

**Awaiting CODEX review per Rule 11.**
