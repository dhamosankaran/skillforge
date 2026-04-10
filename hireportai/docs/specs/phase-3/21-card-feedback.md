# SPEC #21: Per-Card Feedback with Admin Dashboard

## Status: Done

## Problem

Users have no way to flag low-quality, confusing, or incorrect flashcards.
Without this signal the content team operates blind — bad cards stay in rotation
and erode trust in the study experience.

## Solution

Add a lightweight thumbs-up / thumbs-down feedback mechanism on every card,
surfaced immediately after the user rates recall (FSRS). Down-votes optionally
prompt for a free-text comment. An admin dashboard aggregates all feedback so the
content team can triage the worst cards first.

## Acceptance Criteria

- [x] AC-1: After rating a card, the user sees thumbs-up / thumbs-down icons.
- [x] AC-2: Clicking thumbs-down reveals an optional "What's wrong with this card?" textarea.
- [x] AC-3: Submitting feedback POSTs to `/api/v1/cards/{card_id}/feedback` (auth required).
- [x] AC-4: Admins can list all feedback via `GET /api/v1/admin/feedback` (paginated, filterable by vote type).
- [x] AC-5: Admins can view a summary via `GET /api/v1/admin/feedback/summary` returning `{ total_up, total_down, worst_cards }`.
- [x] AC-6: Non-admin users receive 403 on admin endpoints.
- [x] AC-7: PostHog event `card_feedback_submitted` fires with `{ card_id, vote, has_comment }`.

## API Contract

### POST /api/v1/cards/{card_id}/feedback (auth required)

**Request:**
```json
{ "vote": "up" | "down", "comment": "optional string" }
```

**Response (201):**
```json
{ "id": "uuid", "user_id": "uuid", "card_id": "uuid", "vote": "up", "comment": null, "created_at": "iso8601" }
```

**Errors:** 401 (no auth), 404 (card not found), 422 (invalid vote)

### GET /api/v1/admin/feedback (admin only)

**Query params:** `page` (default 1), `per_page` (default 50, max 200), `vote` (optional filter)

**Response (200):**
```json
{ "feedback": [...], "total": 42, "page": 1, "per_page": 50 }
```

### GET /api/v1/admin/feedback/summary (admin only)

**Response (200):**
```json
{ "total_up": 120, "total_down": 18, "worst_cards": [{ "card_id": "uuid", "question": "...", "down_count": 5 }, ...] }
```

## Data Model Changes

**New table: `card_feedback`**

| Column     | Type        | Constraints                        |
|------------|-------------|------------------------------------|
| id         | UUID (str)  | PK, auto-generated                 |
| user_id    | String(36)  | FK → users.id, CASCADE, indexed    |
| card_id    | String(36)  | FK → cards.id, CASCADE, indexed    |
| vote       | String(4)   | NOT NULL, "up" or "down"           |
| comment    | Text        | nullable                           |
| created_at | DateTime    | server_default=now()               |

Migration: `alembic/versions/e5b2c8d4a1f7_add_card_feedback_table.py`

## UI/UX

After the FSRS rating is saved (state=done), a `CardFeedbackRow` component
appears below the "Saved!" confirmation:

1. **Idle:** "Rate this card:" label with thumbs-up and thumbs-down icon buttons.
2. **Up-vote:** Submits immediately, shows "Thanks for your feedback!".
3. **Down-vote:** Reveals a textarea ("What's wrong with this card?") + Cancel / Send buttons.
4. **Sent:** Replaces row with "Thanks for your feedback!".

## Edge Cases

- Duplicate feedback from the same user on the same card is allowed (each submission is independent).
- Empty comment on down-vote is permitted (comment is optional).
- Card deletion cascades to feedback records.

## Dependencies

- Spec #05 (FSRS daily review) — QuizPanel must exist.
- Spec #10 (PostHog analytics) — capture() utility must be available.

## Test Plan

- **Integration tests** (`tests/test_feedback_api.py`):
  - `test_submit_feedback` — authenticated user submits up-vote with comment
  - `test_admin_can_view_feedback` — admin lists feedback, total >= 1
  - `test_non_admin_cannot_view_feedback` — regular user gets 403
  - `test_feedback_summary_returns_worst_cards` — summary includes seeded down-voted card
- **Manual verification:**
  - Study a card, rate it, confirm feedback row appears
  - Submit thumbs-down with comment, verify it appears in admin dashboard
