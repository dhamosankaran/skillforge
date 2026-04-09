# SkillForge — Local Setup & Prerequisites Guide

> **Run this guide once before touching any code.**
> Covers: system requirements, third-party accounts, API keys, local services, project scaffold, security, git hygiene, and troubleshooting.

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

Before starting, make sure every item below is installed and at the correct version. Run each command and compare output.

### System Requirements

```bash
# ── Operating System ──
sw_vers                              # macOS 15+ (or any Linux)

# ── Languages ──
python3 --version                    # 3.13+ (REQUIRED — asyncpg needs 3.10+, we target 3.13)
node --version                       # 20+ (LTS — don't use 21/22 odd-numbered)
npm --version                        # 10+

# ── Package Managers ──
brew --version                       # Homebrew (macOS only)
pip --version                        # comes with Python

# ── Databases ──
pg_config --version                  # PostgreSQL 16+
redis-server --version               # Redis 7+

# ── Tools ──
git --version                        # 2.40+
claude --version                     # Claude Code (latest)
```

### What to install if missing

```bash
# Python 3.13 (macOS)
brew install python@3.13

# Node 20 LTS (macOS)
brew install node@20

# PostgreSQL 16
brew install postgresql@16
brew link postgresql@16 --force

# pgvector extension
brew install pgvector
# If brew install doesn't work, see Troubleshooting §12.1

# Redis
brew install redis

# Claude Code
npm install -g @anthropic-ai/claude-code
```

---

## 2. Third-Party Accounts & API Keys

You need accounts on 7 services. Set them up **before writing any code** — waiting until the moment you need a key breaks your flow.

### Phase 0 (needed immediately)

| Service | What you need | How to get it | Free tier? |
|---------|--------------|---------------|------------|
| **GitHub** | Repository + GitHub Actions | github.com → create repo `hireportai` | Yes |
| **Google Cloud** | OAuth Client ID + Secret | console.cloud.google.com → APIs & Services → Credentials → OAuth 2.0 Client | Yes |
| **Railway** | Account + project | railway.app → sign up with GitHub | $5/mo hobby plan (needed for deploy) |
| **Vercel** | Account + project | vercel.com → sign up with GitHub | Yes (hobby tier) |

### Phase 1 (needed by Week 3)

| Service | What you need | How to get it | Free tier? |
|---------|--------------|---------------|------------|
| **Stripe** | Secret key + Webhook secret + Price ID | dashboard.stripe.com → sign up → Developers → API keys. Create a Product ($49/mo) → copy Price ID | Yes (test mode) |
| **Google AI Studio** | Gemini API key | aistudio.google.com → Get API key | Yes (free tier generous) |
| **PostHog** | Project API key + Host URL | us.posthog.com → sign up → Project Settings → API key | Yes (1M events/mo) |

### Phase 2 (needed by Week 7)

| Service | What you need | How to get it | Free tier? |
|---------|--------------|---------------|------------|
| **Resend** | API key | resend.com → sign up → API Keys → Create | Yes (100 emails/day) |

### Phase 4 (needed by Week 13)

| Service | What you need | How to get it | Free tier? |
|---------|--------------|---------------|------------|
| **Sentry** | DSN (frontend + backend) | sentry.io → sign up → Create Project (Python + React) | Yes (5K events/mo) |
| **Domain Registrar** | skillforge.app (or similar) | namecheap.com, cloudflare.com, etc. | ~$12/year |

### Step-by-Step: Google OAuth Setup

This is the most error-prone setup. Follow exactly:

```
1. Go to console.cloud.google.com
2. Create project: "SkillForge"
3. APIs & Services → OAuth consent screen
   - User Type: External
   - App name: "SkillForge"
   - Authorized domains: localhost, your-vercel-url, your-domain
   - Scopes: email, profile, openid
4. APIs & Services → Credentials → Create OAuth 2.0 Client ID
   - Application type: Web application
   - Authorized JavaScript origins:
     - http://localhost:5199
     - https://your-vercel-app.vercel.app
   - Authorized redirect URIs:
     - http://localhost:5199/auth/callback
     - https://your-vercel-app.vercel.app/auth/callback
5. Copy: Client ID → VITE_GOOGLE_CLIENT_ID
6. Copy: Client Secret → GOOGLE_CLIENT_SECRET (backend env)
```

