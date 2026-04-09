# SkillForge — Master Development Playbook v2

> **The CTO/Growth Partner/Architect/VC Guide to Building SkillForge Right**
> *Spec-Driven · Test-First · Agent-Powered · Deploy Continuously · Ship Fast*

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

---

## 1. Product Requirements Document

### 1.1 Problem Statement

Senior/Staff/Principal engineers preparing for $200K+ roles face a fragmented learning landscape: LeetCode for algorithms (wrong audience), Udemy for theory (shallow), and expensive coaching ($300/hr) for behavioral prep. No single platform closes the loop from **"scan resume → find gaps → study cards → re-scan → improve score → ace interview → keep learning at work."**

### 1.2 Product Vision

**SkillForge (under HirePort AI umbrella)** is an AI-powered career acceleration platform that combines:
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
| **P0** | Stripe payments ($49/mo) | 1 | Revenue before features |
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

**Why this is one phase**: The problem statement promises "scan → find gaps → study cards." If these are in separate phases, the product is a disconnected flashcard browser for months. The ATS→card mapping is a lightweight tag-based join on top of the embeddings already being generated — it doesn't require a separate phase.

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
| 1.9 | **Onboarding flow**: after ATS scan, show "Your gaps: X, Y — start studying" | Manual test: scan → gap screen → first card |
| 1.10 | **PostHog analytics**: paste snippet, track core events | Test: `ats_scanned`, `card_viewed`, `paywall_hit` events fire |
| 1.11 | Stripe integration ($49/mo Pro) | Test: checkout session creates, webhook processes |
| 1.12 | Free tier gating (15 foundation cards) | Non-pro user blocked from full library |

> **Phase 1 contingency (if slipping past Week 5):** The release valve is the onboarding flow (Task 1.9), not Stripe. A manual link from ATS results to the relevant card category achieves 80% of onboarding with a fraction of the effort. Cut onboarding polish — not the paywall. Revenue gating validates willingness to pay; free beta testers tell you nothing about conversion.

**User journey after Phase 1:**
```
Sign in (Google) → Upload resume (free) → See ATS score + skill gaps
     → "You're weak in RAG and System Design — here are cards"
          → Browse cards → Hit 15-card wall → Pay $49/mo
               → Daily 5 (FSRS) → Quiz → Come back tomorrow
```

---

### Phase 2: Retention + Conversion Engine (Weeks 7–9)

**Ship Milestone**: Users have daily streaks, XP, progress visualization, daily reminders, and Interview-Preppers can run a timed Mission Mode sprint.

**Why Mission Mode is here**: The Interview-Prepper persona ("I have an interview in 14 days") is the highest-intent buyer. Without a time-bound mode, they use the Daily 5 like everyone else — which doesn't match their urgency. Mission Mode is the conversion differentiator.

**Why notifications are here**: FSRS scheduling is invisible if nobody comes back. A "3 cards due — keep your 7-day streak" email is the minimum viable reminder. Without it, streaks are a counter nobody sees.

| # | Task | Test Gate |
|---|------|-----------|
| 2.1 | Streaks + XP + badges service | `pytest tests/test_gamification.py` — streak calc, XP awards |
| 2.2 | Streaks + XP UI (profile, header badge) | Browser test: streak counter visible after review |
| 2.3 | Skill radar chart + activity heatmap | Browser test: radar shows category coverage |
| 2.4 | Mission Mode: create sprint (target date + card set) | Test: POST creates sprint, GET returns countdown |
| 2.5 | Mission Mode UI: countdown, daily targets, progress | Browser test: "12 days left, 8 cards today" |
| 2.6 | Daily email: "N cards due today" (SendGrid / Resend) | Test: trigger fires, email contains correct card count |
| 2.7 | Email preferences: opt-out, frequency | Test: opted-out user receives no email |

**User journey after Phase 2:**
```
Interview-Prepper: Scan → Gaps → "Start Mission: Google in 14 days"
     → Daily targets → Streak building → Countdown pressure → Pay

Career-Climber: Scan → Gaps → Browse cards → Daily 5 → Streak + XP
     → Skill radar shows growth → Daily email pulls them back
```

---

### Phase 3: Content Pipeline + Marketing (Weeks 10–12)

**Ship Milestone**: Admin can create/edit cards at scale, landing page is live, quality feedback loop is running.

**Why this is now**: The product is feature-complete for users. This phase is about scaling content, enabling outreach, and closing the quality loop. Admin CRUD is an internal tool that doesn't affect any user's journey — it belongs after the user-facing product works.

| # | Task | Test Gate |
|---|------|-----------|
| 3.1 | Admin card CRUD (create, edit, delete, bulk import) | Test: admin can create card, non-admin gets 403 |
| 3.2 | AI card generation (Gemini: topic → card draft) | Test: generated card has all required fields |
| 3.3 | Landing page (value prop, pricing, CTA) | Manual: loads fast, responsive, CTA → sign up |
| 3.4 | Onboarding polish (guided tour, persona picker) | Manual: new user completes onboarding in < 2 min |
| 3.5 | "My Experience" AI generation | Test: generates personalized study suggestions |
| 3.6 | Per-card feedback + NPS widget | Test: feedback stored, admin can view |

---

### Phase 4: Hardening + Observability (Weeks 13–15)

**Ship Milestone**: Production is monitored, performant, resilient, and ready for growth.

**Why this is lighter now**: Deploy and CI/CD already happened in Phase 0. Analytics already happened in Phase 1. This phase is about making the deployed product robust — not getting it deployed for the first time.

| # | Task | Test Gate |
|---|------|-----------|
| 4.1 | Error monitoring (Sentry) | Test: thrown error appears in dashboard |
| 4.2 | PostHog funnels + retention dashboards | Dashboard: scan → card → paywall → payment funnel visible |
| 4.3 | Performance audit: < 2s TTFB, < 3s LCP | Lighthouse score > 90 |
| 4.4 | Rate limiting + abuse prevention | Test: > 100 req/min returns 429 |
| 4.5 | Backup + disaster recovery runbook | Test: restore from backup succeeds |
| 4.6 | Custom domain + SSL | `curl https://skillforge.app/health` → 200 |

---

### Persona Journey Validation

**Interview-Prepper** ("I have a Google interview in 14 days"):

| Week | What they experience | Phase |
|------|---------------------|-------|
| W3 | Sign in → scan resume → see gaps → "You need RAG + System Design" → browse cards | 1 |
| W3 | Hit 15-card limit → pay $49/mo → unlock full library | 1 |
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

**Team Lead** ("My team needs to learn agentic AI patterns"):

| Week | What they experience | Phase |
|------|---------------------|-------|
| W3 | Sign in → browse cards → sees "Agentic AI" category → shares with team | 1 |
| W10 | Landing page exists → can share link with team members | 3 |
| Future | Team dashboards (B2B) — not yet built | Future |

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

Create specs in `docs/specs/` with this format:

