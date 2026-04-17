# SkillForge — Local Setup & Prerequisites Guide

> **Run this guide once before touching any code.**
> Covers: system requirements, third-party accounts, API keys, local services, project scaffold,
> security, git hygiene, and troubleshooting.
>
> **v2.1 updates**: Added LLM router env vars (LLM_FAST_MODEL, LLM_REASONING_MODEL,
> LLM_FAST_PROVIDER, LLM_REASONING_PROVIDER), Anthropic + OpenAI as optional providers,
> STRIPE_PRO_PRICE_ID_INR for geo pricing, anthropic + openai + react-markdown packages,
> LLM fallback troubleshooting entry, updated health check script.

---

## Table of Contents

1. [Pre-Flight Checklist](#1-pre-flight-checklist)
2. [Third-Party Accounts & API Keys](#2-third-party-accounts--api-keys)
3. [Local System Setup](#3-local-system-setup)
4. [Project Scaffold](#4-project-scaffold)
5. [Backend Setup](#5-backend-setup)
6. [Frontend Setup](#6-frontend-setup)
7. [Skeleton Deploy (Phase 0)](#7-skeleton-deploy)
8. [Security Best Practices](#8-security-best-practices)
9. [Git & Branch Strategy](#9-git--branch-strategy)
10. [Development Workflow](#10-development-workflow)
11. [Environment Variable Reference](#11-environment-variable-reference)
12. [Troubleshooting](#12-troubleshooting)
13. [Health Check Script](#13-health-check-script)

---

## 1. Pre-Flight Checklist

Before starting, make sure every item below is installed and at the correct version.

### System Requirements

```bash
sw_vers                              # macOS 15+ (or any Linux)
python3 --version                    # 3.13+ REQUIRED
node --version                       # 20+ (LTS)
npm --version                        # 10+
brew --version                       # Homebrew (macOS only)
pg_config --version                  # PostgreSQL 16+
redis-server --version               # Redis 7+
git --version                        # 2.40+
claude --version                     # Claude Code (latest)
```

### Install if missing

```bash
brew install python@3.13
brew install node@20
brew install postgresql@16
brew link postgresql@16 --force
brew install pgvector
brew install redis
npm install -g @anthropic-ai/claude-code
```

---

## 2. Third-Party Accounts & API Keys

Set these up **before writing any code**.

### Phase 0 (needed immediately)

| Service | What you need | How to get it | Free tier? |
|---------|--------------|---------------|------------|
| Google Cloud | Client ID + Secret for OAuth | console.cloud.google.com → Credentials → OAuth 2.0 | Yes |
| GitHub | Repo + Actions enabled | github.com | Yes |
| Railway | Account + project | railway.app | $5/mo hobby |
| Vercel | Account linked to GitHub | vercel.com | Free |

**Google OAuth setup:**
1. console.cloud.google.com → New project → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID (Web application)
3. Authorized origins: `http://localhost:5199`, `http://localhost:5173`, `https://theskillsforge.dev`
4. Redirect URIs: `http://localhost:8000/api/v1/auth/google/callback`, `https://your-railway-url/api/v1/auth/google/callback`, `https://theskillsforge.dev/api/v1/auth/google/callback`
5. Copy Client ID + Client Secret → backend `.env`

### Phase 1 (needed before implementing payments/analytics)

| Service | What you need | Notes |
|---------|--------------|-------|
| Stripe | Secret key + Webhook secret + 2 Price IDs | stripe.com — create USD ($49/mo) AND INR (₹999/mo) prices |
| PostHog | Project API key | us.posthog.com — free up to 1M events/mo |
| Google AI Studio | Gemini API key | aistudio.google.com — required as LLM fallback |
| **Anthropic** (optional) | API key | console.anthropic.com — optional LLM provider |
| **OpenAI** (optional) | API key | platform.openai.com — optional LLM provider |
| Cloudflare R2 | Bucket + API keys | For resume file storage. Free tier: 10GB |

**Stripe setup (important — create BOTH prices):**
1. stripe.com → Products → Create product "SkillForge Pro"
2. Add price: $49.00/month recurring → copy price ID → `STRIPE_PRO_PRICE_ID`
3. Add another price: ₹999.00/month recurring → copy price ID → `STRIPE_PRO_PRICE_ID_INR`
4. Developers → API Keys → copy Secret key → `STRIPE_SECRET_KEY`
5. Webhooks → Add endpoint → your Railway URL + `/api/v1/payments/webhook`
   Events: `checkout.session.completed`, `customer.subscription.deleted`, `invoice.payment_failed`
6. Copy Signing secret → `STRIPE_WEBHOOK_SECRET`

**LLM providers (Anthropic + OpenAI are OPTIONAL):**
- The LLM router defaults to Gemini if neither is configured.
- Set `LLM_FAST_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=...` to use Claude for fast tasks.
- Set `LLM_REASONING_PROVIDER=openai` and `OPENAI_API_KEY=...` to use GPT-4 for reasoning tasks.
- If keys are not set, the router logs a warning and falls back to Gemini automatically.

### Phase 2 (needed for email)

| Service | What you need | Notes |
|---------|--------------|-------|
| Resend | API key | resend.com — free tier: 3,000 emails/month |

### Phase 4 (needed for monitoring)

| Service | What you need | Notes |
|---------|--------------|-------|
| Sentry | DSN | sentry.io — free tier: 5K errors/month |

---

## 3. Local System Setup

### 3.1 Start PostgreSQL

```bash
brew services start postgresql@16
pg_isready  # → "accepting connections"

# Create databases
createdb hireport
createdb hireport_test

# Create pgvector extension
psql -d hireport -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d hireport -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
psql -d hireport_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d hireport_test -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"

# Create dedicated DB user
psql -d postgres -c "CREATE USER hireport WITH PASSWORD 'dev_password';"
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE hireport TO hireport;"
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE hireport_test TO hireport;"

# PostgreSQL 15+ requires explicit schema grants
psql -d hireport -c "GRANT ALL ON SCHEMA public TO hireport;"
psql -d hireport_test -c "GRANT ALL ON SCHEMA public TO hireport;"
```

> [!WARNING]
> **If you see `permission denied for schema public`**, run the schema grant commands above.

> [!WARNING]
> **macOS pgvector gotcha**: If `CREATE EXTENSION vector` fails:
> ```bash
> git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git /tmp/pgvector
> cd /tmp/pgvector && make PG_CONFIG=$(which pg_config) && make install PG_CONFIG=$(which pg_config)
> brew services restart postgresql@16
> ```

### 3.2 Start Redis

```bash
brew services start redis
redis-cli ping  # → "PONG"
```

### 3.3 Verify All Services

```bash
pg_isready && echo "✅ PostgreSQL" || echo "❌ PostgreSQL"
redis-cli ping | grep -q PONG && echo "✅ Redis" || echo "❌ Redis"
psql -U hireport -d hireport -c "SELECT extname FROM pg_extension WHERE extname='vector';" 2>/dev/null | grep -q vector && echo "✅ pgvector" || echo "❌ pgvector"
```

---

## 4. Project Scaffold

```bash
cd /path/to/hireportai  # your project root

# Spec directories
mkdir -p docs/specs/{phase-0,phase-1,phase-2,phase-3,phase-4}

# Agent skills + workflows
mkdir -p .agent/{skills,workflows}

# Backend
mkdir -p hirelens-backend/{scripts,tests}
mkdir -p hirelens-backend/app/{api/routes,core,models,schemas,services,templates}
mkdir -p hirelens-backend/alembic/versions

# Frontend
mkdir -p hirelens-frontend/tests
mkdir -p hirelens-frontend/src/{components/{study,profile,mission,onboarding,settings},pages,context,hooks,services,types,styles}

# CI/CD
mkdir -p .github/workflows

# Claude Code config
mkdir -p .claude

# Verify
find . -type d -maxdepth 4 | head -40
```

---

## 5. Backend Setup

```bash
cd hirelens-backend

# Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install SkillForge-specific packages
pip install asyncpg pgvector py-fsrs redis posthog stripe resend slowapi

# Install LLM providers (all three — they're optional at runtime)
pip install google-genai anthropic openai

# Install dev/test dependencies
pip install pytest pytest-asyncio httpx pytest-cov

# Download spaCy model (for ATS scanner)
python -m spacy download en_core_web_sm

# Freeze for reproducibility
pip freeze > requirements-lock.txt
```

### Backend `.env` File

```bash
cat > .env << 'ENVEOF'
# ═══════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════
DATABASE_URL=postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport
TEST_DATABASE_URL=postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport_test

# ═══════════════════════════════════════════
# REDIS
# ═══════════════════════════════════════════
REDIS_URL=redis://localhost:6379

# ═══════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════
JWT_SECRET_KEY=CHANGE_ME_run_openssl_rand_hex_32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# ═══════════════════════════════════════════
# LLM — MULTI-MODEL ROUTER
# ═══════════════════════════════════════════
# Google (required — used as fallback if other providers not configured)
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-2.0-flash

# Fast model configuration (used for embeddings, rewrites, card drafts)
LLM_FAST_MODEL=gemini-2.0-flash
LLM_FAST_PROVIDER=google                 # google | anthropic | openai

# Reasoning model configuration (used for ATS scoring, gap analysis)
LLM_REASONING_MODEL=gemini-2.5-pro
LLM_REASONING_PROVIDER=google            # google | anthropic | openai

# Anthropic (optional — set to use Claude as LLM provider)
ANTHROPIC_API_KEY=

# OpenAI (optional — set to use GPT-4 as LLM provider)
OPENAI_API_KEY=

# ═══════════════════════════════════════════
# STRIPE
# ═══════════════════════════════════════════
STRIPE_SECRET_KEY=sk_test_CHANGE_ME
STRIPE_WEBHOOK_SECRET=whsec_CHANGE_ME
STRIPE_PRO_PRICE_ID=price_CHANGE_ME       # USD $49/mo
STRIPE_PRO_PRICE_ID_INR=price_CHANGE_ME   # INR ₹999/mo

# ═══════════════════════════════════════════
# ANALYTICS
# ═══════════════════════════════════════════
POSTHOG_API_KEY=phc_CHANGE_ME
POSTHOG_HOST=https://us.i.posthog.com

# ═══════════════════════════════════════════
# EMAIL (Phase 2 — leave blank until needed)
# ═══════════════════════════════════════════
RESEND_API_KEY=

# ═══════════════════════════════════════════
# MONITORING (Phase 4 — leave blank until needed)
# ═══════════════════════════════════════════
SENTRY_DSN=

# ═══════════════════════════════════════════
# CORS
# ═══════════════════════════════════════════
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5199
ENVEOF
```

> [!IMPORTANT]
> **Generate a real JWT secret immediately:**
> ```bash
> openssl rand -hex 32
> ```
> Paste into JWT_SECRET_KEY. Never ship with the placeholder.

### Backend pytest Configuration

```bash
cat > pytest.ini << 'EOF'
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
testpaths = tests
EOF
```

### Verify Backend Starts

```bash
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
# Visit: http://localhost:8000/docs → Swagger UI should load
# Visit: http://localhost:8000/health → {"status": "ok"}
```

---

## 6. Frontend Setup

```bash
cd hirelens-frontend

# Install existing dependencies
npm install

# Install SkillForge-specific packages
npm install recharts@latest @tanstack/react-query zustand posthog-js framer-motion stripe @stripe/stripe-js react-markdown

# Install dev/test dependencies
npm install -D vitest @testing-library/react @testing-library/jest-dom @vitest/coverage-v8 jsdom @types/react @types/react-dom
```

### Frontend `.env` File

```bash
cat > .env << 'ENVEOF'
# API
VITE_API_BASE_URL=

# Auth
VITE_GOOGLE_CLIENT_ID=your-google-client-id

# Analytics
VITE_POSTHOG_KEY=phc_CHANGE_ME
VITE_POSTHOG_HOST=https://us.i.posthog.com

# Stripe
VITE_STRIPE_KEY=pk_test_CHANGE_ME

# Monitoring (Phase 4 — leave blank until needed)
VITE_SENTRY_DSN=
ENVEOF
```

> [!NOTE]
> `VITE_API_BASE_URL` is intentionally empty for local dev — the frontend proxies to `localhost:8000`.
> Set it to your Railway URL for production via the Vercel dashboard.

### Verify Frontend Starts

```bash
npm run dev -- --port 5199
# Visit: http://localhost:5199 → app loads
```

---

## 7. Skeleton Deploy (Phase 0)

Do this **before writing any feature code**.

### 7.1 Railway (Backend)

```
1. railway.app → New Project → Deploy from GitHub repo
2. Select your hireportai repo, root directory: hirelens-backend
3. Add PostgreSQL plugin (Railway auto-sets DATABASE_URL)
4. Add Redis plugin (Railway auto-sets REDIS_URL)
5. Enable pgvector: Railway psql shell → CREATE EXTENSION IF NOT EXISTS vector;
6. Settings → Deploy:
   - Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   - Release: alembic upgrade head
7. Variables → add ALL backend env vars from Section 11 below
   (include LLM_FAST_MODEL, LLM_REASONING_MODEL, STRIPE_PRO_PRICE_ID_INR)

Verify: curl https://your-railway-url.railway.app/health → 200
```

### 7.2 Vercel (Frontend)

```
1. vercel.com → Import Git Repository → select hireportai
2. Root directory: hirelens-frontend, Framework: Vite
3. Environment variables:
   - VITE_API_BASE_URL=https://your-railway-url.railway.app
   - VITE_GOOGLE_CLIENT_ID=...
   - VITE_POSTHOG_KEY=...
   - VITE_POSTHOG_HOST=...
   - VITE_STRIPE_KEY=...
4. Deploy

Verify: visit https://your-app.vercel.app → frontend loads
```

### 7.3 CI/CD Pipeline

```bash
cat > .github/workflows/ci.yml << 'CIEOF'
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: hireport_test
          POSTGRES_USER: hireport
          POSTGRES_PASSWORD: test_password
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgresql+asyncpg://hireport:test_password@localhost:5432/hireport_test
      TEST_DATABASE_URL: postgresql+asyncpg://hireport:test_password@localhost:5432/hireport_test
      JWT_SECRET_KEY: test-secret-key-for-ci-only
      JWT_ALGORITHM: HS256
      LLM_FAST_PROVIDER: google
      LLM_REASONING_PROVIDER: google
      GEMINI_API_KEY: test-key-for-ci
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: "pip"
      - run: |
          cd hirelens-backend
          pip install -r requirements.txt
          pip install asyncpg pgvector py-fsrs pytest-asyncio httpx anthropic openai google-genai
          python -m pytest tests/ -v --tb=short --cov=app

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: hirelens-frontend/package-lock.json
      - run: |
          cd hirelens-frontend
          npm ci
          npx vitest run --coverage

  migration-rollback:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: hireport_test
          POSTGRES_USER: hireport
          POSTGRES_PASSWORD: test_password
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: |
          cd hirelens-backend
          pip install -r requirements.txt
          pip install asyncpg pgvector
          alembic upgrade head
          alembic downgrade -1
          alembic upgrade head
CIEOF
```

---

## 8. Security Best Practices

### .gitignore

```bash
cat > .gitignore << 'EOF'
# Environment
.env
.env.*
!.env.example

# Python
__pycache__/
*.pyc
venv/
.venv/
*.egg-info/

# Node
node_modules/
dist/
.next/

# DB
*.sqlite
*.db

# Keys
*.pem
*.key
*.p12

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/settings.json
.idea/

# Test artifacts
.coverage
htmlcov/
.pytest_cache/
EOF
```

### .env.example Files

Always commit `.env.example` to git so teammates know what keys are needed:

```bash
# hirelens-backend/.env.example
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/hireport
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/hireport_test
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=  # generate: openssl rand -hex 32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GEMINI_API_KEY=
LLM_FAST_MODEL=gemini-2.0-flash
LLM_FAST_PROVIDER=google
LLM_REASONING_MODEL=gemini-2.5-pro
LLM_REASONING_PROVIDER=google
ANTHROPIC_API_KEY=  # optional
OPENAI_API_KEY=     # optional
STRIPE_SECRET_KEY=sk_test_
STRIPE_WEBHOOK_SECRET=whsec_
STRIPE_PRO_PRICE_ID=price_
STRIPE_PRO_PRICE_ID_INR=price_
POSTHOG_API_KEY=phc_
POSTHOG_HOST=https://us.i.posthog.com
RESEND_API_KEY=
SENTRY_DSN=
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5199
```

---

## 9. Git & Branch Strategy

For a solo developer, direct-to-main is recommended. CI still protects you.

```bash
# Commit convention
git commit -m "feat(study): add FSRS daily review endpoint"
git commit -m "fix(payments): geo detection falls back to USD on failure"
git commit -m "chore: phase 2 complete"

# Types: feat, fix, chore, docs, test, refactor, ci
# Scopes: auth, study, cards, payments, gamification, mission, email, admin, ui, security, llm
```

---

## 10. Development Workflow

### Morning Startup

```bash
brew services start postgresql@16
brew services start redis
cd /path/to/hireportai

# Tab 1: Backend
cd hirelens-backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Tab 2: Frontend
cd hirelens-frontend && npm run dev -- --port 5199

# Tab 3: Claude Code
claude
# Start with: "Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md."
```

### After Each Claude Code Session

```
Run python -m pytest tests/ -v --tb=short.
Run npx vitest run.
If all green: git add -A && git commit -m "type(scope): description" && git push.
Update SESSION-STATE.md with what was done and the next slice.
```

---

## 11. Environment Variable Reference

### Backend (hirelens-backend/.env locally, Railway dashboard for production)

| Variable | Phase | Required? | Example | Notes |
|----------|-------|-----------|---------|-------|
| `DATABASE_URL` | 0 | Yes | `postgresql+asyncpg://...` | Railway auto-sets |
| `TEST_DATABASE_URL` | 0 | Local only | `...hireport_test` | Not needed in production |
| `REDIS_URL` | 0 | Yes | `redis://localhost:6379` | Railway auto-sets |
| `JWT_SECRET_KEY` | 0 | Yes | (32-byte hex) | `openssl rand -hex 32` |
| `JWT_ALGORITHM` | 0 | Yes | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 0 | Yes | `30` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 0 | Yes | `30` | |
| `GOOGLE_CLIENT_ID` | 0 | Yes | `xxx.apps.googleusercontent.com` | |
| `GOOGLE_CLIENT_SECRET` | 0 | Yes | `GOCSPX-...` | |
| `GEMINI_API_KEY` | 1 | **Yes** | `AI...` | Required — LLM fallback |
| `GEMINI_MODEL` | 1 | Yes | `gemini-2.0-flash` | Legacy alias |
| `LLM_FAST_MODEL` | 1 | Yes | `gemini-2.0-flash` | Fast task model |
| `LLM_FAST_PROVIDER` | 1 | Yes | `google` | `google` \| `anthropic` \| `openai` |
| `LLM_REASONING_MODEL` | 1 | Yes | `gemini-2.5-pro` | Reasoning task model |
| `LLM_REASONING_PROVIDER` | 1 | Yes | `google` | `google` \| `anthropic` \| `openai` |
| `ANTHROPIC_API_KEY` | 1 | No | `sk-ant-...` | Optional — leave blank to use Gemini |
| `OPENAI_API_KEY` | 1 | No | `sk-...` | Optional — leave blank to use Gemini |
| `STRIPE_SECRET_KEY` | 1 | Yes | `sk_test_...` | |
| `STRIPE_WEBHOOK_SECRET` | 1 | Yes | `whsec_...` | |
| `STRIPE_PRO_PRICE_ID` | 1 | Yes | `price_...` | USD $49/mo |
| `STRIPE_PRO_PRICE_ID_INR` | 1 | Yes | `price_...` | INR ₹999/mo |
| `POSTHOG_API_KEY` | 1 | Yes | `phc_...` | |
| `POSTHOG_HOST` | 1 | Yes | `https://us.i.posthog.com` | |
| `RESEND_API_KEY` | 2 | Phase 2+ | `re_...` | |
| `SENTRY_DSN` | 4 | Phase 4+ | `https://...@sentry.io/...` | |
| `ALLOWED_ORIGINS` | 0 | Yes | `http://localhost:5199,...` | |

### Frontend (hirelens-frontend/.env locally, Vercel dashboard for production)

| Variable | Phase | Required? | Example | Notes |
|----------|-------|-----------|---------|-------|
| `VITE_API_BASE_URL` | 0 | Prod only | `https://xxx.railway.app` | Empty for local dev |
| `VITE_GOOGLE_CLIENT_ID` | 0 | Yes | `xxx.apps.googleusercontent.com` | |
| `VITE_POSTHOG_KEY` | 1 | Yes | `phc_...` | |
| `VITE_POSTHOG_HOST` | 1 | Yes | `https://us.i.posthog.com` | |
| `VITE_STRIPE_KEY` | 1 | Yes | `pk_test_...` | |
| `VITE_SENTRY_DSN` | 4 | Phase 4+ | `https://...@sentry.io/...` | |

---

## 12. Troubleshooting

### 12.1 pgvector extension not found

```bash
# Error: could not open extension control file
git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git /tmp/pgvector
cd /tmp/pgvector
make PG_CONFIG=$(which pg_config)
make install PG_CONFIG=$(which pg_config)
brew services restart postgresql@16
psql -d hireport -c "CREATE EXTENSION vector;"
```

### 12.2 `permission denied for schema public` (PostgreSQL 15+)

```bash
psql -d hireport -c "GRANT ALL ON SCHEMA public TO hireport;"
psql -d hireport_test -c "GRANT ALL ON SCHEMA public TO hireport;"
```

### 12.3 CORS errors in browser

Symptom: `Access-Control-Allow-Origin` missing in browser console.

```bash
# Check ALLOWED_ORIGINS in backend .env
echo $ALLOWED_ORIGINS
# Should include: http://localhost:5199 (or your Vite port)

# Check that app/main.py reads from env:
# origins = os.environ.get("ALLOWED_ORIGINS", "").split(",")
```

### 12.4 Stripe webhook signature failure

```bash
# Must use raw body for webhook verification
# In FastAPI: use Request.body() before parsing JSON
# Check STRIPE_WEBHOOK_SECRET matches the signing secret in Stripe dashboard (not the API key)

# For local testing:
stripe listen --forward-to localhost:8000/api/v1/payments/webhook
# Use the signing secret it prints, not the dashboard one
```

### 12.5 Railway DATABASE_URL format

Railway provides `postgresql://` not `postgresql+asyncpg://`:

```python
# In app/core/config.py:
database_url = os.environ.get("DATABASE_URL", "")
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
```

### 12.6 Google OAuth redirect URI mismatch

```
Error: redirect_uri_mismatch

Fix: In Google Cloud Console, add EVERY URL you're using:
- http://localhost:5199 (frontend dev)
- http://localhost:8000/api/v1/auth/google/callback (backend dev)
- https://your-app.vercel.app (production FE)
- https://your-railway-url.railway.app/api/v1/auth/google/callback (production BE)
- https://theskillsforge.dev/api/v1/auth/google/callback (custom domain)
```

### 12.7 Vite `global is not defined`

```bash
# In vite.config.ts add:
define: {
  global: 'globalThis',
}
```

### 12.8 LLM router falls back to Gemini unexpectedly

Symptom: Log shows "LLM provider key not set for anthropic, falling back to google/Gemini"

```bash
# Check that ANTHROPIC_API_KEY (or OPENAI_API_KEY) is set in your .env
cat hirelens-backend/.env | grep ANTHROPIC_API_KEY
# If blank, that's expected — Gemini is the fallback
# To use Anthropic: set ANTHROPIC_API_KEY=sk-ant-xxx AND LLM_FAST_PROVIDER=anthropic
```

> This is NOT an error. The fallback is intentional. Only investigate if you expect
> a specific provider and want to confirm it's being used.

### 12.9 Stripe geo-pricing always shows USD

Symptom: Indian users see USD price.

```bash
# Check STRIPE_PRO_PRICE_ID_INR is set in .env
# Check app/services/geo_service.py — test with a known Indian IP
# ip-api.com free tier has rate limits: 45 req/min. Add caching if needed.
# On localhost, your IP is likely not Indian — test with mock in development
```

### 12.10 Migration autogenerate misses Vector columns

pgvector's `Vector` type isn't auto-detected by Alembic:

```python
# In alembic/env.py, add:
from pgvector.sqlalchemy import Vector

# In the migration, manually add:
sa.Column('embedding', Vector(1536), nullable=True)
```

---

## 13. Health Check Script

Save as `scripts/health_check.sh` and run from project root:

```bash
#!/bin/bash

echo "═══════════════════════════════════════"
echo "  SkillForge Health Check"
echo "═══════════════════════════════════════"

# System versions
echo ""
echo "── System ──"
python3 --version 2>&1 | grep -q "3.13" && echo "✅ Python 3.13+" || echo "❌ Python 3.13 required"
node --version 2>&1 | grep -q "v20\|v21\|v22" && echo "✅ Node 20+" || echo "❌ Node 20 required"

# Services
echo ""
echo "── Services ──"
pg_isready &>/dev/null && echo "✅ PostgreSQL running" || echo "❌ PostgreSQL not running — run: brew services start postgresql@16"
redis-cli ping 2>/dev/null | grep -q PONG && echo "✅ Redis running" || echo "❌ Redis not running — run: brew services start redis"
psql -U hireport -d hireport -c "SELECT 1" &>/dev/null && echo "✅ DB user 'hireport' works" || echo "❌ DB user issue — check createdb and GRANT commands"
psql -U hireport -d hireport -c "SELECT extname FROM pg_extension WHERE extname='vector';" 2>/dev/null | grep -q vector && echo "✅ pgvector installed" || echo "❌ pgvector missing — see Section 12.1"

# Backend
echo ""
echo "── Backend ──"
[ -f hirelens-backend/venv/bin/activate ] && echo "✅ venv exists" || echo "❌ venv missing — run: python3 -m venv venv"
[ -f hirelens-backend/.env ] && echo "✅ .env exists" || echo "❌ .env missing — copy from .env.example"

# Check required env vars
source hirelens-backend/.env 2>/dev/null || true
check_var() {
  local var_name=$1
  local required=$2
  local value=${!var_name}
  if [ -z "$value" ] || [[ "$value" == *"CHANGE_ME"* ]]; then
    if [ "$required" = "required" ]; then
      echo "❌ $var_name not set (required)"
    else
      echo "⚠️  $var_name not set (optional)"
    fi
  else
    echo "✅ $var_name set"
  fi
}

echo ""
echo "── Required Env Vars ──"
check_var "DATABASE_URL" "required"
check_var "REDIS_URL" "required"
check_var "JWT_SECRET_KEY" "required"
check_var "GOOGLE_CLIENT_ID" "required"
check_var "GEMINI_API_KEY" "required"
check_var "LLM_FAST_MODEL" "required"
check_var "LLM_FAST_PROVIDER" "required"
check_var "LLM_REASONING_MODEL" "required"
check_var "LLM_REASONING_PROVIDER" "required"
check_var "STRIPE_SECRET_KEY" "required"
check_var "STRIPE_WEBHOOK_SECRET" "required"
check_var "STRIPE_PRO_PRICE_ID" "required"
check_var "STRIPE_PRO_PRICE_ID_INR" "required"
check_var "POSTHOG_API_KEY" "required"
check_var "ALLOWED_ORIGINS" "required"

echo ""
echo "── Optional Env Vars ──"
check_var "ANTHROPIC_API_KEY" "optional"
check_var "OPENAI_API_KEY" "optional"
check_var "RESEND_API_KEY" "optional"
check_var "SENTRY_DSN" "optional"

# Frontend
echo ""
echo "── Frontend ──"
[ -f hirelens-frontend/.env ] && echo "✅ frontend .env exists" || echo "❌ frontend .env missing"
[ -d hirelens-frontend/node_modules ] && echo "✅ node_modules exist" || echo "❌ node_modules missing — run: npm install"

# Check react-markdown
[ -d "hirelens-frontend/node_modules/react-markdown" ] && echo "✅ react-markdown installed" || echo "⚠️  react-markdown not installed — run: npm install react-markdown"

# Scaffold files
echo ""
echo "── Agent Files ──"
[ -f AGENTS.md ] && echo "✅ AGENTS.md" || echo "❌ AGENTS.md missing"
[ -f CLAUDE.md ] && echo "✅ CLAUDE.md" || echo "❌ CLAUDE.md missing"
[ -f SESSION-STATE.md ] && echo "✅ SESSION-STATE.md" || echo "❌ SESSION-STATE.md missing — create it!"
[ -f .agent/skills/llm-strategy.md ] && echo "✅ skill: llm-strategy" || echo "❌ skill: llm-strategy missing"
[ -f .agent/skills/security.md ] && echo "✅ skill: security" || echo "❌ skill: security missing"
[ -f .agent/skills/design-system.md ] && echo "✅ skill: design-system" || echo "❌ skill: design-system missing"
[ -f .agent/skills/geo-pricing.md ] && echo "✅ skill: geo-pricing" || echo "❌ skill: geo-pricing missing"

# Git
echo ""
echo "── Git ──"
git remote -v | grep -q origin && echo "✅ git remote set" || echo "❌ git remote missing — add your GitHub repo"
[ -f .github/workflows/ci.yml ] && echo "✅ CI/CD pipeline exists" || echo "❌ CI/CD missing — see Section 7.3"

echo ""
echo "═══════════════════════════════════════"
echo "  Check complete!"
echo "  Any ❌ items must be fixed before starting."
echo "  ⚠️  items are optional and can be left blank."
echo "═══════════════════════════════════════"
```

Run with:
```bash
chmod +x scripts/health_check.sh
./scripts/health_check.sh
```

---

*SkillForge Local Setup Guide v2.1 — Updated with LLM router vars, Anthropic/OpenAI providers, geo pricing (STRIPE_PRO_PRICE_ID_INR), anthropic + openai + react-markdown packages, LLM fallback troubleshooting, and updated health check script.*
