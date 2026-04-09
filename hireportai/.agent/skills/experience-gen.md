---
description: "My Experience" AI generation — personalized study narratives based on user's learning history
---

# Experience Generation Skill

## Overview
"My Experience" generates a personalized narrative for each user based on
their study history. It synthesizes what they've learned into a coherent
"experience" they can reference during interviews or performance reviews.
Think of it as "AI turns your flashcard history into a story."

## Key Files
- Backend:
  - `app/services/experience_service.py` — generation logic
  - `app/api/routes/experience.py` — API endpoint
  - `app/schemas/experience.py` — Pydantic schemas
- Frontend:
  - `src/components/profile/MyExperience.tsx` — display component
  - `src/pages/Profile.tsx` — hosts the experience section

## How It Works
1. User clicks "Generate My Experience" on their profile
2. Backend queries: which cards has this user studied? Which categories?
   What's their mastery level per category?
3. Backend sends a structured prompt to Gemini:
   - "This user has studied 45 cards across RAG Architecture (85% mastery),
     System Design (60%), and Foundations (95%). Generate a 2-3 paragraph
     narrative describing their expertise in these areas, written in first
     person, suitable for an interview context."
4. Gemini returns the narrative → stored in user_experiences table
5. User can regenerate, edit, or copy the narrative

## Data Model
- user_experiences table: id, user_id, content (Text), generated_at,
  categories_snapshot (JSON — frozen category stats at generation time)

## API Contract
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/experience/generate` | POST | Required | Generate new experience narrative |
| `/api/v1/experience/latest` | GET | Required | Get most recent narrative |
| `/api/v1/experience/{id}` | PUT | Required | Edit a generated narrative |

## Analytics Events
- `experience_generated` — { categories_count, total_cards_studied }
- `experience_copied` — { user_id }
- `experience_edited` — { user_id }

## Dependencies
- Requires: Card progress data (Phase 1), Category mastery stats (Phase 2)
- Phase: 3

## Testing Checklist
- [ ] User with study history gets a coherent narrative
- [ ] User with no study history gets a helpful message ("Study some cards first!")
- [ ] Generated narrative references actual categories the user studied
- [ ] Narrative is stored and retrievable
- [ ] User can edit the narrative after generation