```markdown
# SPEC: [Feature Name]

## Status: Draft | Approved | In Progress | Done

## Problem
What user problem does this solve?

## Solution
How does this feature solve it?

## Acceptance Criteria
- [ ] AC-1: Given [context], when [action], then [expected result]
- [ ] AC-2: ...
- [ ] AC-3: ...

## API Contract
### Endpoints
- `METHOD /api/v1/path` — description
  - Request: `{ field: type }`
  - Response: `{ field: type }`
  - Errors: `400 (validation)`, `401 (unauth)`, `403 (plan limit)`

## Data Model Changes
- New tables, columns, indexes

## UI/UX
- Page/component description
- Key interactions
- Mobile behavior

## Analytics Events
- PostHog events this feature should fire
- Properties attached to each event

## Edge Cases
- What happens when...?

## Dependencies
- What must be built first?

## Test Plan
- Unit tests needed
- Integration tests needed
- Manual verification steps
```

### 3.3 Spec Directory

```
docs/
├── specs/
│   ├── phase-0/                          ← ✅ DONE
│   │   ├── 00-postgresql-migration.md
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
│   │   ├── 09-onboarding-flow.md
│   │   ├── 10-posthog-analytics.md
│   │   └── 11-stripe-integration.md
│   ├── phase-2/
│   │   ├── 12-streaks-xp-badges.md
│   │   ├── 13-skill-radar-heatmap.md
│   │   ├── 14-mission-mode.md
│   │   ├── 15-daily-email.md
│   │   └── 16-email-preferences.md
│   ├── phase-3/
│   │   ├── 17-admin-card-crud.md
│   │   ├── 18-ai-card-generation.md
│   │   ├── 19-landing-page.md
│   │   ├── 20-my-experience.md
│   │   └── 21-per-card-feedback.md
│   └── phase-4/
│       ├── 22-error-monitoring.md
│       ├── 23-posthog-dashboards.md
│       ├── 24-performance-hardening.md
│       └── 25-custom-domain.md
├── prd.md
└── architecture.md
```

---

## 4. AGENTS.md & Skills System

### 4.1 What Is AGENTS.md?

`AGENTS.md` is the **single source of truth** that tells Claude Code (or any AI coding agent) HOW your project works. It replaces ad-hoc prompting with a living document that evolves with your codebase.

### 4.2 The Master AGENTS.md

Create this at the project root: `hireportai/AGENTS.md`

```markdown
# SkillForge — Agent Development Guide

## Project Overview
SkillForge (under HirePort AI) is an AI-powered career acceleration
platform combining ATS scanning, spaced-repetition flashcard learning,
and interview prep. Built with FastAPI + React + PostgreSQL + pgvector.

## Architecture
- Backend: FastAPI (Python 3.13) at `hirelens-backend/`
- Frontend: React 18 + TypeScript + Vite at `hirelens-frontend/`
- Database: PostgreSQL 16 + pgvector
- Cache: Redis 7
- Auth: Google OAuth + JWT (access + refresh tokens)
- LLM: Google Gemini (via google-genai SDK)
- Payments: Stripe
- Analytics: PostHog Cloud
- Email: SendGrid or Resend (transactional)
- Deploy: Vercel (FE) + Railway (BE + PG + Redis)
- CI/CD: GitHub Actions (push to main → test → deploy)

## Directory Structure
hireportai/
├── AGENTS.md                    ← YOU ARE HERE
├── CLAUDE.md                    ← Claude Code project rules
├── docs/
│   ├── specs/                   ← Feature specifications (by phase)
│   ├── prd.md                   ← Product Requirements Document
│   └── architecture.md          ← System architecture
├── hirelens-backend/
│   ├── app/
│   │   ├── api/routes/          ← API route handlers
│   │   ├── core/                ← Auth, config, deps
│   │   ├── models/              ← SQLAlchemy ORM models
│   │   ├── schemas/             ← Pydantic request/response
│   │   ├── services/            ← Business logic
│   │   └── main.py              ← FastAPI app factory
│   ├── tests/                   ← pytest tests
│   ├── alembic/                 ← DB migrations
│   └── scripts/                 ← One-off scripts (migration, seeding)
├── hirelens-frontend/
│   ├── src/
│   │   ├── components/          ← Reusable UI components
│   │   ├── pages/               ← Route pages
│   │   ├── context/             ← React contexts
│   │   ├── hooks/               ← Custom hooks
│   │   ├── services/            ← API client
│   │   └── types/               ← TypeScript types
│   └── tests/                   ← Vitest + RTL tests
├── .github/
│   └── workflows/
│       └── ci.yml               ← CI/CD pipeline
└── scripts/                     ← Dev utility scripts

## Coding Conventions

### Backend (Python)
- Use `async def` for all route handlers and service methods
- Use Pydantic v2 models for ALL request/response schemas
- Use SQLAlchemy 2.0 style (`Mapped[]`, `mapped_column()`)
- Use `Depends()` for auth, DB sessions, service injection
- Service layer pattern: routes call services, services call DB
- All new tables need Alembic migrations
- FSRS calculations happen server-side ONLY (not in frontend)
- Naming: `snake_case` for files, functions, variables
- Every user-facing feature must fire a PostHog event

### Frontend (TypeScript/React)
- Functional components with hooks only (no class components)
- Use `useQuery`/`useMutation` pattern for API calls
- All API calls go through `services/api.ts` with auth headers
- Dark mode by default (#0A0A0B base, brand gradients)
- Framer Motion for all animations
- Mobile-first responsive design
- Naming: `PascalCase` for components, `camelCase` for functions
- PostHog `capture()` on key user actions (scan, view card, pay)

### Testing
- Backend: pytest + pytest-asyncio + httpx (async client)
- Frontend: Vitest + React Testing Library
- Test files mirror source structure: `app/services/foo.py` →
  `tests/test_foo.py`
- Every API endpoint needs at least: happy path, auth failure,
  validation error test
- Coverage target: 80%+

### Git Conventions
- Branch: `feature/<phase>-<number>-<name>`
  (e.g., `feature/p1-05-fsrs-daily-review`)
- Commit: `type(scope): description`
  (e.g., `feat(study): add FSRS daily review endpoint`)
- PR = 1 spec = 1 deployable unit
- Every merge to main auto-deploys via CI/CD

### Deployment
- Every push to main runs: lint → test → deploy
- Backend deploys to Railway (auto-deploy on push)
- Frontend deploys to Vercel (auto-deploy on push)
- Database migrations run automatically via release command
- Stripe webhooks use the production URL (set in Phase 0)
- Environment variables live in Railway/Vercel dashboards, NOT in code

## Key Decisions Log
- Auth: Google OAuth + JWT (NOT Clerk — migrating later for B2B)
- FSRS: py-fsrs library, server-side only
- LLM: Gemini 2.5 Pro for reasoning, Flash for speed tasks
- Storage: R2 for files (zero egress), PostgreSQL for data
- Analytics: PostHog Cloud (free tier), instrumented from Phase 1
- Email: SendGrid or Resend for transactional (daily reminders, Phase 2)
- Deploy: Vercel + Railway from Phase 0, not deferred to launch
- No Docker for dev — use local PostgreSQL + Redis via Homebrew
```

