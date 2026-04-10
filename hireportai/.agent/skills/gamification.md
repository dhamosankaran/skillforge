---
description: Streaks, XP, badges, skill radar, activity heatmap
---
# Gamification Skill
## Overview
Gamification provides the psychological hooks for daily return.
Streaks create loss aversion. XP creates progress feeling.
Skill radar visualizes coverage. Heatmap shows consistency.
## Key Files
- Backend: `app/services/gamification_service.py`, `app/api/v1/routes/gamification.py`
- Frontend: `src/components/profile/StreakBadge.tsx`, `src/pages/Profile.tsx`
## Streak Rules
- Streak increments when user completes at least 1 review in a calendar day
- Streak resets to 0 if a day is missed (midnight UTC)
- Streak freeze: stubbed in the model (`freezes_available`, `freeze_week_start`) but not yet implemented — the nightly job that grants Pro freezes does not exist yet
## XP Rules
- Card reviewed: 10 XP (source: `review`)
- Daily 5 completed: 50 XP bonus (source: `daily_complete`)
- Mission day completed: 50 XP bonus (reuses `daily_complete` source)
- Quiz correct: 25 XP (source: `quiz`) — defined in XP_RULES but not awarded anywhere yet
## Analytics Events
- `streak_incremented` — { new_length, previous }
- `streak_broken` — { previous_length }
- `badge_earned` — { badge_id, badge_name }
- `xp_awarded` — { amount, source, new_total }
