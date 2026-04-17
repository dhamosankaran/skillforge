# SkillForge — Strategic Options for $100M ARR

> **Read this before Phase 6 planning. Re-read every quarter.**
> **Audience**: Dhamo (founder). Claude Code does not need to read this.
> **Status**: Decision made — Option D selected on 2026-04-17.

---

## DECISION (2026-04-17)

**Selected: Option D — Stay the course.**

I'm building SkillForge as a focused B2C interview-prep product for senior/staff engineers in English-speaking markets. The $100M ARR target is retired. Realistic targets:

- $1M ARR by month 12 post-launch
- $5M ARR by month 24
- $15M ARR by month 48
- Optional acquisition discussion (Coursera, LinkedIn, GitLab, Atlassian) at $5M+ ARR

Phase 5 plan continues unchanged — every slice is correct work for this strategy. Phase 6+ planning focuses on conversion optimization, retention curves, and word-of-mouth growth — NOT platform expansion, B2B pivot, or geographic scale plays.

**Constraints this decision creates:**
- No multi-tenancy work
- No SOC 2 effort
- No B2B sales infrastructure
- No new geo markets beyond what's already shipped (USD/INR via P5-S3)
- No adjacent product surfaces (no promotion-prep, no comp-negotiation)
- LLM cost discipline still matters but doesn't dominate roadmap

**Re-evaluate this decision if:**
- We hit $5M ARR faster than 24 months (would suggest market is bigger than estimated)
- A clear B2B inbound signal emerges (10+ engineering managers asking for team plans)
- A natural adjacent surface appears with strong product-market fit signal from existing users
- A strategic acquirer expresses interest at terms that don't require a B2B story to justify

Otherwise: stay focused, ship Phase 5, optimize the funnel, build a sustainable business.

---

## Reference: The original analysis (kept for future re-evaluation)

The remainder of this document is the original strategic frame. I'm leaving it in place so future-me can re-read it if circumstances change. It is no longer the active plan.

---

## The honest math

**Goal**: $100M ARR
**Current product**: $49/mo Pro plan, B2C, English-speaking senior/staff engineers, interview-prep wedge
**Subscribers needed at $49/mo**: ~170,000 paying, ~83,000 if blended ARPU climbs to $100/mo

**Realistic English-speaking TAM** for senior+ engineers actively interviewing or upskilling: 2–3M people globally
**Penetration required**: 3–6% of the entire addressable market, sustained, with low churn

**Comparable companies in the space** (rough public/rumored ARR):
- Interview Kit: low single-digit millions ARR
- Exponent: ~$10M ARR estimate
- Hello Interview: similar range
- LeetCode (broader scope): ~$50–80M ARR estimate
- Brilliant.org (adjacent, much broader): ~$50M ARR
- Coursera (adjacent, way broader): public, ~$700M ARR

**Conclusion**: The current B2C interview-prep wedge has a credible ceiling around **$5–15M ARR**. That is a great business. It is not $100M.

To credibly target $100M, the product needs ONE of three structural moves. Each is a real choice with real tradeoffs.

---

## Option A — B2B Pivot (Highest probability of $100M)

### What it is
Sell SkillForge to engineering organizations as a team upskilling platform. Charge per seat or per company.

### Math
- Target: 200 enterprise customers @ $500K ACV = $100M
- Or: 1,000 mid-market customers @ $100K ACV = $100M
- Or: 10,000 SMB engineering teams @ $10K ACV = $100M (much harder sales motion)

