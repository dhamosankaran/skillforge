---
description: Streaks, XP, badges, skill radar, activity heatmap
---
# Gamification Skill
## Overview
Gamification provides the psychological hooks for daily return.
Streaks create loss aversion. XP creates progress feeling.
Skill radar visualizes coverage. Heatmap shows consistency.
## Key Files
- Backend: `app/services/gamification_service.py`, `app/api/routes/gamification.py`
- Frontend: `src/components/profile/StreakBadge.tsx`, `src/pages/Profile.tsx`
## Streak Rules
- Streak increments when user completes at least 1 review in a calendar day
- Streak resets to 0 if a day is missed (midnight UTC)
- Streak freeze: Pro users get 1 free freeze per week
## XP Rules
- Card reviewed: 10 XP
- Quiz correct: 25 XP
- Daily 5 completed: 50 XP bonus
- Mission day completed: 75 XP bonus
## Analytics Events
- `streak_incremented` — { new_length, user_id }
- `streak_broken` — { previous_length, user_id }
- `badge_earned` — { badge_id, badge_name }
