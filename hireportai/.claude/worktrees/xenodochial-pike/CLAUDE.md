# HireLens AI — Claude Project Guide

AI-powered career intelligence platform: ATS scoring, keyword gap analysis, resume rewriting, cover letter generation, interview prep, resume comparison, and job application tracking.

---

## Product Vision

HireLens AI acts as a career intelligence tool that helps users:
- Understand how their resume performs in ATS systems
- Identify missing skills for specific jobs
- Improve resume bullet points
- Automatically generate optimized resumes
- Generate tailored cover letters
- Prepare for interviews with AI-generated questions
- Compare two resumes head-to-head for the same job

The UI should feel like a modern SaaS dashboard (Stripe / Linear / Vercel aesthetic).

---

## Project Structure

```
hirelensai/
├── hirelens-backend/    # FastAPI + Python (port 8000)
├── hirelens-frontend/   # React + TypeScript + Vite (port 5199)
├── scripts/
│   ├── start.sh         # Start both services (kills stale processes, checks venv)
│   └── stop.sh          # Stop both services cleanly
└── logs/                # Runtime logs (backend.log, frontend.log, *.pid)
```

---

## Tech Stack

**Backend**
- FastAPI 0.109 + Uvicorn (ASGI)
- Google Gemini API (`google-genai`) — model `gemini-2.0-flash`
- spaCy 3.7 (`en_core_web_sm`) for NLP (stopword removal, lemmatization, noun phrase detection)
- scikit-learn TF-IDF for keyword scoring
- pdfplumber + python-docx for document parsing
- SQLite via aiosqlite (job tracker)
- Pydantic v2 settings

**Frontend**
- React 18 + TypeScript 5
- Vite 5 (dev server, HMR, `/api` proxy to `:8000`)
- Tailwind CSS + Framer Motion (animations)
- Zustand (state), Axios (HTTP), react-router-dom v6
- Recharts (charts: bar, radar/SkillOverlap, gauge)
- react-dropzone (file upload)
- `@react-oauth/google` — Google Sign-In
- `html2pdf.js` — PDF export of optimized resume and cover letter

---

## Start & Stop

```bash
# Start both services (checks venv, kills stale processes on 8000/5199)
./scripts/start.sh

# Stop all services
./scripts/stop.sh
```

Logs go to `logs/backend.log` and `logs/frontend.log`.

**Manual start (individual services):**
```bash
# Backend
cd hirelens-backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend
cd hirelens-frontend
npm run dev -- --port 5199
```

---

## Local URLs

| Service      | URL                              |
|--------------|----------------------------------|
| Frontend     | http://localhost:5199            |
| Backend API  | http://localhost:8000            |
| Swagger docs | http://localhost:8000/docs       |
| ReDoc        | http://localhost:8000/redoc      |
| Health check | http://localhost:8000/health     |

---

## Environment Setup

**Backend** — `hirelens-backend/.env` (copy from `.env.example`):
```
GEMINI_API_KEY=<your-key>
GEMINI_MODEL=gemini-2.0-flash
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5199
ENABLE_SQLITE_TRACKER=true
MAX_UPLOAD_SIZE_MB=5
```

**Frontend** — `hirelens-frontend/.env` (copy from `.env.example`):
```
VITE_API_BASE_URL=          # leave blank in dev; Vite proxies /api → :8000
VITE_GOOGLE_CLIENT_ID=      # optional: Google OAuth Client ID for Sign-In feature
```

To enable Google Sign-In:
1. Go to https://console.cloud.google.com/
2. Create an OAuth 2.0 Client ID (Web application)
3. Add `http://localhost:5199` to Authorised JavaScript origins
4. Copy the Client ID into `VITE_GOOGLE_CLIENT_ID`

---

## Python venv

```bash
cd hirelens-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm   # required for NLP features
```

The `start.sh` script handles all of this automatically.

---

## Core User Flow

1. User uploads resume (PDF or DOCX)
2. User pastes job description
3. System NLP-processes the job description
4. System parses resume into sections
5. System compares resume vs job requirements
6. System produces ATS analysis (score, keywords, gaps, bullets, formatting)
7. System provides improvement suggestions
8. User can generate optimized resume and cover letter
9. User can prepare for interviews with AI-generated questions
10. User can compare two resumes for the same job

