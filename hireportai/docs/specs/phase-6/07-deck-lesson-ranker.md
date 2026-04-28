# Phase 6 — Slice 6.6: Lens-Ranked Deck/Lesson Ordering for Interview Prepper

## Status: Drafted + §12 amended at `<this-slice>` locking D-1..D-16 from §14 OQ-1..OQ-11 + sub-OQs (OQ-1b / 1c / 3b / 4b / 9b)

| Field | Value |
|-------|-------|
| **Slice** | 6.6 |
| **Phase** | 6 (Curriculum Platform) |
| **Mode** | Mode 4 spec-author → followed by §12 amendment → impl |
| **Filed at** | `bcb1085` (spec-author HEAD pin) |
| **BACKLOG row** | **B-074** 🔴 (filed by this slice) |
| **Depends on** | spec #01 (`a989539`) ▪ spec #02 (`7b654fb`) ▪ spec #06 (`930a6a2`) ▪ existing `app/services/gpt_service.py` ATS scan output ▪ `tracker_applications_v2.analysis_payload` JSONB column (spec #59) |
| **Blocks** | spec #07 (slice 6.7 — persona-aware Learn page composition) which consumes the ranker's output. |
| **Cross-refs** | scout `docs/audits/phase-6-scout.md` §2.4 (ATS gap-mapping today) + §2.5 (cold-start) + §6 slice-by-slice line 945-952 + Recommendations R-2 (helper shape lock-in). LD G2/H1/I1/J2 untouched. |

---

## 1. Problem

The Phase 6 curriculum is a flat catalogue of 12 decks × N lessons. With
slice 6.5 shipped, every read path now respects persona-visibility and
tier invariants — a free Interview Prepper sees a deterministic subset
of foundation decks, ordered by `decks.display_order`. That deterministic
order is correct for browse but **not** for the core interview-prep loop
the PRD describes:

> "Scan a JD → see your skill gaps → study the lessons that close the
> gaps you have right now → re-scan and watch the score climb."

`display_order` is a curator preference, not a personalisation signal.
The user just told us (via their last ATS scan) which skills the JD
demands and which they're missing — we should rank decks/lessons by how
well each closes those gaps. That's the core "lens" promise of the
product: every static asset (deck, lesson, quiz_item) is re-ordered by
the user's most recent scan-derived skill-gap-set.

### 1.1 Step 0 audit findings

Audit reads at HEAD `bcb1085` (post-B-073 cohort item 2):

