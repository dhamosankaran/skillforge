# Phase 6 — Slice 6.13: Pro Daily Digest Opt-Out + `email_log` Dedup Table

## Status: 🔴 Drafted, §12 amendment pending — locks D-1..D-N from §14 OQ-A..OQ-N (mirrors slice 6.0 / 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 / 6.10 / 6.11 §12 amendment pattern at `e8eecdd` / `df58eaf` / `acba7ed` / `fb92396` / `0c21223` / `ab07168` / `be7d59a` / `d9bfcfc`); B-087 🔴 (filed by this slice).

| Field | Value |
|-------|-------|
| **Slice** | 6.13 (Track D — Pro digest opt-out persistence + `email_log` dedup schema; precondition for slice 6.14 cron) |
| **Phase** | 6 (Curriculum Platform) |
| **Mode** | Mode 4 spec-author → followed by §12 amendment → impl |
| **Filed at** | `<this-slice>` (spec-author commit) |
| **BACKLOG row** | **B-087** 🔴 (filed by this slice) |
| **Depends on** | Phase-2 `email_preferences` table (`alembic/versions/c9863b51075d_add_email_preferences_table.py`; shipped) ▪ Phase-2 `app/services/email_service.py` Resend wrapper (shipped) ▪ Phase-2 `app/services/reminder_service.py` daily-reminder selector (shipped — NOT touched by this slice) ▪ existing `Subscription.plan == "pro"` join precedent (`app/services/admin_analytics_service.py:149`) ▪ existing `usage.plan` FE gating precedent (`src/context/UsageContext.tsx:131` `canUsePro`; `src/components/home/widgets/MissionActiveWidget.tsx:40` `isPaid`) ▪ existing `Depends(get_current_user)` chain (`app/core/deps.py`). |
| **Blocks** | Slice 6.14 (cron daily Pro digest — consumes the opt-out flag from §5.1 and the `email_log` dedup contract from §5.2 / §6.2). B-078 (cron architecture decision: Railway cron vs APScheduler vs RQ-on-Redis) is orthogonal; locked at LD G2 = Railway cron, but does NOT bind 6.13's surface. |
| **Cross-refs** | Phase-2 spec #15 (`docs/specs/phase-2/15-daily-email.md`) §`email_send_log` (lines 160-171) — pre-authored design that was never built; **superseded by §5.2 of this spec** (see §15 forward-link + bundled one-line amendment to spec #15 in this commit). `analytics.md` (catalog discipline). SESSION-STATE Phase 6 LDs **G2** (Railway cron — slice 6.14 binding only) + **J2** (`card_quality_signals` — slice 6.13.5; **NOT bundled here**). Audit `docs/audits/phase-6-scout.md:1024-1026` (slice 6.13 framing). |

---

## 1. Problem

Phase 2 shipped a daily *reminder* email (one card-due nudge per user per
day) via `app/services/reminder_service.py` + `app/services/email_service.py`
+ the `email_preferences` table (`daily_reminder` Boolean + `timezone` +
dormant `unsubscribe_token`). Phase 6 LD G2 locks **Railway cron for the
daily Pro digest** (slice 6.14) — a richer Pro-tier-only digest that goes
beyond the Phase-2 single-line reminder. Slice 6.14 needs two pieces of
infrastructure on disk before it can ship safely:

1. **A persisted Pro-digest opt-out preference**, distinct from Phase-2's
   `daily_reminder` flag. A Pro user might want to keep the Phase-2 reminder
   ("you have N cards due") but opt out of the richer Pro digest, or vice
   versa. Conflating the two flags would force a binary choice and surprise
   existing reminder subscribers when slice 6.14 ships.
2. **An `email_log` dedup table.** The Phase-2 reminder loop has no on-disk
   dedup mechanism — re-running `send_daily_reminders()` on the same day
   re-sends. A cron job that fires hourly (per spec #15 line 155) MUST
   dedup at the persistence layer to be safe under retry, replay, or
   accidental double-trigger. Phase-2 spec #15 §`email_send_log` (lines
   160-171) pre-authored this exact design but the table was never built.

Three concrete gaps:

