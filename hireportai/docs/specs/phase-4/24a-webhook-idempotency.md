# SPEC: Stripe Webhook Idempotency

## Status: Implemented — Spec Backfill Pending (P5-S26c)

## Code Pointers
- Model: `app/models/stripe_event.py` (`StripeEvent` — PK is the Stripe event id `evt_xxx`).
- Migration: `alembic/versions/83a02cb65464_add_stripe_events_table_for_webhook_.py`.
- Webhook handler: `app/services/payment_service.py` (consult for the dedupe query).
- Route: `app/api/routes/payments.py` (legacy) → also mounted under `/api/v1/payments` per `app/main.py:142`.
- Idempotency is **DB-backed** (not Redis as the playbook skill `security.md` originally described).
- Currently folded into the existing Phase-4 `22-error-monitoring.md` and `23-error-monitoring.md` specs — both reference it but neither spec is dedicated to idempotency.

## Problem
*(to be filled in during P5-S26c)*

## Solution
*(to be filled in during P5-S26c — document the DB-based dedupe flow and the retry-safe response shape)*

## Acceptance Criteria
*(to be filled in during P5-S26c — duplicate-webhook test, concurrent-delivery test)*

## Open Audit Items
- Known-broken per SESSION-STATE: duplicate webhook delivery could double-grant Pro. Verify during P5-S26c.

---
*Placeholder created during P5-S0b on 2026-04-17. Replace with full spec during P5-S26c.*
