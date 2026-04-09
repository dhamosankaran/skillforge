# SPEC: Stripe Integration — Checkout, Webhooks, Paywall

**Spec #:** 11
**Phase:** 1
**Status:** Draft
**Branch:** `feature/p1-11-stripe-integration`

---

## Problem

SkillForge has a two-tier product (Free: 15 Foundation cards + ATS scans;
Pro: full library at $49/mo) but no path from "user hits the wall" to
"money in the bank." Stripe keys and placeholder price IDs exist in
`core/config.py` and `stripe_service.py` is stubbed, but there is no
Checkout Session endpoint, no webhook handler, no `user.plan` state
transition, and no frontend paywall that converts. The free-tier gate in
`UsageContext` currently opens an `UpgradeModal` that has no CTA wired to
Stripe.

Without this, the `ats_scanned → card_viewed → paywall_hit → payment_completed`
funnel defined in `.agent/skills/analytics.md` dead-ends at step 3.

## Solution

Ship a minimal, production-shaped Stripe integration that covers the two
events that actually move revenue — a successful checkout and a cancellation
— plus the UI surface that drives users into checkout.

### High-level flow
1. Free user hits a Pro-gated surface (16th card, locked category tile,
   scan limit) → `PaywallModal` opens.
2. User clicks **Upgrade to Pro** → frontend `POST /api/v1/payments/checkout`
   with the price ID.
3. Backend creates a Stripe Checkout Session (mode: `subscription`) with
   `success_url` and `cancel_url` pointing back to the app, and a
   `client_reference_id` set to the authenticated user's ID.
4. Frontend redirects the browser to `session.url`.
5. User pays on Stripe-hosted page.
6. Stripe fires `checkout.session.completed` →
   `POST /api/v1/payments/webhook` → backend flips `user.plan = "pro"`,
   stores `stripe_customer_id` and `stripe_subscription_id`.
7. User is returned to `/pricing?upgrade=success`; the app refetches
   `/auth/me`, `UsageContext` sees `plan === "pro"`, gates lift.
8. Later, if the subscription is cancelled, Stripe fires
   `customer.subscription.deleted` → backend flips `plan` back to `"free"`.

---

## API Contract

### `POST /api/v1/payments/checkout`
**Auth:** required (`Depends(get_current_user)`).

**Request**
```json
{ "price_id": "price_XXX" }
```
`price_id` must be in an allowlist (pro monthly, pro annual) read from
settings — do NOT trust arbitrary price IDs from the client.

**Response** `200`
```json
{ "session_id": "cs_test_...", "url": "https://checkout.stripe.com/..." }
```

**Errors**
- `400` — price_id not in allowlist.
- `401` — unauthenticated.
- `409` — user already on Pro (prevent double-subscribe).
- `502` — Stripe API failure (log + bubble a safe message).

### `POST /api/v1/payments/webhook`
**Auth:** none (Stripe calls this). Signature verified via
`stripe.Webhook.construct_event(payload, sig_header, webhook_secret)`.
Raw request body is required — must use `request.body()`, not a parsed
Pydantic model.

Handled events:
| Event                              | Action                                                      |
|------------------------------------|-------------------------------------------------------------|
| `checkout.session.completed`       | Look up user by `client_reference_id`; set `plan = "pro"`, store `stripe_customer_id` + `stripe_subscription_id`; fire `payment_completed` analytics event |
| `customer.subscription.deleted`    | Look up user by `stripe_customer_id`; set `plan = "free"`; fire `subscription_cancelled` analytics event |

Every other event is acknowledged with `200` and ignored (Stripe retries on
non-2xx, so silent-ignore is correct).

**Idempotency:** Stripe may deliver the same event multiple times. Store
the last processed `event.id` per user, or use a small `stripe_events`
table keyed on `event.id` with a unique constraint, so replayed deliveries
become no-ops. Either approach is acceptable; pick the simpler one for
Phase 1.

**Response** always `{ "received": true }` with status `200` when the
signature verifies; `400` with no body when it does not.

### `GET /api/v1/payments/config` *(optional but recommended)*
Returns the public Stripe publishable key + the allowlisted price IDs so
the frontend does not need to hardcode them in `import.meta.env`.

---

## Data Model Changes

`users` table — add (all nullable, migration via Alembic):
- `stripe_customer_id TEXT UNIQUE NULL`
- `stripe_subscription_id TEXT NULL`
- `plan_updated_at TIMESTAMPTZ NULL`

