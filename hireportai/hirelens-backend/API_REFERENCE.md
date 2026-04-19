# HirePort AI — API Reference

## Base URLs

| Environment | Base URL |
|-------------|----------|
| Development | `http://localhost:8000` |
| Legacy API  | `/api/*` (no auth required) |
| v1 API      | `/api/v1/*` (auth required for most endpoints) |

---

## Authentication Flow

### 1. Google Sign-In → Backend JWT

```
Frontend: User clicks Google Sign-In
         → @react-oauth/google returns credential (Google ID token)
         → POST /api/v1/auth/google {credential: "eyJ..."}
         → Backend validates with Google, upserts user, returns JWT pair

Backend Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {"id": "uuid", "email": "...", "name": "...", "avatar_url": "..."}
}
```

### 2. Authenticated Requests

```bash
curl -H "Authorization: Bearer <access_token>" http://localhost:8000/api/v1/auth/me
```

### 3. Token Refresh

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'
```

---

## Auth Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/google` | No | Exchange Google credential for JWT pair |
| POST | `/api/v1/auth/refresh` | No | Refresh access token |
| POST | `/api/v1/auth/logout` | Yes | Logout (client discards tokens) |
| GET  | `/api/v1/auth/me` | Yes | Get current user + subscription info |

---

## Billing Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/billing/create-checkout-session` | Yes | Create Stripe Checkout → returns URL |
| POST | `/api/v1/billing/webhook` | No* | Handle Stripe events (*signature verified) |
| GET  | `/api/v1/billing/subscription` | Yes | Current plan, status, usage |
| POST | `/api/v1/billing/cancel` | Yes | Cancel subscription at period end |
| GET  | `/api/v1/billing/portal` | Yes | Stripe Customer Portal URL |

### Payment Flow

```
1. User clicks "Upgrade to Pro" on /pricing
2. Frontend: POST /api/v1/billing/create-checkout-session {"plan": "pro"}
3. Backend creates Stripe Checkout session, returns {url: "https://checkout.stripe.com/..."}
4. Frontend redirects user to Stripe Checkout
5. User completes payment on Stripe
6. Stripe sends webhook → POST /api/v1/billing/webhook
7. Backend activates subscription in database
8. Stripe redirects user to /payment/success
```

### Stripe CLI Testing

```bash
# Install Stripe CLI: https://stripe.com/docs/stripe-cli
stripe login
stripe listen --forward-to localhost:8000/api/v1/billing/webhook
# In another terminal, trigger test events:
stripe trigger checkout.session.completed
stripe trigger invoice.payment_succeeded
stripe trigger invoice.payment_failed
stripe trigger customer.subscription.deleted
```

---

## Resume Optimizer Endpoints (Enterprise)

| Method | Path | Auth | Plan | Description |
|--------|------|------|------|-------------|
| POST | `/api/v1/resume/upload` | Yes | Any | Upload PDF/DOCX → parse and store |
| POST | `/api/v1/resume/{id}/optimize` | Yes | Enterprise | LLM-powered ATS optimization |
| GET  | `/api/v1/resume/{id}` | Yes | Any | Get original + optimized content |
| GET  | `/api/v1/resume/{id}/diff` | Yes | Any | Unified diff view |

### Example: Upload + Optimize

```bash
# Upload
curl -X POST http://localhost:8000/api/v1/resume/upload \
  -H "Authorization: Bearer <token>" \
  -F "resume_file=@resume.pdf"

# Optimize
curl -X POST http://localhost:8000/api/v1/resume/<resume_id>/optimize \
  -H "Authorization: Bearer <token>" \
  -F "job_description=We are looking for a senior software engineer..."
```

---

## Legacy Analysis Endpoints (No Auth)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/analyze` | Full ATS analysis (resume file + JD) |
| POST | `/api/compare` | Compare two resumes vs same JD |
| POST | `/api/rewrite` | AI resume rewrite |
| POST | `/api/cover-letter` | Cover letter generation |
| POST | `/api/interview-prep` | Interview questions + STAR framework |

These same endpoints are also available at `/api/v1/*`. Tracker CRUD is
authenticated-only at `/api/v1/tracker` (GET/POST/PATCH/DELETE).

---

## Plan Limits

| Feature | Free | Pro ($9.99/mo) | Enterprise ($29.99/mo) |
|---------|------|----------------|------------------------|
| ATS analyses/month | 3 | Unlimited | Unlimited |
| Resume rewrite | No | Yes | Yes |
| Cover letter | No | Yes | Yes |
| Interview prep | 5/month | Unlimited | Unlimited |
| Claude optimizer | No | No | Yes |

---

## Database

- **Dev**: SQLite at `data/hirelens.db`
- **Prod**: Set `DATABASE_URL=postgresql+asyncpg://user:pass@host/db`
- **Migrations**: `alembic upgrade head` / `alembic downgrade -1`

### Tables

| Table | Purpose |
|-------|---------|
| `users` | Google OAuth user accounts |
| `subscriptions` | Stripe subscription state per user |
| `payments` | Payment history (Stripe payment intents) |
| `resumes` | Stored resume content (original + optimized) |
| `usage_logs` | Feature usage tracking per user |
| `tracker_applications_v2` | Job applications (SQLAlchemy-backed) |
| `tracker_applications` | Legacy tracker (raw aiosqlite, kept for compat) |

---

## LLM Provider Configuration

Set `LLM_PROVIDER` in `.env`:

| Value | Provider | API Key Env Var |
|-------|----------|-----------------|
| `gemini` (default) | Google Gemini | `GEMINI_API_KEY` |
| `claude` | Anthropic Claude | `ANTHROPIC_API_KEY` |

Both providers implement the same interface — switch without code changes.
