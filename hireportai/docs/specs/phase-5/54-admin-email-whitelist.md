# SPEC: Admin Email Whitelist (env-driven) + AdminGate

## Status: Draft

Supersedes the "admin-access-hardening" follow-up candidate listed in
`docs/specs/phase-5/38-admin-analytics.md:424-443` — specifically the
admin-promotion UI / source-of-truth concern. MFA, admin session IP
pinning, short admin-TTL tokens, and admin-scoped rate limit profiles
remain open follow-ups under a narrower hardening umbrella and are
explicitly out of scope here (LD-1).

---

## Problem

Admin access today is granted by a single manual DB `UPDATE` on
`users.role`:

- `users.role` is a free-form `VARCHAR(20)` with server default `'user'`
  (`app/models/user.py:17-19`) — no enum, no CHECK constraint, no
  external source of truth.
- `require_admin` (`app/core/deps.py:91-101`) does a literal string match
  (`if user.role != "admin": 403`). Nothing cross-checks against env,
  config, or any list of approved operators.
- `google_auth` (`app/api/v1/routes/auth.py:141-164`) does zero role
  reconciliation on login. Role is written once and persists forever.
- No frontend `AdminGate` exists. `/admin` is wrapped in
  `ProtectedRoute → PersonaGate` (see `App.tsx:99`), with the admin
  check buried inside `AdminPanel`. Non-admins hitting `/admin` today
  load the lazy chunk, then discover the in-component guard fires —
  surfaced as CODE-REALITY Section 12 Q4 and Section 11 flag #4.

**Consequences:**
1. A legitimate admin who leaves the org retains admin access
   indefinitely unless someone remembers to run another `UPDATE`.
2. Compromising any database write-path lets an attacker self-promote
   with no reconciliation step catching it.
3. Admin status has no declarative, version-controllable home — it
   lives only in production DB rows.
4. Frontend/backend drift: backend enforces `require_admin`; frontend
   relies on a component-level check that non-admins would only hit
   after downloading admin code.

## Solution

`ADMIN_EMAILS` environment variable (comma-separated, case-insensitive,
whitespace-trimmed) is the **single source of truth** for who is
an admin. On every Google OAuth login, reconcile DB `role` against
the list:

```
desired_role = 'admin' if user.email.lower() in admin_emails_set else 'user'
if user.role != desired_role:
    promote or demote, audit, emit event
```

Frontend gains `<AdminGate>` that mirrors `require_admin`. `/admin` is
wrapped so non-admins see a 403 view instead of downloading
`AdminPanel.tsx`.

### Behavior

- **Source of truth.** `ADMIN_EMAILS` env var parsed into a
  `frozenset[str]` of lowercased emails at config-load time
  (cached via `@lru_cache` on `get_settings()`). Empty or missing →
  empty frozenset → **fail-closed** (no user is admin).
- **Whitespace + case.** Leading/trailing spaces stripped per email;
  `.lower()` applied. `'Foo@Bar.com'` in env matches `'foo@bar.com'`
  on login.
- **Reconciliation trigger.** Runs in `google_auth` after
  `get_or_create_user` and before issuing the JWT. Does **not** run
  on every request (LD-3 — keeps hot path clean; `require_admin`
  stays a simple `user.role == 'admin'` DB check).
- **Audit row.** Every promotion OR demotion writes an
  `AdminAuditLog` entry with `route='/api/v1/auth/google'`,
  `method='POST'`,
  `query_params={"action": "promoted"|"demoted", "prior_role": ...,
   "new_role": ...}`, `ip_address=<client ip>`. `admin_id` is the
  affected user's id. Reuses the E-018a table and follows the same
  best-effort-flush / no-raise discipline (`_write_admin_audit_log`
  pattern).
- **PostHog event.** `admin_role_reconciled` with
  `{email, prior_role, new_role, action: 'promoted'|'demoted'|'unchanged'}`
  fires on every login — including `unchanged` so we have a running
  heartbeat of whitelist evaluation for dashboards. Unchanged emits
  no audit row.
- **Frontend `AdminGate`.** Reads `user` from `AuthContext`; renders
  children iff `user?.role === 'admin'`. Non-admins see a
  `Forbidden` view (HTTP-403-style copy, "Admin access required.",
  back link to `/home`). Rendered inside `ProtectedRoute` so
  unauthenticated users still redirect to `/`.

### Known Limitations