The existing `plan` column (already `"free" | "pro"`) is reused — no new
column. Index `stripe_customer_id` for webhook lookups.

Optional `stripe_events` table for idempotency:
- `event_id TEXT PRIMARY KEY`
- `event_type TEXT NOT NULL`
- `processed_at TIMESTAMPTZ DEFAULT now()`

---

## UI/UX

### `PaywallModal` component (new)
`src/components/PaywallModal.tsx`. Replaces the current generic
`UpgradeModal` for Pro-gated surfaces (keep `UpgradeModal` only if it
serves a distinct purpose; otherwise delete and rename).

Props:
```ts
interface PaywallModalProps {
  open: boolean
  onClose: () => void
  trigger: 'scan_limit' | 'card_limit' | 'locked_category' | 'daily_review'
  context?: { cardsViewed?: number; categoryName?: string }
}
```

Content:
- Headline tied to trigger ("You've hit your free scan limit",
  "Unlock the full card library", etc.)
- Three-bullet value prop (unlimited scans, full library, daily review)
- Price display: **$49/mo**, pulled from `GET /payments/config`
- Primary CTA: **Upgrade to Pro** → calls `createCheckoutSession(priceId)`
  → `window.location.href = session.url`
- Secondary: **Not now** → `onClose()`
- Loading state on the CTA while the checkout call is in flight; error
  toast on failure.

### Wiring
- `UsageContext.checkAndPromptUpgrade()` already fires `paywall_hit` — keep
  that, but swap the modal it opens from `UpgradeModal` to `PaywallModal`
  and pass the correct `trigger`.
- Card viewer: when a free user opens a non-Foundation card, show
  `PaywallModal` with `trigger="card_limit"`.
- Category tiles: when a free user clicks a locked tile, show with
  `trigger="locked_category"` and the category name.
- Post-checkout success: on `/pricing?upgrade=success`, fire a single
  refetch of `/auth/me`, update the auth context, show a success toast.

### Analytics
Per `.agent/skills/payments.md` + `.agent/skills/analytics.md`:
- `paywall_hit` — already wired, verify `trigger` property is set
- `checkout_started` — fire on `PaywallModal` CTA click, before redirect,
  props `{ price_id, trigger }`
- `payment_completed` — fire **server-side** from the webhook handler,
  props `{ amount, plan, user_id }` (client cannot be trusted here)
- `subscription_cancelled` — fire server-side from the webhook handler

---

## Acceptance Criteria
- [ ] AC-1: Free user with `scansUsed >= maxScans` clicks Scan →
      `PaywallModal` opens with `trigger="scan_limit"` and
      `paywall_hit` event fires.
- [ ] AC-2: Free user clicks **Upgrade to Pro** → `checkout_started`
      fires, browser redirects to a live Stripe Checkout URL.
- [ ] AC-3: Using a Stripe test card (`4242 4242 4242 4242`), payment
      succeeds → webhook updates `users.plan = "pro"` within 5 seconds
      → user lands on `/pricing?upgrade=success` → frontend reflects
      Pro state without a hard refresh.
- [ ] AC-4: Manually triggering `customer.subscription.deleted` via
      Stripe CLI (`stripe trigger customer.subscription.deleted`) →
      `users.plan` flips back to `"free"`.
- [ ] AC-5: Replaying the same `checkout.session.completed` event twice
      via Stripe CLI does NOT create duplicate state transitions or
      duplicate `payment_completed` analytics events (idempotency).
- [ ] AC-6: Webhook with an invalid signature returns `400` and does
      not mutate any user state.
- [ ] AC-7: `POST /payments/checkout` with a `price_id` not in the
      allowlist returns `400`.
- [ ] AC-8: A user already on Pro calling `/payments/checkout` receives
      `409` and is not billed twice.

---

## Edge Cases
- **Webhook arrives before success redirect.** Expected — handle it; the
  frontend's post-redirect refetch of `/auth/me` is the tie-breaker.
- **Webhook arrives but user row is gone** (deleted account mid-flow):
  log and `200` so Stripe stops retrying; do not crash.
- **User pays, Stripe webhook is delayed > 5 seconds.** Frontend should
  poll `/auth/me` for up to ~10s on the success page before giving up
  and showing "Processing, refresh in a moment."
- **Duplicate webhook delivery.** Idempotency key (see above).
- **Price ID rotated in Stripe dashboard.** Allowlist is env-driven —
  rotate via Railway env vars, no code change.
