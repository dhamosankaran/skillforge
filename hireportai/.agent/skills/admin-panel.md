---
description: Admin surface — card CRUD, bulk import, AI card generation, analytics dashboard, audit log, and admin access model
---
# Admin Panel Skill

## Overview

The admin surface gives operators a way to manage content, observe product
health, and audit their own actions. It is a single-page admin layout
(`/admin/*`) gated by the `users.role` column — **no separate admin login,
no separate admin user table**.

Surfaces shipped:
- **Cards** — create / edit / delete / bulk-import / AI-generate (Phase 3,
  spec `phase-3/17-admin-card-crud.md`)
- **Registration logs** — filterable view of sign-ups by IP / date
- **Analytics** — OKR metrics, performance, behavior funnels, enhancement
  signals, feedback themes (Phase 5, spec `phase-5/38-admin-analytics.md`)
- **Audit log** — every admin request, paginated (Phase 5, same spec)

## Key Files

### Backend
- `app/api/v1/routes/admin.py` — cards CRUD + AI draft + bulk import + registration logs + audit log
- `app/api/v1/routes/admin_analytics.py` — analytics dashboard endpoints (Phase 5)
- `app/api/v1/routes/admin_decks.py` — deck CRUD + archive + admin-LIST (Phase 6 slice 6.4b)
- `app/api/v1/routes/admin_lessons.py` — lesson CRUD + publish + archive + per-deck list (Phase 6 slice 6.4b)
- `app/api/v1/routes/admin_quiz_items.py` — quiz_item CRUD + retire + per-lesson list (Phase 6 slice 6.4b)
- `app/core/deps.py` — `require_admin` + `audit_admin_request` chain
- `app/services/card_admin_service.py` — card CRUD + CSV import
- `app/services/ai_card_service.py` — Gemini draft generation
- `app/services/deck_admin_service.py` / `lesson_admin_service.py` / `quiz_item_admin_service.py` — Phase 6 admin authoring services (slice 6.4b)
- `app/services/admin_errors.py` — shared admin error classes + `SUBSTANTIVE_EDIT_THRESHOLD = 0.15`
- `app/models/registration_log.py` — signup audit
- `app/models/admin_audit_log.py` — admin request audit (Phase 5)