> [!WARNING]
> Google OAuth will silently fail if your redirect URIs don't **exactly** match — including trailing slashes. Double-check after deploy.

### Step-by-Step: Stripe Setup

```
1. Go to dashboard.stripe.com → sign up
2. Toggle to "Test mode" (top right)
3. Developers → API keys:
   - Copy "Secret key" → STRIPE_SECRET_KEY (starts with sk_test_)
   - Copy "Publishable key" → VITE_STRIPE_KEY (starts with pk_test_)
4. Products → Add Product:
   - Name: "SkillForge Pro"
   - Price: $49.00 / month, recurring
   - Copy the Price ID → STRIPE_PRO_PRICE_ID (starts with price_)
5. Developers → Webhooks → Add endpoint:
   - URL: https://your-railway-url/api/v1/payments/webhook
   - Events: checkout.session.completed, customer.subscription.deleted, invoice.payment_failed
   - Copy "Signing secret" → STRIPE_WEBHOOK_SECRET (starts with whsec_)
```

> [!NOTE]
> For local development, use Stripe CLI to forward webhooks:
> ```bash
> brew install stripe/stripe-cli/stripe
> stripe login
> stripe listen --forward-to localhost:8000/api/v1/payments/webhook
> # Copy the webhook signing secret it prints
> ```

### Step-by-Step: PostHog Setup

```
1. Go to us.posthog.com → sign up
2. Create project: "SkillForge"
3. Project Settings → Project API key → copy
4. Your host is: https://us.i.posthog.com
5. Backend: POSTHOG_API_KEY=phc_...
6. Frontend: VITE_POSTHOG_KEY=phc_... , VITE_POSTHOG_HOST=https://us.i.posthog.com
```

---

## 3. Local System Setup

### 3.1 Start PostgreSQL

```bash
# Start service
brew services start postgresql@16

# Verify
pg_isready
# Expected: "localhost:5432 - accepting connections"

# Create databases
createdb hireport
createdb hireport_test

# Install extensions
psql -d hireport -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d hireport -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
psql -d hireport_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d hireport_test -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"

# Create dedicated user
psql -d postgres -c "CREATE USER hireport WITH PASSWORD 'dev_password';"
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE hireport TO hireport;"
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE hireport_test TO hireport;"

# Grant schema privileges (PostgreSQL 15+ requires this)
psql -d hireport -c "GRANT ALL ON SCHEMA public TO hireport;"
psql -d hireport_test -c "GRANT ALL ON SCHEMA public TO hireport;"

# Verify connection with the new user
psql -U hireport -d hireport -c "SELECT 1;"
# Expected: returns 1
```

> [!WARNING]
> **PostgreSQL 15+ changed default privileges.** If you see `permission denied for schema public`, run the schema grant commands above. This trips up almost everyone.

> [!WARNING]
> **The macOS pgvector Gotcha**: If `CREATE EXTENSION vector` fails with `could not open extension control file`, Homebrew installed the `.so` in the wrong directory. Fix:
> ```bash
> git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git /tmp/pgvector
> cd /tmp/pgvector
> make PG_CONFIG=$(which pg_config)
> make install PG_CONFIG=$(which pg_config)
> brew services restart postgresql@16
> psql -d hireport -c "CREATE EXTENSION vector;"
> ```

### 3.2 Start Redis

```bash
brew services start redis

# Verify
redis-cli ping
# Expected: "PONG"

# Check version
redis-cli INFO server | grep redis_version
# Expected: 7.x
```

### 3.3 Verify All Services

