# Spec #36 — Subscription Cancellation (Stripe Billing Portal)

**Status:** Active — shipping with P5-S26b
**Owner:** Dhamo
**Created:** 2026-04-19
**Phase:** 5F (P5-S26b)
**Depends on:** Spec #11 (Stripe checkout + webhook), Spec #43 (webhook idempotency)

## 1. Problem Statement

Pro users have no self-serve path to cancel their subscription. Today the only escape hatches are contacting support or issuing a chargeback. That is a trust barrier for new-customer conversion ("can I actually stop paying?") and a support burden once users start asking to downgrade. For a single-seat $49/mo SaaS, not having a cancel button is the kind of thing that turns a closed trial into a churned user before they even sign up.

## 2. Solution

Embed Stripe's **hosted billing portal**. "Manage subscription" button on the Profile page → backend creates a portal session for the authenticated user's Stripe customer → 302 redirect to Stripe's hosted UI → user self-serves (cancel / update payment method / view invoices / switch plan in future) on Stripe's domain → Stripe fires `customer.subscription.deleted` at period end → the existing webhook handler flips `Subscription.plan` to `free`.

The portal UX is owned end-to-end by Stripe. We provide one new backend endpoint (`POST /api/v1/payments/portal`) and one new Profile section with a button. The `/payments/webhook` handler already processes `customer.subscription.deleted` correctly — this slice only adds the entry point.

### Why hosted portal, not custom

Stripe's portal handles: cancellation confirmation, cancel-at-period-end semantics, invoice history, payment-method updates, upcoming-invoice display, prorated-refund policy enforcement, and every cancellation-flow A/B test Stripe's growth team has ever run on it. Building any of that in-house would be redundant and would require keeping it in sync with Stripe's subscription model. The portal is free (bundled with Stripe), zero-maintenance, and mobile-responsive out of the box. Revisit only if the hosted portal becomes a product blocker (e.g. we need a bespoke win-back flow in the cancellation path).

## 3. Data Model

**No schema changes.** Everything needed already exists:
- `Subscription.stripe_customer_id` (`app/models/subscription.py:22`) — used as portal customer.
- `Subscription.plan` — flipped to `free` by the existing `_handle_subscription_deleted` webhook handler.
- `Subscription.status`, `Subscription.stripe_subscription_id`, `Subscription.current_period_end` — cleared by the same handler.

## 4. Cancellation Timing

Cancellation happens **at period end**, which is Stripe's portal default. A user who cancels on day 10 of a 30-day billing cycle keeps Pro access for the remaining 20 days. On day 30, Stripe fires `customer.subscription.deleted` → `_handle_subscription_deleted` flips `plan` to `free` → `home_state_service.invalidate(user_id)` fires so the user's home dashboard reflects the new plan on next visit. Immediate-cancellation (with prorated refund) is explicitly **not** wired — Stripe's default is the right trade-off (users get what they paid for; we avoid refund accounting complexity).

## 5. API Contract

### `POST /api/v1/payments/portal`

**Auth:** required. Standard `Depends(get_current_user)` pattern, same as `/payments/checkout`.

**Authorisation:** Pro-only. Free users → 403.

**Request body:** none.

**Response:**

```json
{ "url": "https://billing.stripe.com/p/session/bps_..." }
```

The URL is a short-lived Stripe-hosted portal session URL. Frontend does `window.location.href = response.url`.