1. **ATS scan output** (`app/services/gpt_service.py` +
   `app/schemas/responses.py:17-22`):
   `AnalysisResponse.skill_gaps: List[SkillGap]` where
   `SkillGap = {skill: str, category: 'Technical'|'Soft'|'Certification'|'Tool',
   importance: 'critical'|'recommended'|'nice-to-have'}`. Also exposes
   `missing_keywords: List[str]` (raw keyword list before structuring).
   Persisted on disk via `tracker_applications_v2.analysis_payload`
   (JSONB, `deferred()` load, spec #59 §6).

2. **Existing legacy bridge** (`app/services/gap_mapping_service.py`):
   two-tier strategy mapping `SkillGap.skill` strings to legacy
   `categories` rows — Tier 1 deterministic tag-join on `cards.tags`
   JSON; Tier 2 pgvector cosine fallback on `cards.embedding`. Only
   live consumer: `/api/v1/onboarding/recommendations`. **This bridge
   targets `cards`/`categories`, NOT `decks`/`lessons`.** A Phase 6
   ranker cannot reuse it directly — it needs a parallel bridge over
   the new schema.

3. **Phase 6 schema reality** (`app/models/deck.py` +
   `app/models/lesson.py` from slice 6.1):
   - `decks` columns: `slug`, `title`, `description`, `display_order`,
     `icon`, `persona_visibility`, `tier`, `archived_at`. **No
     `tags` column.** **No embedding column.**
   - `lessons` columns: + `concept_md`, `production_md`, `examples_md`,
     `version`, `version_type`, `published_at`, `quality_score`
     (`Numeric(3,2) NULLABLE`), `archived_at`. **No `tags` column.**
     **No embedding column.**
   - The natural matching surface today is **slug** (decks +
     lessons) and **title** (both) — both are short, human-curated
     strings. `concept_md` body text exists but is large and noisy.

4. **lesson_service post-slice-6.5** (`app/services/lesson_service.py`):
   four public functions all respect persona/tier/archive invariants
   (`get_lesson_with_quizzes`, `get_deck_with_meta`,
   `list_lessons_in_deck`, `get_deck_lessons_bundle`). **Missing:** a
   "list all decks visible to user" helper. The ranker needs one
   (either as a new public function on `lesson_service` or by
   borrowing the persona/tier filter helpers and writing its own
   query).

5. **quiz_item_progress** (slice 6.1 / used by slice 6.2 + slice 6.5):
   per-`(user, quiz_item)` FSRS state; columns include `state`
   (new|learning|review|relearning), `due_date NOT NULL`,
   `last_reviewed`, `reps`, `lapses`. The personalisation signal
   "how much work does this user have left in this deck" requires
   joining `quiz_item_progress` → `quiz_items` → `lessons` → `decks`
   filtered by `(user_id, due_date <= now)`, then aggregating per
   deck. Live in slice 6.5's invariants but not exposed as a service
   function today.

6. **No "recent skill gaps" service helper exists today.** Scout
   §2.4 + R-2 explicitly call this out as a missing dependency. Two
   options sketched:

   - **(A) Aggregated read.** New `get_recent_skill_gaps(user_id,
     lookback_days, limit) → list[SkillGap]` that queries
     `tracker_applications_v2` for the user's recent rows with
     `analysis_payload IS NOT NULL`, unmarshals the JSONB
     `skill_gaps` array, and unions/dedupes. Cost: N rows × JSONB
     unmarshal per ranker call. No schema work, no backfill.
   - **(B) Materialised `user_skill_gap` table.** Denormalise rows
     on scan write. Faster reads, but adds schema work, an
     `analyze.py` write-side hook, and a backfill migration for
     pre-existing scans.

   §12 D-13 locks (A) per scout default; no schema work, no backfill.

7. **Cold-start state** (scout §2.5): a Pro user with no scan has
   zero rows in `tracker_applications_v2` for their `user_id`,
   `home_state_service.last_scan_date == null`, and
   `/api/v1/onboarding/recommendations` returns
   `{scan_id: null, results: []}`. There is no synthesised default
   "lens-result" — the ranker MUST handle the no-scan branch
   explicitly. Per scout's locked decision, the cold-start fallback
   is "Study Board all decks" view (i.e., `display_order` ranking).

8. **No FE consumer of ranked output exists today.**
   `StudyDashboard.tsx` is the existing /learn entry point and shows
   no deck/recommendation/ranked references. Slice 6.7 is the planned
   consumer. This slice's deliverable is **BE-only**.

### 1.2 Why this matters

Without the ranker, the lens promise is not yet wired:

- Free Interview Prepper sees foundation decks in `display_order`
  even after a scan that flagged "RAG" and "Kubernetes" as critical
  gaps — the LLM-Internals deck won't surface above Personality-Coding
  unless the curator happens to have ordered it that way.
- The "scan → study → re-scan" loop has no per-user bias. The user
  could scan, fail to find their gaps in the first three decks, and
  abandon the loop.
- Slice 6.7's persona-aware Learn-page composition needs a stable
  ranker output to consume; without this slice it would have to
  compute its own ordering inline, mixing concerns.

Slice 6.6 ships the ranker as a service-layer primitive; slice 6.7
mounts the FE that consumes it.

---

## 2. Goals

| # | Goal |
|---|------|
| G-1 | Ship a heuristic, deterministic `deck_ranker_service` that produces a per-user ranked list of decks (and optionally lessons) given the user's most recent ATS scan. |
| G-2 | Ship the missing "recent skill gaps" helper. Its shape is the **first** thing the ranker depends on; lock it before scoring. |
| G-3 | Reuse slice 6.5's filtered reads (`lesson_service.*`) — the ranker MUST NOT bypass persona/tier/archive invariants. The ranker is a re-orderer, not an authoriser. |
| G-4 | Cold-start safe: a Pro user with no scan must get a non-error response (the deterministic `display_order` ordering, surfaced as the same response shape with a `cold_start: true` flag or equivalent). |
| G-5 | BE-only this slice. No FE component. No new route mount path beyond what §6 specifies. No new analytics events per §12 D-11. |
| G-6 | Heuristic-only this slice. NO LLM call, NO embedding similarity, NO ML model. The scoring formula is pure SQL + Python arithmetic so it can be unit-tested deterministically. (Embedding-based ranking is reserved for a hypothetical slice 6.6b — not this slice's scope.) |

---

## 3. Non-goals (out-of-scope this slice)

- **No FE consumer.** Slice 6.7 ships the persona-aware Learn-page
  composition that mounts the ranker output. This slice ships only
  the BE service + Pydantic schemas + the BE route per §12 D-9.
- **No admin-facing ranking config.** No "weight tuning" admin UI.
  The scoring weights are constants in `deck_ranker_service.py`,
  changeable via PR + redeploy. Admin tuning is deferred until
  empirical signal that the heuristics are wrong.
- **No ML / embedding-based ranking.** §6 sticks to deterministic
  string-overlap + FSRS-state arithmetic per §12 D-1 / D-7. Embedding
  similarity is intentionally deferred to a hypothetical slice 6.6b
  (see §13).
- **No new persona-eligibility logic.** Slice 6.5 owns persona /
  tier / archive invariants. The ranker imports and reuses the
  shared helpers extracted to `app/services/curriculum_visibility.py`
  per §12 D-6 (`_visible_persona_set`, `_allowed_tiers_for_user`,
  `_persona_visible_to`).
- **No persistent ranking cache.** Ranking re-computes on every
  request per §12 D-12; the 12-deck universe is cheap.
- **No retroactive backfill of user_skill_gap rows.** §12 D-13
  locks the aggregated-read (A) helper shape; no materialised table,
  no backfill.
- **No cross-persona ranking.** This slice's ranker is per-user,
  honoring `users.persona`. §12 D-4 locks all-three-personas scope
  for v1 (one ranker, persona filter upstream).
- **No deletion of `gap_mapping_service.py`.** The legacy bridge
  remains live for `/api/v1/onboarding/recommendations`. Phase 6
  cleanup (slice 6.15) decides whether to retire it once the new
  ranker proves out.
- **No scoring of individual quiz_items.** v1 ranks decks per §12
  D-5; quiz_item ordering inside a lesson stays at slice 6.5's
  `display_order ASC, created_at ASC`.
- **No new Alembic migration** per §12 D-13.

---

## 4. Ranking model

This is the deliverable shape. Five sub-sections cover inputs,
scoring, output, cold-start, and the helper that bridges scans to
candidate decks.

### 4.1 Input signals

The ranker accepts the **user** plus an optional **lookback window**
and produces a ranked list. Inputs come from three sources:

| Source | Field | Use |
|--------|-------|-----|
| `users.persona` | enum: `interview_prepper` / `career_climber` / `team_lead` / null | Persona-visibility filter (delegated to slice 6.5's helpers). |
| `users.subscription` (best-effort, no lazy-load) | plan: `free` / `pro` / `enterprise` | Tier filter (delegated). |
| `tracker_applications_v2.analysis_payload` (deferred JSONB) | `skill_gaps[].skill` + `.importance` | The scoring signal. |
| `quiz_item_progress` (joined to quiz_items → lessons → decks) | `state`, `due_date`, `reps` | Per-deck progress signal (locked at §12 D-1 + D-3). |
| `decks.display_order` | int | Tie-break + cold-start ordering (§12 D-1). |
| `lessons.quality_score` | Numeric(3,2) nullable | Quality weight (locked at §12 D-1 + D-2). |

### 4.2 Scoring formula (heuristic v1)

The default v1 scoring formula is a weighted sum per deck. Weights
are constants in the service; locked at §12 D-1:

```
score(deck) = w_gap   * gap_match_score(deck, recent_gaps)
            + w_fsrs  * fsrs_due_score(deck, user)
            + w_qual  * avg_quality_score(deck)
            + w_order * (1 / display_order_rank(deck))
```

Where:

- `gap_match_score(deck, recent_gaps)` ∈ [0, 1]. **Locked at §12 D-7:**
  case-insensitive substring match of each gap's `skill` string against
  `deck.slug.replace('-', ' ')` + `deck.title`. Each matched gap
  contributes its importance weight (`critical=1.0`, `recommended=0.5`,
  `nice-to-have=0.25`); sum is normalised by the count of considered
  gaps. Lesson-title matching deferred per §12 D-8.
- `fsrs_due_score(deck, user)` ∈ [0, 1]. **Locked at §12 D-3:** linear
  `min(due_count, total_quiz_items) / total_quiz_items`, empty-deck
  floor 0.
- `avg_quality_score(deck)` ∈ [0, 1]. Average of `lessons.quality_score`
  across the deck's published, non-archived lessons. **Locked at §12
  D-2:** null-coerced to 0.5 (neutral) when zero lessons have a score.
- `display_order_rank(deck)` ∈ [1, N]. Rank within the persona+tier
  visible set, ascending by `display_order`. The reciprocal pulls
  curator-favoured decks up as a tie-break. v1 weight is small
  enough that it cannot overcome a strong gap-match.

**Default weights** (v1, locked at §12 D-1):

| Weight | Value | Rationale |
|--------|-------|-----------|
| `w_gap`   | 0.55 | Primary signal — what the user just told us they need. |
| `w_fsrs`  | 0.25 | Secondary — what they're already engaged with. |
| `w_qual`  | 0.10 | Tertiary — quality nudge, can be muted by null-coercion. |
| `w_order` | 0.10 | Tie-break — keeps cold-start parity with `display_order`. |

Sum is 1.0; final scores are in `[0, 1]`. Decks with `score == 0`
land last but are NOT filtered out — the user always sees the full
visible-deck universe (see §4.3 cold-start handling for the
zero-recent-gap case).

### 4.3 Output shape

The ranker returns a `RankedDecksResponse`:

```python
class RankedDeck(BaseModel):
    deck: DeckResponse              # full deck shape per slice 6.3
    score: float                    # [0, 1], 4-decimal precision
    rank: int                       # 1-indexed
    matched_gaps: list[str]         # gap.skill values that contributed
    score_breakdown: ScoreBreakdown # diagnostic

class ScoreBreakdown(BaseModel):
    gap_match: float
    fsrs_due: float
    avg_quality: float
    display_order_rank: float

class RankedDecksResponse(BaseModel):
    user_id: str
    persona: str | None
    cold_start: bool                # true iff no recent scan was found
    lookback_days: int              # the actual window used
    recent_gap_count: int           # number of distinct gaps fed into ranking
    ranked_at: datetime             # server-side computation timestamp
    decks: list[RankedDeck]         # ordered by score DESC, then display_order ASC
```

Per **§12 D-5**, `lessons` is NOT populated in v1 (`lessons=None` on
every response). The optional field is a forward-compat affordance
for a hypothetical slice 6.6b lesson-ranking surface.

### 4.4 Cold-start behaviour

Cold-start triggers when **either** the user has no scan history
OR the lookback window contains zero scans with non-null
`analysis_payload`. In that case:

- `cold_start = True`
- `recent_gap_count = 0`
- Decks are ordered by `display_order ASC` (within the
  persona/tier-visible set), `score = w_order * 1/rank` (gap signal
  is zero by definition; FSRS signal still fires if the user has
  any progress; quality signal still fires).
- The same response shape is returned. Callers can opt to render a
  "scan now to personalise" CTA based on `cold_start = True` — that
  behaviour is slice 6.7's concern.

### 4.5 Recent-skill-gaps helper (the bridge)

New helper, option (A) per scout R-2 + §12 D-13:

```python
async def get_recent_skill_gaps(
    user_id: str,
    db: AsyncSession,
    *,
    lookback_days: int = 30,
    max_scans: int = 5,
) -> list[SkillGap]:
    ...
```

Behaviour:

- SELECT from `tracker_applications_v2` WHERE `user_id = :user_id`
  AND `created_at >= now() - lookback_days::interval` AND
  `analysis_payload IS NOT NULL` ORDER BY `created_at DESC` LIMIT
  `max_scans`. **`undefer(TrackerApplicationModel.analysis_payload)`
  is required** because the column is `deferred()` per spec #59 §6.
- For each row, parse `analysis_payload['skill_gaps']` into
  `SkillGap` Pydantic instances. Skip rows whose payload is malformed
  or missing the field (logged at WARNING, not raised).
- Union and dedupe by `(skill.lower(), importance)`. Preserve the
  highest importance when the same skill string appears at multiple
  importance levels (`critical > recommended > nice-to-have`).
- Return ordered by `importance` DESC then alphabetical `skill` ASC
  for stable test assertions.

Cost (rough): a Pro user typically has 1-5 scans in a 30-day
window; each row yields ~10-30 gaps after dedup. The full helper
returns in O(50) Python objects per call — cheap.

Defaults `lookback_days=30`, `max_scans=5` per §12 D-14.

---

## 5. Pydantic schemas

New file: `app/schemas/ranker.py`. Reuses `app/schemas/deck.py`
(`DeckResponse`) and the existing `app/schemas/responses.py`
(`SkillGap`).

Five new shapes:

```python
# app/schemas/ranker.py
from datetime import datetime
from pydantic import BaseModel
from app.schemas.deck import DeckResponse
from app.schemas.lesson import LessonResponse  # forward-compat only — v1 leaves lessons=None per §12 D-5


class ScoreBreakdown(BaseModel):
    gap_match: float
    fsrs_due: float
    avg_quality: float
    display_order_rank: float


class RankedDeck(BaseModel):
    deck: DeckResponse
    score: float
    rank: int
    matched_gaps: list[str]
    score_breakdown: ScoreBreakdown


class RankedLesson(BaseModel):     # forward-compat shape only; v1 never populates per §12 D-5
    lesson: LessonResponse
    deck_id: str
    deck_slug: str
    score: float
    rank: int
    matched_gaps: list[str]


class RankedDecksResponse(BaseModel):
    user_id: str
    persona: str | None
    cold_start: bool
    lookback_days: int
    recent_gap_count: int
    ranked_at: datetime
    decks: list[RankedDeck]
    lessons: list[RankedLesson] | None = None   # always None in v1 per §12 D-5
```

The ranker does NOT define a request schema — input is driven by
the authenticated `User` object plus optional query params on the
route (per §12 D-9 + D-14).

---

## 6. BE service & route surface

### 6.1 New service: `app/services/deck_ranker_service.py`

Single public function plus the `get_recent_skill_gaps` bridge:

```python
async def rank_decks_for_user(
    user: User,
    db: AsyncSession,
    *,
    lookback_days: int = 30,
    max_scans: int = 5,
) -> RankedDecksResponse:
    """Rank persona/tier-visible decks for ``user`` using their most
    recent ATS scans as the dominant signal. Cold-start safe.
    """
    ...


async def get_recent_skill_gaps(
    user_id: str,
    db: AsyncSession,
    *,
    lookback_days: int = 30,
    max_scans: int = 5,
) -> list[SkillGap]:
    """Aggregated read of recent ATS scan skill_gaps. See §4.5."""
    ...
```

Internal helpers (private, leading underscore):

```python
def _gap_match_score(
    deck: Deck,
    recent_gaps: list[SkillGap],
) -> tuple[float, list[str]]:
    """Returns (score, matched_skill_strings) per §4.2."""

async def _fsrs_due_score(
    deck_id: str,
    user_id: str,
    db: AsyncSession,
) -> float:
    """Per-deck due-fraction signal. Single query joining
    quiz_item_progress → quiz_items → lessons WHERE
    deck_id = :deck_id AND user_id = :user_id.
    """

async def _avg_quality_score(deck_id: str, db: AsyncSession) -> float:
    """Mean of lessons.quality_score across published, non-archived
    lessons. Null-coerced to 0.5 when zero scored lessons.
    """

async def _list_visible_decks(
    db: AsyncSession,
    *,
    user: User,
) -> list[Deck]:
    """Imports `_visible_persona_set` + `_allowed_tiers_for_user`
    from `app/services/curriculum_visibility.py` per §12 D-6
    (slice 6.5 D-5 escape-hatch fired here). No public 'list
    visible decks' helper exists on lesson_service today.
    """
```

The ranker:

1. Loads recent gaps via `get_recent_skill_gaps`. Empty → `cold_start = True`.
2. Loads visible decks via `_list_visible_decks`.
3. For each deck, computes the four sub-scores. The FSRS query is
   batched (one query joining all visible decks) to avoid N+1 — see
   §10 test plan.
4. Sorts by `score DESC`, ties broken by `display_order ASC`.
5. Returns `RankedDecksResponse`.

The function is **idempotent and side-effect-free** — no database
writes, no analytics events fired (per §12 D-11). Callable from a
route handler, a script, or a future cache-warming job.

### 6.2 Route surface

Per §12 D-9: new endpoint `GET /api/v1/learn/ranked-decks` →
`RankedDecksResponse`. Auth required (`Depends(get_current_user)`).
Optional query params `?lookback_days=N&max_scans=M` (defaults from
§12 D-14).

New file `app/api/v1/routes/ranker.py` mounted at `/api/v1` in
`app/main.py` (mirrors slice 6.0's `lesson_view_events.py`
precedent). Returns:

- `200` with `RankedDecksResponse` on success.
- `401` if no auth (handled by `Depends(get_current_user)`).
- `400` if `lookback_days` is non-positive or `max_scans` is non-positive
  (Pydantic / FastAPI validation on query params).

No 403 path — the ranker reuses persona/tier filters and returns
the user's visible subset; an authenticated user always gets a
`200` (potentially with `cold_start: true`).

### 6.3 Reuse vs duplication of slice 6.5 helpers

Per §12 D-6: extract `_visible_persona_set`, `_allowed_tiers_for_user`,
`_persona_visible_to` into a new module
`app/services/curriculum_visibility.py` IN this slice's impl commit.
Slice 6.5 D-5 rule-of-three escape-hatch fires explicitly here
(ranker is the third consumer).

Concretely: `quiz_item_study_service.py` + `lesson_service.py` swap
their private duplicates for `from app.services.curriculum_visibility
import ...`; `deck_ranker_service.py` imports the same module.
Additive change, no behavioural delta. Spec #06 §6.3 inline note
re: deferring extraction is amended in lockstep at the impl commit
(not this amendment slice — amendment slices touch only spec #07).

---

## 7. Migration

**No migration this slice** per §12 D-13. The ranker is computed
live from existing tables; the recent-skill-gaps helper reads
`tracker_applications_v2.analysis_payload` JSONB at query time
with `undefer(...)` per spec #59 §6.

The (B) materialised `user_skill_gap` table alternative is locked
out of v1; revisit only if read latency posts a telemetry signal.

---

## 8. FE component graph

**No FE deliverable this slice.** Slice 6.7 ships the persona-aware
Learn-page composition that mounts `RankedDecksResponse` and
renders ranked decks above the deterministic browse list.

Forward-looking only (slice 6.7 will pick this up):

- `pages/StudyDashboard.tsx` (or its successor per slice 6.7)
  fetches `GET /api/v1/learn/ranked-decks` on mount when the user
  is any of the three personas (per §12 D-4).
- New `components/learn/RankedDeckRow.tsx` renders each
  `RankedDeck` with the `matched_gaps` chips + score chip.
- Cold-start branch renders a "Scan a JD to personalise this list"
  CTA card at the top, then the deterministic ordering below.

This slice ships zero FE. `tsc` baseline unchanged.

---

## 9. Analytics events declared by this slice

**Zero new events** per §12 D-11.

Rationale: the ranker is a server-side ordering primitive; user-facing
engagement events (`deck_recommended_clicked`, `ranked_list_viewed`)
naturally belong to slice 6.7 where the FE ships. Cost / latency
monitoring is covered by Sentry + structured logging at WARNING for
the helper's malformed-payload path (§12 D-16).

---

## 10. Test plan (implementation slice)

Two new test files. **No FE tests** (no FE surface).

### 10.1 `tests/test_deck_ranker_service.py` — service unit tests

Default-selector (`-m "not integration"`) tests covering the
heuristic and edge cases. Estimated **~14-18 tests**:

| # | Test | Purpose |
|---|------|---------|
| 1 | `test_rank_decks_cold_start_returns_display_order` | No scan history → `cold_start=True`, decks ordered by `display_order ASC`. |
| 2 | `test_rank_decks_cold_start_response_shape_correct` | `cold_start=True` response has `recent_gap_count=0`, `lookback_days=30`. |
| 3 | `test_rank_decks_with_recent_scan_promotes_matching_deck` | Scan with skill_gap "RAG"; deck slug `llm-internals` with title containing "RAG"; ranks above non-matching decks. |
| 4 | `test_rank_decks_critical_importance_outweighs_recommended` | Two decks, one matches `critical` gap, one matches `recommended`; critical-match ranks higher even when both have same `display_order`. |
| 5 | `test_rank_decks_filters_archived_deck` | Archived deck excluded. |
| 6 | `test_rank_decks_filters_persona_narrowed_deck` | Climber-only deck not in `interview_prepper` user's response. |
| 7 | `test_rank_decks_filters_premium_for_free_user` | Premium-tier deck not in free user's response per §12 D-10. |
| 8 | `test_rank_decks_pro_user_sees_premium_decks` | Pro plan unlocks premium tier. |
| 9 | `test_rank_decks_fsrs_due_score_pulls_engaged_deck_up` | Two decks tied on gap-match; one has 5 due quiz_items, one has 0 → engaged deck ranks higher. |
| 10 | `test_rank_decks_quality_score_null_coerced_to_neutral` | Deck with no `quality_score` lessons gets `0.5` neutral score, not 0. |
| 11 | `test_rank_decks_zero_match_gap_does_not_filter` | Decks scoring 0 still appear at the bottom of the list (no filter). |
| 12 | `test_rank_decks_score_in_zero_to_one_range` | All scores ∈ [0, 1] across pathological inputs. |
| 13 | `test_rank_decks_stable_tiebreak_by_display_order` | Identical scores → `display_order ASC`. |
| 14 | `test_rank_decks_persona_null_user_falls_back_to_both_only` | User with `persona=NULL` sees only `persona_visibility='both'` decks. |
| 15 | `test_rank_decks_no_lazy_load_on_subscription` | `_resolve_plan`-style guard prevents async lazy-load (slice 6.2 / 6.5 pattern). |
| 16 | `test_get_recent_skill_gaps_dedupes_across_scans` | Same skill in two scans returns once. |
| 17 | `test_get_recent_skill_gaps_promotes_highest_importance` | Same skill at `recommended` then `critical` → `critical` wins. |
| 18 | `test_get_recent_skill_gaps_skips_malformed_payload` | Row with non-dict `analysis_payload` logged + skipped, not raised. |

### 10.2 `tests/test_ranker_routes.py` — route integration tests

Default-selector tests against the new endpoint (per §12 D-9).
Estimated **~5-8 tests**:

| # | Test | Purpose |
|---|------|---------|
| 1 | `test_get_ranked_decks_authed_returns_200` | Happy path. |
| 2 | `test_get_ranked_decks_unauthed_returns_401` | Auth gate. |
| 3 | `test_get_ranked_decks_cold_start_response_well_formed` | New user, no scans → 200, `cold_start=True`. |
| 4 | `test_get_ranked_decks_lookback_days_query_param_honored` | `?lookback_days=7` narrows the window. |
| 5 | `test_get_ranked_decks_invalid_lookback_returns_400` | `?lookback_days=-1` validation. |
| 6 | `test_get_ranked_decks_response_matches_pydantic_schema` | Schema-shape regression. |
| 7 | `test_get_ranked_decks_persona_changes_response` | PATCH persona then re-call → different visible set. |
| 8 | `test_get_ranked_decks_skips_unauthorized_via_persona_or_tier` | Doesn't leak premium decks to free users. |

Total estimated test addition: **~19-26 BE tests**. Bracket
expressed as `+15..+30` for impl-slice prompt envelope; within the
±10% R3 tolerance (max upper = 33).

### 10.3 Integration tests (`@pytest.mark.integration`)

None planned. The ranker is purely synchronous + DB-bound; no LLM
call, no external service. Per R13, no integration marker.

### 10.4 Regression set must stay green

- `tests/test_lesson_service_invariants.py` (slice 6.5 — 14 tests).
- `tests/test_quiz_item_study_service_invariants.py` (slice 6.5 — 11
  tests).
- Existing `tests/test_phase6_schema.py` (slice 6.1).

---

## 11. Acceptance criteria

- **AC-1** New file `app/services/deck_ranker_service.py` exists
  with public `rank_decks_for_user` + `get_recent_skill_gaps`
  signatures matching §6.1.
- **AC-2** New file `app/schemas/ranker.py` exists with
  `RankedDeck` + `RankedDecksResponse` + `ScoreBreakdown` +
  forward-compat `RankedLesson` shape (always unpopulated in v1
  per §12 D-5).
- **AC-3** New route `GET /api/v1/learn/ranked-decks` mounted in
  `app/main.py` per §12 D-9; returns `RankedDecksResponse` for
  authenticated callers.
- **AC-4** Ranker honours persona-visibility (no climber-only deck
  in interview_prepper user's response; no interview_prepper-only
  deck in climber's response).
- **AC-5** Ranker honours tier-gating (premium decks excluded for
  free user per §12 D-10; no `locked_decks` field).
- **AC-6** Ranker honours archive (no `archived_at IS NOT NULL`
  decks in response).
- **AC-7** Cold-start response has `cold_start=True`,
  `recent_gap_count=0`, decks ordered by `display_order ASC`,
  shape unchanged from happy path (per §4.4).
- **AC-8** Critical-importance gap ranks above recommended ranks
  above nice-to-have (per §4.2).
- **AC-9** FSRS-due signal pulls engaged decks up given equal
  gap-match scores.
- **AC-10** All scores ∈ [0, 1]; final ordering is `score DESC`
  with `display_order ASC` tiebreak.
- **AC-11** `get_recent_skill_gaps` dedupes by `(skill.lower(),
  importance)` and prefers higher importance on collision.
- **AC-12** No analytics events emitted (per §12 D-11).
- **AC-13** No FE files touched. `tsc --noEmit` baseline unchanged
  from `bcb1085`.
- **AC-14** No new Alembic migration (per §12 D-13).
- **AC-15** Slice 6.5 invariant tests (`test_lesson_service_invariants`,
  `test_quiz_item_study_service_invariants`) all green post-impl.

---

## 12. Decisions

> Locked at §12 amendment `<this-slice>` from §14 OQ-1..OQ-11 + sub-OQs
> (mirrors slice 6.0 `e8eecdd` / slice 6.4.5 `df58eaf` / slice 6.5
> `acba7ed` precedent). Each D-N below resolves the like-numbered §14
> OQ; §14 retains the question + RESOLVED pointer back here for
> traceability.

**D-1 (resolves OQ-1) — ranking signals subset = all four (gap-match
+ FSRS-due + quality + display_order)** per author hint (a). Default
weights `(w_gap, w_fsrs, w_qual, w_order) = (0.55, 0.25, 0.10, 0.10)`
per §4.2 (sum = 1.0; final scores in [0, 1]). Adding signals later is
cheap; removing them is a strict regression in personalisation.

**D-2 (resolves OQ-1b) — `lessons.quality_score` null-coercion =
neutral 0.5** per author hint (a). Per-deck average over published,
non-archived lessons; if zero scored lessons, fall back to 0.5 (no
penalty for new content). Slice 6.13.5 may swap `_avg_quality_score`
for an `avg_critique_score` term without changing this lock.

**D-3 (resolves OQ-1c) — FSRS-due score = linear `min(due_count,
total_quiz_items) / total_quiz_items`** per author hint (a). ∈ [0, 1].
Empty deck (`total_quiz_items == 0`) coerces to 0. Sigmoid /
constant-bucket alternatives (b)/(c) deferred — revisit only if v1
visibly mis-ranks micro vs macro decks.

**D-4 (resolves OQ-2) — persona scope = all three personas** per
author hint (a). Ranker is a generic re-orderer; persona filtering is
enforced upstream by `_visible_persona_set`. Same heuristic applies
to climber + team_lead. Scout's "Interview Prepper" framing is the
**dominant** consumer (per slice 6.7's FE composition) but not the
**exclusive** persona — the BE primitive is persona-agnostic.

**D-5 (resolves OQ-3) — output shape = decks-only** per author hint (a).
`RankedDecksResponse.lessons` field stays unpopulated (the optional
field in §5 is a forward-compat affordance; v1 always returns
`lessons=None`). Lesson-level cross-deck ranking is reserved for a
hypothetical slice 6.6b. Inside-deck lesson order remains slice 6.5's
`display_order ASC, created_at ASC`.

**D-6 (resolves OQ-3b) — extract `_visible_persona_set` /
`_allowed_tiers_for_user` / `_persona_visible_to` to
`app/services/curriculum_visibility.py` IN this slice's impl commit**
per author hint (a). Slice 6.5 D-5 escape-hatch fires explicitly here
— third consumer materialised. Extraction is additive (no behavioural
delta): `quiz_item_study_service.py` + `lesson_service.py` swap their
private duplicates for `from app.services.curriculum_visibility
import ...`; `deck_ranker_service.py` imports the same module. The
slice 6.5 inline note re: deferring extraction is amended in lockstep
at impl commit, not this amendment.

**D-7 (resolves OQ-4) — gap → deck matching = case-insensitive
substring against `decks.slug.replace('-', ' ')` + `decks.title`** per
author hint (a). No schema work, deterministic, unit-testable.
Tags-column (b) and embedding (c) alternatives deferred to slice 6.6b
if v1 recall is empirically too low. The match function's substring
check is `gap.skill.lower() in haystack.lower()` over the
slug-as-words + title concatenation; tie-break uses importance
weights `critical=1.0`, `recommended=0.5`, `nice-to-have=0.25` per
§4.2.

**D-8 (resolves OQ-4b) — lesson-title matching NOT included in v1
deck score** per author hint (b). v1 stays deck-shell-only (slug +
title). Lesson-title matching is part of the OQ-3 (b) lesson-ranking
surface that D-5 deferred. Re-evaluate when slice 6.6b ships embedding
similarity (which subsumes lesson-title matching naturally).

**D-9 (resolves OQ-5) — new endpoint `GET /api/v1/learn/ranked-decks`**
per author hint (a). Clean separation; distinct response shape
(`RankedDecksResponse` vs `list[DeckResponse]`). Mirrors slice 6.0's
`/api/v1/lessons/:id/view-event` precedent of putting a Phase-6 verb
under `/api/v1/...` rather than overloading legacy `/decks` semantics.
Mounted in `app/main.py` from a new router file
`app/api/v1/routes/ranker.py`.

**D-10 (resolves OQ-6) — premium-deck visibility for free users =
filtered out** per author hint (a). Slice 6.5 D-2 / D-10 tier-gating
stays unchanged; the ranker re-orders the user's **visible** universe.
The "locked bucket" UX (b) trades a tier-leak (free user sees premium
deck slugs + matched gaps) for a marketing nudge — that trade
belongs to slice 6.7's FE composition layer if it surfaces at all,
not the BE ranker primitive. `RankedDecksResponse` carries no
`locked_decks` field; v1 schema is final.

**D-11 (resolves OQ-7) — zero new analytics events** per author hint
(a). Engagement events (`ranked_deck_clicked` etc.) live with slice
6.7's FE consumer. The ranker is a server-side ordering primitive;
emitting a backend event with no consumer dashboard is premature
instrumentation. Cost / latency monitoring is covered by Sentry +
existing structured logging at WARNING for the helper's
malformed-payload path (D-16).

**D-12 (resolves OQ-8) — no caching layer** per author hint (a). v1
re-computes on every request: O(60) gap-match comparisons + 1 FSRS
join + 1 quality query for the 12-deck universe. Redis caching is
revisited only if a slow-query telemetry signal materialises. Cache
invalidation on scan-write (which would trip every cached entry) is
itself non-trivial and the freshness loss vs latency win is
unattractive at v1's compute envelope.

**D-13 (resolves OQ-9) — recent-skill-gaps helper = aggregated read
of `tracker_applications_v2.analysis_payload`** per author hint (a)
(scout R-2 default). No schema work, no migration, no backfill, no
write-side hook. The `undefer(TrackerApplicationModel.analysis_payload)`
plumbing is required since the column is `deferred()` per spec #59
§6 — the helper applies it at query time. Materialised `user_skill_gap`
table (b) deferred until read latency posts a telemetry signal.

**D-14 (resolves OQ-9b) — defaults `lookback_days=30`, `max_scans=5`**
per author hint. Captures the typical "applying to interviews this
month" cadence; bounded Python work (~5 rows × ~10-30 gaps × dedup =
O(50) Pydantic objects). Aggressive recency (14 days / 3 scans) is
revisited only if user-reported staleness on the ranked output
materialises. Both values are constants in
`deck_ranker_service.py`; route exposes them as optional
`?lookback_days=N&max_scans=M` query params for ad-hoc tuning per
§6.2.

**D-15 (resolves OQ-10) — cold-start response carries `cold_start:
true` only; no copy hint** per author hint (a). Copy belongs in the
slice 6.7 FE consumer (where styling, i18n, and persona-aware
phrasing live). Mixing copy into the BE response shape is concerns
contamination — the BE primitive returns data, the FE renders.

**D-16 (resolves OQ-11) — partial-failure on `get_recent_skill_gaps`
= skip + log at WARNING** per author hint (a). A row whose
`analysis_payload` is malformed (non-dict, missing `skill_gaps`,
non-list `skill_gaps`) is logged via `logger.warning(...)` with the
`tracker_application_id` for diagnostic backtrace, then dropped from
the union. The helper continues processing remaining rows. Partial
recovery beats a 500 from one bad row; AC-11's dedup invariant is
unaffected (a missing row contributes zero gaps to the union).

---

## 13. Out of scope (deferred to other Phase-6 slices)

- **Slice 6.6b (hypothetical) — embedding-based ranking.** If
  string-overlap heuristics prove insufficient, a follow-up slice
  could add `lessons.embedding` (pgvector) + cosine similarity
  scoring against `SkillGap.skill` embeddings. Not pre-allocated;
  spawned only if heuristic v1 visibly underperforms.
- **Slice 6.7 — persona-aware Learn-page composition.** Owns the
  FE consumer of `RankedDecksResponse`. `<RankedDeckList>`
  component, `<ColdStartCard>` CTA, persona-branching mount in
  StudyDashboard / its successor.
- **Slice 6.10 — AI ingestion pipeline.** When new lessons are
  AI-generated, this ranker should re-rank inclusively without
  needing a deploy. Tested implicitly via the heuristic-only
  formula (no model dependency).
- **Slice 6.11 — FSRS retention dashboard.** Will read from
  `quiz_review_events` (slice 6.0) — orthogonal.
- **Slice 6.13.5 — `card_quality_signals`.** When AI-critique
  signals materialise, an `avg_critique_score` term could replace
  or augment `lessons.quality_score`. Out of scope here; the
  ranker's `_avg_quality_score` helper is a simple swap.
- **Slice 6.15 — Phase 6 cleanup.** Decides whether to retire
  `gap_mapping_service.py` (legacy `cards`/`categories` bridge).
  Not in scope here.
- **Admin tunable weights.** No admin UI for `(w_gap, w_fsrs,
  w_qual, w_order)` this slice. Constants live in the service.
- **Caching layer.** No Redis caching of ranked output. v1
  re-computes on every request.
- **Cross-deck ranking.** No "this lesson from deck A is more
  relevant than that lesson from deck B" — output is grouped
  per-deck per §12 D-5. Lesson-level cross-deck ordering is a
  hypothetical slice 6.6b surface.

---

## 14. Open questions

> All OQs locked at §12 amendment `<this-slice>` (mirrors slice 6.0
> `e8eecdd` / slice 6.4.5 `df58eaf` / slice 6.5 `acba7ed` precedent).
> Each OQ retains its question text + RESOLVED pointer to §12 D-N for
> traceability; option bodies + author hints have been replaced.

**OQ-1 — ranking signals subset for v1.** Scout §6 implies all four:
gap-match + FSRS-due + quality + display_order. Should v1 ship all
four, or start with a smaller subset?
RESOLVED — see §12 **D-1** (`<this-slice>`): all four signals at
default weights `(0.55, 0.25, 0.10, 0.10)`.

**OQ-1b — `lessons.quality_score` null-coercion.** Most rows will be
NULL until slice 6.13.5 ships.
RESOLVED — see §12 **D-2** (`<this-slice>`): null-coerce per-deck
average to neutral 0.5; no penalty for unscored content.

**OQ-1c — FSRS-due score shape.** Linear / sigmoid / capped count?
RESOLVED — see §12 **D-3** (`<this-slice>`): linear
`min(due_count, total_quiz_items) / total_quiz_items`, empty-deck
floor 0.

**OQ-2 — persona scope for v1.** Interview Prepper only or all three
personas?
RESOLVED — see §12 **D-4** (`<this-slice>`): all three personas;
ranker is persona-agnostic, persona filtering enforced upstream by
`_visible_persona_set`.

**OQ-3 — output shape (decks vs lessons vs both).**
RESOLVED — see §12 **D-5** (`<this-slice>`): decks-only;
`RankedDecksResponse.lessons` field stays unpopulated as a forward-
compat affordance; v1 always returns `lessons=None`.

**OQ-3b — slice 6.5 D-5 escape-hatch fire.** Extract
`_visible_persona_set` / `_allowed_tiers_for_user` /
`_persona_visible_to` to a shared module, or defer?
RESOLVED — see §12 **D-6** (`<this-slice>`): extract NOW into
`app/services/curriculum_visibility.py` in the impl commit; slice
6.5 D-5 escape-hatch fires explicitly here.

**OQ-4 — gap → deck matching strategy.**
RESOLVED — see §12 **D-7** (`<this-slice>`): case-insensitive
substring against `decks.slug.replace('-', ' ')` + `decks.title`;
no schema work. Tags-column / embedding alternatives deferred to
slice 6.6b.

**OQ-4b — extend matching to `lessons.title`.**
RESOLVED — see §12 **D-8** (`<this-slice>`): NO — v1 stays
deck-shell-only (slug + title). Lesson-title matching is part of
the OQ-3 (b) surface that D-5 deferred.

**OQ-5 — route shape.**
RESOLVED — see §12 **D-9** (`<this-slice>`): new endpoint
`GET /api/v1/learn/ranked-decks` mounted from new router file
`app/api/v1/routes/ranker.py`.

**OQ-6 — premium-deck visibility for free users.**
RESOLVED — see §12 **D-10** (`<this-slice>`): premium decks
filtered out for free users (slice 6.5 D-2 / D-10 tier-gating
unchanged); no `locked_decks` field on `RankedDecksResponse`.

**OQ-7 — analytics events.**
RESOLVED — see §12 **D-11** (`<this-slice>`): zero new events.
Engagement events live with slice 6.7's FE consumer; cost / latency
monitoring covered by Sentry + WARNING-level logging on the
helper's malformed-payload path (D-16).

**OQ-8 — caching strategy.**
RESOLVED — see §12 **D-12** (`<this-slice>`): no caching layer.
Re-compute on every request; revisit only if slow-query telemetry
signal materialises.

**OQ-9 — recent-skill-gaps helper shape (scout R-2 lock).**
RESOLVED — see §12 **D-13** (`<this-slice>`): aggregated read of
`tracker_applications_v2.analysis_payload` (scout R-2 default
(A)); `undefer(...)` plumbing required at query time. No schema
work, no migration, no backfill.

**OQ-9b — `lookback_days` + `max_scans` defaults.**
RESOLVED — see §12 **D-14** (`<this-slice>`): `lookback_days=30`,
`max_scans=5`; route exposes both as optional `?lookback_days=N&max_scans=M`
query params per §6.2.

**OQ-10 — cold-start response copy.**
RESOLVED — see §12 **D-15** (`<this-slice>`): BE returns
`cold_start: true` only; no copy hint. Copy lives with slice 6.7
FE consumer (i18n + persona-aware phrasing).

**OQ-11 — error shape on partial failure.**
RESOLVED — see §12 **D-16** (`<this-slice>`): skip + log at
WARNING with `tracker_application_id`; helper continues processing
remaining rows. AC-11 dedup invariant unaffected by skips.

---

## 15. Implementation slice forward-link

Implementation row: **B-074** 🔴 (filed by this slice).

Forward dependencies before impl can start:

1. **§12 amendment slice** locked D-1..D-16 from §14 OQ-1..OQ-11 +
   sub-OQs at `<this-slice>` (mirrors slice 6.0 / 6.4.5 / 6.5
   pattern at `e8eecdd` / `df58eaf` / `acba7ed`). ✅ shipped.
2. Scout R-2 lock — defaults match scout R-2 (option (A) aggregated
   read) per §12 D-13; no pre-impl migration slice needed.

Impl slice expected scope:

- New file `app/services/deck_ranker_service.py` (~250 lines).
- New file `app/schemas/ranker.py` (~50 lines).
- New file `app/api/v1/routes/ranker.py` (~50 lines) per §12 D-9.
- New file `app/services/curriculum_visibility.py` (~30 lines) per
  §12 D-6 (slice 6.5 D-5 escape-hatch extraction).
- `app/main.py` route mount line addition.
- Two new test files (§10).
- BACKLOG B-074 closure with impl SHA.
- SESSION-STATE Recently Completed entry.
- CODE-REALITY targeted regen at impl close (new service +
  schema + route surface).

Impl test envelope: BE **612 → 631..645** (`+19..+33`); FE 375
unchanged.