```bash
# Run this any time to check everything is healthy
pg_isready && echo "✅ PostgreSQL" || echo "❌ PostgreSQL"
redis-cli ping | grep -q PONG && echo "✅ Redis" || echo "❌ Redis"
psql -U hireport -d hireport -c "SELECT extname FROM pg_extension WHERE extname='vector';" | grep -q vector && echo "✅ pgvector" || echo "❌ pgvector"
```

---

## 4. Project Scaffold

```bash
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai

# ── Spec directories ──
mkdir -p docs/specs/{phase-0,phase-1,phase-2,phase-3,phase-4}

# ── Agent skills + workflows ──
mkdir -p .agent/{skills,workflows}

# ── Backend ──
mkdir -p hirelens-backend/{scripts,tests}
mkdir -p hirelens-backend/app/{api/routes,core,models,schemas,services,templates}
mkdir -p hirelens-backend/alembic/versions

# ── Frontend ──
mkdir -p hirelens-frontend/tests
mkdir -p hirelens-frontend/src/{components/{study,profile,mission,onboarding,settings},pages,context,hooks,services,types}

# ── CI/CD ──
mkdir -p .github/workflows

# ── Claude Code config ──
mkdir -p .claude

# ── Verify structure ──
find . -type d -maxdepth 4 | head -40
```

---

## 5. Backend Setup

```bash
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai/hirelens-backend

# ── Python virtual environment ──
python3 -m venv venv
source venv/bin/activate

# ── Install dependencies ──
pip install -r requirements.txt

# ── Install SkillForge-specific packages ──
pip install asyncpg pgvector py-fsrs redis posthog stripe resend slowapi

# ── Install dev/test dependencies ──
pip install pytest pytest-asyncio httpx pytest-cov

# ── Download spaCy model (for ATS scanner) ──
python -m spacy download en_core_web_sm

# ── Freeze deps for reproducibility ──
pip freeze > requirements-lock.txt
```

### Backend .env File

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
# AUTH (Phase 0)
# ═══════════════════════════════════════════
JWT_SECRET_KEY=CHANGE_ME_run_openssl_rand_hex_32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# ═══════════════════════════════════════════
# LLM (Phase 1)
# ═══════════════════════════════════════════
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-2.0-flash

# ═══════════════════════════════════════════
# STRIPE (Phase 1)
# ═══════════════════════════════════════════
STRIPE_SECRET_KEY=sk_test_CHANGE_ME
STRIPE_WEBHOOK_SECRET=whsec_CHANGE_ME
STRIPE_PRO_PRICE_ID=price_CHANGE_ME

# ═══════════════════════════════════════════
# ANALYTICS (Phase 1)
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
> Paste the output into JWT_SECRET_KEY. Do NOT ship with the placeholder.

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
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai/hirelens-frontend

# ── Install existing dependencies ──
npm install

# ── Install SkillForge-specific packages ──
npm install recharts@latest @tanstack/react-query zustand posthog-js framer-motion stripe @stripe/stripe-js

# ── Install dev/test dependencies ──
npm install -D vitest @testing-library/react @testing-library/jest-dom @vitest/coverage-v8 jsdom @types/react @types/react-dom
```

### Frontend .env File

```bash
cat > .env << 'ENVEOF'
# API
VITE_API_BASE_URL=

# Auth (Phase 0)
VITE_GOOGLE_CLIENT_ID=your-google-client-id

# Analytics (Phase 1)
VITE_POSTHOG_KEY=phc_CHANGE_ME
VITE_POSTHOG_HOST=https://us.i.posthog.com

# Stripe (Phase 1)
VITE_STRIPE_KEY=pk_test_CHANGE_ME