**Error cases:**
- `401` — no valid bearer token.
- `403` — authenticated user's `Subscription.plan` is not `pro`, or no `stripe_customer_id` on the subscription row (portal requires an existing Stripe customer; free-never-upgraded users don't have one).
- `502` — Stripe API call failed (mirrors the existing checkout route's error handling).

**Return URL:** portal sends the user back to `f"{settings.frontend_url}/profile"` on completion, reusing the existing `FRONTEND_URL` env var set for checkout redirects.

## 6. Frontend

### Profile page — new "Subscription" section

Placement: directly above the existing "Settings" (EmailPreferences) section. Styled with the same `rounded-2xl border border-contrast/[0.08] bg-bg-surface/60 p-5` card shell used elsewhere on the page so it is visually consistent.

**Pro users see:**
- Header: "Subscription"
- Line 1: "Pro plan" badge with the same accent styling as the streak/XP cards.
- Line 2 (small text, muted): "Active" — we don't currently surface `current_period_end` to the frontend; an "Active" label is honest and avoids a new endpoint.
- Primary button: "Manage subscription". On click, `POST /api/v1/payments/portal` → `window.location.href = response.url`.

**Free users see:**
- Header: "Subscription"
- Line 1: "Free plan".
- Line 2 (small text, muted): "Unlock Pro for full library access and unlimited scans." (copy tuned to the existing paywall triggers — not new marketing).
- Primary button: "Upgrade to Pro" → `navigate('/pricing')`. Reuses the existing Pricing page as the single upgrade entry point; we do not duplicate the Stripe-checkout-from-profile flow here.

### Plan source of truth

`useUsage().usage.plan` (localStorage-backed; mirrors the existing UX pattern used by Navbar, Analyze, Results, Rewrite, StudyDashboard). This is slightly stale when the webhook flips a user to free at period end (localStorage needs a refresh to pick it up), but that is a pre-existing property of the UsageContext design, not a regression introduced by this slice. Deferring a `plan`-on-`/auth/me` fix to a separate slice.

### Button states

- **Idle:** "Manage subscription"
- **Loading:** disabled + inline `Loader2` spinner (same pattern as the existing "Generate My Experience" button in Profile).
- **Error:** inline text below the button ("Couldn't open billing portal. Please try again.") — no toast, mirroring the Experience section's inline error treatment. The button becomes clickable again on error for a retry.

### Redirect pattern

```ts
capture('subscription_portal_opened')
const res = await api.post<{ url: string }>('/api/v1/payments/portal')
window.location.href = res.data.url
```

Analytics fires **before** the redirect — if the POST fails, the event still captures user intent (valuable for funnel analysis).

## 7. Webhook (no changes)

`_handle_subscription_deleted` in `app/services/payment_service.py:244-266` already:

1. Looks up the `Subscription` row by `stripe_customer_id`.
2. Sets `plan='free'`, `status='canceled'`.
3. Clears `stripe_subscription_id` and `current_period_end`.
4. Fires the `subscription_cancelled` analytics event.
5. Calls `home_state_service.invalidate(sub.user_id)` so the home dashboard re-evaluates the user's plan on next fetch.

Existing coverage: `test_webhook_cancels_pro` (`tests/test_payments.py:273-315`) asserts the plan + status + subscription-id flips. Idempotency coverage lives in `test_duplicate_webhook_is_idempotent` (spec #43). No new webhook code or tests in this slice.

## 8. Analytics

| Event | Fired by | Properties |
|-------|----------|------------|
| `subscription_portal_opened` (**new**) | `src/pages/Profile.tsx` — "Manage subscription" click | — |
| `subscription_cancelled` (existing, §7) | `app/services/payment_service.py` — webhook | `{user_id, plan}` |

`subscription_portal_opened` will be added to the frontend events table in `.agent/skills/analytics.md` in this same slice.

## 9. Acceptance Criteria

- **AC-1** — A Pro user visiting `/profile` sees a "Subscription" section with "Pro plan" status and a "Manage subscription" button.
- **AC-2** — Clicking "Manage subscription" POSTs to `/api/v1/payments/portal`, receives a URL, and assigns `window.location.href` to it.
- **AC-3** — A free user visiting `/profile` sees a "Subscription" section with "Free plan" status and an "Upgrade to Pro" button that navigates to `/pricing`. The Manage button is not rendered.
- **AC-4** — `POST /api/v1/payments/portal` returns **403** for a user whose `Subscription.plan != 'pro'` or who has no `stripe_customer_id`.
- **AC-5** — `POST /api/v1/payments/portal` returns **401** for an unauthenticated request.
- **AC-6** — End-to-end (Stripe test mode): cancel in the portal → Stripe fires `customer.subscription.deleted` at period end → `Subscription.plan` flips to `free` in our DB. Covered by the existing `test_webhook_cancels_pro` unit test; manual Stripe-CLI smoke test before production go-live.
- **AC-7** — A user who cancels keeps Pro access between the cancel click and the period end. Stripe enforces this timing; no code required on our side beyond "do not flip plan until the webhook fires".
- **AC-8** — The `customer.subscription.deleted` webhook still invokes `home_state_service.invalidate(user_id)` on plan flip (regression guard; already shipped in P5-S18c).

## 10. Test Plan

| Test | File | AC | Status |
|---|---|---|---|
| `test_create_portal_session_for_pro_user` | `tests/test_payments.py` | AC-1, AC-2 | **new** |
| `test_portal_session_403_for_free_user` | `tests/test_payments.py` | AC-4 | **new** |
| `test_portal_session_401_for_unauth` | `tests/test_payments.py` | AC-5 | **new** |
| `test_webhook_cancels_pro` | `tests/test_payments.py:273` | AC-6 | existing |
| `test_subscription_section_shows_manage_for_pro` | `tests/Profile.subscription.test.tsx` | AC-1 | **new** |
| `test_subscription_section_shows_upgrade_for_free` | `tests/Profile.subscription.test.tsx` | AC-3 | **new** |
| `test_manage_button_redirects_to_portal_url` | `tests/Profile.subscription.test.tsx` | AC-2 | **new** |

Backend: +3 tests (220 → 223 unit, 6 integration deselected).
Frontend: +3 tests (91 → 94).

## 11. Out of Scope

- **In-app cancellation confirmation modal.** Stripe's portal owns the cancel confirmation UX. Rebuilding it here would duplicate and diverge.
- **Win-back flow ("50% off for 3 months").** Flagged in SESSION-STATE §Open Decisions Awaiting Dhamo — deferred until we have cancellation volume to justify the A/B.
- **Prorated refunds on immediate cancel.** We cancel at period end (Stripe default). No refund accounting on our side.
- **`current_period_end` display on Profile.** Would require surfacing the field via `/auth/me` or a new `/payments/subscription` endpoint. Dropped in favour of a generic "Active" label — a small UX gap that is honest and not worth a scope expansion.
- **Plan-on-`/auth/me` refresh.** `useUsage().usage.plan` is localStorage-backed and can be stale after a webhook-driven downgrade. Pre-existing limitation; separate slice.
- **Custom pause/downgrade options.** Stripe portal offers these at config time if we enable them; our current portal config uses Stripe defaults. No config changes in this slice.
- **`STRIPE_BILLING_PORTAL_CONFIGURATION_ID` env var.** Stripe auto-creates a default portal config per account; no explicit config id is required. If we want custom branding / features, we'd add one in a follow-up ops slice.
- **Stale `API_REFERENCE.md` `/api/v1/billing/*` paths (line 67).** Pre-existing doc drift; all billing paths there are wrong (actual prefix is `/api/v1/payments/*`). Out of scope for this slice — flag for a Phase 6 doc sweep.
