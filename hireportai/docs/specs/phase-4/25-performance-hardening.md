# SPEC #25: Rate Limiting + Frontend Performance

## Status: Complete
## Phase: 4
## Branch: main

---

## Problem

The API has no rate limiting — a single client can make unlimited requests,
enabling abuse, credential stuffing on auth endpoints, and expensive LLM calls
via the admin card generator. Additionally, the frontend ships all page
components in a single bundle, penalizing initial load for admin-only and
infrequently-used pages.

## Solution

### Part A — Backend Rate Limiting (slowapi)

Add per-IP rate limiting via `slowapi`:
- **100 req/min** — default for all API endpoints
- **10 req/min** — auth endpoints (login, refresh, logout, me, onboarding)
- **5 req/min** — `POST /admin/cards/generate` (LLM calls are expensive)
- Returns `429 Too Many Requests` with `Retry-After` header when exceeded.

### Part B — Frontend Code Splitting

Use `React.lazy()` for pages not on the critical path:
- `AdminPanel` — admin-only, never loaded by regular users
- `MissionMode` — only used by Interview-Prepper persona
- `Profile` — not on the critical path

Keep in main bundle (core experience):
- `StudyDashboard`, `CardViewer`, `DailyReview`
- `Analyze`, `Results`, `Rewrite`
- `LandingPage`, `LoginPage`, `Pricing`

## API Contract

No new endpoints. Existing endpoints gain rate limiting headers:
- `X-RateLimit-Limit` — max requests in window
- `X-RateLimit-Remaining` — requests remaining
- `X-RateLimit-Reset` — window reset timestamp

## Data Model Changes

None.

## Acceptance Criteria

- [x] AC-1: `slowapi` is in requirements.txt.
- [x] AC-2: Rate limiter middleware attached to FastAPI app.
- [x] AC-3: Auth endpoints limited to 10 req/min per IP.
- [x] AC-4: Admin generate endpoint limited to 5 req/min per IP.
- [x] AC-5: Default rate limit is 100 req/min per IP.
- [x] AC-6: `test_rate_limit_returns_429` passes.
- [x] AC-7: AdminPanel, MissionMode, Profile use `React.lazy()`.
- [x] AC-8: `npx tsc --noEmit` passes.
- [x] AC-9: `npx vitest run` passes.
- [x] AC-10: All existing backend tests pass.

## Edge Cases

- Rate limit storage is in-memory (per process). Behind a load balancer with
  multiple workers, each worker tracks independently. For stricter enforcement,
  upgrade to Redis-backed storage (out of scope).
- `React.lazy()` requires `<Suspense>` — a minimal loading spinner is shown
  while chunks download.

## Dependencies

- Phase 0 deploy (FastAPI on Railway) — completed.
- Phase 1 auth + payments routes — completed.

## Out of Scope

- Redis-backed rate limit storage (multi-worker coordination).
- Per-user (JWT-based) rate limiting — IP-based is sufficient for Phase 4.
- Lighthouse CI integration.
- Image optimization / CDN setup.
