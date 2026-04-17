# SPEC: Multi-Model LLM Router (Fast vs Reasoning Tiers)

## Status: Implemented — Spec Backfill Pending (P5-S1)

## Code Pointers
- Router: `app/core/llm_router.py` (NOT `app/services/llm_router.py` as the playbook originally named it).
- Entry point: `generate_for_task(task: str, prompt: str, system_prompt=None, json_mode=False, max_tokens=4096, temperature=0.7) -> str`.
- Task classification: two frozensets in the module.
  - `FAST_TASKS = {"ats_keyword_extraction", "card_draft", "quiz_generation", "gap_mapping", "rewrite_bullets"}`
  - `REASONING_TASKS = {"resume_rewrite", "cover_letter", "interview_questions", "experience_narrative"}`
  - Unknown tasks default to **fast** (cheaper).
- Provider dispatch: module-level `_call_gemini` / `_call_anthropic` / `_call_openai`, selected by `LLM_FAST_PROVIDER` / `LLM_REASONING_PROVIDER`. Fallback is implicit — if a provider key is missing the call raises `RuntimeError("<PROVIDER>_API_KEY not configured")`.
- Legacy provider abstraction at `app/services/llm/factory.py` (`get_llm_provider()`) is **deprecated**. Do not route new calls through it. See SESSION-STATE "Tech Debt".
- Tests: `tests/test_llm_router.py`.

## Problem
*(to be filled in during P5-S1 backfill)*

## Solution
*(to be filled in during P5-S1 backfill)*

## Acceptance Criteria
*(to be filled in during P5-S1 backfill — include task-to-tier mapping table)*

## Divergence from Original Spec
- Location: `app/core/` not `app/services/`.
- API shape: function `generate_for_task(task="...")` instead of `TaskType` enum + `get_llm_client(task_type)`.
- No explicit Gemini fallback — missing-key raises `RuntimeError` rather than silently falling back. Revisit in P5-S1.

---
*Placeholder created during P5-S0b on 2026-04-17. Replace with full spec during P5-S1.*
