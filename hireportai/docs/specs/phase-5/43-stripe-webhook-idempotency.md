# Spec #43 — Stripe Webhook Idempotency

**Status:** Retroactive spec (code already shipped; this is a Rule-14 backfill)
**Owner:** Dhamo
**Created:** 2026-04-19
**Phase:** 5F (P5-S26c)
**Depends on:** Spec #11 (Stripe checkout + webhook — the feature this hardens)
**Supersedes:** the "Spec #22" citation in `.agent/skills/payments.md` — Spec #22 on disk is unrelated (phase-3 my-experience / phase-4 error-monitoring). The idempotency feature was shipped without a dedicated spec; this document closes that debt per CLAUDE.md Rule 14.

## 1. Problem Statement

Stripe delivers webhooks with at-least-once semantics. Duplicates happen in practice via:

- network-level retries (Stripe resends on non-2xx responses or timeouts);
- manual redelivery from the Stripe dashboard (test-mode and production);
- replay attacks against the webhook endpoint by an attacker who has captured a valid payload + signature.

Without deduplication, duplicate `checkout.session.completed` events would double-grant Pro (each firing `payment_completed` analytics, each mutating `Subscription`). Duplicate `customer.subscription.deleted` events would re-fire `subscription_cancelled` analytics and thrash the subscription row. Both are observable user-facing bugs (double analytics, inflated revenue counts, confused downstream dashboards).

## 2. Current Solution (shipped — what this spec documents)

The webhook handler uses a **SELECT-first-then-INSERT-then-flush-before-dispatch** pattern against a dedicated `stripe_events` dedup table. On duplicate `event.id`, the handler short-circuits with a no-op 200 response **before** any side effect runs. On a first delivery, the dedup row is inserted inside the same transaction as the dispatch — so a dispatch failure rolls back the dedup row too, allowing Stripe's next retry to process the event cleanly.

## 3. Data Model

Table `stripe_events` (ORM: `app/models/stripe_event.py`, migration: Phase-1 webhook migration):

| Column | Type | Nullable | Notes |
|---|---|:---:|---|
| `id` | `String(255)` **PK** | no | Stripe event id (`evt_…`) |
| `event_type` | `String(100)` | no | Stripe event type (e.g. `checkout.session.completed`) |
| `processed_at` | `DateTime` | no | Set by the handler at dispatch time |
| `created_at` | `DateTime` | no | `server_default=func.now()` — row insertion time |