- **Test mode vs live mode.** Backend reads `STRIPE_SECRET_KEY` from env,
  so local dev uses `sk_test_...` and production Railway uses `sk_live_...`
  — no branching in code.
- **Stripe CLI for local webhook testing.** `stripe listen --forward-to
  localhost:8000/api/v1/payments/webhook` — document in the PR.

---

## Test Plan

Per the 3-strike rule and CLAUDE.md "test first", tests come before
implementation. **All Stripe network calls are mocked.** Do NOT hit the
real Stripe API from pytest, even in test mode.

### Backend tests — `tests/test_payments.py`

Use `unittest.mock.patch` on `stripe.checkout.Session.create`,
`stripe.Webhook.construct_event`, and `stripe.Subscription.retrieve`.

**Checkout endpoint**
1. `test_checkout_creates_session` — patched `Session.create` returns a
   fake session; endpoint returns `{session_id, url}`; the mock was
   called with the authenticated user's ID as `client_reference_id`.
2. `test_checkout_rejects_unknown_price_id` — 400.
3. `test_checkout_requires_auth` — 401.
4. `test_checkout_blocks_existing_pro_user` — 409, `Session.create` not
   called.
5. `test_checkout_handles_stripe_api_error` — patched mock raises
   `stripe.error.APIError` → 502; no DB mutation.

**Webhook handler**
6. `test_webhook_rejects_invalid_signature` — `construct_event` raises
   `SignatureVerificationError` → 400; no DB mutation.
7. `test_webhook_checkout_completed_upgrades_user` — construct_event
   returns a canned `checkout.session.completed` payload with
   `client_reference_id` = test user ID; assert `plan` flips to `"pro"`
   and `stripe_customer_id` / `stripe_subscription_id` are stored.
8. `test_webhook_subscription_deleted_downgrades_user` — assert `plan`
   flips to `"free"`.
9. `test_webhook_idempotent_replay` — deliver the same
   `checkout.session.completed` twice; assert `plan` still `"pro"`,
   `plan_updated_at` unchanged on the second call, and `payment_completed`
   analytics fired exactly once (mock `app.core.analytics.track`).
10. `test_webhook_ignores_unrelated_event` — deliver a `ping`/`invoice.created`
    event; responds 200, no DB writes.
11. `test_webhook_missing_user_is_logged_not_raised` — canned event with a
    `client_reference_id` that does not exist → 200, warning logged.

Fixtures live in `tests/conftest.py`:
- `stripe_fake_session` factory — returns a dict/obj matching the real
  Session shape just closely enough for the handler.
- `stripe_fake_event` factory — builds well-typed event dicts for each
  handled event type.

### Frontend tests — `src/components/__tests__/PaywallModal.test.tsx`

Vitest + RTL. Mock `services/api.ts` `createCheckoutSession`.

12. `renders trigger-specific headline` for each trigger enum value.
13. `clicking Upgrade calls createCheckoutSession then redirects` — mock
    `window.location` assignment; assert the returned URL was used.
14. `shows error toast on checkout failure` — mock rejects; assert toast.
15. `clicking Not now calls onClose`.
16. `fires checkout_started analytics on CTA click` — mock `capture`.

### Manual verification (post-merge, staging)
- Test card `4242 4242 4242 4242` → Pro flip ≤ 5s.
- Stripe CLI: `stripe trigger customer.subscription.deleted` → Free flip.
- PostHog Live Events shows `paywall_hit`, `checkout_started`,
  `payment_completed`.

### Out of scope (deferred)
- Proration, plan switching, annual plan — Phase 2.
- `invoice.payment_failed` grace period + dunning email — Phase 2 (needs
  the email service from Spec #12+).
- Customer portal (Stripe-hosted cancel/update) — Phase 2.
- Refunds UI — never (handle out-of-band via Stripe dashboard).

---

## Dependencies
- Spec #10 (PostHog analytics) — for `paywall_hit`, `checkout_started`,
  `payment_completed` events.
- Existing `users` table + auth (Google OAuth + JWT) — for
  `get_current_user` and the `plan` column.
- `stripe` Python SDK (already in `requirements.txt`) and
  `@stripe/stripe-js` on the frontend (add if missing; Checkout
  redirects do not strictly need it, plain `window.location` works).
- Stripe dashboard: Pro product + monthly price created, webhook
  endpoint registered, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`,
  `STRIPE_PRO_PRICE_ID` set in Railway.
