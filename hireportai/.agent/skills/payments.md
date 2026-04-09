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
4. Stripe webhook → POST /api/v1/payments/webhook → update user.plan = "pro"
5. Redirect back to app → full library unlocked
## Webhook Events to Handle
- `checkout.session.completed` → activate Pro
- `customer.subscription.deleted` → downgrade to Free
- `invoice.payment_failed` → grace period, email user
## Analytics Events
- `paywall_hit` — { card_count_viewed, trigger_page }
- `checkout_started` — { price_id }
- `payment_completed` — { amount, plan }
- `subscription_cancelled` — { months_active, reason }
