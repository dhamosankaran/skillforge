# SkillForge — Implementation Plan v2.0

## Goal

Build SkillForge as a **career acceleration platform** with a Dual-Track architecture:

1. **The Forge / Academy** (Retention Engine) — Daily-use study system with FSRS spaced repetition, streaks, XP, skill badges, and full card library
2. **Mission Mode** (Conversion Engine) — Focused interview sprint with ATS tracking + AI-generated personalized experiences
3. **ATS Scanner** (Acquisition Engine) — Free skill gap analysis that converts to paid

**MVP Scope**: Core Study Engine first → then ATS/Mission Mode → then B2B

> See [strategic_review.md](file:///Users/kalaidhamu/.gemini/antigravity/brain/c0639d8c-1bc7-4106-9f30-147ef512f0a0/strategic_review.md) for the full CTO/VC analysis.

---

## Confirmed Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Frontend** | React + Vite | Extend existing dashboard, fast DX |
| **Backend** | FastAPI (Python) | Best LLM ecosystem, async, fast |
| **Database** | PostgreSQL + pgvector | Relational + vector search in one |
| **LLM Provider** | **Google Gemini** | Gemini 2.5 Pro (reasoning), 2.0 Flash (fast tasks) |
| **Auth** | **Clerk** | Fast integration, free tier for MVP |
| **Frontend Hosting** | **Vercel** | Zero-config React deploys |
| **Backend Hosting** | **Railway or Render** | Easy MVP, Dockerized for AWS migration |
| **Payments** | Stripe | Industry standard |
| **Analytics** | PostHog (self-hostable) | Product analytics + feedback |
| **Cache** | Redis | Session cache, rate limiting |
| **File Storage** | **Cloudflare R2** | Zero egress fees — critical if ATS goes viral |

### AWS Migration Path (Built-In From Day 1)

The architecture is **containerized** from the start so moving from Railway → AWS is a config change, not a rewrite:

```
MVP (Month 1-6)                    Scale (Month 6+)
─────────────────                   ─────────────────
Vercel (frontend)        →          CloudFront + S3
Railway (backend)        →          ECS Fargate or EKS
Railway PostgreSQL       →          RDS PostgreSQL
Railway Redis            →          ElastiCache
Cloudflare R2 (files)    →          S3 (egress negligible at scale)
PostHog Cloud            →          Self-hosted PostHog on ECS
```

**How we ensure portability:**
- All backend services are **Dockerized** (`Dockerfile` + `docker-compose.yml`)
- All config via **environment variables** (no hardcoded Railway URLs)
- Database migrations via **Alembic** (works on any PostgreSQL)
- S3-compatible file storage via **R2** (works with R2, MinIO, or real S3 — same API)
- **Terraform templates** included (commented out for MVP, ready for AWS)

---

## Gemini LLM Architecture

> [!IMPORTANT]
> **Key decision**: Use Gemini's **reasoning model** to dynamically decide what to retrieve and how to generate responses — not rigid template-based prompts.

### Model Routing Strategy

| Task | Model | Why | Cost/1K calls |
|------|-------|-----|---------------|
| Resume parsing (structured extraction) | **Gemini 2.0 Flash** | Fast, cheap, great at structured output | ~$0.002 |
| ATS evaluation (gap analysis) | **Gemini 2.5 Pro** | Needs reasoning to assess skill depth | ~$0.01 |
| Experience generation (**async pre-gen**) | **Gemini 2.5 Pro** (with thinking) | Pre-generated in background, cached in DB | ~$0.015 |
| Quiz feedback & explanations | **Gemini 2.0 Flash** | Simple, fast feedback | ~$0.001 |
| Card search & recommendations | **Gemini text-embedding-005** | Embedding for vector similarity | ~$0.0001 |
| Admin: AI card generation | **Gemini 2.5 Pro** | Quality content creation | ~$0.02 |
| Feedback summarization | **Gemini 2.0 Flash** | Aggregate user feedback themes | ~$0.003 |

> [!IMPORTANT]
> **Experience Generation Latency Fix**: Gemini 2.5 Pro thinking mode takes 4-8 seconds. Experiences are **pre-generated asynchronously** when a user uploads a resume or starts a Mission — NOT on card flip. The frontend fetches cached results instantly from the `generated_experiences` table. See [cto_challenge_and_execution.md](file:///Users/kalaidhamu/.gemini/antigravity/brain/c0639d8c-1bc7-4106-9f30-147ef512f0a0/cto_challenge_and_execution.md) for the exact async pattern.

### Reasoning Model for Dynamic Experience Generation

Instead of rigid template prompts, the reasoning model **decides what information to retrieve and how to use it**:

```python
# services/experience_gen.py — Gemini reasoning decides the strategy

class ExperienceGenerator:
    """Uses Gemini 2.5 Pro's reasoning to dynamically generate 
    personalized experiences. The model REASONS about what resume 
    context is relevant, then generates the answer."""
    
    async def generate(self, card: Card, resume: ParsedResume) -> str:
        # Step 1: Retrieve candidate resume bullets via vector search
        candidate_bullets = await self.vector_search(
            query=card.question + " " + " ".join(card.tags),
            corpus=resume.experience_bullets,
            top_k=5
        )
        
        # Step 2: Let Gemini REASON about which bullets are relevant
        # and HOW to construct the experience answer
        response = await self.gemini.generate(
            model="gemini-2.5-pro",
            config={"thinking": True},  # Enable reasoning
            contents=f"""
You are an interview coach helping an engineer prepare their personal 
experience answer for a technical interview question.

INTERVIEW QUESTION:
{card.question}

TECHNICAL CONCEPT (for context):
{card.answer}

CANDIDATE'S RESUME EXPERIENCE (from their actual resume):
{self._format_bullets(candidate_bullets)}

YOUR TASK:
1. REASON about which resume experiences are most relevant to this question
2. DECIDE if the candidate has direct experience or adjacent experience
3. If direct: craft a STAR-format answer using their real projects and metrics
4. If adjacent: adapt their closest experience to demonstrate transferable skills
5. Include SPECIFIC metrics and technologies from their resume
6. Sound natural — like a confident engineer telling their story, not a robot

Generate a 2-3 paragraph "How I Applied This" answer.
"""
        )
        return response.text
```

### Why Reasoning Model > Rigid Templates

| Aspect | Rigid Template | Gemini Reasoning |
|--------|---------------|-----------------|
| Resume with direct match | ✅ Works well | ✅ Works well |
| Resume with partial match | ❌ Awkward forced fit | ✅ Adapts, finds adjacent experience |
| Resume with no match | ❌ Generates hallucinated experience | ✅ Honestly says "here's how you could frame it" |
| Different question types | ❌ One template for all | ✅ Adjusts approach per question type |
| Quality improvement | Manual prompt tweaking | Model improves with better reasoning |

---

## Content Extraction Strategy

### Step 1: Extract Cards from JSX → JSON → Database

The 177+ flashcards currently live in two monolithic JSX files. We need to:

1. Parse `ai_genai_interview_dashboard.jsx` and `chase_interview_flashcards.jsx`
2. Extract each card's structured data (question, answer, experience, quiz, tags, difficulty)
3. **Anonymize all enterprise references** (see below)
4. Store in PostgreSQL with pgvector embeddings
5. Provide an Admin UI for ongoing management

### Anonymization Rules (Remove All Specific Company References)

| Before (Current) | After (Anonymized) |
|-------------------|--------------------|
| "At Citi, we built..." | "At a Fortune 100 financial institution, we built..." |
| "Citi's internal red team" | "The organization's internal red team" |
| "Our Citi-Bench" | "Our internal domain benchmark" |
| Specific team member names | Remove entirely |
| "Citi's LDAP" | "The enterprise LDAP" |
| Exact dollar amounts tied to company | Keep amounts, remove company: "$3.2M annual savings at a major bank" |

**Automated approach:**
```python
ANONYMIZATION_RULES = {
    r"\bCiti\b": "a Fortune 100 financial institution",
    r"\bCiti's\b": "the organization's",
    r"\bat Citi\b": "at a Fortune 100 financial institution",
    r"Citi-Bench": "an internal domain benchmark",
    r"Citi-specific": "enterprise-specific",
}
```

> [!NOTE]
> The "expert experience" sections become **example enterprise experiences** — templates that show users what good answers look like. The real magic is the Gemini reasoning model generating **their own** personalized experiences from **their resume**.

### Card Data Format (Database-Ready JSON)

```json
{
  "id": "rag-1",
  "category": "RAG Architecture",
  "category_icon": "🔗",
  "category_color": "#10B981",
  "question": "Design a production-grade RAG system end-to-end...",
  "answer": "Complete RAG Pipeline:\n\n📥 INGESTION:...",
  "expert_experience": "At a Fortune 100 financial institution, I architected the enterprise RAG platform serving 15 internal applications...",
  "difficulty": "Hard",
  "tags": ["RAG", "System Design"],
  "quiz": {
    "question": "What is the primary benefit of hybrid search?",
    "options": ["...", "...", "...", "..."],
    "correct": 1,
    "explanation": "..."
  },
  "skill_keywords": ["rag", "vector-db", "embeddings", "chunking", "reranking"],
  "prerequisites": ["tf-1"],
  "domain": "ai_ml"
}
```

---

## Feature: Admin Panel

### Admin Dashboard Capabilities

```
┌───────────────────────────────────────────────────────────┐
│                 SKILLFORGE ADMIN PANEL                     │
│                 (Role: admin in Clerk)                     │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  📚 CONTENT MANAGEMENT                                    │
│  ├── Card Library (CRUD)                                  │
│  │   ├── Add new card (manual or AI-assisted)             │
│  │   ├── Edit existing card (inline editor)               │
│  │   ├── Delete card (soft delete, audit trail)           │
│  │   ├── Reorder cards within category                    │
│  │   ├── Bulk import (JSON/CSV upload)                    │
│  │   └── Bulk export (JSON download)                      │
│  ├── Category Management                                  │
│  │   ├── Add/edit/reorder categories                      │
│  │   └── Set category icon + colors                       │
│  └── AI Card Generator                                    │
│      ├── Paste a topic → Gemini generates card draft      │
│      ├── Review + edit before publishing                  │
│      └── Bulk generate cards for a new domain             │
│                                                           │
│  📊 ANALYTICS DASHBOARD                                   │
│  ├── User Metrics                                         │
│  │   ├── DAU / WAU / MAU                                  │
│  │   ├── New signups (daily/weekly trend)                  │
│  │   ├── Active subscriptions + MRR                       │
│  │   ├── Churn rate + churned user analysis                │
│  │   └── Cohort retention curves                          │
│  ├── Engagement Metrics                                   │
│  │   ├── Cards studied per session (avg, median)          │
│  │   ├── Quiz accuracy by category                        │
│  │   ├── Most studied / least studied cards               │
│  │   ├── Average session duration                         │
│  │   ├── Streak distribution (how many on 7+, 30+ day)   │
│  │   └── Daily 5 completion rate                          │
│  ├── Content Metrics                                      │
│  │   ├── Card difficulty ratings (user-reported)          │
│  │   ├── Cards with lowest mastery rate (need rework?)    │
│  │   ├── Most bookmarked cards                            │
│  │   └── Quiz questions with highest miss rate            │
│  └── Revenue Metrics                                      │
│      ├── MRR / ARR                                        │
│      ├── Conversion rate (free → pro)                     │
│      ├── ATS scans → subscription conversion              │
│      └── Revenue by cohort                                │
│                                                           │
│  💬 CUSTOMER FEEDBACK                                      │
│  ├── In-app feedback inbox                                │
│  │   ├── Per-card feedback ("This card was confusing")    │
│  │   ├── General feedback ("I wish you had X topic")      │
│  │   └── Bug reports                                      │
│  ├── NPS Survey results (triggered at day 7, 30, 90)      │
│  ├── Feature request board (vote + prioritize)            │
│  ├── Feedback themes (Gemini-summarized weekly digest)    │
│  └── User interviews / contact queue                      │
│                                                           │
│  👥 USER MANAGEMENT                                       │
│  ├── User list with search/filter                         │
│  ├── View user progress + activity                        │
│  ├── Manage subscriptions                                 │
│  └── Impersonate user (for debugging, with audit log)     │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Admin Card Editor — Detailed Flow

```
┌─ ADD / EDIT CARD ──────────────────────────────────────────┐
│                                                            │
│  Category: [RAG Architecture     ▾]                        │
│  Card ID:  [rag-6] (auto-generated or manual)              │
│                                                            │
│  ┌─ QUESTION ───────────────────────────────────────────┐  │
│  │ Rich text editor with markdown preview               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─ ANSWER ─────────────────────────────────────────────┐  │
│  │ Rich text editor with markdown preview               │  │
│  │ Supports: headers, bullets, code blocks, emojis      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─ EXPERT EXPERIENCE ──────────────────────────────────┐  │
│  │ "At a Fortune 100 financial institution..."          │  │
│  │ [🤖 Generate with AI] ← Gemini drafts from answer   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  Difficulty: ( ) Medium  (•) Hard                          │
│  Tags: [RAG] [Vector DB] [Production] [+ Add tag]         │
│                                                            │
│  ┌─ QUIZ ───────────────────────────────────────────────┐  │
│  │ Question: [________________________________]         │  │
│  │ Option A: [________________________________] ( )     │  │
│  │ Option B: [________________________________] (•) ✓   │  │
│  │ Option C: [________________________________] ( )     │  │
│  │ Option D: [________________________________] ( )     │  │
│  │ Explanation: [_____________________________]         │  │
│  │ [🤖 Auto-generate quiz from card content]            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─ AI ASSIST ──────────────────────────────────────────┐  │
│  │ [🤖 Generate entire card from topic]                 │  │
│  │ Topic: "Explain RLHF vs DPO for fine-tuning"        │  │
│  │ → Gemini generates: question, answer, expert exp,   │  │
│  │   quiz, tags, difficulty — you review + publish      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  [Preview] [Save Draft] [Publish] [Delete]                 │
└────────────────────────────────────────────────────────────┘
```

### Bulk Import/Export Format

```json
// Export format — also used for import
{
  "version": "1.0",
  "exported_at": "2026-04-06T21:57:20Z",
  "categories": [
    {
      "name": "RAG Architecture",
      "icon": "🔗",
      "color": "#10B981",
      "cards": [
        {
          "id": "rag-1",
          "question": "...",
          "answer": "...",
          "expert_experience": "...",
          "difficulty": "Hard",
          "tags": ["RAG", "System Design"],
          "quiz": { "question": "...", "options": [], "correct": 1, "explanation": "..." }
        }
      ]
    }
  ]
}
```

**Admin import flow:**
1. Upload JSON file
2. System validates against schema
3. Preview: shows new cards, updated cards, conflicts
4. Admin confirms → cards upserted to database
5. Embeddings auto-generated for new/updated cards

---

## Feature: Analytics Dashboard

### Data Collection Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   DATA PIPELINE                           │
│                                                          │
│  Frontend Events          Backend Events                 │
│  ──────────────          ──────────────                  │
│  • page_view             • api_call                      │
│  • card_flip             • llm_request (model, tokens,   │
│  • card_master           •   latency, cost)              │
│  • quiz_answer           • resume_parsed                 │
│  • session_start/end     • ats_scored                    │
│  • streak_updated        • experience_generated          │
│  • feedback_submitted    • subscription_created          │
│  • search_query          • subscription_cancelled        │
│                                                          │
│         ↓                         ↓                      │
│  ┌──────────────────────────────────────┐                │
│  │         PostHog (Analytics)          │                │
│  │  • Event tracking                    │                │
│  │  • User identification               │                │
│  │  • Cohort analysis                   │                │
│  │  • Funnel visualization              │                │
│  │  • Retention charts                  │                │
│  │  • Feature flags (for A/B tests)     │                │
│  └──────────────────────────────────────┘                │
│         ↓                                                │
│  ┌──────────────────────────────────────┐                │
│  │      Admin Dashboard (Custom)        │                │
│  │  • Real-time metrics                 │                │
│  │  • Content performance               │                │
│  │  • Revenue tracking                  │                │
│  │  • LLM cost monitoring               │                │
│  └──────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────┘
```

### Dashboard Views

**1. Overview Dashboard (Home)**
```
┌─ TODAY ──────────────────────────────────────────────────┐
│  DAU: 342    WAU: 1,205    MAU: 3,891    MRR: $24,500   │
│  ▲ 8%        ▲ 12%         ▲ 15%         ▲ 18%          │
├──────────────────────────────────────────────────────────┤
│  New Signups (7d)     Cards Studied (7d)    NPS Score    │
│  ████████ 89          █████████ 12,450      ████ 72      │
├──────────────────────────────────────────────────────────┤
│  [Engagement Trend - 30d line chart]                     │
│  [Revenue Trend - 30d line chart]                        │
│  [Conversion Funnel: Visit→Signup→Free→Paid]             │
└──────────────────────────────────────────────────────────┘
```

**2. Content Performance**
```
┌─ CARD ANALYTICS ─────────────────────────────────────────┐
│                                                          │
│  Hardest Cards (lowest mastery rate):                    │
│  1. sec-7: AI Agent Security Playbook    — 23% mastery   │
│  2. ce-4: Graduated Compression          — 31% mastery   │
│  3. rag-3: Advanced RAG Patterns         — 35% mastery   │
│                                                          │
│  Most Popular Cards (highest study count):                │
│  1. pe-1: Prompt Engineering Techniques  — 4,521 views   │
│  2. rag-1: Production RAG Design         — 3,892 views   │
│  3. ai-35: MCP Architecture              — 3,104 views   │
│                                                          │
│  Quiz Miss Rate (questions users get wrong most):        │
│  1. sec-6: Model Armor Floor Settings    — 67% miss      │
│  2. tf-1: MoE Expert Routing            — 58% miss       │
│  3. pe-4: Prompt Cache Stacking          — 54% miss      │
│                                                          │
│  [Heatmap: Category × Difficulty → Mastery Rate]         │
└──────────────────────────────────────────────────────────┘
```

**3. LLM Cost Monitor**
```
┌─ LLM USAGE (MTD) ───────────────────────────────────────┐
│                                                          │
│  Total Spend: $287.40        Budget: $500                │
│  ████████████████░░░░░░░░░ 57%                           │
│                                                          │
│  By Model:                                               │
│  Gemini 2.5 Pro:  $198  (experience gen, ATS eval)       │
│  Gemini 2.0 Flash: $67  (parsing, quiz feedback)         │
│  Embedding:        $22  (text-embedding-005)             │
│                                                          │
│  By Feature:                                             │
│  Experience Generation:  $142  (49%)                     │
│  ATS Scoring:            $68   (24%)                     │
│  Resume Parsing:         $34   (12%)                     │
│  Admin AI Assist:        $28   (10%)                     │
│  Quiz Feedback:          $15   (5%)                      │
│                                                          │
│  [Daily cost trend - 30d chart]                          │
│  [Cost per user trend]                                   │
└──────────────────────────────────────────────────────────┘
```

---

## Feature: Customer Feedback System

### Three Feedback Channels

**1. Per-Card Micro-Feedback**

When studying any card, users see a subtle feedback option:

```
┌─ CARD: rag-1 ─────────────────────────────────────────┐
│                                                        │
│  [Card content...]                                     │
│                                                        │
│  ─────────────────────────────────────────────────────  │
│  Was this helpful?  👍  👎  │  💬 Leave feedback        │
│                                                        │
│  [If 👎 clicked:]                                      │
│  What's wrong?                                         │
│  ( ) Too basic    ( ) Too advanced   ( ) Outdated      │
│  ( ) Confusing    ( ) Missing info   ( ) Other: [___]  │
│  [Submit]                                              │
└────────────────────────────────────────────────────────┘
```

**2. NPS Surveys (Auto-Triggered)**

| Trigger | When | Question |
|---------|------|----------|
| Day 7 | After first week | "How likely are you to recommend SkillForge?" (0-10) |
| Day 30 | After first month | Same + "What's the #1 thing we could improve?" |
| Day 90 | Quarterly | Same + "Has SkillForge helped your career? How?" |
| Post-Mission | After completing a Mission | "Did Mission Mode help you feel prepared?" |
| Churn | When cancelling | "What made you cancel? What would bring you back?" |

**3. Feature Request Board**

```
┌─ FEATURE REQUESTS ──────────────────────────────────────┐
│                                                          │
│  Sort: [Most Voted ▾]   Filter: [All ▾]                 │
│                                                          │
│  ▲ 47  "Add Data Engineering / Spark cards"              │
│        Status: 🟡 Planned                                │
│                                                          │
│  ▲ 35  "Mock interview mode with AI interviewer"         │
│        Status: 🔵 Under Review                           │
│                                                          │
│  ▲ 28  "Mobile app (iOS/Android)"                        │
│        Status: 🔵 Under Review                           │
│                                                          │
│  ▲ 19  "Team leaderboards"                               │
│        Status: 🟢 In Progress                            │
│                                                          │
│  [Submit Feature Request]                                │
└──────────────────────────────────────────────────────────┘
```

### Feedback Data Model

```sql
-- Per-card feedback
CREATE TABLE card_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    card_id TEXT REFERENCES cards(id),
    rating TEXT CHECK (rating IN ('helpful', 'not_helpful')),
    issue_type TEXT,  -- 'too_basic', 'too_advanced', 'outdated', 'confusing', 'missing_info', 'other'
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- NPS surveys
CREATE TABLE nps_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    trigger TEXT NOT NULL,  -- 'day_7', 'day_30', 'day_90', 'post_mission', 'churn'
    score INTEGER CHECK (score BETWEEN 0 AND 10),
    feedback TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Feature requests
CREATE TABLE feature_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'submitted',  -- 'submitted', 'under_review', 'planned', 'in_progress', 'done', 'declined'
    vote_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE feature_votes (
    user_id UUID REFERENCES users(id),
    request_id UUID REFERENCES feature_requests(id),
    PRIMARY KEY (user_id, request_id)
);

-- Weekly AI-summarized feedback digest
CREATE TABLE feedback_digests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_start DATE,
    period_end DATE,
    summary TEXT,  -- Gemini-generated summary of all feedback
    top_themes JSONB,  -- ["Card X needs updating", "Users want mobile app"]
    nps_trend JSONB,   -- {"avg": 72, "promoters": 45, "passives": 30, "detractors": 12}
    action_items JSONB,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Weekly Feedback Digest (AI-Generated)

Every Monday, a scheduled job runs:

```python
# services/feedback_digest.py

async def generate_weekly_digest():
    """Gemini Flash summarizes all feedback from the past week."""
    
    week_feedback = await db.get_feedback_since(days=7)
    
    digest = await gemini.generate(
        model="gemini-2.0-flash",
        contents=f"""
Analyze this week's user feedback for SkillForge and produce an actionable digest.

CARD FEEDBACK ({len(week_feedback.card_feedback)} items):
{format_card_feedback(week_feedback.card_feedback)}

NPS RESPONSES ({len(week_feedback.nps)} items):
{format_nps(week_feedback.nps)}

FEATURE REQUESTS ({len(week_feedback.features)} new):
{format_features(week_feedback.features)}

Produce:
1. TOP 3 THEMES: Most common feedback patterns
2. URGENT ISSUES: Cards or features generating negative feedback
3. NPS TREND: Score compared to last week, promoter/detractor breakdown
4. ACTION ITEMS: Specific, prioritized tasks for this week
5. BRIGHT SPOTS: What users love most (use for marketing)
"""
    )
    
    await db.save_digest(digest)
    await notify_admin_email(digest)  # Send to your inbox
```

---

## Critical Architecture Decision: Multi-Agent

> [!IMPORTANT]
> ### Still: **NO multi-agent for MVP.** Use Gemini's reasoning model within deterministic pipelines.

Full analysis preserved from v1 — every SkillForge task is a deterministic pipeline + single LLM call:

| Task | Approach | Model |
|------|----------|-------|
| Resume parsing | Single structured output call | Gemini 2.0 Flash |
| ATS scoring | Embeddings + single evaluation call | text-embedding-005 + Gemini 2.5 Pro |
| Skill gap analysis | **Algorithmic** (no LLM) | None |
| Learning path generation | **Algorithmic** (topological sort, no LLM) | None |
| Experience generation | Single reasoning call per card | Gemini 2.5 Pro (thinking mode) |
| Quiz feedback | Single call | Gemini 2.0 Flash |
| Card CRUD (admin) | Standard REST API | None (AI-assist optional) |
| Feedback summarization | Single call (weekly batch) | Gemini 2.0 Flash |

**When to reconsider agents** (Phase 3+):
- AI mock interviewer with multi-turn, tool-using conversations
- Autonomous curriculum builder that researches and creates content
- Cross-platform learning coach that integrates with IDE, Slack, etc.

---

## Complete Data Model

```sql
-- ═══════════════════════════════════════════
-- USERS + AUTH
-- ═══════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_id TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    avatar_url TEXT,
    role TEXT DEFAULT 'user',  -- 'user', 'admin'
    plan TEXT DEFAULT 'free',  -- 'free', 'pro', 'enterprise'
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    org_id UUID,  -- FK added after organizations table
    timezone TEXT DEFAULT 'UTC',
    onboarding_goal TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════
-- CONTENT (Cards + Categories)
-- ═══════════════════════════════════════════

CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL,  -- 'rag-architecture'
    name TEXT NOT NULL,         -- 'RAG Architecture'
    icon TEXT,
    color TEXT,
    accent TEXT,
    display_order INTEGER,
    card_count INTEGER DEFAULT 0,
    source TEXT DEFAULT 'core',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE cards (
    id TEXT PRIMARY KEY,
    category_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    expert_experience TEXT,
    difficulty TEXT CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
    tags TEXT[] NOT NULL DEFAULT '{}',
    skill_keywords TEXT[] DEFAULT '{}',  -- For ATS matching
    prerequisites TEXT[] DEFAULT '{}',   -- Card IDs that should be studied first
    quiz_question TEXT,
    quiz_options JSONB,
    quiz_correct INTEGER,
    quiz_explanation TEXT,
    embedding VECTOR(768),  -- Gemini text-embedding-005 dimension
    source TEXT DEFAULT 'core',        -- 'core', 'ai_generated', 'community'
    is_published BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,  -- Soft delete
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE card_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id TEXT REFERENCES cards(id),
    version INTEGER NOT NULL,
    data JSONB NOT NULL,  -- Full card snapshot
    changed_by UUID REFERENCES users(id),
    change_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════
-- LEARNING PROGRESS (FSRS + Gamification)
-- ═══════════════════════════════════════════

CREATE TABLE card_progress (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    card_id TEXT REFERENCES cards(id) ON DELETE CASCADE,
    -- FSRS Fields
    stability FLOAT DEFAULT 0,
    difficulty_fsrs FLOAT DEFAULT 0,
    due_date TIMESTAMPTZ,
    last_review TIMESTAMPTZ,
    review_count INTEGER DEFAULT 0,
    lapses INTEGER DEFAULT 0,
    state TEXT DEFAULT 'new',
    -- Mastery
    mastered BOOLEAN DEFAULT FALSE,
    bookmarked BOOLEAN DEFAULT FALSE,
    self_rating INTEGER,
    quiz_answered BOOLEAN DEFAULT FALSE,
    quiz_correct BOOLEAN,
    -- Timestamps
    first_seen TIMESTAMPTZ,
    mastered_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, card_id)
);

CREATE TABLE study_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    mode TEXT NOT NULL,
    category_slug TEXT,
    cards_reviewed INTEGER DEFAULT 0,
    cards_mastered INTEGER DEFAULT 0,
    quiz_correct INTEGER DEFAULT 0,
    quiz_total INTEGER DEFAULT 0,
    xp_earned INTEGER DEFAULT 0,
    duration_seconds INTEGER,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);

CREATE TABLE user_stats (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    total_xp INTEGER DEFAULT 0,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_study_date DATE,
    total_cards_mastered INTEGER DEFAULT 0,
    total_reviews INTEGER DEFAULT 0,
    total_study_minutes INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    daily_activity JSONB DEFAULT '{}',
    badges JSONB DEFAULT '[]',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE badges (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    category TEXT,
    requirement JSONB
);

-- ═══════════════════════════════════════════
-- ATS + RESUME + MISSIONS
-- ═══════════════════════════════════════════

CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    filename TEXT,
    raw_text TEXT,
    parsed_data JSONB,
    embedding VECTOR(768),
    is_active BOOLEAN DEFAULT TRUE,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE job_targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    company TEXT,
    role TEXT,
    jd_text TEXT,
    jd_parsed JSONB,
    embedding VECTOR(768),
    interview_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ats_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    resume_id UUID REFERENCES resumes(id),
    job_target_id UUID REFERENCES job_targets(id),
    overall_score FLOAT,
    keyword_match JSONB,
    skill_gaps JSONB,
    recommended_card_ids TEXT[],
    scored_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE generated_experiences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    card_id TEXT REFERENCES cards(id),
    resume_id UUID REFERENCES resumes(id),
    generated_text TEXT,
    resume_bullets_used JSONB,
    reasoning_trace TEXT,  -- Gemini's thinking output (for debugging)
    user_approved BOOLEAN,
    share_anonymized BOOLEAN DEFAULT FALSE,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE missions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    job_target_id UUID REFERENCES job_targets(id),
    name TEXT,
    status TEXT DEFAULT 'active',
    target_cards TEXT[],
    mastered_cards TEXT[] DEFAULT '{}',
    deadline DATE,
    initial_ats_score FLOAT,
    current_ats_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ═══════════════════════════════════════════
-- FEEDBACK
-- ═══════════════════════════════════════════

CREATE TABLE card_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    card_id TEXT REFERENCES cards(id),
    rating TEXT CHECK (rating IN ('helpful', 'not_helpful')),
    issue_type TEXT,
    comment TEXT,
    status TEXT DEFAULT 'new',  -- 'new', 'reviewed', 'actioned'
    admin_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE nps_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    trigger TEXT NOT NULL,
    score INTEGER CHECK (score BETWEEN 0 AND 10),
    feedback TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE feature_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'submitted',
    vote_count INTEGER DEFAULT 1,
    admin_response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE feature_votes (
    user_id UUID REFERENCES users(id),
    request_id UUID REFERENCES feature_requests(id),
    PRIMARY KEY (user_id, request_id)
);

CREATE TABLE feedback_digests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_start DATE,
    period_end DATE,
    summary TEXT,
    top_themes JSONB,
    nps_trend JSONB,
    action_items JSONB,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════
-- B2B (Phase 2 — tables ready, not used in MVP)
-- ═══════════════════════════════════════════

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    plan TEXT DEFAULT 'enterprise',
    max_seats INTEGER DEFAULT 50,
    sso_provider TEXT,
    sso_config JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE users ADD CONSTRAINT fk_users_org 
    FOREIGN KEY (org_id) REFERENCES organizations(id);

-- ═══════════════════════════════════════════
-- ANALYTICS EVENTS (For custom admin dashboard)
-- ═══════════════════════════════════════════

CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    event_name TEXT NOT NULL,
    event_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════
-- INDEXES
-- ═══════════════════════════════════════════

CREATE INDEX idx_cards_category ON cards(category_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_cards_embedding ON cards USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_cards_tags ON cards USING gin(tags);
CREATE INDEX idx_card_progress_user ON card_progress(user_id);
CREATE INDEX idx_card_progress_due ON card_progress(user_id, due_date) WHERE state != 'new';
CREATE INDEX idx_study_sessions_user ON study_sessions(user_id, started_at DESC);
CREATE INDEX idx_resumes_user ON resumes(user_id) WHERE is_active = TRUE;
CREATE INDEX idx_analytics_events ON analytics_events(event_name, created_at DESC);
CREATE INDEX idx_card_feedback_card ON card_feedback(card_id, created_at DESC);
CREATE INDEX idx_card_feedback_status ON card_feedback(status) WHERE status = 'new';
CREATE INDEX idx_feature_requests_votes ON feature_requests(vote_count DESC);
```

---

## Revised Build Priority

### Sprint 1 (Week 1-3): Foundation + Core Study Engine

| # | Task | Description |
|---|------|-------------|
| 1 | Project scaffold | React+Vite (frontend), FastAPI (backend), Docker setup |
| 2 | Content extraction | Parse JSX → JSON → PostgreSQL, anonymize enterprise refs |
| 3 | Generate embeddings | Gemini text-embedding-005 for all 177+ cards |
| 4 | Clerk auth | Login/signup, JWT verification in FastAPI |
| 5 | Study engine UI | Enhanced card viewer: flip, quiz, bookmark, mastery |
| 6 | Category navigation | Sidebar with categories, search, difficulty filter |
| 7 | Progress persistence | Save mastery/bookmarks/quiz results to PostgreSQL |
| 8 | FSRS engine (**backend-only**) | Spaced repetition via py-fsrs in FastAPI, "Daily 5" queue |
| 9 | **Stripe integration** | Free → Pro subscription flow (revenue before features) |
| 10 | **Free tier gating** | Curated "Foundations" category free; Pro gates the rest |

### Sprint 2 (Week 4-6): Gamification + Admin Panel

| # | Task | Description |
|---|------|-------------|
| 11 | Streak system | Daily login tracking, streak count, loss-aversion nudges |
| 12 | XP + leveling | Points for studying/quizzing, level progression |
| 13 | Skill badges | Domain mastery badges, milestone badges |
| 14 | Activity heatmap | GitHub-style daily study visualization |
| 15 | Skill radar chart | Spider chart showing domain proficiency |
| 16 | Admin: Card CRUD | Add/edit/delete cards with rich text editor |
| 17 | Admin: AI assist | Gemini generates card drafts from topics |
| 18 | Admin: Bulk import/export | JSON upload/download for batch card management |
| 19 | Admin: Content metrics | Card performance, difficulty, popularity stats |

### Sprint 3 (Week 7-9): Analytics + Feedback + ATS

| # | Task | Description |
|---|------|-------------|
| 20 | PostHog Cloud integration | Event tracking across frontend + backend |
| 21 | Admin analytics dashboard | DAU/MAU, engagement, content performance, LLM costs |
| 22 | Per-card feedback | 👍/👎 + issue categorization on every card |
| 23 | NPS surveys | Auto-triggered at day 7/30/90 |
| 24 | Feature request board | Submit + vote on features |
| 25 | AI feedback digest | Weekly Gemini-summarized feedback themes |
| 26 | Resume upload + parse | PDF/DOCX → Gemini Flash extraction |
| 27 | ATS scoring engine | Embedding similarity + Gemini Pro evaluation |
| 28 | Skill gap → card recommendations | Algorithmic gap mapping to card library |

### Sprint 4 (Week 10-12): Mission Mode + Launch

| # | Task | Description |
|---|------|-------------|
| 29 | Mission Mode UI | Interview sprint with countdown, focused cards |
| 30 | **Async experience pre-generation** | Background jobs pre-generate for all mission cards |
| 31 | ATS re-scoring loop | Track score improvement over study time |
| 32 | Landing page | Conversion-optimized with free ATS demo |
| 33 | Onboarding flow | Goal selection, first-time user experience |
| 34 | Mobile responsive | All features work on phone |
| 35 | Deploy | Vercel (frontend) + Railway (backend) + R2 (files) |

> [!NOTE]
> **Realistic timeline: 10-12 weeks** for a solo dev with Claude Code. Claude Code accelerates coding 3-5x but doesn't eliminate debugging, API integration surprises, or design decisions. See [Claude Code execution guide](file:///Users/kalaidhamu/.gemini/antigravity/brain/c0639d8c-1bc7-4106-9f30-147ef512f0a0/cto_challenge_and_execution.md) for the exact step-by-step prompting strategy.

---

## Project Structure

```
skillforge/
├── frontend/                      # React + Vite → Vercel
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── AppShell.jsx           # Main layout wrapper
│   │   │   │   ├── Sidebar.jsx            # Category nav + stats
│   │   │   │   └── TopBar.jsx             # Search + user menu
│   │   │   ├── study/
│   │   │   │   ├── CardViewer.jsx         # Flip card + quiz UI
│   │   │   │   ├── DailyFive.jsx          # SRS daily review queue
│   │   │   │   ├── CategoryBrowser.jsx    # Browse all categories
│   │   │   │   └── ProgressTracker.jsx    # Mastery progress
│   │   │   ├── gamification/
│   │   │   │   ├── StreakBanner.jsx        # Current streak display
│   │   │   │   ├── XPBar.jsx              # Level + XP progress
│   │   │   │   ├── BadgeGrid.jsx          # Earned badges
│   │   │   │   ├── ActivityHeatmap.jsx    # GitHub-style heatmap
│   │   │   │   └── SkillRadar.jsx         # Spider chart
│   │   │   ├── ats/
│   │   │   │   ├── ResumeUpload.jsx       # Drag-drop resume
│   │   │   │   ├── ATSScoreCard.jsx       # Score visualization
│   │   │   │   ├── SkillGapList.jsx       # Gap breakdown
│   │   │   │   └── ExperiencePanel.jsx    # "My Experience" gen
│   │   │   ├── mission/
│   │   │   │   ├── MissionSetup.jsx       # Create interview sprint
│   │   │   │   ├── MissionDashboard.jsx   # Countdown + progress
│   │   │   │   └── MissionComplete.jsx    # Results + ATS delta
│   │   │   ├── feedback/
│   │   │   │   ├── CardFeedback.jsx       # 👍/👎 on cards
│   │   │   │   ├── NPSSurvey.jsx          # Score 0-10 modal
│   │   │   │   └── FeatureBoard.jsx       # Request + vote
│   │   │   └── admin/
│   │   │       ├── AdminLayout.jsx        # Admin shell
│   │   │       ├── CardEditor.jsx         # CRUD + AI assist
│   │   │       ├── CardList.jsx           # Filterable card table
│   │   │       ├── BulkImport.jsx         # JSON upload
│   │   │       ├── AnalyticsDashboard.jsx # Metrics + charts
│   │   │       ├── FeedbackInbox.jsx      # Review feedback
│   │   │       └── UserManagement.jsx     # User list + details
│   │   ├── hooks/
│   │   │   ├── useAuth.js
│   │   │   ├── useCards.js
│   │   │   ├── useStudy.js
│   │   │   ├── useGamification.js
│   │   │   └── useAdmin.js
│   │   ├── lib/
│   │   │   ├── api.js                     # API client
│   │   │   └── analytics.js               # PostHog wrapper
│   │   │   # NOTE: FSRS runs SERVER-SIDE ONLY (backend/services/study_service.py)
│   │   │   # Frontend only sends review ratings, backend calculates scheduling
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── public/
│   ├── Dockerfile
│   ├── vercel.json
│   └── package.json
│
├── backend/                       # FastAPI → Railway (→ AWS ECS)
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py                # Clerk webhook handlers
│   │   │   │   ├── cards.py               # Card CRUD (user + admin)
│   │   │   │   ├── study.py               # Progress, sessions, FSRS
│   │   │   │   ├── gamification.py        # Streaks, XP, badges
│   │   │   │   ├── resume.py              # Upload, parse, score
│   │   │   │   ├── mission.py             # Mission CRUD
│   │   │   │   ├── experience.py          # AI experience generation
│   │   │   │   ├── feedback.py            # Card feedback, NPS, features
│   │   │   │   ├── admin.py               # Admin-only routes
│   │   │   │   └── analytics.py           # Admin analytics data
│   │   │   ├── deps.py                    # Dependencies (auth, db)
│   │   │   └── middleware.py              # CORS, rate limiting
│   │   ├── services/
│   │   │   ├── card_service.py            # Card business logic
│   │   │   ├── study_service.py           # FSRS scheduling, sessions
│   │   │   ├── gamification_service.py    # Streak + XP + badge logic
│   │   │   ├── resume_parser.py           # Gemini Flash extraction
│   │   │   ├── ats_scorer.py              # Embedding + Gemini Pro eval
│   │   │   ├── gap_analyzer.py            # Algorithmic skill gap
│   │   │   ├── experience_gen.py          # Gemini Pro reasoning
│   │   │   ├── feedback_service.py        # Feedback + digest
│   │   │   ├── analytics_service.py       # Metrics aggregation
│   │   │   └── content_migrator.py        # JSX → DB extraction tool
│   │   ├── llm/
│   │   │   ├── client.py                  # Unified Gemini client
│   │   │   ├── router.py                  # Model routing (Flash/Pro)
│   │   │   ├── prompts/                   # Prompt-as-Code (YAML)
│   │   │   │   ├── resume_extract.yaml
│   │   │   │   ├── ats_evaluate.yaml
│   │   │   │   ├── experience_gen.yaml
│   │   │   │   ├── quiz_feedback.yaml
│   │   │   │   ├── card_generate.yaml     # Admin AI card gen
│   │   │   │   └── feedback_digest.yaml   # Weekly digest
│   │   │   └── cost_tracker.py            # Token + cost logging
│   │   ├── models/                        # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── card.py
│   │   │   ├── progress.py
│   │   │   ├── resume.py
│   │   │   ├── mission.py
│   │   │   ├── feedback.py
│   │   │   └── analytics.py
│   │   ├── core/
│   │   │   ├── config.py                  # Environment-based config
│   │   │   ├── database.py                # DB connection + sessions
│   │   │   └── security.py                # Clerk JWT verification
│   │   └── main.py                        # FastAPI app entry
│   ├── alembic/                           # DB migrations
│   │   ├── versions/
│   │   └── alembic.ini
│   ├── scripts/
│   │   ├── extract_cards.py               # One-time JSX → DB migration
│   │   ├── generate_embeddings.py         # Embed all cards
│   │   └── seed_badges.py                 # Initialize badge definitions
│   ├── tests/
│   │   ├── test_cards.py
│   │   ├── test_study.py
│   │   ├── test_ats.py
│   │   └── test_experience.py
│   ├── Dockerfile
│   ├── docker-compose.yml                 # Local dev (API + DB + Redis)
│   ├── railway.toml                       # Railway config
│   ├── requirements.txt
│   └── .env.example
│
├── infra/                         # AWS-ready (Phase 2)
│   ├── terraform/
│   │   ├── main.tf                        # ECS + RDS + ElastiCache
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── docker-compose.prod.yml
│
└── docs/
    ├── ARCHITECTURE.md
    ├── API.md
    └── ADMIN_GUIDE.md
```

---

## Open Questions (Updated)

> [!IMPORTANT]
> ### Decisions Locked ✅
>
> | Decision | Choice | Status |
> |----------|--------|--------|
> | LLM Provider | Gemini (Google AI Studio → Vertex AI later) | ✅ Locked |
> | Auth | Clerk with RBAC (user/admin roles) | ✅ Locked |
> | Frontend Hosting | Vercel | ✅ Locked |
> | Backend Hosting | Railway (Dockerized for AWS) | ✅ Locked |
> | File Storage | Cloudflare R2 (zero egress) | ✅ Locked |
> | Analytics | PostHog Cloud (free tier) | ✅ Locked |
> | Admin Panel | Same app at `/admin`, Clerk RBAC | ✅ Locked |
> | Free Tier | Curated "Foundations" category (15 cards, 1 per domain) | ✅ Locked |
> | FSRS | Backend-only (py-fsrs in FastAPI) | ✅ Locked |
> | Experience Gen | Async pre-generation, cached in DB | ✅ Locked |
> | Experience Seeding | 4-tier: ⭐ Expert + 🤖 AI Reference + 👤 My Experience + 👥 Community — all transparently labeled | ✅ Locked |
>
> ### Decisions Still Needed
>
> 1. **Domain name**: Register `skillforge.dev` or `skillforge.ai` — needed for Clerk + Vercel production cookies (Safari ITP blocks third-party cookies on `*.vercel.app`)
> 2. **Gemini API key**: Do you have a Google AI Studio account? Need an API key to start
> 3. **Resume privacy policy**: Process-and-delete or store for repeat ATS scans? Recommendation: store encrypted, user can delete anytime (GDPR right to erasure)
> 4. **Content licensing**: Do you have any restrictions on sharing enterprise experiences publicly? Need to confirm anonymization is sufficient
> 5. **Launch target**: When do you want the core study engine (Sprint 1) live? This sets the schedule

---

## Verification Plan

### Automated Tests
- **Backend**: pytest with 80%+ coverage on all services
- **Content extraction**: Verify all 177+ cards parse correctly, no data loss
- **Anonymization**: Grep for any remaining direct company references
- **FSRS accuracy**: Test scheduling algorithm against known-good outputs
- **API**: Integration tests for all routes
- **Frontend**: Vitest + React Testing Library for key components

### Manual Verification
- **Study flow**: End-to-end card study, quiz, mastery, streak tracking
- **Admin flow**: Create card, edit card, delete card, bulk import
- **Resume upload**: Test with 5+ resume formats (PDF, DOCX, different layouts)
- **Experience generation**: Review 10+ generated experiences for quality/naturalness
- **Analytics**: Verify dashboard numbers match raw database queries
- **Feedback**: Submit feedback, verify admin inbox, test NPS triggers
- **Mobile**: Test all features on iPhone Safari + Android Chrome

### Performance Targets
| Feature | Target | Measurement |
|---------|--------|-------------|
| Card navigation | < 100ms | Client-side state |
| Dashboard load | < 2 seconds | Lighthouse |
| Search results | < 300ms | API response time |
| Resume parse | < 5 seconds | API response time |
| ATS score | < 8 seconds | API response time |
| Experience generation | < 6 seconds (streaming) | TTFB + stream complete |
| Admin card save | < 500ms | API response time |
| Daily 5 queue | < 200ms | FSRS calculation + DB query |