- **No digest opt-out column on `email_preferences`.** The slice-6.14 cron
  will want to skip Pro users who opted out; without a column, every
  per-cron-tick selector query has to reconstruct the opt-out semantics
  from scratch (and there's no UI surface to set it).
- **No `email_log` dedup table on disk.** `grep -rn "email_log" hirelens-backend/app`
  returns zero hits per the scout audit (`docs/audits/phase-6-scout.md:475-476`).
  Slice 6.14's cron will need `(user_id, email_type, sent_date)` uniqueness
  to short-circuit re-sends.
- **Phase-2 spec #15 §`email_send_log` is dormant.** The design exists on
  paper but no migration, no model, no service. Slice 6.13 is the natural
  home to resurrect that design with refinements (renamed to `email_log`
  per audit doc; refined column types per Phase-6 precedent shapes); spec
  #15 gets a one-line forward-link amendment in the SAME commit so future
  readers of spec #15 §`email_send_log` are pointed here.

This slice is **upstream of slice 6.14** (cron consumer). It is **infra-
orthogonal to B-078's cron architecture decision** — opt-out persistence +
`email_log` schema + service contract are the same regardless of whether
slice 6.14 picks Railway cron, APScheduler, or RQ-on-Redis. Slice 6.13
ships first, slice 6.14 ships second.

---

## 2. Goals

- **G1.** Add a persisted Pro-digest opt-out preference on
  `email_preferences` via additive Alembic migration. Column semantics
  (opt-out vs opt-in; default value) locked at §12 amendment per OQ-A.
- **G2.** Create the canonical `email_log` table per the refined design in
  §5.2 below — supersedes Phase-2 spec #15 §`email_send_log`.
- **G3.** Extend the existing `<EmailPreferences />` card in
  `src/pages/Profile.tsx:403` with a digest toggle, conditionally rendered
  for Pro / Enterprise users only (FE Pro-tier gating per
  `MissionActiveWidget:40` precedent).
- **G4.** Backend Pro-tier gating on the PUT route — reject opt-out writes
  from free users (semantics: 403 vs silent-ignore — OQ-B).
- **G5.** Ship `email_log_service.py` with at least `record_send()` and
  `was_sent_today()` (or equivalent dedup-query) for slice 6.14 cron to
  consume. **Slice 6.13 ships the service + tests but does NOT wire it
  into `reminder_service.py`** — generalizing dedup to the Phase-2 reminder
  is OQ-C territory (author hint: digest-only).
- **G6.** Forward-link to slice 6.14 cron consumer contract in §15 without
  binding cron architecture (B-078).
- **G7.** Bundled Phase-2 spec #15 §`email_send_log` supersession amendment
  — one-line forward-link header BEFORE the section, pointing to §5.2 of
  this spec. Section body preserved verbatim as historical artifact.

---

## 3. Non-Goals (Out of Scope)

- **Token-unsubscribe handler.** The Phase-2 `unsubscribe_token` column
  exists but no `/unsubscribe?token=...` route consumes it. Wiring that
  handler (+ email-template footer link) is deferred to a follow-up
  slice (filed as a §13 forward-pointer). Slice 6.13 digest emails (when
  slice 6.14 ships them) will surface only a "manage preferences" link
  pointing to `/profile` (settings anchor) — no token-unsubscribe in v1.
- **Cron job + email composition + send pipeline.** That's slice 6.14
  territory and is gated separately on B-078 (cron architecture).
- **Generalize `email_log` to all email sends.** Wiring `record_send()`
  into `reminder_service.py` so the Phase-2 reminder also dedups is OQ-C
  territory; author hint = digest-only for v1; future slice can broaden.
- **`card_quality_signals` table.** That's slice 6.13.5 / LD J2. Do NOT
  bundle — table name similarity (`email_log` ≠ `card_quality_signals`)
  is coincidental.
- **Migration to a third-party email-prefs platform** (e.g., Customer.io,
  Loops). Stays on Resend per Phase-2 architecture; `email_log` is local.
- **Backfill** of `email_log` rows for the historical Phase-2 reminder
  send window — `email_log` is forward-only; historical sends are not
  represented (consistent with `quiz_review_events` greenfield approach
  per slice 6.0).
- **Per-email-type opt-out granularity beyond the digest flag.** v1 ships
  the digest opt-out only; further per-type flags (e.g., per-streak-loss
  email) defer to future slices.
- **Admin observability** of `email_log` (per-type send counts, bounce
  rates, etc.). Out of scope; covered if/when slice 6.14 ships and an
  admin dashboard slice picks it up.

---

## 4. Architecture

### 4.1 Component graph

```
┌─────────────────────────────────────────┐
│  FE: Profile.tsx                        │
│   └─ <EmailPreferences /> (extended)    │  ← G3 / §8
│         daily_reminder toggle           │
│         daily_digest_opt_out toggle     │  (Pro-gated)
│         timezone picker                 │
└─────────────┬───────────────────────────┘
              │ PUT /api/v1/email-preferences
              ▼
┌─────────────────────────────────────────┐
│  BE: email_prefs.py route (extended)    │  ← G4 / §6.3
│   └─ Pro-tier gate on opt-out write     │
└─────────────┬───────────────────────────┘
              │ writes
              ▼
┌─────────────────────────────────────────┐
│  email_preferences (extended)           │  ← G1 / §5.1
│   + daily_digest_opt_out: Boolean       │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  email_log (new)                        │  ← G2 / §5.2
└─────────────────────────────────────────┘
              ▲
              │ record_send() / was_sent_today()
              │ (called by slice 6.14 cron — NOT this slice)
┌─────────────┴───────────────────────────┐
│  email_log_service.py (new)             │  ← G5 / §6.2
└─────────────────────────────────────────┘
              ▲
              │ §15 forward-link
┌─────────────┴───────────────────────────┐
│  Slice 6.14 cron (FUTURE)               │
│   - selects opted-in Pro users          │
│   - was_sent_today() guard              │
│   - email_service.send_email()          │
│   - record_send() on success            │
└─────────────────────────────────────────┘
```

### 4.2 Data flow (in-slice)

1. User loads `/profile` → existing `<EmailPreferences />` component
   mounts, calls `fetchEmailPreferences()`. Response now includes
   `daily_digest_opt_out: bool` (§5.3 schema extension).
2. If `usage.plan === 'pro' || usage.plan === 'enterprise'`, the new
   toggle is rendered alongside `daily_reminder`. Free users see only
   the existing toggle (FE-side hide; BE-side reject).
3. User toggles → `updateEmailPreferences({ daily_digest_opt_out })` →
   PUT route validates plan via `Subscription.plan == "pro"` join, writes
   the column, fires PostHog event (per OQ-D — extend existing or new).
4. Reload returns the new value.

### 4.3 Data flow (forward, slice 6.14)

Slice 6.14 cron is described here for forward-link clarity only; it does
NOT ship in this slice.

1. Cron fires (Railway cron per LD G2; cadence locked at slice 6.14).
2. Selector query: `User × Subscription × EmailPreference` join,
   filtered to `Subscription.plan IN ('pro', 'enterprise')` AND
   `Subscription.status == 'active'` AND
   `EmailPreference.daily_digest_opt_out IS NOT TRUE` (semantics per
   OQ-A column shape).
3. For each candidate: `was_sent_today(user_id, email_type='pro_digest')`
   short-circuit; skip if true.
4. Compose digest body (slice 6.14 §6).
5. `email_service.send_email(...)` → on success, `record_send(user_id,
   email_type='pro_digest', resend_id=msg_id)`.
6. Failures: log + skip (no `email_log` write on failure, so retry loop
   re-attempts on next cron tick).

---

## 5. Schemas

### 5.1 `email_preferences` extension

Additive column:

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `daily_digest_opt_out` | `Boolean` | NO | `False` (server-side) | OQ-A locks semantics + default. Author hint: opt-out form (False = receive digest by default; True = user has explicitly opted out). |

**Rationale (OQ-A author hint):** "opt-out" semantics with `DEFAULT False`
is consistent with `daily_reminder`'s existing default-True pattern (Pro
users opted in by default) without requiring a backfill migration step;
existing rows get the column as `False` via server default.