# Monitoring (Phase 4 — leave blank until needed)
VITE_SENTRY_DSN=
ENVEOF
```

> [!NOTE]
> `VITE_API_BASE_URL` is intentionally empty for local dev — the frontend will proxy to `localhost:8000`. Set it to your Railway URL for production (done via Vercel dashboard, not this file).

### Verify Frontend Starts

```bash
npm run dev -- --port 5199
# Visit: http://localhost:5199 → app loads
```

---

## 7. Skeleton Deploy (Phase 0)

Do this **before writing any feature code**. The goal is a blank app running in production so every subsequent push auto-deploys.

### 7.1 Railway (Backend)

```
1. Go to railway.app → New Project → Deploy from GitHub repo
2. Select your `hireportai` repo
3. Set root directory to: hirelens-backend
4. Add PostgreSQL plugin → Railway auto-sets DATABASE_URL
5. Add Redis plugin → Railway auto-sets REDIS_URL
6. Settings → Build:
   - Builder: Nixpacks (auto-detected for Python)
7. Settings → Deploy:
   - Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   - Release command: alembic upgrade head
8. Variables → add all backend env vars from §11 below
9. Enable pgvector on the Railway PostgreSQL:
   - Connect via Railway's psql shell
   - CREATE EXTENSION IF NOT EXISTS vector;

Verify: curl https://your-railway-url.railway.app/health → 200
```

### 7.2 Vercel (Frontend)

```
1. Go to vercel.com → Import Git Repository → select hireportai
2. Set root directory to: hirelens-frontend
3. Framework: Vite
4. Environment variables:
   - VITE_API_BASE_URL=https://your-railway-url.railway.app
   - VITE_GOOGLE_CLIENT_ID=...
   - VITE_POSTHOG_KEY=...
   - VITE_POSTHOG_HOST=...
5. Deploy

Verify: visit https://your-app.vercel.app → frontend loads
```

### 7.3 Post-Deploy Checklist

```bash
# Backend
curl -s https://your-railway-url.railway.app/health
# → {"status": "ok"}

# Frontend → Backend (CORS check)
# Open browser console on your Vercel URL, run:
# fetch('https://your-railway-url.railway.app/health').then(r => r.json()).then(console.log)
# → Should print {"status": "ok"}, NOT a CORS error

# Update Google OAuth redirect URIs to include your Vercel URL
# Update Stripe webhook URL to point to Railway URL
```

### 7.4 CI/CD Pipeline

After deploy, create the GitHub Actions pipeline:

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
      JWT_SECRET_KEY: test-secret-key-for-ci-only-not-real
      JWT_ALGORITHM: HS256
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: "pip"
      - run: |
          cd hirelens-backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx pytest-cov
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
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgresql+asyncpg://hireport:test_password@localhost:5432/hireport_test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: "pip"
      - run: |
          cd hirelens-backend
          pip install -r requirements.txt
          alembic upgrade head
          alembic downgrade -1
          alembic upgrade head
CIEOF

git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions pipeline"
git push
```

---

## 8. Security Best Practices

### 8.1 Secrets Management

```
DO:
✅ Generate JWT_SECRET_KEY with: openssl rand -hex 32
✅ Use Stripe TEST mode keys during development (sk_test_, pk_test_)
✅ Store all secrets in Railway/Vercel dashboards for production
✅ Use a .env file locally (NEVER committed to git)
✅ Use separate API keys for dev vs production

DON'T:
❌ Commit .env files to git
❌ Hardcode secrets in Python/TypeScript code
❌ Use the same JWT_SECRET_KEY in dev and production
❌ Share Stripe LIVE keys until launch day
❌ Put secrets in GitHub Actions yaml — use GitHub Secrets
```

### 8.2 .gitignore

```bash
cat >> .gitignore << 'EOF'

# ── Secrets ──
.env
.env.local
.env.production
*.pem

# ── Python ──
venv/
__pycache__/
*.pyc
.pytest_cache/
htmlcov/
.coverage

# ── Node ──
node_modules/
dist/
.vercel/

# ── Database ──
*.db
*.sqlite3

# ── IDE ──
.vscode/settings.json
.idea/

# ── OS ──
.DS_Store
Thumbs.db
EOF
```

