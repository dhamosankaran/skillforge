# SPEC: Skeleton Deploy — Vercel (FE) + Railway (BE + Managed PG)

## Status: Done

## Problem
Deferring deployment until features are built guarantees a painful launch day:
CORS headers differ between `localhost` and a real domain, `DATABASE_URL`
formats diverge between local `asyncpg` and Railway's managed PostgreSQL,
connection pool settings that work on a single dev machine fail under a
long-running process, and environment variable wiring is always wrong the first
time. Discovering all of this 12 weeks in — when a large surface area must be
debugged simultaneously — multiplies the time to fix each issue. Standing up
the deploy pipeline in Phase 0, while the codebase is still a skeleton, keeps
the feedback loop tight and eliminates an entire class of launch-day surprises.

## Solution
Deploy the current skeleton app (health endpoint only on the backend, a
placeholder index page on the frontend) to the production-grade infrastructure
the project will use for its entire lifetime: Railway for the backend process
and managed PostgreSQL, Vercel for the frontend. Configure environment
variables in both dashboards, wire Alembic migrations as a Railway release
command, and validate CORS between the two deployed URLs. No new product
features are built in this spec — it is a pure infrastructure milestone that
unblocks every Phase-1 spec that assumes a live deploy target.

## Acceptance Criteria
- [ ] AC-1: Backend is deployed to Railway and
      `curl https://<railway-url>/health` returns
      `{"status": "healthy", "service": "hireport-ai"}` with HTTP 200.
- [ ] AC-2: Frontend is deployed to Vercel and the root URL loads in a browser
      without a build error or blank screen (placeholder page is acceptable).
- [ ] AC-3: Frontend can call the deployed backend API without CORS errors —
      concretely, `fetch("https://<railway-url>/health")` executed from the
      deployed Vercel origin returns a 200 response with no blocked-by-CORS
      error in the browser console.
- [ ] AC-4: `alembic upgrade head` runs automatically on every Railway deploy
      via a release command (configured in `railway.toml` or Railway dashboard
      "Release Command" field) and the Railway deploy logs show
      `INFO [alembic.runtime.migration] Running upgrade ... -> 0001_pg_init`
      with no errors.
- [ ] AC-5: All secrets and connection strings (`DATABASE_URL`, `SECRET_KEY`,
      `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ALLOWED_ORIGINS`) are set
      exclusively in the Railway and Vercel dashboards; none appear in committed
      files, `.env` files pushed to the repo, or CI logs.

## API Contract
No new HTTP API surface. The only endpoint exercised by this spec is the
existing `GET /health` which returns:

```json
{"status": "healthy", "service": "hireport-ai"}
```

The `ALLOWED_ORIGINS` environment variable on Railway must include the
production Vercel URL (e.g. `https://hireportai.vercel.app`) so that the
existing CORS middleware in `app/main.py` allows cross-origin requests from
the frontend.

## Data Model Changes
None. The schema deployed is exactly what `alembic upgrade head` produces from
the migration authored in spec `00-postgresql-migration`. The Railway-managed
PostgreSQL instance is a fresh database; the release command runs the migration
on first deploy and is a no-op on subsequent deploys (Alembic checks the
`alembic_version` table).

## Configuration Changes

### `railway.toml` (new file, committed to repo)
```toml
[build]
builder = "NIXPACKS"

[deploy]
releaseCommand = "cd hirelens-backend && alembic upgrade head"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### `vercel.json` (new file, committed to repo)
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

### Backend environment variables (set in Railway dashboard, NOT in code)
| Variable | Value |
|---|---|
| `DATABASE_URL` | Railway-provided `postgresql://...` URL (see Edge Cases for asyncpg prefix) |
| `SECRET_KEY` | Random 64-char hex string |
| `GOOGLE_CLIENT_ID` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console |
| `ALLOWED_ORIGINS` | `https://<vercel-app>.vercel.app` (comma-separated if multiple) |
| `ENVIRONMENT` | `production` |

### Frontend environment variables (set in Vercel dashboard, NOT in code)
| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://<railway-app>.railway.app` |

## UI/UX
The frontend placeholder is the existing Vite default page or the earliest
real page in the repo — whichever is already implemented. No new UI is built
for this spec. The acceptance criterion is that the page loads without errors,
not that it looks polished.

## Edge Cases