**Existing columns unchanged:** `user_id` (PK, FK→users.id CASCADE),
`daily_reminder`, `timezone`, `unsubscribe_token`, `created_at`,
`updated_at`.

### 5.2 `email_log` table (CANONICAL — supersedes Phase-2 spec #15 §`email_send_log`)

```python
class EmailLog(Base, UUIDPrimaryKeyMixin):
    """One row per email sent by Phase-6 digest pipeline (slice 6.14
    consumer). Purpose: idempotent dedup. Forward-only — no backfill
    of Phase-2 reminder sends.

    Supersedes Phase-2 spec #15 §email_send_log (never built).
    """
    __tablename__ = "email_log"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    email_type: Mapped[str] = mapped_column(String(30), nullable=False)
    sent_date: Mapped[date] = mapped_column(Date, nullable=False)
    resend_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "email_type", "sent_date",
            name="uq_email_log_user_type_date",
        ),
        Index("ix_email_log_user_sent_date", "user_id", "sent_date"),
    )
```

**Column rationale (vs Phase-2 spec #15 §`email_send_log`):**

| Column | Phase-2 §15 spec | Slice 6.13 (this spec) | Why differ? |
|---|---|---|---|
| `id` | `String(36)` PK via `UUIDPrimaryKeyMixin` | Same | OK — preserves Phase-6 model precedent (`quiz_review_events`, `lesson_view_events`). |
| `user_id` | `String(36)` FK NOT NULL | Same; ON DELETE **CASCADE** explicit | Phase-6 `quiz_review_events` uses `SET NULL` per slice 6.0 D-1 (anonymize but preserve aggregates). For `email_log` the row is dedup-only — orphan rows have no aggregate value, so CASCADE on user delete is correct. OQ-E confirms. |
| `email_type` | `String(30)` NOT NULL | Same | Initial values: `"pro_digest"` (slice 6.14). Future: `"daily_reminder"` if OQ-C generalizes. |
| `sent_date` | `Date` NOT NULL | Same | One row per (user, type, day). Date in UTC; per-user-tz interpretation is selector-side (slice 6.14). |
| `resend_id` | `String(100)` Nullable | Same | NULLABLE — `email_service.send_email()` returns `None` when `RESEND_API_KEY` empty (dev/CI no-op); `record_send` may also be invoked for in-flight rows that don't yet have a Resend ID. OQ-F locks the contract. |
| `created_at` | `DateTime(tz)` via `TimestampMixin` | Standalone column with `server_default=func.now()` | `TimestampMixin` adds `updated_at` too, which is meaningless for an append-only log. Drop the mixin and inline `created_at` only. |
| **Unique constraint** | `(user_id, email_type, sent_date)` | Same | Identical to Phase-2 spec. |
| **Index** | (Phase-2 spec listed none) | `(user_id, sent_date)` composite | Slice 6.14 selector lookups query by (user_id, sent_date) for "did I send today" — composite index avoids a full table scan as the table grows. Mirrors `ix_quiz_review_events_user_reviewed_at` shape. |

### 5.3 Pydantic schema extensions (BE)

```python
# app/api/v1/routes/email_prefs.py (extended)

class EmailPreferenceResponse(BaseModel):
    user_id: str
    daily_reminder: bool
    daily_digest_opt_out: bool   # NEW
    timezone: str
    model_config = ConfigDict(from_attributes=True)


class EmailPreferenceUpdate(BaseModel):
    daily_reminder: Optional[bool] = None
    daily_digest_opt_out: Optional[bool] = None   # NEW
    timezone: Optional[str] = None
```

### 5.4 `EmailLog` Pydantic surface

`email_log` is **internal-only in v1** — no public API surface, no
response model, no admin route. Slice 6.14 may surface admin reads later;
not in this slice's scope. The model + service is the entire surface.

### 5.5 FE TypeScript extensions

```typescript
// src/types/index.ts

export interface EmailPreference {
  user_id: string
  daily_reminder: boolean
  daily_digest_opt_out: boolean   // NEW
  timezone: string
}

export interface EmailPreferenceUpdate {
  daily_reminder?: boolean
  daily_digest_opt_out?: boolean   // NEW
  timezone?: string
}
```

---

## 6. Backend

### 6.1 Model changes

- **Modified** `app/models/email_preference.py`:
  - Add `daily_digest_opt_out: Mapped[bool]` column with
    `nullable=False`, `default=False`, `server_default=text("false")`.
- **New** `app/models/email_log.py`:
  - `EmailLog(Base, UUIDPrimaryKeyMixin)` per §5.2.
  - Imports: `datetime`, `date`, SQLAlchemy `Boolean / Date / DateTime /
    ForeignKey / Index / String / UniqueConstraint / func`,
    `Mapped`, `mapped_column`, `app.models.base.Base`,
    `app.models.base.UUIDPrimaryKeyMixin`.
- **Modified** `app/models/__init__.py`:
  - Add `from app.models.email_log import EmailLog  # noqa: F401`.

### 6.2 Service layer

**New** `app/services/email_log_service.py`. Two public functions:

```python
async def record_send(
    db: AsyncSession,
    user_id: str,
    email_type: str,
    resend_id: Optional[str] = None,
) -> EmailLog:
    """Insert an email_log row. INSERT-only — no UPDATE / DELETE. Caller
    is responsible for choosing sent_date (typically date.today() in UTC,
    or per-user-tz interpretation at the selector layer)."""
    ...

async def was_sent_today(
    db: AsyncSession,
    user_id: str,
    email_type: str,
    today: date,
) -> bool:
    """Return True iff an email_log row exists for (user_id, email_type,
    today). Cron callers use this as a short-circuit before send."""
    ...
```

`sent_date` is supplied by caller (NOT inferred inside the service) — this
is intentional so cron logic can pass per-user-tz "today" without the
service having to know about timezones. OQ-G locks the signature exactly.

**NOT modified** in this slice:

- `app/services/reminder_service.py` — generalizing dedup to Phase-2
  reminder is OQ-C territory (author hint: digest-only).
- `app/services/email_service.py` — Resend wrapper unchanged.

### 6.3 Route changes

**Modified** `app/api/v1/routes/email_prefs.py`:

- **GET `/email-preferences`**: response shape extended with
  `daily_digest_opt_out`. The `_get_or_create` helper auto-populates the
  field via the model default for new rows. No auth changes.
- **PUT `/email-preferences`**: request body extended with
  `daily_digest_opt_out: Optional[bool]`. **New BE-side Pro-tier guard:**
  if the request body sets `daily_digest_opt_out` AND the caller's
  `Subscription.plan NOT IN ('pro', 'enterprise')`, the route returns
  HTTP 403 with body `{"detail": "Daily digest opt-out requires a Pro
  subscription"}` (semantics per OQ-B). The `daily_reminder` and
  `timezone` fields remain accessible to all authenticated users.
- **Admin bypass:** OQ-H — should `is_admin` users bypass the Pro gate?
  Author hint: yes, mirror `UsageContext:131 canUsePro` precedent which
  includes admins.

PostHog event (per OQ-D):
- **Author hint = extend existing** `email_preferences_saved` with the
  new field name in the payload (e.g., `{daily_digest_opt_out: bool}`).
  Avoids analytics-catalog churn. Alternative (new event
  `digest_opt_out_changed`) considered but rejected for slice scope.

### 6.4 Pro-tier gating join

Use the existing `Subscription` model precedent from
`app/services/admin_analytics_service.py:149`:

```python
# Inside PUT handler, before applying daily_digest_opt_out
if body.daily_digest_opt_out is not None:
    sub = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    sub_row = sub.scalar_one_or_none()
    is_paid = sub_row is not None and sub_row.plan in ("pro", "enterprise")
    if not (is_paid or user.is_admin):
        raise HTTPException(
            status_code=403,
            detail="Daily digest opt-out requires a Pro subscription",
        )
```

**Note:** the route already has `user: User = Depends(get_current_user)`
via `get_current_user`; no new auth dependency. The Subscription lookup
is a single async query with no caching (acceptable for a low-traffic
preferences write path).

### 6.5 Archived / published filters

N/A — this slice does not touch curriculum visibility, lesson lifecycle,
or the persona-narrowing read surface. Slice 6.5 (read-time invariants)
and slice 6.6 (deck-lesson ranker) remain authoritative for those.

---

## 7. Migrations

One new Alembic migration:

- **Filename:** `alembic/versions/<rev>_phase6_slice613_digest_opt_out_and_email_log.py`
  (revision ID minted at impl-slice generation time per existing convention).
- **`down_revision`:** `e043a1b2c3d4` (current alembic head per
  `grep "^revision" alembic/versions/e043a1b2c3d4_*.py` at this slice).
  Impl slice MUST re-confirm head at code-time — concurrent slices
  between 6.13 spec-author and 6.13 impl could shift head.
- **Upgrade:**
  1. `op.add_column("email_preferences", sa.Column("daily_digest_opt_out",
     sa.Boolean(), nullable=False, server_default=sa.text("false")))`
     — additive; existing rows get `False` per server default.
  2. `op.create_table("email_log", ...)` per §5.2.
  3. `op.create_unique_constraint("uq_email_log_user_type_date",
     "email_log", ["user_id", "email_type", "sent_date"])`.
  4. `op.create_index("ix_email_log_user_sent_date", "email_log",
     ["user_id", "sent_date"])`.
- **Downgrade:**
  1. `op.drop_index("ix_email_log_user_sent_date")`.
  2. `op.drop_table("email_log")` (drops table + UNIQUE constraint).
  3. `op.drop_column("email_preferences", "daily_digest_opt_out")`.
- **Reversible:** yes. Roundtrip (`upgrade head → downgrade -1 →
  upgrade head`) must be clean — AC-12.

**D-028 carry-forward note:** SESSION-STATE.md drift D-028 tracks 4
pre-existing alembic-roundtrip integration failures (orthogonal to this
slice's surface). The new migration's roundtrip test MUST NOT add to that
set. If the new test fails roundtrip, halt impl and triage; do not append
to D-028.

**Server default on existing rows:** `server_default=sa.text("false")`
means existing `email_preferences` rows get `daily_digest_opt_out=False`
without a backfill UPDATE. This matches LD G2-orthogonal default-False
("not opted out") for all existing Pro users, which is correct: existing
Pro users are NOT auto-opted-out of a digest that does not yet exist
(slice 6.14 ships the digest itself). When 6.14 lands, those users will
receive the digest unless they explicitly toggle opt-out.

---

## 8. Frontend

### 8.1 `<EmailPreferences />` component extension

**Modified** `src/components/settings/EmailPreferences.tsx`:

- New state field: `prefs.daily_digest_opt_out: boolean`.
- New toggle UI rendered conditionally:
  ```tsx
  const isPaid = usage.plan === 'pro' || usage.plan === 'enterprise'
  // Free users: existing daily_reminder toggle only.
  // Pro/Enterprise: digest opt-out toggle below daily_reminder.
  {isPaid && (
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm text-text-primary">Pro Daily Digest</p>
        <p className="text-[11px] text-text-muted">
          Skip the morning digest of your career-prep activity
        </p>
      </div>
      <button
        onClick={handleDigestToggle}
        ...
      />
    </div>
  )}
  ```
  Toggle copy locked at OQ-I; above is author-hint draft.
- New handler `handleDigestToggle` mirrors existing `handleToggle`:
  calls `updateEmailPreferences({ daily_digest_opt_out: newVal })`,
  fires PostHog event, flashes "Saved" indicator.
- Loading / error / saving states reuse existing component pattern;
  no new state machine.

### 8.2 Hook for `usage.plan`

`<EmailPreferences />` already lives inside `Profile.tsx` which uses
`useUsage()`. Pass `plan` down as a prop OR consume `useUsage()` directly
in the component (OQ-J locks shape). Author hint: consume `useUsage()`
directly in the component to keep `Profile.tsx` mount-line minimal.

### 8.3 Types

Per §5.5 — `EmailPreference` and `EmailPreferenceUpdate` extended with
the new field. Append-only, no breaking change to existing consumers
(`Profile.tsx`, `services/api.ts`).

### 8.4 API helpers

`src/services/api.ts:479-487` requires NO changes — `fetchEmailPreferences`
and `updateEmailPreferences` are typed against the extended interfaces;
the additional field flows transparently through the existing PUT body.

### 8.5 PostHog FE firing

Existing `email_preferences_saved` capture in `EmailPreferences.tsx:52,67`
is extended with `{daily_digest_opt_out: bool}` when that field is the
saved field. Per author hint at §6.3: NO new event name.

### 8.6 No new pages / routes / context

Slice 6.13 mounts no new page, adds no new route in `App.tsx`, adds no
new context provider. The entire FE delta is two-three lines in
`<EmailPreferences />` + 2 type fields + (optional) `useUsage` hook
addition.

---

## 9. Analytics

### 9.1 PostHog event catalog

**Per OQ-D author hint = extend, not add.** Existing event:

| Event | Source | Properties |
|---|---|---|
| `email_preferences_saved` | `components/settings/EmailPreferences.tsx` | `{daily_reminder?: boolean, daily_digest_opt_out?: boolean, timezone?: string}` |

The catalog row in `.agent/skills/analytics.md` gets a one-line property
extension. No new event.

### 9.2 BE-side firing

**None.** Consistent with slice 6.11 D-11 author hint
("admin-internal events fire BE-side; user-facing prefs fire FE-side").
The PUT route's existing `track(user.id, "email_unsubscribed", ...)` and
`track(user.id, "email_resubscribed", ...)` events for the
`daily_reminder` field are NOT extended to the digest field — toggling
the digest opt-out is FE-fired only.

### 9.3 Skill catalog update

`.agent/skills/analytics.md` row for `email_preferences_saved` gets an
inline property-list update in the impl commit. No new event row.

---

## 10. Test Plan

### 10.1 BE unit tests

- **`tests/test_email_preference_model.py`** (new or extended):
  - `daily_digest_opt_out` column present on insert, default-False.
  - Existing rows queried post-migration carry the default.
- **`tests/services/test_email_log_service.py`** (new):
  - `record_send` inserts a row with the supplied (user_id, email_type,
    sent_date, resend_id).
  - `record_send` raises `IntegrityError` on duplicate (user_id,
    email_type, sent_date) — uniqueness enforced by DB constraint.
  - `was_sent_today` returns `False` when no row exists.
  - `was_sent_today` returns `True` when a matching row exists.
  - `was_sent_today` returns `False` for a different `email_type` on
    the same date (multi-type isolation).
  - `record_send` handles `resend_id=None` cleanly (in-flight / no-op-API
    rows).
- **`tests/test_email_prefs_route.py`** (extended):
  - Pro user PUT with `daily_digest_opt_out=True` → 200, value persists.
  - Free user PUT with `daily_digest_opt_out=True` → 403 with explicit
    message.
  - Free user PUT with only `daily_reminder=False` → 200 (free user
    path unchanged).
  - Admin (free plan, `is_admin=True`) PUT with `daily_digest_opt_out`
    → 200 (admin bypass per OQ-H).
  - GET `/email-preferences` returns `daily_digest_opt_out` in payload
    for both free and Pro users.

### 10.2 BE integration test

- **`tests/test_phase6_slice613_migration.py`** (new,
  `@pytest.mark.integration`-gated per R13):
  - `alembic upgrade head → downgrade -1 → upgrade head` clean.
  - `email_preferences.daily_digest_opt_out` column present
    post-upgrade.
  - `email_log` table present post-upgrade with expected unique
    constraint + index.

### 10.3 FE component tests

- **`tests/components/settings/EmailPreferences.test.tsx`** (extended):
  - Renders digest toggle when `usage.plan === 'pro'`.
  - Renders digest toggle when `usage.plan === 'enterprise'`.
  - Hides digest toggle when `usage.plan === 'free'`.
  - Toggling the digest fires `email_preferences_saved` exactly once
    with `{daily_digest_opt_out: true}` payload.
  - Failed save shows the error state (mirror existing failure path).

### 10.4 Test envelope estimate

- **BE: +12..+22 passing tests** (4-6 model + 6-10 service + 4-6 route).
- **BE integration: +1 test** (`@pytest.mark.integration` gated).
- **FE: +6..+10 passing tests** (5-7 component cases + 1-2 type guard
  smoke).
- **AC count target: 14-18 ACs** (one per goal × verification path).

### 10.5 Tests NOT written this slice

- `reminder_service.py` integration with `email_log_service` — out of
  scope per OQ-C (digest-only).
- Slice 6.14 cron job E2E — slice 6.14 territory.
- Token-unsubscribe handler — out of scope per §3.
- `email_log` admin observability — out of scope per §3.

---

## 11. Acceptance Criteria

- **AC-1.** PUT `/api/v1/email-preferences` with
  `{daily_digest_opt_out: true}` from a Pro user (Subscription.plan='pro',
  status='active') returns 200 and the column on disk reads `True`.
- **AC-2.** PUT `/api/v1/email-preferences` with
  `{daily_digest_opt_out: true}` from a free user (no Subscription row,
  or plan='free') returns 403 with detail
  `"Daily digest opt-out requires a Pro subscription"`. The column on
  disk remains unchanged (default `False`).
- **AC-3.** PUT `/api/v1/email-preferences` with `{daily_reminder: false}`
  from a free user returns 200 (existing reminder path unchanged for
  free users).
- **AC-4.** PUT `/api/v1/email-preferences` with
  `{daily_digest_opt_out: true}` from an admin user (is_admin=True) on a
  free plan returns 200 (admin bypass per OQ-H).
- **AC-5.** GET `/api/v1/email-preferences` returns
  `daily_digest_opt_out` in the response payload for users on every plan.
- **AC-6.** `email_log_service.record_send(user_id, email_type='pro_digest',
  sent_date=today, resend_id='resend_abc')` inserts one row in `email_log`.
- **AC-7.** A second `record_send` call with identical
  `(user_id, email_type, sent_date)` raises `IntegrityError`.
- **AC-8.** `email_log_service.was_sent_today(user_id,
  email_type='pro_digest', today=today)` returns `True` after AC-6,
  `False` for a different `email_type` on the same day.
- **AC-9.** `<EmailPreferences />` renders the digest toggle when
  `usage.plan === 'pro' || usage.plan === 'enterprise'`; hides it when
  `usage.plan === 'free'`.
- **AC-10.** Toggling the FE digest toggle fires
  `email_preferences_saved` with payload `{daily_digest_opt_out: bool}`
  exactly once per user-initiated toggle.
- **AC-11.** Toggling the digest toggle persists the new value
  (PUT round-trip; UI reflects the new value after refresh).
- **AC-12.** Alembic round-trip clean: `upgrade head → downgrade -1 →
  upgrade head` produces no schema diff. Test gated with
  `@pytest.mark.integration`.
- **AC-13.** Existing `email_preferences` rows post-migration carry
  `daily_digest_opt_out=False` (server-default applied; no backfill
  needed).
- **AC-14.** Phase-2 spec #15 §`email_send_log` carries a one-line
  amendment header pointing to this spec's §5.2 (verified via
  `grep "Superseded by" docs/specs/phase-2/15-daily-email.md`).
- **AC-15.** `unsubscribe_token` column on `email_preferences` remains
  unwritten by this slice's code paths (regression guard against
  accidental token-unsubscribe-handler scope creep per §3).
