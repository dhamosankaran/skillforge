# SPEC: Admin Card CRUD

## Status: Draft

## Problem

Admins have no way to create, edit, or delete flashcards through the API.
Card content is currently seed-only (loaded from scripts). When subject matter
needs updating — new questions, corrected answers, difficulty adjustments, or
retiring stale cards — there is no pathway short of raw SQL. Bulk content
loading (e.g., importing hundreds of cards from a curriculum spreadsheet)
is also unsupported.

## Solution

Five admin-only endpoints under `/api/v1/admin/cards` for full card lifecycle
management plus bulk CSV import. All routes require `Depends(require_admin)`,
returning `403` for non-admin users. Embeddings are generated asynchronously
after create/update so that admin operations remain fast.

---

## Acceptance Criteria

- [ ] AC-1: `POST /api/v1/admin/cards` creates a card with the provided
  fields and returns the created card with its UUID. The card's `embedding`
  is `null` initially and populated asynchronously.

- [ ] AC-2: `PUT /api/v1/admin/cards/{id}` updates any mutable field on an
  existing card and returns the updated card. If `question` or `answer`
  changed, the existing `embedding` is set to `null` and re-generated
  asynchronously.

- [ ] AC-3: `DELETE /api/v1/admin/cards/{id}` soft-deletes or hard-deletes
  the card (hard-delete if no FSRS review history references it; soft-delete
  otherwise). Returns `204 No Content`.

- [ ] AC-4: `GET /api/v1/admin/cards` lists all cards with pagination,
  optional filters by `category_id`, `difficulty`, and `tags`, and optional
  search by `q` (substring match on question text). Returns cards with
  their category name.

- [ ] AC-5: `POST /api/v1/admin/cards/import` accepts a CSV file upload,
  validates all rows, and bulk-inserts valid cards. Returns a summary with
  `created_count`, `skipped_count`, and per-row errors for invalid rows.
  The entire import is atomic — if any row fails validation, no rows are
  inserted (unless `partial=true` query param is set).

- [ ] AC-6: All five endpoints return `403` for authenticated non-admin
  users and `401` for unauthenticated requests.

- [ ] AC-7: All mutations fire PostHog events (`admin_card_created`,
  `admin_card_updated`, `admin_card_deleted`, `admin_cards_imported`).

---

## API Contract

### Auth

All endpoints require `Authorization: Bearer <access_token>` and
`Depends(require_admin)`. Non-admin users receive `403 Admin access required`.

---

### 1. `POST /api/v1/admin/cards`

Create a single card.

**Request Body**
```json
{
  "category_id":  "<UUID>",          // required — must reference existing category
  "question":     "What is...",      // required — 1–5000 chars
  "answer":       "It is...",        // required — 1–10000 chars
  "difficulty":   "medium",          // required — enum: easy, medium, hard
  "tags":         ["sql", "joins"]   // optional — list of strings, default []
}
```

**Pydantic Schema: `CardCreateRequest`**
```python
class CardCreateRequest(BaseModel):
    category_id: str                                    # UUID of parent category
    question: str = Field(..., min_length=1, max_length=5000)
    answer: str = Field(..., min_length=1, max_length=10000)
    difficulty: Literal["easy", "medium", "hard"]
    tags: list[str] = Field(default_factory=list)
```

**Response 201**
```json
{
  "id":            "<UUID>",
  "category_id":   "<UUID>",
  "category_name": "System Design",
  "question":      "What is...",
  "answer":        "It is...",
  "difficulty":    "medium",
  "tags":          ["sql", "joins"],
  "embedding":     null,
  "created_at":    "2026-04-10T12:00:00Z",
  "updated_at":    "2026-04-10T12:00:00Z"
}
```

**Pydantic Schema: `AdminCardResponse`**
```python
class AdminCardResponse(BaseModel):
    id: str
    category_id: str
    category_name: str
    question: str
    answer: str
    difficulty: str
    tags: list[str]
    embedding_status: Literal["pending", "ready"]   # "pending" when null
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

**Error codes**
| Status | Condition |
|--------|-----------|
| 400    | `category_id` does not reference an existing category |
| 401    | Missing or invalid token |
| 403    | Authenticated user is not an admin |
| 422    | Validation error (missing fields, bad difficulty, etc.) |

---

### 2. `PUT /api/v1/admin/cards/{id}`

Update an existing card. Only provided fields are updated (partial update).

**Request Body** (all fields optional, at least one required)
```json
{
  "category_id":  "<UUID>",
  "question":     "Updated question...",
  "answer":       "Updated answer...",
  "difficulty":   "hard",
  "tags":         ["updated-tag"]
}
```

**Pydantic Schema: `CardUpdateRequest`**
```python
class CardUpdateRequest(BaseModel):
    category_id: Optional[str] = None
    question: Optional[str] = Field(None, min_length=1, max_length=5000)
    answer: Optional[str] = Field(None, min_length=1, max_length=10000)
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    tags: Optional[list[str]] = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> Self:
        if not any([self.category_id, self.question, self.answer,
                    self.difficulty, self.tags is not None]):
            raise ValueError("At least one field must be provided")
        return self
