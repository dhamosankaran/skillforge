# SkillForge — Master Development Playbook v2.1

> **The CTO/Growth Partner/Architect/VC Guide to Building SkillForge Right**
> *Spec-Driven · Test-First · Agent-Powered · Deploy Continuously · Ship Fast*
>
> **v2.1 changelog**: Added LLM multi-model router, design system + themes, geo-pricing, IP
> registration blocking, free-tier interview limits, tracker auto-populate, persona picker fields,
> card soft-delete, resume rewrite + cover letter fixes, and 4 new skill files. Env var tables
> updated throughout. Post-playbook enhancements section added (Section 9).

---

## Table of Contents

1. [Product Requirements Document (PRD)](#1-product-requirements-document)
2. [Phased Execution Plan](#2-phased-execution-plan)
3. [Spec-Driven Development](#3-spec-driven-development)
4. [AGENTS.md & Skills System](#4-agentsmd--skills-system)
5. [Test-Driven Development Strategy](#5-test-driven-development-strategy)
6. [Claude Code Best Practices](#6-claude-code-best-practices)
7. [Bootstrap Protocol](#7-bootstrap-protocol)
8. [CI/CD & Deployment Pipeline](#8-cicd--deployment-pipeline)
9. [Post-Playbook Enhancements](#9-post-playbook-enhancements)

---

## 1. Product Requirements Document

### 1.1 Problem Statement

Senior/Staff/Principal engineers preparing for $200K+ roles face a fragmented learning landscape: LeetCode for algorithms (wrong audience), Udemy for theory (shallow), and expensive coaching ($300/hr) for behavioral prep. No single platform closes the loop from **"scan resume → find gaps → study cards → re-scan → improve score → ace interview → keep learning at work."**

### 1.2 Product Vision

**SkillForge** is an AI-powered career acceleration platform that combines:
- **Lens** (ATS Scanner) — free acquisition engine
- **Forge** (Study Engine) — daily-habit retention engine
- **Mission** (Interview Sprint) — time-bound conversion engine

### 1.3 Target Users

| Persona | Profile | Primary Need | First Value Moment |
|---------|---------|--------------|-------------------|
| **Interview-Prepper** | Senior eng, 4-8 YOE, active job search | "I have a Google interview in 14 days" | ATS scan → gaps → Mission Mode countdown |
| **Career-Climber** | Staff eng, 8-15 YOE, upskilling | "I want to stay sharp and get promoted" | Daily 5 → streak → skill radar growth |
| **Team Lead** | Eng Manager, building AI capability | "My team needs to learn agentic AI patterns" | Browse cards → share link with team |

### 1.4 Success Metrics (OKRs)

| Metric | Launch Target (Month 3) | Growth Target (Month 6) |
|--------|------------------------|-------------------------|
| Registered users | 200 | 2,000 |
| Paying Pro users | 50 | 500 |
| DAU/MAU ratio | 15% | 25% |
| Average streak length | 5 days | 14 days |
| ATS scan → Pro conversion | 8% | 12% |
| Monthly churn | <10% | <6% |

### 1.5 Feature Priority Matrix

| Priority | Feature | Phase | Why this order |
|----------|---------|-------|----------------|
| **P0** | Auth (Google OAuth + JWT) | 0 | Gating mechanism for everything |
| **P0** | Skeleton deploy (Vercel + Railway) + CI/CD | 0 | Deploy on day one. Every merge ships. |
| **P0** | Card browser + search | 1 | Core value — users must see content |
| **P0** | FSRS spaced repetition (Daily 5) | 1 | Retention mechanic that prevents churn |
| **P0** | Quiz system per card | 1 | Proves learning happened |
| **P0** | ATS → skill gap → card mapping | 1 | Closes the scan→study loop on day one |
| **P0** | Lightweight onboarding flow | 1 | Bridges ATS scan result to study engine |
| **P0** | Stripe payments ($49/mo USD / ₹999/mo INR) | 1 | Revenue before features |
| **P0** | PostHog analytics (basic events) | 1 | 10 min to add. Blind without it. |
| **P1** | Mission Mode (countdown sprint) | 2 | Interview-Prepper conversion engine |
| **P1** | Streaks + XP + badges | 2 | Daily return hooks |
| **P1** | Skill radar + activity heatmap | 2 | Visual progress = motivation |
| **P1** | Daily email / push notification | 2 | "3 cards due" — makes FSRS + streaks work |
| **P1** | Landing page + onboarding polish | 3 | Marketing surface before outreach |
| **P1** | Admin card CRUD + AI generation | 3 | Content pipeline at scale (internal tool) |
| **P2** | "My Experience" AI generation | 3 | Differentiator |
| **P2** | Per-card feedback + NPS | 3 | Quality loop |
| **P2** | Error monitoring (Sentry) + hardening | 4 | Production observability and resilience |
| **P3** | Cmd+K reference search | Future | Retention feature |
| **P3** | Team dashboards (B2B) | Future | Enterprise upsell |
| **P3** | Community content submissions | Future | Scale when 500+ users |

---

## 2. Phased Execution Plan

### The Golden Rule

> [!IMPORTANT]
> **Each phase has ONE shipping milestone. You don't start the next phase until the current one is deployed and tested by at least 1 real user (you count).**

---

### Phase 0: Foundation Surgery + Skeleton Deploy (Weeks 1–2) ✅ DONE

**Ship Milestone**: HireLens ATS features work identically on PostgreSQL with unified auth. Skeleton app deployed to production. CI/CD pipeline active.

| # | Task | Test Gate |
|---|------|-----------|
| 0.1 | Install PostgreSQL 16 + pgvector locally | `pg_isready` returns "accepting connections" |
| 0.2 | Migrate SQLAlchemy from SQLite → PostgreSQL | All existing tests pass |
| 0.3 | Alembic migration for existing tables | `alembic upgrade head` succeeds |
| 0.4 | Unify frontend auth (use backend JWT) | Login → API call → protected route works |
| 0.5 | Add `role` column to User model | `require_admin()` dependency blocks non-admins |
| 0.6 | **Skeleton deploy**: Vercel (FE) + Railway (BE + managed PG) | `curl https://yourdomain.com/health` → 200 |
| 0.7 | **CI/CD pipeline** (GitHub Actions): push → test → deploy | Push to main → tests pass → auto-deploy |
| 0.8 | **VERIFY**: All ATS features still work **in production** | Manual test on deployed URL: upload resume → score → rewrite |

> **Why deploy now?** Deploying for the first time after 12 weeks of localhost code is a guaranteed failure. CORS, connection pooling, env var mismatches, and Stripe webhook URLs all break on first deploy. Deploy an empty skeleton now. Every merge from Phase 1 onward ships continuously.

---

### Phase 1: Core Study Engine + ATS Bridge (Weeks 3–6)

**Ship Milestone**: A user can scan their resume, see skill gaps mapped to study cards, study with FSRS, take quizzes, and pay $49/mo. Analytics tracking from day one.

| # | Task | Test Gate |
|---|------|-----------|
| 1.1 | Extract 177 cards from JSX → PostgreSQL | `SELECT count(*) FROM cards` = 177 |
| 1.2 | Generate embeddings for all cards | `SELECT count(*) FROM cards WHERE embedding IS NOT NULL` = 177 |
| 1.3 | Cards API: list, by category, by ID, search | `pytest tests/test_cards_api.py` — 10+ assertions |
| 1.4 | FSRS study service + API | `pytest tests/test_study_service.py` — scheduling accuracy |
| 1.5 | Study Dashboard UI (category grid) | Browser test: all categories visible |
| 1.6 | Card Viewer UI (flip + 4-tier tabs + quiz) | Browser test: flip animation, quiz submit |
| 1.7 | Daily 5 UI (FSRS queue) | Browser test: shows due cards |
| 1.8 | **ATS → skill gap → card mapping** | Test: scan result with "RAG" gap returns RAG category cards |
| 1.9 | **Onboarding flow + persona picker** (target_company, target_date fields) | Manual test: scan → gap screen → first card |
| 1.10 | **PostHog analytics**: paste snippet, track core events | Test: `ats_scanned`, `card_viewed`, `paywall_hit` events fire |
| 1.11 | Stripe integration (USD $49/mo + INR ₹999/mo geo-pricing) | Test: checkout session creates, webhook processes |
| 1.12 | Free tier gating (15 foundation cards; 3 interview Q/month) | Non-pro user blocked from full library and interview Q limit enforced |
| 1.13 | Auto-populate job tracker from ATS scan results | Test: scan → tracker entry created with company/role |
| 1.14 | IP registration blocking (max 2 accounts per IP per 30 days) | Test: 3rd registration from same IP returns 429 |
| 1.15 | LLM multi-model router (fast vs reasoning, multi-provider) | Test: fast tasks use Flash, reasoning tasks use Pro/Opus |

> **Phase 1 contingency (if slipping past Week 5):** The release valve is the onboarding flow (Task 1.9), not Stripe. A manual link from ATS results to the relevant card category achieves 80% of onboarding with a fraction of the effort. Cut onboarding polish — not the paywall. Revenue gating validates willingness to pay; free beta testers tell you nothing about conversion.

**User journey after Phase 1:**
```
Sign in (Google) → Upload resume (free) → See ATS score + skill gaps
     → "You're weak in RAG and System Design — here are cards"
          → Browse cards → Hit 15-card wall → Pay $49/mo (or ₹999/mo)
               → Daily 5 (FSRS) → Quiz → Come back tomorrow
```

---

### Phase 2: Retention + Conversion Engine (Weeks 7–9)

**Ship Milestone**: Users have daily streaks, XP, progress visualization, daily reminders, and Interview-Preppers can run a timed Mission Mode sprint.

| # | Task | Test Gate |
|---|------|-----------|
| 2.1 | Streaks + XP + badges service | `pytest tests/test_gamification.py` — streak calc, XP awards |
| 2.2 | Streaks + XP UI (profile, header badge) | Browser test: streak counter visible after review |
| 2.3 | Skill radar chart + activity heatmap | Browser test: radar shows category coverage |
| 2.4 | Mission Mode: create sprint (target date + card set) | Test: POST creates sprint, GET returns countdown |
| 2.5 | Mission Mode UI: countdown, daily targets, progress | Browser test: "12 days left, 8 cards today" |
| 2.6 | Daily email: "N cards due today" (Resend) | Test: trigger fires, email contains correct card count |
| 2.7 | Email preferences: opt-out, frequency | Test: opted-out user receives no email |

---

### Phase 3: Content Pipeline + Marketing (Weeks 10–12)

**Ship Milestone**: Admin can create/edit cards at scale, landing page is live, quality feedback loop is running.

| # | Task | Test Gate |
|---|------|-----------|
| 3.1 | Admin card CRUD (create, edit, soft-delete via `deleted_at`, bulk import) | Test: admin can create card, non-admin gets 403; deleted_at set on delete |
| 3.2 | AI card generation (LLM router: topic → card draft) | Test: generated card has all required fields |
| 3.3 | Landing page (value prop, pricing, CTA) | Manual: loads fast, responsive, CTA → sign up |
| 3.4 | Onboarding polish (guided tour, persona picker with target_company + target_date) | Manual: new user completes onboarding in < 2 min |
| 3.5 | "My Experience" AI generation (fix: accurate personalization) | Test: generates personalized study suggestions |
| 3.6 | Per-card feedback + NPS widget | Test: feedback stored, admin can view |
| 3.7 | Design system: 3 themes (Dark, Light, Midnight) + ThemePicker | Browser test: theme persists across reload |
| 3.8 | Resume rewrite improvements + cover letter formatting fixes | Test: rewritten resume score ≥ original; cover letter format is clean |

---

### Phase 4: Hardening + Observability (Weeks 13–15)

**Ship Milestone**: Production is monitored, performant, resilient, and ready for growth.

| # | Task | Test Gate |
|---|------|-----------|
| 4.1 | Error monitoring (Sentry) | Test: thrown error appears in dashboard |
| 4.2 | PostHog funnels + retention dashboards | Dashboard: scan → card → paywall → payment funnel visible |
| 4.3 | Performance audit: < 2s TTFB, < 3s LCP | Lighthouse score > 90 |
| 4.4 | Rate limiting + abuse prevention | Test: > 100 req/min returns 429 |
| 4.5 | Webhook idempotency (Stripe event deduplication) | Test: duplicate webhook event processed only once |
| 4.6 | Backup + disaster recovery runbook | Test: restore from backup succeeds |
| 4.7 | Custom domain + SSL + Stripe go-live runbook | `curl https://theskillsforge.dev/health` → 200; Stripe live keys verified |

---

### Persona Journey Validation

**Interview-Prepper** ("I have a Google interview in 14 days"):

| Week | What they experience | Phase |
|------|---------------------|-------|
| W3 | Sign in → scan resume → see gaps → "You need RAG + System Design" → browse cards | 1 |
| W3 | Hit 15-card limit → pay $49/mo (or ₹999 if Indian IP) → unlock full library | 1 |
| W3 | Daily 5 starts → quiz after each card → FSRS schedules reviews | 1 |
| W7 | **Start Mission**: "Google in 14 days" → daily targets → countdown | 2 |
| W7 | Streaks + XP visible → daily email: "8 cards due, 12 days left" | 2 |
| W9 | Skill radar shows coverage → rescan resume → score improved | 2 |

**Career-Climber** ("Stay sharp, get promoted"):

| Week | What they experience | Phase |
|------|---------------------|-------|
| W3 | Sign in → scan resume (optional) → browse cards by category | 1 |
| W3 | Daily 5 → quiz → FSRS schedules next review | 1 |
| W7 | Streaks + XP → "14-day streak!" → skill radar shows growth over time | 2 |
| W7 | Daily email pulls them back → activity heatmap shows consistency | 2 |

---

## 3. Spec-Driven Development

### 3.1 The Spec-First Workflow

> [!IMPORTANT]
> **No code gets written until a spec exists.** Every feature follows this flow:

```
1. Write SPEC (what + why + acceptance criteria)
      ↓
2. Write TESTS that assert the acceptance criteria
      ↓
3. Write CODE that makes the tests pass
      ↓
4. REVIEW (Claude Code self-review + manual check)
      ↓
5. SHIP (merge to main → CI/CD auto-deploys)
```

### 3.2 Spec Template

```markdown
# SPEC: [Feature Name]

## Status: Draft | Approved | In Progress | Done

## Problem
## Solution
## Acceptance Criteria
- [ ] AC-1: Given [context], when [action], then [expected result]

## API Contract
- `METHOD /api/v1/path` — description
  - Request: `{ field: type }`
  - Response: `{ field: type }`
  - Errors: `400`, `401`, `403`, `429`

## Data Model Changes
## UI/UX
## Analytics Events
## Edge Cases
## Dependencies
## Test Plan
```

### 3.3 Spec Directory

```
docs/
├── specs/
│   ├── phase-0/
│   │   ├── 00-postgresql-migration.md    ✅ DONE
│   │   ├── 01-auth-unification.md
│   │   ├── 02-user-roles.md
│   │   ├── 02a-skeleton-deploy.md
│   │   └── 02b-cicd-pipeline.md
│   ├── phase-1/
│   │   ├── 03-card-extraction.md
│   │   ├── 04-cards-api.md
│   │   ├── 05-fsrs-daily-review.md
│   │   ├── 06-study-dashboard-ui.md
│   │   ├── 07-card-viewer-ui.md
│   │   ├── 08-ats-card-mapping.md
│   │   ├── 09-onboarding-flow.md         ← includes persona picker + target_company/target_date
│   │   ├── 10-posthog-analytics.md
│   │   ├── 11-stripe-integration.md      ← includes geo-pricing USD/INR
│   │   ├── 11a-free-tier-limits.md       ← 15 cards + 3 interview Q/month
│   │   ├── 11b-tracker-autopopulate.md
│   │   ├── 11c-ip-registration-blocking.md
│   │   └── 11d-llm-router.md
│   ├── phase-2/
│   │   ├── 12-streaks-xp-badges.md
│   │   ├── 13-skill-radar-heatmap.md
│   │   ├── 14-mission-mode.md
│   │   ├── 15-daily-email.md
│   │   └── 16-email-preferences.md
│   ├── phase-3/
│   │   ├── 17-admin-card-crud.md         ← includes soft-delete (deleted_at)
│   │   ├── 18-ai-card-generation.md      ← uses LLM router
│   │   ├── 19-landing-page.md
│   │   ├── 20-onboarding-polish.md
│   │   ├── 20a-my-experience.md
│   │   ├── 20b-design-system-themes.md
│   │   ├── 20c-resume-cover-letter-fix.md
│   │   └── 21-per-card-feedback.md
│   └── phase-4/
│       ├── 22-error-monitoring.md
│       ├── 23-posthog-dashboards.md
│       ├── 24-performance-hardening.md
│       ├── 24a-webhook-idempotency.md
│       └── 25-custom-domain-golive.md
├── prd.md
└── architecture.md
```

---

## 4. AGENTS.md & Skills System

### 4.2 The Master AGENTS.md

```markdown
# SkillForge — Agent Development Guide

## Project Overview
SkillForge is an AI-powered career acceleration platform combining
ATS scanning, spaced-repetition flashcard learning, and interview prep.
Built with FastAPI + React + PostgreSQL + pgvector.

## Architecture
- Backend: FastAPI (Python 3.13) at `hirelens-backend/`
- Frontend: React 18 + TypeScript + Vite at `hirelens-frontend/`
- Database: PostgreSQL 16 + pgvector
- Cache: Redis 7
- Auth: Google OAuth + JWT (access + refresh tokens)
- LLM: Multi-model router (see LLM Strategy below)
- Payments: Stripe (USD + INR geo-pricing)
- Analytics: PostHog Cloud
- Email: Resend (transactional)
- Deploy: Vercel (FE) + Railway (BE + PG + Redis)
- CI/CD: GitHub Actions (push to main → test → deploy)

## LLM Strategy
- Fast model: `LLM_FAST_MODEL` env var (default: gemini-2.0-flash)
  Provider: `LLM_FAST_PROVIDER` (google | anthropic | openai)
- Reasoning model: `LLM_REASONING_MODEL` env var (default: gemini-2.5-pro)
  Provider: `LLM_REASONING_PROVIDER` (google | anthropic | openai)
- Router: `app/core/llm_router.py` — selects model based on task type
  - fast tasks: embeddings, quick rewrites, card drafts
  - reasoning tasks: ATS scoring, gap analysis, experience generation
- Fallback: if provider key not set, falls back to Gemini (GEMINI_API_KEY)
- Read `.agent/skills/llm-strategy.md` before any LLM work

## Geo Pricing
- Detect user IP at checkout → determine country
- India (IN): STRIPE_PRO_PRICE_ID_INR (₹999/mo)
- All others: STRIPE_PRO_PRICE_ID (USD $49/mo)
- Read `.agent/skills/geo-pricing.md` before payment work

## Security Rules
- IP registration blocking: max 2 accounts per IP per 30 days (Redis-backed)
- Free tier limits: 15 Foundation cards + 3 interview questions/month
- Card soft-delete: use `deleted_at` column, never hard-delete cards
- Stripe webhooks: idempotency key on every event (deduplicate in Redis)
- Read `.agent/skills/security.md` before auth/payment/rate-limit work

## Design System
- 3 themes: Dark (default), Light, Midnight
- ThemePicker component in Settings
- CSS variables for all colors — never hardcode hex in components
- Read `.agent/skills/design-system.md` before any UI work

## Coding Conventions

### Backend (Python)
- Use `async def` for all route handlers and service methods
- Use Pydantic v2 models for ALL request/response schemas
- Use SQLAlchemy 2.0 style (`Mapped[]`, `mapped_column()`)
- Use `Depends()` for auth, DB sessions, service injection
- Service layer pattern: routes call services, services call DB
- All new tables need Alembic migrations
- Card deletes use soft-delete: set `deleted_at = now()`, filter WHERE deleted_at IS NULL
- FSRS calculations happen server-side ONLY
- Naming: `snake_case` for files, functions, variables
- Every user-facing feature must fire a PostHog event

### Frontend (TypeScript/React)
- Functional components with hooks only
- Use `useQuery`/`useMutation` pattern for API calls
- All API calls go through `services/api.ts` with auth headers
- Use CSS variables from design system — no hardcoded colors
- ThemePicker reads from localStorage → applies to :root
- Framer Motion for all animations
- Mobile-first responsive design
- Naming: `PascalCase` for components, `camelCase` for functions
- PostHog `capture()` on key user actions

### Testing
- Backend: pytest + pytest-asyncio + httpx
- Frontend: Vitest + React Testing Library
- Every API endpoint: happy path + auth failure + validation error
- Coverage target: 80%+

### Git Conventions
- Commit: `type(scope): description`
- Every merge to main auto-deploys via CI/CD

## Key Decisions Log
- Auth: Google OAuth + JWT
- FSRS: py-fsrs library, server-side only
- LLM: Multi-model router (fast/reasoning split, multi-provider)
- Storage: R2 for files, PostgreSQL for data
- Analytics: PostHog Cloud, instrumented from Phase 1
- Email: Resend for transactional
- Deploy: Vercel + Railway from Phase 0
- Geo pricing: USD + INR via Stripe price IDs
- Card deletes: soft-delete with deleted_at (never hard-delete)
- IP blocking: Redis-backed, max 2 registrations/30 days per IP
```

### 4.3 Per-Feature Skill Files

```
.agent/
├── skills/
│   ├── study-engine.md        ← FSRS, Daily 5, card progress
│   ├── ats-scanner.md         ← ATS scoring, skill gaps, rewrite, cover letter
│   ├── ats-card-bridge.md     ← ATS gap → card mapping, onboarding flow
│   ├── gamification.md        ← Streaks, XP, badges, heatmap
│   ├── mission-mode.md        ← Interview sprint, countdown, daily targets
│   ├── notifications.md       ← Daily email, email prefs, Resend
│   ├── experience-gen.md      ← AI personalized experiences
│   ├── admin-panel.md         ← Card CRUD, soft-delete, bulk import, AI assist
│   ├── card-extraction.md     ← JSX → PostgreSQL pipeline
│   ├── analytics.md           ← PostHog events, funnels, dashboards
│   ├── payments.md            ← Stripe checkout, webhooks, geo-pricing, plan gating
│   ├── testing.md             ← Test patterns, fixtures, mocks
│   ├── database-schema.md     ← Living schema reference, all tables + columns
│   ├── db-migration.md        ← Alembic migration patterns and rules
│   ├── content-pipeline.md    ← Admin card CRUD + AI generation at scale
│   ├── llm-strategy.md        ← Multi-model router, fast vs reasoning, providers  ← NEW
│   ├── security.md            ← IP blocking, rate limits, idempotency, free limits ← NEW
│   ├── design-system.md       ← 3 themes, CSS vars, ThemePicker conventions       ← NEW
│   └── geo-pricing.md         ← USD/INR detection, Stripe price IDs, checkout     ← NEW
└── workflows/
    ├── new-feature.md
    ├── new-api-route.md
    ├── new-ui-page.md
    ├── run-tests.md
    ├── db-migration.md
    └── deploy.md
```

### 4.4 New Skill File: LLM Strategy

```markdown
---
description: Multi-model LLM router — fast vs reasoning tasks, multi-provider (Google/Anthropic/OpenAI)
---
# LLM Strategy Skill

## Overview
SkillForge uses a multi-model router that selects the right LLM based on
task complexity. Fast tasks use a cheaper/faster model; reasoning tasks
use a more capable model. The provider is configurable via env vars.

## Key Files
- `app/core/llm_router.py` — router logic (entry point: `generate_for_task(task=..., prompt=..., ...)`)
- `app/core/config.py` — LLM env var loading

## Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| LLM_FAST_MODEL | gemini-2.0-flash | Fast model name |
| LLM_FAST_PROVIDER | google | Provider: google, anthropic, openai |
| LLM_REASONING_MODEL | gemini-2.5-pro | Reasoning model name |
| LLM_REASONING_PROVIDER | google | Provider: google, anthropic, openai |
| GEMINI_API_KEY | required | Google AI key (used as fallback) |
| ANTHROPIC_API_KEY | optional | Anthropic Claude key |
| OPENAI_API_KEY | optional | OpenAI key |

## Task Classification
- **Fast tasks**: card embedding generation, quick text rewrites,
  card draft generation, cover letter formatting
- **Reasoning tasks**: ATS resume scoring, skill gap analysis,
  experience generation, personalization

## Fallback Behavior
If the configured provider's API key is not set, the router falls
back to Google Gemini (GEMINI_API_KEY). Log a warning when this occurs.

## Usage Pattern
```python
from app.services.llm_router import get_llm_client, TaskType

# Fast task
client = get_llm_client(TaskType.FAST)
response = await client.generate(prompt)

# Reasoning task  
client = get_llm_client(TaskType.REASONING)
response = await client.generate(prompt)
```
```

### 4.5 New Skill File: Security

```markdown
---
description: IP registration blocking, rate limits, webhook idempotency, free-tier limits
---
# Security Skill

## IP Registration Blocking
- Max 2 accounts per IP address per 30-day rolling window
- Stored in Redis: key = `ip_reg:{ip}`, value = count, TTL = 30 days
- On registration: increment counter; if > 2, return 429
- Key file: `app/api/v1/routes/auth.py` (logic inlined in the Google OAuth callback; uses the `registration_logs` table + 30-day window query, NOT a Redis counter). See the P5-S4 backfill spec for rationale.

## Free Tier Limits
- 15 Foundation category cards (enforced in cards API)
- 3 interview questions per month (enforced in interview Q endpoint)
- Limit check: `app/services/usage_service.py` (DB-backed via `usage_logs` table, monthly window; NOT a Redis counter as originally spec'd). See P5-S6 backfill.
- Return 403 with `{"detail": "free_limit_reached", "limit_type": "interview_questions"}`

## Stripe Webhook Idempotency
- Every Stripe event has an `id` field (e.g., `evt_xxx`)
- Store processed event IDs in Redis: key = `stripe_evt:{id}`, TTL = 24h
- On webhook arrival: check Redis; if exists, return 200 and skip processing
- Key file: `app/services/payment_service.py` → `handle_webhook()`

## Rate Limiting
- Global: 100 req/min per IP (slowapi)
- Auth endpoints: 10 req/min per IP
- ATS scan: 5 req/min per user
```

### 4.6 New Skill File: Design System

```markdown
---
description: 3 themes (Dark/Light/Midnight), CSS variables, ThemePicker component
---
# Design System Skill

## Themes
- **Dark** (default): #0A0A0B base, brand gradients
- **Light**: #FFFFFF base, muted brand colors
- **Midnight**: #050508 base, high-contrast neon accents

## CSS Variables (set on :root per theme)
```css
:root[data-theme="dark"] {
  --bg-primary: #0A0A0B;
  --bg-secondary: #111113;
  --text-primary: #FFFFFF;
  --text-secondary: #9CA3AF;
  --brand-gradient: linear-gradient(135deg, #6366F1, #8B5CF6);
}
```

## ThemePicker
- Component: `src/components/settings/ThemePicker.tsx`
- Persisted: localStorage key `skillforge-theme`
- Applied: `document.documentElement.setAttribute('data-theme', theme)`
- Never hardcode colors in components — always use CSS variables

## Key Files
- `src/styles/design-tokens.css` + `src/styles/design-tokens.ts` — theme variable definitions (token-first, consumed via Tailwind utilities)
- `src/components/settings/ThemePicker.tsx` — picker UI
- `src/context/ThemeContext.tsx` — theme state + provider (NOT `src/hooks/useTheme.ts`)
```

### 4.7 New Skill File: Geo Pricing

```markdown
---
description: USD/INR geo-based pricing, IP detection at checkout, Stripe price IDs
---
# Geo Pricing Skill

## Overview
At checkout, detect the user's country via IP geolocation and show the
appropriate Stripe price. Indian users see ₹999/mo; all others see $49/mo.

## Environment Variables
| Variable | Description |
|----------|-------------|
| STRIPE_PRO_PRICE_ID | USD price ID (e.g., price_usd_xxx) |
| STRIPE_PRO_PRICE_ID_INR | INR price ID (e.g., price_inr_xxx) |

## Detection Flow
1. POST /api/v1/payments/checkout
2. Read client IP from request headers (X-Forwarded-For or request.client.host)
3. Lookup country via ip-api.com or MaxMind (free tier)
4. If country == "IN" → use STRIPE_PRO_PRICE_ID_INR
5. Else → use STRIPE_PRO_PRICE_ID
6. Create Stripe Checkout Session with correct price_id

## Key Files
- `app/services/geo_pricing_service.py` — IP → country lookup + Redis-cached pricing (module-level `get_pricing(ip)`)
- `app/services/payment_service.py` → `create_checkout_session()`

## Analytics
- `checkout_started` — { price_id, currency, country }
```

---

## 5. Test-Driven Development Strategy

*(unchanged from v2 — see original Section 5)*

---

## 6. Claude Code Best Practices

### 6.3 The Updated CLAUDE.md

```markdown
# SkillForge — Claude Code Guide

## Quick Reference
- Backend: `cd hirelens-backend && source venv/bin/activate`
- Frontend: `cd hirelens-frontend`
- Tests (BE): `python -m pytest tests/ -v --tb=short`
- Tests (FE): `npx vitest run`
- DB migrate: `alembic upgrade head`
- Start BE: `uvicorn app.main:app --reload --port 8000`
- Start FE: `npm run dev -- --port 5199`

## MUST-READ Before Any Task
1. Read `AGENTS.md` for project conventions
2. Read `SESSION-STATE.md` for current progress
3. Read the relevant spec in `docs/specs/`
4. Read the relevant skill file in `.agent/skills/`

## Rules
1. **Test first**: Write tests before implementation
2. **One thing at a time**: Each commit = one feature slice
3. **Never skip auth**: All new routes need `Depends(get_current_user)`
4. **FSRS is server-side only**: Never put scheduling logic in frontend
5. **Pydantic for everything**: All API I/O uses Pydantic schemas
6. **Alembic for all schema changes**: Never use `CREATE TABLE` directly
7. **Soft-delete cards**: Set `deleted_at = now()`, never hard-delete
8. **Track everything**: Every user-facing feature fires a PostHog event
9. **Deploy is automatic**: Push to main = production deploy
10. **LLM routing**: Use `llm_router.py` — never call LLM SDKs directly
11. **Design system**: Use CSS variables — never hardcode colors
12. **🚨 3-Strike Rule**: If a test fails 3 times in a row, STOP. Print
    the exact error, list 2-3 possible fixes, wait for human input.

## Environment
- Python 3.13, Node 20, PostgreSQL 16 + pgvector, Redis 7
- Backend: FastAPI, SQLAlchemy 2.0 async, py-fsrs, anthropic, openai, google-genai
- Frontend: React 18, TypeScript 5, Vite 5, Tailwind, Framer Motion, react-markdown
- LLM: Multi-model router (fast/reasoning, google/anthropic/openai)
- Analytics: PostHog (instrumented from Phase 1)
- Email: Resend (from Phase 2)
- Deploy: Vercel + Railway (continuous from Phase 0)
```

---

## 7. Bootstrap Protocol

### 7.9 Step 8: Backend Setup

```bash
pip install asyncpg pgvector py-fsrs redis posthog stripe resend slowapi
pip install anthropic openai google-genai  # LLM providers
pip install pytest pytest-asyncio httpx pytest-cov
python -m spacy download en_core_web_sm
```

Backend `.env` (full reference):

```bash
# DATABASE
DATABASE_URL=postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport
TEST_DATABASE_URL=postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport_test

# REDIS
REDIS_URL=redis://localhost:6379

# AUTH
JWT_SECRET_KEY=CHANGE_ME_run_openssl_rand_hex_32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# LLM — MULTI-MODEL ROUTER
GEMINI_API_KEY=your-gemini-key           # Required (fallback provider)
GEMINI_MODEL=gemini-2.0-flash            # Legacy alias still supported
LLM_FAST_MODEL=gemini-2.0-flash
LLM_FAST_PROVIDER=google                 # google | anthropic | openai
LLM_REASONING_MODEL=gemini-2.5-pro
LLM_REASONING_PROVIDER=google
ANTHROPIC_API_KEY=                       # Optional — leave blank to use Gemini
OPENAI_API_KEY=                          # Optional — leave blank to use Gemini

# STRIPE
STRIPE_SECRET_KEY=sk_test_CHANGE_ME
STRIPE_WEBHOOK_SECRET=whsec_CHANGE_ME
STRIPE_PRO_PRICE_ID=price_CHANGE_ME      # USD $49/mo
STRIPE_PRO_PRICE_ID_INR=price_CHANGE_ME  # INR ₹999/mo

# ANALYTICS
POSTHOG_API_KEY=phc_CHANGE_ME
POSTHOG_HOST=https://us.i.posthog.com

# EMAIL
RESEND_API_KEY=

# MONITORING
SENTRY_DSN=

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5199
```

### 7.10 Step 9: Frontend Setup

```bash
npm install recharts@latest @tanstack/react-query zustand posthog-js framer-motion stripe @stripe/stripe-js react-markdown
npm install -D vitest @testing-library/react @testing-library/jest-dom @vitest/coverage-v8 jsdom
```

Frontend `.env`:

```bash
VITE_API_BASE_URL=
VITE_GOOGLE_CLIENT_ID=your-google-client-id
VITE_POSTHOG_KEY=phc_CHANGE_ME
VITE_POSTHOG_HOST=https://us.i.posthog.com
VITE_STRIPE_KEY=pk_test_CHANGE_ME
VITE_SENTRY_DSN=
```

---

## 8. CI/CD & Deployment Pipeline

### 8.3 Environment Variables Checklist

**Railway (Backend):**
- `DATABASE_URL` — auto-set by Railway managed PG
- `REDIS_URL` — auto-set by Railway managed Redis
- `JWT_SECRET_KEY` — generate with `openssl rand -hex 32`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRO_PRICE_ID` (USD), `STRIPE_PRO_PRICE_ID_INR` (INR)
- `GEMINI_API_KEY`, `LLM_FAST_MODEL`, `LLM_FAST_PROVIDER`
- `LLM_REASONING_MODEL`, `LLM_REASONING_PROVIDER`
- `ANTHROPIC_API_KEY` (optional), `OPENAI_API_KEY` (optional)
- `POSTHOG_API_KEY`, `POSTHOG_HOST`
- `RESEND_API_KEY` (Phase 2+)
- `SENTRY_DSN` (Phase 4+)
- `ALLOWED_ORIGINS` — your Vercel frontend URL

**Vercel (Frontend):**
- `VITE_API_BASE_URL` — your Railway backend URL
- `VITE_GOOGLE_CLIENT_ID`
- `VITE_POSTHOG_KEY`, `VITE_POSTHOG_HOST`
- `VITE_STRIPE_KEY`
- `VITE_SENTRY_DSN` (Phase 4+)

---

## 9. Post-Playbook Enhancements

These features were built after the original playbook was written. They are fully integrated into the phase tasks and skill files above. This section documents what changed and why.

| Enhancement | Where built | Spec file | Skill file |
|-------------|-------------|-----------|------------|
| LLM multi-model router | Phase 1 (Task 1.15) | `11d-llm-router.md` | `llm-strategy.md` |
| Design system + 3 themes + ThemePicker | Phase 3 (Task 3.7) | `20b-design-system-themes.md` | `design-system.md` |
| Geo-based pricing (USD/INR) | Phase 1 (Task 1.11) | `11-stripe-integration.md` | `geo-pricing.md` |
| IP registration blocking (max 2/30d) | Phase 1 (Task 1.14) | `11c-ip-registration-blocking.md` | `security.md` |
| Free tier limits (3 interview Q/month) | Phase 1 (Task 1.12) | `11a-free-tier-limits.md` | `security.md` |
| Auto-populate tracker from ATS scan | Phase 1 (Task 1.13) | `11b-tracker-autopopulate.md` | `ats-scanner.md` |
| Persona picker + target_company + target_date | Phase 1 (Task 1.9) | `09-onboarding-flow.md` | `ats-card-bridge.md` |
| Card soft-delete (deleted_at column) | Phase 3 (Task 3.1) | `17-admin-card-crud.md` | `security.md` |
| Resume rewrite + cover letter formatting fixes | Phase 3 (Task 3.8) | `20c-resume-cover-letter-fix.md` | `ats-scanner.md` |

### Enhancement Prompts

Use these Claude Code prompts to implement each enhancement if not yet built:

**LLM Router:**
```
Read AGENTS.md. Read .agent/skills/llm-strategy.md. Read docs/specs/phase-1/11d-llm-router.md.
Create app/core/llm_router.py (ALREADY BUILT — see P5-S1 backfill) with: a `generate_for_task(task, prompt, ...)` function that classifies `task` into FAST_TASKS / REASONING_TASKS frozensets, reads LLM_FAST_PROVIDER/LLM_REASONING_PROVIDER env vars, and dispatches to `_call_gemini` / `_call_anthropic` / `_call_openai`. Fallback to Gemini if provider key missing.
Write tests: test_fast_uses_configured_model, test_reasoning_uses_configured_model,
test_fallback_to_gemini_when_no_anthropic_key. Run pytest. Commit.
```

**Geo Pricing:**
```
Read AGENTS.md. Read .agent/skills/geo-pricing.md. Read docs/specs/phase-1/11-stripe-integration.md.
Update app/services/payment_service.py: create_checkout_session() should accept request object,
extract IP, call geo_service.get_country(ip), use STRIPE_PRO_PRICE_ID_INR for "IN",
STRIPE_PRO_PRICE_ID for all others. Use the existing app/services/geo_pricing_service.py (already built — calls ip-api.com with a 24-hour Redis cache, returns `{currency, price, price_display, stripe_price_id}`).
Write tests (mock geo service). Run pytest. Commit.
```

**IP Registration Blocking:**
```
Read AGENTS.md. Read .agent/skills/security.md. Read docs/specs/phase-1/11c-ip-registration-blocking.md.
IP-limit logic ALREADY BUILT inline in app/api/v1/routes/auth.py (not in a dedicated service; uses the `registration_logs` DB table, not Redis). Max 2 registrations per IP per 30-day window. Constants `_MAX_REGISTRATIONS_PER_IP = 2` and `_REGISTRATION_WINDOW_DAYS = 30`. Backfill as docs/specs/phase-1/11c-ip-registration-blocking.md.
```

**Card Soft-Delete:**
```
Read AGENTS.md. Read .agent/skills/security.md.
Add deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, default=None)
to the Card model. Generate migration. Update all card queries to filter
WHERE deleted_at IS NULL. Update admin delete endpoint to SET deleted_at = now().
Write tests: test_deleted_card_not_returned_in_api, test_admin_soft_delete.
Run pytest. Commit.
```

**Design System + ThemePicker:**
```
Read AGENTS.md. Read .agent/skills/design-system.md. Read docs/specs/phase-3/20b-design-system-themes.md.
Create src/styles/design-tokens.css (ALREADY BUILT) with CSS variables for 3 themes (dark/light/midnight) alongside `src/styles/design-tokens.ts` for Tailwind integration.
Theme state lives in src/context/ThemeContext.tsx (NOT a `useTheme.ts` hook) — localStorage persistence + :root `data-theme` attribute.
Create src/components/settings/ThemePicker.tsx.
Refactor: replace all hardcoded hex colors in components with CSS variables.
Manual test: switch themes → UI updates. Commit.
```

**Free Tier Limits:**
```
Read AGENTS.md. Read .agent/skills/security.md. Read docs/specs/phase-1/11a-free-tier-limits.md.
Free-tier check ALREADY BUILT in app/services/usage_service.py (DB-backed via the `usage_logs` table, monthly window query — not Redis).
Wire into interview Q endpoint: free users get 403 after 3/month. Backfill as docs/specs/phase-1/11a-free-tier-limits.md.
Existing 15-card limit: verify it's enforced in cards API. Write tests. Run pytest. Commit.
```

**Tracker Auto-Populate:**
```
Read AGENTS.md. Read docs/specs/phase-1/11b-tracker-autopopulate.md.
After ATS scan completes: if job title + company are extractable from resume,
auto-create a tracker entry (status=applied, source=ats_scan).
Add to app/services/tracker_service.py: create_from_scan(user_id, scan_result).
Write tests: test_tracker_entry_created_after_scan. Run pytest. Commit.
```

**Resume Rewrite + Cover Letter Fix:**
```
Read AGENTS.md. Read .agent/skills/ats-scanner.md. Read docs/specs/phase-3/20c-resume-cover-letter-fix.md.
Audit current resume rewrite: identify formatting regressions and fix.
Cover letter: ensure output is clean plain text with no markdown artifacts.
Use LLM router (REASONING task) for both. Write tests (mock LLM responses).
Run pytest. Manual test: rewrite a resume → score should be >= original. Commit.
```

---

*SkillForge Master Development Playbook v2.1 — Updated with post-playbook enhancements, LLM router, geo pricing, IP blocking, design system, free tier limits, soft-delete, and complete env var reference.*
