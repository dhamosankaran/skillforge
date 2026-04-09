---
description: End-to-end content pipeline — card extraction, AI generation, admin CRUD, bulk import
---

# Content Pipeline Skill

## Overview
The content pipeline covers everything related to creating, importing,
and managing study cards at scale. It spans multiple phases:
- Phase 1: Extract 177 cards from JSX → PostgreSQL + generate embeddings
- Phase 3: Admin CRUD, AI-assisted card generation, bulk CSV import

## Pipeline Stages

### Stage 1: Initial Extraction (Phase 1)
- See `.agent/skills/card-extraction.md` for details
- Parse JSX → create Category + Card records → generate embeddings
- One-time script, not a repeatable pipeline

### Stage 2: Admin Manual Creation (Phase 3)
- Admin creates cards via the Admin Panel UI
- POST /api/v1/admin/cards with all required fields
- Card immediately available to users

### Stage 3: AI-Assisted Generation (Phase 3)
- Admin provides a topic + difficulty level
- Gemini generates: question, answer, tags, difficulty
- Admin reviews the draft → edits if needed → publishes
- POST /api/v1/admin/cards/generate → returns draft (not saved)
- POST /api/v1/admin/cards → saves the reviewed draft

### Stage 4: Bulk Import (Phase 3)
- Admin uploads a CSV file with columns: category, question, answer, difficulty, tags
- Backend parses CSV → validates each row → creates Card records
- POST /api/v1/admin/cards/bulk-import (multipart/form-data)
- Returns: { created: N, errors: [ { row: N, reason: "..." } ] }

### Stage 5: Embedding Generation (automatic)
- After any card is created (manual, AI, or bulk), generate embedding
- This can be synchronous (during creation) or async (background job)
- Phase 1: synchronous is fine for 177 cards
- Phase 3+: consider background job if bulk imports > 100 cards

## Key Files
- `scripts/extract_cards.py` — one-time JSX extraction (Phase 1)
- `scripts/generate_embeddings.py` — one-time embedding generation (Phase 1)
- `app/services/card_admin_service.py` — CRUD + bulk import (Phase 3)
- `app/services/ai_card_service.py` — Gemini card generation (Phase 3)
- `app/api/routes/admin.py` — admin endpoints (Phase 3)

## Quality Checks
- Every card must have: question (non-empty), answer (non-empty), category_id (valid FK), difficulty (Easy/Medium/Hard)
- Tags should be lowercase, no duplicates
- Embedding must be non-null after generation
- Admin can flag cards for review via card_feedback

## Analytics Events
- `card_created` — { method: "manual" | "ai" | "bulk", admin_id }
- `bulk_import_completed` — { total, created, errors }
- `ai_card_generated` — { topic, difficulty, accepted: bool }