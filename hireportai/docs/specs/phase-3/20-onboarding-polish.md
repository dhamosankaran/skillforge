# Spec #20 — Onboarding Polish: Persona Picker + Guided Tour

**Phase:** 3
**Status:** in-progress
**Owner:** Full-stack
**Depends on:** Auth (done), Study Dashboard (done), Mission Mode (done)

---

## Goal

Add a first-login experience for ALL users — including those who skip
the ATS scan. A persona picker captures intent, then a lightweight
guided tour orients users on the page they land on.

## Backend

### User model additions

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| `persona` | `String(20)` | `NULL` | `'interview'`, `'climber'`, `'team'` |
| `onboarding_completed` | `Boolean` | `false` | Gate flag |

### New endpoint

`PATCH /api/v1/auth/onboarding`

```json
{
  "persona": "interview",
  "target_company": "Google",   // optional, only for interview
  "target_date": "2026-05-15"   // optional, only for interview
}
```

Response: updated user object (same shape as `/auth/me`).

Sets `onboarding_completed = true` atomically.

## Frontend

### PersonaPicker (`src/components/onboarding/PersonaPicker.tsx`)

Full-screen, no navbar. Three options:

| Choice | Label | Redirect |
|--------|-------|----------|
| A | "I have an interview coming up" | `/mission` (with query params) |
| B | "I want to stay sharp" | `/study/daily` |
| C | "I'm exploring for my team" | `/study` |

Option A shows additional inputs: `target_company` (text, optional),
`target_date` (date picker, optional).

### GuidedTour (`src/components/onboarding/GuidedTour.tsx`)

4 tooltip steps, custom-built (no external library):

1. "This is your study dashboard — pick a category to start"
2. "Flip cards to learn, then test yourself with the quiz"
3. "Your Daily 5 uses spaced repetition — come back tomorrow"
4. "Track your progress here" (streak badge)

Dismissible via click-through or "Skip tour".

### Gate logic

In `App.tsx`: if `user.onboarding_completed === false`, render
`PersonaPicker` instead of the normal protected route content.

## PostHog Events

- `onboarding_persona_selected` — `{ persona: 'interview' | 'climber' | 'team' }`
- `onboarding_tour_completed`
- `onboarding_tour_skipped`

## Out of Scope

- Modifying ATS scan onboarding flow (Onboarding.tsx)
- Changing auth flow or routing structure
- Adding new backend models beyond User column additions
