# SPEC #22: "My Experience" AI Generation

## Status: Done

## Problem

Users study dozens of flashcards across categories but have no way to translate
that effort into a concrete, resume-ready narrative. The gap between "I studied
45 RAG cards" and a polished LinkedIn bullet point is too wide for most users to
bridge on their own.

## Solution

An AI-powered experience generator that queries the user's study history
(categories studied, cards mastered, accuracy rates) and produces a
professional narrative suitable for a resume or LinkedIn profile. Accessed via
a "Generate My Experience" button on the Profile page.

## Acceptance Criteria

- [x] AC-1: `generate_experience(user_id, topic, db)` queries CardProgress + Category data and builds an LLM prompt.
- [x] AC-2: LLM returns structured JSON with `experience_text` and `summary` fields.
- [x] AC-3: `POST /api/v1/study/experience` is auth-required and returns the generated narrative.
- [x] AC-4: If the user has no study history, the endpoint returns a helpful fallback message (not an error).
- [x] AC-5: If the LLM provider fails, the endpoint returns 503.
- [x] AC-6: Profile page shows "Generate My Experience" button with loading → result → copy/regenerate flow.
- [x] AC-7: PostHog event `experience_generated` fires with `{ topic, cards_studied_count }` on both backend and frontend.

## API Contract

### POST /api/v1/study/experience (auth required)

**Request:**
```json
{ "topic": "optional string — focus area" }
```

**Response (200):**
```json
{
  "experience_text": "Demonstrated strong understanding of retrieval-augmented generation...",
  "summary": "RAG, vector search, embeddings",
  "cards_studied": 45
}
```

**Errors:** 401 (no auth), 503 (LLM provider failure)

## Architecture

- **Service:** `app/services/experience_service.py` — aggregates study stats per category, builds prompt, calls `get_llm_provider().generate()` with JSON mode.
- **Route:** Inline in `app/api/v1/routes/study.py` — thin handler delegating to the service.
- **Schemas:** `ExperienceRequest` / `ExperienceResponse` defined inline in the study route file.
- **LLM:** Uses the shared `get_llm_provider()` factory (Gemini or Claude, configured via `llm_provider` setting).
- **Analytics:** `track()` called in the service layer; `capture()` called in frontend Profile.tsx.

## UI/UX

Located in the "My Experience" section of the Profile page (`src/pages/Profile.tsx`):

1. **Initial:** "Generate My Experience" button with Sparkles icon.
2. **Loading:** Spinner with "Generating..." text, button disabled.
3. **Result:** Rendered narrative text with two actions:
   - **Copy to clipboard** — uses `navigator.clipboard.writeText()`, shows visual "Copied!" confirmation.
   - **Regenerate** — clears state and triggers a fresh generation.

## Edge Cases

- User with zero study history gets a helpful message, not an error.
- LLM timeout or failure surfaces as 503 with a user-friendly message.
- Narratives are generated on-demand (not persisted) — each click produces a fresh result from current stats.

## Dependencies

- Spec #05 (FSRS daily review) — CardProgress table must exist.
- Spec #13 (AI card generation) — LLM provider abstraction must be in place.
- Spec #10 (PostHog analytics) — tracking utilities must be available.

## Test Plan

- **Integration tests** (`tests/test_experience_api.py`):
  - `test_generates_experience_from_study_history` — mocks LLM, seeds card progress, verifies structured response
  - `test_experience_requires_auth` — verifies 401 without token
  - `test_experience_with_no_study_history` — verifies graceful fallback
  - `test_experience_llm_failure_returns_503` — verifies error handling
- **Manual verification:**
  - Study several cards, navigate to Profile, generate experience
  - Copy to clipboard, paste into text editor to verify formatting
  - Check PostHog for `experience_generated` event