### 8.3 .env.example (Commit This)

```bash
# Create a template showing required vars WITHOUT real values
cat > hirelens-backend/.env.example << 'EOF'
DATABASE_URL=postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport
TEST_DATABASE_URL=postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport_test
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=run-openssl-rand-hex-32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
STRIPE_SECRET_KEY=sk_test_
STRIPE_WEBHOOK_SECRET=whsec_
STRIPE_PRO_PRICE_ID=price_
POSTHOG_API_KEY=phc_
POSTHOG_HOST=https://us.i.posthog.com
RESEND_API_KEY=
SENTRY_DSN=
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5199
EOF

cat > hirelens-frontend/.env.example << 'EOF'
VITE_API_BASE_URL=
VITE_GOOGLE_CLIENT_ID=
VITE_POSTHOG_KEY=phc_
VITE_POSTHOG_HOST=https://us.i.posthog.com
VITE_STRIPE_KEY=pk_test_
VITE_SENTRY_DSN=
EOF
```

### 8.4 CORS Policy

```python
# In app/main.py — read origins from env, never hardcode production URLs
import os

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5199").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 8.5 Database Security

```
LOCAL DEV:
- dev_password is fine for local PostgreSQL
- Test database uses the same credentials (acceptable for dev)

PRODUCTION (Railway):
- Railway auto-generates strong credentials
- DATABASE_URL is set automatically — never override it
- Enable SSL: add ?sslmode=require to the connection string if needed
- Railway manages backups — verify backup schedule in dashboard
```

---

## 9. Git & Branch Strategy

### 9.1 Repository Setup

```bash
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai

# Initialize if not already
git init
git remote add origin git@github.com:YOUR_USERNAME/hireportai.git

# Initial commit with scaffold
git add -A
git commit -m "chore: initial project scaffold"
git push -u origin main
```

### 9.2 Branch Convention

```
main                              ← production (auto-deploys)
├── feature/p0-01-auth-unify      ← Phase 0, spec 01
├── feature/p1-05-fsrs-daily      ← Phase 1, spec 05
├── feature/p2-14-mission-mode    ← Phase 2, spec 14
└── fix/p1-card-search-timeout    ← Bug fixes reference the phase
```

### 9.3 Commit Convention

```
type(scope): description

Types: feat, fix, refactor, test, docs, ci, chore
Scope: auth, cards, study, payments, gamification, mission, email, admin, ui, analytics

Examples:
  feat(study): add FSRS daily review endpoint
  fix(cards): handle empty embedding in search
  test(payments): add Stripe webhook integration tests
  ci: add migration rollback job
  docs: update spec #05 status to Done
  chore: phase 1 complete
```

### 9.4 Solo Developer Workflow

Since you're a solo dev, you have two options:

**Option A — Direct to main (recommended for speed):**
```bash
# Work on main, push when tests pass
git add -A
git commit -m "feat(study): add FSRS service"
git push origin main
# CI runs → auto-deploys if green
```

**Option B — Feature branches (recommended if you want review checkpoints):**
```bash
git checkout -b feature/p1-05-fsrs-daily
# ... work ...
git add -A && git commit -m "feat(study): add FSRS service"
git push origin feature/p1-05-fsrs-daily
# Create PR → CI runs → merge → auto-deploys
git checkout main && git pull
```

> For solo dev, Option A is faster and CI still protects you. Switch to Option B when you add a second developer or want to batch-review Claude Code's output before it hits production.

---

## 10. Development Workflow

### 10.1 Daily Startup

```bash
# ── Start services ──
brew services start postgresql@16
brew services start redis

# ── Verify ──
pg_isready && redis-cli ping

# ── Open 3 terminal tabs ──

# Tab 1: Backend
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai/hirelens-backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Tab 2: Frontend
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai/hirelens-frontend
npm run dev -- --port 5199

