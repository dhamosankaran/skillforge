# SPEC: Daily Email Reminders

## Status: Done

## Problem
Users forget to return to SkillForge after the initial excitement fades.
Spaced-repetition only works when cards are reviewed on schedule — a single
missed day compounds into an ever-growing backlog that discourages return.
A lightweight daily email that surfaces "cards due today" and the user's
streak acts as an external trigger that pulls users back before the habit
breaks.

## Solution
A scheduled job runs once per hour, finds users whose local time is ~7 AM
and who have opted in to daily reminders, queries their due-card count and
streak, renders an HTML email via a pre-built template, and sends it through
the Resend API. A new `email_preferences` table stores per-user opt-in,
frequency, and timezone. The email contains a deep link to the study
dashboard and an instant one-click unsubscribe link.

## Acceptance Criteria
- [ ] AC-1: Users with `daily_reminder = true` receive exactly one email per
      day at approximately their configured hour (default 07:00 local).
- [ ] AC-2: The email body shows the number of cards due today and the
      user's current streak length.
- [ ] AC-3: Users with 0 cards due do NOT receive an email that day.
- [ ] AC-4: The email contains a working deep link to `/study` and a
      one-click unsubscribe link that disables `daily_reminder`.
- [ ] AC-5: If the Resend API returns a transient error (429, 5xx), the
      sender retries up to 3 times with exponential backoff.
- [ ] AC-6: A `email_sent` PostHog event is fired for each successfully
      delivered email.
- [ ] AC-7: The system sends zero emails to users who have opted out or
      whose accounts are deactivated.

---

## Data Model

### Table: `email_preferences`

| Column           | Type            | Constraints                                | Notes                                                   |
|------------------|-----------------|--------------------------------------------|---------------------------------------------------------|
| `user_id`        | `String(36)` PK | FK → `users.id`, `ON DELETE CASCADE`      | One row per user; created on first opt-in or signup      |
| `daily_reminder` | `Boolean`       | `NOT NULL`, default `true`                 | Master toggle for daily emails                           |
| `frequency`      | `String(20)`    | `NOT NULL`, default `'daily'`              | `daily` · `weekdays` · `none`                            |
| `preferred_hour` | `Integer`       | `NOT NULL`, default `7`, CHECK 0–23        | Hour in user's timezone when the email should arrive     |
| `timezone`       | `String(50)`    | `NOT NULL`, default `'UTC'`                | IANA tz name, e.g. `America/New_York`, `Asia/Kolkata`    |
| `unsubscribe_token` | `String(64)` | `NOT NULL`, `UNIQUE`                       | Random token for one-click unsubscribe without auth      |
| `created_at`     | `DateTime(tz)`  | `TimestampMixin`                           |                                                          |
| `updated_at`     | `DateTime(tz)`  | `TimestampMixin`                           |                                                          |

**Indexes:** PK on `user_id`, unique on `unsubscribe_token`.

### Alembic migration
Single migration: `alembic revision --autogenerate -m "add email_preferences table"`.
Backfill: insert a row for every existing user with defaults (`daily_reminder=true`,
`frequency='daily'`, `preferred_hour=7`, `timezone='UTC'`, random `unsubscribe_token`).

---

## Email Provider — Resend

### Why Resend
- Simple REST API, generous free tier (100 emails/day, 3 000/month).
- First-class support for HTML templates and one-click unsubscribe headers.
- Already listed as the email provider in `AGENTS.md`.

### Integration
- Env var: `RESEND_API_KEY` (stored in Railway dashboard, never in code).
- Env var: `RESEND_FROM_ADDRESS` (e.g. `reminders@skillforge.app`).
- SDK: `resend` Python package (or raw `httpx` POST to `https://api.resend.com/emails`).
- Headers: include `List-Unsubscribe` and `List-Unsubscribe-Post` for
  RFC 8058 one-click unsubscribe support.

### Send Abstraction — `email_service.py`
```python
async def send_email(
    to: str,
    subject: str,
    html: str,
    unsubscribe_url: str,
) -> dict:
    """Send a single transactional email via Resend. Retries on 429/5xx."""
```
Wraps Resend API with:
- 3 retries, exponential backoff (1s, 2s, 4s).
- Returns Resend message ID on success.
- Raises `EmailSendError` on permanent failure (4xx other than 429).

---

## Email Template

Subject line: `You have {cards_due} cards due — keep your {streak}-day streak alive!`
(If streak is 0: `You have {cards_due} cards due — start a new streak today!`)

### Template structure (`app/templates/daily_reminder.html`)
```
┌────────────────────────────────────┐
│  SkillForge logo (brand header)    │
├────────────────────────────────────┤
│  Hey {name}!                       │
│                                    │
│  📚 {cards_due} cards due today    │
│  🔥 {streak}-day streak            │
│                                    │
│  [Start Studying →] (deep link)    │
├────────────────────────────────────┤
│  Footer:                           │
│  Unsubscribe · Manage preferences  │
└────────────────────────────────────┘
```

- Deep link: `{APP_URL}/study?utm_source=email&utm_medium=daily_reminder`
- Unsubscribe link: `{API_URL}/api/v1/email-preferences/unsubscribe?token={token}`
- Inline CSS only (email client compatibility).
- Responsive: single-column, max-width 600px.

---

## Scheduled Task — Cron Approach

### Strategy: hourly sweep by timezone bucket

