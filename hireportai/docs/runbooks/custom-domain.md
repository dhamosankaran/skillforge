# Custom Domain Setup Runbook

## Overview

SkillForge uses two services that need custom domains:
- **Frontend** (Vercel): `skillforge.app`
- **Backend** (Railway): `api.skillforge.app`

SSL is automatic on both platforms via Let's Encrypt.

---

## 1. DNS Records

Add these records at your domain registrar (e.g., Cloudflare, Namecheap, Google Domains):

| Type  | Name               | Value                          | TTL  | Purpose         |
|-------|--------------------|--------------------------------|------|-----------------|
| CNAME | `@` or root        | `cname.vercel-dns.com`         | 3600 | Frontend        |
| CNAME | `www`              | `cname.vercel-dns.com`         | 3600 | www redirect    |
| CNAME | `api`              | `<your-railway-domain>.up.railway.app` | 3600 | Backend API     |

> **Note:** Some registrars don't support CNAME on the root domain (`@`).
> In that case, use an **ALIAS** or **ANAME** record, or use Vercel's
> recommended **A records**:
> - `76.76.21.21` (Vercel's anycast IP)

### Getting the Railway Domain

1. Railway Dashboard → SkillForge backend service → **Settings** → **Networking**.
2. Under **Public Networking**, copy the `*.up.railway.app` domain.
3. Click **Custom Domain** → enter `api.skillforge.app` → Railway provides
   the CNAME target.

### Setting Up in Vercel

1. Vercel Dashboard → SkillForge project → **Settings** → **Domains**.
2. Add `skillforge.app` → Vercel provides the CNAME/A record values.
3. Add `www.skillforge.app` → configure redirect to `skillforge.app`.

---

## 2. SSL Verification

SSL is provisioned automatically by both platforms. After DNS propagation
(typically 5-30 minutes, up to 48 hours):

```bash
# Verify frontend SSL
curl -I https://skillforge.app 2>&1 | grep -E "HTTP|server|strict"
# Expected: HTTP/2 200, server: Vercel

# Verify backend SSL
curl -I https://api.skillforge.app/health 2>&1 | grep -E "HTTP|server"
# Expected: HTTP/1.1 200 OK

# Check certificate details
echo | openssl s_client -connect skillforge.app:443 2>/dev/null | \
  openssl x509 -noout -dates -subject
# Expected: valid dates, subject=CN=skillforge.app
```

---

## 3. Environment Variable Updates

After the domain is live, update these configurations:

### 3a. Railway Environment Variables

| Variable | Current Value | New Value |
|----------|--------------|-----------|
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:5199` | `http://localhost:5173,http://localhost:5199,https://skillforge.app` |
| `FRONTEND_URL` | `http://localhost:5199` | `https://skillforge.app` |

### 3b. Vercel Environment Variables

| Variable | Value |
|----------|-------|
| `VITE_API_BASE_URL` | `https://api.skillforge.app` |

### 3c. Stripe Dashboard

1. Go to **Developers** → **Webhooks**.
2. Update (or create new) webhook endpoint URL:
   - **From:** `https://<railway-auto-domain>.up.railway.app/api/v1/payments/webhook`
   - **To:** `https://api.skillforge.app/api/v1/payments/webhook`
3. Copy the new webhook signing secret → update `STRIPE_WEBHOOK_SECRET` in Railway.

### 3d. Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services** → **Credentials**.
2. Select the OAuth 2.0 Client ID used by SkillForge.
3. Under **Authorized JavaScript origins**, add:
   - `https://skillforge.app`
4. Under **Authorized redirect URIs**, add:
   - `https://skillforge.app`
   - `https://skillforge.app/login`
5. Click **Save**.

### 3e. PostHog

1. Go to [PostHog](https://us.posthog.com) → **Settings** → **Project Settings**.
2. Under **Authorized URLs**, add:
   - `https://skillforge.app`
3. This allows the PostHog toolbar and session replay to work on the custom domain.

### 3f. Sentry

1. Go to [Sentry](https://sentry.io) → **Settings** → **Projects** → SkillForge.
2. Under **Allowed Domains**, add:
   - `skillforge.app`
   - `api.skillforge.app`

---

## 4. Verification

```bash
# Frontend loads
curl -s -o /dev/null -w "%{http_code}" https://skillforge.app
# Expected: 200

# Backend health check
curl -s https://api.skillforge.app/health | jq .
# Expected: {"status": "healthy", "service": "hireport-ai"}

# CORS works (preflight)
curl -s -X OPTIONS https://api.skillforge.app/api/v1/auth/me \
  -H "Origin: https://skillforge.app" \
  -H "Access-Control-Request-Method: GET" \
  -I 2>&1 | grep -i "access-control"
# Expected: access-control-allow-origin: https://skillforge.app

# Google OAuth works
# Open https://skillforge.app → click "Sign in with Google" → should redirect properly

# Stripe checkout works
# Sign in → trigger paywall → verify checkout URL uses correct success/cancel URLs
```

---

## DNS Propagation Check

If DNS isn't resolving yet:

```bash
# Check propagation
dig skillforge.app +short
dig api.skillforge.app +short

# Or use a global propagation checker:
# https://dnschecker.org/#CNAME/skillforge.app
```

---

## Rollback

If the custom domain causes issues:
1. Revert `ALLOWED_ORIGINS` and `FRONTEND_URL` in Railway.
2. Revert `VITE_API_BASE_URL` in Vercel.
3. The Railway auto-domain (`*.up.railway.app`) remains active as a fallback.
