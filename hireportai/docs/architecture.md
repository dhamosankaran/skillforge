# SkillForge — System Architecture

> TODO: Extract and expand the 7-layer architecture diagram from the strategy docs.
> See `../skillforge_strategy.md` Section 5 for the reference architecture.

## Components
- **Frontend**: React 18 + TypeScript + Vite (port 5199)
- **Backend**: FastAPI + Python 3.13 (port 8000)
- **Database**: PostgreSQL 16 + pgvector
- **Cache**: Redis 7
- **Auth**: Google OAuth + JWT
- **LLM**: Google Gemini (google-genai SDK)
- **Payments**: Stripe
- **Analytics**: PostHog Cloud
