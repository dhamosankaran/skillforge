# SPEC: Frontend ↔ Backend Auth Unification

## Status: Done

## Problem
The frontend and backend auth systems are completely disconnected.

The backend has a full JWT auth implementation: `POST /api/v1/auth/google`
accepts a Google ID token, verifies it with Google's tokeninfo endpoint,
upserts the user in PostgreSQL, and returns a signed `access_token` /
`refresh_token` pair. Every protected backend route expects
`Authorization: Bearer <access_token>`.

The frontend ignores all of this. `AuthContext.signIn()` base64-decodes the
raw Google credential *client-side* and stores `{name, email, picture,
googleId}` directly in localStorage — never calling the backend. `api.ts`
sends no auth headers on any request. There are no protected routes: any
URL is accessible without logging in. Token expiry and refresh are not
handled at all.

The result is that every backend route requiring `Depends(get_current_user)`
returns 401 for all frontend requests, and any per-user data (tracker
applications, subscription plan, saved resumes) is inaccessible.

## Solution
Wire the frontend through the backend's existing JWT auth endpoints:

1. After Google One Tap / Sign-In fires, POST the Google credential to
   `POST /api/v1/auth/google` instead of decoding it client-side.
2. Store the returned `access_token`, `refresh_token`, and backend user
   object in localStorage under well-known keys.
3. Add an Axios request interceptor that injects `Authorization: Bearer
   <access_token>` on every request.
4. Add an Axios response interceptor that silently refreshes the access
   token on 401 and retries the original request once.
5. On app load, re-validate tokens by calling `GET /api/v1/auth/me`; clear
   stale tokens if the call fails.
6. Wrap all feature routes in a `<ProtectedRoute>` that redirects
   unauthenticated users to `/`.
7. Update the `AuthUser` TypeScript type to match the backend's user schema.

No backend changes are required — the auth endpoints are complete.

## Acceptance Criteria

- [ ] AC-1: **Backend call on sign-in** — Given a valid Google ID token from
  the One Tap / Sign-In button callback, when `signIn(credential)` is
  called, then the frontend POSTs `{credential}` to
  `POST /api/v1/auth/google`, receives `{access_token, refresh_token,
  token_type, user}`, stores `access_token` under localStorage key
  `hireport_access_token`, stores `refresh_token` under
  `hireport_refresh_token`, stores the user object under `hireport_user`,
  and updates React auth state. The old `decodeGoogleJwt()` helper and
  `hireport_user` storing of raw Google data are removed entirely.

- [ ] AC-2: **Bearer header on every request** — Given a logged-in user,
  when any call is made through `services/api.ts` (Axios instance), then
  the request automatically includes `Authorization: Bearer <access_token>`
  injected by a request interceptor reading from localStorage. Anonymous
  calls (no token in storage) are sent without the header, preserving
  support for unauthenticated tracker operations.

- [ ] AC-3: **Silent token refresh on 401** — Given a logged-in user whose
  access token has expired (30-minute lifetime), when an API call returns
  HTTP 401, then the Axios response interceptor:
  (a) POSTs to `POST /api/v1/auth/refresh` with `{refresh_token}`,
  (b) replaces `hireport_access_token` in localStorage with the new token,
  (c) retries the original request exactly once with the new token.
  If the refresh call itself returns 401 (refresh token expired after 7
  days) or fails, the interceptor calls `signOut()` and navigates to `/`.
  Concurrent 401 responses during a pending refresh are queued and resolved
  with the same new token — the refresh call is made only once.

- [ ] AC-4: **Sign-out** — Given a logged-in user, when `signOut()` is
  called, then:
  (a) `POST /api/v1/auth/logout` is called best-effort (errors are
      swallowed — logout is always local),
  (b) `hireport_access_token`, `hireport_refresh_token`, and `hireport_user`
      are removed from localStorage,
  (c) React auth state is reset to `user: null`,
  (d) the app navigates to `/`.

