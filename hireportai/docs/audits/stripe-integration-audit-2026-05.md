# Stripe integration audit

**Audit date:** 2026-05-02
**Anchor HEAD:** `5b51244`
**Mode:** scout (Mode 1, read-only — R14 exception (b))
**Closes:** B-112 (filed + closed same slice); flips **E-035 🟦 → ✅**

## Scope + intent

E-035 was filed 2026-04-20 after the P5-S26b-impl-BE smoke surfaced
three Stripe issues (two operator env-var mistakes + the real E-033
billing-portal bug). The audit reviewed the full Stripe surface for
bugs, missing handlers, silent-drift risks, and produced a severity-
ranked fix list ahead of the ~2-week production deploy window.

This is a read-only audit. No code touched, no tests run.

## Surface inventory

### Backend

| File | LOC | Role |
|------|-----|------|
| `app/api/routes/payments.py` | 260 | `/payments/{checkout,portal,webhook,paywall-dismiss,should-show-paywall,usage,pricing}` route handlers |
| `app/services/payment_service.py` | 356 | Stripe SDK wrapper — `create_checkout_session` / `create_billing_portal_session` / `handle_webhook` + private dispatchers |
| `app/services/paywall_service.py` | 207 | `record_dismissal` (LD-8 60s dedup) + `should_show_paywall` (Strategy A grace) |
| `app/models/subscription.py` | 39 | `Subscription` ORM — billing state truth source |
| `app/models/stripe_event.py` | 20 | Webhook idempotency log (`evt_*` PK) |
| `app/models/paywall_dismissal.py` | 40 | Append-only dismissal log |
| `app/models/payment.py` | 24 | Defined; **zero writers in codebase** |
| `app/core/config.py` (lines 36-40) | — | 5 `stripe_*` settings |
| `hirelens-backend/.env.example` (lines 13-15) | — | Stripe vars: secret_key + webhook_secret + pro_price_id |
| `scripts/smoke_billing_portal.py` | 382 | E-033 diagnostic script |
| `tests/test_payments.py` | 681 | Webhook + checkout + portal coverage; spec #43 AC-4 idempotency |
| `tests/test_payments_paywall_routes.py` | — | Paywall dismissal endpoint tests |
| `tests/test_payments_usage_route.py` | — | `/payments/usage` shape tests |
| `tests/test_wall.py` | — | Daily-card wall integration |

### Frontend

| File | Role |
|------|------|
| `src/services/api.ts` (lines 601-706) | `createCheckoutSession` / `createBillingPortalSession` / `dismissPaywall` / `shouldShowPaywall` / `fetchUsage` / `fetchPricing` |
| `src/components/PaywallModal.tsx` | Paywall CTA → checkout redirect |
| `src/pages/Pricing.tsx` | Public pricing page; "Upgrade to Pro" button |
| `src/context/UsageContext.tsx` | Hydrates from `/payments/usage`; exposes `canUsePro` |

### Routes mounted (`/api/v1/payments` prefix)

- `GET /pricing` — geo-routed price (USD vs INR by IP)
- `POST /checkout` — auth-gated; creates Stripe Checkout Session
- `POST /portal` — auth-gated; creates billing-portal Session
- `POST /webhook` — UN-AUTH; signature-verified inside service
- `POST /paywall-dismiss` — auth-gated
- `GET /should-show-paywall` — auth-gated
- `GET /usage` — auth-gated

### Env vars consumed

`stripe_secret_key`, `stripe_webhook_secret`, `stripe_pro_price_id`,
`stripe_pro_price_id_inr`, `stripe_enterprise_price_id`. **Only the
first three appear in `.env.example`** (see F-5).

## Findings

Severity legend: P0 launch-blocker / P1 should-fix-pre-launch /
P2 nice-to-have / P3 future.

### F-1 — No Pro short-circuit on `/payments/checkout` (P0 launch-blocker)