### 4.3 Per-Feature Skill Files

Skill files give Claude Code (and your future self) deep context about specific features. Store them at `.agent/skills/`.

```
.agent/
├── skills/
│   ├── study-engine.md       ← FSRS, Daily 5, card progress
│   ├── ats-scanner.md        ← ATS scoring, skill gaps, rewrite
│   ├── ats-card-bridge.md    ← ATS gap → card mapping, onboarding flow
│   ├── gamification.md       ← Streaks, XP, badges, heatmap
│   ├── mission-mode.md       ← Interview sprint, countdown, daily targets
│   ├── notifications.md      ← Daily email, email prefs, SendGrid/Resend
│   ├── experience-gen.md     ← AI personalized experiences
│   ├── admin-panel.md        ← Card CRUD, bulk import, AI assist
│   ├── card-extraction.md    ← JSX → PostgreSQL pipeline
│   ├── analytics.md          ← PostHog events, funnels, dashboards
│   ├── payments.md           ← Stripe checkout, webhooks, plan gating
│   └── testing.md            ← Test patterns, fixtures, mocks
└── workflows/
    ├── new-feature.md        ← How to add a new feature end-to-end
    ├── new-api-route.md      ← How to add a backend API route
    ├── new-ui-page.md        ← How to add a frontend page
    ├── run-tests.md          ← How to run all tests
    ├── db-migration.md       ← How to create an Alembic migration
    └── deploy.md             ← How deploy works (CI/CD, Railway, Vercel)
```

### 4.4 Example Skill File: Study Engine

```markdown
---
description: FSRS spaced repetition study engine — Daily 5, card progress, review scheduling
---

# Study Engine Skill

## Overview
The study engine is the core retention mechanic of SkillForge. It uses
the FSRS (Free Spaced Repetition Scheduler) algorithm to schedule card
reviews at optimal intervals based on individual memory patterns.

## Key Files
- Backend:
  - `app/services/study_service.py` — FSRS scheduling logic
  - `app/api/routes/study.py` — API endpoints
  - `app/models/card_progress.py` — ORM model
  - `app/schemas/study.py` — Pydantic schemas
- Frontend:
  - `src/pages/DailyReview.tsx` — Daily 5 queue page
  - `src/components/study/ReviewCard.tsx` — Card review component
  - `src/hooks/useStudySession.ts` — Study session hook
- Tests:
  - `tests/test_study_service.py` — FSRS scheduling unit tests
  - `tests/test_study_api.py` — API integration tests

## FSRS Algorithm Details
- Library: `py-fsrs>=3.0.0`
- Ratings: Again (1), Hard (2), Good (3), Easy (4)
- State machine: New → Learning → Review → Relearning
- Key fields: `stability`, `difficulty`, `due_date`, `state`
- Daily 5 = SELECT cards WHERE due_date <= NOW() ORDER BY due_date LIMIT 5

## API Contracts
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/study/daily` | GET | Required | Get today's due cards |
| `/api/v1/study/review` | POST | Required | Submit review rating |
| `/api/v1/study/progress` | GET | Required | Get overall progress |
| `/api/v1/study/session` | POST | Required | Start study session |
| `/api/v1/study/session/{id}` | PUT | Required | End study session |

## Analytics Events
- `card_reviewed` — { card_id, rating, time_spent_ms }
- `daily_review_started` — { total_due, session_id }
- `daily_review_completed` — { cards_reviewed, session_id }

## Testing Checklist
- [ ] FSRS "Good" rating increases interval by 2-4x
- [ ] FSRS "Again" rating resets card to today
- [ ] Daily 5 returns max 5 cards
- [ ] Daily 5 returns empty list when nothing is due
- [ ] Free users only get Foundation category cards
- [ ] XP is awarded on each review (calls gamification service)
```

### 4.5 Example Skill File: ATS → Card Bridge

```markdown
---
description: Maps ATS scan skill gaps to study cards, powers onboarding flow
---

# ATS → Card Bridge Skill

## Overview
When a user scans their resume, the ATS scanner produces a list of
skill gaps. This service maps those gaps to study card categories
so the user immediately knows what to study. This is the core
conversion mechanism: scan → "you're weak in X" → here are cards.

## Key Files
- Backend:
  - `app/services/gap_mapping_service.py` — gap → category mapping
  - `app/api/routes/onboarding.py` — onboarding endpoints
- Frontend:
  - `src/pages/Onboarding.tsx` — post-scan gap display
  - `src/components/onboarding/GapCard.tsx` — individual gap card

## How Mapping Works
1. ATS scanner returns skill gaps as tags (e.g., "RAG", "System Design")
2. Each card category has a `tags` array
3. Mapping is a tag-based join: gap tag ∈ category tags → match
4. For semantic matching (Phase 1+): use pgvector cosine similarity
   between gap description embedding and card embeddings

## Analytics Events
- `onboarding_started` — { source: "ats_scan" | "direct" }
- `gap_card_clicked` — { gap_name, category_id }
- `onboarding_completed` — { gaps_shown, cards_clicked }
```

### 4.6 Example Skill File: Notifications

```markdown
---
description: Daily email reminders, email preferences, SendGrid/Resend integration
---

# Notifications Skill

## Overview
Daily email reminders drive retention by pulling users back to their
FSRS queue. Without reminders, users forget the app exists — streaks
break and churn spikes.

## Key Files
- Backend:
  - `app/services/email_service.py` — email sending abstraction
  - `app/services/reminder_service.py` — daily digest logic
  - `app/api/routes/email_prefs.py` — preference endpoints
  - `app/models/email_preference.py` — opt-out model
- Templates:
  - `app/templates/daily_reminder.html` — email template

## Email Provider
- Primary: Resend (simple API, good free tier)
- Fallback: SendGrid
- API key in env: `RESEND_API_KEY`

## Daily Digest Logic
1. Cron job runs at 7 AM user's local time (or UTC default)
2. Query: users WHERE has_due_cards AND email_opted_in
3. For each user: count due cards, current streak length
4. Send: "You have {N} cards due today. Keep your {streak}-day streak alive!"

## Analytics Events
- `email_sent` — { user_id, type: "daily_reminder", cards_due }
- `email_clicked` — { user_id, type, utm_source }
```

### 4.7 Workflow: Adding a New Feature

Create `.agent/workflows/new-feature.md`:

```markdown
---
description: How to add a new feature to SkillForge end-to-end
---

## Steps

1. **Write the spec** in `docs/specs/phase-N/NN-feature-name.md`
   using the template from AGENTS.md

2. **Create the Alembic migration** (if new tables/columns needed)
// turbo
3. Run `cd hirelens-backend && alembic revision --autogenerate -m "add feature_name tables"`
// turbo
4. Run `cd hirelens-backend && alembic upgrade head`

5. **Write backend tests first** in `tests/test_feature_name.py`
   - Happy path test
   - Auth failure test (401)
   - Validation error test (422)
   - Plan gating test (403 for free users if applicable)

