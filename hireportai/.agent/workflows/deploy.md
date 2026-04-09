---
description: "How to deploy frontend to Vercel and backend to Railway"
---

# Deployment

## How It Works
Deployment is NOT a manual step. It happens automatically on every
push to main via GitHub Actions.

## Pipeline: push → test → deploy
1. Push to `main` (or merge PR)
2. GitHub Actions runs: lint → backend tests → frontend tests
3. If all green:
   - Railway auto-deploys backend (detects push, runs migrations)
   - Vercel auto-deploys frontend (detects push, builds)
4. If tests fail: deploy is blocked, PR cannot merge

## Environment Variables
- Production env vars live in Railway and Vercel dashboards
- NEVER commit secrets to code
- Required vars (Railway):
  - `DATABASE_URL` — Railway managed PostgreSQL
  - `REDIS_URL` — Railway managed Redis
  - `JWT_SECRET_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
  - `GEMINI_API_KEY`, `POSTHOG_API_KEY`
  - `RESEND_API_KEY` (Phase 2+)
- Required vars (Vercel):
  - `VITE_API_BASE_URL` — Railway backend URL
  - `VITE_GOOGLE_CLIENT_ID`
  - `VITE_POSTHOG_KEY`

## Database Migrations
Railway runs `alembic upgrade head` as the release command before
starting the new version. If migration fails, deploy rolls back.

## Rollback
- Railway: one-click rollback to previous deployment
- Vercel: one-click rollback to previous deployment
- Database: `alembic downgrade -1` (test downgrade locally first)

## Verifying a Deploy
```bash
curl -s https://yourdomain.com/health    # → {"status": "ok"}
# Check Railway logs for migration output
# Check Vercel deployment logs for build output
# Check PostHog for incoming events
```