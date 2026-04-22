# E2E Walkthrough — Path A — 2026-04-21

> Co-walk. Dhamo drives the browser, Claude Code scribes. N6 enforced: no fabricated observations.
> HEAD at walkthrough start: `6f6f61f`. Flow reference: `docs/status/E2E-READINESS-2026-04-21.md` §2.

---

## Step 0 — Pre-flight (Claude Code, autonomous)

**Result: ✅ all green** — booted for walkthrough.

| Check | Result | Detail |
|-------|--------|--------|
| Postgres 16 up | ✅ | `pg_isready` → ready |
| Redis 7 up | ✅ | `redis-cli ping` → PONG |
| Alembic current = head | ✅ | Both = `1176cc179bf0` |
| Migrations pending | ✅ none | — |
| `SELECT count(*) FROM cards` | ✅ 15 | > 0 as required |
| `SELECT count(*) FROM categories` | ✅ 14 | matches 2026-04-19 baseline |
| `SELECT count(*) FROM badges` | ✅ 9 | matches 2026-04-19 baseline |
| BE `.env` keys present | ✅ | All 18 required keys (readiness §3.1) found by name |
| FE `.env` keys present | ✅ | All 6 `VITE_*` live-import keys found by name (including the 4 missing from `.env.example`) |

**Env var KEY inventory** (values NOT inspected per sandbox policy — Dhamo must spot-check values):

- **BE present (23 keys):** `ACCESS_TOKEN_EXPIRE_MINUTES`, `ALLOWED_ORIGINS`, `DATABASE_URL`, `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `JWT_ALGORITHM`, `JWT_SECRET_KEY`, `LLM_FAST_MODEL`, `LLM_FAST_PROVIDER`, `LLM_REASONING_MODEL`, `LLM_REASONING_PROVIDER`, `POSTHOG_API_KEY`, `POSTHOG_HOST`, `REDIS_URL`, `REFRESH_TOKEN_EXPIRE_DAYS`, `RESEND_API_KEY`, `SENTRY_DSN`, `STRIPE_PRO_PRICE_ID`, `STRIPE_PRO_PRICE_ID_INR`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `TEST_DATABASE_URL`
- **BE absent (not blocking for Path A):** `GEMINI_MODEL` (falls back to `gemini-2.0-flash` per config default), `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` (not needed — router stays on Gemini), `STRIPE_ENTERPRISE_PRICE_ID` (Enterprise plan out of Path A scope), `RESEND_FROM_ADDRESS` (defaults to `reminders@skillforge.app`)
- **FE present (6 keys):** `VITE_API_BASE_URL`, `VITE_GOOGLE_CLIENT_ID`, `VITE_POSTHOG_HOST`, `VITE_POSTHOG_KEY`, `VITE_SENTRY_DSN`, `VITE_STRIPE_KEY`

**Value-presence spot-checks Dhamo should run before boot (cannot verify from here):**
1. `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — non-empty, matches a real Google Cloud OAuth client with `http://localhost:5199` as an authorized origin.
2. `STRIPE_PRO_PRICE_ID` — a **price** id (`price_…`), NOT a product id (`prod_…`). This was the P5-S26b-impl-BE smoke failure mode.
3. `STRIPE_SECRET_KEY` (`sk_test_…`) and `STRIPE_WEBHOOK_SECRET` (`whsec_…`) — belong to the same Stripe account as the price id above (the cross-account mismatch was the other P5-S26b smoke failure).
4. `GEMINI_API_KEY` — non-empty; required for scan + rewrite + cover letter + interview + experience paths.

---

## Step 1 — Boot (Claude Code, 2026-04-21)

**Status: ✅ up — with one Stripe warning.**

| Service | Port | Status | Probe |
|---------|------|--------|-------|
| Backend (FastAPI / uvicorn) | 8000 | ✅ | `GET /health` → 200 |
| Frontend (Vite) | 5199 | ✅ | `GET /` → 200; Vite ready in 187 ms |
| Stripe CLI (webhook listener) | — | ⚠️ | **NOT authenticated** (see W1 below) |