- [ ] AC-5: **Auth hydration on page reload** — Given valid tokens in
  localStorage, when the React app first mounts, then `AuthContext` calls
  `GET /api/v1/auth/me` with the stored access token to re-validate the
  session and refresh the user object (subscription info may have changed).
  If the call succeeds, auth state is populated with the backend user object.
  If the call returns 401 (token expired, no refresh attempted here since
  this is the initial hydration path), all three localStorage keys are
  cleared and the user is treated as unauthenticated. An `isLoading: boolean`
  flag is exposed on the context so consuming components can show a spinner
  during the initial hydration check rather than flashing a redirect.

- [ ] AC-6: **Protected routes** — Given an unauthenticated user (no valid
  token in localStorage or hydration returned 401), when they navigate to
  any feature route (`/analyze`, `/results`, `/rewrite`, `/tracker`,
  `/interview`), then they are redirected to `/`. The routes `/` and
  `/pricing` remain publicly accessible. The redirect preserves the
  attempted path in location state so the user can be sent there after
  successful sign-in (future improvement, not required for this spec).

- [ ] AC-7: **`AuthUser` type alignment** — Given `AuthContext.tsx`, when
  this spec is complete, then the `AuthUser` TypeScript interface matches
  the backend `TokenResponse.user` shape exactly:
  ```typescript
  interface AuthUser {
    id: string
    email: string
    name: string
    avatar_url: string | null
  }
  ```
  All components that currently read `user.picture` or `user.googleId` are
  updated to `user.avatar_url` and removed respectively.

- [ ] AC-8: **Environment variables** — Given `hirelens-frontend/.env.example`,
  when this spec is complete, then it documents:
  ```
  VITE_GOOGLE_CLIENT_ID=<your Google OAuth client ID>
  VITE_API_BASE_URL=http://localhost:8000
  ```
  The backend `.env.example` already documents `GOOGLE_CLIENT_ID`,
  `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, and
  `REFRESH_TOKEN_EXPIRE_DAYS` — no changes needed there.

- [ ] AC-9: **No SQLite / client-only auth references** — Given
  `hirelens-frontend/src`, when this spec is complete, then
  `grep -r "decodeGoogleJwt\|googleId\|hireport_user.*picture"` returns
  zero matches. The Google credential string from One Tap is only ever
  forwarded to the backend; it is never decoded or stored in the frontend.

## API Contract

All endpoints are already implemented on the backend. This section documents
the contracts the frontend must conform to.

### `POST /api/v1/auth/google`
Exchange a Google ID token for backend JWTs.

**Request**
```json
{ "credential": "<Google ID token string>" }
```

**Response 200**
```json
{
  "access_token":  "<signed HS256 JWT, expires in 30 min>",
  "refresh_token": "<signed HS256 JWT, expires in 7 days>",
  "token_type":    "bearer",
  "user": {
    "id":         "<UUID string>",
    "email":      "user@example.com",
    "name":       "Display Name",
    "avatar_url": "https://..." | null
  }
}
```

**Response 401** — Google credential invalid or audience mismatch
```json
{ "detail": "Invalid Google credential" }
```

---

### `POST /api/v1/auth/refresh`
Exchange a valid refresh token for a new access token.

**Request**
```json
{ "refresh_token": "<stored refresh JWT>" }
```

**Response 200**
```json
{ "access_token": "<new access JWT>", "token_type": "bearer" }
```

**Response 401** — refresh token expired or malformed
```json
{ "detail": "Invalid or expired refresh token" }
```

---

### `POST /api/v1/auth/logout`
Stateless server-side logout (client discards tokens).

**Request** — `Authorization: Bearer <access_token>` header required

**Response 200**
```json
{ "message": "Logged out successfully" }
```

---

### `GET /api/v1/auth/me`
Return the current user's profile and subscription.

**Request** — `Authorization: Bearer <access_token>` header required

**Response 200**
```json
{
  "id":         "<UUID string>",
  "email":      "user@example.com",
  "name":       "Display Name",
  "avatar_url": "https://..." | null,
  "created_at": "2026-04-07 12:00:00",
  "subscription": {
    "plan":               "free" | "pro" | "enterprise",
    "status":             "active" | "...",
    "current_period_end": "2026-05-07 12:00:00" | null
  }
}
```

**Response 401** — token missing, expired, or invalid user
```json
{ "detail": "Authentication required" }
```

---

### localStorage key schema (frontend)

| Key                      | Value                          | Cleared on    |
|--------------------------|--------------------------------|---------------|
| `hireport_access_token`  | Raw JWT string                 | signOut, 401 refresh failure |
| `hireport_refresh_token` | Raw JWT string                 | signOut, 401 refresh failure |
| `hireport_user`          | JSON `AuthUser` object         | signOut, 401 refresh failure |

## Data Model Changes

None. The backend schema (`users`, `subscriptions`) and all auth service
functions are unchanged.

## UI/UX

- **Sign-in flow**: The Google One Tap / Sign-In button already exists on
  the Landing page. The only visible change is that sign-in may take slightly
  longer (one extra network round-trip to the backend) — no UI change
  required beyond the async handling.
- **Loading state**: Components that depend on `useAuth()` should render a
  neutral loading state while `isLoading` is true (hydration in progress) to
  avoid a flash of the unauthenticated view on page refresh.
- **Navbar**: The avatar display (`user.picture`) must be updated to
  `user.avatar_url`. Sign-out button calls the new `signOut()` which is now
  async (awaits the logout API call before clearing state).
- **No new pages**: There is no dedicated `/login` route in this spec.
  Sign-in happens via the Google button on the Landing page. Post-login
  redirect to `/analyze` is the target UX.

## Edge Cases

- **Google Client ID missing**: `VITE_GOOGLE_CLIENT_ID` is empty in dev.
  `GoogleOAuthProvider` still renders; the sign-in button fails with a
  console warning. Auth state stays `null`. No crash.
- **Backend unreachable during hydration** (`GET /api/v1/auth/me` network
  error, not 401): treat as unauthenticated — clear tokens, no redirect loop.
  Use a `try/catch` separate from the 401 path.
- **Concurrent 401 responses**: two inflight requests both get 401. Implement
  a module-level `isRefreshing` flag and a `pendingQueue` in the Axios
  response interceptor. While a refresh is in flight, queue subsequent
  retries; resolve or reject them all once the refresh resolves.
- **Refresh token expired on first page load**: hydration calls
  `GET /auth/me`, gets 401 (access token expired). At hydration time do NOT
  attempt a refresh — just clear tokens. This avoids a three-way chain on
  initial load. The user must sign in again.
- **Sign-in while already signed in**: `signIn()` always overwrites stored
  tokens — no guard needed.
- **CORS**: the backend already has `allow_credentials=True` and
  `allow_origins` set to `http://localhost:5199`. `VITE_API_BASE_URL` in the
  frontend `.env` must point to `http://localhost:8000` for CORS to pass in
  dev.