```

**Response 200** — returns `AdminCardResponse` (same shape as create).

If `question` or `answer` changed, the card's `embedding` is nullified and
re-generated asynchronously. If only `difficulty`, `tags`, or `category_id`
changed, the existing embedding is preserved.

**Error codes**
| Status | Condition |
|--------|-----------|
| 400    | `category_id` does not reference an existing category |
| 401    | Missing or invalid token |
| 403    | Authenticated user is not an admin |
| 404    | No card with the given `id` |
| 422    | No fields provided, or validation error |

---

### 3. `DELETE /api/v1/admin/cards/{id}`

Delete a card.

**Request** — no body. Card UUID in path.

**Response 204** — no body.

If the card has associated FSRS review records (`user_card_states` rows), the
card is soft-deleted (`deleted_at` timestamp set, excluded from all read
queries). If no review records reference it, it is hard-deleted.

**Error codes**
| Status | Condition |
|--------|-----------|
| 401    | Missing or invalid token |
| 403    | Authenticated user is not an admin |
| 404    | No card with the given `id` |

---

### 4. `GET /api/v1/admin/cards`

List all cards with pagination and filters. Unlike the user-facing
`GET /api/v1/cards/category/{id}`, this endpoint is not plan-gated and
shows all cards regardless of category source.

**Query Parameters**
| Parameter     | Type    | Required | Default | Description |
|---------------|---------|----------|---------|-------------|
| `page`        | int     | no       | `1`     | Page number (1-indexed) |
| `per_page`    | int     | no       | `50`    | Items per page (1–200) |
| `category_id` | UUID    | no       | —       | Filter by category |
| `difficulty`  | string  | no       | —       | Filter: easy/medium/hard |
| `tags`        | string  | no       | —       | Comma-separated tag filter (AND logic) |
| `q`           | string  | no       | —       | Substring search on question text (case-insensitive) |

**Response 200**
```json
{
  "cards": [
    {
      "id": "<UUID>",
      "category_id": "<UUID>",
      "category_name": "System Design",
      "question": "What is...",
      "answer": "It is...",
      "difficulty": "medium",
      "tags": ["sql"],
      "embedding_status": "ready",
      "created_at": "2026-04-10T12:00:00Z",
      "updated_at": "2026-04-10T12:00:00Z"
    }
  ],
  "total": 342,
  "page": 1,
  "per_page": 50,
  "pages": 7
}
```

**Pydantic Schema: `AdminCardListResponse`**
```python
class AdminCardListResponse(BaseModel):
    cards: list[AdminCardResponse]
    total: int
    page: int
    per_page: int
    pages: int
```

**Error codes**
| Status | Condition |
|--------|-----------|
| 401    | Missing or invalid token |
| 403    | Authenticated user is not an admin |
| 422    | Invalid filter values |

---

### 5. `POST /api/v1/admin/cards/import`

Bulk import cards from a CSV file.

**Request** — `multipart/form-data`
| Field     | Type   | Required | Description |
|-----------|--------|----------|-------------|
| `file`    | file   | yes      | CSV file (max 5 MB) |
| `partial` | bool   | no       | If `true`, insert valid rows and skip invalid ones. Default `false` (all-or-nothing). |

**CSV Format**
```csv
category_id,question,answer,difficulty,tags
<UUID>,"What is X?","X is...","medium","tag1;tag2"
```

- Headers are required (first row).
- `tags` uses semicolon-delimited values within the CSV cell.
- Maximum 500 rows per import.

**Response 200**
```json
{
  "created_count": 48,
  "skipped_count": 2,
  "errors": [
    {"row": 12, "error": "Invalid difficulty 'extreme' — must be easy, medium, or hard"},
    {"row": 37, "error": "category_id 'abc' does not reference an existing category"}
  ]
}
```

**Pydantic Schema: `CardImportResponse`**
```python
class CardImportRowError(BaseModel):
    row: int
    error: str

class CardImportResponse(BaseModel):
    created_count: int
    skipped_count: int
    errors: list[CardImportRowError]
```

When `partial=false` (default) and any row has errors, the response returns
`400` with `created_count: 0` and the full error list. No rows are inserted.

When `partial=true`, valid rows are inserted and invalid rows are skipped.
The response is always `200` (even if some rows were skipped).

**Error codes**
| Status | Condition |
|--------|-----------|
| 400    | File is not valid CSV, exceeds 5 MB, exceeds 500 rows, or has validation errors (when `partial=false`) |
| 401    | Missing or invalid token |
| 403    | Authenticated user is not an admin |
| 422    | Missing `file` field or wrong content type |

---

## Data Model Changes

### Soft-delete support on `cards` table

Add a nullable `deleted_at` column to the `cards` table:

```python
# In Card model
deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Alembic migration: `alembic revision --autogenerate -m "add cards deleted_at for soft delete"`

All existing read queries (user-facing `/api/v1/cards/*`) must add
`.where(Card.deleted_at.is_(None))` to exclude soft-deleted cards.

