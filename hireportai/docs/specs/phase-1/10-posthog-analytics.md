# SPEC: PostHog Analytics Instrumentation

**Spec #:** 10
**Phase:** 1
**Status:** Draft
**Branch:** `feature/p1-10-posthog-analytics`

---

## Problem

HirePort AI needs product analytics from day one. Without instrumentation we
cannot see the **scan → view card → paywall → pay** funnel that drives the
whole business model, and we cannot tell whether a Daily 5 user actually
reviewed cards or just landed on the dashboard and bounced.

AGENTS.md and CLAUDE.md already mandate PostHog from Phase 1 ("every
user-facing feature fires a PostHog event"), and `.agent/skills/analytics.md`
lists the core Phase 1 events. Neither the backend nor the frontend has any
PostHog code yet.

## Solution

Stand up PostHog on both sides of the stack with the minimum viable surface
area so every shipped spec can call one function.

### Backend
- Add `posthog` to `requirements.txt`.
- New module `app/core/analytics.py` that lazily constructs a PostHog client
  from the `POSTHOG_API_KEY` env var (and optional `POSTHOG_HOST`, default
  `https://us.i.posthog.com`). When the key is missing — local dev, CI — the
  module becomes a no-op so tests never hit the network.
- Public API: `track(user_id: str | int | None, event: str, properties: dict
  | None = None)`.

### Frontend
- `npm install posthog-js`.
- Initialize PostHog once in `src/main.tsx` using `VITE_POSTHOG_KEY` (and
  optional `VITE_POSTHOG_HOST`). If the key is absent, skip init silently.
- All UI capture calls go through `posthog-js` directly
  (`posthog.capture(event, props)`).

## Events Wired in This Spec

| Event                    | Side     | Location                                |
|--------------------------|----------|-----------------------------------------|
| `ats_scanned`            | Backend  | `tracker_service_v2` after a scan run   |
| `card_reviewed`          | Backend  | `study_service` after FSRS review       |
| `card_viewed`            | Frontend | `CardViewer` on mount per card          |
| `paywall_hit`            | Frontend | Wherever a free user is blocked         |
| `study_dashboard_viewed` | Frontend | Study dashboard page mount              |

Properties follow `.agent/skills/analytics.md` conventions.

## Acceptance Criteria
- [ ] AC-1: `POSTHOG_API_KEY` unset → backend imports and runs cleanly; no
      network calls; `track()` is a no-op.
- [ ] AC-2: `POSTHOG_API_KEY` set → `ats_scanned` and `card_reviewed` show
      up in the PostHog Live Events feed within seconds of the action.
- [ ] AC-3: `VITE_POSTHOG_KEY` unset → frontend builds and runs; no console
      errors; capture calls no-op.
- [ ] AC-4: `VITE_POSTHOG_KEY` set → `card_viewed`, `paywall_hit`, and
      `study_dashboard_viewed` appear in the PostHog dashboard.

## Out of Scope
- Dashboards, funnels, retention cohorts — Phase 4.
- Identify/alias on login — deferred until auth refactor.
- Extensive unit tests for analytics — per spec direction, manual
  verification via the PostHog Live Events feed is sufficient.

## Dependencies
- Spec #07 (card viewer UI) — for `card_viewed`.
- Spec #06 (study dashboard / FSRS) — for `card_reviewed` and
  `study_dashboard_viewed`.
- Existing ATS scanner — for `ats_scanned`.