6. **Implement backend service** in `app/services/feature_service.py`
// turbo
7. Run `cd hirelens-backend && python -m pytest tests/test_feature_name.py -v`

8. **Implement API routes** in `app/api/routes/feature.py`
   - Register router in `main.py`
// turbo
9. Run `cd hirelens-backend && python -m pytest tests/ -v`

10. **Add PostHog events** in the service layer
    - Track key user actions
    - Include relevant properties

11. **Implement frontend page/component**
    - Create page in `src/pages/FeatureName.tsx`
    - Add route in `App.tsx`
    - Add API client method in `services/api.ts`
    - Add PostHog `capture()` calls on user interactions

// turbo
12. Run `cd hirelens-frontend && npx vitest run`

13. **Manual verification**
    - Open browser, test the feature end-to-end
    - Test on mobile viewport
    - Verify PostHog events fire in the dashboard
    - Verify it works on the deployed URL (CI/CD auto-deploys)

14. **Git commit**
    ```bash
    git add -A
    git commit -m "feat(feature): add feature_name — closes spec #NN"
    git push origin main
    # CI/CD auto-deploys to production
    ```
```

### 4.8 Workflow: Deploy

Create `.agent/workflows/deploy.md`:

```markdown
---
description: How deployment works — continuous from Phase 0
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
```

---

## 5. Test-Driven Development Strategy

### 5.1 The Test Pyramid

```
          ┌───────────┐
          │   E2E     │  ← 5-10 critical user flows (browser tests)
          │  Tests    │
         ┌┴───────────┴┐
         │ Integration  │  ← API endpoint tests (httpx + test DB)
         │    Tests     │
        ┌┴─────────────┴┐
        │   Unit Tests   │  ← Services, models, utilities
        │                │
        └────────────────┘
```

| Layer | Tool | Count Target | What It Tests |
|-------|------|-------------|---------------|
| **Unit** | pytest | 100+ | FSRS scheduling, scoring logic, card extraction, gamification math |
| **Integration** | pytest + httpx | 50+ | API routes end-to-end with real DB |
| **E2E** | Browser subagent | 10-15 | Critical flows: login → study → quiz → streak |

### 5.2 Backend Test Setup

```python
# tests/conftest.py

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.main import app
from app.db.session import get_db
from app.models.base import Base
from app.models.user import User
from app.models.card import Card, Category

TEST_DATABASE_URL = "postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport_test"

@pytest_asyncio.fixture
async def db_session():
    """Create a fresh test database for each test."""
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        pytest.skip("Test database unreachable — skipping DB tests")

    async with AsyncSession(engine) as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def seeded_db_session(db_session):
    """Pre-seeded DB with canonical test data.

    WHY THIS EXISTS: Without this fixture, every integration test
    wastes 20-30 lines inserting boilerplate users and cards.
    Claude Code will write slightly different seed data each time,
    causing phantom test failures. One canonical fixture =
    deterministic, reproducible tests.

    Seeds:
    - 1 admin user ("admin@test.com", role="admin", plan="pro")
    - 1 free user  ("free@test.com", role="user", plan="free")
    - 1 pro user   ("pro@test.com", role="user", plan="pro")
    - 2 categories ("RAG Architecture", "Foundations")
    - 5 cards per category (10 total, with realistic content)
    - 3 cards with due_date=today (for FSRS testing)
    - 2 cards with due_date=future (for "not due" assertions)
    """
    # --- USERS ---
    admin = User(id="test-admin-id", email="admin@test.com",
                 name="Admin User", role="admin", plan="pro")
    free_user = User(id="test-free-id", email="free@test.com",
                     name="Free User", role="user", plan="free")
    pro_user = User(id="test-pro-id", email="pro@test.com",
                    name="Pro User", role="user", plan="pro")
    db_session.add_all([admin, free_user, pro_user])

    # --- CATEGORIES ---
    rag_cat = Category(id="cat-rag", name="RAG Architecture",
                       icon="📚", color="#4ECDC4", display_order=1)
    found_cat = Category(id="cat-found", name="Foundations",
                         icon="🏗️", color="#FFE66D", display_order=0,
                         source="foundation")  # Free-tier visible
    db_session.add_all([rag_cat, found_cat])

    # --- CARDS (5 per category) ---
    for i in range(5):
        db_session.add(Card(
            id=f"rag-{i+1}", category_id="cat-rag",
            question=f"RAG Question {i+1}",
            answer=f"RAG Answer {i+1} with production context.",
            difficulty="Hard" if i < 2 else "Medium",
            tags=["rag", "retrieval"],
        ))
        db_session.add(Card(
            id=f"found-{i+1}", category_id="cat-found",
            question=f"Foundation Question {i+1}",
            answer=f"Foundation Answer {i+1}.",
            difficulty="Medium",
            tags=["basics"],
        ))

    await db_session.commit()
    yield db_session

@pytest_asyncio.fixture
async def client(seeded_db_session):
    """Authenticated test client with pre-seeded data."""
    async def override_get_db():
        yield seeded_db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["Authorization"] = f"Bearer {create_test_token('test-pro-id')}"
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def client_free_tier(seeded_db_session):
    """Test client authenticated as a free-tier user."""
    async def override_get_db():
        yield seeded_db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["Authorization"] = f"Bearer {create_test_token('test-free-id')}"
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def client_admin(seeded_db_session):
    """Test client authenticated as admin."""
    async def override_get_db():
        yield seeded_db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["Authorization"] = f"Bearer {create_test_token('test-admin-id')}"
        yield ac
    app.dependency_overrides.clear()
```

### 5.3 TDD Workflow Per Sprint

> [!IMPORTANT]
> **The Red-Green-Refactor cycle applies to EVERY feature, not just backend.**

```
FOR EACH SPEC:
  1. Write failing test    → RED    ❌
  2. Write minimal code    → GREEN  ✅
  3. Refactor + clean up   → REFACTOR 🔄
  4. Run full suite        → VERIFY ✅✅✅
  5. Commit + push (auto-deploys)
```

### 5.4 Alembic Migration Rollback Testing

> [!WARNING]
> **A migration that can't `downgrade` is a one-way door.** Test locally on every migration.

```bash
cd hirelens-backend && source venv/bin/activate

# 1. Apply the migration
alembic upgrade head

# 2. Roll it back
alembic downgrade -1

# 3. Re-apply (proves the cycle is clean)
alembic upgrade head