No other schema changes required — all existing Card columns are sufficient.

---

## Edge Cases

- **Duplicate question:** Not blocked at the DB level (two cards can have the
  same question in different categories). Admins are trusted to manage this.
- **Deleting a card mid-review:** If a user has the card in their current
  review session and it gets soft-deleted, the next fetch will simply skip it.
  The `user_card_states` row is preserved for historical stats.
- **CSV encoding:** Assume UTF-8. If the file cannot be decoded as UTF-8,
  return `400` with a clear message.
- **CSV with extra columns:** Extra columns are silently ignored.
- **CSV with missing columns:** Return `400` listing the missing required
  headers.
- **Empty CSV (headers only):** Return `200` with `created_count: 0`.
- **Embedding generation failure:** Cards are created with `embedding = null`.
  A background retry should re-attempt embedding generation. Cards with null
  embeddings are still usable in non-search contexts.
- **Category deletion:** Out of scope. The FK on `category_id` uses
  `ondelete="RESTRICT"`, so a category with cards cannot be deleted.

---

## Dependencies

- Spec #03 (Card + Category models, `require_admin`) — **Done**
- Spec #04 (Cards API — read endpoints) — **Done**
- Spec #02 (Auth unification, `get_current_user`) — **Done**

---

## Test Plan

### Unit tests (`tests/test_admin_card_crud.py`)

**Create**
- `test_create_card_ok` — admin creates card with valid payload; assert `201`,
  returned card has correct fields, `embedding_status` is `"pending"`.
- `test_create_card_invalid_category` — `category_id` does not exist; assert
  `400`.
- `test_create_card_missing_required_fields` — omit `question`; assert `422`.
- `test_create_card_invalid_difficulty` — `difficulty="extreme"`; assert `422`.

**Update**
- `test_update_card_ok` — admin updates `question`; assert `200`, question
  changed, `embedding_status` resets to `"pending"`.
- `test_update_card_tags_only` — admin updates only `tags`; assert `200`,
  `embedding_status` remains `"ready"` (no re-embed needed).
- `test_update_card_not_found` — non-existent UUID; assert `404`.
- `test_update_card_no_fields` — empty body; assert `422`.

**Delete**
- `test_delete_card_ok` — admin deletes card with no review history; assert
  `204`, card is hard-deleted (not in DB).
- `test_delete_card_with_reviews` — admin deletes card that has review records;
  assert `204`, card is soft-deleted (`deleted_at` is set), still in DB.
- `test_delete_card_not_found` — non-existent UUID; assert `404`.

**List**
- `test_list_cards_paginated` — admin lists cards; assert pagination fields
  (`total`, `page`, `per_page`, `pages`) are correct.
- `test_list_cards_filter_category` — filter by `category_id`; assert all
  returned cards belong to that category.
- `test_list_cards_filter_difficulty` — filter by `difficulty=hard`; assert all
  returned cards have `difficulty == "hard"`.
- `test_list_cards_search_q` — search `q=CAP`; assert results contain "CAP"
  in question text.

**CSV Import**
- `test_import_csv_ok` — upload valid CSV with 3 rows; assert `200`,
  `created_count == 3`, `errors == []`.
- `test_import_csv_all_or_nothing` — CSV with 1 invalid row, `partial=false`;
  assert `400`, `created_count == 0`, no cards inserted.
- `test_import_csv_partial` — CSV with 1 invalid row, `partial=true`; assert
  `200`, valid rows inserted, invalid rows in `errors`.
- `test_import_csv_too_large` — CSV > 5 MB; assert `400`.
- `test_import_csv_too_many_rows` — CSV > 500 rows; assert `400`.
- `test_import_csv_missing_headers` — CSV without `question` header; assert
  `400`.
- `test_import_csv_empty` — headers only, no data rows; assert `200`,
  `created_count == 0`.

**Auth / Access Control**
- `test_all_admin_endpoints_non_admin` — call each endpoint as a non-admin
  user; assert `403` on all five.
- `test_all_admin_endpoints_unauthenticated` — call each endpoint with no
  token; assert `401` on all five.

### Integration tests (`tests/test_admin_card_crud_integration.py`)

- `test_create_then_list` — create a card, then list; assert the new card
  appears in the list response.
- `test_create_update_delete_lifecycle` — create a card, update it, delete it;
  verify each step returns expected status and the card is no longer visible
  via the user-facing `GET /api/v1/cards/category/{id}`.
- `test_import_then_search` — import cards via CSV, trigger embedding
  generation, verify cards appear in semantic search results.

### Manual verification

1. Create a card via `POST /api/v1/admin/cards` — verify it appears in the
   study dashboard.
2. Update the card's question — verify the change is reflected and embedding
   re-generates.
3. Delete the card — verify it no longer appears in category listing or search.
4. Upload a CSV with 10 rows — verify all 10 cards are created.
5. Upload a CSV with 1 bad row and `partial=false` — verify `400` and zero
   cards created.
6. Call any admin endpoint as a regular user — verify `403`.