- **AC-16.** No changes to `app/services/reminder_service.py` (regression
  guard against OQ-C scope creep).

---

## 12. Locked decisions

> Empty placeholder. Locks land in a separate §12 amendment-author
> micro-slice once §14 OQs are reviewed by Dhamo. Mirrors slice 6.10 /
> 6.11 §12 amendment pattern at `be7d59a` / `d9bfcfc`.

---

## 13. Out of Scope (deferred / follow-up)

- **Token-unsubscribe handler.** A follow-up slice owns
  `GET /unsubscribe?token=...` route + `unsubscribe_token` consumption
  + email-template footer link wiring. Not yet filed as a BACKLOG row
  — file at impl-time of slice 6.13 if Dhamo approves the follow-up
  scope. Trigger condition: slice 6.14 (cron daily Pro digest) ships
  and the digest email needs a footer link.
- **Generalize `email_log` to all email sends.** OQ-C author hint =
  digest-only in v1. Future slice migrates `reminder_service.py` to
  call `record_send(email_type='daily_reminder', ...)` for symmetry +
  observability. Not blocked on slice 6.14.
- **`card_quality_signals` table.** Slice 6.13.5 / LD J2 territory —
  finer-grained per-(lesson, quiz_item, signal_source, dimension) layer
  for content-quality observability. NOT bundled here despite slice-
  number proximity.