# 4. Run ALL tests against the final state
python -m pytest tests/ -v --tb=short
```

### 5.5 Coverage Targets

| Component | Target | Tool |
|-----------|--------|------|
| Backend services | 85% | `pytest --cov=app/services` |
| Backend API routes | 80% | `pytest --cov=app/api` |
| Frontend components | 70% | `vitest --coverage` |
| Overall | 80% | CI gate |

---

## 6. Claude Code Best Practices

### 6.1 The "Context-Slice-Test-Ship" Loop

> [!IMPORTANT]
> **This is the most important section in this document.**

```
┌─────────────────────────────────────────────────────┐
│  1. CONTEXT                                          │
│     Load the right files into Claude Code's context  │
│     → AGENTS.md + spec file + relevant skill file    │
├─────────────────────────────────────────────────────┤
│  2. SLICE                                            │
│     Give ONE task that takes ~30 minutes              │
│     → NOT "Build the entire study engine"            │
├─────────────────────────────────────────────────────┤
│  3. TEST                                             │
│     Ask Claude Code to run the tests immediately     │
│     → Fix until GREEN                                │
├─────────────────────────────────────────────────────┤
│  4. SHIP                                             │
│     Commit and push (CI/CD auto-deploys)             │
│     → Move to next slice                             │
└─────────────────────────────────────────────────────┘
```

### 6.2 The 30-Minute Slice Rule

> [!WARNING]
> **Never give Claude Code a task that would take YOU more than 2 hours to do manually.** Break it into 30-minute slices.

### 6.3 The Updated CLAUDE.md

```markdown
# SkillForge (HirePort AI) — Claude Code Guide

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
2. Read the relevant spec in `docs/specs/`
3. Read the relevant skill file in `.agent/skills/`

## Rules
1. **Test first**: Write tests before implementation
2. **One thing at a time**: Each commit = one feature slice
3. **Never skip auth**: All new routes need `Depends(get_current_user)`
4. **FSRS is server-side only**: Never put scheduling logic in frontend
5. **Pydantic for everything**: All API I/O uses Pydantic schemas
6. **Alembic for all schema changes**: Never use `CREATE TABLE` directly
7. **No console.log in production**: Use proper logging
8. **Track everything**: Every user-facing feature fires a PostHog event
9. **Deploy is automatic**: Push to main = production deploy. Never do manual deploys.
10. **🚨 AI Loop Breaker (3-Strike Rule)**: If a test fails 3 times
    in a row, **STOP IMMEDIATELY**. Print the exact error, explain
    your hypothesis, list 2-3 possible fixes, and wait for human
    intervention.

## How to Add a Feature
1. Check spec exists in `docs/specs/`
2. Create/update backend models in `app/models/`
3. Create Alembic migration: `alembic revision --autogenerate -m "description"`
4. Apply: `alembic upgrade head`
5. Create Pydantic schemas in `app/schemas/`
6. Write tests in `tests/`
7. Implement service in `app/services/`
8. Add PostHog events in the service layer
9. Create API route in `app/api/routes/`
10. Register route in `app/main.py`
11. Run: `python -m pytest tests/ -v`
12. Implement frontend (page → component → hook → API client)
13. Add PostHog `capture()` on user interactions
14. Run: `npx vitest run`
15. Push to main (CI/CD auto-deploys)

## Environment
- Python 3.13, Node 20, PostgreSQL 16 + pgvector, Redis 7
- Backend: FastAPI, SQLAlchemy 2.0 async, py-fsrs, google-genai
- Frontend: React 18, TypeScript 5, Vite 5, Tailwind, Framer Motion
- Analytics: PostHog (instrumented from Phase 1)
- Email: Resend (from Phase 2)
- Deploy: Vercel + Railway (continuous from Phase 0)
- DB URL: `postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport`
```

### 6.4 Session Management Best Practices

| Practice | Why |
|----------|-----|
| **Start each session by saying "Read AGENTS.md and docs/specs/phase-N/NN-feature.md"** | Loads the right context |
| **End each session with "Run the tests and commit"** | Ensures clean state for next session |
| **Keep sessions focused on 1 spec** | Context window stays coherent |
| **If Claude Code drifts, say "Stop. Re-read the spec. Focus on AC-3."** | Resets the agent |
| **After 5+ slices, start a new session** | Prevents context window degradation |
| **Always review generated tests** | AI-written tests can be tautological |

### 6.5 Claude Code Permission Settings

```json
{
  "permissions": {
    "allow": [
      "Bash(python -m pytest:*)",
      "Bash(python3 -m pytest:*)",
      "Bash(npx vitest:*)",
      "Bash(npm run:*)",
      "Bash(npm install:*)",
      "Bash(pip install:*)",
      "Bash(alembic revision:*)",
      "Bash(alembic upgrade:*)",
      "Bash(alembic downgrade:*)",
      "Bash(uvicorn:*)",
      "Bash(psql:*)",
      "Bash(redis-cli:*)",
      "Bash(curl -s:*)",
      "Bash(git:*)",
      "Bash(python -c:*)",
      "Bash(source venv/bin/activate:*)",
      "Bash(pip freeze:*)",
      "Bash(pg_isready:*)"
    ]
  }
}
```

---

## 7. Bootstrap Protocol

> **Run this once when setting up the project from scratch.**
> If Phase 0 DB migration is already done, skip to the scaffolding steps.

### 7.1 Prerequisites

Your system needs:
- macOS (or Linux)
- Python 3.13+
- Node.js 20+ + npm
- Homebrew (macOS)
- Redis 7+
- Git
- Claude Code
- PostgreSQL 16 (via Homebrew — needs to be started)

### 7.2 Step 1: Start Services

```bash
# PostgreSQL
brew services start postgresql@16
pg_isready  # → "accepting connections"

# Create databases
createdb hireport
createdb hireport_test

# Install pgvector extension
psql -d hireport -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d hireport -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
psql -d hireport_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d hireport_test -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"

# Create dedicated user
psql -d hireport -c "CREATE USER hireport WITH PASSWORD 'dev_password';"
psql -d hireport -c "GRANT ALL PRIVILEGES ON DATABASE hireport TO hireport;"
psql -d hireport_test -c "GRANT ALL PRIVILEGES ON DATABASE hireport_test TO hireport;"

# Redis
brew services start redis
redis-cli ping  # → "PONG"
```

> [!NOTE]
> If pgvector isn't installed: `brew install pgvector` then `brew services restart postgresql@16`

### 7.3 Step 2: Folder Scaffolding

```bash
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai

# ── Spec directories (by phase) ──
mkdir -p docs/specs/{phase-0,phase-1,phase-2,phase-3,phase-4}

# ── Agent skills + workflows ──
mkdir -p .agent/{skills,workflows}

# ── Backend directories ──
mkdir -p hirelens-backend/{scripts,tests}
mkdir -p hirelens-backend/app/{api/routes,core,models,schemas,services,templates}
mkdir -p hirelens-backend/alembic/versions

# ── Frontend directories ──
mkdir -p hirelens-frontend/tests
mkdir -p hirelens-frontend/src/{components,pages,context,hooks,services,types}

# ── CI/CD ──
mkdir -p .github/workflows
```

### 7.4 Step 3: Agent Rules (AGENTS.md)

```bash
# Create AGENTS.md at project root
# Use the full content from Section 4.2 above
cat > AGENTS.md << 'AGENTS_EOF'
# SkillForge — Agent Development Guide
# ... (paste the full content from Section 4.2)
AGENTS_EOF
```

### 7.5 Step 4: Claude Code Rules (CLAUDE.md)

```bash
# Create CLAUDE.md at project root
# Use the full content from Section 6.3 above
cat > CLAUDE.md << 'CLAUDE_EOF'
# SkillForge (HirePort AI) — Claude Code Guide
# ... (paste the full content from Section 6.3)
CLAUDE_EOF