No indexes beyond the PK on `id`. No `idempotency_key` column (Stripe's per-request idempotency key is distinct from `event.id` and not currently consumed). No `raw_event_json` column — debugging relies on Stripe dashboard's event log.

## 4. Algorithm (verbatim from `app/services/payment_service.py:174-204`)

```python
event_id = event.get("id", "")
event_type = event["type"]
data = event["data"]["object"]

# Idempotency: skip if this Stripe event was already processed.
if event_id:
    existing = (
        await db.execute(
            select(StripeEvent).where(StripeEvent.id == event_id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        logger.info("Duplicate Stripe event %s — skipping", event_id)
        return {"received": True, "event_type": event_type}
    db.add(
        StripeEvent(
            id=event_id,
            event_type=event_type,
            processed_at=datetime.now(tz=None),
        )
    )
    await db.flush()

if event_type == "checkout.session.completed":
    await _handle_checkout_completed(data, db)
elif event_type == "customer.subscription.deleted":
    await _handle_subscription_deleted(data, db)
else:
    logger.info("Ignoring unhandled Stripe event: %s", event_type)

return {"received": True, "event_type": event_type}
```

Key properties:

1. **Short-circuit before dispatch.** The SELECT runs first. If the row exists, the function returns without mutating anything — no analytics event, no `Subscription` update, no `home_state_service.invalidate()`.
2. **Flush-then-dispatch in one transaction.** `db.flush()` sends the INSERT to Postgres but does **not** commit. The dispatch (`_handle_checkout_completed` / `_handle_subscription_deleted`) runs within the same outer transaction opened by the per-request session in `app/db/session.py:38-46`.
3. **Rollback on dispatch failure.** `get_db` wraps the request in `try: yield; await commit except Exception: await rollback; raise`. If the dispatcher raises, the rollback unwinds both the dispatch's partial work **and** the StripeEvent INSERT. Stripe's retry then hits the SELECT-miss path and processes the event cleanly.
4. **Signature verification is upstream and unchanged.** `stripe.Webhook.construct_event` runs before the idempotency block; a signature failure raises `InvalidSignatureError` before any DB work.

## 5. Acceptance Criteria

- **AC-1 — First delivery processes.** A fresh `event.id` for a supported event type runs the dispatcher, mutates state (`Subscription.plan='pro'` for `checkout.session.completed`), fires the analytics event, and inserts the `stripe_events` row. Covered by: `test_webhook_activates_pro_plan` and `test_webhook_cancels_subscription` in `tests/test_payments.py`.
- **AC-2 — Duplicate delivery is a 200 no-op.** A second call with the same `event.id` returns 200 without any additional side effect. Exactly one row exists in `stripe_events` for that id. Covered by: `test_duplicate_webhook_is_idempotent` (`tests/test_payments.py:318-379`).
- **AC-3 — Invalid signature is rejected.** A payload that fails signature verification returns 400 and never touches the DB. Covered by: `test_webhook_rejects_invalid_signature`.
- **AC-4 — Dispatch failure rolls back the dedup row.** If the dispatcher raises after the StripeEvent flush, the session rollback (`get_db`) removes the dedup row. A fresh delivery of the same `event.id` afterward is processed normally — not silently skipped as a duplicate from the failed attempt. **New in this spec.** Covered by: `test_handler_exception_rolls_back_stripe_event_row` (`tests/test_payments.py`).

## 6. Test Plan

| Test | File:line | AC |
|---|---|---|
| `test_webhook_activates_pro_plan` (existing) | `tests/test_payments.py` | AC-1 |
| `test_webhook_cancels_subscription` (existing) | `tests/test_payments.py` | AC-1 |
| `test_duplicate_webhook_is_idempotent` (existing) | `tests/test_payments.py:318` | AC-2 |
| `test_webhook_rejects_invalid_signature` (existing) | `tests/test_payments.py` | AC-3 |
| `test_handler_exception_rolls_back_stripe_event_row` (**new this slice**) | `tests/test_payments.py` | AC-4 |

The AC-4 test invokes `payment_service.handle_webhook` directly (not via the HTTP client) and wraps the failing call in a SAVEPOINT (`db_session.begin_nested()`) to mirror production's per-request rollback without tearing down shared fixture state. After `savepoint.rollback()`, the test asserts (a) zero `stripe_events` rows for the event id, (b) a subsequent call with the same payload runs the dispatcher and flips the plan, (c) exactly one `stripe_events` row exists post-retry.

## 7. Out of Scope

- **INSERT-first-catch-IntegrityError pattern.** The plan outline for P5-S26c described an INSERT-first algorithm that returns 200 even under concurrent duplicate deliveries. The current SELECT-first pattern has a narrow edge case: two deliveries of the same `event.id` arriving concurrently on **separate DB connections** can both see a SELECT miss; one INSERT wins, the other raises `IntegrityError` which bubbles as a 500. Stripe's retry logic then hits the duplicate-SELECT path and processes cleanly. The user-visible effect is one transient 500 per true concurrent-duplicate pair — Stripe self-heals on retry. **Deferred**: revisit as a pattern refactor only if production logs show concurrent-delivery 500s with non-trivial frequency. Tracked in `SESSION-STATE.md` §Deferred Hygiene Items as `[S26c-defer]`.
- **`invoice.payment_failed` handling.** The handler acknowledges but does not act on this event today. Out of scope for idempotency work — that's a separate feature (dunning flow).
- **`idempotency_key` column.** Stripe sends a per-request idempotency key distinct from `event.id`. Not consumed today; no correctness issue — `event.id` alone is sufficient for dedup since Stripe guarantees unique event ids per event. Adding the column would be a no-op unless a future handler needed it.
- **`raw_event_json` column.** Debugging failed handlers could be easier with the raw payload persisted, but Stripe's dashboard event log already stores every event. No storage cost justifies duplicating it in our DB today.
- **Composite observability index `(event_type, processed_at)`.** No queries today run over these columns; the PK index on `id` is sufficient. Add only if an admin dashboard starts aggregating by event type over time.
- **Backfill of historical events from Stripe API.** Production has never accumulated real users (local dev-DB was wiped 2026-04-19, Railway DB is empty). No historical events to backfill.
- **Webhook signature verification hardening.** Already handled by `stripe.Webhook.construct_event` using `STRIPE_WEBHOOK_SECRET`. Out of scope.

## 8. Provenance

This spec is retroactive. The implementation was shipped under Spec #11 (Stripe checkout + webhook) or a later unnumbered slice — the original citation in `.agent/skills/payments.md` pointed at "Spec #22", but Spec #22 on disk covers unrelated topics (phase-3 my-experience, phase-4 error-monitoring). The 2026-04-17 doc-sync audit (CLAUDE.md Rule 14) flagged this kind of shipped-without-spec debt; this document closes it for webhook idempotency. Code references: `app/models/stripe_event.py`, `app/services/payment_service.py:145-204`, `app/db/session.py:38-46`, `tests/test_payments.py:318-379` and the new AC-4 test appended below it.