- **Cron job + email composition + send pipeline.** Slice 6.14 territory.
  B-078 (cron architecture decision: Railway cron locked at LD G2;
  APScheduler vs RQ-on-Redis alternatives still surfaceable at 6.14
  spec-author time) is independent of this slice.
- **Admin observability of `email_log`.** No admin dashboard rows for
  per-type send counts, bounce rates, etc. in v1.
- **Backfill of historical Phase-2 reminder sends.** Not represented in
  `email_log` (forward-only).
- **Per-email-type opt-out granularity beyond the digest flag.** v1
  ships only `daily_digest_opt_out`; further per-type flags defer.
- **Migration to a third-party email-prefs platform.** Stays on Resend +
  local `email_preferences` + `email_log`.

---

## 14. Open Questions (12 OQs surfaced — §12 amendment slice locks)

> Each OQ carries an **author hint** to minimize §12 amendment churn.
> Mirrors slice 6.0 / 6.4.5 / 6.5 / 6.6 / 6.7 / 6.8 / 6.10 / 6.11
> precedent.

- **OQ-A — `daily_digest_opt_out` column semantics + default.** Two
  options: (a) `daily_digest_opt_out: Boolean DEFAULT False` (opt-out =
  True means do not send; default-receive); (b) `pro_digest_opt_in:
  Boolean DEFAULT True` (opt-in = True means send; default-receive but
  via opposite verb). Both achieve "Pro users receive by default". **Author
  hint: (a) opt-out form** for consistency with conventional email-prefs
  vocabulary ("opt out of marketing emails") and to match the
  `email_unsubscribed` PostHog event semantics already on disk.
