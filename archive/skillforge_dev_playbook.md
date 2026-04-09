# SkillForge — Master Development Playbook

> **The CTO/Growth Partner/Architect/VC Guide to Building SkillForge Right**
> *Spec-Driven · Test-First · Agent-Powered · Ship Fast*

---

## Table of Contents

1. [Product Requirements Document (PRD)](#1-product-requirements-document)
2. [Phased Execution Plan](#2-phased-execution-plan)
3. [Spec-Driven Development](#3-spec-driven-development)
4. [AGENTS.md & Skills System](#4-agentsmd--skills-system)
5. [Test-Driven Development Strategy](#5-test-driven-development-strategy)
6. [Claude Code Best Practices](#6-claude-code-best-practices)
7. [Local Mac Setup](#7-local-mac-setup)
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

| Persona | Profile | Primary Need |
|---------|---------|--------------|
| **Interview-Prepper** | Senior eng, 4-8 YOE, active job search | "I have a Google interview in 14 days" |
| **Career-Climber** | Staff eng, 8-15 YOE, upskilling | "I want to stay sharp and get promoted" |
| **Team Lead** | Eng Manager, building AI capability | "My team needs to learn agentic AI patterns" |

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

| Priority | Feature | Sprint | Why This Order |
|----------|---------|--------|----------------|
| **P0** | Card browser + search | 1 | Core value — users must see content before anything else |
| **P0** | FSRS spaced repetition (Daily 5) | 1 | The retention mechanic that prevents churn |
| **P0** | Quiz system per card | 1 | Proves learning happened |
| **P0** | Auth (Google OAuth + JWT) | 0 | Gating mechanism for everything |
| **P0** | Stripe payments ($49/mo) | 1 | Revenue before features |
| **P1** | Streaks + XP + badges | 2 | Psychological hooks for daily return |
| **P1** | Skill radar + activity heatmap | 2 | Visual progress = motivation |
| **P1** | Admin card CRUD + AI generation | 2 | Content pipeline at scale |
| **P1** | ATS → skill gap → card mapping | 3 | The killer flywheel |
| **P1** | Mission Mode (countdown sprint) | 3 | Conversion engine |
| **P2** | "My Experience" AI generation | 3 | Differentiator |
| **P2** | Per-card feedback + NPS | 3 | Quality loop |
| **P2** | Landing page + onboarding | 4 | Polish for launch |
| **P3** | Cmd+K reference search | Future | Retention feature |
| **P3** | Team dashboards (B2B) | Future | Enterprise upsell |
| **P3** | Community content submissions | Future | Scale when 500+ users |

---

## 2. Phased Execution Plan

### The Golden Rule

> [!IMPORTANT]
> **Each phase has ONE shipping milestone. You don't start the next phase until the current one is deployed and tested by at least 1 real user (you count).**

### Phase 0: Foundation Surgery (Weeks 1-2)

**Ship Milestone**: HireLens ATS features work identically on PostgreSQL with unified auth.

| # | Task | Test Gate |
|---|------|-----------|
| 0.1 | Install PostgreSQL 16 + pgvector locally | `pg_isready` returns "accepting connections" |
| 0.2 | Migrate SQLAlchemy from SQLite → PostgreSQL | All 3 existing tests pass |
| 0.3 | Alembic migration for existing 6 tables | `alembic upgrade head` succeeds |
| 0.4 | Unify frontend auth (use backend JWT) | Login → API call → protected route works |
| 0.5 | Add `role` column to User model | `require_admin()` dependency blocks non-admins |
| 0.6 | **VERIFY**: All ATS features still work | Manual test: upload resume → score → rewrite |

### Phase 1: Core Study Engine (Weeks 3-5)

**Ship Milestone**: A user can browse cards, study with FSRS, take quizzes, and pay $49/mo.

| # | Task | Test Gate |
|---|------|-----------|
| 1.1 | Extract 177 cards from JSX → PostgreSQL | `SELECT count(*) FROM cards` = 177 |
| 1.2 | Generate embeddings for all cards | `SELECT count(*) FROM cards WHERE embedding IS NOT NULL` = 177 |
| 1.3 | Cards API: list, by category, by ID, search | `pytest tests/test_cards_api.py` — 10+ assertions |
| 1.4 | FSRS study service + API | `pytest tests/test_study_service.py` — scheduling accuracy |
| 1.5 | Study Dashboard UI (category grid) | Browser test: all categories visible |
| 1.6 | Card Viewer UI (flip + 4-tier tabs + quiz) | Browser test: flip animation, quiz submit |
| 1.7 | Daily 5 UI (FSRS queue) | Browser test: shows due cards |
| 1.8 | Stripe integration ($49/mo Pro) | Test: checkout session creates, webhook processes |
| 1.9 | Free tier gating (15 foundation cards) | Non-pro user blocked from full library |

### Phase 2: Gamification + Admin (Weeks 6-8)

**Ship Milestone**: Users have daily streaks, XP, badges. Admin can create/edit cards.

### Phase 3: ATS Bridge + Mission Mode (Weeks 9-11)

**Ship Milestone**: ATS skill gaps map to study cards. Mission Mode with countdown.

### Phase 4: Polish + Launch (Weeks 12-14)

**Ship Milestone**: Production deployment on custom domain with landing page.

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
5. SHIP (merge to main, deploy)
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

## Edge Cases
- What happens when...?

## Dependencies
- What must be built first?

## Test Plan
- Unit tests needed
- Integration tests needed
- Manual verification steps
```

### 3.3 Example Spec: FSRS Daily Review

```markdown
# SPEC: FSRS Daily Review ("Daily 5")

## Status: Approved

## Problem
Users study cards but forget them within days. Without spaced
repetition, the study engine is just a flashcard browser —
no better than Quizlet.

## Solution
Implement FSRS (Free Spaced Repetition Scheduler) to schedule
card reviews at optimal intervals based on individual memory
patterns. Present a "Daily 5" queue each day.

## Acceptance Criteria
- [ ] AC-1: Given a user who has studied 10 cards, when they
      open Daily Review, they see only cards that FSRS has
      scheduled for today (≤5 cards per session).
- [ ] AC-2: Given a user rates a card "Good", the next review
      is scheduled 2-4 days later (FSRS stability increases).
- [ ] AC-3: Given a user rates a card "Again", the card
      re-appears in today's queue.
- [ ] AC-4: Given no cards are due, the UI shows "All caught up! 🎉".
- [ ] AC-5: Given a free-tier user, Daily Review is limited to
      Foundation cards only.

## API Contract
### Endpoints
- `GET /api/v1/study/daily`
  - Response: `{ cards: Card[], total_due: int, completed: int }`
  - Errors: `401`
- `POST /api/v1/study/review`
  - Request: `{ card_id: str, rating: "again"|"hard"|"good"|"easy" }`
  - Response: `{ next_due: datetime, stability: float, remaining: int }`
  - Errors: `401`, `404 (card not found)`

## Data Model
- Uses existing `card_progress` table (FSRS columns)
- `stability`, `difficulty_fsrs`, `due_date`, `state`

## Test Plan
- Unit: FSRS scheduling algorithm outputs (5 test cases)
- Integration: API returns correct cards for a user with
  mixed due dates
- E2E: Browser test — rate card → check it disappears from queue
```

### 3.4 Where to Store Specs

```
docs/
├── specs/
│   ├── phase-0/
│   │   ├── 00-postgresql-migration.md
│   │   ├── 01-auth-unification.md
│   │   └── 02-user-roles.md
│   ├── phase-1/
│   │   ├── 03-card-extraction.md
│   │   ├── 04-cards-api.md
│   │   ├── 05-fsrs-daily-review.md
│   │   ├── 06-study-dashboard-ui.md
│   │   ├── 07-card-viewer-ui.md
│   │   └── 08-stripe-integration.md
│   ├── phase-2/
│   │   └── ...
│   └── phase-3/
│       └── ...
├── prd.md                    ← This document's Section 1
└── architecture.md           ← System architecture diagram
```

---

## 4. AGENTS.md & Skills System

### 4.1 What Is AGENTS.md?

`AGENTS.md` is the **single source of truth** that tells Claude Code (or any AI coding agent) HOW your project works. It replaces ad-hoc prompting with a living document that evolves with your codebase. Think of it as "onboarding docs for your AI pair programmer."

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

## Directory Structure
```
hireportai/
├── AGENTS.md                    ← YOU ARE HERE
├── CLAUDE.md                    ← Claude Code project rules
├── docs/
│   ├── specs/                   ← Feature specifications
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
│   └── scripts/                 ← One-off scripts
├── hirelens-frontend/
│   ├── src/
│   │   ├── components/          ← Reusable UI components
│   │   ├── pages/               ← Route pages
│   │   ├── context/             ← React contexts
│   │   ├── hooks/               ← Custom hooks
│   │   ├── services/            ← API client
│   │   └── types/               ← TypeScript types
│   └── tests/                   ← Vitest + RTL tests
└── scripts/                     ← Dev utility scripts
```

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

### Frontend (TypeScript/React)
- Functional components with hooks only (no class components)
- Use `useQuery`/`useMutation` pattern for API calls
- All API calls go through `services/api.ts` with auth headers
- Dark mode by default (#0A0A0B base, brand gradients)
- Framer Motion for all animations
- Mobile-first responsive design
- Naming: `PascalCase` for components, `camelCase` for functions

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

## Key Decisions Log
- Auth: Google OAuth + JWT (NOT Clerk — migrating later for B2B)
- FSRS: py-fsrs library, server-side only
- LLM: Gemini 2.5 Pro for reasoning, Flash for speed tasks
- Storage: R2 for files (zero egress), PostgreSQL for data
- Analytics: PostHog Cloud (free tier)
- No Docker for dev — use local PostgreSQL + Redis via Homebrew
```

### 4.3 Per-Feature Skill Files

Skill files give Claude Code (and your future self) deep context about specific features. Store them at `.agent/skills/`.

```
.agent/
├── skills/
│   ├── study-engine.md       ← FSRS, Daily 5, card progress
│   ├── ats-scanner.md        ← ATS scoring, skill gaps, rewrite
│   ├── gamification.md       ← Streaks, XP, badges, heatmap
│   ├── mission-mode.md       ← Interview sprint, countdown
│   ├── experience-gen.md     ← AI personalized experiences
│   ├── admin-panel.md        ← Card CRUD, bulk import, AI assist
│   ├── card-extraction.md    ← JSX → PostgreSQL pipeline
│   └── testing.md            ← Test patterns, fixtures, mocks
└── workflows/
    ├── new-feature.md        ← How to add a new feature end-to-end
    ├── new-api-route.md      ← How to add a backend API route
    ├── new-ui-page.md        ← How to add a frontend page
    ├── run-tests.md          ← How to run all tests
    ├── db-migration.md       ← How to create an Alembic migration
    └── deploy.md             ← How to deploy to production
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

## Testing Checklist
- [ ] FSRS "Good" rating increases interval by 2-4x
- [ ] FSRS "Again" rating resets card to today
- [ ] Daily 5 returns max 5 cards
- [ ] Daily 5 returns empty list when nothing is due
- [ ] Free users only get Foundation category cards
- [ ] XP is awarded on each review (calls gamification service)
```

### 4.5 Example Workflow: Adding a New Feature

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

10. **Implement frontend page/component**
    - Create page in `src/pages/FeatureName.tsx`
    - Add route in `App.tsx`
    - Add API client method in `services/api.ts`

// turbo
11. Run `cd hirelens-frontend && npx vitest run`

12. **Manual verification**
    - Open browser, test the feature end-to-end
    - Test on mobile viewport

13. **Git commit**
    ```bash
    git add -A
    git commit -m "feat(feature): add feature_name — closes spec #NN"
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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
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
        # Inject test auth token (pro user by default)
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
  5. Commit
```

### 5.4 Concrete Test Examples

**Unit Test — FSRS Scheduling:**
```python
# tests/test_study_service.py

import pytest
from app.services.study_service import StudyService
from datetime import datetime, timedelta

class TestFSRSScheduling:
    async def test_good_rating_increases_interval(self, db_session):
        service = StudyService(db_session)
        card_progress = await service.create_progress("user-1", "rag-1")
        
        result = await service.review_card("user-1", "rag-1", "good")
        
        assert result.due_date > datetime.utcnow() + timedelta(days=1)
        assert result.stability > 0
        assert result.state == "review"

    async def test_again_rating_resets_to_today(self, db_session):
        service = StudyService(db_session)
        await service.create_progress("user-1", "rag-1")
        
        result = await service.review_card("user-1", "rag-1", "again")
        
        assert result.due_date <= datetime.utcnow() + timedelta(minutes=10)
        assert result.state == "relearning"
        assert result.lapses == 1

    async def test_daily_five_returns_max_five(self, db_session):
        service = StudyService(db_session)
        # Create 10 cards all due today
        for i in range(10):
            await service.create_progress("user-1", f"card-{i}",
                due_date=datetime.utcnow() - timedelta(hours=1))
        
        daily = await service.get_daily_review("user-1")
        
        assert len(daily.cards) <= 5
        assert daily.total_due == 10
```

**Integration Test — Cards API:**
```python
# tests/test_cards_api.py

class TestCardsAPI:
    async def test_list_categories(self, client):
        response = await client.get("/api/v1/cards")
        assert response.status_code == 200
        data = response.json()
        assert len(data["categories"]) > 0
        assert "card_count" in data["categories"][0]

    async def test_requires_auth(self, client):
        client.headers.pop("Authorization")
        response = await client.get("/api/v1/study/daily")
        assert response.status_code == 401

    async def test_free_user_sees_only_foundation(self, client_free_tier):
        response = await client_free_tier.get("/api/v1/cards")
        data = response.json()
        accessible = [c for c in data["categories"] if c["accessible"]]
        assert len(accessible) == 1
        assert accessible[0]["name"] == "Foundations"
```

### 5.5 Alembic Migration Rollback Testing

> [!WARNING]
> **A migration that can't `downgrade` is a one-way door.** If your deploy breaks in production, you can't revert the database. Test this LOCALLY on every migration.

```bash
# After creating any new Alembic migration, run this gauntlet:
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

**If `downgrade -1` fails**, the migration has a bug — likely a missing `op.drop_table()` or `op.drop_column()` in the `downgrade()` function. Fix it before committing.

**Add this to CI as well:**
```yaml
# In .github/workflows/ci.yml, add after backend-tests:
  migration-rollback:
    runs-on: ubuntu-latest
    services:
      postgres: { ... }  # same as backend-tests
    steps:
      - run: |
          cd hirelens-backend
          alembic upgrade head
          alembic downgrade -1
          alembic upgrade head
```

### 5.6 Coverage Targets

| Component | Target | Tool |
|-----------|--------|------|
| Backend services | 85% | `pytest --cov=app/services` |
| Backend API routes | 80% | `pytest --cov=app/api` |
| Frontend components | 70% | `vitest --coverage` |
| Overall | 80% | CI gate |

### 5.7 Running Tests

```bash
# Backend — all tests
cd hirelens-backend && python -m pytest tests/ -v --tb=short

# Backend — specific file
python -m pytest tests/test_study_service.py -v

# Backend — with coverage
python -m pytest tests/ --cov=app --cov-report=term-missing

# Backend — migration rollback gauntlet
alembic upgrade head && alembic downgrade -1 && alembic upgrade head

# Frontend — all tests  
cd hirelens-frontend && npx vitest run

# Frontend — watch mode
npx vitest

# Frontend — with coverage
npx vitest run --coverage
```

---

## 6. Claude Code Best Practices

### 6.1 The "Context-Slice-Test-Ship" Loop

> [!IMPORTANT]
> **This is the most important section in this document.**

Claude Code works best when you give it **focused, bounded tasks** with clear success criteria. Here's the optimal loop:

```
┌─────────────────────────────────────────────────────┐
│  1. CONTEXT                                          │
│     Load the right files into Claude Code's context  │
│     → AGENTS.md + spec file + relevant skill file    │
│     → "Read docs/specs/phase-1/05-fsrs-daily.md"     │
├─────────────────────────────────────────────────────┤
│  2. SLICE                                            │
│     Give ONE task that takes ~30 minutes              │
│     → "Implement the FSRS study service with tests"  │
│     → NOT "Build the entire study engine"            │
├─────────────────────────────────────────────────────┤
│  3. TEST                                             │
│     Ask Claude Code to run the tests immediately     │
│     → "Run pytest tests/test_study_service.py -v"    │
│     → Fix until GREEN                                │
├─────────────────────────────────────────────────────┤
│  4. SHIP                                             │
│     Commit the working slice                         │
│     → "git add -A && git commit -m 'feat(study):..'" │
│     → Move to next slice                             │
└─────────────────────────────────────────────────────┘
```

### 6.2 Task Decomposition — The 30-Minute Slice Rule

> [!WARNING]
> **Never give Claude Code a task that would take YOU more than 2 hours to do manually.** Break it into 30-minute slices.

**❌ BAD: "Build the study engine"**
This is 3-5 days of work. Claude Code will produce inconsistent code, miss edge cases, and create a Frankenstein.

**✅ GOOD: Slice it into 8-10 tasks:**

```
Slice 1: "Create the card_progress SQLAlchemy model and Alembic migration"
Slice 2: "Create the study Pydantic schemas (request + response models)"
Slice 3: "Implement StudyService.get_daily_review() with py-fsrs"
Slice 4: "Write 5 unit tests for FSRS scheduling in test_study_service.py"
Slice 5: "Implement StudyService.review_card() with rating logic"
Slice 6: "Create /api/v1/study/ routes (daily, review, progress)"
Slice 7: "Write integration tests for study API endpoints"
Slice 8: "Build DailyReview.tsx frontend page with card queue"
Slice 9: "Build ReviewCard.tsx component with rating buttons"
Slice 10: "Wire up API calls and test end-to-end in browser"
```

Each slice: write → test → commit → next.

### 6.3 The Updated CLAUDE.md

Replace the existing `CLAUDE.md` with this enhanced version:

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
7. **No console.log in production**: Use proper logging (backend: `logger`, frontend: remove before commit)
8. **🚨 AI Loop Breaker (3-Strike Rule)**: If a test fails 3 times in a row during the RED-GREEN-REFACTOR cycle, **STOP IMMEDIATELY**. Do NOT attempt another fix. Instead: (a) print the exact error message, (b) explain what you think is wrong, (c) list 2-3 hypotheses for the root cause, and (d) wait for human intervention. This prevents burning API tokens and prevents "fix cascades" where each attempt introduces a new bug.

## How to Add a Feature
1. Check spec exists in `docs/specs/`
2. Create/update backend models in `app/models/`
3. Create Alembic migration: `alembic revision --autogenerate -m "description"`
4. Apply: `alembic upgrade head`
5. Create Pydantic schemas in `app/schemas/`
6. Write tests in `tests/`
7. Implement service in `app/services/`
8. Create API route in `app/api/routes/`
9. Register route in `app/main.py`
10. Run: `python -m pytest tests/ -v`
11. Implement frontend (page → component → hook → API client)
12. Run: `npx vitest run`

## Environment
- Python 3.13, Node 20, PostgreSQL 16 + pgvector, Redis 7
- Backend: FastAPI, SQLAlchemy 2.0 async, py-fsrs, google-genai
- Frontend: React 18, TypeScript 5, Vite 5, Tailwind, Framer Motion
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

Update `.claude/settings.local.json` for the new project structure:

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

## 7. Local Mac Setup

### 7.1 Prerequisites Check

Your system already has:
- ✅ macOS 26.2
- ✅ Python 3.13.3
- ✅ Node.js 20.19.2 + npm 10.8.2
- ✅ Homebrew 5.1.0
- ✅ Redis 7.2.5
- ✅ Git 2.46.0
- ✅ Claude Code 2.1.76
- ✅ PostgreSQL (via Homebrew — needs to be started)
- ❌ Docker (not installed — we'll use local services instead)

### 7.2 Step-by-Step Setup

#### Step 1: Start PostgreSQL

```bash
# Start PostgreSQL service
brew services start postgresql@16

# Verify it's running
pg_isready
# Expected: "localhost:5432 - accepting connections"

# Create the databases
createdb hireport
createdb hireport_test

# Install pgvector extension
psql -d hireport -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d hireport -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
psql -d hireport_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d hireport_test -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"

# Create a dedicated user (optional, can use your default user)
psql -d hireport -c "CREATE USER hireport WITH PASSWORD 'dev_password';"
psql -d hireport -c "GRANT ALL PRIVILEGES ON DATABASE hireport TO hireport;"
psql -d hireport_test -c "GRANT ALL PRIVILEGES ON DATABASE hireport_test TO hireport;"
```

> [!NOTE]
> If pgvector isn't installed: `brew install pgvector`
> Then restart PostgreSQL: `brew services restart postgresql@16`

> [!WARNING]
> **The macOS pgvector Gotcha**: Homebrew sometimes installs pgvector's `.so` file into a directory that doesn't match your `postgresql@16` extension path. If `CREATE EXTENSION vector;` fails with `could not open extension control file`, the Homebrew install put the files in the wrong place.
>
> **Fix — compile pgvector from source:**
> ```bash
> # 1. Find your PostgreSQL config
> pg_config --sharedir   # e.g., /opt/homebrew/opt/postgresql@16/share/postgresql
>
> # 2. Build pgvector from source targeting that path
> git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git /tmp/pgvector
> cd /tmp/pgvector
> make PG_CONFIG=$(which pg_config)
> make install PG_CONFIG=$(which pg_config)
>
> # 3. Restart PostgreSQL and retry
> brew services restart postgresql@16
> psql -d hireport -c "CREATE EXTENSION vector;"
> ```
> Keep this in your back pocket — you likely won't need it, but if Step 1 throws a `could not open extension` error, this is the escape hatch.

#### Step 2: Start Redis

```bash
# Start Redis service
brew services start redis

# Verify
redis-cli ping
# Expected: "PONG"
```

#### Step 3: Backend Setup

```bash
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai/hirelens-backend

# Create fresh venv
python3 -m venv venv
source venv/bin/activate

# Install existing + new dependencies
pip install -r requirements.txt

# Install NEW dependencies for SkillForge
pip install asyncpg pgvector py-fsrs redis posthog pytest-asyncio httpx

# Download spaCy model
python -m spacy download en_core_web_sm

# Create .env file
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

# Analytics (optional for now)
POSTHOG_API_KEY=phc_...
EOF

# Verify backend starts
uvicorn app.main:app --reload --port 8000
# Visit: http://localhost:8000/docs
```

#### Step 4: Frontend Setup

```bash
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai/hirelens-frontend

# Install dependencies
npm install

# Install NEW dependencies for SkillForge
npm install recharts@latest @tanstack/react-query zustand

# Install dev dependencies for testing
npm install -D vitest @testing-library/react @testing-library/jest-dom @vitest/coverage-v8 jsdom

# Create/update .env
cat > .env << 'EOF'
VITE_API_BASE_URL=
VITE_GOOGLE_CLIENT_ID=your-google-client-id
EOF

# Start dev server
npm run dev -- --port 5199
# Visit: http://localhost:5199
```

#### Step 5: Project Scaffold

```bash
cd /Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/SkillForge/hireportai

# Create directory structure
mkdir -p docs/specs/{phase-0,phase-1,phase-2,phase-3,phase-4}
mkdir -p .agent/{skills,workflows}
mkdir -p hirelens-backend/scripts
mkdir -p hirelens-frontend/tests

# Create AGENTS.md at project root  
# (use the content from Section 4.2 above)

# Update CLAUDE.md
# (use the content from Section 6.3 above)
```

#### Step 6: Verify Everything Works

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

### 7.3 The Developer Workflow (Daily Routine)

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

### 8.1 GitHub Actions (Future — When Ready to Deploy)

```yaml
# .github/workflows/ci.yml
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
```

### 8.2 Deployment Targets (Phase 4)

| Component | Platform | Why |
|-----------|----------|-----|
| Frontend | Vercel | Zero-config React deployment, edge CDN |
| Backend | Railway | Easy Python hosting, managed PostgreSQL option |
| Database | Railway PostgreSQL or Supabase | Managed, pgvector included |
| Files | Cloudflare R2 | Zero egress costs for resumes |
| Redis | Railway Redis or Upstash | Managed, free tier available |

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
│  COMMIT:                                              │
│    git add -A                                         │
│    git commit -m "type(scope): description"           │
│                                                       │
│  CLAUDE CODE:                                         │
│    "Read AGENTS.md. Read the spec. Do Slice N."       │
│    "Run the tests." "Commit."                         │
│                                                       │
│  URLS:                                                │
│    Frontend:  http://localhost:5199                    │
│    Backend:   http://localhost:8000                    │
│    Swagger:   http://localhost:8000/docs               │
│    DB:        psql -d hireport                        │
│    Redis:     redis-cli                               │
└──────────────────────────────────────────────────────┘
```

---
*SkillForge Master Development Playbook v1.0 — Prepared by your CTO/Growth Partner/Architect/VC*
