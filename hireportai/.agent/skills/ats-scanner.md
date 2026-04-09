---
description: ATS resume scanning, scoring, skill gap extraction, resume rewrite
---
# ATS Scanner Skill
## Overview
The ATS scanner is the free acquisition engine. Users upload a resume,
get an ATS compatibility score, see skill gaps, and optionally rewrite.
## Key Files
- Backend: `app/services/tracker_service_v2.py`, `app/api/routes/tracker.py`
- Frontend: existing HireLens ATS UI
## Analytics Events
- `ats_scanned` — { score, gaps_found: int, file_type }
- `resume_rewritten` — { original_score, new_score }