# Tab 3: Claude Code
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai
claude
```

### 10.2 Daily Shutdown

```bash
brew services stop postgresql@16
brew services stop redis
```

### 10.3 Before Each Claude Code Session

Always start with:
```
Read AGENTS.md. Read docs/specs/phase-N/NN-feature.md.
```

This loads the right context. Without it, Claude Code will guess conventions and get them wrong.

### 10.4 After Each Claude Code Session

Always end with:
```
Run python -m pytest tests/ -v --tb=short. Run npx vitest run. If all green, git add -A && git commit -m "type(scope): description" && git push.
```

### 10.5 Weekly Maintenance

```bash
# ── Update dependencies ──
cd hirelens-backend && source venv/bin/activate
pip install --upgrade pip
pip list --outdated

cd hirelens-frontend
npm outdated

# ── Run full test suite with coverage ──
cd hirelens-backend
python -m pytest tests/ --cov=app --cov-report=term-missing

cd hirelens-frontend
npx vitest run --coverage

# ── Check production health ──
curl -s https://your-production-url/health

# ── Check PostHog for event flow ──
# Visit us.posthog.com → Live Events → verify events are coming in

# ── Check Sentry for unresolved errors (Phase 4+) ──
# Visit sentry.io → Issues → resolve or triage
```

---

## 11. Environment Variable Reference

Complete list of every env var used across all phases, when it's needed, and where it's set.

### Backend (hirelens-backend/.env locally, Railway dashboard for production)

| Variable | Phase | Required? | Example | Notes |
|----------|-------|-----------|---------|-------|
| `DATABASE_URL` | 0 | Yes | `postgresql+asyncpg://...` | Railway auto-sets in production |
| `TEST_DATABASE_URL` | 0 | Local only | `postgresql+asyncpg://...hireport_test` | Not needed in production |
| `REDIS_URL` | 0 | Yes | `redis://localhost:6379` | Railway auto-sets |
| `JWT_SECRET_KEY` | 0 | Yes | (32-byte hex) | `openssl rand -hex 32` |
| `JWT_ALGORITHM` | 0 | Yes | `HS256` | Don't change |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 0 | Yes | `30` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 0 | Yes | `30` | |
| `GOOGLE_CLIENT_ID` | 0 | Yes | `xxx.apps.googleusercontent.com` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | 0 | Yes | `GOCSPX-...` | From Google Cloud Console |
| `GEMINI_API_KEY` | 1 | Yes | `AI...` | From Google AI Studio |
| `GEMINI_MODEL` | 1 | Yes | `gemini-2.0-flash` | |
| `STRIPE_SECRET_KEY` | 1 | Yes | `sk_test_...` | Stripe dashboard |
| `STRIPE_WEBHOOK_SECRET` | 1 | Yes | `whsec_...` | Stripe webhook config |
| `STRIPE_PRO_PRICE_ID` | 1 | Yes | `price_...` | From Stripe product |
| `POSTHOG_API_KEY` | 1 | Yes | `phc_...` | PostHog project settings |
| `POSTHOG_HOST` | 1 | Yes | `https://us.i.posthog.com` | |
| `RESEND_API_KEY` | 2 | Phase 2+ | `re_...` | resend.com |
| `SENTRY_DSN` | 4 | Phase 4+ | `https://...@sentry.io/...` | sentry.io |
| `ALLOWED_ORIGINS` | 0 | Yes | `http://localhost:5199,...` | Comma-separated |

### Frontend (hirelens-frontend/.env locally, Vercel dashboard for production)