# Create Claude Code permissions
mkdir -p .claude
cat > .claude/settings.local.json << 'EOF'
{
  "permissions": {
    "allow": [
      "Bash(python -m pytest:*)",
      "Bash(python3 -m pytest:*)",
      "Bash(npx vitest:*)",
      "Bash(npm run:*)",
      "Bash(npm install:*)",
      "Bash(pip install:*)",
      "Bash(alembic revision:*)",
      "Bash(alembic upgrade:*)",
      "Bash(alembic downgrade:*)",
      "Bash(uvicorn:*)",
      "Bash(psql:*)",
      "Bash(redis-cli:*)",
      "Bash(curl -s:*)",
      "Bash(git:*)",
      "Bash(python -c:*)",
      "Bash(source venv/bin/activate:*)",
      "Bash(pip freeze:*)",
      "Bash(pg_isready:*)"
    ]
  }
}
EOF
```

### 7.6 Step 5: Product Requirements Document

```bash
# Create the PRD as a standalone doc
cat > docs/prd.md << 'EOF'
# SkillForge — Product Requirements Document

## See: Master Playbook Section 1

This file is the canonical PRD. Key points:

### Problem
Senior/Staff engineers preparing for $200K+ roles face fragmented prep.
No platform closes the scan → gaps → study → rescan → improve loop.

### Product = Three Engines
- Lens (ATS Scanner): free acquisition engine
- Forge (Study Engine): daily-habit retention via FSRS
- Mission (Interview Sprint): time-bound conversion engine

### Personas
1. Interview-Prepper: "Google interview in 14 days" → Mission Mode
2. Career-Climber: "Stay sharp, get promoted" → Daily 5 + streaks
3. Team Lead: "Team needs AI skills" → Card library + sharing

### Core Loop (must work end-to-end in Phase 1)
Scan resume → See skill gaps → Mapped to study cards → FSRS daily review
→ Quiz → Hit paywall → Pay $49/mo → Keep studying → Rescan → Score improves

### Revenue Model
$49/mo Pro plan. Free tier: ATS scan + 15 Foundation cards.
Conversion trigger: hit 15-card wall after seeing gaps.

### Success Metrics
- 200 registered / 50 paying by Month 3
- 8% ATS scan → Pro conversion
- 15% DAU/MAU, 5-day avg streak
EOF
```

### 7.7 Step 6: Skills Initialization

```bash
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai

# ── Study Engine Skill ──
cat > .agent/skills/study-engine.md << 'EOF'
---
description: FSRS spaced repetition study engine — Daily 5, card progress, review scheduling
---
# Study Engine Skill
# (paste full content from Section 4.4)
EOF

# ── ATS Scanner Skill ──
cat > .agent/skills/ats-scanner.md << 'EOF'
---
description: ATS resume scanning, scoring, skill gap extraction, resume rewrite
---
# ATS Scanner Skill
## Overview
The ATS scanner is the free acquisition engine. Users upload a resume,
get an ATS compatibility score, see skill gaps, and optionally rewrite.
## Key Files
- Backend: `app/services/tracker_service_v2.py`, `app/api/routes/tracker.py`
- Frontend: existing HireLens ATS UI
## Analytics Events
- `ats_scanned` — { score, gaps_found: int, file_type }
- `resume_rewritten` — { original_score, new_score }
EOF

# ── ATS → Card Bridge Skill ──
cat > .agent/skills/ats-card-bridge.md << 'EOF'
---
description: Maps ATS scan skill gaps to study cards, powers onboarding flow
---
# ATS → Card Bridge Skill
# (paste full content from Section 4.5)
EOF

# ── Gamification Skill ──
cat > .agent/skills/gamification.md << 'EOF'
---
description: Streaks, XP, badges, skill radar, activity heatmap
---
# Gamification Skill
## Overview
Gamification provides the psychological hooks for daily return.
Streaks create loss aversion. XP creates progress feeling.
Skill radar visualizes coverage. Heatmap shows consistency.
## Key Files
- Backend: `app/services/gamification_service.py`, `app/api/routes/gamification.py`
- Frontend: `src/components/profile/StreakBadge.tsx`, `src/pages/Profile.tsx`
## Streak Rules
- Streak increments when user completes at least 1 review in a calendar day
- Streak resets to 0 if a day is missed (midnight UTC)
- Streak freeze: Pro users get 1 free freeze per week
## XP Rules
- Card reviewed: 10 XP
- Quiz correct: 25 XP
- Daily 5 completed: 50 XP bonus
- Mission day completed: 75 XP bonus
## Analytics Events
- `streak_incremented` — { new_length, user_id }
- `streak_broken` — { previous_length, user_id }
- `badge_earned` — { badge_id, badge_name }
EOF

# ── Mission Mode Skill ──
cat > .agent/skills/mission-mode.md << 'EOF'
---
description: Interview sprint — countdown timer, daily targets, focused card set
---
# Mission Mode Skill
## Overview
Mission Mode is a time-bound study sprint for Interview-Preppers.
User sets a target date (e.g., "Google interview in 14 days"),
selects categories, and gets daily card targets with a countdown.
## Key Files
- Backend: `app/services/mission_service.py`, `app/api/routes/mission.py`
- Frontend: `src/pages/MissionMode.tsx`, `src/components/mission/Countdown.tsx`
## Mission Logic
- User creates mission: { target_date, category_ids[], daily_card_target }
- System calculates: total_cards / days_remaining = daily_target
- Each day: pull daily_target cards from selected categories (FSRS-prioritized)
- Countdown UI: "12 days left — 8 cards today"
- Completion: "Mission complete! You covered 95% of RAG + System Design"
## Analytics Events
- `mission_created` — { days, categories, total_cards }
- `mission_day_completed` — { day_number, cards_done, days_remaining }
- `mission_completed` — { total_days, coverage_pct }
- `mission_abandoned` — { day_abandoned, reason }
EOF

# ── Notifications Skill ──
cat > .agent/skills/notifications.md << 'EOF'
---
description: Daily email reminders, email preferences, SendGrid/Resend integration
---
# Notifications Skill
# (paste full content from Section 4.6)
EOF