**Path correction found during boot (W2 below):** the script is at `../scripts/dev-start.sh` (git repo root), not `./scripts/dev-start.sh` (hireportai/). The readiness report §3.6 command `./scripts/dev-start.sh` fails from inside `hireportai/` with `no such file or directory`. This is the same D-004 drift flag (hireportai-as-repo-root ambiguity, tracked as B-013) — it bites users following the readiness instructions.

### Boot warnings captured

**W1 — Stripe CLI not authenticated.** `../logs/stripe.log` reports:
> `You have not configured API keys yet. If you have an API key: set STRIPE_API_KEY or pass --api-key <key>. To start a browser login (requires user action): run 'stripe login' and follow the printed instructions.`

The dev-start script doesn't pass `STRIPE_SECRET_KEY` (from `.env`) to `stripe listen` as `--api-key` or `STRIPE_API_KEY`. The CLI is running but can't forward webhooks. **Impact on Path A:** steps 11–13 (Stripe checkout → webhook → post-upgrade plan flip) will likely fail — the checkout itself works, but `customer.subscription.created` / `checkout.session.completed` webhook events won't reach `/api/v1/payments/webhook`, so the user's plan won't flip to Pro. Dhamo's options: (a) `stripe login` in a separate terminal before Step 11, (b) export `STRIPE_API_KEY=$STRIPE_SECRET_KEY` and restart Stripe CLI alone, or (c) skip Steps 11–13 and verify the BE webhook path separately later.

**W2 — Script-path mismatch vs readiness report.** `./scripts/dev-start.sh` (readiness §3.6 command) does not exist at that relative path; the correct invocation is `../scripts/dev-start.sh` or from repo root. Minor doc drift; candidate follow-up for B-013.

### Processes launched (outlive this session)
- Backend PID 47680 — `/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/logs/backend.log`
- Frontend PID 47685 — `/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/logs/frontend.log`
- Stripe CLI PID 47693 — `/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/logs/stripe.log`
- PID file: `/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/.dev-pids`

**Stop when done:** run `../scripts/dev-stop.sh` (or `./scripts/dev-stop.sh` from repo root).

### URLs
- Frontend: `http://localhost:5199`
- Backend: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

> **Dhamo — stack is up. Open http://localhost:5199 and start walking Step 2.**
>
> Before Step 11 (Stripe checkout), either (a) run `stripe login` in a separate terminal, or (b) tell me to skip 11–13 and mark them as blocked on W1.

---

## Step 2 — Flow walkthrough (Dhamo drives; Claude Code scribes)

All rows start as `pending`. Status flips only on direct Dhamo report or tool-verifiable evidence.

| # | Flow step | Status | What Dhamo reported | Severity | BACKLOG candidate? |
|---|-----------|--------|---------------------|----------|--------------------|
| 1 | Anon visits `/` → LandingPage renders, CTA → `/login` | pending | — | — | — |
| 2 | Click login → Google OAuth → first-login redirect | pending | — | — | — |
| 3 | PersonaPicker appears → select `interview_prepper` | pending | — | — | — |
| 4 | Redirect to `/home` → HomeDashboard with persona widgets | pending | — | — | — |
| 5 | Navigate to scan (`/prep/analyze` or FirstAction CTA) | pending | — | — | — |
| 6 | Upload resume + paste JD → submit → LLM roundtrip | pending | — | — | — |
| 7 | Results page — Job Fit above fold, KeywordChart colors, MissingSkillsPanel free-tier CTA | pending | — | — | — |
| 8 | Click a missing-skill CTA → routes to `/learn?category=<id>` "free preview" | pending | — | — | — |
| 9 | Start study session → submit 15 reviews | pending | — | — | — |
| 10 | 16th review → 402 → `PaywallModal` with `trigger="daily_review"` | pending | — | — | — |
| 11 | Click upgrade → Stripe checkout opens | pending | — | — | — |
| 12 | Checkout with card `4242…` → redirect to `/pricing` (E-032 expected) | pending | — | — | — |
| 13 | Return to study → wall bypassed → continue reviews | pending | — | — | — |
| 14 | Visit `/learn/mission` → Mission mode accessible | pending | — | — | — |

