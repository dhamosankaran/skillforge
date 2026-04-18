---
description: Auth hardening, rate limiting, CORS, request size, webhook idempotency, abuse prevention
---
# Security Skill

## Overview
SkillForge ships with layered abuse prevention: IP-bound registration
caps, per-endpoint rate limits, CORS allowlist, request size caps,
short-lived JWTs with refresh tokens, and idempotent Stripe webhook
handling. Most of this is enforced at the middleware layer so routes
stay clean.

## Registration IP Blocking (Spec #25)

- **Model:** `app/models/registration_log.py` → table `registration_logs`
- **Key columns:** `id`, `user_id`, `ip_address` (indexed), `google_email`, `created_at`
- **Rule:** Max **2 accounts per IP per 30 days**
- **Enforced in:** `POST /api/v1/auth/google` (`app/api/v1/routes/auth.py`)
- **Logic:**
  1. When a **new** Google user signs up, count `registration_logs`
     rows where `ip_address = <client_ip>` and
     `created_at > now() - 30 days`.
  2. If count ≥ 2 → return `403` and fire
     `registration_blocked` PostHog event with `{ip_hash, existing_accounts}`.
  3. Otherwise insert a new `registration_logs` row alongside the user.
- Admin audit view: `GET /api/v1/admin/registration-logs`.

## Rate Limiting

- **Library:** `slowapi` (backed by in-process limiter, Redis in prod)
- **Config:** `app/core/rate_limit.py`
- **Key function:** `get_remote_address` (per client IP)
- **Limits:**

| Scope | Limit |
|-------|-------|
| Global default | **100 req/min** per IP |
| Auth endpoints (`/auth/google`, `/auth/refresh`, `/auth/logout`, `/auth/me`) + `PATCH /users/me/persona` | **10 req/min** |
| LLM-backed admin endpoint (`POST /admin/cards/generate`) | **5 req/min** |

- Returns `429 Too Many Requests` with `Retry-After` header.
- Exposes `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

## CORS

- **Env var:** `ALLOWED_ORIGINS` (comma-separated)
- **Parsed in:** `app/core/config.py` → `Settings.allowed_origins_list`
- **Applied in:** `app/main.py` via `CORSMiddleware`
- `allow_credentials=True`, all methods and headers permitted.
- Dev default: `http://localhost:5173,http://localhost:5199`.
  Prod: set explicit Vercel domain(s).

## Request Size Limit

- **Env var:** `MAX_UPLOAD_SIZE_MB` (default `5`)
- Custom HTTP middleware in `app/main.py` rejects any request whose
  `Content-Length` exceeds `max_upload_size_bytes` with HTTP `413`
  before route handlers run. Protects resume upload endpoints from
  memory DoS.

## JWT Authentication

- **Scheme:** Google OAuth → backend mints an **access token** +
  **refresh token** pair.
- **Env vars:** `JWT_SECRET_KEY`, `JWT_ALGORITHM` (default `HS256`),
  `ACCESS_TOKEN_EXPIRE_MINUTES` (default `30`),
  `REFRESH_TOKEN_EXPIRE_DAYS` (default `7`).
- **Refresh:** `POST /api/v1/auth/refresh` exchanges a valid refresh
  token for a new access token. Clients store both in memory/storage.
- **Logout:** stateless — client discards tokens. No server-side
  session revocation (acceptable given short access token TTL).
- **Protection:** every non-public route uses
  `Depends(get_current_user)`; admin routes use `Depends(require_admin)`.

## Stripe Webhook Idempotency (Spec #22)

- **Model:** `app/models/stripe_event.py` → table `stripe_events`
  with `id` (Stripe event id, e.g. `evt_...`) as **primary key**.
- **Enforced in:** `payment_service.handle_webhook()`
  (`app/services/payment_service.py`).
- **Flow:**
  1. Verify Stripe signature using `stripe_webhook_secret`.
  2. Parse event id; `SELECT FROM stripe_events WHERE id = :id`.
  3. If row exists → return `200 {status: "duplicate"}` and stop.
  4. Otherwise insert row, then process the event body
     (`checkout.session.completed`, `customer.subscription.deleted`).
  5. Commit in a single transaction so a retry after a crash is safe.
- Prevents double upgrades / double refunds on Stripe retries.

## Quick Audit Checklist
- [ ] New public route? Add a slowapi limit override.
- [ ] New auth-bearing route? `Depends(get_current_user)`.
- [ ] New webhook handler? Idempotency table + signature verification.
- [ ] New env var? Add to `Settings` **and** to `AGENTS.md` env table.
- [ ] New upload endpoint? Check payload against `max_upload_size_bytes`.
