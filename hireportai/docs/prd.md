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
