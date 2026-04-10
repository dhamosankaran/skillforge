# SPEC: Email Preferences API

## Status: Done

## Problem
Users need control over the daily email reminders introduced in Spec #15.
Without an opt-out mechanism, we risk spam complaints, poor deliverability
reputation, and potential CAN-SPAM / GDPR violations. Users should be able
to change their reminder frequency, preferred send hour, timezone, and fully
unsubscribe — both from within the app and via a one-click link in the email
itself.

## Solution
A set of REST endpoints under `/api/v1/email-preferences` that allow
authenticated users to read and update their email preferences, plus a
public (unauthenticated) unsubscribe endpoint that accepts a secure token
from the email footer. A minimal React settings panel in the frontend lets
users toggle and configure their preferences.

## Acceptance Criteria
- [ ] AC-1: `GET /api/v1/email-preferences` returns the current user's
      preferences (daily_reminder, frequency, preferred_hour, timezone).
- [ ] AC-2: `PATCH /api/v1/email-preferences` updates any subset of
      (daily_reminder, frequency, preferred_hour, timezone) and returns
      the updated row.
- [ ] AC-3: `GET /api/v1/email-preferences/unsubscribe?token={token}`
      sets `daily_reminder = false` without requiring authentication and
      redirects to a confirmation page.
- [ ] AC-4: Invalid or expired tokens return `404` on the unsubscribe
      endpoint — no information leakage about user existence.
- [ ] AC-5: Changing `daily_reminder` to `false` fires an
      `email_unsubscribed` PostHog event.
- [ ] AC-6: The frontend settings panel reflects the current state and
      allows toggling all fields.

---

## API Contract

Base path: `/api/v1/email-preferences`

### GET `/` — Read Preferences

