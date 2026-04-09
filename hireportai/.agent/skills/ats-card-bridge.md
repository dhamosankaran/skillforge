---
description: Maps ATS scan skill gaps to study cards, powers onboarding flow
---

# ATS → Card Bridge Skill

## Overview
When a user scans their resume, the ATS scanner produces a list of
skill gaps. This service maps those gaps to study card categories
so the user immediately knows what to study. This is the core
conversion mechanism: scan → "you're weak in X" → here are cards.

## Key Files
- Backend:
  - `app/services/gap_mapping_service.py` — gap → category mapping
  - `app/api/routes/onboarding.py` — onboarding endpoints
- Frontend:
  - `src/pages/Onboarding.tsx` — post-scan gap display
  - `src/components/onboarding/GapCard.tsx` — individual gap card

## How Mapping Works
1. ATS scanner returns skill gaps as tags (e.g., "RAG", "System Design")
2. Each card category has a `tags` array
3. Mapping is a tag-based join: gap tag ∈ category tags → match
4. For semantic matching (Phase 1+): use pgvector cosine similarity
   between gap description embedding and card embeddings

## Analytics Events
- `onboarding_started` — { source: "ats_scan" | "direct" }
- `gap_card_clicked` — { gap_name, category_id }
- `onboarding_completed` — { gaps_shown, cards_clicked }