---

## ATS Scoring

Score range: 0–100, broken into 5 components:

| Component           | Weight |
|---------------------|--------|
| Keyword Match       | 40%    |
| Skill Coverage      | 25%    |
| Experience Alignment| 20%    |
| Bullet Strength     | 10%    |
| Formatting          | 5%     |

ATS Rating:
- 90–100 → Excellent compatibility
- 75–89 → Likely passes ATS
- 60–74 → Risky
- Below 60 → Likely rejected

---

## API Routes

All prefixed with `/api`:

| Route                   | Description                                                   |
|-------------------------|---------------------------------------------------------------|
| `POST /api/analyze`     | Resume + JD analysis (score, keywords, gaps, bullets)         |
| `POST /api/compare`     | Side-by-side comparison of two resumes vs same JD             |
| `POST /api/rewrite`     | AI-powered resume bullet rewriting                            |
| `POST /api/cover-letter`| Cover letter generation (professional/confident/conversational tones) |
| `POST /api/interview-prep` | AI interview questions with STAR framework answers         |
| `GET/POST /api/tracker` | Job application CRUD                                          |

---

## Frontend Pages & Routes

| Route        | Page           | Status      |
|--------------|----------------|-------------|
| `/`          | Landing        | ✅ Built    |
| `/analyze`   | Analyze        | ✅ Built    |
| `/results`   | Results        | ✅ Built    |
| `/rewrite`   | Rewrite        | ✅ Built    |
| `/tracker`   | Tracker        | ✅ Built    |
| `/pricing`   | Pricing        | ✅ Built    |
| `/interview` | Interview Prep | ✅ Built    |
| `/compare`   | Resume Compare | ✅ Built    |

---

## Pricing Model

| Plan    | Price  | Key Limits                                           |
|---------|--------|------------------------------------------------------|
| Free    | $0     | 3 ATS scans, no rewrite, no cover letter             |
| Pro     | $15/mo | Unlimited scans, full analytics, no rewrite          |
| Premium | $20/mo | Everything + AI rewrite, cover letter, PDF export    |

Usage enforcement: `UsageContext` tracks free scans in `localStorage`. `upgradePlan()` upgrades the plan (demo mode — no real Stripe payments wired). Plan gates the `/rewrite` page and premium features.

---

## Key Files

| File | Purpose |
|------|---------|
| `hirelens-backend/app/main.py` | FastAPI app factory, CORS, middleware, router registration |
| `hirelens-backend/app/config.py` | Pydantic settings loaded from `.env` |
| `hirelens-backend/app/services/gpt_service.py` | Gemini API integration |
| `hirelens-backend/app/services/scorer.py` | ATS scoring logic (5 components) |
| `hirelens-backend/app/services/nlp.py` | spaCy skill/requirement extraction |
| `hirelens-backend/app/services/parser.py` | PDF/DOCX parsing |
| `hirelens-backend/app/services/gap_detector.py` | Skill gap + radar chart data |
| `hirelens-backend/app/services/bullet_analyzer.py` | Action verb + impact scoring |
| `hirelens-backend/app/api/routes/compare.py` | Resume comparison endpoint |
| `hirelens-backend/app/db/database.py` | SQLite init (`data/hirelens.db`) |
| `hirelens-frontend/src/services/api.ts` | Axios API client |
| `hirelens-frontend/src/context/UsageContext.tsx` | Free tier scan limit + plan upgrade (localStorage) |
| `hirelens-frontend/src/context/AnalysisContext.tsx` | Global analysis state |
| `hirelens-frontend/src/context/AuthContext.tsx` | Google Sign-In auth state |
| `hirelens-frontend/src/utils/skillResources.ts` | Curated learning resource links per skill |
| `hirelens-frontend/src/components/rewrite/ResumePDFTemplate.tsx` | Hidden template for html2pdf.js export |
| `hirelens-frontend/vite.config.ts` | Vite config with `/api` proxy |