| Variable | Phase | Required? | Example | Notes |
|----------|-------|-----------|---------|-------|
| `VITE_API_BASE_URL` | 0 | Prod only | `https://your-app.railway.app` | Empty for local dev |
| `VITE_GOOGLE_CLIENT_ID` | 0 | Yes | `xxx.apps.googleusercontent.com` | Same as backend |
| `VITE_POSTHOG_KEY` | 1 | Yes | `phc_...` | Same key as backend |
| `VITE_POSTHOG_HOST` | 1 | Yes | `https://us.i.posthog.com` | |
| `VITE_STRIPE_KEY` | 1 | Yes | `pk_test_...` | Publishable key (safe for frontend) |
| `VITE_SENTRY_DSN` | 4 | Phase 4+ | `https://...@sentry.io/...` | |

---

## 12. Troubleshooting

### 12.1 pgvector: "could not open extension control file"

Homebrew installed pgvector into the wrong directory.

```bash
# Build from source
git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git /tmp/pgvector
cd /tmp/pgvector
make PG_CONFIG=$(which pg_config)
make install PG_CONFIG=$(which pg_config)
brew services restart postgresql@16
psql -d hireport -c "CREATE EXTENSION vector;"
```

### 12.2 PostgreSQL: "permission denied for schema public"

PostgreSQL 15+ changed default schema permissions.

```bash
psql -d hireport -c "GRANT ALL ON SCHEMA public TO hireport;"
psql -d hireport_test -c "GRANT ALL ON SCHEMA public TO hireport;"
```

### 12.3 PostgreSQL: "role hireport does not exist"

You forgot to create the user.

```bash
psql -d postgres -c "CREATE USER hireport WITH PASSWORD 'dev_password';"
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE hireport TO hireport;"
```

### 12.4 asyncpg: "connection refused" in tests

PostgreSQL isn't running, or TEST_DATABASE_URL is wrong.

```bash
pg_isready                          # Is PG running?
echo $TEST_DATABASE_URL             # Is the URL correct?
psql $TEST_DATABASE_URL -c "SELECT 1;"  # Can you connect?
```

### 12.5 CORS errors in browser

The backend ALLOWED_ORIGINS doesn't include the frontend URL.

```bash
# Check what's set
grep ALLOWED_ORIGINS hirelens-backend/.env

# Must include the exact frontend URL (no trailing slash)
# Local: http://localhost:5199
# Production: https://your-app.vercel.app
```

### 12.6 Stripe webhook: "No signatures found matching the expected signature"

You're using the wrong webhook secret, or the secret is for a different endpoint.

```bash
# Local dev: use Stripe CLI
stripe listen --forward-to localhost:8000/api/v1/payments/webhook
# Copy the whsec_ secret it prints → STRIPE_WEBHOOK_SECRET

# Production: check Stripe dashboard → Developers → Webhooks → your endpoint → Signing secret
```

### 12.7 Google OAuth: "redirect_uri_mismatch"

The redirect URI in Google Cloud Console doesn't exactly match what your app sends.

```
Check: console.cloud.google.com → Credentials → your OAuth client
Authorized redirect URIs must include EXACTLY:
  http://localhost:5199/auth/callback        (local)
  https://your-app.vercel.app/auth/callback  (production)

Common mistakes:
  - Missing trailing slash (or extra trailing slash)
  - http vs https mismatch
  - Wrong port number
```

### 12.8 Railway: "alembic upgrade head" fails on deploy

Usually a missing env var or wrong DATABASE_URL format.

```
Railway provides: postgresql://user:pass@host:port/db
asyncpg needs:    postgresql+asyncpg://user:pass@host:port/db

Fix in config.py:
  url = os.getenv("DATABASE_URL", "")
  if url.startswith("postgresql://"):
      url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
```

### 12.9 Tests pass locally, fail in CI

Usually a missing env var in GitHub Actions or a different database state.

```
Check .github/workflows/ci.yml:
  - Does the PostgreSQL service have the right POSTGRES_USER/PASSWORD?
  - Do env vars match what tests expect?
  - Does the test database have pgvector installed? (use pgvector/pgvector:pg16 image)
```

### 12.10 Frontend: "process is not defined" or "global is not defined"

Some npm packages (posthog-js, stripe) reference Node.js globals that don't exist in the browser.

