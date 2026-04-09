---
description: Card CRUD, bulk import, AI-assisted card generation (Phase 3)
---
# Admin Panel Skill
## Overview
Admin panel lets admins create, edit, delete cards and bulk-import
from CSV. AI assist uses Gemini to draft cards from a topic.
## Key Files
- Backend: `app/api/routes/admin.py`, `app/services/card_admin_service.py`
- Frontend: `src/pages/AdminPanel.tsx`
## Access Control
- All admin routes require `Depends(require_admin)` — returns 403 for non-admins
## AI Card Generation
- Input: topic string + difficulty level
- Process: Gemini generates question, answer, tags, difficulty
- Output: draft card for admin review before publish
