# Spec #19 — Landing Page Upgrade (Conversion-Grade)

**Phase:** 3
**Status:** in-progress
**Owner:** Frontend
**Depends on:** Google OAuth (done), PostHog (done), existing LandingPage.tsx

---

## Goal

Upgrade the existing `LandingPage.tsx` from a beta-quality placeholder to a
high-converting marketing page. No new backend work — purely frontend.

## Sections

### 1. Hero (above the fold)

| Element | Detail |
|---------|--------|
| Headline | "Ace your next engineering interview" (or better value-prop copy) |
| Subheadline | One sentence: scan → study → ace |
| Primary CTA | "Start Free" → Google OAuth login (or `/study` if logged in) |
| Secondary CTA | "See how it works" → smooth scroll to `#how` |
| Social proof | "Join 500+ engineers studying smarter" |

### 2. How It Works

Three-step walkthrough (not a feature list):

1. **Scan your resume** — icon + one-line desc
2. **Study your gaps** — icon + one-line desc
3. **Ace the interview** — icon + one-line desc

### 3. Pricing

| | Free | Pro ($49/mo) |
|---|---|---|
| Cards | 15 | Unlimited |
| Scans | 1 | Unlimited |
| Daily review | Yes | Yes |
| Mission Mode | — | Yes |
| Streak freeze | — | Yes |
| Badge | — | Most Popular |

### 4. Trust

3–4 trust elements:
- AI-powered spaced repetition
- 177+ expert-curated cards
- Personalized to your resume gaps
- Built by engineers, for engineers

### 5. Footer

Links: About, Pricing (anchor), Privacy, Terms, Contact

## Technical Requirements

- Mobile-first responsive (single column mobile, two-column pricing desktop)
- Dark mode via existing theme system
- No heavy images — Lucide React icons or inline SVGs
- Auth-aware CTAs: logged-in users go to `/study`
- PostHog: `landing_page_viewed` on mount, `cta_clicked` with
  `{ button: 'hero' | 'pricing' | 'how_it_works' }` on each CTA

## Out of Scope

- Auth flow changes
- Routing changes
- Backend work
- New pages or routes
