---
description: ATS resume scanning, scoring, keyword extraction, bullet rewriting, auto-tracker
---
# ATS Scanner Skill

## Overview
The ATS scanner is the free acquisition engine. Users upload a
resume + paste a job description, get an ATS compatibility score,
see skill gaps, and optionally rewrite bullets or the full resume.
Every successful scan also auto-populates the application tracker.

## Key Files
- **Scoring & parsing (`app/services/`):**
  - `parser.py` — resume PDF/DOCX → plain text
  - `text_cleaner.py` — normalization
  - `keywords.py` — ATS keyword extraction rules + taxonomy
  - `skill_taxonomy.py` — canonical skill names + aliases
  - `scorer.py` — ATS score computation
  - `bullet_analyzer.py` — detects weak bullets (metrics, verbs)
  - `formatter_check.py` — flags ATS-hostile formatting
    (tables, images, columns, headers)
  - `resume_templates.py` — ATS-safe rewrite templates
- **LLM-powered rewrites (`app/services/`):**
  - `ai_service.py`, `gpt_service.py` — call
    `generate_for_task(task="resume_rewrite" | "rewrite_bullets" |
    "ats_keyword_extraction", …)`
- **Tracker integration:**
  - `app/services/tracker_service_v2.py` — auto-creates a
    `tracker_applications_v2` row after each scan
- **Routes:** `app/api/routes/analyze.py`, `rewrite.py`
- **Frontend:** `src/pages/Analyze.tsx`, `Results.tsx`,
  `src/hooks/useAnalysis.ts`

## Auto-Save to Tracker
After a successful ATS scan the backend writes a row into
`tracker_applications_v2` with:
`user_id`, `company`, `role`, `ats_score`, `scan_id`,
`skills_matched`, `skills_missing`, `status='scanned'`.

This fires the PostHog event `tracker_auto_created_from_scan` and
means the user's "Tracker" page is never empty once they've run a
scan. The scan result links back to the tracker row via `scan_id`.

## LLM Task Mapping
See the [llm-strategy skill](llm-strategy.md) for the full router,
but in short:

| Operation | Task name | Tier |
|-----------|-----------|------|
| Parse JD → keyword set | `ats_keyword_extraction` | fast |
| Rewrite individual bullets | `rewrite_bullets` | fast |
| Full resume rewrite | `resume_rewrite` | reasoning |
| Tailored cover letter | `cover_letter` | reasoning |

## Analytics Events
- `ats_scanned` — `{user_id, scan_id, resume_id, job_description_length}`
- `tracker_auto_created_from_scan` — `{user_id, company, role, matched_skills}`

## Free-Tier Limits
Free users get a small monthly scan quota enforced in
`usage_service.py`; when exceeded the route returns 403 and the
frontend shows `PaywallModal` with `trigger: 'scan_limit'`.
See the [payments skill](payments.md).
