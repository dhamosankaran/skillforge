---
slice: P5-S26b (spec) + P5-S26b-impl (implementation)
base_sha: b31cb17
drafted: 2026-04-20
locked_decisions: LD-1..LD-8 (in-spec, §3)
unblocks: P5-S26b-impl
depends_on: spec #50 (daily-card wall — shipped `ebef7da`), spec #22 (plan-aware Missing Skills CTA — shipped `b31cb17`)
---

# SPEC: Paywall Dismissal + Win-Back

**Status:** Draft
**Owner:** Dhamo
**Created:** 2026-04-20
**Phase:** 5 (v2.2-patch item 5.30)
**Closes:** spec-authoring portion of E-014 / row 5.30. The implementation half is P5-S26b-impl (a separate slice).

## 1. Problem

Free users who hit the daily-card review wall (spec #50, shipped `ebef7da`) today have exactly one escape hatch: close the `PaywallModal` with either the top-right **X** (`src/components/PaywallModal.tsx:141-148`) or the **"Not now"** secondary button (`:210-216`). Both call `onClose` and nothing else — no event, no signal, no grace. The very next rate-click re-opens the same modal with identical copy.

Two user segments suffer:

1. **The not-now-but-maybe-later** user — legitimately interested, not buying today. Every retry re-walls them. The product feels hostile; abandonment is a rational response.
2. **The buy-curious but price-sensitive** user — we have no tool to re-engage them when they dismiss repeatedly (high-intent signal, no nurture path).

We also have zero data on the dismissal funnel today: no `paywall_dismissed` event, no per-trigger dismissal history, no way to pull a "how many free users have walked away from the wall 3+ times" cohort.

The `PaywallTrigger` union (`PaywallModal.tsx:21-27`) already names six gating surfaces — `scan_limit`, `card_limit`, `locked_category`, `daily_review`, `interview_limit`, `skill_gap_study` — but only `daily_review` is wired to a live backend wall today (spec #50). The other five are future-tense: this spec scopes to the one wall that exists, and designs the primitives so the other five land here later for free.

## 2. Audit of existing state (Step-3 verification, 2026-04-20)

### 2.1 Frontend paywall chokepoint

- **`src/components/PaywallModal.tsx`** — already renders a "Not now" button at `:210-216` (secondary text link below the primary "Upgrade to Pro"). Today `onClick={onClose}`; zero network or analytics side-effect. The X close at `:141-148` is semantically identical. **No UI primitive needs to be added — the existing button just gains handlers.**
- **`src/components/study/QuizPanel.tsx:177-189`** — the single submit chokepoint (consumed by `DailyReview`, `CardViewer`, `MissionMode`). Catches 402 via `extractWallPayload`, stores payload in `wall` state, renders `<PaywallModal open trigger="daily_review" onClose={() => setWall(null)}>` at `:317-321`. On dismiss (`setWall(null)`), the payload is cleared; next walled submit re-opens the modal.
- **`daily_card_wall_hit`** fires once per modal open via `useEffect` on `wall !== null` (`:145-150`, props `{resets_at_hours_from_now: int}`). Matches the `paywall_hit` open-semantic in `PaywallModal.tsx:78-85`. The new `paywall_dismissed` event will follow the same flat-primitive convention.

### 2.2 Backend billing router — ⚠️ path prefix deviates from stub

- Router file: **`app/api/routes/payments.py`** (legacy folder — previously flagged by the 2026-04-19 CODE-REALITY audit; routers `onboarding.py` and `payments.py` live in `api/routes/` despite being v1-mounted). Mounted via `app.include_router(payments.router, prefix="/api/v1", tags=["v1 Payments"])` in `main.py:144`.
- Existing endpoints — **all at `/api/v1/payments/*`**:
  - `GET /payments/pricing` — geo-pricing by client IP
  - `POST /payments/checkout` — creates Stripe Checkout Session
  - `POST /payments/portal` — Stripe billing portal
  - `POST /payments/webhook` — Stripe webhook receiver (idempotent per spec #43)
- **No `/api/v1/billing/*` router exists anywhere on disk.** The v2.2 patch stub (`claude-code-prompts-all-phases-v2.2-patch.md:192-193`) wrote `/api/v1/billing/...`; that was planning-era shorthand. This spec uses **`/api/v1/payments/*`** to match the live convention and keep the billing surface on one router.

### 2.3 Email (Resend) infrastructure

- Send path: **`app/services/email_service.py::send_email(to, subject, html_body) -> str | None`** (async). Retries 3× on 429/5xx with exponential backoff. Silent no-op (log + return `None`) when `RESEND_API_KEY` is unset — keeps dev/CI from hitting the network.
- Templates live at `app/templates/*.html`. Only `daily_reminder.html` exists today. Rendering is string `.replace("{{var}}", value)` inside `reminder_service.build_email_body` — **not** Jinja2. The win-back template must follow the same shape.
- Unsubscribe: `EmailPreference.unsubscribe_token` (64-char hex, unique) exists but is **not injected** into any email body today. Daily reminder has passive footer copy only. This spec proposes injecting the unsubscribe link into the new win-back template (§5.5).
- **No deferred/scheduled-send infra.** `reminder_service.send_daily_reminders(db)` iterates users and calls `send_email` synchronously. No APScheduler, no job queue, no cron inside the app. Per **LD-4**, the win-back email fires synchronously from the `/paywall-dismiss` handler on the 3rd dismissal — no scheduler is introduced.

### 2.4 `daily_card_wall_hit` payload — reference point

Catalogued in `.agent/skills/analytics.md:79` — frontend-fired from `QuizPanel.tsx:147`, open-only (re-open re-fires). Payload: `{resets_at_hours_from_now: int}`. The new `paywall_dismissed` event (§6) follows the same flat-primitives convention.

### 2.5 Plan determination (live, not cached)

- `user.subscription` relationship, eager-loaded via selectin in `get_current_user` (per `app/core/deps.py`). **No cached `plan` column on `User`.**
- Helper `_is_free(user)` duplicated in `app/api/v1/routes/study.py:34-45` and `app/services/card_service.py:35-44` — same logic: `sub is None OR sub.status != 'active' OR sub.plan == 'free'`. Enterprise (`sub.plan == 'enterprise'`) is treated as Pro for gating.
- Consistent with drift flag D-010: frontend also composes plan live via `useAuth` + `useUsage`, not from a cached `AuthUser.subscription` field.
- **Implication for AC-3 (Pro never walled):** the backend `POST /paywall-dismiss` and `GET /should-show-paywall` handlers MUST call `_is_free(user)` at request time; they cannot lean on a cached plan snapshot.

### 2.6 Downgrade detection — ⚠️ no column today

- `customer.subscription.deleted` webhook handler: `app/services/payment_service.py::_handle_subscription_deleted` (`:299-322`). Sets `sub.plan = "free"`, `sub.status = "canceled"`, clears `stripe_subscription_id` + `current_period_end`, fires `subscription_cancelled` analytics, invalidates home-state cache.
- **Grep `downgraded_at|was_pro|churn` across `hirelens-backend/` returns zero matches.** There is no durable "last downgrade" marker anywhere.
- `Subscription.updated_at` has `onupdate=func.now()` but mutates on any change (plan up, plan down, customer_id update) — **not** a reliable churn timestamp.
- Per **LD-5**, this spec proposes adding **`user.downgraded_at: TIMESTAMPTZ NULL`**, set from `_handle_subscription_deleted`. Logged as an impl-slice dependency (§9).

## 3. Locked design decisions

All eight decisions below are locked in the authoring prompt. They are re-stated here so the spec is self-contained and reviewers do not have to chase the prompt.

- **LD-1 — Scope (daily_review only).** Schema accepts any `trigger: VARCHAR(64)`; backend endpoints accept any string; frontend wiring, ACs, and tests cover `trigger="daily_review"` only. Other `PaywallTrigger` values (`scan_limit`, `card_limit`, `locked_category`, `interview_limit`, `skill_gap_study`) reuse the same endpoints when they later wall — zero backend change needed.
- **LD-2 — Per-trigger grace.** Dismissing `daily_review` silences `daily_review` only. Other triggers keep independent grace counters. Rationale: dismissals signal intent about a specific feature, not about the whole product.
- **LD-3 — Thresholds (intuition-based, retune after 30 days).**
  - Grace: **3 further attempts** per trigger before the modal re-appears.
  - Win-back: **3 dismissals in rolling 30 days** → one win-back email per trigger-family.
  - Discount: **30% off first month**, Stripe coupon.
  - These numbers are intuition; they must be re-tuned from production telemetry. See §11.
- **LD-4 — Email infra reuse.** Win-back reuses the Phase-2 Resend path — new template under `app/templates/`, existing `email_service.send_email`. No scheduler, no queue; send fires synchronously from the `/paywall-dismiss` handler on the 3rd-in-30d threshold.
- **LD-5 — Downgrade handling + churn guard.** Dismissal rows survive every plan change (up, down, both); win-back eligibility gains a guard:
  `win_back_eligible = (dismissals_in_last_30d >= 3) AND (user.downgraded_at IS NULL OR user.downgraded_at < now() - INTERVAL '60 days')`.
  Rationale: a fresh churner will not convert on a 30%-off email — wait for the normal counter to re-accumulate post-churn. Introduces a new column `user.downgraded_at` (see §2.6).
- **LD-6 — Silent inline nudge.** Within the grace window, a retry of the gated action shows an **inline** message ("This is a Pro feature — upgrade anytime from Profile"), **not** a modal. The inline message **does not** fire `paywall_shown` / `paywall_hit`. Rationale: counting silent nudges would inflate the denominator and break conversion-rate math for the funnel.
- **LD-7 — Pro users are untouched.** Pro and Enterprise never see the paywall modal, never see the inline nudge, regardless of any dismissal history. Upgrading **does not** clear dismissal rows — history is retained for analytics and downgrade-then-retry edge cases.
- **LD-8 — Idempotency (60s per `(user_id, trigger)`).** `POST /paywall-dismiss` within 60 seconds of an existing row for the same `(user_id, trigger)` returns the existing row instead of inserting a duplicate. Prevents double-logging from rapid clicks and network retries.

## 4. Solution

Four moving parts:

### 4.1 Persistence — `paywall_dismissals` table

A single new table records every dismissal. No CRUD API for rows — they are append-only (or idempotent-merge within 60s per LD-8). Rows survive upgrade, downgrade, and persona changes; they are only removed by user deletion via the existing `users.id` CASCADE.

### 4.2 Backend API — two endpoints on the live `/api/v1/payments` router

- `POST /api/v1/payments/paywall-dismiss` — logs the dismissal, computes `win_back_eligible`, sends the win-back email synchronously when eligible.
- `GET /api/v1/payments/should-show-paywall?trigger=<str>` — the FE polls this after a 402 to decide **modal vs inline nudge**. Single indexed query on `(user_id, trigger, dismissed_at DESC)`; AC-8 budgets <50 ms.

### 4.3 Frontend — dismiss-aware wall chokepoint

The chokepoint is **`src/components/study/QuizPanel.tsx`**'s 402 handler. Today it unconditionally opens `PaywallModal`. This spec rewires it:

1. On 402 with `trigger="daily_review"` → call `GET /should-show-paywall?trigger=daily_review`.
2. If `show: true` → open modal (unchanged behavior + `paywall_shown` per existing convention).
3. If `show: false` → render inline nudge (new component, §5.4), do **not** open modal, do **not** fire `paywall_shown` (LD-6).

The `PaywallModal` "Not now" button gains two handlers: `capture('paywall_dismissed', ...)` + `POST /paywall-dismiss`, then `onClose`. The X close button gets the same treatment (same semantic: user declined).

### 4.4 Re-engagement — win-back email on 3rd dismissal in 30d

The `/paywall-dismiss` handler, after logging the new row, recomputes the 30-day window count. If ≥3 AND the churn guard passes (LD-5), it fires the win-back email synchronously via `email_service.send_email` using a new template `app/templates/paywall_winback.html`. The link in the email carries a signed query param (`?winback=1&campaign=<dismissal_id>`) that the `/pricing` / Stripe Checkout page parses to fire `winback_email_clicked` and, on conversion, `winback_converted`.

## 5. Data model + API + UI

### 5.1 New table — `paywall_dismissals`

```
CREATE TABLE paywall_dismissals (
    id                         UUID        PRIMARY KEY,
    user_id                    UUID        NOT NULL
                                            REFERENCES users(id) ON DELETE CASCADE,
    trigger                    VARCHAR(64) NOT NULL,
    dismissed_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    action_count_at_dismissal  INT         NULL
);

-- Primary query path: "give me dismissals for (user, trigger) in last 30d"
-- and "last dismissal for (user, trigger)" for LD-8 idempotency.
CREATE INDEX ix_paywall_dismissals_user_trigger_dismissed_at
    ON paywall_dismissals (user_id, trigger, dismissed_at DESC);
```

Column notes:
- `trigger: VARCHAR(64)` — matches the frontend `PaywallTrigger` union length budget and leaves room for composite names like `card_wall_15` from the stub. Not an enum at the DB level per LD-1 (future triggers add zero schema churn).
- `action_count_at_dismissal: INT NULL` — number of walled attempts the user made **before** this dismissal (so the first dismissal after a wall has `1`, a dismissal after 3 walled retries within grace has `4`, etc.). Nullable because the frontend may not always have a clean counter; the BE accepts `null` and records `null`. Telemetry only — not consumed by business logic.
- **No unique constraint** on `(user_id, trigger, dismissed_at)` — LD-8 idempotency is enforced in application code via a 60s window check, not via DB uniqueness (a unique index would need millisecond precision and would race under concurrent writes).

### 5.2 New column — `users.downgraded_at`

```
ALTER TABLE users
    ADD COLUMN downgraded_at TIMESTAMPTZ NULL;
```

Set from `app/services/payment_service.py::_handle_subscription_deleted` in the impl slice (right next to `sub.plan = "free"`). Nullable — pre-existing free users (never Pro) keep `NULL` forever.

Alternative considered: put it on `Subscription` instead. Rejected because (a) LD-5 names `user.downgraded_at` explicitly, (b) a user with a cancelled-then-re-upgraded-then-cancelled-again history would otherwise need versioning or overwrite semantics on Subscription; keeping the "last downgrade" pointer on User is simpler and matches the churn-guard read shape.

### 5.3 API contract

#### POST `/api/v1/payments/paywall-dismiss`

Auth: `Depends(get_current_user)` (matches every other payments endpoint except `/webhook`).

Request:
```
{
  "trigger": "daily_review",
  "action_count_at_dismissal": 1   // optional, default null
}
```

Response (`200 OK`):
```
{
  "logged":                true,    // false on LD-8 de-dup hit within 60s
  "dismissal_id":          "<uuid>",// existing row id when logged=false
  "dismissals_in_window":  2,       // rolling-30d count for this (user, trigger) INCLUDING this row
  "win_back_eligible":     false    // evaluated AFTER logging + churn guard
}
```

Errors:
- `401 Unauthorized` — missing/invalid JWT (auth dependency).
- `422 Unprocessable Entity` — `trigger` missing, empty, or >64 chars; `action_count_at_dismissal` negative.
- `429 Too Many Requests` — **reserved for a future rate-limit; not implemented in this spec.** Documented here so the contract is future-stable.

Side effects (in order):
1. Compute 60s-window lookup on `(user_id, trigger)`; if a row exists, return `{logged: false, dismissal_id: <existing_id>, dismissals_in_window: <count>, win_back_eligible: <recomputed>}` and skip insert.
2. Insert new `paywall_dismissals` row.
3. Compute `dismissals_in_window` (rolling 30-day count for same user+trigger, including the just-inserted row).
4. Compute `win_back_eligible` = `dismissals_in_window >= 3 AND (user.downgraded_at IS NULL OR user.downgraded_at < now() - INTERVAL '60 days')`.
5. If `win_back_eligible AND not already_sent_winback_for_this_window` → call `send_email` synchronously with the new template. A sent-once guard (§5.5) prevents re-sending on every dismissal ≥3.

#### GET `/api/v1/payments/should-show-paywall?trigger=<str>`

Auth: same.

Response:
```
{
  "show":                bool,   // false iff the user has dismissed this trigger within the grace window AND grace is not exhausted
  "attempts_until_next": int,    // 3 if no recent dismissal; decrements per attempt the FE reports; 0 means "next attempt re-opens modal"
  "win_back_offered":    bool    // true if we've sent a win-back email for this trigger in the last 30d
}
```

Logic:
- **Pro / Enterprise / admin** → always `{show: false, attempts_until_next: 0, win_back_offered: false}` — AC-3. The FE is responsible for never even calling this endpoint for Pros (`_is_free` short-circuit), but the BE defends the contract.
- Free users:
  - If no `paywall_dismissals` row for `(user, trigger)` → `{show: true, attempts_until_next: 3, win_back_offered: false}`.
  - If the most recent dismissal has been followed by ≥3 walled-retries (the FE has been hitting the endpoint on each inline-nudge display — see §5.4) → `{show: true, attempts_until_next: 3, win_back_offered: ...}`.
  - Otherwise → `{show: false, attempts_until_next: N, win_back_offered: ...}` where `N = 3 - (walled_retries_since_last_dismiss)`.

**Implementation note for impl slice:** "walled retries since last dismissal" needs a counter somewhere. Two acceptable strategies — impl picks:
- **Strategy A (recommended):** FE tracks the grace counter in React state (`attemptsSinceDismiss`), passes it on each `GET /should-show-paywall` call as a query param. Backend is pure read-compute. Simplest; no Redis.
- **Strategy B:** Redis key `paywall_grace:{user_id}:{trigger}` incremented on each walled submit post-dismiss, cleared when the counter reaches 3 or the dismissal ages out. Matches the spec #50 wall-counter idiom.

Strategy A keeps the backend stateless and is compatible with the <50ms AC-8 budget (single dismissals-table query).

AC-8 budget verification — the query is literally:
```sql
SELECT dismissed_at
  FROM paywall_dismissals
 WHERE user_id = $1 AND trigger = $2
 ORDER BY dismissed_at DESC
 LIMIT 1;
```
hitting `ix_paywall_dismissals_user_trigger_dismissed_at`. Expected plan: Index Scan Using, rows=1, <5ms locally; <50ms over a loaded prod connection is comfortable.

### 5.4 UI/UX

- **`PaywallModal` changes** (minimal):
  - "Not now" button (`PaywallModal.tsx:210-216`) gets a new `onClick` — fires `paywall_dismissed`, `POST /paywall-dismiss`, then the existing `onClose`. Text stays `"Not now"`.
  - X close button (`:141-148`) gets the same handler pair — same semantic (user declined, not "I changed my mind").
  - No copy change, no new variant, no new prop surface. Mobile layout unchanged (full-width buttons stacked).

- **New inline nudge** — new component `src/components/study/WallInlineNudge.tsx`:
  - Renders above the rating-button grid in `QuizPanel` when `should-show-paywall` returned `{show: false}`.
  - Copy: `"This is a Pro feature — upgrade anytime from Profile"` (LD-6 exact wording).
  - Design: single-line text nudge using `text-text-muted` + subtle `border-border-accent/30` background card — matches the `card-feedback-submitted` "Thanks for your feedback!" nudge shape in `QuizPanel.tsx:373-376`. Design-system tokens only (R12).
  - Does **not** fire `paywall_shown` or `paywall_hit` (LD-6). It **may** fire a new `inline_nudge_shown` event if the impl audit finds telemetry value; otherwise silent.
  - Mobile: identical layout (native flex).

- **QuizPanel 402 handler flow change** (`QuizPanel.tsx:177-189`):
  1. On 402 with `trigger="daily_review"` → call `GET /should-show-paywall?trigger=daily_review`.
  2. `show: true` → open modal (today's behavior), fire `paywall_shown` via the existing modal-open effect.
  3. `show: false` → set `inlineNudge: true` state, render `<WallInlineNudge />` above the rating grid; do not open modal; do not fire `paywall_shown`.
  4. On user-initiated retry (re-click Rate), the wall re-triggers at the backend (spec #50 enforces); the FE repeats the cycle — if dismissals exhausted grace, `show: true` returns and the modal re-opens.

- **Anonymous / logged-out users:** not reachable — `/learn/daily` requires auth. No guest surface in scope.

### 5.5 Win-back email

- New template: `app/templates/paywall_winback.html`. Same string-replace rendering as `daily_reminder.html` (§2.3). Placeholders: `{{name}}`, `{{discount_pct}}` (hardcoded `30` in builder; keeps template reusable if LD-3 retunes), `{{checkout_link}}`, `{{unsubscribe_link}}`.
- Builder: new helper `build_winback_email(user, dismissal_id) -> {subject, html}` in `app/services/email_service.py` or a new `win_back_service.py` (impl picks; the latter keeps `email_service` a pure transport).
- Send path: synchronous call to `email_service.send_email` from `POST /paywall-dismiss` when `win_back_eligible` flips true. No queue.
- **Sent-once guard:** before sending, the handler checks whether a win-back email was sent for this `(user_id, trigger)` within the last 30 days. Impl strategies (pick one):
  - **A (preferred):** add `winback_sent_at: TIMESTAMPTZ NULL` to `paywall_dismissals` — the row that crossed the threshold gets the timestamp set; the 30-day query checks `MAX(winback_sent_at) >= now() - 30d`. Adds one nullable column to the new table — cheap.
  - **B:** separate `paywall_winback_sends` table. Clean separation, more plumbing.
- **Link construction:** `checkout_link = f"{FRONTEND_URL}/pricing?winback=1&campaign={dismissal_id}&utm_source=email&utm_medium=winback&utm_campaign=paywall_dismiss_3x"`. The query params survive through the Stripe Checkout redirect via the existing `client_reference_id` / `metadata` plumbing — impl slice wires whichever carrier is easiest.
- **Unsubscribe link:** `f"{FRONTEND_URL}/email-preferences?token={user.email_preference.unsubscribe_token}"`. First production use of `unsubscribe_token` — the daily-reminder template does not inject it today. Impl slice may optionally backfill the daily reminder in the same commit; out-of-scope for this spec.
- **Coupon:** Stripe coupon ID for 30% off first month is an **operational prerequisite** (create in Stripe Dashboard; record ID as `STRIPE_WINBACK_COUPON_ID` env var). Impl slice reads env and passes `discounts=[{"coupon": coupon_id}]` to `stripe.checkout.Session.create`. See §9.
- **Send-time plan re-check:** `email_service.send_email` wrapper is generic; the re-engagement handler MUST re-load `user.subscription` immediately before sending and **skip-with-log** if the user upgraded since the dismissal was recorded (edge case in §8). This is a correctness check, not a race-window optimization.

## 6. Analytics events

All events landed in `.agent/skills/analytics.md` in the same commit as the impl slice (per P5-S21b convention).

| Event | Tier | Fires from | Props |
|-------|------|------------|-------|
| `paywall_shown` *(existing, do not redefine)* | FE | `PaywallModal.tsx` open `useEffect` | `{trigger, category_name?, cards_viewed?}` — today named `paywall_hit`; see note below |
| `paywall_dismissed` *(new)* | FE | `PaywallModal.tsx` "Not now" + X close handlers | `{trigger, dismissals_in_window: int, action_count_at_dismissal: int \| null, will_get_winback: bool}` |
| `winback_email_sent` *(new)* | BE | `/paywall-dismiss` handler after synchronous `send_email` success | `{trigger_counts: {daily_review: N, ...}, discount_pct: 30}` |
| `winback_email_clicked` *(new)* | FE | `/pricing` page on mount when `?winback=1` is present | `{campaign_id: string, hours_since_sent: int}` |
| `winback_converted` *(new)* | BE | `payment_service._handle_checkout_completed` when the Stripe session's metadata carries `winback_campaign_id` | `{hours_since_sent: int, subscription_amount: int}` |
| `inline_nudge_shown` *(optional, impl-slice call)* | FE | `WallInlineNudge.tsx` mount | `{trigger}` — impl MAY skip if telemetry value is judged low |

**Naming note on `paywall_shown` vs existing `paywall_hit`.** The codebase's current event name is `paywall_hit` (`PaywallModal.tsx:80`, `.agent/skills/analytics.md:41`). The stub and this spec use `paywall_shown` as the conceptual name. **Decision:** the impl slice keeps the existing event name `paywall_hit` — renaming breaks PostHog dashboards and violates the "deprecate, don't rename" convention in `.agent/skills/analytics.md:22`. Where this spec says `paywall_shown` treat it as a synonym for the already-wired `paywall_hit`. LD-6 still applies: the silent inline nudge does NOT fire `paywall_hit`.

**Campaign ID semantics:** `winback_email_clicked` and `winback_converted` carry a `campaign_id` that equals the `dismissal_id` of the row that tripped the threshold. This lets us join click → convert back to the originating dismissal without a separate campaigns table.

## 7. Acceptance criteria

- **AC-1 — Grace behavior (happy path).** A free user dismisses the `daily_review` paywall. Their next walled rate-click returns 402, FE calls `should-show-paywall`, receives `{show: false, attempts_until_next: 3}`, renders the inline nudge (not the modal). After 3 further walled rate-click attempts within the grace window, the modal re-appears on the 4th. Verified by Vitest for the FE flow and pytest for the backend counter.
- **AC-2 — Win-back trigger (30d window).** With the user-local clock advanced, 3 successful `POST /paywall-dismiss` calls for any combination of triggers within a rolling 30-day window cause the 3rd call to fire the win-back email (assuming churn guard passes). Verified by pytest: stub `email_service.send_email`, assert it was called once with the win-back subject and with `html_body` containing the unsubscribe link.
- **AC-3 — Pro never sees paywall or nudge.** A Pro user's `POST /paywall-dismiss` and `GET /should-show-paywall` both return `{show: false}` / `{win_back_eligible: false}`; the FE never renders either surface for Pros. The FE short-circuits before calling the endpoints when `_is_free` is false client-side. Verified by pytest (BE contract) and Vitest (FE short-circuit).
- **AC-4 — Inline nudge does not fire `paywall_shown`/`paywall_hit`.** After a dismissal, the silent inline nudge renders when the user retries within grace. PostHog capture for `paywall_hit` is NOT called. Verified by Vitest: mock `capture`; assert zero calls with `'paywall_hit'` across a dismissal → retry → nudge sequence.
- **AC-5 — Idempotency (60s window).** Two rapid `POST /paywall-dismiss` calls for the same `(user, trigger)` within 60 seconds produce one DB row; the second response has `{logged: false, dismissal_id: <first_row_id>}`. Verified by pytest: call twice with a 1-second gap; assert row count = 1 and second response echoes first `dismissal_id`.
- **AC-6 — Churn guard excludes fresh churners from win-back.** A user with `user.downgraded_at` set within the last 60 days and 3+ dismissals in the 30-day window receives `{win_back_eligible: false}` and no email. Advance the mock clock past the 60-day churn mark; next dismissal that keeps the 3-in-30 condition triggers the email. Verified by pytest.
- **AC-7 — Dismissal history survives plan changes.** Dismissals remain in the table across upgrade (`plan: free → pro`), downgrade (`plan: pro → free` via `customer.subscription.deleted` webhook), and persona changes. No DELETE fires on any plan-mutation path. Verified by pytest: seed dismissals; run both webhook handlers; assert rows unchanged.
- **AC-8 — `GET /should-show-paywall` latency budget.** Single indexed query on `(user_id, trigger, dismissed_at DESC)` returns in <50 ms p50 on a loaded prod connection. Verified by pytest with `time.perf_counter()` harness in CI (seed 10k dismissals across 100 users, assert p50 query time).

## 8. Edge cases

- **User dismisses, then immediately upgrades to Pro.** No inline nudge is shown (AC-3). Existing dismissal rows stay in the table for analytics (LD-7). `user.downgraded_at` is not touched on upgrade (it tracks downgrades).
- **User hits wall on multiple triggers (future, post-LD-1 scope expansion).** Each trigger has an independent grace counter (LD-2). Win-back threshold is also per-trigger — 3 dismissals of `daily_review` and 1 dismissal of `interview_limit` ≠ 4 toward the window; only the trigger whose count hits 3 qualifies for its win-back. Open question for the next trigger: should the threshold become cross-trigger ("3 dismissals across any triggers")? Out of scope here — revisit when the second trigger walls.
- **Clock skew / backdated dismissals.** `paywall_dismissals.dismissed_at` uses `DEFAULT now()` — server time only. The FE does not supply a timestamp. Prevents client clock games.
- **Win-back email sent but user upgraded before send.** The send path re-loads `user.subscription` immediately before calling `email_service.send_email` and skips-with-log if `plan == "pro"`. No email, no `winback_email_sent` event, log-line at INFO level ("skipping win-back; user upgraded post-dismissal-threshold").
- **Stripe webhook for downgrade fires while a dismissal is being logged (race).** `user.downgraded_at` write happens in a different request than the dismissal insert. Acceptable: the churn-guard read inside `/paywall-dismiss` is a plain `SELECT user.downgraded_at` at AC-evaluation time; if the webhook commits first, the guard sees the new timestamp and blocks the win-back. If the dismissal commits first, a subsequent dismissal will see the new `downgraded_at` and block.
- **Deleted user.** `paywall_dismissals.user_id FK` has `ON DELETE CASCADE` (matching the existing `subscriptions.user_id` FK in `app/models/subscription.py:14`). No new cascade logic; existing FK behavior suffices.
- **`trigger` string too long / empty / non-ASCII.** Pydantic request-model validator enforces `1 <= len(trigger) <= 64`. Invalid strings return 422; no silent truncation.
- **Concurrent `POST /paywall-dismiss` on a fresh user (row count 0).** Two concurrent requests both pass the 60s window check, both insert. Acceptable: LD-8's 60s dedup is a best-effort UX guard, not a strict uniqueness invariant. Analytics will see 2 rows instead of 1 on a vanishingly rare race; `dismissals_in_window` reads correctly.
- **Dismissal at count=15 (the wall boundary itself).** The daily wall's backend check is independent — the 16th rate-click on day 1 is the first walled attempt. Dismissal is recorded with `action_count_at_dismissal = 1`. Subsequent walled retries increment the FE-side grace counter, not `action_count_at_dismissal` (that field is captured at the moment of dismissal only).

## 9. Dependencies

- **Spec #50 (daily-card wall) — SHIPPED (`ebef7da`).** This spec presumes the wall exists as the paywall to dismiss. Reference point, not a co-slice.
- **`user.downgraded_at` column — NEW, impl-slice dependency.** Impl slice MUST add the column (Alembic migration) **and** wire `_handle_subscription_deleted` to set it in the same commit. The spec cannot ship without it or AC-6 is unverifiable.
- **Stripe coupon — OPERATIONAL PREREQUISITE.** Dhamo creates a 30%-off-first-month coupon in the Stripe Dashboard **before** P5-S26b-impl ships. Coupon ID lands in Railway env as `STRIPE_WINBACK_COUPON_ID`; `app/core/config.py` Settings gains a new optional field in the same impl commit.
- **Resend win-back template — CONTENT TASK.** `app/templates/paywall_winback.html` drafted in the impl slice. Subject line locked: `"We'd love to have you on Pro — 30% off your first month"`.
- **Rule-14 spec prerequisite — SATISFIED BY THIS FILE.** Per CLAUDE.md R14, no code ships without a spec. This file is that spec.
- **`.agent/skills/payments.md` + `analytics.md` updates** — bundled into the impl-slice commit (same P5-S21b convention that §6 references).

## 10. Test plan (to be written in P5-S26b-impl BEFORE implementation per Rule 1)

### 10.1 Backend pytest (`hirelens-backend/tests/`)

- `test_post_paywall_dismiss_logs_row` — AC-1 base case. Free user; POST with `{trigger: "daily_review", action_count_at_dismissal: 1}`; assert one new row in `paywall_dismissals` + response `{logged: true, dismissals_in_window: 1, win_back_eligible: false}`.
- `test_post_paywall_dismiss_is_idempotent_within_60s` — AC-5. Two POSTs 1 second apart for the same `(user, trigger)`; assert row count = 1, second response `{logged: false, dismissal_id: <first>}`.
- `test_post_paywall_dismiss_after_60s_creates_new_row` — AC-5 negative. Two POSTs 61 seconds apart; assert row count = 2.
- `test_3rd_dismissal_in_30d_fires_winback_email` — AC-2. Seed 2 dismissals 10 and 20 days ago; 3rd POST triggers `email_service.send_email` (stub + assert once); `winback_email_sent` event fires; response `win_back_eligible: true`.
- `test_winback_not_sent_if_fresh_churner` — AC-6. User with `downgraded_at = now() - 30 days`; seed 3 dismissals in the window; assert `email_service.send_email` NOT called; response `win_back_eligible: false`.
- `test_winback_sent_after_churn_guard_expires` — AC-6 negative. User with `downgraded_at = now() - 61 days`; 3 dismissals; assert email sent.
- `test_winback_skipped_if_user_upgraded_before_send` — §8. User dismisses; between threshold-check and send, simulate upgrade (mutate `sub.plan = "pro"` mid-call via monkeypatch); assert email NOT sent, INFO log emitted.
- `test_winback_sent_once_per_30d_window` — §5.5 sent-once guard. Seed 3 dismissals → email sent. Seed 4th, 5th dismissals in same window → email NOT re-sent; response `win_back_offered: true` on subsequent `GET /should-show-paywall`.
- `test_pro_user_post_paywall_dismiss_returns_show_false_everywhere` — AC-3 contract-level. Pro user; POST and GET both respond with `show: false` / eligible flags false; no row inserted.
- `test_dismissals_survive_upgrade_and_downgrade` — AC-7. Seed 2 dismissals; simulate `checkout.session.completed` webhook (upgrade) and `customer.subscription.deleted` (downgrade); assert both rows unchanged.
- `test_downgrade_webhook_sets_user_downgraded_at` — LD-5 impl. Simulate `customer.subscription.deleted`; assert `user.downgraded_at ≈ now()`.
- `test_should_show_paywall_returns_show_true_with_no_history` — GET contract. Free user, zero dismissals; assert `{show: true, attempts_until_next: 3, win_back_offered: false}`.
- `test_should_show_paywall_returns_show_false_within_grace` — GET contract. Seed 1 dismissal 10 seconds ago; assert `show: false`.
- `test_should_show_paywall_returns_show_true_after_grace_exhausted` — Strategy A: FE passes `attempts_since_dismiss=3` query param; assert `show: true`.
- `test_should_show_paywall_latency_budget` — AC-8. Seed 10k dismissals across 100 users; `time.perf_counter()` wraps single endpoint call; assert p50 < 50 ms (may use a loose `< 100 ms` threshold in CI if machine-variance is high — tighten to 50 ms for impl-slice review).
- `test_invalid_trigger_returns_422` — §5.3 errors. Empty string; 65-char string; missing field; each returns 422.
- `test_unauthenticated_returns_401` — standard auth.

Expected BE test count delta at P5-S26b-impl ship: **+16** (265 → 281). Actual delta may differ — impl slice locks the final count.

### 10.2 Frontend Vitest (`hirelens-frontend/tests/`)

- `PaywallModal.dismiss.test.tsx`:
  - "Not now click fires `paywall_dismissed` + POST /paywall-dismiss then closes"
  - "X close button fires the same sequence (same semantic)"
  - "dismissal error path: POST fails → modal still closes, toast shown, no `paywall_dismissed` event"
- `QuizPanel.dismiss.test.tsx`:
  - AC-1: mock 402 → mock GET `{show: true}` → modal opens → Not now click → next 402 → mock GET `{show: false}` → inline nudge renders, modal does NOT open
  - AC-4: across the AC-1 flow, assert `capture('paywall_hit', ...)` fires exactly once (on the first modal open), not on the inline-nudge mount
  - AC-1 grace-exhaust: 4 walled retries post-dismiss → 4th time GET returns `{show: true}` → modal re-opens
- `WallInlineNudge.test.tsx`:
  - Renders the locked LD-6 copy verbatim
  - Uses design-system tokens (snapshot contains `text-text-muted`, `border-border-accent/30`, no hex)
  - Optional: `inline_nudge_shown` fires on mount (skip if impl drops this event)
- `Pricing.winback.test.tsx`:
  - `?winback=1&campaign=<uuid>` on URL → `winback_email_clicked` fires once on mount with `{campaign_id, hours_since_sent: int}`
  - `hours_since_sent` computed from a signed / hashed timestamp — impl picks the carrier (likely `campaign_id` joined with a BE lookup on mount; spec defers mechanism to impl)

Expected FE test count delta at P5-S26b-impl ship: **+10** (161 → 171). Actual delta locked by impl slice.

### 10.3 Integration / manual post-deploy

- **Free user, dismiss + nudge loop**: log in, walk to 16th rate submit, modal shows, click "Not now", next rate submit shows inline nudge, repeat 3 times, 4th re-opens modal.
- **Win-back email**: back-date two `paywall_dismissals` rows via `psql`, dismiss again, check Resend dashboard for delivery + click through the email, land on `/pricing?winback=1&campaign=<uuid>` and convert; verify `winback_converted` fires with correct `subscription_amount`.
- **Churn guard**: `UPDATE users SET downgraded_at = now() - interval '30 days' WHERE id = <test>;`, dismiss 3 times, confirm no email sent + log line "win-back skipped; recent churn".
- **Pro invariant**: upgrade to Pro, verify that the `/learn/daily` flow does not 402 at all (spec #50 guarantee) and that the FE never calls `/should-show-paywall` or `/paywall-dismiss`.

## 11. Threshold retune plan

The four numbers in LD-3 are intuition:
- 3-attempt grace per trigger
- 3 dismissals in 30 days → win-back
- 30% off first month
- `paywall_winback.html` subject + copy

After 30 days of production dismissal data, pull the following metrics from PostHog:

1. **Grace-window utilization.** Distribution of `action_count_at_dismissal` across all rows. If p50 > 1 (most users dismiss only after multiple walled tries), the grace may already be too short. If p90 == 1 (everyone dismisses on first wall), 3 is fine or could even tighten to 2.
2. **Dismissal-to-conversion latency.** For users who dismissed and later converted, histogram the hours/days between last-dismissal and `payment_completed`. If the median is <24h, the inline nudge is doing enough and the email may be noise. If median is >7d, the email is load-bearing.
3. **Win-back funnel.** Sent → open → click → convert. If convert-rate <5% of opens, either raise the discount (40%? 50%?), lengthen the first-month trial, or switch to a different CTA (annual discount, free strategy call, etc.). If convert-rate >20%, we're under-discounting — dial it back.
4. **Comparative: dismissed vs walled-without-dismissing.** The `paywall_hit` event's denominator minus the `paywall_dismissed` numerator gives the "walled but didn't dismiss — closed tab" cohort. If that cohort is 3× bigger than the dismissed cohort, dismissal isn't the main leak — rewall copy/flow, not email cadence, is the lever.

**Documented amendment path:** retunes land as follow-up commits amending this spec file's LD-3 block, with a dated note ("LD-3 retune 2026-MM-DD: grace 3→5 based on p50 action_count=4"). No new spec file; same commit convention as LD-001's 2026-04-19 amendment in SESSION-STATE.

## 12. Out of scope / follow-ups

- **Other triggers (`scan_limit`, `card_limit`, `locked_category`, `interview_limit`, `skill_gap_study`).** Per LD-1, those land as zero-backend-change rewires when their respective walls become live. Each will need a spec-note or small follow-up spec documenting the trigger's `action_count_at_dismissal` semantics (how the FE counts walled attempts for that feature).
- **Cross-trigger win-back aggregation.** If a user dismisses 2 daily_review + 2 interview_limit in the same 30d window, that's intent — but our threshold only counts same-trigger. Revisit when the 2nd trigger goes live.
- **Per-plan grace tuning** (e.g., Enterprise-adjacent team users get a longer grace). Out of scope — no Enterprise-team flow lives in Phase 5.
- **Email cadence controls.** Win-back is a single one-shot email per 30d window. No 2nd-chance email, no drip sequence. Add later if conversion data argues for it.
- **Rate-limit hardening on `/paywall-dismiss`.** The 60s idempotency window (LD-8) is a correctness guard, not a rate limit. A per-user 429 ceiling is reserved for future if we see abusive clients; documented in §5.3 errors as "reserved."
- **Unsubscribe-link backfill on `daily_reminder.html`.** This spec introduces the unsubscribe-link pattern for the win-back template. The daily-reminder template could backfill it in the same impl commit; not required.
- **`inline_nudge_shown` analytics event.** Optional per §6 / §5.4. Impl slice decides based on telemetry-cost vs instrumentation-value tradeoff.
- **Stripe Customer Portal integration for dismissal.** Stripe's portal has its own cancellation flow (spec #36 / E-013); this spec doesn't touch it. Churn signals from the portal are independent from `paywall_dismissals`.
- **`paywall_hit` vs `paywall_shown` rename.** Locked in §6 as "do not rename." The semantic-name drift between spec and code is acceptable.

## 13. Open questions

**None.** All eight LDs are locked in §3; all infra deviations (B, F) are resolved in §2 and §9; the path-prefix correction (`/billing/` → `/payments/`) is documented in §2.2.

---

*Next slice: P5-S26b-impl — implements this spec. The impl slice's Step-1 audit must surface (a) the `user.downgraded_at` migration impact on existing free users, (b) the `STRIPE_WINBACK_COUPON_ID` env var wiring in `app/core/config.py`, (c) the FE grace-counter strategy choice (§5.3 Strategy A vs B). Do not ship without those three audit findings explicit in the commit message.*