- **OQ-B — Free-user digest-opt-out write semantics.** Two options:
  (a) HTTP 403 with explicit detail; (b) silent ignore (200 with
  unchanged column). **Author hint: (a) 403** for clarity — silent
  ignore creates surprise when a free user sets the flag, upgrades to
  Pro, and finds the value reverted to default rather than what they
  set. 403 forces the upgrade-then-set ordering.
- **OQ-C — `email_log` dedup scope: digest-only or generalize?** Two
  options: (a) digest-only — slice 6.13 ships `email_log` + service but
  only slice 6.14 cron writes; reminder_service.py untouched.
  (b) generalize — slice 6.13 also migrates `reminder_service.py` to
  call `record_send(email_type='daily_reminder', ...)`. **Author hint:
  (a) digest-only** to keep slice scope tight; future slice can
  generalize. Decision drives §6 scope + AC-16.
- **OQ-D — PostHog event: extend or add?** Two options: (a) extend
  existing `email_preferences_saved` payload with the new field;
  (b) add new event `digest_opt_out_changed`. **Author hint: (a) extend**
  to avoid analytics-catalog churn for a low-frequency preferences write.
- **OQ-E — `email_log.user_id` ON DELETE behavior: CASCADE or SET NULL?**
  `quiz_review_events` uses `SET NULL` per slice 6.0 D-1 to preserve
  aggregates. `email_log` is dedup-only — orphan rows have no aggregate
  value, so CASCADE is correct. **Author hint: CASCADE.**
