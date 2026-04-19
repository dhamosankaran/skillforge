# P5-S21·legacy-route-cleanup — Delete `/api/tracker` + Harden `/api/v1/tracker` + Tracker Service

**Status:** Active — shipping this slice
**Owner:** Dhamo
**Created:** 2026-04-19
**Phase:** 5
**Depends on:** Spec #44 (home widget empty-state contract — patched the call-site leak symptom)
**Closes:** Deferred Hygiene Item `[S35-flag, P5-S18]` — tracker helper path mismatch (cleared after CODEX review, not in this slice)

## 1. Problem Statement

S44 surfaced a cross-tenant data leak: `LastScanWidget` rendered another
user's scan on a fresh user's home page. The root cause was traced to
`GET /api/tracker → tracker_service_v2.get_applications(db, user_id=None) →
unfiltered SELECT`. S44 patched the **symptom** at the widget call-site
by swapping it to a new `fetchUserApplications()` helper pointed at
`/api/v1/tracker`. The **root cause** — the legacy route, the permissive
service branch, and (as this slice's audit now establishes) the v1 route
using `get_current_user_optional` rather than required auth — still sits
on `main`.

### 1.1 Audit findings (Step 2 of this slice)

Three related issues form a single security defect:

1. **Legacy route `/api/tracker` is entirely unauthenticated.** Four
   endpoints (GET/POST/PATCH/DELETE) in `app/api/routes/tracker.py:20-58`
   have no auth dependency and pass `user_id=None` to every service call.
   Any caller — anonymous or otherwise — can read, modify, or delete any
   user's tracker rows.

2. **`/api/v1/tracker` is not actually authenticated.** Four endpoints in
   `app/api/v1/routes/tracker.py:22-68` use
   `Depends(get_current_user_optional)` and pass
   `user_id=user.id if user else None` to the service. When called
   without a bearer token the same cross-tenant leak applies. S44
   referred to this route as "the authenticated replacement"; in truth
   it was misclassified.

3. **`tracker_service_v2` has six permissive-default functions.** Not
   just `get_applications`. Every read function
   (`get_applications`, `find_by_scan_id`, `get_application_by_id`) and
   every write function (`create_application`, `update_application`,
   `delete_application`) accepts `user_id: Optional[str] = None` and
   drops the `WHERE user_id = :uid` filter when None. The three write
   functions are particularly dangerous: `update_application` can
   modify any row and `delete_application` can delete any row when
   called without a user_id.

The problem is one pattern with eight surface endpoints and six service
functions. Splitting across slices would leave the live leak on `main`
for an unknown window. Closing it as one coherent slice is the right
scope.

### 1.2 Why S44 didn't already fix this

S44's [Out of Scope §](./44-home-widget-empty-states.md#out-of-scope)
explicitly deferred both the route deletion and the helper migration:

> - Removing the legacy `/api/tracker` route. Still wired to the legacy
>   `Tracker.tsx` page via `getApplications()`. Separate cleanup.
> - Migrating `getApplications()` globally from `/api/tracker` →
>   `/api/v1/tracker`. Touches every `Tracker.tsx` consumer.

This slice closes both.

## 2. Goals / Non-Goals

### Goals

- Delete the legacy `/api/tracker` route entirely.
- Harden `/api/v1/tracker` so every endpoint requires a valid JWT.
- Harden `tracker_service_v2` so every function that reads or writes
  tracker rows requires an explicit `user_id` and cannot silently
  operate on the whole table.
- Migrate `Tracker.tsx`'s 4 api.ts helpers from `/api/tracker` to
  `/api/v1/tracker` so the full-page tracker keeps working after the
  legacy route is removed.
- Add tests that would have caught the original leak, at both the
  route and service layer.

### Non-Goals

- A full codebase-wide auth audit beyond the unauthenticated and
  user_id-optional surfaces (none found outside tracker).
- Fixing the broader `/api/*` legacy shim surface (analyze, rewrite,
  cover_letter, interview-prep). These are stateless LLM endpoints
  operating on submitted text — they don't leak stored data. See Step 2
  sweep for classification.
- A new `security.md` skill. One already exists and the rule that
  this slice enforces is already documented there
  (§JWT Authentication, §Quick Audit Checklist).
- Adding tracker auto-populate to the v1 analyze route. `/api/v1/analyze`
  does not currently call `tracker_service_v2`; that parity gap is
  pre-existing and out of scope.

## 3. Solution

### 3.1 Per-route changes

| Route | File:line | Before | After |
|---|---|---|---|
| `GET /api/tracker` | `app/api/routes/tracker.py:20` | no auth, `user_id=None` | **DELETED** |
| `POST /api/tracker` | `app/api/routes/tracker.py:28` | no auth, `user_id=None` | **DELETED** |
| `PATCH /api/tracker/{id}` | `app/api/routes/tracker.py:37` | no auth, `user_id=None` | **DELETED** |
| `DELETE /api/tracker/{id}` | `app/api/routes/tracker.py:50` | no auth, `user_id=None` | **DELETED** |
| Registration | `app/main.py:125` | `app.include_router(tracker.router, prefix="/api", tags=["Tracker"])` | **REMOVED** |
| Import | `app/main.py:22` | `from app.api.routes import ..., tracker, ...` | **REMOVED** |
| `GET /api/v1/tracker` | `app/api/v1/routes/tracker.py:22` | `get_current_user_optional` | `get_current_user` (required) |
| `POST /api/v1/tracker` | `app/api/v1/routes/tracker.py:31` | `get_current_user_optional` | `get_current_user` (required) |
| `PATCH /api/v1/tracker/{id}` | `app/api/v1/routes/tracker.py:41` | `get_current_user_optional` | `get_current_user` (required) |
| `DELETE /api/v1/tracker/{id}` | `app/api/v1/routes/tracker.py:57` | `get_current_user_optional` | `get_current_user` (required) |

The legacy route file `app/api/routes/tracker.py` is deleted from disk.

### 3.2 Service hardening

All six functions in `app/services/tracker_service_v2.py` have their
`user_id: Optional[str] = None` default removed — made non-optional
(`user_id: str`) — and the `if user_id:` guard dropped so the filter
is always applied:

| Function | Signature before | Signature after |
|---|---|---|
| `create_application` | `user_id: Optional[str] = None` | `user_id: str` |
| `find_by_scan_id` | `user_id: Optional[str] = None` | `user_id: str` |
| `get_applications` | `user_id: Optional[str] = None` | `user_id: str` |
| `get_application_by_id` | `user_id: Optional[str] = None` | `user_id: str` |
| `update_application` | `user_id: Optional[str] = None` | `user_id: str` |
| `delete_application` | `user_id: Optional[str] = None` | `user_id: str` |

Rationale for **Option A** (non-optional signature) over **Option B**
(runtime `raise ValueError` with Optional default): every caller in
production code (`app/api/routes/analyze.py:206,220` and both route
files) already passes a user_id (once the v1 route is hardened). The
type signature change is self-documenting and fails at call-site
type-check time rather than runtime. Tests additionally assert the
runtime behavior for each function (see §4 below).

### 3.3 Frontend helper migration

`hirelens-frontend/src/services/api.ts` four helpers migrate in place
from `/api/tracker` to `/api/v1/tracker`:

| Helper | Line | Before | After |
|---|---|---|---|
| `getApplications` | 204 | `api.get('/api/tracker')` | `api.get('/api/v1/tracker')` |
| `createApplication` | 218 | `api.post('/api/tracker', data)` | `api.post('/api/v1/tracker', data)` |
| `updateApplication` | 225 | `api.patch('/api/tracker/${id}', data)` | `api.patch('/api/v1/tracker/${id}', data)` |
| `deleteApplication` | 233 | `api.delete('/api/tracker/${id}')` | `api.delete('/api/v1/tracker/${id}')` |

The axios request interceptor (`api.ts:46-52`) already attaches the
Bearer token on every request, so `Tracker.tsx` behavior for
signed-in users does not change. The stale comment block at
`api.ts:209-212` referencing the legacy route is removed; the
`fetchUserApplications()` helper introduced by S44 is kept (it is
pure-v1 already) and its doc comment simplified.

### 3.4 AGENTS.md + API_REFERENCE.md + skill updates

- `AGENTS.md:175` removes the `/api/tracker` row from the Routes
  table.
- `hirelens-backend/API_REFERENCE.md:131` removes the legacy
  `/api/tracker` row.
- `.agent/skills/home.md:151` updates the `LastScanWidget` data-source
  path row from a parenthetical "(post-spec #44)" to a clean
  `/api/v1/tracker` reference.
- `SESSION-STATE.md` "Deferred Hygiene Items" — `[S35-flag, P5-S18]`
  row is **NOT cleared in this slice**. Cleared as a follow-up after
  CODEX review per user directive.

## 4. Acceptance Criteria

- **AC-1.** `GET /api/tracker`, `POST /api/tracker`,
  `PATCH /api/tracker/{id}`, `DELETE /api/tracker/{id}` all return
  **404** (route deleted — FastAPI returns 404 for unmatched paths,
  not 401/405).
- **AC-2.** `GET /api/v1/tracker`, `POST /api/v1/tracker`,
  `PATCH /api/v1/tracker/{id}`, `DELETE /api/v1/tracker/{id}` called
  without a bearer token return **401**.
- **AC-3.** `tracker_service_v2.get_applications` cannot be called
  with `user_id=None`. Calling it with None raises `TypeError` (via
  runtime typing) — covered by an explicit rejection test that passes
  None at runtime and asserts the failure.
- **AC-4.** Same rejection-on-None test exists for the other five
  functions: `create_application`, `find_by_scan_id`,
  `get_application_by_id`, `update_application`, `delete_application`.
- **AC-5.** S44 regression test (`LastScanWidget.test.tsx` empty-state
  branch) still passes unchanged.
- **AC-6.** `Tracker.tsx` page continues to load, create, update, and
  delete applications for a signed-in user. Behavior identical; only
  the URL changed.
- **AC-7.** No regression in existing BE or FE test suites.
- **AC-8.** New backend tests (8 total, per §5 Test Plan) all pass.

## 5. Test Plan

### 5.1 New backend tests

Two route tests (parametrized over all 4 verbs each) and six service
rejection tests.

**Route tests** (new file: `tests/test_tracker_route_auth.py` or
appended to an existing tracker-route test file):

- `test_legacy_tracker_route_returns_404` — parametrized over
  `[("GET", "/api/tracker"), ("POST", "/api/tracker"),
  ("PATCH", "/api/tracker/abc"), ("DELETE", "/api/tracker/abc")]`.
  Hits the path with an unauthenticated httpx client, asserts 404.
- `test_v1_tracker_requires_auth` — parametrized over the same 4
  verbs on `/api/v1/tracker`. Hits each with no Authorization header,
  asserts 401.

**Service rejection tests** (appended to `tests/test_tracker_orm.py`):

- `test_get_applications_rejects_null_user_id`
- `test_create_application_rejects_null_user_id`
- `test_find_by_scan_id_rejects_null_user_id`
- `test_get_application_by_id_rejects_null_user_id`
- `test_update_application_rejects_null_user_id`
- `test_delete_application_rejects_null_user_id`

Each passes `user_id=None` via keyword and asserts the call raises
(TypeError or whatever the typing-enforced runtime reports — the test
uses `pytest.raises(Exception)` with a narrower assertion on the
message containing `user_id`).

### 5.2 Existing test changes

- `tests/test_tracker_orm.py::test_unauthenticated_crud` — **DELETED**.
  This test explicitly validated the leak path end-to-end
  (create/list/update/delete all with `user_id=None`). Its intent was
  bad: it documented the unauthenticated CRUD as a feature. Replaced
  by the six rejection tests listed above.
- `tests/test_tracker_orm.py::test_authenticated_scoped_crud` —
  unchanged. Validates cross-tenant scoping (two users, one doesn't
  see the other's row).
- `tests/test_tracker_scan.py` — unchanged. All three tests already
  pass real `user_id`.

### 5.3 Expected test counts

- BE baseline: 228 unit passed, 6 integration deselected.
- BE after slice: 228 − 1 (deleted unauth test) + 8 (new tests) = **235 unit**.
- FE baseline: 101 passing.
- FE after slice: **101 unchanged** — no new frontend tests; URL swap
  is behavior-preserving for signed-in users and covered by the
  existing `LastScanWidget.test.tsx` + widget empty-state suite.

### 5.4 Manual verification

- Boot backend: `uvicorn app.main:app --reload --port 8000`.
- `curl -i http://localhost:8000/api/tracker` → expect 404.
- `curl -i http://localhost:8000/api/v1/tracker` (no token) → expect 401.
- Boot frontend, open `/prep/tracker` as a signed-in user, add a row,
  edit it, delete it — all CRUD works.
- Open `/home` on the same user, verify LastScan widget unchanged.

## 6. Security Note

This class of bug — a service function accepting `user_id: Optional = None`
and silently dropping the tenant filter — is what the widget empty-state
contract in `.agent/skills/home.md` §Rule 2 exists to prevent at the
call-site. This slice closes it at the source, so the skill rule is now
backed by the code layer and not just reviewer discipline.

The same-pattern audit (Step 2c of this slice) confirmed no other
service in `app/services/` uses this signature. The pattern is
localized to `tracker_service_v2` and now eliminated.

No new skill file is needed: the existing `.agent/skills/security.md`
§JWT Authentication rule already says *"every non-public route uses
`Depends(get_current_user)`"*. The legacy `/api/tracker` route and the
optional-auth `/api/v1/tracker` route were pre-existing violations of
that rule. The rule didn't need rewriting — it needed enforcing.

## 7. Out of Scope

- A full `security.md` rewrite or a new auth-scope skill
  (pattern-enforcement rule belongs in a lint, not a skill).
- Migrating the other legacy `/api/*` stateless endpoints
  (analyze / rewrite / cover-letter / interview-prep) to v1. They do
  not leak stored data; they operate on submitted text.
- Backfilling the `/api/v1/analyze` route to auto-populate the tracker
  (legacy-only behavior; pre-existing parity gap).
- Clearing the `[S35-flag, P5-S18]` Deferred Hygiene entry in
  `SESSION-STATE.md` — cleared as a follow-up after CODEX review.
- Test `test_unauthenticated_crud` is deleted rather than refactored:
  its intent was to validate the leak path, not a new no-auth policy.

## 8. Rollout

No migration. No environment variable. No user-facing copy change.
Push to `main` → Railway redeploys the backend → legacy path
returns 404 within one restart. Vercel redeploys the frontend with
the updated api.ts URLs. Behavior for authenticated users is
identical on both sides of the deploy.

Rollback: `git revert <commit>` restores the leak. Because the
service-function signatures also revert, `Tracker.tsx` would continue
to work on the v1 route (which also reverts to optional auth).

## 9. Observability

- No new PostHog events — nothing new for the user, and reversing a
  leak isn't a product event. A successful deploy is the entire
  acceptance signal.
- Optional future follow-up (not in this slice): if Sentry logs a
  `401` spike on `/api/v1/tracker` within 24h of deploy, that's the
  signal a caller we missed was relying on the optional-auth path.
  None is expected given the call-site audit (two route files + one
  legacy analyze caller + tests).
