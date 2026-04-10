# SPEC: ATS Gap → Card Category Mapping

**Spec #:** 08
**Phase:** 1
**Status:** Done
**Branch:** `feature/p1-08-ats-card-mapping`

---

## Problem

The ATS scanner (Phase 0) produces a list of **skill gaps** — e.g.
`["RAG", "System Design", "Kubernetes"]` — that a user is missing
relative to a job description. The study engine (specs #04–#07) owns
a library of cards grouped by **category** (e.g. "ML Infrastructure",
"System Design") where each card carries a `tags` array.

Today, after a scan the user sees a flat list of gaps but has **no path
to study them**. There is no connection between a gap string and the
cards/categories that would actually teach it. This breaks the core
conversion loop described in `.agent/skills/ats-card-bridge.md`:

> scan → "you're weak in X" → here are cards

A user who scans a resume, sees "RAG" listed as a gap, and finds no way
to click through to RAG cards will churn before ever starting the
spaced-repetition loop.

---

## Solution

Introduce a **gap mapping service** that takes a list of ATS gap strings
and returns, for each gap, a ranked list of **recommended card
categories** (with a card count and match reason).

Mapping is done in two tiers:

1. **Tag join (primary, deterministic).** For each gap, look up cards
   whose `tags` JSON array contains a normalized form of the gap
   string, then aggregate by `category_id`. The category with the most
   matching cards wins; ties broken by `display_order`.
2. **pgvector similarity (fallback, optional).** If the tag join
   returns zero matches for a gap, embed the gap string via the
   existing `ai_service` embedder and run a cosine-similarity search
   against `cards.embedding`. Group the top-K nearest cards by
   category, return the top category with a `match_type: "semantic"`
   flag and a similarity score.

The service is consumed by a new onboarding endpoint
`POST /api/v1/onboarding/map-gaps` which the post-scan frontend calls
to render the "Start studying" screen.

No new tables are added. No model changes are required — `cards.tags`
(JSON) and `cards.embedding` (Vector(1536)) already exist.

---

## Acceptance Criteria

- [ ] **AC-1:** `POST /api/v1/onboarding/map-gaps` accepts
  `{ gaps: string[] }` (1–50 items) and returns a `GapMappingResponse`
  (schema below). Requires `Depends(get_current_user)`.

- [ ] **AC-2:** For each input gap, the tag-join tier runs first:
  cards are filtered by `LOWER(tag) = LOWER(gap)` across the JSON
  `tags` array, grouped by `category_id`, ordered by match count
  descending then `categories.display_order` ascending.

- [ ] **AC-3:** If the tag-join yields ≥ 1 matching category for a gap,
  the response item has `match_type: "tag"` and lists up to 3 recommended
  categories with `matched_card_count` per category.

- [ ] **AC-4:** If the tag-join yields zero matches **and** the request
  flag `use_semantic: true` is set (default `true`), the service runs a
  pgvector cosine-similarity search (`embedding <=> query_embedding`)
  over cards, takes the top 20 nearest, groups by category, and returns
  the top category with `match_type: "semantic"` and a `similarity_score`
  (0–1, higher = closer).

- [ ] **AC-5:** If both tiers return zero matches for a gap, the item is
  returned with `match_type: "none"` and `recommended_categories: []`.
  It is **not** dropped from the response.

- [ ] **AC-6:** Gap strings are normalized before matching: trimmed,
  collapsed whitespace, lowercased for comparison. The original string
  is echoed back as `gap` in the response.

- [ ] **AC-7:** The endpoint fires PostHog event `gaps_mapped` with
  `{ gap_count, tag_matches, semantic_matches, none_matches }`.

- [ ] **AC-8:** Unknown gap input (empty string, > 100 chars) returns
  HTTP 422 via Pydantic validation.

- [ ] **AC-9:** Unauthenticated requests return 401. Requests with more
  than 50 gaps return 422.

- [ ] **AC-10:** The mapping service is pure business logic in
  `app/services/gap_mapping_service.py` — routes call the service, the
  service owns DB access and embedding calls. No ORM queries in routes.

---

## Mapping Service API

**File:** `app/services/gap_mapping_service.py`

```python
class GapMappingService:
    def __init__(self, db: AsyncSession, ai: AIService): ...

    async def map_gaps(
        self,
        gaps: list[str],
        *,
        use_semantic: bool = True,
        max_categories_per_gap: int = 3,
    ) -> list[GapMapping]:
        """Return one GapMapping per input gap, preserving order."""

    async def _match_by_tags(
        self, normalized_gap: str
    ) -> list[CategoryMatch]:
        """Tag-join tier. Returns matches grouped by category."""

    async def _match_by_embedding(
        self, gap: str
    ) -> list[CategoryMatch]:
        """Semantic fallback tier. Embeds gap, runs pgvector search."""
```

### Why a service class (not loose functions)?
- Holds the `AsyncSession` and `AIService` dependencies injected once.
- Keeps the two-tier strategy in one place for testing.
- Matches the pattern used by `study_service.py` and `card_service.py`.

---

## How Gaps Map to Categories

### Tier 1 — Tag join (primary)

```sql
-- Conceptual; actual query uses SQLAlchemy + JSON containment.
SELECT
    c.category_id,
    COUNT(*) AS matched_card_count
FROM cards c
WHERE EXISTS (
    SELECT 1
    FROM jsonb_array_elements_text(c.tags::jsonb) AS tag
    WHERE LOWER(tag) = LOWER(:gap)
)
GROUP BY c.category_id
ORDER BY matched_card_count DESC;
```

- Input gap `"RAG"` → matches cards with tag `"RAG"` or `"rag"`.
- Grouped by `category_id`, joined to `categories` for `name`, `icon`,
  `color`, `display_order`.
- Returned list is truncated to `max_categories_per_gap` (default 3).

### Tier 2 — pgvector similarity (fallback)

- Triggered only when Tier 1 returns `[]`.
- Embed the gap string via `ai_service.embed_text(gap)` → 1536-dim vector.
- Query:

```sql
SELECT
    c.id,
    c.category_id,
    1 - (c.embedding <=> :query_vec) AS similarity
FROM cards c
WHERE c.embedding IS NOT NULL
ORDER BY c.embedding <=> :query_vec
LIMIT 20;
```

- Group the 20 nearest cards by `category_id`, pick the group with the
  highest average similarity, return that single category with
  `match_type: "semantic"` and `similarity_score` = the group's top card
  similarity.
- Embedding calls are cached in-memory per request (same gap string
  within one request → one embed call).

### Tie-breaking rules

| Situation | Rule |
|---|---|
| Two categories, equal `matched_card_count` | Lower `categories.display_order` wins |
| Semantic tier finds no card with embedding | Return `match_type: "none"` |
| Gap matches `> max_categories_per_gap` categories | Truncate after sort |

---

## API Endpoint

**Route:** `POST /api/v1/onboarding/map-gaps`
**File:** `app/api/routes/onboarding.py`
**Auth:** `Depends(get_current_user)`

### Request schema — `GapMappingRequest`

```json
{
  "gaps": ["RAG", "System Design", "Kubernetes"],
  "use_semantic": true
}
```

| Field | Type | Validation |
|---|---|---|
| `gaps` | `list[str]` | 1–50 items, each 1–100 chars |
| `use_semantic` | `bool` | default `true` |

### Response schema — `GapMappingResponse`

```json
{
  "results": [
    {
      "gap": "RAG",
      "match_type": "tag",
      "recommended_categories": [
        {
          "category_id": "c1f...",
          "name": "ML Infrastructure",
          "icon": "🧠",
          "color": "violet",
          "matched_card_count": 7,
          "similarity_score": null
        },
        {
          "category_id": "d4a...",
          "name": "LLM Engineering",
          "icon": "💬",
          "color": "blue",
          "matched_card_count": 3,
          "similarity_score": null
        }
      ]
    },
    {
      "gap": "Distributed Consensus",
      "match_type": "semantic",
      "recommended_categories": [
        {
          "category_id": "e9b...",
          "name": "System Design",
          "icon": "🏛️",
          "color": "amber",
          "matched_card_count": 4,
          "similarity_score": 0.82
        }
      ]
    },
    {
      "gap": "Underwater Basket Weaving",
      "match_type": "none",
      "recommended_categories": []
    }
  ],
  "summary": {
    "gap_count": 3,
    "tag_matches": 1,
    "semantic_matches": 1,
    "none_matches": 1
  }
}
```

### Pydantic types

```python
class RecommendedCategory(BaseModel):
    category_id: str
    name: str
    icon: str
    color: str
    matched_card_count: int
    similarity_score: float | None = None

class GapMapping(BaseModel):
    gap: str                        # original input, not normalized
    match_type: Literal["tag", "semantic", "none"]
    recommended_categories: list[RecommendedCategory]

class GapMappingSummary(BaseModel):
    gap_count: int
    tag_matches: int
    semantic_matches: int
    none_matches: int

class GapMappingResponse(BaseModel):
    results: list[GapMapping]
    summary: GapMappingSummary
```

Results preserve input order so the frontend can render them alongside
the ATS scan output without re-sorting.

---

## Dependencies

| Spec | Status | Why |
|---|---|---|
| Phase 0 — ATS scanner (produces `gaps[]`) | Done | Supplies input |
| #04 — Cards API / `cards.tags` JSON | Done | Tag-join source |
| #05/06 — FSRS study service | Done | Recommendation target |
| Phase 0 — pgvector extension + `cards.embedding` | Done | Semantic tier |
| `ai_service.embed_text()` | Exists in `app/services/ai_service.py` | Embedding generation |

No new tables. No Alembic migration.

---

## PostHog Events

| Event | When | Properties |
|---|---|---|
| `gaps_mapped` | Request completes | `{ gap_count, tag_matches, semantic_matches, none_matches, use_semantic }` |

(Frontend-side events `onboarding_started` and `gap_card_clicked` are
already covered by the `ats-card-bridge` skill file.)

---

## Edge Cases

- **Empty tags array on card:** tag-join skips it silently.
- **Gap with special characters (`C++`, `.NET`):** normalization only
  trims/lowercases; substring matching is **not** used — this would
  cause false positives (`C` matching `C++`). Exact normalized match only.
- **Card has no embedding (`NULL`):** excluded from the semantic tier.
- **All cards lack embeddings:** semantic tier returns `[]`; gap falls
  through to `match_type: "none"`.
- **Duplicate gaps in input:** preserved and mapped independently; the
  embedder cache dedupes the expensive call.
- **Gap string identical to a category name but no tag match** (e.g.
  gap `"System Design"` but no card tagged `"System Design"`): falls
  through to semantic tier. We deliberately do **not** match against
  `categories.name` directly — tags are the contract.

---

## Test Plan

### Unit tests — `tests/services/test_gap_mapping_service.py`

- **`map_gaps` — tag tier happy path:** seed 2 categories, 5 cards
  tagged `"RAG"` across them; assert returned categories ordered by
  `matched_card_count` desc.
- **`map_gaps` — normalization:** input `" rag "` matches cards tagged
  `"RAG"`; original `" rag "` echoed back in response.
- **`map_gaps` — tie-break by display_order:** two categories both
  with 3 matching cards; category with lower `display_order` returned
  first.
- **`map_gaps` — max_categories_per_gap truncation:** 5 matching
  categories, default `max_categories_per_gap=3` returns 3.
- **`_match_by_embedding` fallback:** seed cards with stubbed embeddings,
  mock `ai_service.embed_text` to return a known vector; assert correct
  category and `similarity_score` populated.
- **`map_gaps` — semantic disabled:** `use_semantic=False` with zero tag
  matches returns `match_type: "none"` without calling the embedder
  (assert mock not called).
- **`map_gaps` — none match:** gap with no tag and no embeddings
  returns `match_type: "none"`, empty list.
- **`map_gaps` — duplicate gaps:** input `["RAG", "RAG"]` produces two
  result entries; `embed_text` called at most once.
- **`map_gaps` — summary counts:** returned `summary` tallies match types
  correctly for a mixed input.

### Route tests — `tests/api/test_onboarding_routes.py`

- **Happy path:** authenticated `POST /api/v1/onboarding/map-gaps`
  with a 3-gap payload returns 200 and a 3-item `results` array in input
  order.
- **Auth failure:** no token → 401.
- **Validation — empty list:** `gaps: []` → 422.
- **Validation — too many gaps:** 51 items → 422.
- **Validation — gap too long:** 101-char gap → 422.
- **PostHog event fired:** assert `capture("gaps_mapped", ...)` called
  once with correct summary counts (mock PostHog client).

### Manual verification

1. Run a real ATS scan on a sample resume + JD; note the returned gap list.
2. `POST /api/v1/onboarding/map-gaps` with that list.
3. Confirm response: each gap has at least one category recommended
   where possible; summary counts add up to `len(gaps)`.
4. Spot-check one `match_type: "semantic"` entry — similarity score
   should be plausible (> 0.5 for reasonable gaps).
5. Confirm `gaps_mapped` event visible in PostHog.
