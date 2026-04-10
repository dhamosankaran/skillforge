# Backup & Restore Runbook

## Overview

SkillForge uses PostgreSQL 16 on Railway. Railway provides automatic daily
backups for Pro/Team plans. This runbook covers manual backup creation,
restoration, and post-restore verification.

---

## 1. Creating a Backup

### Option A: Railway Dashboard (recommended)

1. Open [Railway Dashboard](https://railway.app) → select the **SkillForge** project.
2. Click the **PostgreSQL** service.
3. Go to the **Backups** tab.
4. Click **Create Backup** → wait for completion (typically < 1 minute).
5. Note the backup timestamp for reference.

### Option B: Railway CLI

```bash
# Install Railway CLI if not already installed
npm install -g @railway/cli

# Login and link project
railway login
railway link

# Create a manual backup via plugin
railway run pg_dump --format=custom --no-owner --no-acl \
  -f backup_$(date +%Y%m%d_%H%M%S).dump
```

### Option C: Direct pg_dump (requires DATABASE_URL)

```bash
# Get the connection string from Railway dashboard → Variables → DATABASE_URL
export DATABASE_URL="postgresql://..."

# Create compressed custom-format backup
pg_dump "$DATABASE_URL" --format=custom --no-owner --no-acl \
  -f skillforge_$(date +%Y%m%d_%H%M%S).dump

# Verify the dump is valid
pg_restore --list skillforge_*.dump | head -20
```

**Backup naming convention:** `skillforge_YYYYMMDD_HHMMSS.dump`

---

## 2. Restoring from Backup

### Pre-restore Checklist

- [ ] Notify the team that the app will be temporarily unavailable.
- [ ] Confirm which backup to restore (check timestamp).
- [ ] If restoring to production, take a fresh backup first (safety net).

### Restore Steps

#### Option A: Railway Dashboard

1. Go to **PostgreSQL** service → **Backups** tab.
2. Find the target backup by timestamp.
3. Click **Restore** → confirm.
4. Wait for restore to complete (progress shown in dashboard).

#### Option B: CLI Restore

```bash
# Restore from custom-format dump
# WARNING: This drops and recreates all tables!
pg_restore --clean --if-exists --no-owner --no-acl \
  -d "$DATABASE_URL" skillforge_YYYYMMDD_HHMMSS.dump
```

### Post-restore: Run Pending Migrations

Backups may predate recent Alembic migrations. Always run:

```bash
cd hirelens-backend
railway run alembic upgrade head
```

---

## 3. Verification After Restore

Run these checks immediately after any restore:

### 3a. API Health Check

```bash
curl -s https://api.skillforge.app/health | jq .
# Expected: {"status": "healthy", "service": "hireport-ai"}
```

### 3b. Database Connectivity

```bash
railway run python -c "
from sqlalchemy import create_engine, text
from app.core.config import get_settings
e = create_engine(get_settings().database_url.replace('+asyncpg', ''))
with e.connect() as c:
    r = c.execute(text('SELECT count(*) FROM users'))
    print(f'Users: {r.scalar()}')
    r = c.execute(text('SELECT count(*) FROM cards'))
    print(f'Cards: {r.scalar()}')
    r = c.execute(text('SELECT count(*) FROM subscriptions'))
    print(f'Subscriptions: {r.scalar()}')
print('DB connectivity: OK')
"
```

### 3c. Auth Flow

1. Open https://skillforge.app in an incognito window.
2. Sign in with Google → verify redirect to `/analyze`.
3. Check `/profile` shows correct subscription plan.

### 3d. Stripe Sync

1. Open Stripe Dashboard → Developers → Webhooks.
2. Send a test webhook event.
3. Verify it returns 200 (check Railway logs).

### 3e. Alembic Migration State

```bash
railway run alembic current
# Should show the latest migration revision
railway run alembic check
# Should report "No new upgrade operations detected"
```

---

## Automated Backups (Railway)

Railway Pro/Team plans include automatic daily backups with 7-day retention.
Verify this is enabled:

1. Railway Dashboard → PostgreSQL service → **Settings**.
2. Confirm **Automatic Backups** is toggled on.
3. Retention: 7 days (default).

---

## Emergency Contacts

- Railway status: https://status.railway.app
- Railway support: support@railway.app
- Stripe status: https://status.stripe.com