### Frontend
- `src/components/admin/AdminLayout.tsx` — multi-route admin shell (sidebar + `<Outlet />`; Phase 6 slice 6.4a)
- `src/pages/admin/AdminCards.tsx` — card CRUD + AI draft + bulk-import (extracted from old `AdminPanel.tsx` per spec #04 §12 D-12; Phase 6 slice 6.4a)
- `src/pages/admin/AdminDecks.tsx` — deck list editor (Phase 6 slice 6.4b)
- `src/pages/admin/AdminDeckDetail.tsx` — deck-detail editor with persona-narrowing modal (Phase 6 slice 6.4b)
- `src/pages/admin/AdminLessonEditor.tsx` — lesson editor with substantive-edit cascade modal (Phase 6 slice 6.4b)
- `src/pages/admin/AdminQuizItems.tsx` — quiz-item editor with retire-and-replace flow (Phase 6 slice 6.4b)
- `src/pages/AdminAnalytics.tsx` — analytics dashboard (Phase 5)
- `src/components/admin/MarkdownEditor.tsx` — edit/preview-tab markdown editor (Phase 6 slice 6.4b)
- `src/components/admin/ConfirmCascadeModal.tsx` — pre-PATCH cascade warning + post-PATCH results-view (Phase 6 slice 6.4b)
- `src/components/admin/ConfirmPersonaNarrowingModal.tsx` — D-19 amended persona-narrowing copy (Phase 6 slice 6.4b)
- `src/utils/lessonEdit.ts` — FE-side substantive-edit classifier mirroring BE `_is_substantive_change` (Phase 6 slice 6.4b)
- `src/context/AuthContext.tsx` — `user.role` source of truth

> **Removed slice 6.4a + 6.4b:** `src/pages/AdminPanel.tsx` (deleted per spec #04 §12 D-12 — extract path; replaced by `<AdminLayout>` + `pages/admin/AdminCards.tsx`); `src/pages/AdminAudit.tsx` (never shipped per spec #04 §12 D-14 — `/admin/audit` link dropped from sidebar; BE endpoint `GET /api/v1/admin/audit` is live and un-consumed; future FE consumer = file new BACKLOG row when product demand surfaces).

## Access Control

Every admin route **must** declare `Depends(require_admin)`. This dep:
- Re-uses `get_current_user` (JWT verification + DB lookup).
- Raises `HTTPException(403, "Admin access required.")` when
  `user.role != "admin"`.
- Reads role from the database on every request — **no role claim in JWT**.
  Consequence: demotion takes effect immediately without requiring a new
  token. Promotion does too.

Frontend mirror: `<AdminGate>` (`src/components/auth/AdminGate.tsx`)
wraps `<AdminLayout>` in `App.tsx` and renders a 403 view when
`user.role !== 'admin'` — chunks for nested admin routes are not
downloaded for non-admins. Never rely on frontend-only gating — it is
UX sugar; the backend dep is the actual boundary.

## Admin Promotion

Promotion is via direct DB update today:
```sql
UPDATE users SET role = 'admin' WHERE email = '<email>';
```

There is no UI for this. A promotion UI is a deliberate follow-up (flagged
in spec `phase-5/38-admin-analytics.md` §Admin Access & Audit as a
follow-up spec).

Google re-login does NOT reset role (`get_or_create_user` preserves
`role` on updates — only `name` and `avatar_url` are refreshed).

## Audit Logging

Every request to `/api/v1/admin/*` writes one row to `admin_audit_log`
via the `audit_admin_request` FastAPI dependency (fire-and-forget via
`BackgroundTasks` — audit I/O never blocks responses).

Row shape: `{admin_id, route, method, query_params, ip_address, created_at}`.

Index `(admin_id, created_at DESC)` backs the `/admin/audit` view.
Index `(route, created_at DESC)` backs per-endpoint forensic queries.

FK `admin_id → users.id ON DELETE RESTRICT`: audit rows anchor the user
row, intentional so an admin cannot be deleted while an audit trail
references them.

**Never attach the audit dep to non-admin routes** — it would log legit
user traffic as admin and confuse the dashboard.

## AI Card Generation

- Input: `{topic: str, difficulty: 'easy'|'medium'|'hard'}`
- LLM: `generate_for_task(task="admin_card_generate", tier="fast", ...)`
  per R11.
- Output: `CardDraft` for admin review before publish (not auto-inserted).
- Rate limit: `5/minute` per admin (`limiter.limit("5/minute")` — see
  `admin.py`). Tighter ceilings deliberately prevent accidental LLM cost
  spikes.

Emits `admin_card_draft_generated` (see `analytics.md` catalog).

## Analytics Dashboard (Phase 5)

Five sections, each a dedicated endpoint under
`/api/v1/admin/analytics/*`:

| Section | Source | LLM? | Cache |
|---------|--------|------|-------|
| Metrics | Postgres (users, subs, card_reviews, usage_log) | No | 5 min |
| Performance | Postgres (usage_log, stripe_event) + backend latency | No | 5 min |
| Behavior | PostHog Query API (HogQL) | No | 5 min |
| Enhancement signals | Postgres (paywall_dismissal, card_feedback) + `search_no_results` event | No | 5 min |
| Feedback themes | Postgres (card_feedback.comment) → LLM cluster | Yes (`admin_feedback_cluster`, fast tier) | 24 h |

Rate limit on `/themes`: `10/hour` per admin. Other analytics endpoints
are unrate-limited (cheap aggregate queries).

CSV export: `?format=csv` on any endpoint returns `text/csv`. Rows capped
at 10k per export.

See spec `phase-5/38-admin-analytics.md` for schemas, acceptance
criteria, and rollout plan.

## Admin-only PostHog Events

All admin-originating events set `internal: true` in properties so they
can be excluded from user-facing funnels:
- `admin_card_draft_generated` (backend) — see `analytics.md` catalog
- `admin_card_created`, `admin_card_updated`, `admin_card_deleted`,
  `admin_cards_imported` (backend, per spec #17)
- `admin_analytics_viewed`, `admin_analytics_section_drilled`,
  `admin_analytics_export_clicked` (frontend, Phase 5)
- `admin_deck_created`, `admin_deck_updated`, `admin_deck_archived`,
  `admin_deck_persona_narrowed` (backend, Phase 6 slice 6.4b)
- `admin_lesson_created`, `admin_lesson_updated_minor`,
  `admin_lesson_substantively_edited`, `admin_lesson_published`,
  `admin_lesson_archived` (backend, Phase 6 slice 6.4b)
- `admin_quiz_item_created`, `admin_quiz_item_retired` (backend, Phase
  6 slice 6.4b — `retire_reason` discriminates direct / cascade /
  retire-and-replace)

## Security Considerations

- **PII in admin views**: the analytics themes endpoint scrubs email /
  phone / URL from feedback comments before LLM clustering and before
  echoing `representative_quotes`. Other admin endpoints (user list,
  registration logs) expose PII by design and rely on audit logging +
  human accountability.
- **Admin actions on paid users**: deletions / role changes should trigger
  a confirmation modal on the frontend, but the backend is the boundary —
  never rely on confirmation for access control.
- **LLM cost ceiling**: `/admin/cards/generate` is 5/min, `/analytics/themes`
  is 10/hour. Raising either requires a BACKLOG row + sign-off.
- **No MFA today**: admin sign-in is Google OAuth, single factor.
  Acceptable for the current ops footprint; flagged as a follow-up in
  spec `phase-5/38-admin-analytics.md` §Admin Access & Audit.

## Adding a New Admin Endpoint

1. Put the route in `app/api/v1/routes/admin.py` (or a sibling admin_*.py
   module if it grows).
2. Declare `Depends(require_admin)` on the route.
3. Declare `Depends(audit_admin_request)` on the route (Phase 5+).
4. If the route calls an LLM, route it through `llm_router.generate_for_task`
   with a task name prefixed `admin_` (e.g. `admin_feedback_cluster`).
   Add the task to `llm_router.py` if new.
5. Add a PostHog event with `internal: true` in the properties; register
   it in `.agent/skills/analytics.md`.
6. If the route is expensive (>1s typical) and idempotent, wrap results
   in Redis cache keyed by route + query params.
7. If the route is LLM-backed or otherwise cost-sensitive, add a rate
   limit via the existing `limiter` decorator.
8. Add tests to `tests/test_admin_*.py` — always include
   `test_non_admin_blocked` and `test_unauthenticated_blocked` variants.
9. Update this skill file with the new endpoint in the table above.