**Skipped by design:** E-033 (billing portal / "Manage Subscription") — known broken, back-burnered.

**Reporting format Dhamo — paste one step at a time or in batches:**

```
STEP <N>: <✅|⚠️|❌|skipped>
What I saw: <1-3 lines>
Console / network errors: <paste or "none">
Copy / UX notes: <optional>
Timing: <"fast" | "<N>s" | "none">
```

---

## Step 3 — Synthesis

> **Deferred until Dhamo says "done".** Groupings below are empty placeholders — populated at end.

### Bugs (functional broken)
_pending Dhamo report_

### UX friction (works but awkward)
_pending Dhamo report_

### Copy issues
_pending Dhamo report_

### Performance concerns
_pending Dhamo report_

### Missing telemetry (PostHog events not firing)
_pending Dhamo report_

---

## Step 4 — Suggested follow-up slices

> **Deferred until Step 3 lands.** Ranked top 5 by (impact × ease-to-fix); each gets a one-line slice description and a candidate BACKLOG ID (new or existing).

_pending Dhamo report_

---

## Findings Disposition

Running log of per-finding resolutions as slices land. One row per finding
touched by a slice; status captured at slice-close. Accumulates as the
remaining findings are worked.

| # | Finding (as reported by Dhamo) | Disposition | Slice / commit | Notes |
|---|---|---|---|---|
| #1 | HomeDashboard greets new users with "Welcome back" | ✅ FIXED | B-016 / `d835fb8` | New `users.home_first_visit_seen_at` + stamp endpoint; greeting fork. |
| #2 | "No active mission found" rendered as alert/error | 🟡 DROPPED — unverified | D-017 | Literal copy not reproducible on disk; prior verification doc says "by design." Re-verify on next walkthrough. |
| #3 | Cover letter heading leak after "Sincerely," (Pro+Confident tones) | 🟡 DROPPED — unverified | D-016 (related latent gap filed) | 9/9 live LLM samples clean in scout; needs reproduction evidence before BACKLOG row. |
| #6 | Interview date should be a date picker, not free text | ✅ VERIFIED-ALREADY-CORRECT — no action needed | spec #53 audit (`060c4c3`) | All three capture sites (`PersonaPicker.tsx:170`, `CountdownWidget.tsx`, `MissionSetup.tsx:120`) already use native HTML5 `<input type="date">`. Spec #53 codifies this as a non-regression invariant (LD-2); no separate enforcement slice needed. |
| #7 | Interview date + company should be optional; /home + Mission Mode degrade gracefully | ✅ FIXED | B-018 / spec #53 | Option β (no coercive setup gate). CountdownWidget Mode 1 reframed to link-only unlock CTA; new `MissionDateGate` replaces MissionSetup for no-date interview_preppers; PersonaPicker `return_to` URL-param with inline whitelist. 4 new PostHog events. |
| #16 | InterviewTargetWidget empty-state copy references non-existent Countdown company field | ✅ FIXED | B-017 / `d835fb8` | Three-case `emptyCopy()` split; PersonaPicker stays canonical company capture until E-017 ships a Profile editor. |

## Meta

| Field | Value |
|-------|-------|
| HEAD at walkthrough start | `6f6f61f` |
| CODE-REALITY sha | `a13c217` (fresh) |
| BE tests baseline | 312 non-integration |
| FE tests baseline | 182 passing |
| Active drift flags | D-014 (rewrite tuple) 🟡, D-015 (concurrent-session HEAD race) 🟡, D-016 (cover-letter response_schema) 🟡, D-017 (walkthrough #2 unverified) 🟡 |
| Known-broken skip | E-033 🟦 (billing portal) |
