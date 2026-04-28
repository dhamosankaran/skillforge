# Phase 6 — Slice 6.6: Lens-Ranked Deck/Lesson Ordering for Interview Prepper

## Status: Drafted — §12 awaits amendment slice locking D-1..D-N from §14 OQ-1..OQ-N

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

   Scout default is (A); §14 OQ-9 confirms or flips.

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
| G-5 | BE-only this slice. No FE component. No new route mount path beyond what §6 specifies. No new analytics events unless §14 OQ-7 locks otherwise. |
| G-6 | Heuristic-only this slice. NO LLM call, NO embedding similarity, NO ML model. The scoring formula is pure SQL + Python arithmetic so it can be unit-tested deterministically. (Embedding-based ranking is reserved for a hypothetical slice 6.6b — not this slice's scope.) |

---

## 3. Non-goals (out-of-scope this slice)

- **No FE consumer.** Slice 6.7 ships the persona-aware Learn-page
  composition that mounts the ranker output. This slice ships only
  the BE service + Pydantic schemas + (per §14 OQ-5) the BE route.
- **No admin-facing ranking config.** No "weight tuning" admin UI.
  The scoring weights are constants in `deck_ranker_service.py`,
  changeable via PR + redeploy. Admin tuning is deferred until
  empirical signal that the heuristics are wrong.
- **No ML / embedding-based ranking.** §6 sticks to deterministic
  string-overlap + FSRS-state arithmetic. Embedding similarity is
  evaluated as a candidate signal in §14 OQ-1 and intentionally
  deferred.
- **No new persona-eligibility logic.** Slice 6.5 owns persona /
  tier / archive invariants. The ranker imports and reuses
  `lesson_service._visible_persona_set`,
  `lesson_service._allowed_tiers_for_user`, and
  `lesson_service._persona_visible_to` (or accepts pre-filtered
  inputs from `list_lessons_in_deck`-style callers — locked at §14
  OQ-3).
- **No persistent ranking cache.** Ranking re-computes on every
  request unless §14 OQ-8 locks otherwise. (Default per author hint:
  no cache; ranking is cheap given the 12-deck universe.)
- **No retroactive backfill of user_skill_gap rows.** The §14 OQ-9
  default (A) avoids the materialised table; if §14 OQ-9 flips to
  (B), the backfill scope is added in the §12 amendment slice and
  remains separate from the ranker logic.
- **No cross-persona ranking.** This slice's ranker is per-user,
  honoring `users.persona`. A future "team_lead" or "career_climber"
  ranker shape may diverge — §14 OQ-2 confirms whether v1 covers
  all three personas or scopes to Interview Prepper only.
- **No deletion of `gap_mapping_service.py`.** The legacy bridge
  remains live for `/api/v1/onboarding/recommendations`. Phase 6
  cleanup (slice 6.15) decides whether to retire it once the new
  ranker proves out.
- **No scoring of individual quiz_items.** v1 ranks decks (and
  optionally lessons via §14 OQ-3); quiz_item ordering inside a
  lesson stays at slice 6.5's `display_order ASC, created_at ASC`.
- **No new Alembic migration** unless §14 OQ-9 flips to option (B)
  (the materialised table). Default is no migration.

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
| `quiz_item_progress` (joined to quiz_items → lessons → decks) | `state`, `due_date`, `reps` | Per-deck progress signal (locked at §14 OQ-1). |
| `decks.display_order` | int | Tie-break + cold-start ordering. |
| `lessons.quality_score` | Numeric(3,2) nullable | Optional weight (locked at §14 OQ-1). |

### 4.2 Scoring formula (heuristic v1)

The default v1 scoring formula is a weighted sum per deck. Weights
are constants in the service; locked in §12 from §14 OQ-1:

```
score(deck) = w_gap   * gap_match_score(deck, recent_gaps)
            + w_fsrs  * fsrs_due_score(deck, user)
            + w_qual  * avg_quality_score(deck)
            + w_order * (1 / display_order_rank(deck))
```

Where:

- `gap_match_score(deck, recent_gaps)` ∈ [0, 1]. v1 default
  (locked at §14 OQ-4): case-insensitive substring match of each
  gap's `skill` string against the deck's `slug` and `title`. Each
  matched gap contributes its importance weight (`critical=1.0`,
  `recommended=0.5`, `nice-to-have=0.25`); sum is normalised by the
  count of considered gaps. Optional v1.b extension to `lessons.title`
  inside the deck — see OQ-4.
- `fsrs_due_score(deck, user)` ∈ [0, 1]. The fraction of the
  deck's quiz_items that are currently due (`due_date <= now`) for
  this user, OR a sigmoid-of-due-count if a non-monotonic shape is
  preferred. v1 default: linear `due_count / total_quiz_items`,
  capped at 1.0. **Locked at §14 OQ-1c.**
- `avg_quality_score(deck)` ∈ [0, 1]. Average of `lessons.quality_score`
  across the deck's published, non-archived lessons; null-coerced to 0.5
  (neutral) when zero lessons have a score. **Locked at §14 OQ-1b.**
- `display_order_rank(deck)` ∈ [1, N]. Rank within the persona+tier
  visible set, ascending by `display_order`. The reciprocal pulls
  curator-favoured decks up as a tie-break. v1 weight is small
  enough that it cannot overcome a strong gap-match.

**Default weights** (v1, OQ-1):

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

**§14 OQ-3** decides whether `lessons` is also surfaced (either
nested under each `RankedDeck` as a sorted `list[LessonResponse]`,
or as a separate top-level `lessons: list[RankedLesson]`).

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

New helper, default option (A) per scout R-2 + §14 OQ-9:

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

§14 OQ-9 confirms the `lookback_days` + `max_scans` defaults; the
bridge implementation does not change between (A) and (B).

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
from app.schemas.lesson import LessonResponse  # only if §14 OQ-3 includes lessons


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


class RankedLesson(BaseModel):     # only if §14 OQ-3 ships lessons
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
    lessons: list[RankedLesson] | None = None   # populated only if OQ-3 (b)
```

The ranker does NOT define a request schema — input is driven by
the authenticated `User` object plus optional query params on the
route (per §14 OQ-5 + §14 OQ-9).

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
    """Reuses lesson_service._visible_persona_set +
    _allowed_tiers_for_user. **Does not** call lesson_service
    itself (no public 'list visible decks' there today); imports
    the helpers directly per §14 OQ-3 (a).
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
writes, no analytics events fired (unless §14 OQ-7 flips). Callable
from a route handler, a script, or a future cache-warming job.

### 6.2 Route surface

§14 OQ-5 picks one of three options:

- **(a)** New endpoint: `GET /api/v1/learn/ranked-decks` →
  `RankedDecksResponse`. Auth required (`Depends(get_current_user)`).
  Optional query params `?lookback_days=N&max_scans=M`.
  **Author-hint default.**
- **(b)** Extend existing endpoint: `GET /api/v1/decks?sort=recommended`.
  Adds an opt-in flag to the existing list endpoint.
- **(c)** Both — `(a)` for the rich response shape, `(b)` for a
  thin re-ordering convenience.

Default (a). Implication: new file `app/api/v1/routes/ranker.py`
mounted at `/api/v1` in `app/main.py` (mirrors slice 6.0's
`lesson_view_events.py` precedent). Returns:

- `200` with `RankedDecksResponse` on success.
- `401` if no auth (handled by `Depends(get_current_user)`).
- `400` if `lookback_days` is non-positive or `max_scans` is non-positive
  (Pydantic / FastAPI validation on query params).

No 403 path — the ranker reuses persona/tier filters and returns
the user's visible subset; an authenticated user always gets a
`200` (potentially with `cold_start: true`).

### 6.3 Reuse vs duplication of slice 6.5 helpers

Per §14 OQ-3 default (a): import `_visible_persona_set`,
`_allowed_tiers_for_user`, `_persona_visible_to` directly from
`lesson_service`. Do NOT duplicate them into
`deck_ranker_service.py`. The rule-of-three threshold is now
tripped — slice 6.5 D-5 escape hatch fires on this slice. **§14
OQ-3 confirms whether to honor D-5 by extracting helpers to a
new `app/services/curriculum_visibility.py` module IN this
slice's commit, or defer the extraction to a follow-up.**

If the extraction lands in this slice: spec #06 §6.3 + slice 6.5
service files get one-line `from app.services.curriculum_visibility
import ...` imports; this is an additive change, no behavioural
delta. If deferred: slice 6.6 imports from `lesson_service`; a
follow-up slice extracts the module.

---

## 7. Migration

**Default: no migration this slice.** The ranker is computed live
from existing tables. §14 OQ-9 confirms.

If §14 OQ-9 flips to option (B) materialised `user_skill_gap`
table:

- New table: `user_skill_gap (id PK, user_id FK CASCADE, scan_id
  String(36) FK nullable, skill String(200), category String(50),
  importance String(20), source_created_at DateTime, created_at
  DateTime default now())`.
- Indexes: `(user_id, source_created_at DESC)` for the recent-N
  query; `(user_id, skill)` for dedup.
- Backfill migration: iterate `tracker_applications_v2` rows with
  non-null `analysis_payload`, populate `user_skill_gap`. Out of
  scope: backfill is bundled into the §12 amendment slice if (B)
  is chosen.

The §12 amendment slice locks (A) or (B) before impl starts. No
mid-slice migration authoring.

---

## 8. FE component graph

**No FE deliverable this slice.** Slice 6.7 ships the persona-aware
Learn-page composition that mounts `RankedDecksResponse` and
renders ranked decks above the deterministic browse list.

Forward-looking only (slice 6.7 will pick this up):

- `pages/StudyDashboard.tsx` (or its successor per slice 6.7)
  fetches `GET /api/v1/learn/ranked-decks` on mount when the user
  is `interview_prepper` (or all personas, per §14 OQ-2).
- New `components/learn/RankedDeckRow.tsx` renders each
  `RankedDeck` with the `matched_gaps` chips + score chip.
- Cold-start branch renders a "Scan a JD to personalise this list"
  CTA card at the top, then the deterministic ordering below.

This slice ships zero FE. `tsc` baseline unchanged.

---

## 9. Analytics events declared by this slice

**Default: zero new events** (locked at §14 OQ-7 author hint (a)).

Rationale: the ranker is a server-side ordering primitive; user-facing
engagement events (`deck_recommended_clicked`, `ranked_list_viewed`)
naturally belong to slice 6.7 where the FE ships. Premature instrumentation
at the BE creates events with no consumer dashboards.

If §14 OQ-7 flips to (b): add a single backend-emitted
`deck_ranking_computed` event with payload
`{user_id, persona, cold_start, recent_gap_count, ranked_count,
top_deck_slug, computation_ms}` for diagnostic / cost monitoring.
Catalog row goes in `.agent/skills/analytics.md`.

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
| 7 | `test_rank_decks_filters_premium_for_free_user` | Premium-tier deck not in free user's response (or surfaces in a separate "locked" bucket per §14 OQ-6). |
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

Default-selector tests against the new endpoint (per §14 OQ-5 (a)).
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
  `RankedDeck` + `RankedDecksResponse` + `ScoreBreakdown` (and
  `RankedLesson` if §14 OQ-3 flips).
- **AC-3** New route `GET /api/v1/learn/ranked-decks` mounted in
  `app/main.py`; returns `RankedDecksResponse` for authenticated
  callers (§14 OQ-5 (a) default).
- **AC-4** Ranker honours persona-visibility (no climber-only deck
  in interview_prepper user's response; no interview_prepper-only
  deck in climber's response).
- **AC-5** Ranker honours tier-gating (premium decks excluded for
  free user unless §14 OQ-6 carves a "locked" bucket).
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
- **AC-12** No analytics events emitted (default §14 OQ-7 (a)) OR
  exactly one `deck_ranking_computed` event per call ((b)).
- **AC-13** No FE files touched. `tsc --noEmit` baseline unchanged
  from `bcb1085`.
- **AC-14** No new Alembic migration (default §14 OQ-9 (A)) OR
  exactly one `user_skill_gap` migration ((B)) — locked at §12
  amendment slice, not in flight.
- **AC-15** Slice 6.5 invariant tests (`test_lesson_service_invariants`,
  `test_quiz_item_study_service_invariants`) all green post-impl.

---

## 12. Decisions

> **Empty initially.** Locked decisions D-1..D-N are filled by the
> §12 amendment slice (mirrors slice 6.0 / 6.4.5 / 6.5 spec slice
> 2/2 precedent at `e8eecdd` / `df58eaf` / `acba7ed`). Until then,
> §14 OQs hold the live design call.

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
  per-deck. Lesson-level cross-deck ordering is §14 OQ-3 (b)
  surface.

---

## 14. Open questions

> Author-hint disposition is per-question. Locked at §12 amendment
> slice. **Each OQ that locks becomes a D-N entry.**

**OQ-1 — ranking signals subset for v1.** Scout §6 implies all
four: gap-match + FSRS-due + quality + display_order. Should v1
ship all four, or start with gap-match + display_order only and
add FSRS+quality in a follow-up?

- **Author hint (a):** all four. The four are cheap to add up-front;
  removing them later is a strict regression in personalisation.
- (b) gap-match + display_order only. Smaller surface, faster to
  ship. Adds FSRS+quality in a 6.6.5 follow-up.

**OQ-1b — quality_score null-coercion.** `lessons.quality_score`
is `Numeric(3,2) NULLABLE` and most rows will be NULL until
slice 6.13.5 ships. What's the v1 behaviour?

- **Author hint (a):** null-coerce per-deck average to **0.5**
  (neutral). Decks with no scores get a neutral nudge, not penalised.
- (b) Coerce to 0 (penalty for unscored). Risks penalising new
  content.
- (c) Drop the term entirely until slice 6.13.5. `w_qual = 0` for
  v1; flip in a follow-up.

**OQ-1c — FSRS-due score shape.** Linear `due / total`?
Sigmoid (saturating)? Capped count?

- **Author hint (a):** linear `min(due_count, total_quiz_items) /
  total_quiz_items`. Cheap, intuitive, ∈ [0, 1]. Cap floor at 0
  for empty deck.
- (b) Sigmoid with k=10 around the median deck size — non-monotonic
  but more "balanced" between micro and macro decks.
- (c) Constant 0.5 if user has any progress on the deck else 0.

**OQ-2 — persona scope for v1.** Scout line 945 says "Lens-ranked
deck/card ordering for **Interview Prepper**" — should v1 only
serve interview_prepper users, or all three personas?

- **Author hint (a):** all three personas. The ranker is a generic
  re-orderer; persona filtering is enforced upstream by
  `_visible_persona_set`. The same heuristic applies to climber
  + team_lead.
- (b) Interview Prepper only. Other personas get an HTTP 200 with
  `cold_start: true` regardless. Tighter scope; defers
  career_climber + team_lead surfaces to a future slice.

**OQ-3 — output shape (decks vs lessons vs both).** Does v1 ship
ranked decks only, ranked lessons only, or both?

- **Author hint (a):** decks only. Lesson-level ranking inside a
  deck is `display_order ASC` per slice 6.5; cross-deck lesson
  ranking is a slice 6.6b candidate.
- (b) Both — `RankedDecksResponse.decks` + `.lessons`. Larger
  payload; the `lessons` list is independent (not nested under
  decks).
- (c) Lessons only — decks become a derived grouping. Riskier
  shape change for slice 6.7's consumer.

**OQ-3b — slice 6.5 D-5 escape-hatch fire.** With the ranker
becoming the **third** consumer of `_visible_persona_set` /
`_allowed_tiers_for_user` / `_persona_visible_to`, slice 6.5
D-5's rule-of-three threshold is tripped. Extract helpers in
this slice or defer?

- **Author hint (a):** extract NOW into
  `app/services/curriculum_visibility.py`. Slice 6.5 commit body
  already documented this would be the trigger.
- (b) Defer to a 6.6-follow-up. Faster ranker ship; trades cohesion.

**OQ-4 — gap → deck matching strategy.** How does a `SkillGap.skill`
string match a deck?

- **Author hint (a):** case-insensitive substring against
  `decks.slug.replace('-', ' ')` + `decks.title`. Cheap, deterministic,
  no schema work. Matches "rag" → "Retrieval-Augmented Generation"
  deck via title.
- (b) Add `decks.skill_tags JSONB` column + Alembic migration;
  curators populate it. Better precision; schema cost.
- (c) Embedding similarity (`pgvector`) on a per-deck embedding.
  Best precision; large schema + ingestion cost.

**OQ-4b — extend matching to `lessons.title`.** Inside a deck,
should we also boost decks whose lessons (not just the deck shell)
match the gap?

- (a) Yes — sum lesson-title matches into the deck's gap_match
  score. Improves recall when deck title is generic (e.g.
  "ML Fundamentals" with lessons "RAG", "Embeddings", "LoRA").
- **Author hint (b):** no — keep v1 deck-shell-only. Lesson-title
  matching is part of OQ-3 (b) lesson-ranking surface.

**OQ-5 — route shape.** New endpoint or extend existing?

- **Author hint (a):** new `GET /api/v1/learn/ranked-decks`. Clean
  separation, distinct response shape.
- (b) Extend `GET /api/v1/decks?sort=recommended`. Reuses URL but
  returns different shape (`RankedDecksResponse` vs `list[DeckResponse]`)
  — either ugly polymorphism or the same shape with optional
  ranking fields.
- (c) Both.

**OQ-6 — premium-deck visibility for free users.** Slice 6.5
filters premium decks **out** for free users. The ranker's job is
"show me what's relevant" — should free users see premium decks
in a "locked" bucket so they know what's available?

- **Author hint (a):** keep slice 6.5 filtering — premium decks
  excluded entirely for free users. The ranker is a re-orderer of
  the user's visible universe.
- (b) Surface premium decks in a separate `locked_decks: list[RankedDeck]`
  field. UX nudge for upgrade. Trades a tier-leak (free user sees
  deck names + matched_gaps for premium content).

**OQ-7 — analytics events.** Zero new events (server-side
ranker), or one diagnostic event?

- **Author hint (a):** zero. Engagement events live with slice 6.7's
  FE consumer.
- (b) One: `deck_ranking_computed { user_id, persona, cold_start,
  recent_gap_count, ranked_count, top_deck_slug, computation_ms }`
  for cost monitoring.

**OQ-8 — caching strategy.** Re-compute on every request, or cache
per user with TTL?

- **Author hint (a):** no cache. The 12-deck universe + Pro user's
  ~5 recent scans = O(60) gap-match comparisons + 1 FSRS join +
  1 quality query per request. Cheap.
- (b) Redis cache keyed by `(user_id, last_scan_id)` with 24h TTL.
  Trades freshness for compute. Worth revisiting if `(b)` ever
  posts a slow-query telemetry signal.

**OQ-9 — recent-skill-gaps helper shape (scout R-2 lock).**

- **Author hint (a):** aggregated read iterating
  `tracker_applications_v2.analysis_payload`. No schema work.
  Per scout default.
- (b) Materialised `user_skill_gap` table + write-side hook on
  `analyze` + backfill migration. Faster reads; schema cost.

**OQ-9b — `lookback_days` + `max_scans` defaults.** What's the
default lookback window?

- **Author hint:** `lookback_days=30`, `max_scans=5`. Captures the
  typical "applying to interviews this month" cadence; bounded
  Python work.
- Alternative: `lookback_days=14`, `max_scans=3` (more aggressive
  recency bias).

**OQ-10 — cold-start response copy.** Does the BE response
include any "scan a JD to personalise" copy hint, or is that
purely the FE consumer's concern?

- **Author hint (a):** purely FE concern. BE returns
  `cold_start: true` only.
- (b) BE includes a copy hint string. Ugly mixing of concerns; not
  recommended.

**OQ-11 — error shape on partial failure.** If `get_recent_skill_gaps`
encounters a malformed JSONB payload, should the whole call fail or
should it skip the malformed row?

- **Author hint (a):** skip + log at WARNING. Partial recovery
  beats a 500 from one bad row. AC-11 implicit.
- (b) Raise. Forces upstream to surface payload-corruption as an
  HTTP 500 — louder, but worse UX.

---

## 15. Implementation slice forward-link

Implementation row: **B-074** 🔴 (filed by this slice).

Forward dependencies before impl can start:

1. **§12 amendment slice** locks D-1..D-N from §14 OQ-1..OQ-11.
   Mirrors slice 6.0 / 6.4.5 / 6.5 pattern at `e8eecdd` / `df58eaf`
   / `acba7ed`.
2. Optional: scout R-2 lock — **defaults match scout R-2** so this
   slice does NOT carry that pre-spec lock as a separate slice
   unless §14 OQ-9 flips to (B) (in which case the §12 amendment
   slice writes the (B) story including the migration + backfill).

Impl slice expected scope:

- New file `app/services/deck_ranker_service.py` (~250 lines).
- New file `app/schemas/ranker.py` (~50 lines).
- New file `app/api/v1/routes/ranker.py` (~50 lines) per §14 OQ-5
  (a).
- Optional: new file
  `app/services/curriculum_visibility.py` (~30 lines) per §14
  OQ-3b (a) extraction.
- `app/main.py` route mount line addition.
- Two new test files (§10).
- BACKLOG B-074 closure with impl SHA.
- SESSION-STATE Recently Completed entry.
- CODE-REALITY targeted regen at impl close (new service +
  schema + route surface).

Impl test envelope: BE **612 → 631..645** (`+19..+33`); FE 375
unchanged.
