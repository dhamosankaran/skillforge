# E-033 Stripe Dashboard Checklist — 2026-04-21

**For:** Dhamo (or whoever has Stripe Dashboard access for the SkillForge account).
**Goal:** Confirm or refute the primary E-033 hypothesis — that the Stripe Dashboard default Customer Portal configuration has never been saved, which would cause `stripe.billing_portal.Session.create()` to fail with an opaque Stripe error and surface as "Couldn't open billing portal. Please try again." in the Profile UI.
**Paired with:** `hirelens-backend/scripts/smoke_billing_portal.py` — run this checklist first, then run the smoke script to verify.
**Investigation report:** `docs/investigations/E-033-billing-portal-2026-04-21.md` (see §4 for hypothesis, §5 for fix-branch decision tree).
**Scope:** Diagnostic only. No fix to E-033 is applied by this document. E-033 remains 🟦 P1.

---

## 1. Prerequisites

Before starting, confirm you have all of the below. Missing any one of these blocks the checklist — stop and resolve.

| Prerequisite | How to verify |
|---|---|
| Stripe account owner or admin role | Log into `dashboard.stripe.com`. Click your avatar top-right → "Account settings" → "Team." Your row must show role = Owner or Administrator. Developer / Analyst roles cannot save portal config. |
| Access to both test and live modes | Top-left toggle in the Dashboard flips between "Test mode" and live. Confirm you can flip it. Some accounts have live mode pending activation — if so, skip §4 and resume when live is activated. |
| `STRIPE_SECRET_KEY` available to the backend | `rg STRIPE_SECRET_KEY hirelens-backend/.env* 2>/dev/null` shows a test key (`sk_test_…`). If running against live, confirm the live key is in the Railway / Vercel env. The smoke script refuses to run if the prefix doesn't match the selected mode. |
| Business info completed in the Stripe account | Dashboard → Settings → Business → Public business information. A brand name + support email are required before the portal can render the business name. The portal page will render a stub fallback if this is empty, but configuration-save may be gated. |

> If any prerequisite fails, record it under §7 and stop here.

---

## 2. Activation check (primary hypothesis)

This is the single most likely cause of E-033. Stripe requires the default Customer Portal configuration to be **reviewed and explicitly saved** at least once before API calls to `billing_portal.Session.create()` will succeed — the API does not auto-create a default on first call.

**Steps:**

1. In Stripe Dashboard, confirm you are in **Test mode** (toggle top-left shows orange "Test mode" banner).
2. Navigate to **Settings (gear icon top-right) → Billing → Customer portal**, or go directly to:
   `https://dashboard.stripe.com/test/settings/billing/portal`
3. Observe the page state. One of the following is true:

   | State | What you see | Meaning |
   |---|---|---|
   | **Never saved** | A page with form fields pre-filled with defaults but NO "Save" confirmation in the top banner. Page title may read "Activate your test link" or "Configure your Customer portal" with an unsaved-changes indicator. | ❌ Primary hypothesis CONFIRMED. Portal API calls will fail. |
   | **Saved once** | Page loads normally, shows "Save" button as disabled (nothing to save) and all sections filled in. No "unsaved changes" indicator. | ✅ Configuration exists. Move to §3. |
   | **Saved once, with changes pending** | Page shows your last-saved settings, plus "Save" is enabled (unsaved diff). | Partial — last save worked, but in-flight edits haven't shipped. Hit Save, then proceed. |

4. **If the state is "Never saved":** Do NOT change any settings yet. First, scroll to the bottom of the page and click **Save** to commit the defaults. Then return here and work through §3 to verify the saved defaults are correct.

5. **Record the state** you observed in §7, including a screenshot if practical.

---

## 3. Configuration check (secondary surfaces)

If §2 is ✅, verify these individual settings are either correct or deliberately not-yet-customized. Each has a known failure mode that could also surface as E-033's symptom.

**Navigation:** still on `dashboard.stripe.com/test/settings/billing/portal`.

