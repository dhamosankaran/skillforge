# Study Engine Skill

## Overview
The study engine is the core retention mechanic of SkillForge. It uses
the FSRS (Free Spaced Repetition Scheduler) algorithm to schedule card
reviews at optimal intervals based on individual memory patterns.

## Key Files
- Backend:
  - `app/services/study_service.py` — FSRS scheduling logic
  - `app/api/v1/routes/study.py` — API endpoints
  - `app/models/card_progress.py` — ORM model
  - `app/schemas/study.py` — Pydantic schemas
- Frontend:
  - `src/pages/DailyReview.tsx` — Daily 5 queue page
  - `src/components/study/FlipCard.tsx` — Card flip display component
  - `src/components/study/QuizPanel.tsx` — Rating submission component
  - `src/hooks/useStudyDashboard.ts` — Study dashboard data hook
- Tests:
  - `tests/test_study_service.py` — FSRS scheduling unit tests
  - `tests/test_study_api.py` — API integration tests

## FSRS Algorithm Details
- Library: `fsrs` (imported as `from fsrs import Card, Rating, Scheduler, State`)
- Ratings: Again (1), Hard (2), Good (3), Easy (4)
- State machine: New → Learning → Review → Relearning
- Key fields: `stability`, `difficulty_fsrs`, `due_date`, `state`
- Daily 5 = SELECT cards WHERE due_date <= NOW() ORDER BY due_date LIMIT 5

## API Contracts
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/study/daily` | GET | Required | Get today's due cards |
| `/api/v1/study/review` | POST | Required | Submit review rating |
| `/api/v1/study/progress` | GET | Required | Get overall progress |
| `/api/v1/study/experience` | POST | Required | Generate AI experience narrative |

## Analytics Events
- `card_reviewed` — { card_id, rating, time_spent_ms, fsrs_state, reps, lapses }
- `daily_review_started` — { total_due, session_id } (frontend)
- `daily_review_completed` — { cards_reviewed, session_id } (frontend)

## Testing Checklist
- [ ] FSRS "Good" rating increases interval by 2-4x
- [ ] FSRS "Again" rating resets card to today
- [ ] Daily 5 returns max 5 cards
- [ ] Daily 5 returns empty list when nothing is due
- [ ] Free users only get Foundation category cards
- [ ] XP is awarded on each review (calls gamification service)
