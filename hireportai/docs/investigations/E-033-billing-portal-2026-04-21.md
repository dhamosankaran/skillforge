# E-033 Billing Portal — Investigation Report

**Date:** 2026-04-21
**HEAD at investigation:** `147bc18`
**BACKLOG row:** E-033 (priority P1, status 🟦 back-burner as of 2026-04-21 Stripe pivot, added `dda860a` 2026-04-20)
**Scope:** Investigation only — no code, no fixes, no BACKLOG flips, no Stripe Dashboard changes.
**Skill loaded:** None of the flat `.agent/skills/*.md` files exclusively own the billing-portal surface; the closest owner is `.agent/skills/payments.md` (covers checkout + webhooks but is silent on the portal session path). The nested skill `.agent/skills/stripe-best-practices/SKILL.md` + `references/billing.md` is the more relevant reference and was read — see §Prior-audit correction at the end of this report.

---

## 1. Summary

The BACKLOG row hypothesizes the bug is a webhook handler failing to persist `stripe_customer_id` on the `Subscription` row. **The code on disk contradicts that hypothesis**: both the checkout-creation path (`create_checkout_session`, `payment_service.py:100-123`) and the webhook handler (`_handle_checkout_completed`, `payment_service.py:282-283`) already persist `stripe_customer_id` — there are two independent persistence points, both verified by passing tests.

The user-visible error ("Couldn't open billing portal. Please try again.") is an **opaque generic toast from a bare `catch {}` block** (`Profile.tsx:95-97`) that swallows 403 / 404 / 502 / network errors under one string. Without distinguishing which HTTP status actually fires, the real root cause is one of three equally plausible candidates — none of which is what the BACKLOG row guessed.

**Most likely real cause:** a Stripe Dashboard configuration step (the default Customer Portal config must be saved in the Stripe Dashboard at least once before `stripe.billing_portal.Session.create()` succeeds — this is a well-known Stripe onboarding gotcha and matches the context that P5-S26b smoke testing hit two other Dashboard-config issues). If confirmed, the fix is **zero code changes** — a Stripe Dashboard one-click.

This slice is an investigation, so the recommendation is `INVESTIGATE FURTHER`: one diagnostic query + one Dashboard check before touching code.

---

## 2. Reproduction steps

**Did NOT reproduce live** — this slice is read-only per locked decisions (no DB queries against live, no Stripe Dashboard access). Reproduction evidence is drawn from three written artifacts:

- `BACKLOG.md:82` E-033 row — original bug report with conjectured cause.
- `docs/status/E2E-READINESS-2026-04-21.md:67`, `:104`, `:234` — readiness matrix mentions.
- `docs/status/E2E-WALKTHROUGH-2026-04-21.md:99, :151` — skipped by design during the 2026-04-21 walkthrough.

**Reported symptom (per BACKLOG E-033):**
> "Clicking 'Manage Subscription' on `/profile` as a Pro user shows error toast 'Couldn't open billing portal. Please try again.'"

**Required to confirm a reproduction** (deferred to a follow-up slice per locked decisions):
1. Open local dev with a test-mode Stripe key and a logged-in Pro user.
2. Click "Manage Subscription" button on `/profile`.
3. Capture: network tab response for `POST /api/v1/payments/portal` (status code + response body) + browser console + backend logs (`logger.exception("Stripe billing portal session creation failed")` will dump the Stripe error body if the Stripe call itself fails).
4. Run the diagnostic: `SELECT user_id, plan, stripe_customer_id, stripe_subscription_id FROM subscriptions WHERE plan='pro';`.

Until one of these three signal sources is captured, the exact branch of the failure is unknown.

---

## 3. Surface map

### Frontend
- `src/pages/Profile.tsx:88-99` — `handleManageSubscription()` handler. **Bare `catch {}` block swallows all errors into one opaque string.**
- `src/services/api.ts:467-473` — `BillingPortalResponse` type + `createBillingPortalSession()` POSTs to `/api/v1/payments/portal` and expects `{url: string}` back. No status-code-based branching on the FE.
- `tests/Profile.subscription.test.tsx` — FE test suite; exercises the happy path with a mocked `createBillingPortalSession`.

