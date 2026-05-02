# Phase 6 / Slice 6.15 — Legacy retirement easy-wins

## Status: Drafted (spec-author) — closes B-101. Impl forward-filed at B-102.

> **Scope precedent.** This spec implements the "Option C / spec 15"
> recommendation from the cleanup triage at
> `docs/audits/phase-6-cleanup-triage.md` (B-100, anchor `5291d9e`). The
> sibling spec `16-legacy-cards-schema-retirement.md` (not yet authored)
> covers the 18 RETIRE-WITH-MIGRATION items the triage flagged as
> Phase-6 cleanup overflow. This spec covers ONLY the mechanically
> safe, zero-consumer-impact items.

### Phase 6 locked decisions referenced by this spec

- **R15(d)**: BACKLOG row scope blocks ≤ 200 words target / 400 hard;
  Recently Completed entries ≤ 250 hard ceiling. This spec authoring
  itself is process-rule-aligned (B-100 RC entry compaction is co-shipped
  in this slice's SS write).
- **N1**: do not name a BACKLOG ID that doesn't exist on disk. Spec
  closes B-101 (spec-author) + forward-files B-102 (impl). Both
  verified at slice start (R17 watermark = B-100 highest in-use, B-101
  next-free).

---

## 1. Problem

Three "weak-coupling" cleanups were deferred from Phase-6 implementation
slices to slice 6.15 (cleanup) on the assumption that retirement would
ship as one umbrella slice. The cleanup triage at
`docs/audits/phase-6-cleanup-triage.md` (B-100) verified that the
umbrella scope (~25 items / 8 themes) overflows a single slice and
recommended splitting into:

- **Spec 15 (this spec)** — the 3 mechanically safe items with zero or
  trivially re-pointable live consumers.
- **Spec 16** — the 18 RETIRE-WITH-MIGRATION items (live-consumer
  rewrites, dual-read collapses, table drops).

Without this split, the easy-wins items continue to accrete drift
(every Phase-6 spec that references them re-mentions the deferral) and
slice 16 grows in scope every time a new "we'll fix this in 6.15" note
is added to a Phase-6 spec.

### 1.1 Step 0 audit findings

Verified at HEAD `9ee8281`:

- **T7.1 — `DailyStatus` weak coupling.** Defined at
  `hirelens-backend/app/schemas/study.py:30`. Re-imported by
  `hirelens-backend/app/schemas/quiz_item.py:14` with the comment
  "re-imported per spec §6.2". Consumed by `study_service.py:37`
  (5 instantiations) + `quiz_item_study_service.py:52` (3
  instantiations). The re-import is the only thing that ties Phase-6
  schemas to a Phase-5 file — once `DailyStatus` lives in a neutral
  module, both consumers import from the same place.

- **T7.2 — `_next_local_midnight` duplication.** Defined byte-identically
  (modulo docstring) at `study_service.py:168` AND
  `quiz_item_study_service.py:88`. The Phase-6 service's docstring even
  flags it: *"Duplicated from `study_service.py:168` per OQ-3 — kept
  local so slice 6.15 cleanup can `git rm` this file without touching
  `study_service`."* (per B-062 closure trail). Total 4 callsites
  (3 in `study_service.py`, 1 in `quiz_item_study_service.py`).

- **T8.1 — `study_dashboard_viewed` catalog row.** The row at
  `.agent/skills/analytics.md:46` lists `pages/StudyDashboard.tsx` as
  the emitter. `pages/StudyDashboard.tsx` was deleted in slice 6.7
  (B-077, `c6d9274`). `rg "study_dashboard_viewed"` across
  `hirelens-backend/`, `hirelens-frontend/src/`, and `.agent/skills/`
  finds zero code emitters — only the catalog row itself. The catalog
  row is the last reference to a deleted page; it is dead documentation.

### 1.2 Why this matters

- **Drift accretion.** Every Phase-6 spec (`02`, `04`, `06`, `07`, `08`)
  contains a "slice 6.15 cleanup" reference. Until 6.15 ships, the
  references stay live and grow with every new spec authored.
- **Catalog accuracy.** `analytics.md` is the canonical PostHog event
  catalog; carrying a row for a deleted page misleads anyone grepping
  for "where does this event fire".
- **Helper duplication.** `_next_local_midnight` is a 4-line helper;
  it is not a "this needs a refactor" smell at face value. But it is a
  **flagged** duplication (the docstring calls it out) — leaving it
  duplicated invites the next FSRS-related slice to add a third copy
  rather than fix the second. Cheap to fix now.

---

## 2. Goals

- **G-1** Move `DailyStatus` to a neutral module so `schemas/quiz_item.py`
  no longer re-imports from `schemas/study.py`. Spec-§6.2 cross-coupling
  flag in `02-fsrs-quiz-item-binding.md` clears.
- **G-2** Eliminate the `_next_local_midnight` duplicate by extracting
  the helper to a shared util. Both services call the same function.
  B-062's "slice 6.15 git rm cleanliness" note clears.
- **G-3** Remove the `study_dashboard_viewed` catalog row from
  `analytics.md`. Catalog matches reality.
- **G-4** Each item is independently revertable. The slice ships as one
  commit (per C3 single-concern at the *concern* level — "easy-wins
  cleanup"); revert flips all three back atomically.

---

## 3. Non-goals (out-of-scope this slice)

- **No FE deletions.** T1.3 (`/study/category/:id` + `/study/card/:id`
  redirects) was triage-listed as RETIRE-NOW but is contingent on
  T1.1+T1.2 retiring first; standalone deletion would 404 old bookmarks
  → UX regression. Deferred to spec 16.
- **No service deletions.** `study_service.py`, `card_service.py`,
  `gap_mapping_service.py`, `card_admin_service.py` all stay. Spec 16.
- **No table drops.** No alembic migration in this slice. `cards` /
  `categories` / `card_progress` / `card_feedback` stay. Spec 16.
- **No FSRS helper consolidation beyond `_next_local_midnight`.** T7.4
  (broader FSRS helper fold) cascades from `study_service.py`
  retirement (T3.3, spec 16). Spec 16 absorbs it naturally when the
  legacy service is deleted.
- **No analytics catalog rewrites beyond T8.1.** T8.2
  (`study_dashboard_source_hint_shown` rename-or-retire decision) is
  DEFERRED — needs Dhamo input. Out of mechanical-cleanup scope.
- **No B-010 row edit.** Triage flagged `Navbar.tsx` is not orphan on
  disk (live in `LandingPage.tsx` + `LoginPage.tsx`); B-010 row is
  stale. Edit is its own slice.
- **No new tests beyond regression guards.** This slice deletes /
  relocates; existing tests must continue to pass. New tests are
  bounded to "import from the new home works" + "helper still returns
  the right value".

---

## 4. Architecture — file-deletion / relocation manifest

This is a **deletion-heavy spec**. There is no new feature surface,
no new schema, no new route, no new FE component. The deliverables are:

| Item | Action | File(s) | Lines added | Lines removed |
|------|--------|---------|-------------|---------------|
| T7.1 | New file | `app/schemas/daily_status.py` (or move into existing module per §14 OQ-A) | ~20 | 0 |
| T7.1 | Edit | `app/schemas/study.py` — remove `class DailyStatus` body, keep a thin re-export `from app.schemas.daily_status import DailyStatus` for Phase-6-spec-16 back-compat (or delete entirely per §14 OQ-A) | ~1 | ~17 |
| T7.1 | Edit | `app/schemas/quiz_item.py:14` — flip import source | ~1 | ~1 |
| T7.1 | Edit | `app/services/study_service.py:37` — flip import source | ~1 | ~1 |
| T7.1 | Edit | `app/services/quiz_item_study_service.py:52` — flip import source | ~1 | ~1 |
| T7.2 | New file (or new symbol in existing util) | `app/utils/local_time.py` (or per §14 OQ-B) — `_next_local_midnight` (renamed to `next_local_midnight`, no leading underscore now that it's public-shared) | ~10 | 0 |
| T7.2 | Edit | `app/services/study_service.py:168` — `git rm` the helper, flip 3 callsites (`:246`, `:294`, plus internal at `_compute_daily_status`) to import + call public name | ~1 import + 3 callsite renames | ~6 |
| T7.2 | Edit | `app/services/quiz_item_study_service.py:88` — `git rm` the helper, flip 1 callsite (`:222`) | ~1 import + 1 callsite rename | ~10 (helper + docstring) |
| T8.1 | Edit | `.agent/skills/analytics.md:46` — delete row | 0 | 1 |

**Total file-touch count:** ~7 files modified, 1-2 new files created.
**Net line delta:** estimated -10 to +10 (deletion-heavy with
re-export thin-files compensating).

---

## 5. Schema definitions

No new tables. No column additions. No alembic migration.

The only schema-layer change is **module relocation** of an existing
Pydantic model:

```
# Before: hirelens-backend/app/schemas/study.py
class DailyStatus(BaseModel):
    cards_consumed: int
    cards_limit: int
    can_review: bool
    resets_at: datetime

# After: hirelens-backend/app/schemas/daily_status.py
class DailyStatus(BaseModel):
    cards_consumed: int
    cards_limit: int
    can_review: bool
    resets_at: datetime

# hirelens-backend/app/schemas/study.py keeps a thin re-export
# (per §14 OQ-A's hint (a)):
from app.schemas.daily_status import DailyStatus  # back-compat re-export
```

The model body, docstring, and field semantics are byte-identical.
Existing serialisation contracts (PostHog events, response payloads)
are unaffected.

---

## 6. BE service & route surface

### 6.1 `_next_local_midnight` extraction (T7.2)

Helper body (current, identical in both files):

```python
def _next_local_midnight(now_utc: datetime, tz: ZoneInfo) -> datetime:
    local_now = now_utc.astimezone(tz)
    tomorrow = (local_now + timedelta(days=1)).date()
    return datetime.combine(tomorrow, time(0, 0, 0), tzinfo=tz)
```

After T7.2:

```python
# hirelens-backend/app/utils/local_time.py  (or per §14 OQ-B)
def next_local_midnight(now_utc: datetime, tz: ZoneInfo) -> datetime:
    """Next user-local midnight as a tz-aware datetime in the user's tz.

    Used by daily-review wall reset (study_service / quiz_item_study_service)
    to compute when the per-day card-review counter resets.
    """
    local_now = now_utc.astimezone(tz)
    tomorrow = (local_now + timedelta(days=1)).date()
    return datetime.combine(tomorrow, time(0, 0, 0), tzinfo=tz)
```

Naming change: leading underscore dropped (the helper is now part of a
shared util's public surface, not a service-private). Both services
import: `from app.utils.local_time import next_local_midnight`.

Callsite renames (4 total):

- `study_service.py:246` `_next_local_midnight(...)` → `next_local_midnight(...)`
- `study_service.py:294` same
- `study_service.py` (`_compute_daily_status` body) — third callsite
- `quiz_item_study_service.py:222` same

### 6.2 No route changes

Zero routes touched. `/api/v1/study/...` and `/api/v1/quiz-items/...`
mounts unchanged. Service signatures unchanged (only an internal helper
moves).

---

## 7. Migration

**Zero new alembic migrations.** No DB schema change. Alembic chain
head stays at `c2b8a4d9e6f1` (carry-forward from slice 6.14 / B-098 /
spec 14).

---

## 8. FE component graph

No FE files touched. Zero FE deltas.

---

## 9. Analytics events

### 9.1 T8.1 — `study_dashboard_viewed` catalog row removal

**Before** — `.agent/skills/analytics.md:46`:

```
| `study_dashboard_viewed` | `pages/StudyDashboard.tsx` | `{category_count, locked_count}` |
```

**After:** row deleted.

**Verification** — at slice start, `rg "study_dashboard_viewed"` across
`hirelens-backend/`, `hirelens-frontend/src/`, and `.agent/skills/`
returned zero matches outside the catalog row itself. After deletion,
expect zero matches anywhere.

### 9.2 No other catalog edits

`study_dashboard_source_hint_shown` (live emitter at `Learn.tsx:302`,
slice 6.7 preserved) stays. T8.2 deferred per §3 non-goal.

---

## 10. Test plan (implementation slice)

**No new feature tests.** Existing test suite verifies behavioural
contracts; this slice only relocates symbols.

### 10.1 Regression guards (BE)

Both targeted at the lift/dedup mechanics. Bounded test additions:

- **`tests/test_daily_status_relocation.py`** (new file, ~3-5 tests):
  1. `from app.schemas.daily_status import DailyStatus` resolves.
  2. `from app.schemas.study import DailyStatus` still resolves
     (back-compat re-export per §14 OQ-A hint (a)).
  3. `from app.schemas.quiz_item import DailyStatus` — verifies the
     re-import on `quiz_item.py:14` was flipped to the new home (or
     removed if §14 OQ-A locks (b) "delete re-export" instead of (a)).
  4. Pydantic field shape assertion: `DailyStatus.model_fields` keys =
     `{'cards_consumed', 'cards_limit', 'can_review', 'resets_at'}`.
- **`tests/test_local_time_util.py`** (new file, ~3 tests):
  1. `next_local_midnight(now_utc=2026-05-02T12:00:00+00:00, tz=UTC)` →
     `2026-05-03T00:00:00+00:00`.
  2. `next_local_midnight(now_utc=2026-05-02T23:00:00+00:00, tz=ZoneInfo('America/Los_Angeles'))`
     → `2026-05-03T00:00:00-07:00` (verifies the local-tz crossing).
  3. Both `study_service` and `quiz_item_study_service` import the
     shared helper (verify via inspect/import).

### 10.2 Existing test suite must stay green

CI-canonical (`-m "not integration"`) baseline at slice start: **BE
842, FE 456**. Expectation:
- BE: **+5..+8** (new regression files).
- FE: **+0** (no FE surface).
- Existing tests must NOT regress (any currently-passing test that
  imports `DailyStatus` from `schemas.study` continues to pass via the
  re-export per §14 OQ-A hint (a)).

### 10.3 No integration tests added

R13 marker discipline preserved. No live LLM keys or external services
touched.

---

## 11. Acceptance criteria

- **AC-1** `app/schemas/daily_status.py` exists and exports `DailyStatus`
  with the byte-identical 4-field shape (`cards_consumed`,
  `cards_limit`, `can_review`, `resets_at`).
- **AC-2** `app/schemas/study.py` re-exports `DailyStatus` (per §14
  OQ-A hint (a)) OR deletes it entirely (per OQ-A hint (b)) — one
  must hold.
- **AC-3** `app/schemas/quiz_item.py:14` import line no longer
  references `schemas.study` (sourced from `schemas.daily_status` or
  the chosen new home).
- **AC-4** `app/utils/local_time.py` (or chosen home per §14 OQ-B)
  defines `next_local_midnight(now_utc, tz)` returning a tz-aware
  datetime equal to the next midnight in `tz`.
- **AC-5** `_next_local_midnight` symbol no longer exists in either
  `study_service.py` or `quiz_item_study_service.py`. Both services
  import the public symbol from the shared util.
- **AC-6** `rg "_next_local_midnight"` returns zero matches outside
  this slice's git diff.
- **AC-7** `.agent/skills/analytics.md` no longer contains a row for
  `study_dashboard_viewed`. `rg "study_dashboard_viewed"` across
  `hirelens-backend/`, `hirelens-frontend/src/`, `.agent/skills/`
  returns zero matches.
- **AC-8** BE test count = 842 + new regression tests (+5..+8). FE
  count unchanged (+0). No regression in any pre-existing test.
- **AC-9** Zero alembic revisions added. `alembic heads` returns
  `c2b8a4d9e6f1` (carry-forward).
- **AC-10** Spec `02-fsrs-quiz-item-binding.md` §6.2 cross-coupling
  note ("weak coupling, slice 6.15 cleanup") still references the same
  semantic concern; the spec text is NOT edited in the impl slice (Q2
  surgical — spec body edits are spec-edit slices, not impl slices).
  The cross-coupling itself is *gone* on disk; the spec note now
  describes pre-impl history, which is acceptable.

---

## 12. LOCKED DECISIONS (D-N)

> Empty placeholder — locked at the §12 amendment slice (mirrors slice
> 6.0 `e8eecdd` / 6.4.5 `df58eaf` / 6.5 `acba7ed` / 6.6 `fb92396` /
> 6.7 `0c21223` / 6.8 `ab07168` / 6.10 `be7d59a` / 6.11 `d9bfcfc` /
> 6.13.5 `4bf5220` / 6.14 `b5bec37` precedent). Once Dhamo locks each
> §14 OQ to one of its options + author hints, this section will carry
> the resolved decisions. Until then, §14 is the source of truth.

---

## 13. Out of scope (deferred to other Phase-6 slices)

Mirrors the cleanup triage's verdict buckets:

- **Spec 16** absorbs all 18 RETIRE-WITH-MIGRATION items: T1.1 / T1.2 /
  T1.3 / T2.2 / T2.4 / T2.5 / T3.1 / T3.2 / T3.3 / T4.1 / T4.2 / T4.3 /
  T5.1 / T5.2 / T5.4 / T6.1 / T6.2 / T6.3 / T6.4 (T7.4 subsumed by
  T3.3).
- **DEFERRED** items per triage §Theme tables: T1.4 (Mission Mode
  retirement, out of 18-slice plan), T2.1 (`Navbar.tsx` — not orphan,
  B-010 row stale), T2.3 (`SkillRadar` — Profile-page redesign needed),
  T3.4 (`experience_service` narrative source), T3.5
  (`mission_service`), T3.6 (`onboarding_checklist_service`), T3.7
  (`progress_service` — slice 6.16), T5.3 (`/api/v1/progress/radar` +
  `/heatmap`), T8.2 (`study_dashboard_source_hint_shown` — Dhamo
  decision needed).
- **PROCESS** convention per triage §Theme 8: T8.3 (telemetry-
  confirmation gate before BE-route drops). Lives as Step 0 instruction
  for spec 16 implementation slices, not a deletion artifact.
- **B-010 row edit** (Navbar.tsx is not orphan). Separate slice.

---

## 14. Open questions for chat-Claude / Dhamo

> **Per amendment cadence:** §12 stays empty until a chat-Claude /
> Dhamo §12 amendment slice locks each OQ below to one of its options.
> Until then, §14 is the source of truth.

### OQ-A — `DailyStatus` post-relocation home in `schemas/study.py`

**Author hint:** (a) keep thin re-export `from app.schemas.daily_status
import DailyStatus`. Spec 16 will eventually delete or rewrite
`schemas/study.py` itself; until then, the re-export shields any
external test fixture or downstream consumer that imports from the old
path.

**Options:**
- (a) Keep `schemas/study.py` re-export of `DailyStatus` for
  back-compat. (Author hint.)
- (b) Delete the `DailyStatus` class from `schemas/study.py` entirely;
  no re-export. Forces every importer to flip to the new home in this
  slice. Risk: any importer outside the verified consumer list
  (`schemas/quiz_item.py`, `services/study_service.py`,
  `services/quiz_item_study_service.py`) breaks.

### OQ-B — Home for `next_local_midnight` shared helper

**Author hint:** (a) `app/utils/local_time.py` (new file). The helper
is general (date/tz arithmetic) and not service- or FSRS-specific. A
new `app/utils/` module is conventional for cross-cutting helpers in
this codebase (cf. `app/utils/anonymizer.py`, `app/utils/uuid.py`).

**Options:**
- (a) New file `app/utils/local_time.py`. (Author hint.)
- (b) Add to existing `app/utils/datetime_util.py` — IF it exists.
  (Verify at impl Step 0.)
- (c) Add to a new module-private util inside
  `app/services/_fsrs_helpers.py`. Keeps the helper in the FSRS
  neighbourhood. Risk: future non-FSRS callers have to depend on a
  service-internal module.

### OQ-C — Helper rename: drop leading underscore?

**Author hint:** (a) Yes, rename `_next_local_midnight` →
`next_local_midnight`. Once the helper lives in a shared util, the
leading underscore (Python convention for module-private) is
inconsistent with its now-public role.

**Options:**
- (a) Rename to `next_local_midnight`. (Author hint.)
- (b) Keep `_next_local_midnight` even in the shared util. Pro:
  fewer callsite edits. Con: convention violation.

### OQ-D — Test file naming

**Author hint:** (a) `tests/test_daily_status_relocation.py` +
`tests/test_local_time_util.py`. Mirrors the codebase's existing flat-
tests/ convention (cf. `test_phase6_schema.py`,
`test_quiz_items_api.py`).

**Options:**
- (a) Two flat files per the names above. (Author hint.)
- (b) One bundled file `tests/test_slice_6_15_easy_wins.py`. Pro:
  one slice = one test file. Con: not topical-coherent (the two
  changes are unrelated technically; bundling by slice ID couples
  them artificially).

### OQ-E — `analytics.md` row deletion vs strikethrough

**Author hint:** (a) Hard delete the row. The catalog is supposed to
reflect on-disk reality; a strikethrough creates "deprecated zombie"
rows that accumulate over time. The slice's git diff is the historical
record.

**Options:**
- (a) Hard delete. (Author hint.)
- (b) Strikethrough with `**(DELETED slice 6.15 — emitter
  `pages/StudyDashboard.tsx` removed in B-077)**` annotation. Pro:
  preserves "this used to fire" awareness for someone diffing PostHog
  funnels against the catalog. Con: catalog clutter; PR description
  + git history already preserve provenance.

### OQ-F — Spec 16 follow-up triggering

**Author hint:** (a) Spec 16 authoring is a separate slice; this slice
does NOT block on it. Spec 16 is itself recommended-but-not-mandated
by the triage doc; if Dhamo decides Phase-7 is the right home for
the `cards`-schema retirement, spec 16 may never exist.

**Options:**
- (a) No automatic trigger. Spec 16 is a Dhamo decision. (Author hint.)
- (b) File a 🟦 BACKLOG row at this slice's close pointing at "Spec 16
  authoring — author when slice 6.16 (FSRS retention dashboard)
  ships, since 16d gates on it". Pro: prevents dropping the thread.
  Con: the triage doc itself already serves that role (it lives at
  `docs/audits/`); a 🟦 row duplicates.

### OQ-G — B-010 ("Navbar orphan") row review timing

**Author hint:** (a) File a separate B-### at 🟦 in this slice's close
to track the B-010 review (Navbar is NOT orphan, row needs
update-or-close decision). The triage doc flagged the staleness;
filing a row converts the flag into a queueable item.

**Options:**
- (a) File a 🟦 row at this slice's close. (Author hint.)
- (b) Inline-edit B-010's Notes field in this slice ("disk shows 2
  live importers; row may be stale"). Pro: zero new BACKLOG ID. Con:
  R15(b) "status updates are the only edits CC may make autonomously"
  — touching the Notes field is borderline.
- (c) Defer entirely; chat-Claude / Dhamo handles in a separate
  cohort triage. Pro: cleanest scope. Con: drops the thread.

---

## 15. Dependencies / Status

### Dependencies (slices that must ship before this one)

- Slice 6.7 (B-077, `c6d9274`) — deleted `pages/StudyDashboard.tsx`,
  the emitter that the T8.1 catalog row references. Confirmed shipped.
- Slice 6.2 (B-062, `7b654fb`) — flagged `_next_local_midnight`
  duplication in `quiz_item_study_service.py:88` docstring. Confirmed
  shipped.
- Slice 6.1 (B-061, `a989539`) — created the `quiz_item_progress`
  schema that `quiz_item_study_service` operates on. Confirmed shipped.
- Triage doc B-100 (`5291d9e`) — recommended this spec's scope per
  Option C. Confirmed shipped.

### Slices this spec unblocks

- Spec 16 (`16-legacy-cards-schema-retirement.md`) — once spec 15
  lands the easy-wins, spec 16's scope is unambiguously "everything
  triage marked RETIRE-WITH-MIGRATION". Spec 15 is a forcing function
  for spec 16's authoring.

### Status

- **Spec authored:** B-101 (this slice).
- **Implementation:** B-102 (forward-filed at 🔴, ready for impl
  pickup post-§12 amendment).
- **§12 amendment:** filed by chat-Claude when Dhamo locks §14 OQs.

---

*Spec authored 2026-05-02 by Claude Code at HEAD `9ee8281`. Closes
B-101 (spec-author). Forward-files B-102 (impl, 🔴). Closes triage
recommendation Option C from B-100 (`5291d9e`).*