# ── Payments Skill ──
cat > .agent/skills/payments.md << 'EOF'
---
description: Stripe checkout, webhooks, plan gating, free tier limits
---
# Payments Skill
## Overview
Stripe handles the $49/mo Pro subscription. Free tier gets 15
Foundation cards + ATS scanning. Pro unlocks the full library.
## Key Files
- Backend: `app/services/payment_service.py`, `app/api/routes/payments.py`
- Frontend: `src/components/PaywallModal.tsx`
## Flow
1. User hits 15-card wall → PaywallModal shows
2. Click "Upgrade" → POST /api/v1/payments/checkout → Stripe Checkout Session
3. User completes payment on Stripe-hosted page
4. Stripe webhook → POST /api/v1/payments/webhook → update user.plan = "pro"
5. Redirect back to app → full library unlocked
## Webhook Events to Handle
- `checkout.session.completed` → activate Pro
- `customer.subscription.deleted` → downgrade to Free
- `invoice.payment_failed` → grace period, email user
## Analytics Events
- `paywall_hit` — { card_count_viewed, trigger_page }
- `checkout_started` — { price_id }
- `payment_completed` — { amount, plan }
- `subscription_cancelled` — { months_active, reason }
EOF

# ── Analytics Skill ──
cat > .agent/skills/analytics.md << 'EOF'
---
description: PostHog events, funnels, dashboards, tracking conventions
---
# Analytics Skill
## Overview
PostHog is instrumented from Phase 1. Every user-facing feature
fires events. Phase 4 builds dashboards and funnels on top.
## Setup
- Frontend: PostHog JS snippet in index.html (or React provider)
- Backend: posthog-python library for server-side events
## Event Naming Convention
- Use snake_case: `card_reviewed`, NOT `CardReviewed`
- Include relevant properties as a dict
- Always include `user_id` (auto from PostHog identify)
## Core Events (Phase 1)
- `user_signed_up` — { auth_provider }
- `ats_scanned` — { score, gaps_found }
- `card_viewed` — { card_id, category }
- `card_reviewed` — { card_id, rating, time_spent_ms }
- `paywall_hit` — { cards_viewed, trigger }
- `payment_completed` — { amount, plan }
## Phase 2+ Events
- `streak_incremented`, `streak_broken`
- `mission_created`, `mission_completed`
- `email_sent`, `email_clicked`
## Key Funnels (build in Phase 4)
1. Acquisition: Sign up → ATS scan → View card → Paywall → Pay
2. Retention: Day 1 → Day 7 → Day 30 return rate
3. Mission: Create mission → 50% complete → 100% complete
EOF

# ── Card Extraction Skill ──
cat > .agent/skills/card-extraction.md << 'EOF'
---
description: JSX → PostgreSQL card extraction pipeline
---
# Card Extraction Skill
## Overview
Extract 177 study cards currently hardcoded in JSX components
into the PostgreSQL cards table with embeddings.
## Pipeline
1. Parse JSX files → extract card content (question, answer, category, difficulty, tags)
2. INSERT into cards table
3. Generate embeddings via Gemini/OpenAI → UPDATE cards SET embedding = Vector(1536)
4. Verify: SELECT count(*) FROM cards = 177, all embeddings non-null
## Key Files
- Script: `scripts/extract_cards.py`
- Source: `hirelens-frontend/src/data/` or wherever JSX cards live
EOF

# ── Admin Panel Skill ──
cat > .agent/skills/admin-panel.md << 'EOF'
---
description: Card CRUD, bulk import, AI-assisted card generation (Phase 3)
---
# Admin Panel Skill
## Overview
Admin panel lets admins create, edit, delete cards and bulk-import
from CSV. AI assist uses Gemini to draft cards from a topic.
## Key Files
- Backend: `app/api/routes/admin.py`, `app/services/card_admin_service.py`
- Frontend: `src/pages/AdminPanel.tsx`
## Access Control
- All admin routes require `Depends(require_admin)` — returns 403 for non-admins
## AI Card Generation
- Input: topic string + difficulty level
- Process: Gemini generates question, answer, tags, difficulty
- Output: draft card for admin review before publish
EOF

