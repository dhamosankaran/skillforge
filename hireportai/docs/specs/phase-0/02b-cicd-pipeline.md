# SPEC: GitHub Actions CI Pipeline

## Status: Done

## Problem
Without a CI pipeline every merge to main is a manual gamble: a developer
must remember to run `pytest`, `vitest`, and verify that `alembic upgrade head`
followed by `alembic downgrade -1` actually works before pushing. Human memory
is not a reliable gate. The longer CI is deferred the more tests accumulate
without being run in a neutral environment, and the more likely it is that
"works on my machine" diverges from what Railway and Vercel will see.

## Solution
Add a three-job GitHub Actions workflow (`.github/workflows/ci.yml`) that runs
on every push to `main` and on every pull request. The jobs are:

1. **backend-tests** — spin up a PostgreSQL 16 + pgvector service container,
   install Python 3.13 deps, run the full `pytest` suite.
2. **frontend-tests** — install Node 20 deps, run `vitest run`.
3. **migration-rollback** — spin up a separate PostgreSQL 16 + pgvector
   container, run `alembic upgrade head → downgrade -1 → upgrade head` to
   prove every migration is reversible.

No auto-deploy steps are included: Railway and Vercel both watch the repo
directly via git push detection and trigger their own deploy pipelines. CI's
job is to be the red/green gate, not the deploy agent.

## Acceptance Criteria
- [ ] AC-1: A push to `main` triggers the workflow and all three jobs appear
      in the GitHub Actions UI.
- [ ] AC-2: `backend-tests` runs `pytest tests/ -v --tb=short` against a live
      PostgreSQL 16 + pgvector service container and exits 0.
- [ ] AC-3: `frontend-tests` runs `vitest run --passWithNoTests` and exits 0.
      (The `--passWithNoTests` flag is required because there are no frontend
      tests yet in Phase 0; the flag is removed when the first real test ships.)
- [ ] AC-4: `migration-rollback` runs `alembic upgrade head`, then
      `alembic downgrade -1`, then `alembic upgrade head` and all three
      commands exit 0 against a live PostgreSQL 16 + pgvector container.
- [ ] AC-5: The workflow uses Python 3.13 for all backend steps and Node 20
      for all frontend steps.
- [ ] AC-6: `pip` and `npm` caches are keyed to their respective lock files
      (`requirements-dev.txt` for backend, `package-lock.json` for frontend)
      so repeated runs do not re-download the internet.
- [ ] AC-7: No secrets or credentials are hardcoded in the workflow file. The
      PostgreSQL service containers use ephemeral CI-only credentials scoped
      to the GitHub Actions runner.

## API Contract
None. This spec adds no new HTTP surface.

## Data Model Changes
None. The PostgreSQL service containers are ephemeral and torn down when the
runner exits.

## Configuration Changes

### New file: `.github/workflows/ci.yml`
Three-job workflow at the repository root. See the Implementation Notes section
for the job graph and key decisions.

### Updated: `hirelens-frontend/package.json`
- Added `"vitest": "^2.0.0"` to `devDependencies`.
- Added `"test": "vitest run --passWithNoTests"` to `scripts`.

### Updated: `hirelens-frontend/vite.config.ts`
Added a `test` block so Vitest inherits the existing Vite alias and plugin
config without a separate `vitest.config.ts`:
```ts
test: {
  globals: true,
  passWithNoTests: true,
}
```

### Not changed: `requirements.txt` / `requirements-dev.txt`
`requirements-dev.txt` was introduced in spec `02a` and already includes
`pytest` and `pytest-asyncio`. CI installs `requirements-dev.txt`.

## UI/UX
None. This spec is entirely infrastructure.

## Edge Cases

### pgvector not available in the default `postgres:16` image
The official `postgres:16` Docker image does not include the `vector` extension.
Using it as the service container causes `CREATE EXTENSION vector` to fail and
all DB integration tests to fail. **Fix:** Use `pgvector/pgvector:pg16` as the
service image for both `backend-tests` and `migration-rollback`. This is the
official pgvector-bundled PostgreSQL image maintained by the pgvector project.

### `alembic downgrade -1` with no prior revision
The first migration (`0001_pg_init`) has `down_revision = None`. Running
`downgrade -1` from the base revision attempts to step below `None`, which
Alembic handles by doing nothing and exiting 0 — so the three-step
(upgrade → downgrade → upgrade) sequence is safe even for the very first
migration. This was verified locally before this spec was written.

### `pytest` skipping DB tests when `TEST_DATABASE_URL` is unreachable
`conftest.py` calls `pytest.skip` at the session level if the DB is not
reachable. In CI the service container is started before the test step, so
the DB is always reachable. If the service container fails to start,
GitHub Actions marks the job as failed at the service-startup step rather
than at pytest, which gives a clear signal.

### `vitest run` exiting 1 with no test files
Vitest >= 1.0 exits with code 1 if no test files are found, unless
`--passWithNoTests` is passed or `passWithNoTests: true` is set in config.
Since Phase 0 ships no frontend tests, both the CLI flag and the config key
are set. The flag is removed when the first real frontend test lands.

### `pip cache` keyed to `requirements-dev.txt`
The `actions/setup-python` cache is keyed to `requirements-dev.txt` because
that is the file CI installs. If only `requirements.txt` changes but not
`requirements-dev.txt`, the cache key does not change — `requirements-dev.txt`
uses `-r requirements.txt` so pip will upgrade the changed packages from the
partial cache on cache hit, which is fast and correct.

## Dependencies
- **Spec `00-postgresql-migration`**: migration must exist and be reversible
  for AC-4 to pass.
- **Spec `02a-skeleton-deploy`**: `requirements-dev.txt` introduced there is
  the install target for `backend-tests`.
- **External**: The GitHub repository must have Actions enabled (default for
  new repos). No additional GitHub secrets are required for Phase 0 CI —
  deploy secrets (Railway token, Vercel token) are added in the deploy spec.

## Implementation Notes

### Job isolation
Each job gets its own runner and its own PostgreSQL service container. The
`backend-tests` and `migration-rollback` jobs use separate DB names
(`hireport_test` and `hireport_migrate` respectively) even though they run in
separate containers — belt-and-suspenders to make it obvious in logs which
job owns which DB.

### `working-directory` via `defaults.run`
All steps within a job inherit the `defaults.run.working-directory` so
individual `run` steps do not repeat the `cd` prefix. The working-directory
is relative to the repository root.

### No deploy steps
Railway auto-deploys on push to `main` via its GitHub integration.
Vercel does the same. Adding deploy steps to CI would create a race condition
(CI deploy + platform deploy in parallel) and would require storing
platform API tokens as GitHub secrets. Both are unnecessary overhead in
Phase 0.

## Test Plan
This spec is itself a test harness. Its acceptance criteria are verified by
pushing the workflow file to `main` and observing the GitHub Actions run.
There is no separate test file for this spec.
