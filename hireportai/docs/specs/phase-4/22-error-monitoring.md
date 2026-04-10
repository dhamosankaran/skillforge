# SPEC #22: Sentry Error Monitoring + Webhook Idempotency

## Status: Done
## Phase: 4
## Branch: main

---

## Problem

Production errors are invisible until users report them. Backend exceptions and
frontend crashes go untracked — there is no alerting, no stack trace aggregation,
and no performance baseline.

Additionally, Stripe webhook delivery is at-least-once. The current webhook
handler in `payment_service.handle_webhook()` processes every delivery, meaning a
duplicate `checkout.session.completed` event could flip a user to Pro twice or
fire duplicate analytics events.

## Solution

### Part A — Sentry Integration

**Backend:**
- Initialize `sentry-sdk[fastapi]` in the FastAPI lifespan with `SENTRY_DSN`
  from environment. Set `traces_sample_rate=0.1` for performance monitoring.
- After JWT validation in `get_current_user`, call `sentry_sdk.set_user()` to
  enrich error reports with user context (`id`, `email`).

**Frontend:**
- Initialize `@sentry/react` in `main.tsx` with `VITE_SENTRY_DSN`.
- Wrap `<App />` in `Sentry.ErrorBoundary` with a fallback UI showing
  "Something went wrong" and a reload button.

### Part B — Webhook Idempotency

- New `stripe_events` table: `id` (String PK = Stripe event ID), `event_type`,
  `processed_at`, `created_at`.
- Before processing a webhook event, check if the event ID already exists. If
  yes, return `200` immediately (idempotent). If no, insert the row and proceed.

## API Contract

No new endpoints. Existing `POST /api/v1/payments/webhook` gains idempotency.

## Data Model Changes

### New table: `stripe_events`

| Column        | Type         | Constraints       |
|---------------|--------------|-------------------|
| id            | String(255)  | PK (Stripe evt_*) |
| event_type    | String(100)  | NOT NULL          |
| processed_at  | DateTime     | NOT NULL          |
| created_at    | DateTime     | server_default=now |

Migration: Alembic autogenerate.

## Acceptance Criteria

- [x] AC-1: `sentry-sdk[fastapi]` is in requirements.txt.
- [x] AC-2: Sentry initializes on backend startup when `SENTRY_DSN` is set.
- [x] AC-3: Authenticated requests attach user context to Sentry scope.
- [x] AC-4: `@sentry/react` is in package.json.
- [x] AC-5: Frontend initializes Sentry when `VITE_SENTRY_DSN` is set.
- [x] AC-6: `<App />` is wrapped in `Sentry.ErrorBoundary` with fallback UI.
- [x] AC-7: Duplicate webhook with same Stripe event ID is a no-op (200).
- [x] AC-8: `test_duplicate_webhook_is_idempotent` passes.
- [x] AC-9: All existing tests continue to pass.

## Edge Cases

- `SENTRY_DSN` unset: Sentry SDK is a no-op — no crash, no network calls.
- `VITE_SENTRY_DSN` unset: Frontend Sentry init is skipped gracefully.
- Concurrent duplicate webhooks: PK constraint on `stripe_events.id` prevents
  double-insert; the second transaction gets an IntegrityError and returns 200.

## Dependencies

- Spec #11 (Stripe integration) — completed.
- PostgreSQL + Alembic — completed (Phase 0).

## Out of Scope

- Sentry release tracking / source maps upload (future CI task).
- Slack alerting integration for Sentry issues.
- Webhook retry queue / dead-letter handling.
