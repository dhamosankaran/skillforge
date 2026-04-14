---
description: Stripe checkout, webhooks, plan gating, free tier limits, geo pricing, usage caps
---
# Payments Skill

## Overview
Stripe handles the Pro subscription. Free tier users get limited
access (15 Foundation cards, a small number of free ATS scans, 3
interview-question generations per month) and hit a PaywallModal
that kicks off Stripe Checkout. Pricing is **localized by IP**
(see [geo-pricing](geo-pricing.md)).

## Key Files
- Backend:
  - `app/services/payment_service.py` — checkout + webhook
  - `app/services/geo_pricing_service.py` — INR/USD routing
  - `app/services/usage_service.py` — free-tier quota enforcement
  - `app/api/v1/routes/payments.py` — routes
  - `app/models/subscription.py`, `payment.py`, `stripe_event.py`,
    `usage_log.py`, `usage_limit.py`
- Frontend:
  - `src/components/PaywallModal.tsx`
  - `src/hooks/usePricing.ts`
  - `src/context/UsageContext.tsx` (`useUsage()` hook)

## Checkout Flow
1. User hits a paywall trigger (15-card wall, scan limit, locked
   category, daily review, interview limit, gap study).
2. `PaywallModal` shows, reading `pricing.price_display` from
   `usePricing()` so the amount matches the visitor's country.
3. Click **Upgrade** → `POST /api/v1/payments/checkout` with
   `{currency}` → backend creates a Stripe Customer on first call,
   then creates a Checkout Session using the matching price id
   (`STRIPE_PRO_PRICE_ID` or `STRIPE_PRO_PRICE_ID_INR`).
4. Backend fires `checkout_started` PostHog event.
5. User completes payment on Stripe-hosted page.
6. Stripe webhook → `POST /api/v1/payments/webhook` → update
   `subscriptions.plan = "pro"` and fire `payment_completed`.
7. Redirect back to `/pricing` → frontend fires a second
   `payment_completed` event with `source: 'stripe_checkout_return'`.

## Geo Pricing
Price display + currency come from `GET /api/v1/payments/pricing`.
India → INR ₹999/mo; everyone else → USD $49/mo. See
[geo-pricing skill](geo-pricing.md) for full details.

## Webhook Events Handled
- `checkout.session.completed` → activate Pro, fire `payment_completed`
- `customer.subscription.deleted` → downgrade to Free, fire
  `subscription_cancelled`
- `invoice.payment_failed` → acknowledged but not yet acted on

## Webhook Idempotency (Spec #22)
- Dedup table: `stripe_events` (`app/models/stripe_event.py`)
- Primary key = Stripe event id (`evt_…`)
- Flow in `payment_service.handle_webhook()`:
  1. Verify signature with `STRIPE_WEBHOOK_SECRET`.
  2. `SELECT` from `stripe_events` by event id.
  3. If present → return `{status: "duplicate"}`, do nothing.
  4. Otherwise insert row + process body in the same transaction.
- Safe to replay the entire Stripe event log.

## Usage Limits (Free Tier)
- Model: `app/models/usage_log.py` — rows per (user, feature, timestamp)
- Config: `app/models/usage_limit.py` — plan × feature → cap
- Enforcement: `app/services/usage_service.py` → `check_and_increment()`
- **Free plan caps:**
  - ATS scans: small monthly allowance (configured per deploy)
  - Interview questions: **3 per month**
  - Foundation cards: 15 lifetime
- Pro/Enterprise: unlimited (`usage_limit` row absent or very high).
- On cap hit, the service raises a 403 that the frontend catches and
  converts into a PaywallModal with the matching `trigger`.

## Frontend Hooks
- **`usePricing()`** (`src/hooks/usePricing.ts`) — loads current
  pricing, returns `{pricing, isLoading}`. Used by LandingPage,
  Pricing page, and PaywallModal. Defaults keep rendering working
  before the fetch resolves.
- **`useUsage()`** (`src/context/UsageContext.tsx`) — exposes the
  user's plan, remaining scan/interview counts, and an
  `openPaywall(trigger, context)` helper. Any component that wants
  to gate an action calls this.

## PostHog Events
Property names below reflect the current code.

| Event | Fired by | Properties |
|-------|----------|-----------|
| `paywall_hit` | `PaywallModal.tsx` | `{trigger, category_name?, cards_viewed?}` |
| `checkout_started` | `PaywallModal.tsx` (FE) / `payment_service.py` (BE) | FE: `{trigger, plan, price, currency}` · BE: `{user_id, price_id, plan}` |
| `payment_completed` | `payment_service.py` webhook / `Pricing.tsx` | BE: `{user_id, plan, amount_total, currency}` · FE: `{plan, price, currency, source: 'stripe_checkout_return'}` |
| `subscription_cancelled` | `payment_service.py` webhook | `{user_id, plan}` |

Paywall triggers in the frontend:
`scan_limit`, `card_limit`, `locked_category`, `daily_review`,
`interview_limit`, `skill_gap_study`.
