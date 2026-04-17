# SPEC: Resume Rewrite + Cover Letter Formatting Fix

## Status: Planned — Known-Broken, awaiting P5-S9 + P5-S10

## Code Pointers
- Resume rewrite service: `app/services/ai_service.py` / `app/services/gpt_service.py` (legacy shim that now delegates to the LLM router). Confirm authoritative path during P5-S9.
- Cover-letter route (legacy): `app/api/routes/cover_letter.py`; v1: `app/api/v1/routes/cover_letter.py`.
- Route: `app/api/routes/rewrite.py` + `app/api/v1/routes/rewrite.py`.
- LLM path: both flows must go through `app/core/llm_router.py → generate_for_task(task="resume_rewrite" | "cover_letter", ...)` — reasoning tier.

## Known Bugs (per SESSION-STATE "Known-Broken")
- **AI Resume Rewrite (P5-S9)**: drops sections from the original (work history, education). Output reads like a summary, not a full rewrite.
- **Cover Letter Generation (P5-S10)**: format inconsistent — wrong headers, missing greeting/signature blocks.

## Problem
*(to be filled in during P5-S9 / P5-S10)*

## Solution
*(to be filled in during P5-S9 / P5-S10 — likely structured response parsing with named sections, not free-form text)*

## Acceptance Criteria
*(to be filled in during P5-S9 / P5-S10)*

---
*Placeholder created during P5-S0b on 2026-04-17. Filled in during P5-S9 + P5-S10.*
