# P5-S10 — Cover Letter: Restore Business-Letter Format

**Status:** Done
**Owner:** Dhamo
**Created:** 2026-04-17
**Phase:** 5B (broken-feature fixes)

## Problem

The AI-generated cover letter did not look like a cover letter. The
prompt asked the LLM to emit four `##` markdown sections
(`## Opening`, `## Why I'm a Fit`, `## Key Achievement`,
`## Closing`). The frontend renders those faithfully as bold,
accent-coloured mini-headers — so the result looked like a form with
labelled fields, not a business letter. The prompt also contained no
instruction to produce a date, recipient block, `Dear …` greeting, or
`Sincerely, [Name]` sign-off.

Secondary: the user-selected `tone` arg was silently ignored because
the prompt hardcoded *"Tone: confident, specific, not generic."*
regardless of the selection. And the same 2.5k / 1.5k char input
truncation that caused the P5-S9 resume-rewrite bug applied here
against the resume and JD.

## Root Cause

`app/services/gpt_service.py:generate_cover_letter` (and its parity
twin `ai_service.py:generate_cover_letter`) built a prompt that:

1. Explicitly instructed the LLM to emit `##` section headers.
2. Named the sections ("Opening", "Why I'm a Fit", "Key Achievement",
   "Closing") — which is prompt-author scaffolding, not body text
   convention.
3. Never mentioned date, recipient, greeting, or sign-off.
4. Hardcoded the tone string, ignoring the `tone` argument.
5. Applied a `[:2500]` / `[:1500]` truncation to resume and JD.

No server-side parsing of the response happens; the raw LLM output
goes straight to the frontend, which renders via `ReactMarkdown` —
the frontend was not at fault.

## Fix

1. **Rewrite the prompt** to emit traditional business-letter format
   in this order: Date → blank → Recipient block (2 lines) → blank →
   `Dear Hiring Manager,` → blank → 3 body paragraphs separated by
   blank lines → blank → `Sincerely,` → candidate name.
2. **Explicit negative instructions:** *"Do NOT use markdown headers
   (no ##, no #, no bold section titles). Do NOT label sections with
   words like 'Opening', 'Why I'm a Fit', 'Key Achievement', or
   'Closing'."*
3. **Inject structured context** into the prompt:
   - `today` — server-computed `date.today().strftime("%B %d, %Y")`.
   - `company_name` — from `jd_requirements.get("company_name")`
     with `"your company"` fallback.
   - `candidate_name` — best-effort extraction from the first
     non-empty resume line that looks like 2–4 Title-Case tokens
     with no digits, email, or colon. Fallback `"The Applicant"`.
4. **Wire the `tone` argument into the prompt** via `Tone: {tone}.`.
5. **Raise truncation caps** — resume `[:2500] → [:20000]`, JD
   `[:1500] → [:10000]`.
6. **Raise `max_tokens`** — 900 → 1500.
7. **Parity in `ai_service.py`** (v1 path) with identical edits.
8. **PostHog** — fire `cover_letter_generated { tone, resume_chars,
   company_name_present }` on success.
9. **Fallback branch** (the `except Exception` path that renders a
   static cover letter when the LLM fails) updated to match the new
   format so the fallback still looks like a cover letter.

## Out of Scope

- Auth on `/api/cover-letter`. Same as the rewrite route, this
  endpoint is currently unauthenticated; a separate slice will add
  `Depends(get_current_user)` and gate on premium.
- Parsing a structured recipient block (name, title, address) from
  the JD. The JD parser already exposes `company_name`; extracting
  hiring-manager name is brittle and low-value today.
- Consolidating `gpt_service.py` + `ai_service.py`. Tracked for
  Phase 6 cleanup.

## Analytics

New event (added to `.agent/skills/analytics.md`):

| Event | Source | Properties |
|-------|--------|-----------|
| `cover_letter_generated` | `app/api/routes/cover_letter.py` | `{tone, resume_chars, company_name_present}` |

Fired after successful generation, before returning. Anonymous
`user_id` — route is unauthenticated today. Upgrade when auth lands.

## Test Plan

- `tests/services/test_cover_letter.py` (new) — two tests:
  1. Mock `generate_for_task`; assert the prompt (a) contains
     `"Do NOT use markdown headers"`, (b) explicitly names the
     forbidden labels Opening / Why I'm a Fit / Key Achievement /
     Closing, (c) contains `"Dear Hiring Manager,"`, (d) contains
     `"Sincerely,"`, (e) contains `"Tone: conversational."` when
     that tone is selected, (f) contains the full 12k-char resume
     and a unique marker, (g) floors `max_tokens` at 1500.
  2. Mock a well-formed business-letter response; assert it is
     returned verbatim (whitespace-stripped) on `cover_letter`
     and contains no `##`.
- Full backend suite: `python -m pytest tests/ -v --tb=short`
- Frontend suite: `cd hirelens-frontend && npx vitest run`

Manual smoke test (post-deploy): generate a cover letter, confirm
the preview shows a traditional letter (date at top, recipient
block, greeting, 3 paragraphs, sign-off, signature), with no
`## Opening`-style mini-headers. Test each tone (professional /
confident / conversational) and verify the voice differs between
them.

## Files Touched

- `hirelens-backend/app/services/gpt_service.py` (new helper +
  rewrite prompt + cap raises + fallback)
- `hirelens-backend/app/services/ai_service.py` (same)
- `hirelens-backend/app/api/routes/cover_letter.py` (PostHog event)
- `hirelens-backend/tests/services/test_cover_letter.py` (new)
- `.agent/skills/analytics.md` (catalog entry)
- `docs/specs/phase-5/10-cover-letter-format-fix.md` (this file)
- `SESSION-STATE.md` (slice pointer)