---

## Database

SQLite at `hirelens-backend/data/hirelens.db`.
Table: `tracker_applications` (id, company, role, date_applied, ats_score, status, created_at).
Auto-initialised on backend startup when `ENABLE_SQLITE_TRACKER=true`.

Tracker statuses: `Applied` | `Interviewing` | `Rejected` | `Offer`

---

## Tests

```bash
cd hirelens-backend
source venv/bin/activate
pytest tests/
```

Test files: `tests/test_nlp.py`, `tests/test_parser.py`, `tests/test_scorer.py`

---

## Docker (optional)

```bash
cd hirelens-backend
docker-compose up
```

Exposes port 8000, downloads `en_core_web_sm` on build. Health check on `GET /health`.

---

## Feature Status — All Built

| Feature | Status | Notes |
|---------|--------|-------|
| Resume upload (PDF/DOCX) | ✅ | pdfplumber + python-docx, 5 MB limit |
| ATS Scoring (0–100) | ✅ | 5-component weighted formula |
| Keyword match + gap analysis | ✅ | TF-IDF + spaCy |
| Skill gap detection | ✅ | Radar chart data |
| Bullet point analyzer | ✅ | Action verb detection, impact scoring |
| Resume Rewrite (AI) | ✅ | Gemini-powered, accept/reject UI |
| Cover letter generator | ✅ | 3 tones |
| **Interview Prep UI** | ✅ | Page + hook + categories + STAR framework |
| **Resume Comparison** | ✅ | `/api/compare` backend + Compare.tsx frontend |
| **PDF Export** | ✅ | html2pdf.js — resume + cover letter |
| **Plan Gating** | ✅ | Rewrite locked to Premium; mock upgrade on Pricing page |
| **Google Sign-In** | ✅ | @react-oauth/google; requires VITE_GOOGLE_CLIENT_ID |
| **Skill Learning Links** | ✅ | ~60 skills mapped to curated resources |
| **Three-column Results layout** | ✅ | Left sidebar + main + right panel |
| Job application tracker | ✅ | SQLite, Kanban board |
| ATS score gauge | ✅ | Recharts gauge |
| Keyword bar chart | ✅ | `KeywordChart` |
| Skills radar chart | ✅ | `SkillOverlapChart` |
| Score breakdown bars | ✅ | `ScoreBreakdown` |
| Animated loading states | ✅ | `SkeletonDashboard`, Framer Motion |
| Free plan scan limit | ✅ | 3 scans in localStorage, `UpgradeModal` |
| Pricing page | ✅ | 3-tier, mock upgrade wired |
| Vercel deploy config | ✅ | `hirelens-frontend/vercel.json` |
| Docker | ✅ | `Dockerfile` + `docker-compose.yml` |
| Privacy (no persistent resume storage) | ✅ | Files processed in-memory |

---

## Remaining / Future Work

| Item | Priority | Notes |
|------|----------|-------|
| Real Stripe integration | HIGH | Pricing CTAs use mock `upgradePlan()` — no real payments |
| Backend JWT auth | MEDIUM | Frontend Google auth exists; backend APIs are still public |
| User auth persistence across devices | MEDIUM | Currently localStorage only |
| Skill learning recommendations expansion | LOW | ~60 skills mapped; extend `skillResources.ts` |

---

## Common Issues

| Problem | Fix |
|---------|-----|
| Port already in use | Run `./scripts/stop.sh` or `lsof -ti tcp:8000 \| xargs kill -9` |
| `spacy` model missing | `python -m spacy download en_core_web_sm` |
| `GEMINI_API_KEY` not set | Edit `hirelens-backend/.env` |
| venv not activated | `source hirelens-backend/venv/bin/activate` |
| Frontend can't reach API | Vite proxies `/api` to `:8000` — ensure backend is running |
| AI features return fallback text | Check Gemini API key validity and model name in `.env` |
| Google Sign-In not showing | Set `VITE_GOOGLE_CLIENT_ID` in `hirelens-frontend/.env` |
| PDF export blank | Ensure `html2pdf.js` is installed: `npm install html2pdf.js` |
