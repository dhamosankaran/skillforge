# Stripe Go-Live Checklist

## Overview

This runbook covers switching SkillForge from Stripe test mode to live mode.
Every step must be completed in order. Do NOT skip the verification steps.

**Estimated time:** 30-45 minutes

---

## Pre-flight

- [ ] All Phase 4 specs are complete and deployed.
- [ ] Sentry is capturing errors correctly.
- [ ] PostHog is receiving events.
- [ ] All tests pass on main branch.
- [ ] You have access to the Stripe Dashboard (live mode).
- [ ] You have access to Railway environment variables.

---

## Checklist

### 1. Create Live-Mode Product & Price

- [ ] Open [Stripe Dashboard](https://dashboard.stripe.com) → toggle to **Live mode** (top-right).
- [ ] Go to **Products** → **Add product**.
- [ ] Create the Pro plan product:
  - Name: `SkillForge Pro`
  - Price: `$49.00 / month` (recurring)
  - Currency: USD
- [ ] Copy the live **Price ID** (starts with `price_`).

### 2. Create Live-Mode Webhook Endpoint

- [ ] Go to **Developers** → **Webhooks** → **Add endpoint**.
- [ ] Endpoint URL: `https://api.skillforge.app/api/v1/payments/webhook`
- [ ] Events to listen for:
  - `checkout.session.completed`
  - `customer.subscription.deleted`
  - `invoice.payment_failed` (future use)
- [ ] Copy the **Signing secret** (starts with `whsec_`).

### 3. Get Live API Keys

- [ ] Go to **Developers** → **API keys** (live mode).
- [ ] Copy the **Secret key** (starts with `sk_live_`).
- [ ] Note: Publishable key is not needed (we use server-side Checkout).

### 4. Update Railway Environment Variables

- [ ] Open Railway Dashboard → SkillForge backend service → **Variables**.
- [ ] Update these variables:

| Variable | Old Value | New Value |
|----------|-----------|-----------|
| `STRIPE_SECRET_KEY` | `sk_test_...` | `sk_live_...` |
| `STRIPE_PRO_PRICE_ID` | `price_test_...` | `price_...` (live) |
| `STRIPE_WEBHOOK_SECRET` | `whsec_test_...` | `whsec_...` (live) |

- [ ] Click **Deploy** to apply changes (Railway auto-deploys on variable change).

### 5. Verify Webhook Connectivity

- [ ] In Stripe Dashboard → Webhooks → select the live endpoint.
- [ ] Click **Send test webhook** → choose `checkout.session.completed`.
- [ ] Verify Railway logs show the event was received and returned 200.
- [ ] Verify the event appears in the `stripe_events` table (idempotency check).

### 6. Test with a Real $1 Charge

- [ ] Create a temporary test price in live mode:
  - Product: `SkillForge Pro`
  - Price: `$1.00 / month` (recurring)
  - Copy the temporary Price ID.
- [ ] Temporarily set `STRIPE_PRO_PRICE_ID` to the $1 price in Railway.
- [ ] Wait for deploy to complete.
- [ ] Open SkillForge → trigger the paywall → complete checkout with a real card.
- [ ] Verify in the Stripe Dashboard:
  - [ ] Payment of $1.00 appears in **Payments**.
  - [ ] Customer was created.
  - [ ] Subscription is active.
- [ ] Verify in the app:
  - [ ] User's plan flipped to `pro`.
  - [ ] PostHog received `payment_completed` event.
  - [ ] Sentry has no errors.
- [ ] Cancel the test subscription in Stripe Dashboard.
- [ ] Verify:
  - [ ] `customer.subscription.deleted` webhook fires.
  - [ ] User's plan flipped back to `free`.
- [ ] Refund the $1 charge in Stripe Dashboard → **Payments** → **Refund**.

### 7. Switch to Real Price

- [ ] Set `STRIPE_PRO_PRICE_ID` back to the real $49/month price ID.
- [ ] Wait for deploy.
- [ ] Archive the $1 test price in Stripe Dashboard → **Products**.

### 8. Final Verification

- [ ] Open SkillForge in incognito → sign in → trigger paywall.
- [ ] Verify the checkout page shows `$49.00/month`.
- [ ] Do NOT complete checkout (unless you want to subscribe yourself).
- [ ] Check Railway logs for any errors.
- [ ] Check Sentry for any new issues.

---

## Rollback Plan

If something goes wrong after going live:

1. **Revert env vars** in Railway to the `sk_test_` / `whsec_test_` values.
2. Railway will auto-deploy with test-mode keys.
3. Refund any accidental live charges in Stripe Dashboard.
4. Investigate and fix the issue before retrying.

---

## Post Go-Live

- [ ] Delete or archive all test-mode webhook endpoints in Stripe.
- [ ] Update the team that live payments are enabled.
- [ ] Monitor Sentry and Stripe Dashboard for the first 24 hours.
- [ ] Set up Stripe email receipts (Settings → Emails → Customer emails).