Auth: `Depends(get_current_user)`.

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "daily_reminder": true,
  "frequency": "daily",
  "preferred_hour": 7,
  "timezone": "America/New_York"
}
```

If the user has no `email_preferences` row yet (edge case for users created
before the backfill migration), create one with defaults and return it.

**Errors:** `401` unauthenticated.

---

### PATCH `/` — Update Preferences

Auth: `Depends(get_current_user)`.

**Request** (all fields optional):
```json
{
  "daily_reminder": false,
  "frequency": "weekdays",
  "preferred_hour": 9,
  "timezone": "Asia/Kolkata"
}
```

**Validation:**
- `frequency` must be one of: `daily`, `weekdays`, `none`.
- `preferred_hour` must be 0–23.
- `timezone` must be a valid IANA timezone string (validated via
  `zoneinfo.ZoneInfo`).
- Setting `frequency = 'none'` also sets `daily_reminder = false`.
- Setting `daily_reminder = true` with `frequency = 'none'` → auto-correct
  `frequency` to `'daily'`.

**Response:** `200 OK` (same shape as GET).

**Errors:**
- `401` unauthenticated
- `422` invalid field value (bad timezone, hour out of range, invalid frequency)

**PostHog events:**
- `email_preferences_updated` — `{ fields_changed: [...], new_values: {...} }`
- `email_unsubscribed` — fired additionally when `daily_reminder` transitions
  from `true` to `false`
- `email_resubscribed` — fired when `daily_reminder` transitions from `false`
  to `true`

---

### GET `/unsubscribe` — One-Click Unsubscribe (Public)

Auth: **None** (public endpoint). Token-based authentication.

**Query params:** `token` (required, string).

**Behavior:**
1. Look up `email_preferences` row by `unsubscribe_token`.
2. If not found → return `404` with generic "Invalid link" message.
3. Set `daily_reminder = false`.
4. Fire `email_unsubscribed` PostHog event with `method: "one_click"`.
5. Redirect (`302`) to `{APP_URL}/unsubscribed` — a static confirmation page.

**Why GET, not POST?**
Email clients (especially Apple Mail and Gmail) support RFC 8058 one-click
unsubscribe via a POST to the `List-Unsubscribe` header URL. We implement
*both*:
- The `List-Unsubscribe` / `List-Unsubscribe-Post` headers use POST
  (handled by a separate `POST /unsubscribe` endpoint with the same logic).
- The visible footer link uses GET for maximum user-agent compatibility.

### POST `/unsubscribe` — RFC 8058 One-Click (Public)

**Request body:** `List-Unsubscribe=One-Click` (form-encoded, per RFC 8058).
**Query params:** `token` (required).
**Behavior:** Same as GET version. Returns `200 OK` (no redirect).

---

## Frontend: Settings Panel

### Location
New section in the existing user settings/profile page.

### UI Components
```
┌─ Email Notifications ─────────────────────┐
│                                           │
│  Daily Reminders    [Toggle ON/OFF]       │
│                                           │
│  Frequency          [Daily ▼]             │
│                     Daily / Weekdays      │
│                                           │
│  Send Time          [07:00 ▼]             │
│                     Dropdown: 00–23       │
│                                           │
│  Timezone           [America/New_York ▼]  │
│                     Searchable dropdown   │
│                                           │
│  [Save Changes]                           │
└───────────────────────────────────────────┘
```

- Toggle OFF → grays out frequency/time/timezone fields.
- Save → `PATCH /api/v1/email-preferences`.
- On mount → `GET /api/v1/email-preferences` to populate.
- PostHog `capture('email_preferences_viewed')` on mount.
- PostHog `capture('email_preferences_saved')` on save.

### Unsubscribed Confirmation Page (`/unsubscribed`)
Simple static page:
- "You've been unsubscribed from daily reminders."
- "Changed your mind? [Re-enable in settings →]"
- Link goes to the settings panel.

---

## Edge Cases
- **User clicks unsubscribe link twice**: Second click is a no-op (already
  `daily_reminder = false`). Still returns success redirect.
- **Token collision**: `unsubscribe_token` is 64 chars of `secrets.token_hex(32)`.
  Collision probability is negligible. Unique constraint catches it on insert.
- **No email_preferences row**: Both GET and PATCH endpoints auto-create a
  default row if missing (lazy initialization).
- **Invalid IANA timezone**: Validated server-side via `zoneinfo.ZoneInfo`.
  Returns `422` with "Invalid timezone: {value}".
- **Concurrent PATCH requests**: Last-write-wins is acceptable for preferences.
- **Resubscribe after unsubscribe**: Setting `daily_reminder = true` via PATCH
  is the only way to re-enable. The unsubscribe token is NOT rotated on
  resubscribe — rotating would invalidate future email links sent before the
  rotation.

## Dependencies
- Spec #15 (daily email reminders) — defines `email_preferences` table and
  sends the emails that link here
- Users table (FK)
- Frontend settings page (may need to be created or extended)

## Test Plan

### Unit tests
- `PATCH` validation:
  - Valid timezone → accepted
  - Invalid timezone (e.g. `Foo/Bar`) → `422`
  - `preferred_hour = -1` or `24` → `422`
  - `frequency = 'invalid'` → `422`
  - `frequency = 'none'` → also sets `daily_reminder = false`
  - `daily_reminder = true` + `frequency = 'none'` → auto-corrects to `'daily'`
- Unsubscribe token lookup:
  - Valid token → sets `daily_reminder = false`
  - Invalid token → `404`
  - Already unsubscribed → still returns success (idempotent)
- PostHog events:
  - Transition `true → false` fires `email_unsubscribed`
  - Transition `false → true` fires `email_resubscribed`
  - No transition (same value) fires neither

### Integration tests
- `GET /email-preferences` for new user → auto-creates default row, returns 200
- `PATCH /email-preferences` → updates and returns new values
- `GET /unsubscribe?token=valid` → 302 redirect, `daily_reminder` now false
- `GET /unsubscribe?token=invalid` → 404
- `POST /unsubscribe?token=valid` → 200, `daily_reminder` now false
- Auth enforcement: `GET /` and `PATCH /` return `401` without token;
  `GET /unsubscribe` works without auth (public)

### Manual verification
- Open settings panel → see current preferences
- Toggle off → save → re-open → toggle is off
- Receive daily email → click unsubscribe link → see confirmation page
- Re-open settings → toggle is off
- Re-enable → save → receive email next day