# ── Testing Skill ──
cat > .agent/skills/testing.md << 'EOF'
---
description: Test patterns, fixtures, mocks for SkillForge
---
# Testing Skill
## Overview
Backend: pytest + pytest-asyncio + httpx. Frontend: Vitest + RTL.
## Key Patterns
- Use `seeded_db_session` fixture for integration tests (canonical test data)
- Use `client` fixture for authenticated API tests (Pro user by default)
- Use `client_free_tier` for plan-gating tests
- Use `client_admin` for admin endpoint tests
- Auto-skip if TEST_DATABASE_URL is unreachable (CI without PG doesn't fail)
## Running Tests
- All backend: `cd hirelens-backend && python -m pytest tests/ -v --tb=short`
- Specific file: `python -m pytest tests/test_study_service.py -v`
- With coverage: `python -m pytest tests/ --cov=app --cov-report=term-missing`
- All frontend: `cd hirelens-frontend && npx vitest run`
- Migration rollback: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
EOF
```

### 7.8 Step 7: Workflows Initialization

```bash
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai

# ── New Feature Workflow ──
# (paste content from Section 4.7 into .agent/workflows/new-feature.md)

# ── New API Route Workflow ──
cat > .agent/workflows/new-api-route.md << 'EOF'
---
description: How to add a backend API route
---
## Steps
1. Create Pydantic schemas in `app/schemas/feature_name.py`
2. Create service in `app/services/feature_service.py`
3. Create route in `app/api/routes/feature.py`
4. Register router in `app/main.py`:
   `app.include_router(feature_router, prefix="/api/v1/feature", tags=["feature"])`
5. Add auth: `current_user: User = Depends(get_current_user)`
6. Add PostHog event tracking in the service layer
7. Write tests: happy path, 401, 422, 403 (if plan-gated)
8. Run: `python -m pytest tests/test_feature_api.py -v`
EOF

# ── New UI Page Workflow ──
cat > .agent/workflows/new-ui-page.md << 'EOF'
---
description: How to add a frontend page
---
## Steps
1. Create page in `src/pages/FeatureName.tsx`
2. Add route in `App.tsx`
3. Add API client method in `services/api.ts`
4. Add PostHog `capture()` on key user interactions
5. Use `useQuery`/`useMutation` for data fetching
6. Mobile-first, dark mode default
7. Write Vitest + RTL test
8. Run: `npx vitest run`
EOF

# ── Run Tests Workflow ──
cat > .agent/workflows/run-tests.md << 'EOF'
---
description: How to run all tests
---
## Backend
```bash
cd hirelens-backend && source venv/bin/activate
python -m pytest tests/ -v --tb=short          # All tests
python -m pytest tests/test_foo.py -v          # Single file
python -m pytest tests/ --cov=app              # With coverage
```
## Frontend
```bash
cd hirelens-frontend
npx vitest run                                 # All tests
npx vitest run --coverage                      # With coverage
```
## Migration Rollback
```bash
cd hirelens-backend
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
```
EOF

# ── DB Migration Workflow ──
cat > .agent/workflows/db-migration.md << 'EOF'
---
description: How to create an Alembic migration
---
## Steps
1. Modify ORM model in `app/models/`
2. Generate migration:
   `alembic revision --autogenerate -m "add feature_name column"`
3. Review the generated file in `alembic/versions/`
4. Check that `downgrade()` reverses everything in `upgrade()`
5. Apply: `alembic upgrade head`
6. Test rollback: `alembic downgrade -1 && alembic upgrade head`
7. Run tests: `python -m pytest tests/ -v`

## Rules
- Always verify the generated migration — autogenerate misses some things
- Hand-author migrations for complex changes (type promotions, data migrations)
- Every migration must have a working downgrade()
EOF

# ── Deploy Workflow ──
# (paste content from Section 4.8 into .agent/workflows/deploy.md)
```

### 7.9 Step 8: Backend Setup

```bash
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai/hirelens-backend

# Create fresh venv
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install asyncpg pgvector py-fsrs redis posthog pytest-asyncio httpx

# Download spaCy model
python -m spacy download en_core_web_sm

# Create .env
cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport
TEST_DATABASE_URL=postgresql+asyncpg://hireport:dev_password@localhost:5432/hireport_test

# Redis
REDIS_URL=redis://localhost:6379

# LLM
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.0-flash

# Auth
JWT_SECRET_KEY=your-random-secret-key-here-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5199

# Analytics
POSTHOG_API_KEY=phc_...
POSTHOG_HOST=https://us.i.posthog.com
EOF

# Verify backend starts
uvicorn app.main:app --reload --port 8000
# Visit: http://localhost:8000/docs
```

### 7.10 Step 9: Frontend Setup

```bash
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai/hirelens-frontend

# Install dependencies
npm install
npm install recharts@latest @tanstack/react-query zustand posthog-js

# Dev dependencies
npm install -D vitest @testing-library/react @testing-library/jest-dom @vitest/coverage-v8 jsdom

# Create .env
cat > .env << 'EOF'
VITE_API_BASE_URL=
VITE_GOOGLE_CLIENT_ID=your-google-client-id
VITE_POSTHOG_KEY=phc_...
VITE_POSTHOG_HOST=https://us.i.posthog.com
EOF

# Start dev server
npm run dev -- --port 5199
# Visit: http://localhost:5199
```

### 7.11 Step 10: CI/CD Pipeline

```bash
cat > .github/workflows/ci.yml << 'EOF'
name: CI
on: [push, pull_request]

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
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.13" }
      - run: |
          cd hirelens-backend
          pip install -r requirements.txt
          pip install asyncpg pgvector py-fsrs pytest-asyncio httpx
          python -m pytest tests/ -v --tb=short --cov=app

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
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
        with: { python-version: "3.13" }
      - run: |
          cd hirelens-backend
          pip install -r requirements.txt
          pip install asyncpg pgvector
          alembic upgrade head
          alembic downgrade -1
          alembic upgrade head
EOF
```

### 7.12 Step 11: Verify Everything Works

```bash
# Terminal 1: Backend
cd hirelens-backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd hirelens-frontend
npm run dev -- --port 5199

# Terminal 3: Verification
pg_isready                           # → "accepting connections"
redis-cli ping                       # → "PONG"
curl -s http://localhost:8000/health  # → {"status": "ok"}
curl -s http://localhost:5199         # → HTML response
```

### 7.13 The Developer Workflow (Daily Routine)

```bash
# Morning startup
brew services start postgresql@16
brew services start redis
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai

# Open 3 terminal tabs:
# Tab 1: Backend
cd hirelens-backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Tab 2: Frontend
cd hirelens-frontend && npm run dev -- --port 5199

# Tab 3: Claude Code
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai
claude
# → "Read AGENTS.md. Then read docs/specs/phase-1/05-fsrs-daily.md.
#    Implement Slice 3: StudyService.get_daily_review()"

# Evening shutdown
brew services stop postgresql@16
brew services stop redis
```

---

## 8. CI/CD & Deployment Pipeline

### 8.1 Pipeline Architecture

```
Push to main → GitHub Actions → lint → test (BE + FE) → migration rollback test
                                                            ↓ (all green)
                                              Railway auto-deploy (BE)
                                              Vercel auto-deploy (FE)
```

### 8.2 Deployment Targets

| Component | Platform | Why | When |
|-----------|----------|-----|------|
| Frontend | Vercel | Zero-config React, edge CDN | Phase 0 |
| Backend | Railway | Easy Python hosting, managed PG | Phase 0 |
| Database | Railway PostgreSQL | Managed, pgvector included | Phase 0 |
| Files | Cloudflare R2 | Zero egress costs for resumes | Phase 1 |
| Redis | Railway Redis or Upstash | Managed, free tier available | Phase 0 |
| Email | Resend | Simple API, good free tier | Phase 2 |
| Analytics | PostHog Cloud | Free tier, self-serve funnels | Phase 1 |
| Monitoring | Sentry | Error tracking, perf monitoring | Phase 4 |

### 8.3 Environment Variables Checklist

**Railway (Backend):**
- `DATABASE_URL` — auto-set by Railway managed PG
- `REDIS_URL` — auto-set by Railway managed Redis
- `JWT_SECRET_KEY` — generate with `openssl rand -hex 32`
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRO_PRICE_ID`
- `GEMINI_API_KEY`, `GEMINI_MODEL`
- `POSTHOG_API_KEY`, `POSTHOG_HOST`
- `RESEND_API_KEY` (Phase 2+)
- `ALLOWED_ORIGINS` — your Vercel frontend URL

**Vercel (Frontend):**
- `VITE_API_BASE_URL` — your Railway backend URL
- `VITE_GOOGLE_CLIENT_ID`
- `VITE_POSTHOG_KEY`, `VITE_POSTHOG_HOST`

---

## Appendix: Quick Reference Card

```
┌──────────────────────────────────────────────────────┐
│  SKILLFORGE DEVELOPMENT QUICK REFERENCE               │
│                                                       │
│  START:                                               │
│    brew services start postgresql@16                  │
│    brew services start redis                          │
│    cd hirelens-backend && source venv/bin/activate    │
│    uvicorn app.main:app --reload --port 8000          │
│    cd hirelens-frontend && npm run dev -- --port 5199 │
│                                                       │
│  TEST:                                                │
│    python -m pytest tests/ -v --tb=short              │
│    npx vitest run                                     │
│                                                       │
│  MIGRATE:                                             │
│    alembic revision --autogenerate -m "description"   │
│    alembic upgrade head                               │
│                                                       │
│  COMMIT + DEPLOY:                                     │
│    git add -A                                         │
│    git commit -m "type(scope): description"           │
│    git push origin main  ← auto-deploys              │
│                                                       │
│  CLAUDE CODE:                                         │
│    "Read AGENTS.md. Read the spec. Do Slice N."       │
│    "Run the tests." "Commit and push."                │
│                                                       │
│  URLS:                                                │
│    Frontend (local):  http://localhost:5199            │
│    Backend (local):   http://localhost:8000            │
│    Swagger:           http://localhost:8000/docs       │
│    DB:                psql -d hireport                 │
│    Redis:             redis-cli                        │
│    Production:        https://yourdomain.com           │
│    PostHog:           https://us.posthog.com           │
└──────────────────────────────────────────────────────┘
```

---
*SkillForge Master Development Playbook v2.0 — Revised with corrected user journey, continuous deployment from Phase 0, and analytics from Phase 1.*
