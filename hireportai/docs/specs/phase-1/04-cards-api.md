# SPEC: Cards API

## Status: Draft

## Problem
Cards and categories live in PostgreSQL (seeded in spec #03), but there is no
API to read them. The study UI (spec #07, #08) and any frontend feature that
renders a card deck cannot function until these read endpoints exist. Additionally,
free-plan users must not see paid content — enforcement belongs at the API
layer, not the frontend.

## Solution
Four read-only endpoints under `/api/v1/cards/`. All require authentication.
Plan gating is enforced server-side: users whose `subscription.plan` is `"free"`
may only receive categories (and cards within them) where `category.source =
"foundation"`. Pro and enterprise users receive all categories and cards.
Semantic search uses pgvector cosine similarity over pre-computed `embedding`
vectors and applies the same plan gate to results.

---

## Acceptance Criteria

- [ ] AC-1: `GET /api/v1/cards` returns all categories for pro/enterprise users,
  and only `source="foundation"` categories for free users, each with an
  accurate `card_count`.

- [ ] AC-2: `GET /api/v1/cards/category/{id}` returns all cards in the
  requested category. A free user requesting a non-foundation category receives
  `403`. A request for a non-existent category receives `404`.

- [ ] AC-3: `GET /api/v1/cards/{id}` returns a single card. A free user
  requesting a card that belongs to a non-foundation category receives `403`.
  A non-existent card receives `404`.

- [ ] AC-4: `GET /api/v1/cards/search?q=<query>` returns up to `limit` cards
  ranked by cosine similarity. Results are filtered by the caller's plan gate
  before being returned — a free user never sees cards from paid categories.

- [ ] AC-5: All four endpoints return `401` when no token or an invalid token
  is provided.

- [ ] AC-6: Cards that have `embedding IS NULL` are excluded from search
  results (they cannot be ranked).

---

## API Contract

### Auth
All endpoints require `Authorization: Bearer <access_token>` (JWT issued by
`/api/v1/auth/google`). Missing or invalid tokens return `401 Unauthorized`.

### Plan Gate Logic
```
is_free  := user.subscription.plan == "free"
            OR user.subscription IS NULL
            OR user.subscription.status != "active"

allowed_category(category) :=
    NOT is_free  OR  category.source == "foundation"
```

---

### 1. `GET /api/v1/cards`
List all categories visible to the caller, with a card count per category.

**Request**
| Parameter | In     | Type   | Required | Description |
|-----------|--------|--------|----------|-------------|
| —         | header | string | yes      | `Authorization: Bearer <token>` |

**Response 200**
```json
{
  "categories": [
    {
      "id":            "<UUID>",
      "name":          "System Design",
      "icon":          "🏗️",
      "color":         "from-purple-500 to-indigo-600",
      "display_order": 1,
      "source":        "foundation",
      "card_count":    42
    }
  ]
}
```

`card_count` is computed server-side (`SELECT count(*) FROM cards WHERE
category_id = ?`). Categories are returned ordered by `display_order ASC`.

**Plan gate:** free users only receive categories where `source = "foundation"`.
Pro/enterprise users receive all categories regardless of `source`.

**Error codes**
| Status | Condition |
|--------|-----------|
| 401    | Missing or invalid token |

---

### 2. `GET /api/v1/cards/category/{id}`
List all cards in a specific category.

**Request**
| Parameter | In     | Type   | Required | Description |
|-----------|--------|--------|----------|-------------|
| `id`      | path   | UUID   | yes      | Category UUID |
| —         | header | string | yes      | `Authorization: Bearer <token>` |

**Response 200**
```json
{
  "category": {
    "id":            "<UUID>",
    "name":          "System Design",
    "icon":          "🏗️",
    "color":         "from-purple-500 to-indigo-600",
    "display_order": 1,
    "source":        "foundation"
  },
  "cards": [
    {
      "id":          "<UUID>",
      "question":    "What is CAP theorem?",
      "answer":      "CAP theorem states that...",
      "difficulty":  "medium",
      "tags":        ["distributed-systems", "databases"],
      "created_at":  "2026-04-07T12:00:00Z",
      "updated_at":  "2026-04-07T12:00:00Z"
    }
  ],
  "total": 42
}
```

Cards do **not** include the `embedding` vector in the response.
Cards are returned in insertion order (no client-controlled sort in this spec).

**Plan gate:** if the requested category exists but `source != "foundation"` and
the caller is on the free plan, return `403`.

**Error codes**
| Status | Condition |
|--------|-----------|
| 401    | Missing or invalid token |
| 403    | Category exists but caller's plan does not grant access |
| 404    | No category with the given `id` |

---

### 3. `GET /api/v1/cards/{id}`
Fetch a single card by UUID.

**Request**
| Parameter | In     | Type   | Required | Description |
|-----------|--------|--------|----------|-------------|
| `id`      | path   | UUID   | yes      | Card UUID |
| —         | header | string | yes      | `Authorization: Bearer <token>` |

**Response 200**
```json
{
  "id":            "<UUID>",
  "category_id":   "<UUID>",
  "category_name": "System Design",
  "question":      "What is CAP theorem?",
  "answer":        "CAP theorem states that...",
  "difficulty":    "medium",
  "tags":          ["distributed-systems", "databases"],
  "created_at":    "2026-04-07T12:00:00Z",
  "updated_at":    "2026-04-07T12:00:00Z"
}
```

`category_name` is included for display convenience so callers do not need to
make a second request. The `embedding` vector is never returned.

**Plan gate:** the server resolves the card's category. If `category.source !=
"foundation"` and the caller is on the free plan, return `403`.

**Error codes**
| Status | Condition |
|--------|-----------|
| 401    | Missing or invalid token |
| 403    | Card exists but belongs to a category the caller's plan does not permit |
| 404    | No card with the given `id` |

---

### 4. `GET /api/v1/cards/search`
Semantic search over card content using pgvector cosine similarity.

The server embeds the query string via the Gemini embedding model
(`models/text-embedding-004`, 1536 dims), then executes:

```sql
SELECT cards.*, 1 - (embedding <=> :query_vector) AS score
FROM cards
JOIN categories ON categories.id = cards.category_id
WHERE cards.embedding IS NOT NULL
  AND <plan_gate_filter>
ORDER BY embedding <=> :query_vector
LIMIT :limit;
```

`<plan_gate_filter>` is `categories.source = 'foundation'` for free users, or
omitted entirely for pro/enterprise users.

**Request**
| Parameter | In     | Type    | Required | Default | Description |
|-----------|--------|---------|----------|---------|-------------|
| `q`       | query  | string  | yes      | —       | Natural-language search query (1–500 chars) |
| `limit`   | query  | integer | no       | `10`    | Max results to return (1–50) |
| —         | header | string  | yes      | —       | `Authorization: Bearer <token>` |

**Response 200**
```json
{
  "query": "what is eventual consistency",
  "results": [
    {
      "id":            "<UUID>",
      "category_id":   "<UUID>",
      "category_name": "System Design",
      "question":      "Explain eventual consistency.",
      "answer":        "Eventual consistency is a consistency model...",
      "difficulty":    "hard",
      "tags":          ["distributed-systems"],
      "score":         0.91
    }
  ],
  "total": 3
}
```

`score` is the cosine similarity value in `[0, 1]`; higher is more similar.
Results are sorted by descending `score`. The `embedding` vector itself is
never returned.

**Plan gate:** only cards from plan-accessible categories appear in results.
A free user searching for "eventual consistency" will never receive a card from
a premium category even if it is the closest match.

**Error codes**
| Status | Condition |
|--------|-----------|
| 400    | `q` is missing, empty, or exceeds 500 characters |
| 400    | `limit` is outside the range [1, 50] |
| 401    | Missing or invalid token |
| 503    | Gemini embedding API unavailable; do not cache partial results |

---

## Route Ordering Note

FastAPI resolves path parameters greedily. The literal segment `search` in
`GET /api/v1/cards/search` must be registered **before** `GET /api/v1/cards/{id}`
in the router, otherwise `search` is treated as a card UUID and returns 404.

---

## Data Model Dependencies

No schema changes in this spec. All columns referenced are already present
from spec #03 (Card + Category extraction):

| Model        | Columns used |
|--------------|--------------|
| `categories` | `id`, `name`, `icon`, `color`, `display_order`, `source` |
| `cards`      | `id`, `category_id`, `question`, `answer`, `difficulty`, `tags`, `embedding`, `created_at`, `updated_at` |
| `users`      | `id`, `subscription` (via `selectin` relationship) |
| `subscriptions` | `plan`, `status` |

The `ivfflat` index on `cards.embedding` (created post-seeding in spec #03)
is required for acceptable search latency at scale.

---

## Edge Cases

- **No active subscription row:** treat the user as free. Guard with `if
  user.subscription is None or user.subscription.status != "active"`.
- **`embedding IS NULL` on a card:** excluded from search; still returned by
  `GET /cards/{id}` and `GET /cards/category/{id}` since those do not rank.
- **Empty search results:** return `200` with `"results": []` and `"total": 0`;
  do not return `404`.
- **Gemini embedding failure on search:** return `503` with
  `"detail": "Embedding service unavailable. Please try again."`. Do not fall
  back to text search (no such index exists).
- **`limit` defaulting to 10:** the default keeps latency predictable; callers
  that need more results must pass `limit` explicitly, up to 50.
- **UUID path param validation:** FastAPI validates path params against the
  declared type. A malformed UUID (non-UUID string) in `/{id}` returns `422
  Unprocessable Entity` automatically — no extra handling needed.

---

## Dependencies

- Spec #00 (PostgreSQL + pgvector) — **Done**
- Spec #02 (Auth unification, `get_current_user`) — **Done**
- Spec #03 (User role + admin, `require_admin`) — **Done**
- Spec #03-card-extraction (Card + Category models, seeded data, embeddings) — **Done**

---

## Test Plan

### Unit tests (`tests/test_cards_api.py`)
- **`test_list_categories_free_user`**: free-plan user; assert response only
  contains categories where `source == "foundation"`.
- **`test_list_categories_pro_user`**: pro-plan user; assert all categories
  are returned including non-foundation ones.
- **`test_get_category_cards_ok`**: pro user requests a valid category;
  assert `200`, card list is non-empty, no `embedding` field in any card.
- **`test_get_category_cards_free_blocked`**: free user requests a category
  with `source != "foundation"`; assert `403`.
- **`test_get_category_cards_not_found`**: any user requests a non-existent
  UUID; assert `404`.
- **`test_get_card_ok`**: pro user fetches a card by UUID; assert `200`,
  `category_name` is present, no `embedding` field.
- **`test_get_card_free_blocked`**: free user fetches a card from a premium
  category; assert `403`.
- **`test_get_card_not_found`**: any user fetches a non-existent UUID; assert
  `404`.
- **`test_search_returns_ranked_results`**: mock Gemini embed call; assert
  results are sorted by descending `score`, `embedding` field absent.
- **`test_search_free_plan_filters_premium`**: free user search; assert no
  result belongs to a non-foundation category.
- **`test_search_missing_q`**: omit `q`; assert `400`.
- **`test_search_limit_out_of_range`**: `limit=0` and `limit=51`; assert `400`.
- **`test_search_gemini_failure`**: mock Gemini to raise; assert `503`.
- **`test_all_endpoints_unauthenticated`**: call each endpoint without a
  bearer token; assert `401` on all four.

### Manual verification
1. `GET /api/v1/cards` with a free-plan token — confirm only foundation
   categories appear.
2. `GET /api/v1/cards` with a pro-plan token — confirm all categories appear.
3. `GET /api/v1/cards/category/<foundation-id>` with a free token — confirm
   `200` with cards.
4. `GET /api/v1/cards/category/<premium-id>` with a free token — confirm
   `403`.
5. `GET /api/v1/cards/<card-id>` — confirm `embedding` is absent from
   response.
6. `GET /api/v1/cards/search?q=eventual+consistency&limit=5` — confirm
   results are ranked by score, plan gate respected.
7. `GET /api/v1/cards/search?q=` — confirm `400`.