- **Live-session demotion lag (LD-3 consequence).** A demoted admin
  retains live-session admin power until their access token expires.
  With `ACCESS_TOKEN_EXPIRE_MINUTES=30` + `REFRESH_TOKEN_EXPIRE_DAYS=7`
  (refresh can chain), the worst case is **up to 30 minutes** of
  residual access-token use. `require_admin` re-reads `user.role` from
  DB on every request, so the DB flip takes effect at next token-auth.
  There is no active JWT invalidation. Intentional per LD-3 — full
  revocation needs its own infra decision (Redis blocklist vs
  short-admin-TTL tokens vs per-request role re-check). Tracked as
  **E-040-follow** (🔴 P3).

---

## Acceptance Criteria

- **AC-1** — Login via `POST /api/v1/auth/google` with a Google email
  in `ADMIN_EMAILS` results in `user.role = 'admin'` in DB; the
  `_user_dict` response reflects `role: 'admin'`.
- **AC-2** — Login with a Google email NOT in `ADMIN_EMAILS` while the
  DB row has `role='admin'` demotes that user to `role='user'` on
  that login.
- **AC-3** — `ADMIN_EMAILS=""` (or unset) treats every user as `role='user'`,
  even when the DB says otherwise — all stale admins demote on next
  login. Fail-closed.
- **AC-4** — Case-insensitive match: `ADMIN_EMAILS='Foo@Bar.com'` +
  login with `'foo@bar.com'` → promotion fires. Whitespace trimmed:
  `ADMIN_EMAILS=' a@b.com , c@d.com '` → frozenset is
  `{'a@b.com', 'c@d.com'}`.
- **AC-5** — `/admin` on the frontend renders a 403 view for
  non-admin authenticated users (no `AdminPanel` lazy chunk
  executed past the gate). Admins see `AdminPanel` unchanged.
  Unauthenticated requests hit `ProtectedRoute` and redirect
  to `/` (existing behaviour).
- **AC-6** — A promotion writes one `admin_audit_log` row with
  `query_params.action = 'promoted'`, `query_params.prior_role = 'user'`,
  `query_params.new_role = 'admin'`. A demotion writes the mirror row
  with `action = 'demoted'`. An `unchanged` reconciliation writes
  **no** audit row.
- **AC-7** — `admin_role_reconciled` PostHog event fires on every
  login with `{email, prior_role, new_role, action}` — including
  the `unchanged` branch. Test verifies `action` string matches
  the three legal values and that the `email` property is present.

---

## Locked Decisions

- **LD-1** — **No MFA in this slice.** TOTP/WebAuthn for admins is
  its own spec. Don't bundle.
- **LD-2** — **No admin-promotion UI.** The env var is the only
  promotion path. Any in-app "make this user an admin" endpoint
  would subvert the single-source-of-truth premise.
- **LD-3** — **Reconciliation runs on every login, not every
  request.** `require_admin` stays a cheap DB equality check; no
  per-request env parse or set membership test. Consequence: the
  live-session demotion lag documented in §Known Limitations.
- **LD-4** — **Demotion of a legitimate admin whose email was
  removed from `ADMIN_EMAILS` is the intended behaviour.** No
  "grace period", no confirmation prompt, no override flag. The
  env var is the source of truth; if a name drops off the list,
  that's a real change.

---

## API Contract

No new endpoints. `POST /api/v1/auth/google` gets two side effects
between user upsert and JWT issuance:

1. Reconcile role (possible DB mutation + commit).
2. Write audit row (promotion/demotion only) + emit PostHog event.

Response shape (`TokenResponse.user = _user_dict(user)`) reflects the
reconciled role, so the frontend receives the correct state on the
same call.

---

## Implementation Plan

### Backend

1. **`app/core/config.py`** — add:
   ```python
   admin_emails: str = ""

   @property
   def admin_emails_set(self) -> frozenset[str]:
       return frozenset(
           e.strip().lower()
           for e in self.admin_emails.split(",")
           if e.strip()
       )
   ```
   Parse once via the existing `@lru_cache` on `get_settings()`.

2. **`hirelens-backend/.env.example`** — append:
   ```
   # Comma-separated list of Google emails granted admin role on login.
   # Case-insensitive. Empty/unset = no admins (fail-closed).
   ADMIN_EMAILS=
   ```