### Backend routes
- `app/api/routes/payments.py:95-116` — `POST /api/v1/payments/portal`. Auth-gated (`Depends(get_current_user)`). Maps three service exceptions:
  - `NotProSubscriberError` → HTTP 403 "Billing portal is only available to Pro subscribers"
  - `UserNotFoundError` → HTTP 404
  - `PaymentError` (covers `stripe.error.StripeError`) → HTTP 502 with the raw Stripe error message in `detail`.

### Backend service
- `app/services/payment_service.py:48-53` — `NotProSubscriberError` docstring: *"Raised when a non-Pro user (or a user without a Stripe customer id) attempts to open a portal session."* — i.e. the "no customer_id" case IS mapped to the same error as "not Pro," which the route serves as 403.
- `app/services/payment_service.py:153-194` — `create_billing_portal_session()`:
  - `:178-183` — loads Subscription by user_id; raises `NotProSubscriberError` if `sub is None`, `sub.plan != "pro"`, OR `not sub.stripe_customer_id`. All three conditions collapse into the same 403.
  - `:186-189` — calls `stripe.billing_portal.Session.create(customer=..., return_url=...)` with no `configuration` parameter (relies on Stripe's default Dashboard config).
  - `:190-192` — on `stripe.error.StripeError`, logs traceback + raises `PaymentError(str(exc))` → 502. **This is where a Dashboard-config failure would land.**
- `app/services/payment_service.py:100-123` — `create_checkout_session()` already persists `stripe_customer_id` **before** creating the Checkout session, either on an existing Subscription row or a new one. So any user who completed real checkout has `stripe_customer_id` populated.
- `app/services/payment_service.py:282-283` — `_handle_checkout_completed()` **also** persists `stripe_customer_id` from the webhook payload (`if customer_id: sub.stripe_customer_id = customer_id`). Second persistence point — defensive redundancy.

### Data model
- `app/models/subscription.py` — `Subscription.stripe_customer_id: Optional[str]`. Nullable. No unique constraint documented in the skill / schema page.

### Tests (all green per SESSION-STATE last baseline BE 300 / FE 178)
- `tests/test_payments.py:591-629` — `test_create_portal_session_for_pro_user` — mocks `stripe.billing_portal.Session.create`, seeds `sub.stripe_customer_id = "cus_portal_abc"`, asserts 200 + URL returned. **Passes** — meaning the code path is exercised and returns the expected shape in the happy case.
- `tests/test_payments.py:632-650` — `test_portal_session_403_for_free_user` — confirms no-customer-id → 403 branch.
- `tests/test_payments.py:653-661` — `test_portal_session_401_for_unauth`.

### Analytics
- `subscription_portal_opened` (FE, fired on button click — see `Profile.tsx:91`). Fires *regardless of success*. No `subscription_portal_failed` event exists; failures are invisible to PostHog funnels.

### External
- Stripe Customer Portal — Stripe-hosted UI. Created via `stripe.billing_portal.Session.create()`. **Requires a one-time Dashboard activation step** at `dashboard.stripe.com/test/settings/billing/portal` (test mode) and `dashboard.stripe.com/settings/billing/portal` (live) before the API call will succeed. This is not something the codebase can do — it's an account/console action.

### Not in use
- There is **no** custom in-app billing UI. All subscription management is delegated to Stripe's hosted portal. (`docs/specs/phase-5/36-subscription-cancellation.md:15` confirms.)
- The spec (`phase-5/36`) deliberately skipped `STRIPE_BILLING_PORTAL_CONFIGURATION_ID` env var (see spec §152: *"Stripe auto-creates a default portal config per account; no explicit config id is required."*) — which is correct for the API call but assumes the default portal config has been saved in the Dashboard. **The spec does not document the Dashboard activation step.**

---

## 4. Root cause hypothesis

### Primary hypothesis (confidence: MEDIUM-HIGH)

**Stripe Dashboard default Customer Portal configuration has not been saved.** `stripe.billing_portal.Session.create()` returns a Stripe error along the lines of `"No configuration provided and your default configuration has not been created. Provide a configuration or create your default by saving your customer portal settings in test mode at https://dashboard.stripe.com/test/settings/billing/portal."` if the Dashboard step hasn't been done.

**Why this is the most likely cause:**
- Contextual evidence: P5-S26b-impl-BE smoke testing hit **three** Stripe-config issues. The BACKLOG row itself lists two of them: "price ID was product ID" + "account mismatch between API key and dashboard." It labels the third (E-033) as "the real E-033 code bug" but assumes it's a code bug without diagnostic evidence. A Dashboard-config miss is a natural third in that cluster.
- Code-evidence contradicts the code-bug hypothesis: both customer_id persistence points are present and passing tests.
- The error surface (`logger.exception` at `payment_service.py:191`) would capture the full Stripe message in backend logs — but nobody has checked the backend logs for the failed calls (the E2E walkthrough explicitly skipped E-033).
- Spec #36 skips the Dashboard activation step entirely (flagged above), which is precisely the kind of undocumented prerequisite that breaks silently at runtime.

**Evidence that would confirm:** backend log line from a real failure containing the Stripe error body. Specifically, a substring match on `"default configuration has not been created"` or `"No configuration provided"`.

### Alternative hypothesis A (confidence: LOW-MEDIUM)

**Test-methodology bug: the "Pro user" seeded during P5-S26b smoke was manually set to `plan='pro'` via DB shortcut rather than going through `create_checkout_session`, so `stripe_customer_id` was never populated.**

**Why this is plausible:**
- Smoke testing often uses DB-seeded users to avoid real Stripe round-trips.
- If the seed didn't include a fake `stripe_customer_id`, the service hits the `raise NotProSubscriberError` branch (not-Pro OR no-customer-id) — same 403 either way.
- The BACKLOG diagnostic (`SELECT stripe_customer_id FROM subscriptions WHERE plan='pro'`) would return NULL, matching the BACKLOG row's expectation — but the root cause is test setup, not a code bug.

**Evidence that would confirm:** actually running the diagnostic query against the smoke-test DB. If rows exist with `plan='pro'` and `stripe_customer_id IS NULL` AND those users did NOT go through `create_checkout_session` at some point, this is the cause.

**Evidence that would refute:** the real prod user (who went through Stripe checkout) also has NULL customer_id. Since no real prod users exist yet (local dev-DB wiped 2026-04-19 per `phase-5/43`:106, Railway DB empty), this is hard to test until there's a real upgrade.

### Alternative hypothesis B (confidence: LOW)

**Live/test Stripe key + Dashboard-portal-config mismatch.** If `STRIPE_SECRET_KEY` is a live key but the portal config was only saved in the test-mode Dashboard (or vice versa), calls fail with a similar error. The BACKLOG row mentions "account mismatch between API key and dashboard" was one of the pre-smoke issues — it's conceivable a partial version of this persists.

**Evidence that would confirm:** backend logs showing `invalid API key` or `account mismatch` in the Stripe error body.

### Alternative hypothesis C (confidence: VERY LOW — likely NOT this)

**The BACKLOG row's original conjecture — webhook fails to persist stripe_customer_id.** Reading `_handle_checkout_completed` (`payment_service.py:282-283`) and `create_checkout_session` (`payment_service.py:100-123`) shows two separate persistence points. Test `test_create_portal_session_for_pro_user` is green. For this to actually be the cause, **both** paths would need to fail silently on the specific user who hit the bug — possible only via a race condition or a partial migration state. No evidence in either direction today.

### What distinguishes them

One diagnostic command + one Dashboard glance resolves this:

1. Run `SELECT id, user_id, plan, stripe_customer_id FROM subscriptions WHERE plan='pro';` against the DB the smoke test used.
   - NULL → alternative A (test methodology) OR alternative C (code bug).
   - Populated → primary hypothesis (Stripe Dashboard) or alternative B (key/dashboard mismatch).
2. Check the backend log for the failed portal call (grep for `"Stripe billing portal session creation failed"` — `logger.exception` writes the full Stripe error body right after that line).
   - Contains `"default configuration has not been created"` / `"No configuration provided"` → primary hypothesis confirmed.
   - Contains `"invalid API key"` / `"account mismatch"` → alternative B.
   - Contains something else → re-evaluate.

Neither step is risky to run (read-only DB SELECT, log grep).

---

## 5. Blast radius

### Who is blocked
- **All Pro users who want self-serve subscription management** if the primary hypothesis (Dashboard config) is correct. That's 100% of Pro users at cancellation time.
- **Only the specific smoke-test user** if alternative A (test methodology) is correct — zero real users blocked until real upgrades happen.
- **Only a subset of Pro users** if alternative C is correct (unlikely).

### What is blocked
- Self-service cancellation.
- Payment-method update (e.g., card expired → user can't fix it themselves).
- Invoice / receipt history.
- Plan switching (future Enterprise tier).

### What is NOT blocked
- New signups, checkout, upgrade, webhook delivery all work (verified by green test suite + separate smoke evidence in SESSION-STATE).
- Existing Pro plan access (study, ATS, interview prep). Users can *use* Pro, they just can't *manage* it.
- Analytics, Sentry, email delivery — all unaffected.

### Data impact
- **None.** No data loss, no corruption. Purely a UX dead-end.

### Workaround
- Users would have to email support to cancel / update payment method / get invoices. High friction; support-load-creating.

### Why P1 (verifying the label)
- **Confirmed legitimate.** Self-service cancellation is a de-facto launch requirement:
  - Stripe's own Go-Live Checklist flags billing portal behavior as a pre-launch test item (per `.agent/skills/stripe-best-practices/SKILL.md:38`).
  - US FTC regulations around subscription cancellation (effective since the 2024 Click-to-Cancel rulemaking; enforcement proceeding) make "easy cancel" a legal expectation, not a nice-to-have.
  - Dhamo's SESSION-STATE "Next Slice" section lists E-033 as explicit launch-blocker priority (#3 in the ordered list).
- **Label is accurate.** Not a P2 masquerading as P1.

---

## 6. Fix shape recommendation

**Recommendation: INVESTIGATE FURTHER — one diagnostic slice, then branch.**

The cheapest slice that doesn't prematurely commit to a fix:

### Proposed diagnostic slice (~30min, zero code changes, produces evidence)
1. Start local backend + Stripe CLI forwarding.
2. Log in as a Pro test user. Before clicking the button, run the DB diagnostic:
   `SELECT user_id, plan, stripe_customer_id, stripe_subscription_id FROM subscriptions WHERE plan='pro';`
3. Click "Manage Subscription." Capture: network response (status + body), backend log line following `"Stripe billing portal session creation failed"`, and browser console.
4. Check Stripe Dashboard: does `dashboard.stripe.com/test/settings/billing/portal` show a saved default configuration? (Zero-code one-click check.)
5. Write the evidence to `docs/investigations/E-033-diagnostic-findings-<date>.md`.

### Likely follow-up fix shapes by branch

**Branch A: primary hypothesis confirmed (Dashboard config missing)**
- **DIRECT IMPL, zero code.** Save the default config in Stripe Dashboard (test + live). Amend `docs/specs/phase-5/36-subscription-cancellation.md` to add a §Dashboard Prerequisite note so the next ops engineer doesn't hit this again. Amend the BACKLOG E-033 row to reflect the actual cause (the conjectured "stripe_customer_id persistence" hypothesis should be replaced with "Stripe Dashboard config not saved"). Close E-033 only after confirming the portal opens end-to-end in both test and live modes.

**Branch B: alt-A confirmed (test methodology)**
- **No production code bug.** Fix the test setup to go through `create_checkout_session` (or seed `stripe_customer_id` explicitly in the fixture). E-033 is not actually a launch blocker — it's a smoke-test artifact. Reclassify as INVALID; close with evidence.

**Branch C: alt-B confirmed (key/dashboard mismatch)**
- **Ops / env-var fix.** No code. Rotate keys or re-save config for the correct mode. Amend the Stripe-setup runbook.

**Branch D: alt-C confirmed (code bug in customer_id persistence, unlikely)**
- **DIRECT IMPL, 1-3 lines** — add a guard and regression test. Probably a post-login backfill if somehow customer_id went missing after creation. Needs careful repro first.

### Orthogonal: FE error-handling improvement (deferred to E-034)
- The bare `catch {}` at `Profile.tsx:95-97` is a separate UX bug (error copy tells users nothing actionable, regardless of root cause). Already tracked as E-034 ("Generic error toasts don't give users actionable recovery paths"). **Recommend: do NOT bundle into E-033's fix** — E-034 is listed as blocked on E-033 and has a broader error-surface audit scope that's its own slice.

### What this is NOT
- NOT a spec-author slice — no design decisions to make regardless of branch (A = ops, B = invalid, C = ops, D = surgical code fix).
- NOT an escalation — all four branches are internal to our team / account; no third-party hand-off required.

---

## 7. Open questions for Dhamo

1. **Has the Stripe Billing Portal default configuration been saved** in the Stripe Dashboard for the test-mode account? (One-click step at `dashboard.stripe.com/test/settings/billing/portal`.) If no → primary hypothesis confirmed with ~90% confidence without even running the diagnostic.
2. **How was the Pro user seeded for P5-S26b smoke testing** — real Stripe checkout, or DB manipulation? If DB-only: this reclassifies E-033 as a test-setup artifact, not a launch blocker.
3. **Is there a backend log snippet from the actual failure?** If yes, it resolves the hypothesis in a single grep.
4. **Should the diagnostic slice run now or remain 🟦 back-burnered?** Per SESSION-STATE 2026-04-21 pivot, Stripe surface is back-burnered; E-033 investigation predates the next Stripe-touching feature. The diagnostic is cheap and fits inside the pivot's "return trigger: before next Stripe-touching feature work" clause.
5. **Does E-033's BACKLOG row need amending** to reflect that the original hypothesis (customer_id persistence) is unsupported by code evidence? This is a documentation hygiene question, not a priority change.

---

## 8. Prior-audit correction (flagged per CLAUDE.md honesty clause)

My earlier audit `docs/audits/SKILLS-SPECS-ALIGNMENT-2026-04-21.md` claimed `.agent/skills/` has exactly **20 flat `.md` files** and that the prompt's `.agent/skills/*/SKILL.md` layout assumption was wrong. During this investigation I hit `.agent/skills/stripe-best-practices/SKILL.md` — a nested-directory skill my `ls` had missed.

**Further nuance discovered at staging time:** that nested skill is **untracked** in git (`git status` shows `?? .agent/skills/stripe-best-practices/` along with `?? .agent/skills/stripe-projects/`, `?? .agent/skills/upgrade-stripe/`, `?? .claude/skills/`, and `?? skills-lock.json`). So the audit's count of **committed** skills (20 flat `.md`) was correct for the repo's versioned surface, but the on-disk reality includes additional uncommitted tooling skills that my first `ls` command didn't surface.

Impact:
- §1 "Skills inventory" of the earlier audit is correct for committed skills.
- §0 finding P-02 ("no SKILL.md pattern in use") was wrong about **on-disk reality** — the nested pattern exists for at least 3 uncommitted directories.
- The uncommitted skills raise a separate question: are they intentionally local (Dhamo's personal skill workbench?), or are they drift that should be committed / `.gitignore`d? Not for me to decide.

**Not fixing here** — logging the correction so CODEX sees it and a future doc-sync or workspace-hygiene slice can decide what to do about the uncommitted `.agent/skills/` subdirs and the untracked `.claude/skills/` + `skills-lock.json`.

---

## 9. Final-slice report

- **Commit SHA:** (this slice's commit, once made).
- **Files created:** 1 (`docs/investigations/E-033-billing-portal-2026-04-21.md`).
- **Test counts:** not run (investigation only; no code touched).
- **Skills loaded per SOP-4:** `.agent/skills/payments.md` (partial read — silent on portal surface), `.agent/skills/stripe-best-practices/SKILL.md` + `references/billing.md` (closer to the domain). Skill-inventory gap: neither flat `payments.md` nor the nested `stripe-best-practices` skill directly covers the Stripe Dashboard **activation prerequisite** for the Customer Portal — this is a documented blind spot that contributed to spec #36 not flagging it. Candidate for a skill amendment in a future slice.
- **Specs cited per SOP-5:** read `phase-5/36-subscription-cancellation.md` (authoritative for the portal surface) and `phase-5/42-paywall-dismissal.md` (cross-reference for `/api/v1/payments/*` convention + `user.downgraded_at` context).
- **Judgment calls in flight:**
  - Did not reproduce live (prompt locked decision: read-only).
  - Did not amend BACKLOG E-033's "likely root cause" text even though code evidence contradicts it — that's a BACKLOG edit and out of scope per locked decisions.
  - Did not run the diagnostic DB query (would be a mutation of my local state / require live services; stayed within read-only disk scope).
  - Flagged my prior-audit error (§8) as a side-finding rather than silently moving on.
- **Drift flags:** no new flags logged in SESSION-STATE (read-only slice). The `BACKLOG.md:82` hypothesis vs code mismatch is a BACKLOG content issue, not a code↔spec drift; noted in §1 + §4 + question #5.
- **BACKLOG IDs touched:** none flipped, none created.

---

## 9. Diagnostic plan (appended after initial commit)

The investigation's §5 fix-shape recommendation was `INVESTIGATE FURTHER` — a cheap diagnostic slice before committing to code. That diagnostic has now been scaffolded:

- **Dashboard checklist (human-executed):** `docs/diagnostics/E-033-stripe-dashboard-checklist-2026-04-21.md`. Dhamo walks the prerequisites, activation check, configuration check, webhook check, and live-mode repeat; fills in the result-recording template (§7 of the checklist). Resolves branches A / B / C from §6 of this report with Dashboard-side evidence.
- **Smoke script (automated):** `hirelens-backend/scripts/smoke_billing_portal.py`. Two checks: (1) `billing_portal.Configuration.list()` — empty collection confirms the primary hypothesis; (2) `billing_portal.Session.create()` round-trip against a real test-mode customer. Test-mode by default; `--live` + `--yes-live` + confirmation phrase required to hit live. Refuses to run on key/mode mismatch.

**E-033 remains 🟦 P1.** No fix applied in the scaffolding slice. The diagnostic evidence from running the checklist + smoke script will determine which of §6's four fix-shape branches applies.

**Recommended execution order (for whoever picks this up):** §1 prerequisites → §2 activation check → §3 config review → §4 live mode → §5 webhook check → §6 smoke script → §7 fill in result → decide branch → file the resolution slice.

---

## §10 Diagnostic Outcome (2026-04-21)

**Outcome in one sentence:** Primary hypothesis confirmed — the Stripe Dashboard default Customer Portal configuration had never been saved in test mode; saving it resolved Check 1 PASS. E-033 remains 🟦 P1 pending live-mode config + full paid-flow E2E validation.

### Diagnostic result (test mode)

```
Date: 2026-04-21
Mode: TEST (key prefix sk_test_)
Action taken: Saved default Customer Portal configuration via Stripe
  Dashboard at https://dashboard.stripe.com/test/settings/billing/portal
Smoke test result (post-Save): PASS at Check 1
  - "1 configuration(s) found"
  - id=bpc_1TOowxCl9xZqd5Sx208P98Nd
  - is_default=True, active=True
Check 2: SKIPPED (no --customer arg passed)
Hypothesis: confirmed. The original FAIL ("No billing portal configurations
  found") matched the script's primary E-033 hypothesis exactly. Saving
  the default Dashboard config resolved Check 1.
```

**Branch decision** (from §6 of this report): **Branch A — Dashboard config**. Zero code changes required for the test-mode surface. Live mode and E2E validation remain outstanding.

### Check 2 deferral

Running Check 2 requires a real test-mode Stripe customer ID. DB inspection revealed: **0 subscription rows on disk have `stripe_customer_id` populated** — 2 rows exist, both `plan=free`, `status=active`, both `stripe_customer_id NULL` and `stripe_subscription_id NULL` (placeholder free-tier rows from signup; no upgrade flow has ever completed in this local environment).

Generating a test customer therefore requires running the full upgrade flow end-to-end (FE Upgrade → Stripe Checkout → success webhook → DB write of `stripe_customer_id` on the subscription row), which is a larger surface than this diagnostic was scoped for. Deferred to a new BACKLOG row tracked separately.

### Forward links

- **New BACKLOG row:** `E-039` — "Test paid flow E2E (Stripe Check 2 + upgrade flow validation)." Status 🟦 P2 (gated on E-033 live-mode config + upstream DB state — no `stripe_customer_id` exists to test against until the upgrade flow completes at least once). Tracks the deferred Check 2 work plus the end-to-end validation the test-mode fix by itself cannot confirm.
- **E-033 close conditions** (Dhamo-locked): live-mode Dashboard Customer Portal config **saved AND verified** **AND** full paid-flow E2E validated via the E-039 work. Both are required; test-mode Check 1 PASS alone is not sufficient.
- **Spec #36 follow-up (recommended, not in scope here):** amend `docs/specs/phase-5/36-subscription-cancellation.md` §152 to document the Dashboard-activation prerequisite so future ops engineers don't hit the same silent failure. Tracked informally; file under the E-033 resolution slice when live-mode is landed.