### Railway free tier sleep
Railway's free tier idles services after inactivity. On the first request after
a sleep period, the backend cold-starts and the request may time out or return
a 503. **Mitigation (Phase 0):** Document this behaviour in a comment in
`railway.toml`. Upgrade to a paid Railway plan before any user-facing launch.
Do not implement a ping-to-keep-alive hack — it masks the real solution and
wastes free-tier hours. AC-1 is validated immediately after a manual deploy
(not after a sleep period), so the free-tier sleep does not block acceptance.

### CORS origin mismatch
The most common deploy-day CORS failure is a trailing slash or HTTP/HTTPS
mismatch between `ALLOWED_ORIGINS` on the backend and the actual Vercel
origin. **Rules to follow:**
- Always use the exact origin as seen in the browser's `Origin` request header
  (no trailing slash, `https://` scheme, no path).
- If Vercel generates a preview URL (e.g. `https://hireportai-git-main-xxx.vercel.app`),
  it is a different origin from the production URL — add both to
  `ALLOWED_ORIGINS` if previews need to call the backend.
- Validate by opening the browser DevTools Network tab, not just by checking
  the response body: a CORS failure shows up as a blocked request, not a 4xx.

### `DATABASE_URL` format: local asyncpg vs. Railway managed PG
Railway injects `DATABASE_URL` in the standard `postgresql://` (psycopg2)
format. The `asyncpg` driver requires the `postgresql+asyncpg://` scheme prefix
and does not accept `postgres://` (the older Heroku-style alias). **Fix:**
In `app/core/config.py`, normalise the URL at load time:

```python
@property
def async_database_url(self) -> str:
    url = self.database_url
    # Railway injects postgres:// or postgresql:// without driver prefix
    url = url.replace("postgres://", "postgresql://", 1)
    if not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url
```

Use `settings.async_database_url` (not `settings.database_url`) everywhere
`create_async_engine` is called. Alembic's `env.py` continues to use the raw
`DATABASE_URL` with the `psycopg` sync driver (which is already the pattern
established in spec `00-postgresql-migration`).

## Dependencies
- **Spec `00-postgresql-migration`**: must be complete so that `alembic upgrade head`
  runs cleanly against a fresh PostgreSQL database (AC-4).
- **External accounts required** (set up manually before implementing this spec):
  - Railway account with a new project containing a PostgreSQL plugin and a
    web service pointed at this repo's `hirelens-backend/` directory.
  - Vercel account with a new project pointed at this repo's
    `hirelens-frontend/` directory, root directory set to `hirelens-frontend`.
  - Google Cloud Console OAuth credentials with the Railway backend URL added
    to "Authorised redirect URIs" (can be placeholder for now — real auth
    flow is spec `02-auth-unification`).
- **No code dependencies on Phase-1+ specs.** This spec deliberately ships
  zero product features so the deploy surface stays minimal.

## Test Plan

### Manual verification (the only test plan for this spec)
This spec has no automated tests — its acceptance criteria are environmental
facts that cannot be asserted by a local test suite. Each AC must be verified
by hand after deploying.

1. **AC-1 — Backend health:**
   ```
   curl -i https://<railway-url>/health
   ```
   Expected: `HTTP/2 200` with body `{"status":"healthy","service":"hireport-ai"}`.

2. **AC-2 — Frontend loads:**
   Open `https://<vercel-url>` in a browser. Expected: page renders without
   a blank screen or JS console errors (network errors for missing backend data
   are acceptable at this stage).

3. **AC-3 — No CORS errors:**
   Open the browser DevTools Console on the Vercel URL and run:
   ```js
   fetch("https://<railway-url>/health").then(r => r.json()).then(console.log)
   ```
   Expected: `{status: "healthy", service: "hireport-ai"}` printed with no
   CORS error in the Console or Network tab.

4. **AC-4 — Migrations ran:**
   In the Railway dashboard → Deployments → latest deploy → "Release" log,
   confirm the line:
   ```
   INFO [alembic.runtime.migration] Running upgrade  -> 0001_pg_init, initial postgres + pgvector schema
   ```
   appears with no `ERROR` lines. On subsequent redeploys, the log should show:
   ```
   INFO [alembic.runtime.migration] No migrations to apply.
   ```

5. **AC-5 — No secrets in code:**
   ```
   git log -p | grep -E "(SECRET_KEY|DATABASE_URL|CLIENT_SECRET)" | grep "^\+"
   ```
   Expected: zero matches.
   Additionally confirm Railway and Vercel dashboards show the variables listed
   in the Configuration Changes section above.