A single cron job runs every hour (`:00`). On each tick it:
1. Computes the current UTC hour.
2. Queries `email_preferences` for users whose `preferred_hour` matches the
   current hour in their timezone:
   ```sql
   SELECT ep.user_id, ep.timezone, u.email, u.name, ep.unsubscribe_token
   FROM email_preferences ep
   JOIN users u ON u.id = ep.user_id
   WHERE ep.daily_reminder = true
     AND ep.frequency != 'none'
     AND (ep.frequency = 'daily'
          OR (ep.frequency = 'weekdays'
              AND EXTRACT(DOW FROM NOW() AT TIME ZONE ep.timezone) BETWEEN 1 AND 5))
     AND ep.preferred_hour = EXTRACT(HOUR FROM NOW() AT TIME ZONE ep.timezone)
   ```
3. For each user, queries `card_progress` for cards where `due_date <= now()`.
4. Skips users with 0 cards due (AC-3).
5. Fetches `gamification_stats.current_streak` for the user.
6. Renders the email template and calls `email_service.send_email()`.
7. Fires `email_sent` PostHog event.

### Deduplication
To prevent double-sends if the job is slow or re-triggered:
- Maintain an `email_send_log` table (or use a Redis key
  `email:daily:{user_id}:{date}`) to record today's send.
- Skip users who already have a log entry for today.

### Deployment
- **Railway Cron Job**: Railway supports cron services. Create a cron service
  that runs `python -m app.jobs.daily_reminder` on schedule `0 * * * *` (every
  hour at :00).
- Alternatively, use an internal scheduler (APScheduler or the `/schedule`
  skill) if Railway cron is unavailable.

### `email_send_log` table (dedup)

> **Superseded by `docs/specs/phase-6/13-pro-digest-opt-out.md` §5.2
> (slice 6.13, `d6ddcb6`).** The canonical `email_log` table design
> lives in slice 6.13 — additive migration, refined column rationale,
> Phase-6 model conventions (UUIDPrimaryKeyMixin, denormalized FKs,
> CASCADE on user delete, composite `(user_id, sent_date)` index). The
> `email_send_log` shape below is preserved as the historical Phase-2
> proposal; future readers should treat slice 6.13 §5.2 as authoritative.

| Column     | Type            | Constraints                    |
|------------|-----------------|--------------------------------|
| `id`       | `String(36)` PK | `UUIDPrimaryKeyMixin`         |
| `user_id`  | `String(36)` FK | → `users.id`, `NOT NULL`      |
| `email_type` | `String(30)`  | `NOT NULL` (e.g. `daily_reminder`) |
| `sent_date`| `Date`          | `NOT NULL`                     |
| `resend_id`| `String(100)`   | Nullable; Resend message ID    |
| `created_at`| `DateTime(tz)` | `TimestampMixin`               |

**Unique:** `(user_id, email_type, sent_date)` — prevents double-send.

---

## Analytics Events (PostHog)

| Event           | Properties                                                     |
|-----------------|----------------------------------------------------------------|
| `email_sent`    | `{ user_id, type: "daily_reminder", cards_due, streak }`      |
| `email_clicked` | `{ user_id, type: "daily_reminder", utm_source }` (via UTM)   |
| `email_unsubscribed` | `{ user_id, method: "one_click" \| "preferences" }`      |

---

## Edge Cases
- **User changes timezone mid-day**: Next email uses the new timezone;
  may result in 0 or 2 emails that transition day. Acceptable.
- **Resend rate limit**: 429 triggers retry with backoff. If all retries
  fail, log the error and skip — do not block other users' emails.
- **User deletes account**: `ON DELETE CASCADE` removes `email_preferences`
  and `email_send_log` rows; no orphaned sends.
- **DST transitions**: Using IANA timezone names with `AT TIME ZONE` handles
  DST correctly in PostgreSQL.
- **Massive user base (>3 000/month free tier)**: Upgrade Resend plan or
  switch to SendGrid. The `email_service.py` abstraction makes this a
  one-file change.
- **Backfill existing users**: Migration inserts default rows. All existing
  users are opted IN by default (CAN-SPAM compliant because this is
  transactional/account-related email, not marketing).

## Dependencies
- Spec #05 (FSRS daily review) — `card_progress` table for due-card count
- Spec #10 (streaks/XP) — `gamification_stats` for streak data
- Spec #16 (email preferences API) — opt-out endpoint and preferences UI
- Resend account + verified sending domain
- Railway cron service (or alternative scheduler)

## Test Plan

### Unit tests
- `email_service.send_email()` with mocked Resend API:
  - Happy path → returns message ID
  - 429 response → retries 3 times then succeeds
  - 500 response → retries then raises `EmailSendError`
  - 400 response → raises immediately (no retry)
- `reminder_service.build_email_body()`:
  - Renders correct card count and streak in template
  - Streak = 0 uses alternate subject line
  - Unsubscribe link contains correct token
- `reminder_service.get_eligible_users()`:
  - Includes users with `daily_reminder=true` and matching hour
  - Excludes users with `frequency='none'`
  - Excludes users with `frequency='weekdays'` on Saturday/Sunday
  - Excludes users with 0 cards due
  - Excludes users already sent today (dedup)

### Integration tests
- Full cron cycle with mocked Resend:
  - Creates 3 test users (opted-in, opted-out, 0 cards due)
  - Runs the job → exactly 1 email sent
  - `email_send_log` row created for the sent user
  - Re-run the job → 0 emails sent (dedup)
- Unsubscribe flow:
  - `GET /unsubscribe?token=...` → sets `daily_reminder=false`
  - Next cron run skips that user

### Manual verification
- Sign up, wait for (or trigger) the cron job, confirm email arrives
- Click the study link in the email → lands on `/study` with UTM params
- Click unsubscribe → no more emails the next day
- Change timezone in preferences → email arrives at new local hour