`payment_service.create_checkout_session` (L63-147) does not check
whether the user already holds an active Pro subscription before
calling `stripe.checkout.Session.create`. A Pro user navigating to
`/pricing` and re-clicking **"Upgrade to Pro"** (Pricing.tsx:172)
or hitting the public Pricing route directly creates a second
subscription on the same Customer for the same Price.

Stripe permits multiple active subscriptions per Customer by default;
the API does not 4xx on duplicate-price subscriptions. Result: user
billed twice, two `subscription.created` events fire, the second
`checkout.session.completed` overwrites `stripe_subscription_id` on
the single Subscription row, and refunds require manual Stripe
Dashboard intervention.

**Fix:** add Pro guard to `create_checkout_session` after the
Subscription lookup (around L100). Raise a new `AlreadyProError`
(maps to **409 Conflict** with detail `"User already has an active
Pro subscription — manage it via the billing portal."`). Mirror the
guard on Pricing.tsx — hide the Upgrade CTA when `canUsePro === true`.

**Test envelope:** +2 BE (route 409 + service raise) + 1 FE
(Pricing button hidden for Pro). ~15 lines BE + ~3 lines FE.

### F-2 — `customer.subscription.updated` event NOT handled (P1)

`handle_webhook` (L256-257) silently ignores every event except
`checkout.session.completed` and `customer.subscription.deleted`.

Consequence: status flips to `past_due` (failed dunning attempt) /
`unpaid` (dunning exhausted, before deletion) / trial-end transitions
all invisible. A Pro user with a failed payment retains Pro access
until Stripe gives up and fires `customer.subscription.deleted`
(~3 weeks default dunning + 1 retry cycle). During that window the
user is not paying but consumes Pro features.

**Fix:** add `_handle_subscription_updated` dispatcher mapping
`status` → DB `Subscription.status`; if `status in {'past_due',
'unpaid'}`, optionally suspend Pro features (decision-needed: hard
gate vs grace).

### F-3 — `invoice.payment_failed` NOT handled (P1)

Pairs with F-2. No FE alert, no email warning to the user, no
operator visibility (admin analytics doesn't aggregate failed
charges). Stripe's hosted dunning email is the only signal — and it
goes to the customer's Stripe-on-file email, which may differ from
the OAuth Google email.

**Fix:** add `_handle_invoice_payment_failed` dispatcher writing a
`Payment` row (with `status='failed'`, see F-6) and emitting a
`payment_failed` PostHog event for product visibility.

### F-4 — `current_period_end` never SET, only cleared (P1)

`Subscription.current_period_end` (model L28-30) is exposed via
`/auth/me` (auth.py:273). It is **never written by any webhook
handler** — only cleared on cancel (`payment_service.py:314`). FE
cannot render "Pro until <date>" because the value is always NULL.
A consumer that fell back to "Pro permanent" would silently
regress when this field eventually gets populated.

**Fix:** wire `_handle_checkout_completed` and the proposed
`_handle_subscription_updated` to populate from
`data['current_period_end']` (Stripe sends UNIX seconds → convert
to UTC datetime).

### F-5 — `.env.example` missing 2 STRIPE_* vars (P1)

`.env.example` (lines 13-15) lists `STRIPE_SECRET_KEY`,
`STRIPE_WEBHOOK_SECRET`, `STRIPE_PRO_PRICE_ID`. Missing:
`STRIPE_PRO_PRICE_ID_INR`, `STRIPE_ENTERPRISE_PRICE_ID`.

Same shape as the P5-S26b operator-side incident where the wrong
price ID blocked checkout. An operator copying `.env.example` to
`.env` for local setup gets silent NULL fallbacks: INR users get
billed in USD; Enterprise plan can never be checked out (raises
`PaymentError` at L88).

**Fix:** append the two missing vars with empty defaults +
inline comment pointing at the dashboard.

### F-6 — `Payment` model has zero writers (P2)

`app/models/payment.py` defines a `payments` table with
`stripe_payment_intent_id` UNIQUE. Codebase grep finds zero
writers — model is dead. Either:

