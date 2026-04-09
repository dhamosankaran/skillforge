---
description: Interview sprint — countdown timer, daily targets, focused card set
---
# Mission Mode Skill
## Overview
Mission Mode is a time-bound study sprint for Interview-Preppers.
User sets a target date (e.g., "Google interview in 14 days"),
selects categories, and gets daily card targets with a countdown.
## Key Files
- Backend: `app/services/mission_service.py`, `app/api/routes/mission.py`
- Frontend: `src/pages/MissionMode.tsx`, `src/components/mission/Countdown.tsx`
## Mission Logic
- User creates mission: { target_date, category_ids[], daily_card_target }
- System calculates: total_cards / days_remaining = daily_target
- Each day: pull daily_target cards from selected categories (FSRS-prioritized)
- Countdown UI: "12 days left — 8 cards today"
- Completion: "Mission complete! You covered 95% of RAG + System Design"
## Analytics Events
- `mission_created` — { days, categories, total_cards }
- `mission_day_completed` — { day_number, cards_done, days_remaining }
- `mission_completed` — { total_days, coverage_pct }
- `mission_abandoned` — { day_abandoned, reason }