3. **`app/services/user_service.py`** — new
   `reconcile_admin_role(user, admin_emails_set) -> tuple[str, str, str]`
   returning `(action, prior_role, new_role)`. Pure function over
   the User object; mutates `user.role` in-place on promotion/
   demotion. Does not commit, does not audit, does not emit — caller
   owns those side effects. Keeps the branching testable in
   isolation.

4. **`app/api/v1/routes/auth.py::google_auth`** — after
   `get_or_create_user`, before `create_access_token`:
   - Call `reconcile_admin_role(user, settings.admin_emails_set)`.
   - On `action in ('promoted', 'demoted')`: `await db.flush()`,
     write `AdminAuditLog` row via a small helper mirroring
     `_write_admin_audit_log` from `deps.py` (don't reuse that one
     directly — it's request-scoped and tuned for the audit
     dependency; a dedicated `_log_role_reconciliation` helper
     keeps auth.py clean and testable).
   - Emit `admin_role_reconciled` PostHog event unconditionally
     (all three actions) via `app.core.analytics.track`.

5. **Tests** (`tests/test_auth_admin_whitelist.py`, new file):
   - `test_login_whitelisted_email_promotes_to_admin`
   - `test_login_non_whitelisted_demotes_stale_admin`
   - `test_empty_admin_emails_demotes_all_stale_admins`
   - `test_case_insensitive_whitelist_match`
   - `test_whitespace_stripped_in_whitelist_parsing`
   - `test_unchanged_role_writes_no_audit_row`
   - `test_audit_row_written_on_promotion_with_query_params`
   - `test_audit_row_written_on_demotion_with_query_params`
   - `test_admin_role_reconciled_event_fires_on_every_login`

### Frontend

1. **New `src/components/auth/AdminGate.tsx`** — reads `user` from
   `useAuth()`; if `user?.role === 'admin'` renders `children`; else
   renders a `Forbidden` view using design tokens (no hardcoded
   hex). Typed as
   `({ children }: { children: React.ReactNode }) => JSX.Element | null`.
   Returns `null` while auth is loading to avoid a flicker.

2. **`src/App.tsx`** — wrap `<AdminPanel />` route element in
   `<ProtectedRoute><AdminGate><AdminPanel /></AdminGate></ProtectedRoute>`.
   No other routes change.

3. **Tests** (`hirelens-frontend/tests/AdminGate.test.tsx`, new file):
   - renders children for `user.role === 'admin'`
   - renders Forbidden view for `user.role === 'user'`
   - returns null while `isLoading`
   - Forbidden view has a back-link to `/home`

---

## Analytics

Add to `.agent/skills/analytics.md` Frontend/Backend events table:

- `admin_role_reconciled` (backend, `app/api/v1/routes/auth.py`) —
  `{email, prior_role, new_role, action: 'promoted'|'demoted'|'unchanged'}`.
  Fires on every `POST /api/v1/auth/google` call. `unchanged` fires
  too — it's a heartbeat signal that whitelist evaluation is
  happening, useful for dashboards and for alerting on sudden
  absence.

No new frontend events. `AdminGate` doesn't fire analytics (the
403 view is a dead-end state; if we ever care about "non-admin
hit `/admin`" counts, file a follow-up).

---

## Config Changes

New env var:

| Var | Purpose | Default | Phase |
|-----|---------|---------|-------|
| `ADMIN_EMAILS` | Comma-separated Google emails granted admin role on login | `""` (empty = no admins) | 5 |

Update `AGENTS.md` Environment Variables table in the same commit
as the impl (commit 3), not the spec commit.

---

## Dependencies

- ✅ `admin_audit_log` table + `AdminAuditLog` model shipped in
  E-018a (`hirelens-backend/app/models/admin_audit_log.py`,
  migration `538fe233b639`).
- ✅ `app.core.analytics.track` is already the canonical backend
  PostHog emitter.
- ✅ `AuthContext` already exposes `user.role: 'user' | 'admin'`
  (`hirelens-frontend/src/context/AuthContext.tsx:32`).

---

## Out of Scope

- **MFA** for admin role — separate spec if/when needed.
- **Admin-promotion UI** — LD-2 explicitly rejects it.
- **JWT revocation on demotion** — §Known Limitations;
  tracked as **E-040-follow**.
- **Admin session IP pinning** — spec #38 §Out-of-scope follow-up;
  stays deferred under the narrower hardening umbrella.
- **Short admin-TTL tokens** — same; deferred.
- **Admin-scoped rate limit profile** — same; deferred.