## Dependencies

- Spec `00-postgresql-migration.md` — **Done**. The `users` table and all
  auth services are PostgreSQL-backed as of that spec.
- Spec `01-alembic-setup.md` — not a blocker for auth; auth tables already
  exist from migration `0001_pg_init`.

## Test Plan

### Backend tests (`tests/test_auth.py` — new file)

Uses `httpx.AsyncClient` via FastAPI's `TestClient` pattern and mocks
`app.core.security.verify_google_token` at the module level with
`unittest.mock.AsyncMock`.

- **`test_google_auth_valid_credential`**: patch `verify_google_token` to
  return `{google_id, email, name, avatar_url}`, POST to
  `/api/v1/auth/google`, assert HTTP 200, `access_token` and
  `refresh_token` present, `user.email` matches.
- **`test_google_auth_invalid_credential`**: patch `verify_google_token` to
  return `None`, assert HTTP 401 with `detail: "Invalid Google credential"`.
- **`test_google_auth_upserts_existing_user`**: call `google_auth` twice with
  the same `google_id`; assert HTTP 200 both times and that the returned
  `user.id` is identical (upsert, not duplicate insert).
- **`test_refresh_valid_token`**: generate a refresh token via
  `create_refresh_token({"sub": user_id, "email": email})`, POST to
  `/api/v1/auth/refresh`, assert HTTP 200 and `access_token` present.
- **`test_refresh_expired_token`**: sign a token with `exp` in the past,
  assert HTTP 401.
