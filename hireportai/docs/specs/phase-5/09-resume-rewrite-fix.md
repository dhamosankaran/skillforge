# P5-S9 — AI Resume Rewrite: Restore Full-Resume Output

**Status:** Done
**Owner:** Dhamo
**Created:** 2026-04-17
**Phase:** 5B (broken-feature fixes)

## Problem

When a Premium user clicks **Generate AI Rewrite** on the AI
Optimization page, the returned resume drops later sections (most
commonly Education, Certifications, and the earliest Experience
entries). The output reads as a *summary* rather than a full rewrite.
This breaks the core premium promise and produces downloadable PDFs
and DOCX files that are unusable for job applications.

## Root Cause

Two hard input/output caps in the service layer — both conservative
hangovers from earlier provider constraints — silently truncate the
resume before it reaches Gemini 2.5 Pro:

| Location | Value | Effect |
|----------|-------|--------|
| `app/services/gpt_service.py:82` | `resume_data.get("full_text", "")[:4000]` | Input slice: a typical 2–3 page resume is 8–15k chars, so tail sections (Education, Certifications) never enter the prompt context. |
| `app/services/gpt_service.py:107` | `max_tokens=4000` | Output cap: even when the input reaches the LLM, generation can run out of tokens on long resumes. |
| `app/services/ai_service.py:79, 104` | Same two caps | Duplicate bug on the dormant `/api/v1/resume/*` path. |

The prompt itself is well-formed — it explicitly says *"Maintain the
EXACT same sections"* and *"Do NOT remove any jobs, education entries,
or skills"* — but the prompt can't enforce what the LLM never sees.
Frontend rendering (`ResumeEditor.tsx` → `MarkdownPreview`) passes
`full_text` through `ReactMarkdown` verbatim; no client-side drop.

## Fix

1. Raise the input character cap from **4,000 → 40,000** chars in
   both services. Gemini 2.5 Pro has ~1M token input context; 40k
   chars (~10k tokens) is generous for even a very long senior
   resume.
2. Raise `max_tokens` from **4,000 → 8,000** in both services so the
   rewritten output has headroom.
3. Apply identical edits to `ai_service.py` (v1 path) to keep
   parity when it gets wired up.
4. Fire a PostHog `resume_rewrite_generated` event from
   `app/api/routes/rewrite.py` on success.

## Out of Scope (intentional)

- Reworking `/api/rewrite` to require auth (`Depends(get_current_user)`).
  The route is currently unauthenticated; the FE gates on `canUsePremium`
  client-side. Fixing this is a separate security/billing slice.
- Switching the legacy `/api/rewrite` caller to the v1 path. Consolidation
  is tracked for Phase 6 cleanup.
- Revisiting the prompt itself. It is already explicit about preserving
  all sections.

## Analytics

New event (added to `.agent/skills/analytics.md`):

| Event | Source | Properties |
|-------|--------|-----------|
| `resume_rewrite_generated` | `app/api/routes/rewrite.py` | `{resume_chars, missing_keywords_count, template_type}` |

Fired after successful generation, before returning. User id is not
available on this route yet — fires as `anonymous`. Upgrade when the
route is authenticated.

## Test Plan

- `tests/services/test_resume_rewrite.py` — mocks `generate_for_task`,
  feeds a 12k-char synthetic resume (Summary + 3 Experience entries +
  Skills + Education + Certifications), asserts that **the prompt
  passed to the mock contains every section heading and every org
  name from the fixture**. This directly catches the regression if
  anyone re-introduces the truncation cap.
- Full backend suite: `python -m pytest tests/ -v --tb=short`
- Frontend suite: `cd hirelens-frontend && npx vitest run`

Manual smoke test (post-deploy): paste a known 3-page resume on
`/rewrite`, confirm all sections appear and the Education block is
the last thing rendered in the Markdown preview.

## Files Touched

- `hirelens-backend/app/services/gpt_service.py` (2 lines)
- `hirelens-backend/app/services/ai_service.py` (2 lines)
- `hirelens-backend/app/api/routes/rewrite.py` (analytics event)
- `hirelens-backend/tests/services/test_resume_rewrite.py` (new)
- `.agent/skills/analytics.md` (catalog entry)
- `docs/specs/phase-5/09-resume-rewrite-fix.md` (this file)
- `SESSION-STATE.md` (slice pointer)
