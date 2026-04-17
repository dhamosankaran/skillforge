# P5-S11 — Generate My Experience: Token Budget + Tier + Empty-Response Guard

**Status:** Done
**Owner:** Dhamo
**Created:** 2026-04-17
**Phase:** 5B (broken-feature fixes)

## Problem

The "Generate My Experience" button on the Profile page silently
failed in production: the user clicked, the spinner ran, then either
nothing happened (no rendered text, no visible error) or a generic
"Failed to generate experience" toast appeared with no actionable
detail. The button looked broken.

## Root Cause

`app/services/experience_service.py` called the LLM router with:

```python
generate_for_task(
    "experience_narrative",
    prompt,
    None,   # system_prompt
    True,   # json_mode
    500,    # max_tokens
    0.7,    # temperature
)
```

Two compounding defects:

1. **Token starvation on the reasoning tier.**
   `experience_narrative` was registered in `REASONING_TASKS`
   (`app/core/llm_router.py`), so it routed to
   `LLM_REASONING_MODEL` (default `gemini-2.5-pro`). Gemini 2.5 Pro
   has thinking enabled by default, and thinking tokens count
   against `max_output_tokens`. With only 500 tokens available, the
   model frequently spent the entire budget on hidden thinking and
   returned `response.text = None`. `_call_gemini` coerced that to
   `""`, `json.loads("")` raised, the bare `except Exception` in
   the service mapped that to HTTPException 503 → frontend showed a
   generic error.
2. **Silent fallback when the LLM returned a structurally-valid but
   empty payload.** If the LLM ever returned valid JSON without the
   `experience_text` key (or with an empty string value),
   `data.get("experience_text", "")` returned `""`, the service
   returned 200 with an empty `experience_text`, the frontend set
   `experienceText = ""` (falsy), and the conditional render put the
   button back on screen as if nothing had happened — the true
   "silent failure" the user reported.

The service tier choice was also misaligned with the workload: a 1–2
sentence resume bullet does not need a reasoning-tier model. It was a
prompt-engineering artefact from when the feature first shipped.

## Fix

1. **`app/services/experience_service.py`** — bump `max_tokens` from
   `500` to `2048`. Even after the tier change below, the wider cap
   gives the model headroom for any provider that re-enables
   thinking, and the cost difference at this volume is negligible.
2. **`app/core/llm_router.py`** — move `"experience_narrative"` from
   `REASONING_TASKS` to `FAST_TASKS`. The output is short and
   formulaic; the fast tier (default `gemini-2.0-flash`) handles it
   well and is faster + cheaper.
3. **`app/services/experience_service.py`** — after the LLM call
   succeeds and JSON parses, check `data.get("experience_text")`. If
   falsy, raise `HTTPException(503, "Experience generation returned
   empty — please retry.")`. No empty string ever reaches the route
   response.
4. **`app/core/llm_router.py` `_call_gemini`** — when
   `response.text` is `None` or empty, `logger.warning(...)` the
   model name, `json_mode`, `max_tokens`, and the raw `response`
   object before returning the empty string. Behaviour preserved;
   only visibility added so future regressions of this class are
   greppable from the logs.

## Out of Scope

- Persisting generated experience narratives in a `user_experiences`
  table (the original Phase 3 spec at
  `.agent/skills/experience-gen.md` mentions this; it was descoped
  during P3 and remains future work).
- Adding a "Regenerate" rate limit to the route. Free-tier abuse
  protection is already present at the global rate-limit layer.
- Surfacing the backend 503 detail string into the FE toast in place
  of the generic "Failed to generate experience." message —
  considered, but a copy change can land independently.
- Consolidating `app/services/llm/factory.py` (legacy provider
  abstraction) with `app/core/llm_router.py`. Tracked under the
  Tech Debt log; targeted for Phase 6 cleanup.

## Analytics

`experience_generated` already exists in the catalog
(`.agent/skills/analytics.md`):

- **Frontend:** captured in `pages/Profile.tsx` on successful
  response with `{topic, cards_studied_count}`.
- **Backend:** tracked in `app/services/experience_service.py` via
  `analytics_track(...)` after the LLM call succeeds.

After this slice the backend event is now only fired on a
successful response (the 503 paths abort before
`analytics_track`), which is the correct semantic: an empty
response is a failure, not a generation event.

No new event introduced.

## Test Plan

- `tests/test_experience_api.py` — three pre-existing tests retained
  (happy path, auth required, no-history canned message) plus two
  new regression tests added under `TestGenerateExperience`:
  1. `test_experience_empty_llm_response_returns_503` — mock
     `generate_for_task` returning `""` (simulates Gemini thinking
     budget exhaustion) → assert 503.
  2. `test_experience_missing_key_returns_503` — mock
     `generate_for_task` returning valid JSON without the
     `experience_text` key → assert 503 with `"empty"` in detail.
- Full backend suite: `python -m pytest tests/ -v --tb=short`.
- Frontend suite: `cd hirelens-frontend && npx vitest run`.

Manual smoke test (post-deploy): study at least one card so the
service does not short-circuit to the canned no-history response,
then click "Generate My Experience" on the Profile page. Confirm a
1–2 sentence narrative renders and the Copy / Regenerate buttons
appear. Confirm a second click on Regenerate produces a different
(or at minimum non-empty) bullet.

## Files Touched

- `hirelens-backend/app/services/experience_service.py`
  (`max_tokens` 500→2048; empty-text guard raises 503)
- `hirelens-backend/app/core/llm_router.py`
  (`experience_narrative` moved to `FAST_TASKS`; warning log on
  empty Gemini response)
- `hirelens-backend/tests/test_experience_api.py`
  (two new regression tests)
- `.agent/skills/llm-strategy.md`
  (tier mapping doc kept in sync with the move)
- `docs/specs/phase-5/11-generate-experience-fix.md` (this file)
- `SESSION-STATE.md` (slice pointer, Known-Broken removal, Tech Debt
  note for the unrelated `/api/v1/email-preferences` vs
  `/api/v1/email-prefs` path mismatch)