- (a) **Delete** the model + migration (cleanup; admin analytics
  doesn't read it; revenue is approximated from Subscription rows
  per `admin_analytics_service.py:138-140`).
- (b) **Wire `invoice.paid`** to insert a `Payment` row per
  successful charge (closes F-3's analytics half; needs spec).

Recommendation: defer to (b) when the F-2/F-3/F-4 cluster lands.
Don't delete pre-launch in case the spec for (b) authors quickly.

### F-7 — `NotProSubscriberError` collapses 3 distinct conditions (P2)

`create_billing_portal_session` (L182) raises
`NotProSubscriberError` for: (a) `sub is None`, (b) `sub.plan != 'pro'`,
(c) `not sub.stripe_customer_id`. Route layer maps all three to **403
"Billing portal is only available to Pro subscribers"**. E-033's
diagnosis cost time partly because the error didn't differentiate —
the actual cause was Dashboard config, but the same shape masks
"missing customer_id" (a real code-side bug if it happened).

**Fix:** split into `NotProSubscriberError` (cases a/b — wrong plan)
and `MissingStripeCustomerError` (case c — code-side data drift,
warrants 500 + Sentry alert, not 403).

### F-8 — Timezone inconsistency: `StripeEvent.processed_at` naive (P2)

`payment_service.py:247` writes `datetime.now(tz=None)` (naive
local time) into `StripeEvent.processed_at` (`DateTime`, no tz).
`PaywallDismissal.dismissed_at` is `DateTime(timezone=True) +
server_default=func.now()`. Mixed conventions across models. No
functional bug today (no consumer reads `processed_at` for time
math) but creates surprise for any future analytics query.

**Fix:** flip to `datetime.now(tz=timezone.utc)` and migrate the
column to `DateTime(timezone=True)` in the F-2/F-3/F-4 cluster
migration.

### F-9 — `/payments/webhook` has no per-route rate-limit override (P2)

SlowAPI default 100 req/min applies. Stripe peak retries during
a backlog flush can briefly exceed this. Stripe verifies signature
inside the handler before any DB work, so unauthenticated abuse is
cheap to reject.

**Fix:** either bump the limit to 200/min on this specific path or
exempt the route entirely (signature verification is the real
guard). Low priority — current limit hasn't been hit.

### F-10 — Checkout Session id not persisted (P3)

`_handle_checkout_completed` doesn't store `data['id']` (the
`cs_test_*` / `cs_live_*` session id). If a user reports
"I clicked Pay but I'm still Free", we have no DB-side trace —
must dig in Stripe Dashboard. Dormant; defer until support load
warrants it.

### F-11 — `home_state_service.invalidate` is in-process (P3)

Webhook handler calls `home_state_service.invalidate(sub.user_id)`
(L296, L330) — currently a no-op or in-memory touch (current
codebase has no Redis-backed cache for home_state). When that
lands, this call will become network I/O inside the webhook txn.
Flag for revisit when home_state caching becomes distributed.

## Missing handlers

Stripe events branched on by `handle_webhook`:

| Event | Handled? | Risk if not |
|-------|----------|-------------|
| `checkout.session.completed` | ✅ | — |
| `customer.subscription.deleted` | ✅ | — |
| `customer.subscription.created` | ❌ | Subscription created outside Checkout (admin Dashboard, API) untracked. Low risk — code-path requires Dashboard ops. |
| `customer.subscription.updated` | ❌ | F-2 — status / period_end / plan change drift |
| `invoice.paid` | ❌ | F-6 — revenue not denormalized |
| `invoice.payment_failed` | ❌ | F-3 — dunning failures invisible |
| `customer.subscription.trial_will_end` | ❌ | We don't offer trials today; safe ignore. Re-evaluate if trials launch. |
| `payment_intent.succeeded` / `*.failed` | ❌ | One-time charges not part of v1; safe ignore. |

## Idempotency assessment

