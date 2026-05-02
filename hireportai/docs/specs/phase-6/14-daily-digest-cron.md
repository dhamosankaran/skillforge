# Phase 6 — Slice 6.14: Daily Pro Digest Cron (Railway-cron-driven)

## Status: 🔴 Drafted, §12 amendment pending — locks D-1..D-N from §14 OQ-A..OQ-N (mirrors slice 6.0 / 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 / 6.10 / 6.11 / 6.13.5 §12 amendment pattern at `e8eecdd` / `df58eaf` / `acba7ed` / `fb92396` / `0c21223` / `ab07168` / `be7d59a` / `d9bfcfc` / `4bf5220`); B-097 ✅ (this slice) + B-098 🔴 (forward-filed for impl).

| Field | Value |
|-------|-------|
| **Slice** | 6.14 (Track D — daily Pro digest cron consumer; LD G2 home; consumes 6.13's `email_log` dedup + `daily_digest_opt_out` opt-out column; closes B-078 cron architecture decision via LD G2 confirmation in §12 amendment slice) |
| **Phase** | 6 (Curriculum Platform) |
| **Mode** | Mode 4 spec-author → followed by §12 amendment → impl |
| **Filed at** | `86bc442` (spec-author commit) |
| **BACKLOG row (spec-author)** | **B-097** ✅ (filed + closed in this slice per single-slice spec-author lifecycle; mirrors slice 6.10 / 6.11 / 6.13.5 spec-author rows at `409762f` / `7d7c6e8` / `b93beb8`) |
| **BACKLOG row (impl, forward-filed)** | **B-098** 🔴 (filed at status 🔴 by this slice for the future implementation slice per R15(c)) |
| **B-078 status flip** | 🟦 → ✅ (cron architecture decision resolved — Dhamo locked LD G2 = Railway cron at filing; this spec depends on that lock and confirms it; the decision row resolves on this spec's commit since the work product is the locked decision now codified in §4.1 architecture) |
| **Depends on** | spec #13 (`docs/specs/phase-6/13-pro-digest-opt-out.md` — shipped at `d020f4d`/B-087): `email_log` table + `email_log_service.record_send`/`was_sent_today` + `EmailPreference.daily_digest_opt_out` ▪ Phase-2 spec #15 (`docs/specs/phase-2/15-daily-email.md` — shipped) `email_service.send_email` Resend wrapper ▪ existing `Subscription.plan IN ('pro', 'enterprise')` join precedent (`admin_analytics_service.py:147`) ▪ existing `card_progress` due-card selector precedent (`reminder_service.py:75-97`) ▪ existing `gamification_service.get_stats` for streak counts ▪ Phase-6 LD G2 (Railway cron — locked). |
| **Blocks** | None directly. Future "weekly digest" / "lifecycle email" surfaces will reuse the same cron + composer + dedup pattern this slice ships. |
| **Cross-refs** | scout audit `docs/audits/phase-6-scout.md` (slice 6.14 framing — Track D email cadence). SESSION-STATE Phase 6 LD **G2** ("Background jobs: RQ on Redis for ingestion (slice 6.10); Railway cron for daily Pro digest (slice 6.14)" — this slice activates the cron half). `analytics.md` (catalog discipline; this slice adds 3 BE event rows). `railway.toml` (single existing config file at `hirelens-backend/railway.toml`; this slice extends with a `[[cron]]` section). |

> **Slice numbering note:** slice number **6.14** matches on-disk slot 14 (`14-daily-digest-cron.md`). First slice in Phase 6 to reach 1:1 slice-number / slot-number alignment since 6.13.5 broke the prior 6.X ↔ slot-X parity.

---

## 1. Problem

Phase 6 LD G2 locks **Railway cron for the daily Pro digest** as the
delivery mechanism, and slice 6.13 (B-087, `d020f4d`) shipped the two
upstream artifacts the cron will consume: `email_log` dedup table +
`email_log_service.record_send`/`was_sent_today` + the
`EmailPreference.daily_digest_opt_out` column with a Pro-tier-gated FE
toggle. What does **not** yet exist on disk is the cron entry point
itself — no scheduled invocation, no digest-composition service, no
new Resend-template, and no `railway.toml [[cron]]` section.

Three concrete gaps motivate this slice:

- **No cron entry on disk.** `cat hirelens-backend/railway.toml` shows
  only `[build]` + `[deploy]` sections; there is no `[[cron]]` section,
  and no FastAPI route or Python script intended to be invoked by an
  external scheduler. `find hirelens-backend -name '*.py' | xargs grep
  -l 'cron\|schedule\|APScheduler'` returns zero matches. The Phase-2
  reminder service (`reminder_service.send_daily_reminders`, 155
  lines) exists but is **not currently scheduled** — it is a dormant
  function with no caller on disk. Slice 6.14 is the first scheduled
  job in the codebase.

- **No digest composition service.** Phase-2 `reminder_service`
  composes a single-line "you have N cards due" reminder using the
  `daily_reminder.html` template (one substitution: name, cards_due,
  streak, study_link). The Pro digest is richer — it must surface
  cards due, streak status, mission countdown when active, recent ATS
  scan deltas (slice 6.13.5b ships `tracker_application_scores` row
  on every analyze + rescan), and any quality-signal callouts that
  emerge from the user's recent activity. The composition layer is
  greenfield; it CANNOT be a thin extension of `reminder_service`
  because (a) the audience is different (Pro-only vs all opted-in
  reminder users), (b) the dedup contract is different (cron-based
  via `email_log` vs fire-and-log via PostHog only), and (c) the
  template content differs substantially.

- **No template, no PostHog catalog rows.** `app/templates/` contains
  one HTML file (`daily_reminder.html`); no `pro_digest.html` exists.
  `analytics.md` BE catalog has no `pro_digest_*` event rows. Both
  must land alongside the cron entry to keep the catalog consistent
  with the on-disk send pipeline.

This slice is the **terminal slice in Track D** for the Pro digest
pipeline — the cron consumer that turns slice 6.13's persistence layer
into actual recurring user-facing email. It is **infra-orthogonal to
slice 6.13.5** (which ships `card_quality_signals`); the digest may
reference quality signals in its body content (OQ-C territory) but
does not depend on 6.13.5 to ship.

### 1.1 Step 0 audit findings

Audit reads at HEAD `aa4e9e4`:

1. **`hirelens-backend/railway.toml` exists on disk, no `[[cron]]`
   section.** Current contents: `[build]` (Dockerfile) + `[deploy]`
   (`uvicorn` startCommand + `alembic upgrade head` releaseCommand +
   on-failure restart policy with 3 retries). Railway supports a
   `[[cron]]` block with `command` + `schedule` (cron expression)
   per Railway docs. The cron command runs in a separate process
   spawned from the same Docker image — it does NOT share memory
   with the running uvicorn server, so the cron entry needs its own
   `__main__` boot sequence (DB session factory + service call).

2. **`reminder_service.send_daily_reminders` is dormant.** Function
   exists at `app/services/reminder_service.py:122` but has zero
   on-disk callers (`grep -rn "send_daily_reminders" hirelens-backend/
   --include='*.py'` returns only the function definition + the test
   file). Phase-2 spec #15 implies an hourly cron tick, but the cron
   was never built. **Implication:** slice 6.14 is the FIRST cron in
   the codebase. The Pro digest is greenfield; reminder_service is
   left untouched (per spec #13 §13 fifth bullet "Generalize
   `email_log` to all email sends" — out of scope until follow-up).

3. **`email_service.send_email(to, subject, html_body)` returns
   `str | None`** (the Resend message id, or None when
   `RESEND_API_KEY` is unset for dev/CI). Returns None on missing
   key without raising — this lets dev/CI/test runs of the cron
   exercise the full path without making network calls. `record_send`
   accepts `resend_id: Optional[str]` so the None case is cleanly
   recorded as a "sent (locally)" row.

4. **`EmailPreference` schema on disk diverges from Phase-2 spec #15
   §`Data Model` table.** Spec #15 lists
   `frequency: String(20) DEFAULT 'daily'` + `preferred_hour:
   Integer DEFAULT 7 CHECK 0–23`. Disk reality
   (`app/models/email_preference.py:11`): only `daily_reminder` +
   `daily_digest_opt_out` + `timezone` + `unsubscribe_token` +
   `created_at` + `updated_at`. Neither `frequency` nor
   `preferred_hour` columns exist. Phase-2 spec is partially
   un-shipped on these fields. **Implication for 6.14:** there is no
   per-user "preferred hour" knob, so the cron either fires once-
   daily for everyone at a fixed UTC time (default proposal — see
   OQ-A) or fires hourly and uses the existing `timezone` column to
   match each user's local "send time" (option needing a chosen
   default hour). v1 author hint: once-daily UTC fire is simpler;
   per-user-tz can land later if engagement metrics warrant.
   **Drift carry-forward:** the spec-#15-vs-disk gap on
   `frequency`/`preferred_hour` is a Phase-2 spec drift, not a 6.14
   concern; flag in §13 for awareness only.

5. **Phase 5 spec #63 (E-043) shipped `tracker_application_scores`
   table + `ats_score_before` / `*_delta` payload on
   `rescan_completed`** — the digest composition layer can surface
   "your last ATS scan delta" without re-deriving from scratch. See
   §6.3 composition contract.

6. **Slice 6.13.5b (B-094b, `85860d5`) shipped per-lesson aggregate
   thumbs + `LessonWithQuizzesResponse.viewer_thumbs`** — not load-
   bearing for v1 digest content but available if the digest wants to
   surface "your top-rated lesson last week" copy. Out of scope v1
   per §13.

7. **`Subscription.plan IN ('pro', 'enterprise') AND
   Subscription.status == 'active'`** is the canonical paid-tier
   filter (precedent: `admin_analytics_service.py:147`,
   `email_prefs.py` PUT-handler from B-087). v1 cron uses the same
   join verbatim — no new tier-resolution helper needed.

8. **`gamification_service.get_stats(user_id)`** returns
   `current_streak` + `last_active_date` + `total_xp`. Used by
   `reminder_service._get_streak`; v1 digest reuses verbatim.

9. **No `app/scripts/` directory yet for cron entry points.** The
   slice 6.4.5 seed CLI lives at `app/scripts/seed_phase6.py`; same
   directory is the natural home for `app/scripts/send_pro_digest.py`
   per OQ-B. Alternative: a thin FastAPI endpoint
   `POST /api/v1/cron/pro-digest` invoked by Railway with a shared-
   secret header. Author hint: **CLI script** (option B / chosen
   default) — fewer moving parts, no auth surface to design, and
   the cron runs in a separate process anyway so the FastAPI
   advantage (existing DI / middleware / auth) doesn't apply.

10. **Resend retry policy already exists.** `email_service.send_email`
    already retries 3× with exponential backoff on 429 / 5xx; v1 cron
    does NOT add a second retry layer. Failures bubble up as
    `EmailSendError`; cron logs + skips the user + continues to the
    next.

### 1.2 Why this matters

- **Activates LD G2.** Railway cron has been a locked decision in
  SESSION-STATE since the Phase-6 scout audit; the on-disk activation
  has waited for slice 6.13's persistence layer + the 6.13.5 close
  trigger. With 6.13.5 shipped (B-094a + B-094b at `91be54f` +
  `85860d5`), the LD G2 re-evaluation triggered per
  `CODE-REALITY.md:848` and Dhamo confirmed Railway cron stays the
  call. This slice is the activation.

- **Closes B-078.** The cron architecture decision row is the work
  product; with the lock confirmed and the spec drafted, B-078 ✅
  resolves on this commit.

- **Establishes the cron pattern for future scheduled work.** Once a
  weekly-summary email / lifecycle email / "you missed N days" trigger
  is wanted, those slices reuse the same `[[cron]]` config + script
  entry + composer pattern.

- **Pro tier gets a richer email surface.** Phase-2 reminder is
  audience-flat ("you have N cards due"); the Pro digest is a
  product-differentiator email that reflects the user's recent
  curriculum + tracker + study activity in one place per day.

---

## 2. Goals

| # | Goal |
|---|------|
| **G-1** | **Add a `[[cron]]` section to `hirelens-backend/railway.toml`** invoking the digest entry-point on a daily schedule (cadence locked at §12 D-N from OQ-A). |
| **G-2** | **Ship a digest entry point** — `app/scripts/send_pro_digest.py` CLI per §1.1 finding #9 / OQ-B author hint. The script boots a fresh DB session factory (mirrors `app/scripts/seed_phase6.py` precedent), invokes the composer + sender, exits 0 / non-zero on success / fatal failure. |
| **G-3** | **Ship a digest composition service** — new `app/services/pro_digest_service.py` with `compose_digest(user, db) -> DigestPayload` (returning a Pydantic schema with all fields the template needs) and `send_pro_digest(db) -> SendSummary` (the orchestrator: select Pro candidates, dedup-skip, compose, send, record). |
| **G-4** | **Ship a Pro digest HTML template** — `app/templates/pro_digest.html` with substitution slots for the fields locked at §12. |
| **G-5** | **Consume slice 6.13's dedup contract verbatim.** `email_log_service.was_sent_today(user_id, 'pro_digest', today)` short-circuit BEFORE compose; `email_log_service.record_send(user_id, 'pro_digest', today, resend_id)` AFTER successful send. **`email_type='pro_digest'` is the canonical type string** for this surface. |
| **G-6** | **Pro-tier filter at selector layer.** Selector query joins `Subscription` and filters `plan IN ('pro', 'enterprise') AND status == 'active'` AND `EmailPreference.daily_digest_opt_out IS NOT TRUE` AND user has at least one engagement signal (cards due OR active mission OR recent scan in last 7 days — locked at §12 from OQ-G). |
| **G-7** | **3 PostHog events** — `pro_digest_sent` / `pro_digest_skipped_optout` / `pro_digest_skipped_dedup` (a fourth `pro_digest_failed` for Resend errors per OQ-H). All `internal: true` per Phase-6 admin-event convention (slice 6.10 D-13 precedent). |
| **G-8** | **Idempotent end-to-end.** Cron re-invocation on the same UTC day MUST be a no-op for users already sent that day (dedup short-circuits via §6.2 `was_sent_today` check); MUST NOT skip users not yet sent. |

---

## 3. Non-Goals (Out of Scope)

- **Weekly / monthly digest cadence.** v1 ships daily only.
  Future-cadence specs reuse the same composer + dedup contract.
- **Per-user `preferred_hour` send time.** Phase-2 spec #15 listed it
  but disk reality is no `preferred_hour` column. v1 cron fires
  once-daily at a fixed UTC time per OQ-A. Per-user-tz fire timing
  is OQ-E territory, default-deferred.
- **Generalize `email_log` to `reminder_service`.** Slice 6.13 §13
  defers this; slice 6.14 honors that defer — Phase-2 reminder loop
  remains dedup-free (and dormant on disk per §1.1 finding #2).
- **Token-unsubscribe handler / footer link.** Slice 6.13 §13 deferred
  this; slice 6.14 surfaces only a "manage preferences" link to
  `/profile` per spec #13's locked direction. Out of scope.
- **In-repo scheduler (APScheduler / RQ-on-Redis).** LD G2 locked at
  Railway cron; this slice does not re-litigate.
- **Backfill of historical Pro users with a "first digest" greeting.**
  Pro users get the digest starting on day 1 of cron; no special
  onboarding sequence. Future onboarding spec can layer this.
- **Admin observability of `email_log`.** Slice 6.13 §13 defers; slice
  6.14 honors the defer. The PostHog events provide enough day-1
  observability.
- **Failure-mode user-facing surface.** When Resend errors, the user
  sees nothing — no in-app banner, no retry queue. Cron logs +
  `pro_digest_failed` event + next-day-retry is the contract.
- **Per-section opt-outs within the digest.** v1 is all-or-nothing;
  finer granularity is future work.
- **Digest preview UI.** Pro users do not get an in-app "see what your
  next digest looks like" preview surface. Out of scope.
- **Multiple email_type values from this slice.** Only `'pro_digest'`
  is introduced. Reminder remains untyped via `email_log`.

---

## 4. Architecture

### 4.1 Component graph

```
┌──────────────────────────────────────────────┐
│  Railway cron (LD G2 — locked)               │  ← G-1
│   schedule: <OQ-A>                           │
│   command: python -m app.scripts.send_pro_digest │
└─────────────┬────────────────────────────────┘
              │ subprocess invocation
              ▼
┌──────────────────────────────────────────────┐
│  app/scripts/send_pro_digest.py (NEW)        │  ← G-2
│   - mirrors seed_phase6.py boot pattern      │
│   - asyncio.run(send_pro_digest(db_session)) │
│   - exits 0 on success / non-zero on fatal   │
└─────────────┬────────────────────────────────┘
              │ awaits
              ▼
┌──────────────────────────────────────────────┐
│  pro_digest_service.send_pro_digest (NEW)    │  ← G-3 orchestrator
│   1. select candidates (G-6 join)            │
│   2. for each candidate:                     │
│      a. was_sent_today guard → skip+event    │
│      b. compose_digest → DigestPayload       │
│      c. zero-content guard → skip+event      │  ← OQ-G
│      d. email_service.send_email             │
│      e. record_send + sent event             │
│   3. return SendSummary                      │
└─────────────┬────────────────────────────────┘
              │ reads/writes
              ▼
┌──────────────────────────────────────────────┐
│  email_log (slice 6.13 — `f1a2b3c4d5e6`)     │  ← G-5
│  email_preferences.daily_digest_opt_out      │
│  subscriptions (Pro/Enterprise, active)      │
│  card_progress (cards-due count)             │
│  gamification_stats (streak)                 │
│  missions (active mission countdown)         │
│  tracker_application_scores (recent ATS Δ)   │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│  email_service.send_email (Phase-2, shipped) │
│   Resend wrapper, 3× retry, returns msg_id   │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│  app/templates/pro_digest.html (NEW)         │  ← G-4
│   substitution slots per §6.4                │
└──────────────────────────────────────────────┘
```

### 4.2 Data flow (single cron tick)

1. Railway cron triggers per the configured schedule. Spawns a fresh
   container process from the deployed image, runs
   `python -m app.scripts.send_pro_digest`, exits.
2. Script boots a fresh `async_sessionmaker` (mirrors
   `seed_phase6.py:43-58` pattern) — does NOT share the FastAPI
   request-scoped session.
3. Script calls `await pro_digest_service.send_pro_digest(db)`.
4. Service runs the §6.1 selector → list of candidate users.
5. For each candidate (sequential per OQ-K author hint = simple
   loop, no concurrency v1):
   a. `was_sent_today(user_id, 'pro_digest', today_utc)` — if True,
      fire `pro_digest_skipped_dedup` event + continue.
   b. `compose_digest(user, db)` — see §6.3. Returns
      `DigestPayload | None`. Returning None means "no meaningful
      content" per OQ-G; fire `pro_digest_skipped_empty` (or merge
      with skipped_dedup per OQ — see §14) + continue.
   c. `email_service.send_email(to, subject, html_body)` — returns
      `str | None` (Resend message id or None for dev/CI).
   d. On success: `record_send(user_id, 'pro_digest', today_utc,
      resend_id)` + fire `pro_digest_sent` event.
   e. On `EmailSendError`: log warning + fire `pro_digest_failed`
      event with `error_class` + continue (NO `record_send` write so
      next cron tick retries — see §6.5 failure-mode).
6. Script returns `SendSummary { sent: int, skipped_optout: int,
   skipped_dedup: int, skipped_empty: int, failed: int }`. Logs
   summary at INFO; exits 0.

### 4.3 Failure modes + recovery

- **Cron tick missed (Railway downtime / config drift).** Per cron
  semantics, missed ticks do NOT replay automatically. v1 accepts
  this — a 24h gap means users miss one digest, recovery is the
  next-day tick. No catch-up sweep v1; future SLA can layer one.
- **DB connection failure mid-batch.** Script-level exception
  bubbles out of `send_pro_digest` — script exits non-zero,
  Railway logs the failure, partial sends are recorded in
  `email_log` (per-user `record_send` is committed before the next
  user is processed; see OQ-H). Next tick resumes via dedup skip
  on already-sent users.
- **Resend permanent error (`EmailSendError`).** Per-user — log,
  fire `pro_digest_failed`, skip, continue. NO `email_log` write so
  retry on next tick.
- **Resend transient error (429 / 5xx).** Already retried 3× inside
  `send_email` per §1.1 finding #10. After exhaustion → permanent
  error path above.
- **`compose_digest` raises.** Treat as permanent error — log, fire
  `pro_digest_failed { error_class: 'compose_error' }`, skip,
  continue. Don't write to `email_log` (next-tick retry).
- **`was_sent_today` returns True but no actual email arrived.**
  Off-disk failure (Resend accepted then dropped). v1 accepts; user
  sees no digest that day; next-day cron sends normally. SLA gap
  acceptable for v1.
- **Concurrent cron invocations** (e.g., manual re-trigger during a
  tick). UPSERT semantics on `email_log` UNIQUE constraint mean the
  second invocation's `record_send` raises `IntegrityError` (per
  `email_log_service.record_send` docstring); cron treats that as
  "already sent" + skips — see §6.5 idempotency contract.

### 4.4 Cross-cutting composition rules

- **R3 auth:** the cron entry is a CLI script — no HTTP route, no
  auth surface. The composer reads user data via DB session only;
  no `Depends(...)` chain. Pro-tier gating happens in the SQL
  selector, not in a middleware.
- **R5 Pydantic:** `DigestPayload` + `SendSummary` are Pydantic
  schemas (§5).
- **R6 Alembic:** **zero new migrations** this slice. All schema
  artifacts shipped at slice 6.13 (`f1a2b3c4d5e6`) and earlier. Flag
  if §6 work surfaces a missing column.
- **R8 PostHog:** 4 new BE events per G-7 (sent / skipped_optout /
  skipped_dedup / skipped_empty / failed — final naming locked at
  §12 from OQ-J).
- **R11 LLM router:** zero LLM calls. Digest composition is
  template-substitution only.
- **R12 design tokens:** **N/A** — HTML email template uses
  inline-style hex per Resend / email-client compatibility
  conventions; design tokens do not apply (browsers' email renderers
  do not support CSS variables / theme classes). Spec #15 + Phase-2
  template precedent: `daily_reminder.html` uses inline `#hex`.
  Slice 6.14 mirrors verbatim.
- **R13 integration tests:** none required this slice. The cron
  entry is a thin script + a service; both are unit-testable. No
  alembic round-trip surface (zero migrations).
- **R14 spec-first:** this spec is authored before impl. Confirmed.
- **R15(c) closure:** B-097 ✅ in this commit (spec-author single-
  slice file+close per B-091/B-093 precedent); B-098 🔴 forward-
  filed for impl; B-078 ✅ resolves on this commit (Dhamo-locked
  decision row — work product is the lock + spec).
- **R16 audit at impl Step 1:** the impl slice's Step 1 audit must
  cover (a) BE consumer-graph for new `pro_digest_service` —
  predicted leaf-surface (cron script + tests; no other consumer);
  (b) `railway.toml` cron-syntax compatibility (Railway-supported
  cron schedule expression; impl verifies via Railway docs at impl
  time per OQ-A lock); (c) NO FE consumer audit (zero FE this
  slice); (d) NO new App.tsx route.
- **R17 watermark:** B-097 + B-098 claimed by this slice (B-078
  flips status only — not a new claim). B-099 next-free numeric
  ID post-slice.

---

## 5. Schemas

### 5.1 `DigestPayload` (Pydantic — internal to the composer)

New file `app/schemas/pro_digest.py`.

```python
class DigestPayload(BaseModel):
    """Internal payload returned by ``pro_digest_service.compose_digest``.

    All fields are derived from existing DB tables (no new schema). The
    field set is locked at §12 from OQ-C/F; this docstring is the
    authoritative content contract.
    """
    user_id: str
    user_name: str
    user_email: str
    cards_due: int                          # from card_progress (slice 6.0+)
    streak: int                             # from gamification_stats
    mission_active: bool                    # from missions where status='active'
    mission_days_left: Optional[int]        # populated when mission_active
    last_scan_score: Optional[int]          # from tracker_application_scores
    last_scan_delta: Optional[int]          # signed delta vs prior, when ≥2 history rows
    # Locked at §12 amendment per OQ-C — additional fields may be locked
    # in (e.g., critique highlights, top-rated lesson last week) when the
    # impl slice runs.


class SendSummary(BaseModel):
    """Telemetry shape returned by ``send_pro_digest`` orchestrator.

    Logged at INFO for ops dashboards; not returned over HTTP.
    """
    sent: int
    skipped_optout: int
    skipped_dedup: int
    skipped_empty: int
    failed: int
    candidates_total: int
    duration_seconds: float
```

### 5.2 No new DB schemas

`email_log` (slice 6.13 / `f1a2b3c4d5e6`) + `email_preferences.daily_digest_opt_out`
(slice 6.13 / `f1a2b3c4d5e6`) + `tracker_application_scores` (slice 6.5
E-043 / `e043a1b2c3d4`) + `gamification_stats` (Phase 2) + `missions`
(Phase 2) + `card_progress` (Phase 0) + `subscriptions` (Phase 1) all
exist on disk. **Zero new migrations** this slice.

### 5.3 Existing API surfaces unchanged

No changes to FE-consumed schemas. No `LessonResponse` / `CardResponse`
extensions. The cron script is a closed-box CLI; nothing it produces is
returned over HTTP.

---

## 6. Backend

### 6.1 Selector query (`pro_digest_service.select_candidates`)

```python
async def select_candidates(db: AsyncSession) -> list[User]:
    """Pro/Enterprise active subscribers who haven't opted out.

    Per G-6 + OQ-G author hint = "any engagement signal" filter. The
    join shape mirrors ``admin_analytics_service`` Pro-counter precedent.
    """
    today = datetime.now(timezone.utc).date()  # OQ-E author hint = UTC
    stmt = (
        select(User)
        .join(Subscription, Subscription.user_id == User.id)
        .outerjoin(EmailPreference, EmailPreference.user_id == User.id)
        .where(Subscription.plan.in_(("pro", "enterprise")))
        .where(Subscription.status == "active")
        .where(
            or_(
                EmailPreference.daily_digest_opt_out.is_(False),
                EmailPreference.daily_digest_opt_out.is_(None),  # no row → opted-in
            )
        )
    )
    return list((await db.execute(stmt)).scalars().all())
```

Engagement-signal filter (G-6 second clause) — author hint applies
filter inside `compose_digest` rather than the selector, returning
`None` from `compose_digest` when the user has zero meaningful
content. This keeps the selector simple + lets the
`pro_digest_skipped_empty` telemetry capture the per-user reason.

### 6.2 Dedup short-circuit

Before composing, call `email_log_service.was_sent_today(db,
user.id, 'pro_digest', today)`. On True → fire
`pro_digest_skipped_dedup` event + skip the user. The check is
PER-USER, not batch-level — a single user's prior send does not
short-circuit the whole tick.

### 6.3 Composition (`compose_digest`)

```python
async def compose_digest(
    user: User, db: AsyncSession
) -> Optional[DigestPayload]:
    """Build the per-user payload from existing tables.

    Returns None when the user has zero meaningful content per OQ-G
    author hint = skip empty users. Field semantics:

    - cards_due: count of CardProgress rows where due_date <= now()
      AND user_id == user.id (mirrors reminder_service:75-97).
    - streak: GamificationStats.current_streak (default 0 if no row).
    - mission_active: True iff one Mission row exists with
      status='active' for the user. mission_days_left = (target_date
      - today).days when active; None otherwise.
    - last_scan_score / last_scan_delta: read most-recent
      tracker_application_scores row by user_id; populate when the
      latest 2 rows exist (mirrors HomeScoreDeltaWidget.history.length>=2
      gate from B-086b).

    Empty-content rule: return None when ALL of (cards_due == 0,
    !mission_active, last_scan_score is None). At least one signal
    must be present for the digest to fire.
    """
```

### 6.4 Template (`app/templates/pro_digest.html`)

New file. Substitution slots match `DigestPayload` field names with
double-brace `{{field}}` syntax (mirrors `daily_reminder.html`
precedent at `reminder_service._load_template` / `build_email_body`).
Sections shown conditionally via simple Python-side string replacement
(no Jinja2 — the existing pattern is `template.replace("{{x}}", str(x))`,
intentionally minimal). Conditional sections handled by composing two
template variants OR by leaving empty-string substitutions when the
field is None — author hint: empty-string substitution + CSS-driven
visibility (`display: none` on empty containers). Locked at §12 D-N.

### 6.5 Orchestrator + idempotency contract

```python
async def send_pro_digest(db: AsyncSession) -> SendSummary:
    """Fan-out + dedup + send + record. Cron-safe + idempotent.

    Idempotency contract:
    - Per-user `was_sent_today` guard prevents double-sends within
      the same UTC day.
    - `record_send` raises IntegrityError on UNIQUE collision (slice
      6.13 contract); orchestrator catches it as
      "concurrent-tick-already-sent" + treats as skip_dedup +
      continues (defensive against manual re-trigger during a tick).
    - Failures (no `record_send` write) leave the user re-eligible
      for the next tick.
    """
```

### 6.6 Script entry (`app/scripts/send_pro_digest.py`)

```python
"""CLI entry: python -m app.scripts.send_pro_digest

Mirrors app/scripts/seed_phase6.py boot pattern. Fresh DB session
factory — does NOT share the FastAPI request-scoped session. Returns
exit code 0 on success, non-zero on fatal failure.
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.services.pro_digest_service import send_pro_digest


async def _main() -> int:
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url, pool_pre_ping=True)
    async_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with async_factory() as db:
            summary = await send_pro_digest(db)
            print(summary.model_dump_json())
        return 0
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
```

### 6.7 Reuse of existing services

- **`email_service.send_email(to, subject, html_body)`** — Resend
  wrapper, 3× retry built-in.
- **`email_log_service.was_sent_today` / `record_send`** — slice 6.13
  dedup contract (verbatim).
- **`gamification_service.get_stats(user_id)`** — streak read.
- **`analytics_track`** — PostHog event emission.
- **`Subscription.plan IN (...)`** join — `admin_analytics_service`
  precedent.

### 6.8 Performance envelope

| Stage | Target | Notes |
|---|---|---|
| Selector query | <500ms | one query joining 3 tables; user count bounded by Pro subscribers (~hundreds at v1 scale). |
| Per-user `compose_digest` | <100ms | 3-5 SELECTs (CardProgress count, GamificationStats, Mission, tracker_application_scores). Sequential is fine at v1 scale. |
| Per-user Resend send | 200-500ms (network-bound) | 3× retry built-in. |
| Whole tick | <60s typical at <1000 Pro users | Linear in candidate count; chunked-async batching deferred to OQ-K future. |

---

## 7. Migrations

**Zero new migrations.** All schema artifacts shipped upstream
(slice 6.13 `f1a2b3c4d5e6`, slice 6.5 E-043 `e043a1b2c3d4`, Phase 2
+ Phase 0 baselines). If §6 impl surfaces a missing column, STOP and
file a sub-slice.

---

## 8. Frontend

**No frontend changes** this slice. The Pro digest opt-out toggle UI
shipped with slice 6.13 (`<EmailPreferences />` Pro-gated digest
toggle in `src/components/settings/EmailPreferences.tsx`).
"Manage preferences" link inside the digest HTML template points to
`<frontend>/profile?section=email-preferences` (anchor honored via
existing scroll-to behavior); no new route.

Out of scope: digest preview UI, per-section opt-outs, footer
unsubscribe-token route. See §13.

---

## 9. Analytics

### 9.1 New BE events

| Event | Source | Properties |
|-------|--------|-----------|
| `pro_digest_sent` | `app/services/pro_digest_service.send_pro_digest` (post-`record_send`) | `{user_id, plan: 'pro'\|'enterprise', cards_due, streak, has_mission: bool, has_recent_scan: bool, resend_id: str\|null, internal: true}` |
| `pro_digest_skipped_dedup` | same source (pre-compose dedup short-circuit) | `{user_id, internal: true}` — fires when `was_sent_today` returns True. |
| `pro_digest_skipped_empty` | same source (compose_digest returned None) | `{user_id, plan, internal: true}` — fires when no engagement signal present (OQ-G empty-content rule). |
| `pro_digest_failed` | same source (`EmailSendError` or compose error) | `{user_id, plan, error_class: 'send_error'\|'compose_error', internal: true}` — fires WITHOUT a `record_send` write (next tick re-attempts). |

`pro_digest_skipped_optout` is **NOT** a separate event — opt-out
users are excluded at the SELECTOR layer (§6.1) so they never reach
the compose loop. Counter visibility comes from the
`select_candidates` length vs `SendSummary.sent` delta, logged at
INFO. (Lock decision in §12 from OQ-J.)

### 9.2 Existing events untouched

`email_sent` (Phase-2 reminder event) is unchanged. The Pro digest
events form a parallel surface — analytics dashboards must distinguish
the two.

### 9.3 Catalog discipline

`.agent/skills/analytics.md` BE catalog gets 4 new rows under the
backend-events section. Lock-step update in the impl commit per
slice 6.10 / 6.11 / 6.13 / 6.13.5 precedent.

---

## 10. Test Plan

### 10.1 BE unit — `tests/services/test_pro_digest_service.py`

~10-14 tests:
- `select_candidates` filters by Pro plan + active status + opt-out
- `select_candidates` excludes free users
- `select_candidates` excludes opted-out Pro users
- `select_candidates` includes Pro users with no `EmailPreference` row (column NULL → opted-in via OUTER JOIN)
- `compose_digest` happy-path populates all fields when content present
- `compose_digest` returns None when zero engagement signal (OQ-G)
- `compose_digest` populates mission fields only when active
- `compose_digest` populates last_scan delta only when ≥2 history rows
- `send_pro_digest` skips dedup-hit users + fires `pro_digest_skipped_dedup`
- `send_pro_digest` skips empty users + fires `pro_digest_skipped_empty`
- `send_pro_digest` writes `email_log` row + fires `pro_digest_sent` on success
- `send_pro_digest` does NOT write `email_log` on `EmailSendError` + fires `pro_digest_failed`
- `send_pro_digest` is idempotent across two consecutive calls (second tick = all skip_dedup)

### 10.2 BE integration — `tests/scripts/test_send_pro_digest_script.py`

~3-5 tests via `subprocess.run(['python', '-m', 'app.scripts.send_pro_digest'])`:
- Script exit code 0 on clean run
- Script prints `SendSummary` JSON to stdout
- Script exits non-zero on DB connection failure (with mocked engine)
- (No `@pytest.mark.integration` marker required — these run as part of
  CI-canonical suite since they don't require alembic-roundtrip or live
  network — `RESEND_API_KEY` unset returns None per §1.1 #3.)

### 10.3 BE template — `tests/test_pro_digest_template.py`

~2-3 tests:
- All `{{field}}` slots in `pro_digest.html` are populated when
  `compose_digest` returns a complete payload
- Empty-section rendering when `mission_active=False` /
  `last_scan_score is None` (CSS-driven visibility, no broken HTML)

### 10.4 No FE tests

Zero FE surface this slice.

### 10.5 Test envelope (estimates, locked at impl)

- BE: **802 → ~817-830** (+15..+28 across new service + script + template).
- FE: **466** unchanged.
- Integration: **0 net new** (script tests run in CI-canonical suite).

---

## 11. Acceptance Criteria

- **AC-1** `hirelens-backend/railway.toml` contains a `[[cron]]`
  section with `command = "python -m app.scripts.send_pro_digest"`
  and a `schedule = "..."` cron expression locked at §12 from OQ-A.
- **AC-2** `python -m app.scripts.send_pro_digest` runs to
  completion locally, exits 0, prints valid `SendSummary` JSON.
- **AC-3** Selector excludes free users (subscription.plan != 'pro'
  / 'enterprise') from the candidate set.
- **AC-4** Selector excludes Pro users with
  `EmailPreference.daily_digest_opt_out=True`.
- **AC-5** Selector includes Pro users with no `EmailPreference` row
  (treats absent row as opted-in by default).
- **AC-6** Per-user `was_sent_today` short-circuit fires
  `pro_digest_skipped_dedup` + skips the user.
- **AC-7** Per-user `compose_digest` returning None fires
  `pro_digest_skipped_empty` + skips the user.
- **AC-8** Successful send writes one `email_log` row with
  `(user_id, 'pro_digest', today_utc, resend_id)` + fires
  `pro_digest_sent`.
- **AC-9** Resend `EmailSendError` does NOT write `email_log`,
  fires `pro_digest_failed { error_class: 'send_error' }`, continues
  to next user.
- **AC-10** `compose_digest` raising does NOT write `email_log`,
  fires `pro_digest_failed { error_class: 'compose_error' }`,
  continues.
- **AC-11** Re-running the script in the same UTC day is a no-op
  for already-sent users (all skip_dedup); not yet sent users get
  the digest on the second invocation.
- **AC-12** `compose_digest` mission fields populated only when an
  active mission exists.
- **AC-13** `compose_digest` last-scan-delta populated only when
  `tracker_application_scores` has ≥2 rows for the user.
- **AC-14** `pro_digest.html` template renders without broken HTML
  for all 8 combinations of `(mission_active × has_recent_scan ×
  cards_due > 0)` (one combo is the empty-content case → never
  rendered, so 7 valid combos).
- **AC-15** `app/templates/pro_digest.html` exists on disk; new file.
- **AC-16** `analytics.md` BE catalog has 4 new rows
  (`pro_digest_sent`/`_skipped_dedup`/`_skipped_empty`/`_failed`).
- **AC-17** `app/services/pro_digest_service.py` exists; module
  exports `send_pro_digest`, `compose_digest`, `select_candidates`.
- **AC-18** `app/scripts/send_pro_digest.py` exists; module exports
  `_main` async entry; `if __name__ == '__main__'` boots it.
- **AC-19** `app/schemas/pro_digest.py` exists with `DigestPayload`
  + `SendSummary` Pydantic schemas (§5.1).
- **AC-20** `SendSummary` returned by `send_pro_digest` accurately
  counts `sent + skipped_optout + skipped_dedup + skipped_empty +
  failed == candidates_total` (where `skipped_optout` = `0` since
  opt-out exclusion happens at selector layer, but the field is
  retained for telemetry consistency).

---

## 12. Decisions

> Locked at §12 amendment slice — empty placeholder per slice 6.0 /
> 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 / 6.10 / 6.11 / 6.13.5 amendment-
> slice precedent at `e8eecdd` / `df58eaf` / `acba7ed` / `fb92396` /
> `0c21223` / `ab07168` / `be7d59a` / `d9bfcfc` / `4bf5220`. The
> §12 amendment slice will lock D-1..D-N from §14 OQ-A..OQ-N per
> 1:1 author-hint dispositions.

(Locked decisions land at the §12 amendment slice; the impl slice
picks up post-amendment.)

---

## 13. Out of Scope (deferred to other slices)

- **Weekly / monthly digest cadence** — future spec.
- **Per-user `preferred_hour` send time** — Phase-2 spec #15 listed
  but never built; out of scope here. Future spec can layer.
- **Generalize `email_log` to `reminder_service.py`** — slice 6.13
  §13 deferred; honored.
- **Token-unsubscribe route + footer link** — slice 6.13 §13
  deferred; honored.
- **Digest preview UI in `<EmailPreferences />`** — future product
  surface.
- **Admin observability of `email_log`** — slice 6.13 §13 deferred.
- **Catch-up sweep for missed Railway-cron ticks** — v1 accepts the
  gap; future SLA spec can layer.
- **Concurrency / async batching of per-user sends** — v1 sequential;
  OQ-K author hint = simple loop. Future scaling spec.
- **Per-section opt-outs within the digest** — v1 all-or-nothing.
- **In-repo scheduler / RQ-on-Redis cron** — LD G2 locks Railway
  cron; not re-litigated.
- **Phase-2 spec #15 `frequency` / `preferred_hour` column gap** —
  carry-forward Phase-2 spec drift, NOT a 6.14 concern.

---

## 14. Open Questions

> All OQs RESOLVED at §12 amendment slice (TBD per slice 6.0 /
> 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 / 6.10 / 6.11 / 6.13.5 precedent at
> `e8eecdd` / `df58eaf` / `acba7ed` / `fb92396` / `0c21223` /
> `ab07168` / `be7d59a` / `d9bfcfc` / `4bf5220`). Each OQ carries an
> author hint to minimize amendment churn.

- **OQ-A — Cron schedule cadence + UTC time.** Daily once at fixed
  UTC, or hourly with per-user-tz match? Author hint: **daily
  once at 14:00 UTC** (≈10am ET / 7am PT / 7:30pm IST — hits all
  major time zones during waking hours). v1 doesn't have
  `preferred_hour` per §1.1 #4. Hourly + per-user-tz needs a
  `preferred_hour` column + the hourly cron extra cost.

- **OQ-B — Cron entry point: CLI script vs FastAPI endpoint.**
  Author hint: **CLI script** (`python -m app.scripts.send_pro_digest`)
  per §1.1 #9. CLI is simpler — no auth surface, no shared-secret
  header to design, no HTTP timeout concerns.

- **OQ-C — Digest body content fields.** Default lock: cards_due,
  streak, mission_days_left (when active), last_scan_score +
  last_scan_delta. Optional (§12 may lock IN or OUT): top-rated
  lesson last week (slice 6.13.5b thumbs aggregate), critique
  highlights for content the user studied (slice 6.13.5a critique
  signals), category mastery summary. **Author hint: ship v1 with
  the four core fields only**; richer content is OQ-C-followup
  amendable.

- **OQ-D — HTML template: new `pro_digest.html` vs extend
  `daily_reminder.html`.** Author hint: **new file**. The two
  emails have different audiences + content + visual emphasis;
  extending the existing template would force conditional bloat.

- **OQ-E — `today` definition: UTC vs per-user-tz.** Default:
  **UTC** (cron fires at fixed UTC; "today" is the UTC date at
  fire-time). Per-user-tz needs the cron to fire hourly + filter
  per-user-tz match — adds infra without proportional value at v1
  scale. EmailPreference.timezone exists but is unused for the
  cron in v1.

- **OQ-F — Subscription join filter.**
  `Subscription.plan IN ('pro', 'enterprise') AND
  Subscription.status == 'active'` per `admin_analytics_service`
  precedent. Should `status='trialing'` Pro users also get the
  digest? Default: **no** (active-only; trialing users are
  pre-paying and product can layer "digest preview" later).

- **OQ-G — Engagement-signal filter (compose-time empty rule).**
  Compose returns None when ALL of (cards_due == 0,
  !mission_active, last_scan_score is None). Author hint:
  **strict empty-rule** (zero noise to dormant Pro users). Open-
  ended question: include `recent_review_count_window > 0` as a
  fourth signal? Author hint: **no** (cards_due already proxies
  recent activity).

- **OQ-H — Failure-mode contract on Resend permanent errors.**
  Default: log + fire `pro_digest_failed` + skip + continue
  (next tick retries). Alternative: write a "failed" row to
  `email_log` to suppress retries. Author hint: **no failure-row
  write** — cron retry is the recovery; spec #13 §6.5 contract
  honored.

- **OQ-I — Backfill / first-time Pro users.** Pro users created
  before slice 6.14 ships get their first digest on the next cron
  tick after deploy (no special onboarding sequence). Author hint:
  **accept** — no backfill. Future onboarding spec can layer
  "Welcome to your first digest" copy.

- **OQ-J — Telemetry event split.** Default: 4 events (sent /
  skipped_dedup / skipped_empty / failed). NOT a separate
  `pro_digest_skipped_optout` (opt-out happens at selector layer,
  never reaches loop). Author hint: **4 events as default**;
  selector-layer counter exposed via INFO log.

- **OQ-K — Per-user concurrency.** Author hint: **sequential**
  (simple Python loop; v1 corpus < 1000 Pro users; whole tick
  <60s). Future scaling spec can introduce `asyncio.gather` chunks.

- **OQ-L — Observability + log level.** INFO log of `SendSummary`
  at end of run; WARNING on per-user failures. Default. No new
  structured-metrics surface this slice.

- **OQ-M — Catch-up sweep on missed cron ticks.** Author hint:
  **none** — v1 accepts missed-tick gaps; users get the next-day
  digest. Future SLA spec can layer a "catch up the last 24h"
  flag on the script.

- **OQ-N — Migration `down_revision` for any new alembic.** Not
  applicable — this slice ships **zero new migrations** (G-1 is
  config-only, no DB schema changes). If the §12 amendment slice
  surfaces a need for a column (e.g., extends `EmailPreference`
  with `preferred_hour`), the impl slice's Step 0 verifies head;
  spec #14 §7 says zero — flag at amendment time only.

---

## 15. Implementation Slice Forward-Link

Implementation row: **B-098** 🔴 (filed by this slice; closure
happens in the impl commit per R15(c)).

Forward dependencies before impl can start:

1. **§12 amendment slice** — locks D-1..D-N from §14 OQ-A..OQ-N
   per slice 6.0 / 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 / 6.10 / 6.11 /
   6.13.5 amendment pattern.
2. No BE primitive prerequisite — every existing data source is
   on disk:
   - `email_log` table + service (slice 6.13, `d020f4d`).
   - `email_preferences.daily_digest_opt_out` (slice 6.13).
   - `tracker_application_scores` (slice 6.5 E-043, `e043a1b2c3d4`).
   - `email_service.send_email` (Phase-2, shipped).
   - `gamification_service.get_stats` (Phase-2, shipped).
   - `subscriptions` (Phase-1, shipped).
   - `card_progress` due-card query precedent (Phase-0 +
     `reminder_service.py:75-97`).
   - `analytics_track` PostHog wrapper (Phase-1, shipped).

Impl slice expected scope:

- New file `app/services/pro_digest_service.py` (~150-220 lines).
- New file `app/scripts/send_pro_digest.py` (~30-50 lines).
- New file `app/schemas/pro_digest.py` (~30-50 lines).
- New file `app/templates/pro_digest.html` (~80-150 lines).
- Modify `hirelens-backend/railway.toml` (add `[[cron]]` section,
  ~5-8 lines).
- New BE/FE tests per §10 (~15-22 tests across 3 test files).
- `.agent/skills/analytics.md` updates: 4 new event rows.
- `curriculum.md` reference (cross-link to the new pro digest in
  §7 if applicable; impl decides).
- BACKLOG B-098 closure with impl SHA (R15(c)).
- SESSION-STATE Recently Completed entry.
- CODE-REALITY targeted regen at impl close (new service + script +
  schema + template + railway.toml `[[cron]]`).

Impl test envelope (estimates, locked at impl):
- BE: **802 → ~817-830** (+15..+28).
- FE: **466** unchanged.
- BE integration: **+0** (script tests run in CI-canonical).

R16 consumer-graph audit at impl Step 1:
- New `DigestPayload` / `SendSummary` types — predicted leaf-surface
  (composer + script + tests; no external consumer); no FE mirror.
- Zero new HTTP routes mounted; `App.tsx` untouched.
- Cron entry script + Railway config — no in-app consumer surface.

R11 + LLM-strategy compliance: zero LLM calls this slice.

R12 design-tokens compliance: **N/A** — HTML email template uses
inline-style hex per email-client compatibility (mirrors Phase-2
`daily_reminder.html`). Design tokens do not apply to email
templates.

R13 integration tests: zero alembic-roundtrip surface (zero new
migrations); script tests run in CI-canonical suite per §10.2.

R14 default — implements an authored spec (this slice IS the
authoring slice; impl pickup is the normal one).

R15(c) closure plan:
- This slice (spec-author): B-097 🔴 → ✅ + B-078 🟦 → ✅ in this
  commit; B-098 🔴 forward-filed for impl.
- §12 amendment slice (separate): no closure (B-098 stays 🔴).
- Impl slice: B-098 🔴 → ✅ at impl-merge.

R17 watermark: B-097 spec-author + B-098 forward-filed impl
claimed by this slice; B-099 next-free numeric ID post-slice.
B-078 status flips only — does not advance the watermark.

Out-of-scope at impl (cross-ref §13): weekly/monthly cadence,
preferred_hour column, generalize `email_log` to reminder, token-
unsubscribe handler, digest preview UI, admin observability,
catch-up sweep, async batching, per-section opt-outs.

Skill-author work potentially surfaced post-impl (NOT this slice's
scope): possibly a new `email-pipeline.md` skill covering the
unified send / dedup / template / cron pattern (Phase-2 reminder +
Phase-6 digest). Flag at impl Step 1 audit per SOP-4 if existing
`backend.md` + `analytics.md` cannot absorb the surface. SOP-4
close-loop applies (auto-file 🟦 BACKLOG row at flag #2 per
CLAUDE.md SOP-4 sharpening).

---

*Spec authored at `86bc442` against HEAD `aa4e9e4`. §12 will
amend at follow-up amendment slice locking D-1..D-N from §14
OQ-A..OQ-N per author-hint dispositions. All on-disk citations
verified at audit time per SOP-5; phantom citations zero. B-097 ✅
(this slice); B-078 ✅ (Dhamo-locked decision row resolved); B-098
🔴 (impl-pickup ready post-amendment).*
