---
description: Daily email reminders, email preferences, SendGrid/Resend integration
---

# Notifications Skill

## Overview
Daily email reminders drive retention by pulling users back to their
FSRS queue. Without reminders, users forget the app exists — streaks
break and churn spikes.

## Key Files
- Backend:
  - `app/services/email_service.py` — email sending abstraction
  - `app/services/reminder_service.py` — daily digest logic
  - `app/api/routes/email_prefs.py` — preference endpoints
  - `app/models/email_preference.py` — opt-out model
- Templates:
  - `app/templates/daily_reminder.html` — email template

## Email Provider
- Primary: Resend (simple API, good free tier)
- Fallback: SendGrid
- API key in env: `RESEND_API_KEY`

## Daily Digest Logic
1. Cron job runs at 7 AM user's local time (or UTC default)
2. Query: users WHERE has_due_cards AND email_opted_in
3. For each user: count due cards, current streak length
4. Send: "You have {N} cards due today. Keep your {streak}-day streak alive!"

## Analytics Events
- `email_sent` — { user_id, type: "daily_reminder", cards_due }
- `email_clicked` — { user_id, type, utm_source }