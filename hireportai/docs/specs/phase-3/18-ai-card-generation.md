# SPEC: AI Card Generation

## Status: Draft

## Problem

Admins can create cards manually (spec #17), but writing high-quality
flashcards from scratch is time-consuming. Given a topic and difficulty level,
an LLM can draft a well-structured question, answer, and tags in seconds.
The admin still reviews and optionally edits before publishing.

## Solution

A single admin-only endpoint `POST /api/v1/admin/cards/generate` that accepts
a `topic` and `difficulty`, sends a structured prompt to the configured LLM
(Gemini or Claude via the provider abstraction), and returns a `CardDraft` for
admin review. The draft is **not persisted** — the admin publishes it by
calling `POST /api/v1/admin/cards` with the draft data (possibly edited).

---

## Acceptance Criteria

- [ ] AC-1: `POST /api/v1/admin/cards/generate` accepts `topic` (string,
  1-500 chars) and `difficulty` (easy/medium/hard), calls the LLM, and
  returns a `CardDraft` with `question`, `answer`, `difficulty`, and `tags`.

- [ ] AC-2: The draft is not saved to the database. It is a transient
  response for admin review.

- [ ] AC-3: The endpoint requires `Depends(require_admin)` and returns `403`
  for non-admin users.

- [ ] AC-4: If the LLM call fails, the endpoint returns `503` with a clear
  error message.

- [ ] AC-5: The endpoint fires a PostHog event `admin_card_draft_generated`.

---

## API Contract

### `POST /api/v1/admin/cards/generate`

Generate a card draft using AI.

**Request Body**
```json
{
  "topic":      "Binary search trees",
  "difficulty": "medium"
}
```

**Pydantic Schema: `CardGenerateRequest`**
```python
class CardGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    difficulty: Literal["easy", "medium", "hard"]
```

**Response 200**
```json
{
  "question":   "What is the time complexity of searching in a balanced BST?",
  "answer":     "O(log n). A balanced BST halves the search space at each node...",
  "difficulty": "medium",
  "tags":       ["data-structures", "trees", "algorithms"]
}
```

**Pydantic Schema: `CardDraftResponse`**
```python
class CardDraftResponse(BaseModel):
    question: str
    answer: str
    difficulty: str
    tags: list[str]
```

**Error codes**
| Status | Condition |
|--------|-----------|
| 401    | Missing or invalid token |
| 403    | Authenticated user is not an admin |
| 422    | Validation error (missing topic, bad difficulty) |
| 503    | LLM provider unavailable or returned an unparseable response |

---

## Implementation Notes

- Uses the existing `get_llm_provider().generate()` abstraction so it works
  with both Gemini and Claude.
- The prompt asks the LLM to return JSON with `question`, `answer`, and `tags`.
- `json_mode=True` is used to enforce structured output.
- Temperature 0.7 for creative variety; max 800 tokens.

---

## Data Model Changes

None. Drafts are transient and not persisted.

---

## Dependencies

- Spec #17 (Admin Card CRUD) — **Done** (the publish step reuses its
  `POST /api/v1/admin/cards` endpoint)
- LLM provider abstraction (`app/services/llm/factory.py`) — **Done**

---

## Test Plan

### Unit tests (`tests/test_admin_api.py`)

- `test_generates_valid_card_structure` — mock the LLM provider to return
  a known JSON response; assert the endpoint returns 200 with the correct
  `question`, `answer`, `difficulty`, and `tags` fields.
- `test_generate_non_admin_403` — call as a non-admin user; assert 403.
- `test_generate_llm_failure_503` — mock the LLM to raise an exception;
  assert 503.

### Manual verification

1. Call `POST /api/v1/admin/cards/generate` with topic "Merge sort" and
   difficulty "hard" — verify a sensible draft is returned.
2. Copy the draft into `POST /api/v1/admin/cards` to publish — verify the
   card is created and visible in the study dashboard.