### What changes about the product
- Admin panel for team leads (you have a partial admin panel, expand it)
- SSO (Okta, Google Workspace, Microsoft Entra)
- Team analytics (who's studying, what gaps the team has, ROI dashboards)
- Manager-assigned learning paths
- Custom content authoring (teams want company-specific cards: "How does OUR auth system work?")
- Compliance reports for L&D budgets
- SOC 2 Type II
- Net 30 invoicing, not Stripe self-serve
- A sales team. This is the biggest change.

### Why it's the highest-probability path to $100M
- B2B SaaS has 5–10× higher LTV than B2C
- Engineering L&D budgets are real and growing ($5K–$25K per engineer per year)
- The current product (cards, ATS scanner, mission mode) is most of what enterprises want, just packaged differently
- Adjacent winners exist (Pluralsight, Coursera for Business, A Cloud Guru) so the buyer pattern is proven

### Why it's hard
- You need a B2B sales motion. Founder-led sales for the first 20 customers, then hire AEs. Different muscle than B2C product-led growth.
- 12–18 month sales cycles for enterprise; 3–6 months for mid-market
- SOC 2 alone is 6 months and $50–150K
- You'd serve two masters during the transition (existing B2C users + early B2B pilots)

### When to know if it's working
- Enterprise pilot signed within 6 months of pivot
- 5 paying enterprise customers within 12 months
- $1M ARR from B2B within 18 months
- If you're not at $1M B2B ARR by month 18, the motion isn't working

### First concrete steps if you pick this
1. Identify 20 engineering managers in your existing user base and call them. Ask: "Would your company pay for SkillForge for the whole team?"
2. Pick a beachhead vertical (e.g., AI startups hiring fast, or large fintech engineering orgs)
3. Build the first version of the team admin panel
4. Hire a B2B-experienced advisor or fractional CRO
5. Set up SOC 2 readiness (Vanta, Drata)

---

## Option B — Adjacent Expansion (Medium probability of $100M)

### What it is
Don't stay in interview prep. Become "the operating system for engineering career growth": interview prep + performance review prep + promotion case prep + skill ladders for L+1 + reference checks + salary negotiation + portfolio building.

### Math
- TAM expands from "engineers actively interviewing" (2–3M) to "engineers actively in their career" (15–25M globally)
- ARPU can rise to $80–120/mo with broader feature set
- $100/mo × 100K subs = $120M

### What changes about the product
- New product surfaces beyond interview prep
- Each new surface needs its own engineering investment (could be 2–3× current scope)
- Branding shifts from "ace your interview" to "level up your career"
- Onboarding becomes more complex (more personas to serve)
- The Lens/Forge/Mission engines stay valid, but you add: Promote (promotion case builder), Negotiate (compensation tool), Reflect (performance review prep), Build (portfolio/case-study tool)

### Why it could work
- Engineers think about their career constantly, not just at interview time
- Subscription stickiness goes up massively (year-round value vs job-search-only value)
- Less competition in performance-review-prep and promotion-case-prep specifically
- LinkedIn Learning and Coursera don't go this deep on engineering specifically

### Why it's hard
- Each new product surface dilutes focus. Most B2C SaaS that try to expand fail at it.
- "OS for engineering careers" is a vague positioning that's hard to market
- You're competing with LinkedIn for mindshare on adjacent surfaces
- 2–3× scope means 2–3× engineering team or 2–3× longer

### When to know if it's working
- First adjacent product (recommend: promotion case builder) ships within 6 months
- Adjacent product hits 20% adoption among existing Pro users within 9 months
- Blended ARPU rises 40%+ within 12 months
- If those don't happen, focus is fragmenting

### First concrete steps if you pick this
1. Survey existing Pro users: "What's the next career problem you'd pay $20/mo to solve?"
2. Pick the highest-signal answer (likely promotion prep or comp negotiation)
3. Build that as a Phase 6 product surface
4. Re-brand the home page to position SkillForge as career growth, not just interview prep
5. Measure ARPU lift, not user count

---

## Option C — Geographic + Price Wedge (Hardest path to $100M, highest unit-economics risk)

### What it is
Aggressive India + SEA pricing. Volume play. ₹999/mo (~$12) × 500K subs = $72M. ₹1,499/mo × 600K = $108M.

### Math
- India has 5M+ software engineers
- SEA + LatAm + Eastern Europe add another 4–6M
- The geo-pricing infrastructure is already built (P5-S3 done)

### What changes about the product
- Localization (multi-language eventually, English-first is OK initially)
- Payment methods (UPI in India, GrabPay in SEA, Pix in Brazil — Stripe doesn't cover all)
- Customer support in non-overlapping timezones
- Marketing channels shift (YouTube India, regional LinkedIn, college partnerships)
- Lower-cost LLM routing (Flash by default, Pro only when essential — partially in place)

### Why it could work
- The geo-pricing toggle is already shipped, so the marginal cost of adding a country is small
- Lower competition in non-English markets for engineering interview prep
- High word-of-mouth in tight engineering communities

### Why it's hard
- $12/mo at 500K subs requires brutal cost discipline. LLM costs alone could eat margin.
- High churn risk — emerging markets have lower payment persistence
- Sales/marketing efficiency is harder to model
- Currency exposure
- Customer acquisition cost has to stay under $20 to make unit economics work

### When to know if it's working
- 50K Indian Pro subs within 12 months
- LTV/CAC ≥ 3 in India market within 18 months
- Indian ARR > $1M within 18 months
- If LTV/CAC < 2, the model doesn't scale

### First concrete steps if you pick this
1. Validate INR pricing tiers (₹499 / ₹999 / ₹1,499) — A/B test conversion at each
2. Open 2 more geo-priced markets: Brazil (BRL) and Indonesia (IDR)
3. Add UPI payment via Razorpay (Stripe partnership exists)
4. Build a free-content distribution channel (YouTube India, free LinkedIn carousels)
5. Hire a part-time growth lead in India

---

## Option D — Stay the course ✅ SELECTED

Don't pivot. Build the best $5–15M ARR business you can. Run the Phase 5 + Phase 6 + Phase 7 roadmap focused on B2C interview prep in English-speaking markets.

This is a perfectly defensible choice. Most $5–15M ARR SaaS companies are extremely good lifestyle businesses or attractive acquisition targets. Anthropic-built tools are still tools — not every product needs to be a unicorn.

If you pick this, drop the $100M ARR goal and replace it with realistic targets:
- $1M ARR within 12 months of public launch
- $5M ARR within 24 months
- $15M ARR within 48 months
- Sell to a strategic acquirer (Coursera, LinkedIn, GitLab, Atlassian) at 5–10× revenue

---

## Original recommendation (now overridden by Option D selection)

The original analysis recommended Option A (B2B pivot) as the highest-probability path to $100M, with B2C as the discovery funnel — the Notion/Figma/GitHub/Linear playbook.

That recommendation was correct given a $100M ambition. Option D is the right choice if the ambition is a sustainable business with reasonable hours and an acquisition exit. Both are valid framings — they're not opposed, they're answering different questions.

---

*Created 2026-04-17 by Claude in advisory chat. Decision recorded same day.*
*Re-evaluation triggers listed at top. Otherwise: stay focused.*