- **OQ-F — `email_log.resend_id` nullability.** `email_service.send_email`
  returns `None` when `RESEND_API_KEY` empty. Two options: (a) NULLABLE
  (allow None); (b) NOT NULL (require non-empty). **Author hint:
  (a) NULLABLE** — preserves dev/CI no-op semantics; cron callers can
  still call `record_send` with `resend_id=None` for diagnostic completeness.
- **OQ-G — `email_log_service.record_send` signature: caller-supplied
  `sent_date` or service-computed `date.today()`?** **Author hint:
  caller-supplied** — service is timezone-agnostic; callers (slice
  6.14 cron) can pass per-user-tz "today" without service awareness.
- **OQ-H — Admin bypass on Pro-tier guard.** Two options: (a) admin
  bypasses (per `UsageContext:131 canUsePro` precedent which includes
  admins); (b) strict Pro/Enterprise only. **Author hint: (a) admin
  bypass** for consistency with the FE precedent.
- **OQ-I — FE toggle copy.** Author-hint draft: label "Pro Daily Digest";
  helper "Skip the morning digest of your career-prep activity". Lock
  exact wording (or reframe to opt-in semantics if OQ-A flips) at
  amendment time.
- **OQ-J — FE `usage` consumption shape: prop drill from `Profile.tsx`
  or call `useUsage()` inside `<EmailPreferences />`?** **Author hint:
  call `useUsage()` directly** — keeps `Profile.tsx` mount line minimal
  and `EmailPreferences` self-contained.