- **`test_refresh_access_token_rejected`**: send an access token (not a
  refresh token) to `/auth/refresh`, assert HTTP 401 (type mismatch guard).
- **`test_get_me_authenticated`**: create a user + access token, GET
  `/api/v1/auth/me`, assert HTTP 200 and `email`, `subscription.plan`.
- **`test_get_me_unauthenticated`**: GET `/api/v1/auth/me` without header,
  assert HTTP 401.
- **`test_logout_authenticated`**: POST `/api/v1/auth/logout` with valid
  token, assert HTTP 200 and `message: "Logged out successfully"`.
- **`test_logout_unauthenticated`**: POST without token, assert HTTP 401.

### Frontend tests (`hirelens-frontend/src/context/AuthContext.test.tsx` — new)

Uses Vitest + React Testing Library. The Axios instance is mocked with
`vitest.mock('../services/api')`.

- **`signIn posts credential to backend and stores tokens`**: mock
  `api.post` to return `{access_token, refresh_token, user}`, call
  `signIn("fake-credential")`, assert `localStorage.getItem
  ("hireport_access_token")` is set and context `user` matches backend
  response.
- **`signIn clears state on backend 401`**: mock `api.post` to throw 401,
  assert `user` remains `null` and no tokens are stored.
- **`signOut clears tokens and calls logout endpoint`**: set up signed-in
  state, call `signOut()`, assert all three localStorage keys are cleared
  and `api.post("/api/v1/auth/logout")` was called.
- **`hydration calls /auth/me on mount`**: pre-populate
  `hireport_access_token` in localStorage, mock `api.get` to return user
  object, render `AuthProvider`, assert `user` is populated.
- **`hydration on 401 clears stale tokens`**: pre-populate token, mock
  `api.get` to throw 401, assert localStorage is cleared after mount.
- **`isLoading is true during hydration and false after`**: assert
  `isLoading === true` synchronously after mount and `false` after the mock
  resolves.

### Frontend tests (`hirelens-frontend/src/services/api.test.ts` — new)

- **`request interceptor attaches Bearer token`**: set
  `hireport_access_token` in localStorage, trigger a request, assert
  `Authorization: Bearer <token>` header present.
- **`request interceptor omits header when no token`**: no token in
  storage, assert no `Authorization` header.
- **`401 response triggers refresh and retries original request`**: mock
  first call → 401, mock `/auth/refresh` → new token, mock retry → 200;
  assert final response is 200 and the original endpoint was called twice.
- **`double 401 only triggers one refresh`**: mock two concurrent requests
  both returning 401; assert `/auth/refresh` was called exactly once and
  both requests eventually resolve with 200.
- **`refresh failure triggers signOut`**: mock `/auth/refresh` → 401;
  assert `signOut()` is called.

### Manual verification

1. Set `VITE_GOOGLE_CLIENT_ID` and `VITE_API_BASE_URL=http://localhost:8000`
   in `hirelens-frontend/.env`.
2. Set `GOOGLE_CLIENT_ID` and `JWT_SECRET_KEY` (any non-default string) in
   `hirelens-backend/.env`.
3. Start backend (`uvicorn app.main:app --reload --port 8000`) and frontend
   (`npm run dev -- --port 5199`).
4. Open `http://localhost:5199`, click Google Sign-In → observe Network tab:
   `POST /api/v1/auth/google` returns 200 with tokens.
5. Open DevTools → Application → localStorage → verify
   `hireport_access_token`, `hireport_refresh_token`, `hireport_user` are
   set. Confirm `hireport_user` contains `id` (UUID) and `avatar_url` (not
   `picture`/`googleId`).
6. Navigate to `http://localhost:5199/tracker` while signed in → page loads.
7. Sign out → localStorage cleared, redirected to `/`.
8. Navigate directly to `http://localhost:5199/tracker` while signed out →
   redirected to `/`.
9. Refresh the page while signed in → auth persists (Network tab shows
   `GET /api/v1/auth/me` 200, no sign-in prompt).
10. `grep -r "decodeGoogleJwt\|user\.picture\|user\.googleId"
    hirelens-frontend/src` → zero matches.
11. `python -m pytest tests/ -v --tb=short` → all tests pass (including
    new `test_auth.py`).
