---
description: Stripe checkout, webhooks, plan gating, free tier limits
---
# Payments Skill
## Overview
Stripe handles the $49/mo Pro subscription. Free tier gets 15
Foundation cards + ATS scanning. Pro unlocks the full library.
## Key Files
- Backend: `app/services/payment_service.py`, `app/api/routes/payments.py`
- Frontend: `src/components/PaywallModal.tsx`
## Flow
1. User hits 15-card wall → PaywallModal shows
2. Click "Upgrade" → POST /api/v1/payments/checkout → Stripe Checkout Session
3. User completes payment on Stripe-hosted page
4. Stripe webhook → POST /api/v1/payments/webhook → update subscription.plan = "pro"
5. Redirect back to app → full library unlocked
## Webhook Events Handled
- `checkout.session.completed` → activate Pro
- `customer.subscription.deleted` → downgrade to Free
- `invoice.payment_failed` → not yet implemented (silently acknowledged)
## Webhook Idempotency (Spec #22)
- Duplicate events are deduplicated via the `stripe_events` table (PK = Stripe event ID)
- Model: `app/models/stripe_event.py`
## Analytics Events
- `paywall_hit` — { cards_viewed, trigger, category_name } (frontend)
- `checkout_started` — { price_id, plan } (backend) / { trigger, plan, price_usd } (frontend)
- `payment_completed` — { plan, amount_total, currency } (backend, via webhook)
- `subscription_cancelled` — { plan } (backend, via webhook)