- **OQ-K — FE event-firing cadence: fire on every toggle including
  rapid double-toggles, or debounce?** **Author hint: fire on every
  successful save** (mirror existing `daily_reminder` pattern at
  EmailPreferences.tsx:52). Rapid double-toggles produce two events;
  matches user-perceived action count.
- **OQ-L — Pydantic field naming: `daily_digest_opt_out` (DB-aligned)
  vs `proDigestOptOut` (FE-camelCase)?** Pydantic + FastAPI default to
  snake_case wire format; FE TypeScript types should match. **Author
  hint: snake_case `daily_digest_opt_out`** — matches existing
  `daily_reminder` convention end-to-end.

---

## 15. Implementation Slice Forward-Link

- **Files BACKLOG row:** **B-087** 🔴 (filed at this commit per R15(c);
  closed at impl-slice merge).
- **Predicted impl envelope:**
  - BE +12..+22 passing tests + 1 integration test (alembic
    roundtrip).
  - FE +6..+10 passing tests.
  - 1 alembic migration (additive column + new table + unique
    constraint + composite index).
  - 1 new model (`email_log.py`), 1 new service
    (`email_log_service.py`), 1 modified model
    (`email_preference.py`), 1 modified route
    (`email_prefs.py`), 1 modified component
    (`EmailPreferences.tsx`), 2 modified type interfaces
    (`types/index.ts`), 1 catalog row update
    (`.agent/skills/analytics.md`).
- **R16 audit prediction (impl-slice Step 1):** leaf surface — no
  external consumers of new types beyond this slice's own files.
  - BE consumers of `EmailLog`: only `email_log_service.py` (this
    slice) + slice 6.14 cron (future).
  - FE consumers of new field: only `<EmailPreferences />` (this
    slice).
  - No legacy callsites to migrate.
- **Skill-gap prediction:** none expected. Skills already loaded across
  Phase 6 cover surface (`backend.md` for service-layer + route-mounting
  conventions; `analytics.md` for the catalog update; `design-system.md`
  for the toggle styling). If impl surfaces a skill gap, follow CLAUDE.md
  SOP-4 close-loop discipline.

### 15.1 Slice 6.14 cron consumer contract (forward-link)

When slice 6.14 (cron daily Pro digest, gated on B-078 Railway cron
architecture per LD G2) ships, it consumes:

- **Opt-out flag (§5.1):** `email_preferences.daily_digest_opt_out`.
  Selector: `WHERE daily_digest_opt_out IS NOT TRUE` (semantics per
  OQ-A author hint = opt-out form, default False).
- **Dedup contract (§5.2 / §6.2):** `email_log_service.was_sent_today`
  short-circuit before send; `email_log_service.record_send` after
  successful Resend dispatch. Email type literal: `"pro_digest"`.
- **Pro-tier gating (§6.3 / §6.4):** the cron's selector query MUST
  itself filter `Subscription.plan IN ('pro', 'enterprise')` AND
  `Subscription.status == 'active'` — the BE PUT-route Pro guard does
  not run from a cron context. The cron is responsible for tier
  filtering.

Cron architecture (B-078 / LD G2 = Railway cron) is **NOT bound by this
spec.** Slice 6.14 may revise to APScheduler or RQ-on-Redis at its own
spec-author time without affecting any artifact this slice ships. The
opt-out flag + dedup table + service contract are infra-orthogonal.

### 15.2 Spec #15 supersession cross-ref

Phase-2 spec #15 (`docs/specs/phase-2/15-daily-email.md`) §`email_send_log`
(lines 160-171 at this slice's draft time) was pre-authored as the dedup
table design but never built — no migration, no model, no service. Slice
6.13 supersedes that design with the canonical `email_log` shape in §5.2
of this spec.

**Spec #15 receives a one-line amendment in the SAME commit as this
spec-author commit:** a `>` blockquote header BEFORE the
§`email_send_log` section pointing forward to
`docs/specs/phase-6/13-pro-digest-opt-out.md` §5.2 (slice 6.13,
`<this-slice>`). The §`email_send_log` body is preserved verbatim as
historical artifact; future readers are pointed here for the canonical
design.

### 15.3 Token-unsubscribe handler follow-up (filed pointer, not a row)

The Phase-2 `email_preferences.unsubscribe_token` column exists but no
handler consumes it. A follow-up slice owns:

- `GET /unsubscribe?token=...` public route (no auth — token IS the
  auth).
- Token validation against `unsubscribe_token` column.
- Side effect: set both `daily_reminder=False` AND
  `daily_digest_opt_out=True` (or whatever the OQ-A locked semantics
  imply for "opted out") for the matching user.
- Email template footer link injection (template at
  `app/templates/daily_reminder.html`).
- PostHog event: `email_unsubscribed{method:"one_click"}` (compare to
  existing `method:"preferences"` at `email_prefs.py:101`).

This follow-up slice is NOT filed as a BACKLOG row at this slice. File
at impl-time of slice 6.13 if Dhamo approves; trigger condition is slice
6.14 ship + the digest email needing a footer link.