✅ **Webhook signature verification mandatory** — `InvalidSignatureError` →
400 (payments.py:256-260). Cannot reach handler dispatch without a
valid signature.

✅ **Event-id idempotency** — `payment_service.py:234-250`. First-seen
events are processed; duplicates short-circuit and return 200 without
side effects.

✅ **Dispatch-failure rollback** — `tests/test_payments.py::test_handler_
exception_rolls_back_stripe_event_row` (L478-577) verifies via
SAVEPOINT pattern that a raise inside a dispatcher rolls back the
StripeEvent row, allowing Stripe's retry to land cleanly. Spec #43
AC-4 covered.

✅ **Handler self-idempotency** — `_handle_checkout_completed` and
`_handle_subscription_deleted` set target plan/status to fixed
values, so same-event-twice (post-dedup-bypass) lands the same final
state.

⚠️ **`user.downgraded_at` overwrite on retry** — `_handle_subscription_
deleted` (L323) writes `datetime.now(tz=timezone.utc)` on every
invocation. Pre-handler dedup short-circuits retries before this
runs, so practical risk = zero. Belt-and-suspenders fix: skip the
write when `user.downgraded_at is not None`. Not blocking.

## E-033 + E-039 status

**E-033 — code-side ✅ ready.** Original 2026-04-20 hypothesis
(`stripe_customer_id` not persisted) was refuted by investigation
`eb4259e`. Code persists `stripe_customer_id` in both
`create_checkout_session` (L114-122) for new customers and
`_handle_checkout_completed` (L283) on webhook. `create_billing_
portal_session` reads it cleanly at L182 and raises
`NotProSubscriberError` when missing. Test-mode resolution 2026-04-21
confirmed the real cause was Stripe Dashboard default Customer
Portal config not saved; Dhamo saved it; smoke-script Check 1 PASS.

**E-033 — pending:** repeat the Dashboard save in **live mode** at
`dashboard.stripe.com/settings/billing/portal` (Dhamo ops action,
not CC).

**E-039 — code-side ✅ ready.** Blocked on (a) E-033 live-mode
config save, (b) someone running the upgrade flow to populate
`stripe_customer_id` on a real subscription row, then re-running
`scripts/smoke_billing_portal.py --customer cus_xxx` for Check 2.

**Recommended sequence:** ship F-1 fix BEFORE running E-039.
E-039 will populate `stripe_customer_id` for the test user;
re-clicking Upgrade after E-039 succeeds is exactly the F-1
double-charge surface, and the test user is the most likely target
for that re-click.

## Recommended fix order

1. **F-1** (P0) — Pro short-circuit on `/payments/checkout` + FE
   Pricing button gate. Standalone slice, ~15 BE lines + ~3 FE
   lines, +3 tests. **Must land before E-039.**
2. **F-5** (P1) — `.env.example` add 2 missing STRIPE_* vars.
   Trivial, ~2 lines. Bundle into F-1 commit if scope allows.
3. **F-2 + F-3 + F-4 cluster** (P1) — `customer.subscription.updated`
   handler + `invoice.payment_failed` handler + populate
   `current_period_end`. Spec-worthy slice (~5-10 OQs). Defer if
   launch deadline tightens — failed-payment grace is ~3 weeks of
   leakage in worst case, not catastrophic.
4. **F-7** (P2) — `NotProSubscriberError` split for diagnostic
   clarity. Bundle into F-2/F-3/F-4 cluster.
5. **F-6** (P2) — defer Payment-model decision until F-3 spec
   authors; (b) wire-`invoice.paid` is the more likely pick.
6. **F-8 + F-9** (P2) — bundle into F-2/F-3/F-4 cluster as a polish
   pass.
7. **F-10 + F-11** (P3) — defer indefinitely.

## Closure

- Closes **B-112** (single-slice scout, doc-only).
- Flips **E-035 🟦 → ✅** in same commit per prompt.
- No code touched. No tests run (R14 exception (b) — pure audit).
- BE 824 / FE 466 carry-forward unchanged.