```javascript
// In vite.config.ts, add:
define: {
  global: 'globalThis',
}
```

---

## 13. Health Check Script

Save this as `scripts/healthcheck.sh` and run it any time to verify your entire dev environment:

```bash
#!/bin/bash
set -e

echo "═══════════════════════════════════════════"
echo "  SkillForge Health Check"
echo "═══════════════════════════════════════════"

# Colors
G='\033[0;32m'; R='\033[0;31m'; Y='\033[0;33m'; N='\033[0m'
pass() { echo -e "${G}✅ $1${N}"; }
fail() { echo -e "${R}❌ $1${N}"; FAILED=1; }
warn() { echo -e "${Y}⚠️  $1${N}"; }
FAILED=0

echo ""
echo "── System ──"
python3 --version 2>/dev/null | grep -q "3.1[3-9]" && pass "Python 3.13+" || fail "Python 3.13+ required"
node --version 2>/dev/null | grep -q "v2[0-9]" && pass "Node 20+" || fail "Node 20+ required"

echo ""
echo "── Services ──"
pg_isready -q 2>/dev/null && pass "PostgreSQL running" || fail "PostgreSQL not running (brew services start postgresql@16)"
redis-cli ping 2>/dev/null | grep -q PONG && pass "Redis running" || fail "Redis not running (brew services start redis)"

echo ""
echo "── Database ──"
psql -U hireport -d hireport -c "SELECT 1;" >/dev/null 2>&1 && pass "hireport DB accessible" || fail "Cannot connect to hireport DB"
psql -U hireport -d hireport_test -c "SELECT 1;" >/dev/null 2>&1 && pass "hireport_test DB accessible" || fail "Cannot connect to hireport_test DB"
psql -U hireport -d hireport -c "SELECT extname FROM pg_extension WHERE extname='vector';" 2>/dev/null | grep -q vector && pass "pgvector extension installed" || fail "pgvector not installed"

echo ""
echo "── Backend ──"
if [ -f hirelens-backend/venv/bin/activate ]; then
  pass "Python venv exists"
else
  fail "No venv (cd hirelens-backend && python3 -m venv venv)"
fi
if [ -f hirelens-backend/.env ]; then
  pass ".env file exists"
  grep -q "CHANGE_ME\|your-" hirelens-backend/.env && warn "Some .env values are still placeholders" || pass "No placeholder values found"
else
  fail "No .env file"
fi

echo ""
echo "── Frontend ──"
if [ -d hirelens-frontend/node_modules ]; then
  pass "node_modules exists"
else
  fail "No node_modules (cd hirelens-frontend && npm install)"
fi
if [ -f hirelens-frontend/.env ]; then
  pass ".env file exists"
else
  fail "No .env file"
fi

echo ""
echo "── Git ──"
git remote -v 2>/dev/null | grep -q origin && pass "Git remote configured" || warn "No git remote set"
if [ -f .github/workflows/ci.yml ]; then
  pass "CI/CD pipeline exists"
else
  warn "No CI/CD pipeline yet (create in Phase 0)"
fi

echo ""
echo "── Files ──"
[ -f AGENTS.md ] && pass "AGENTS.md exists" || warn "No AGENTS.md"
[ -f CLAUDE.md ] && pass "CLAUDE.md exists" || warn "No CLAUDE.md"
[ -d docs/specs ] && pass "Spec directory exists" || warn "No docs/specs/"
[ -d .agent/skills ] && pass "Skills directory exists" || warn "No .agent/skills/"

echo ""
if [ $FAILED -eq 0 ]; then
  echo -e "${G}All checks passed! Ready to build.${N}"
else
  echo -e "${R}Some checks failed. Fix the issues above before proceeding.${N}"
fi
```

Make it executable:
```bash
chmod +x scripts/healthcheck.sh
./scripts/healthcheck.sh
```

---

*Run the health check script after setup. Every check should be green before you start Phase 0 prompts.*