| Setting | Where | Expected | What wrong looks like |
|---|---|---|---|
| **Default return URL** | Top of the portal page, in the "Business information" section → "Default redirect link" (also called "Customer landing page"). | **Blank** is acceptable — backend passes `return_url` explicitly on every session. If set, it should point at `https://<frontend>/profile` or equivalent. | A broken/localhost URL only affects the "← Back to …" button inside the portal; does not cause E-033 failure. Low priority. |
| **Allowed features: Cancel subscription** | "Customer permissions" section → "Cancel subscriptions" | ✅ Enabled. Cancellation mode = "At end of period" (matches spec #36 §15 "Cancellation timing is Stripe's default"). | Disabled → user can open portal but cannot cancel. Does not cause the "Couldn't open" error but produces a broken end-user experience. |
| **Allowed features: Update payment method** | "Customer permissions" → "Update payment methods" | ✅ Enabled. | Disabled is a product decision, not a bug. |
| **Allowed features: View / download invoices** | "Customer permissions" → "View invoice history" | ✅ Enabled. | — |
| **Allowed features: Switch plans / upgrade** | "Customer permissions" → "Switch plans" | Optional — currently we don't offer in-portal upgrades. Leaving disabled is fine. | — |
| **Subscription products listed** | "Products" section. Must include at least the Pro product (matches `stripe_pro_price_id` env var). | Pro product present, status = Active. | Missing product → "Switch plans" breaks but billing portal still opens. |
| **Business info: brand + support email** | Settings → Business → Public business information (a separate page). | Brand name + support email set. | Empty fields may block configuration save in newer Dashboard versions. If save was blocked in §2, this is why. |
| **Account activation status** | Top of Stripe Dashboard home — any yellow "Activate account" / "Complete your profile" banner. | No banner OR banner dismissed. | An unactivated account in live mode cannot create portal sessions; in test mode this banner is informational and doesn't block. |

---

## 4. Live mode configuration (repeat §2 + §3 for live)

Stripe test and live modes are **fully separate** — saving the test-mode configuration does NOT save the live-mode one. Before any production deploy:

1. Flip the Dashboard toggle to **Live mode**.
2. Navigate to `https://dashboard.stripe.com/settings/billing/portal` (note: no `/test/` in the path).
3. Repeat §2 activation check and §3 configuration check against live.
4. Record findings in §7 under the "Live mode" subsection.

> Per SESSION-STATE.md 2026-04-21 Stripe pivot: **live-mode configuration is the return-trigger gate** for unblocking Stripe-touching feature work. Don't skip §4.

---

## 5. Webhook check (tangential but worth verifying)

The Customer Portal itself does not emit webhook events (user actions in the portal produce standard `customer.subscription.updated` / `.deleted` / `invoice.paid` events on the Subscription surface, not portal-specific ones). Verify the webhook endpoint already handles these — this is a regression check for the E-033 fix's adjacent code paths, not a direct E-033 cause.

**Steps:**

1. Dashboard → Developers → Webhooks → find the endpoint pointing at `<backend-url>/api/v1/payments/webhook` (or `/api/payments/webhook` legacy).
2. Click the endpoint. Under "Events sent," confirm **all four** of these are enabled:
   - `checkout.session.completed` ✅ expected
   - `customer.subscription.updated` ✅ expected (not always currently handled — spec §42 added `user.downgraded_at` on `.deleted` only)
   - `customer.subscription.deleted` ✅ expected
   - `invoice.payment_failed` — handled at acknowledge level only (`payments.md:51`), but Stripe should still be delivering it.
3. Scroll to "Recent deliveries." Any red ❌ in the last 24h indicates webhook errors unrelated to E-033 — capture those but do not attempt to fix here.

---

## 6. After the checklist — run the smoke script

Once §2 is ✅ and §3 has no red flags:

```bash
cd hirelens-backend
source venv/bin/activate

# Check 1 only — confirm the API sees the Dashboard-side config
python scripts/smoke_billing_portal.py

# Check 1 + Check 2 — exercise full session creation against a test customer
# (get cus_xxx from dashboard.stripe.com/test/customers)
python scripts/smoke_billing_portal.py --customer cus_TEST_xxx

# Optional: also GET the returned portal URL
python scripts/smoke_billing_portal.py --customer cus_TEST_xxx --fetch-url
```

Expected output on green:
```
Mode: TEST (key prefix=sk_test_...)

--- CHECK 1: Customer Portal configuration exists ---
OK (Check 1): 1 configuration(s) found.
  - id=bpc_...  is_default=True  active=True

--- CHECK 2: Session creation round-trip ---
  customer=cus_TEST_xxx
  return_url=http://localhost:5199/profile
OK (Check 2): session created.
  id=bps_...
  url=https://billing.stripe.com/p/session/bps_...

PASS — all requested checks succeeded.
```

If any check fails, the script prints the specific Stripe error body. Record it verbatim in §7.

---

## 7. Result recording template

Fill this in as you go. Copy-paste the completed section into a BACKLOG E-033 update / investigation follow-up.

### Test mode — COMPLETED 2026-04-21

- [x] Prerequisites all satisfied (§1)
- [x] Activation state (§2): **Was "Never saved" — resolved by saving default config in Dashboard.**
- [x] Configuration defaults reviewed (§3) — no unexpected values flagged; defaults accepted.
- [x] Webhook endpoint events verified (§5)
- [x] Smoke script Check 1 result: **PASS** — "1 configuration(s) found", `id=bpc_1TOowxCl9xZqd5Sx208P98Nd`, `is_default=True`, `active=True`.
- [x] Smoke script Check 2 result: **SKIPPED** — no `--customer` arg passed. Deferred to E-039 because DB has 0 subscription rows with `stripe_customer_id` populated (verified: 2 rows, both `plan=free`, both `stripe_customer_id NULL`) — exercising Check 2 requires running the full upgrade flow end-to-end first.

### Live mode — PENDING

- [ ] Prerequisites all satisfied (§1)
- [ ] Activation state (§2): `[ ] Never saved  [ ] Saved once  [ ] Saved with pending changes`
- [ ] Configuration defaults reviewed (§3) — flag any unexpected values:
      `…fill in…`
- [ ] Webhook endpoint events verified (§5)
- [ ] Smoke script Check 1 result: `[ ] PASS  [ ] FAIL — paste output`
- [ ] Smoke script Check 2 result (if run): `[ ] PASS  [ ] FAIL — paste output  [ ] SKIPPED`

### Diagnostic conclusion (test mode, 2026-04-21)

- Hypothesis branch that matched (pick one from investigation report §6):
  - [x] **Branch A — Dashboard config** (primary hypothesis): zero code changes. Default Customer Portal configuration had never been saved in test mode. Saved via Dashboard on 2026-04-21; Check 1 PASS immediately after. Spec #36 amendment (documenting the Dashboard-activation prerequisite) recommended but deferred to the E-033 resolution slice.
  - [ ] Branch B — test methodology
  - [ ] Branch C — live/test key mismatch
  - [ ] Branch D — code bug in customer_id persistence
  - [ ] None of the above

- Next slice recommendation:
  **(a) Live-mode repeat.** Run §4 of this checklist in live mode (same Dashboard → Billing → Customer portal, live-mode URL) to save the default live config. Required before any production deploy.
  **(b) E-039.** Execute the deferred Check 2 work — run the full upgrade flow E2E (FE Upgrade → Stripe Checkout test mode → success webhook → DB write of `stripe_customer_id`) and then re-run the smoke script with `--customer cus_xxx` to confirm the full paid surface works end-to-end.
  **(c) Close E-033** only after both (a) and (b) are green. Test-mode Check 1 alone is not sufficient per Dhamo's close criteria.

---

## 8. What this checklist does NOT cover

- **Does NOT fix E-033.** Only diagnoses. BACKLOG row stays 🟦 P1 until a follow-up slice lands the actual resolution.
- **Does NOT touch production data.** The smoke script's `--customer` flag creates a Stripe portal session object (which Stripe auto-expires), but does not mutate the application database or user rows.
- **Does NOT audit the full Stripe integration.** That's E-035 (🟦) scope — a broader Mode-1 read-only audit of checkout / webhooks / portal / customer-id persistence / price routing.
- **Does NOT run the smoke script automatically.** Claude Code does not execute scripts that hit the live Stripe API; Dhamo runs both phases manually.

---

## 9. Footnotes

- Skill of record: `.agent/skills/stripe-best-practices/` (specifically `references/billing.md` → Stripe Customer Portal integration docs). Note: this skill is **untracked** in git as of HEAD `eb4259e` — flagged in the E-033 investigation report §8.
- Spec of record for the portal surface: `docs/specs/phase-5/36-subscription-cancellation.md`. Spec §152 flagged the `STRIPE_BILLING_PORTAL_CONFIGURATION_ID` env var as deliberately skipped — which means we rely on the Dashboard default, which means §2 of this checklist is load-bearing. If §2 fails, consider amending spec #36 to document the Dashboard-activation prerequisite (recommended follow-up regardless of outcome).
