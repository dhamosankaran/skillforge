# Spec #57 — Tracker-Level Interview Date + Company (Shape 1)

**Status:** Draft — authored 2026-04-23, awaiting CODEX review
**Owner:** Dhamo
**Phase:** 5
**Closes (on implementation):** BACKLOG **E-042** 🔴 P1. Subsumes BACKLOG **E-017** 🔴 (Profile-side editor for `users.interview_target_date` becomes obsolete — flips to ✅ in the same slice that lands E-042's refactor).
**Depends on:** Spec #34 (PersonaPicker capture contract) — amended here to stop writing `users.interview_target_*`. Spec #53 (Interview Target Optional Fields) — amended: LD-3 "link to PersonaPicker" becomes "link to `/prep/tracker` new-row flow" (amendment ships in its own bookkeeping slice; see §12).
**Unblocks:** BACKLOG **E-043** (ATS re-scan loop — needs per-application target context to route the before/after score widget).

---

## 1. Problem

### 1.1 Two revenue-cost CTAs route through PersonaPicker

The 2026-04-23 interview-date CTA audit (scout report, same session as the BACKLOG bookkeeping slice that filed E-042) confirmed two surfaces dump users into `/onboarding/persona` for what is effectively an "update my interview date" action:

- `src/components/home/widgets/CountdownWidget.tsx` — Mode 1 (no date) "Add an interview date to unlock countdown" CTA navigates to `/onboarding/persona` (spec #53 LD-4).
- `src/components/mission/MissionDateGate.tsx` — "Set a date to start a sprint" CTA navigates to `/onboarding/persona` (spec #53 §7.3).

PersonaPicker is the **persona capture** surface. Re-using it as a date-edit surface is wrong shape: it's labelled for new users, has no "return to origin" UX, and is the redirect target for `PersonaGate` (null-persona users). E-017 🔴 exists specifically to ship a Profile-side editor, but that editor is also wrong shape because the real problem is upstream — interview targets are modelled at user scope, not application scope.

### 1.2 The data model mismatch

`users.interview_target_date` + `users.interview_target_company` are 1:1 with the user record. Real-world users — especially senior engineers prepping for 3–5 interviews in parallel — have many applications, each with its own interview date and company. Per `docs/prd.md §1.3`:

> **Interview-Prepper** — "I have a Google interview in 14 days"

The PRD persona phrasing embeds the singular ("a Google interview"), but the product-scope conversation on 2026-04-23 unlocked the multi-application reality: one user → many tracked applications, each with its own interview date.

### 1.3 What spec #53 said and why it's now wrong

Spec #53 **LD-3** (Locked Decision, 2026-04-22): downstream copy for the no-date state frames adding a date as an optional upgrade; the unlock CTA links to the current canonical persona-edit path (PersonaPicker in V1 per LD-4). That decision was right for a world where interview targets live on `users`. In the world where they live on `tracker_applications_v2`, the correct CTA target is `/prep/tracker` (new-row or existing-row edit), and PersonaPicker drops out of the date-edit flow entirely. **This spec amends LD-3 + LD-4.** The concrete amendment to spec #53 ships in its own bookkeeping slice (§12).

---

## 2. Solution — Shape 1

One column on `tracker_applications_v2`. No child events table. Multi-round scheduling is out of scope — if a user has a phone screen + on-site + final, they create three tracker rows.

### 2.1 Schema

- **Add** `tracker_applications_v2.interview_date : Date | null`. Default null. New column only; no type change, no rename.
- **Deprecate (not drop)** `users.interview_target_date` and `users.interview_target_company`. The columns stay on disk through this slice + one release of dual-write fallback. A **Phase-6 cleanup slice** drops them after: (i) the backfill migration has run in prod, (ii) no code reads them, (iii) one release has shipped with the deprecation in effect.
- **No new `interview_company` column on tracker rows.** `tracker_applications_v2.company` already exists (`String(200)`, NOT NULL) — it IS the company field. The deprecated `users.interview_target_company` is obviated by the existing tracker `company` column; no new column is needed on the tracker side.

### 2.2 Reads — the Countdown selection rule

Countdown widget on `/home` computes the "nearest upcoming interview" per:

```
MIN(interview_date)
  WHERE interview_date >= CURRENT_DATE
    AND status IN ('Applied', 'Interview')
    AND user_id = :caller
ORDER BY interview_date ASC, created_at ASC
LIMIT 1
```

Tie-break on identical dates: earliest `created_at` wins. `'Offer'` and `'Rejected'` rows are excluded from countdown selection regardless of `interview_date` value.

### 2.3 Writes — where dates get set

- **New tracker row** (`POST /api/v1/tracker/`): optional `interview_date` in body.
- **Edit tracker row** (`PATCH /api/v1/tracker/{id}`): optional `interview_date` in body.
- **PersonaPicker stops writing interview targets.** New code path: PersonaPicker captures `persona` only. The expansion block on the Interview-Prepper card is removed; the date + company inputs and their helper copy move to a follow-up UI-cleanup slice referenced from §7.1 but not in scope here.
- **`PATCH /api/v1/users/me/persona` continues accepting `interview_target_date` + `interview_target_company`** for one release (dual-write for backfill safety; dropped in the Phase-6 cleanup slice). No new code paths write them after this spec lands — existing writers are converted in §7.

### 2.4 Why this shape, not Shape 2 (child events table)

A separate `interview_events` table (many-to-one with tracker applications) would capture phone screen → on-site → final-round granularity. Rejected here:
- 95th-percentile users are still single-round-per-app; multi-round is a minority use case.
- Users who want multi-round tracking can create separate tracker rows (one per round). Clunky, but supported.
- A child table adds join complexity to every countdown read, plus a "which event is the primary interview" tiebreak question that doesn't exist in Shape 1.
- If telemetry motivates, Shape 2 can follow in its own spec later; Shape 1's column is forward-compatible (child events would reference `tracker_application_id`, not `user_id`).

---

## 3. Acceptance Criteria

- **AC-1 — Column add.** `tracker_applications_v2` gains `interview_date : Date | null`. Default null. Existing rows unaffected by the schema change alone. Asserted by: Alembic `upgrade` against a seeded dataset — `SELECT COUNT(*) FROM tracker_applications_v2 WHERE interview_date IS NOT NULL` returns 0 before backfill step.

- **AC-2 — PATCH accepts `interview_date`.** `PATCH /api/v1/tracker/{id}` accepts an optional `interview_date` in the request body. Validation: date MUST be ≥ today (reject past dates with HTTP 422), AND ≤ today + 365 days (consistent with existing P5-S16 validator pattern on `users.interview_target_date`). Empty string or missing field = unchanged. Explicit `null` = clear the date.

- **AC-3 — POST accepts `interview_date`.** `POST /api/v1/tracker/` accepts an optional `interview_date` in the request body with identical validation to AC-2.

- **AC-4 — `/home/state` returns `next_interview`.** `GET /api/v1/home/state` response gains a new `context.next_interview` field. Shape when present:
  ```json
  {
    "next_interview": {
      "date": "2026-05-14",
      "company": "Google",
      "tracker_id": "8e7c...-uuid"
    }
  }
  ```
  Value is `null` when no tracker row matches the §2.2 selection rule. The rest of the response shape is preserved — this is an additive, non-breaking change. TypeScript types on the FE side (`src/types/homeState.ts`) get an additive field with narrow optionality.

- **AC-5 — CountdownWidget consumes `next_interview`.** On `/home`, `CountdownWidget` reads `context.next_interview` from home state instead of `user.interview_target_date`.
  - If `next_interview !== null`: renders `"{N} days until {company}"` with a link to `/prep/tracker?focus={tracker_id}` (deep-link to that row's edit affordance). The existing ring/visual mode is preserved.
  - If `next_interview === null` AND `user.persona === 'interview_prepper'`: renders `"Add your interview date"` CTA with a button routing to `/prep/tracker?new=1` (new-row create flow — pre-fills no fields, opens the row editor with `interview_date` focused).
  - If `next_interview === null` AND `user.persona !== 'interview_prepper'`: widget does not render (omitted from the grid; no empty-state fallback).

- **AC-6 — MissionDateGate consumes the same rule.** `src/components/mission/MissionDateGate.tsx` applies the §2.2 selection rule via the same `context.next_interview` value. Its "Add interview date" CTA routes to `/prep/tracker?new=1` (NOT `/onboarding/persona`). No other MissionMode branch is touched.

- **AC-7 — Deprecated-field read audit.** `users.interview_target_date` and `users.interview_target_company` are marked DEPRECATED:
  - Docstring on the model (`app/models/user.py`) adds `"""DEPRECATED — see spec #57. Read-only fallback during one-release dual-write window. New code MUST NOT read these; use tracker_applications_v2.interview_date via home_state_service.get_next_interview() instead."""` on both columns.
  - `PATCH /api/v1/users/me/persona` continues to accept and write them (dual-write safety) for one release.
  - Audit: every existing reader is converted in this slice or a referenced follow-up slice. Known readers at spec time (grepped 2026-04-23):
    | Reader | File | Conversion |
    |---|---|---|
    | HomeDashboard countdown | `src/pages/HomeDashboard.tsx:115-116` | Convert to `context.next_interview` from home state. |
    | StudyDashboard header | `src/pages/StudyDashboard.tsx:144-170` | Convert to `context.next_interview` — same service. |
    | FirstAction CTA computer | `src/pages/FirstAction.tsx:80-83` | Convert to `context.next_interview`. Preserves the null-date branch ("Browse interview prep categories"). |
    | MissionMode gate | `src/pages/MissionMode.tsx:389` + `MissionDateGate.tsx` | Convert to `context.next_interview`. |
    | InterviewTargetWidget (B-017) | `src/components/home/widgets/InterviewTargetWidget.tsx` | Convert to `context.next_interview`. Three-case copy helper carries over verbatim; the fields it reads change source. |
    | `GET /api/v1/auth/me` response | `app/api/v1/routes/auth.py:46-49` | Response shape keeps the two fields (additive retention, not breaking) but they become stale-reads. Frontend `User` type retains them but no UI should read them after this slice. |
    | PersonaPicker body construction | `src/pages/PersonaPicker.tsx:87-111` | Strip the expansion block (date + company inputs removed from the Interview-Prepper card). Follow-up UI cleanup slice referenced from §7.1. |

- **AC-8 — Backfill migration.** Part of the same Alembic migration that adds the column (or a data-migration companion). For each user `U` with `users.interview_target_date IS NOT NULL`:
  1. **Find an existing row to seed.** Query `tracker_applications_v2 WHERE user_id = U.id AND status IN ('Applied','Interview') ORDER BY created_at DESC LIMIT 1`.
  2. **If found:** `UPDATE … SET interview_date = U.interview_target_date` on that row (does NOT touch its `company` — U's real company for that application was already captured in the tracker `company` field).
  3. **If not found:** insert a synthetic tracker row with:
     ```
     user_id            = U.id
     company            = COALESCE(U.interview_target_company, 'Unknown')
     role               = 'TBD'
     date_applied       = CURRENT_DATE in 'YYYY-MM-DD' (matches existing String(20) shape)
     status             = 'Interview'
     ats_score          = 0
     scan_id            = NULL
     skills_matched     = NULL
     skills_missing     = NULL
     interview_date     = U.interview_target_date
     created_at         = NOW()
     ```
     The synthetic `role='TBD'` + `ats_score=0` signals to the user that this row came from backfill and needs editing to be useful. The tracker row editor (§7.1) surfaces a non-blocking hint on backfilled rows (implementation-slice detail; not a blocking spec decision).
  4. **Down-migration (rollback).** The down-migration drops the `interview_date` column. The synthetic rows created by backfill remain — they represent a legitimate state (user's interview date on a synthetic tracker row) and are not destructive to preserve. Documented in the migration docstring.

- **AC-9 — Spec #53 LD-3 / LD-4 amendment pointer.** A separate bookkeeping slice (NOT this spec's implementation slice) amends spec #53:
  - LD-3 copy stays; LD-3's "link to persona-edit" becomes "link to `/prep/tracker` new-row flow (for null-date) OR existing-row edit (for date-present)."
  - LD-4 "canonical persona-edit path" is replaced by "canonical tracker-row edit path." References to `/onboarding/persona?return_to=` are removed; the `return_to` URL-param and its whitelist (OD-3) become unnecessary because the tracker row editor is already a first-class page with its own return behaviour.
  - OD-1, OD-2, OD-3 are marked RESOLVED with pointers back to this spec.
  The amendment slice is docs-only and ships after this spec is approved.

---

## 4. API Contract

### 4.1 `POST /api/v1/tracker/` — extended (additive)

Request body additions (Pydantic `TrackerApplicationCreate`):

```python
interview_date: Optional[date] = None  # ISO YYYY-MM-DD; must be >= today, <= today + 365
```

Validation — field validator rejects:
- Past dates → HTTP 422 with `loc=["body", "interview_date"]`, `msg="interview_date must be today or later"`.
- Dates more than 365 days out → HTTP 422 with `loc=["body", "interview_date"]`, `msg="interview_date must be within 365 days"`.

Response: existing `TrackerApplicationRead` shape gains the optional `interview_date` field (additive).

### 4.2 `PATCH /api/v1/tracker/{id}` — extended (additive)

Request body additions (Pydantic `TrackerApplicationUpdate`):

```python
interview_date: Optional[date] = None  # same validation as §4.1
```

Per `PATCH` semantics: field absent → unchanged; field present with value → update; field present with explicit `null` → clear. Pydantic `model_fields_set` or equivalent MUST be used to distinguish "absent" from "explicit null" in the handler — implementation detail, flagged here so the impl slice doesn't collapse them.

### 4.3 `GET /api/v1/home/state` — extended (additive)

Response addition:

```python
class HomeStateContext(BaseModel):
    # ... existing fields ...
    next_interview: Optional[NextInterview] = None


class NextInterview(BaseModel):
    date: date
    company: str
    tracker_id: str
```

Computed via `home_state_service.get_next_interview(user_id, db)` per the §2.2 selection rule. Result is cached under the existing home-state Redis cache (keyed on `user_id`; invalidated on tracker row write per §4.4).

### 4.4 Cache invalidation

Any write to a tracker row (`POST /tracker/`, `PATCH /tracker/{id}`, `DELETE /tracker/{id}`) must call `home_state_service.invalidate(user.id)` — same pattern as `PATCH /users/me/persona` at `app/api/v1/routes/users.py:47`. Implementation slice confirms the existing tracker write path either already invalidates or needs the call added.

### 4.5 `PATCH /api/v1/users/me/persona` — unchanged but deprecated writers

The endpoint continues to accept `interview_target_date` + `interview_target_company` for one release (dual-write safety). PersonaPicker stops writing them (§7.1). After one release, the Phase-6 cleanup slice removes the fields from `PersonaUpdateRequest` and the underlying User columns.

---

## 5. Data Model Changes

### 5.1 Alembic migration (one revision)

- **`op.add_column('tracker_applications_v2', sa.Column('interview_date', sa.Date(), nullable=True))`** — the column add.
- **Partial index** — cheap countdown reads:
  ```sql
  CREATE INDEX ix_tracker_user_interview_active
    ON tracker_applications_v2 (user_id, interview_date)
    WHERE interview_date IS NOT NULL
      AND status IN ('Applied', 'Interview');
  ```
  Alembic: `op.create_index(..., postgresql_where=sa.text("interview_date IS NOT NULL AND status IN ('Applied','Interview')"))`.
- **Data migration (AC-8 backfill)** runs in the same revision after the column + index exist. Implementation-slice author decides between an inline `op.execute(...)` block and a separate data-migration revision; either is acceptable as long as the backfill runs before the Phase-6 cleanup slice drops the deprecated columns.
- **Down-migration** drops the partial index, then drops the column. Synthetic rows inserted by backfill remain (§AC-8 note); documented in revision docstring.

### 5.2 ORM model update

`app/models/tracker.py` gains:

```python
from datetime import date
# ...
interview_date: Mapped[date | None] = mapped_column(Date, nullable=True)
```

No relationship change. `TrackerApplicationModel` does not need a new relationship to `User` for the countdown read — `home_state_service` queries by `user_id` directly.

### 5.3 User model — deprecation annotation

`app/models/user.py` existing columns get updated docstrings (no schema change):

```python
# DEPRECATED — see spec #57.
# Dual-write retained one release post-spec-57 for backfill safety.
# New code MUST read tracker_applications_v2.interview_date via
# home_state_service.get_next_interview(user_id, db) instead.
# Column drop: Phase-6 cleanup slice, gated on zero in-code readers.
interview_target_company: Mapped[str | None] = mapped_column(String(100), nullable=True)
interview_target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
```

---

## 6. UI / UX

### 6.1 Surfaces touched

Three.

**1. Tracker row create / edit form** (`src/pages/Tracker.tsx` + the row editor modal/page, exact file picked at implementation audit time).
- New optional field: **Interview date** (native HTML5 `<input type="date">` per spec #53 LD-2). Label: "Interview date". Helper: `"Optional — add when the interview is scheduled."`.
- Field ordering: after `status`, before `skills_*` lists.
- Validation: client-side `min` attribute = today's ISO date; server echoes AC-2 / AC-3 validation on submit.
- The tracker form also accepts a query-param hint `?new=1` (opens in new-row mode) and `?focus={tracker_id}` (scrolls/opens the specified row's edit affordance). These are used by Countdown + MissionDateGate CTAs per AC-5 / AC-6. Exact scroll/focus UX is an implementation-slice detail.

**2. CountdownWidget** (`src/components/home/widgets/CountdownWidget.tsx`).
- Reads `next_interview` from home state (AC-5).
- Date-present render (existing "N days until ..." shape) — `company` string comes from tracker row, not user record. Ring mode preserved.
- No-date render: "Add your interview date" CTA → `/prep/tracker?new=1`.
- The existing inline `<input type="date">` + Save button **inside the widget is removed** — date capture moves to the tracker row editor. Rationale: spec #53 OD-2 flagged the inline input as visually inconsistent with MissionDateGate; Shape 1 resolves it by centralising capture in the tracker.
- The `updatePersona` call path inside CountdownWidget is deleted — the widget no longer writes to the user record at all.

**3. MissionDateGate** (`src/components/mission/MissionDateGate.tsx`).
- Reads the same `next_interview` (AC-6).
- Date-gate CTA target changes from `/onboarding/persona` to `/prep/tracker?new=1`.
- Telemetry `countdown_unlock_cta_clicked` stays; `surface: 'mission_mode'` unchanged.

**PersonaPicker is NOT touched in this slice.** The expansion block on the Interview-Prepper card (date + company inputs) is removed in a follow-up UI-cleanup slice — it's not critical for shipping the backend + read-path migration, and doing it here would bundle a frontend-heavy change with a data-model change. Until the cleanup slice ships, PersonaPicker's expansion block is a vestigial writer of the deprecated columns; dual-write in `/users/me/persona` handles it safely. Follow-up slice is referenced from §12.

### 6.2 Design tokens

All copy changes use existing design-token classes per `.agent/skills/design-system.md`. No new tokens.

### 6.3 Deep-link query params

- `/prep/tracker?new=1` — open new-row flow; pre-fill nothing.
- `/prep/tracker?focus={tracker_id}` — open existing row for edit. If `tracker_id` doesn't resolve (deleted between navigation and page load), fall back to the tracker list view with a toast `"That application was removed."`.
- Whitelist: no open-redirect risk — both params are internal routing hints, not URLs.

---

## 7. Analytics Events

### 7.1 New events

| Event | Side | Properties | Fires when |
|---|---|---|---|
| `tracker_interview_date_set` | FE | `{ tracker_id: string, days_until: number, source: 'create' \| 'edit' \| 'backfill' }` | Tracker row editor successfully writes an `interview_date` via `POST`/`PATCH`. `source='create'` for POST, `source='edit'` for PATCH. `source='backfill'` is written **only by the migration's data step** (BE event, not FE) — same event name, different side. |
| `tracker_interview_date_cleared` | FE | `{ tracker_id: string }` | Tracker row editor PATCHes `interview_date: null` (explicit clear). |
| `countdown_widget_rendered` | FE | `{ has_date: boolean, days_until?: number }` | `CountdownWidget` mounts. `days_until` is present only when `has_date === true`. |
| `countdown_widget_add_date_cta_clicked` | FE | `{ source: 'home' \| 'mission_gate' }` | The "Add your interview date" / "Set a date to start a sprint" CTA is clicked. |

### 7.2 Retired events

Removed in this slice (not in a separate cleanup slice):

- **`interview_target_date_skipped`** — fired by PersonaPicker `handleContinue` (spec #53 §9). PersonaPicker no longer captures dates, so the event no longer makes sense. Remove the call site in the same slice that removes the PersonaPicker expansion block.
- **`interview_target_date_added`** (with `source='onboarding'` or `'home_cta'`) — superseded by `tracker_interview_date_set`. Call sites in PersonaPicker + CountdownWidget go away in this slice.

### 7.3 Preserved events

- `countdown_unlock_cta_shown` / `countdown_unlock_cta_clicked` (spec #53 §9) — still fire from MissionDateGate. `surface` values unchanged.
- `persona_picker_shown`, `persona_selected` — unchanged (date-skip sub-property removed per §7.2 above).
- `home_dashboard_viewed`, `first_action_viewed` — unchanged.

### 7.4 Catalog update

`.agent/skills/analytics.md` gets the four new events added under the Home / Prep section and the two retired events moved to a "Retired events" note (or equivalent existing pattern). Done in the implementation slice, not this spec slice.

### 7.5 PostHog cohort note

"interview_preppers with an upcoming tracker-row date" becomes the canonical segment for "active Interview-Prepper." Dashboards that split by persona should further split Interview-Prepper by `has_next_interview: boolean` (computable from the `next_interview` field in home state — dashboard-side query, not a new event).

---

## 8. Edge Cases

1. **Three future dates.** User has 3 tracker rows in `status='Applied'` with dates `2026-05-01`, `2026-05-14`, `2026-05-20`. Countdown picks `2026-05-01`. If that row is deleted, next `/home` load returns `2026-05-14`.

2. **Today.** `next_interview.date === CURRENT_DATE`. Widget renders `"Today"` (not `"0 days until"`). FE formatter handles the zero-day case; copy in §AC-5 must honour.

3. **Date passes mid-session.** User opens `/home` at 23:58 with a date of "today"; at 00:02 the server advances. No live reactivity needed — next `/home` navigation recomputes `next_interview` and the widget updates. Documented so the impl doesn't chase a live WebSocket / polling design.

4. **Backfill edge — all existing rows terminal.** User has `users.interview_target_date IS NOT NULL` but every `tracker_applications_v2` row is `status IN ('Offer', 'Rejected')`. Migration falls through to the synthetic-row branch (AC-8 step 3). User sees a new tracker row with `role='TBD', ats_score=0, status='Interview', interview_date=<their old date>`. Non-destructive; user edits the row to flesh it out.

5. **User deletes their only future-date row.** Next `/home` load: `next_interview === null`. Widget shows "Add your interview date" CTA (persona=interview_prepper path). Graceful; no error state.

6. **Status transition.** User moves a future-date row from `Interview` → `Rejected`. That row exits the selection pool immediately. If it was the only match, next `/home` load shows `next_interview === null`. No retroactive mutation of `interview_date` — the date stays on the row (useful for score-delta history via E-043), it just doesn't participate in countdown selection.

7. **User with `persona !== 'interview_prepper'` but a future interview_date on a tracker row.** Countdown widget does **not** render for that user (AC-5 final branch). `next_interview` is still computed server-side (not persona-gated), so the field is present in the response — but the widget decides to omit itself. If a future slice wants to surface the countdown for non-Interview-Prepper personas, that's a UI-only change.

8. **Tracker row without a user.** Tracker rows can have `user_id IS NULL` (unauthenticated usage legacy, per `TrackerApplicationModel` comment). These rows are excluded from the selection rule — `WHERE user_id = :caller` naturally filters them. No change needed.

9. **Concurrency — user PATCHes date while `/home/state` is cached.** Redis cache invalidation on any tracker write (§4.4) guarantees the next `/home/state` read recomputes. Between the write-commit and the invalidation call, a concurrent read returns stale — bounded by the existing home-state cache TTL (short; see `home_state_service._write_cache`). Acceptable stale window; no new locking.

10. **Validation bypass attempt — past date via direct API.** `POST /api/v1/tracker/` body with `interview_date: "2020-01-01"` → HTTP 422 (AC-2 validator). No way to bypass client-side validation. Existing test pattern from `test_users_persona.py` covers this shape.

---

## 9. Test Plan (spec-level, not test code)

### 9.1 Backend

Extend `hirelens-backend/tests/test_tracker.py` (or create a sibling file if scope grows):

- **Unit — selection rule.** Seed 3 tracker rows with mixed statuses + dates; assert `home_state_service.get_next_interview(user_id, db)` returns the correct one per §2.2 rule.
- **Unit — tie-break.** Seed 2 rows with identical `interview_date`; assert earlier `created_at` wins.
- **Unit — excludes terminal statuses.** Seed rows with `status='Offer'` and `status='Rejected'`; assert they're excluded.
- **Integration — `/home/state` shape.** `GET /api/v1/home/state` returns `context.next_interview` as a valid `NextInterview` object when a match exists, `null` otherwise. Additive field presence asserted; no existing field mutated.
- **Integration — `POST /tracker/` validation.** Past date → 422. Future > 365d → 422. Valid date → 200 + persisted. Null/omitted → 200 + field stays null.
- **Integration — `PATCH /tracker/{id}` validation.** Same three cases. Plus explicit-null path clears the date.
- **Integration — cache invalidation.** `POST` or `PATCH` triggers `home_state_service.invalidate(user.id)` — asserted via a mock on the service or by observing the cache state before/after.
- **Migration unit — backfill find-and-seed.** Seed a user with `users.interview_target_date` + one `status='Applied'` tracker row; run the backfill; assert the tracker row's `interview_date` matches the user's value.
- **Migration unit — backfill synthetic-row.** Seed a user with `users.interview_target_date` + only terminal tracker rows; run the backfill; assert a new tracker row was inserted with `role='TBD', ats_score=0, status='Interview', interview_date=<value>, company=COALESCE(...)`.
- **Migration unit — no-op.** User with `users.interview_target_date IS NULL` is untouched by the backfill.
- **Dual-write regression.** `PATCH /api/v1/users/me/persona` body with `interview_target_date` still writes successfully and is readable via `GET /api/v1/auth/me` (one-release compatibility).

### 9.2 Frontend

- **Unit — CountdownWidget date-present.** Fixture with `next_interview = {date, company, tracker_id}`; render the widget; assert copy contains company name, day count, link `href` includes `?focus={tracker_id}`.
- **Unit — CountdownWidget no-date interview_prepper.** Fixture with `next_interview=null, persona='interview_prepper'`; assert "Add your interview date" CTA renders with link to `/prep/tracker?new=1`.
- **Unit — CountdownWidget no-date other persona.** Fixture with `next_interview=null, persona='career_climber'`; assert widget does not render.
- **Unit — CountdownWidget today.** Fixture with `next_interview.date === today`; assert copy shows "Today", not "0 days until".
- **Unit — MissionDateGate CTA target.** Fixture with `next_interview=null, persona='interview_prepper'`; assert CTA `href`/navigation target is `/prep/tracker?new=1`, NOT `/onboarding/persona`.
- **Unit — Tracker row editor.** Renders the new `interview_date` field; accepts a valid date; rejects past date on client-side validation; submits the full body correctly.
- **Integration — home state shape.** Mock `/home/state` response with `next_interview`; mount `HomeDashboard`; assert Countdown renders with tracker-sourced data, not user-sourced.
- **Regression — StudyDashboard header.** Converted to read `next_interview`; fixture with + without date; assert copy + day count match.
- **Regression — FirstAction null-branch preserved.** Null `next_interview` + `interview_prepper` → CTA label `"Browse interview prep categories"`, route `/learn` (preserves existing behaviour from `FirstAction.tsx:34-44`, just re-sourced).

### 9.3 Migration dry-run

Impl slice runs the migration against a seed dataset with known mix:

| Seed | Expected after migration |
|---|---|
| User A: `target_date='2026-05-01'`, 2 `Applied` rows | Newest `Applied` row's `interview_date = 2026-05-01` |
| User B: `target_date='2026-06-10'`, 0 rows | Synthetic row inserted |
| User C: `target_date IS NULL`, 3 rows | No change |
| User D: `target_date='2026-05-15'`, only `Offer`/`Rejected` rows | Synthetic row inserted |

Assert row counts + field values match expectations; assert no existing row's `date_applied` or `ats_score` mutated.

---

## 10. Rollout + Cleanup

- **FE + BE ship in one release** (same commit / same deploy). Backend adds the column + endpoint fields + `next_interview`; frontend reads the new field. No feature flag — the additive shape means old FE against new BE is safe (new field ignored) and new FE against old BE would only affect the 10-minute deploy window.
- **Phase-6 cleanup slice** (separately tracked BACKLOG row, filed as part of or alongside this spec's impl slice):
  - Drop `users.interview_target_date` and `users.interview_target_company` columns.
  - Remove the fields from `PersonaUpdateRequest` + `PATCH /api/v1/users/me/persona` body shape.
  - Remove the fields from `GET /api/v1/auth/me` response (additive removal — FE has no readers by then).
  - Remove `interview_target_date` + `interview_target_company` from the FE `User` type.
  - Gate: (i) this spec's impl has shipped and run in prod for one full release, (ii) `grep -rn 'interview_target_date\|interview_target_company' hirelens-backend hirelens-frontend` returns zero reader-site hits (writers in dual-write paths OK and get removed by the same slice), (iii) no open bug referencing the deprecated fields.
- **E-017 flip to ✅** happens in this spec's impl slice (not the cleanup slice) — E-017 is subsumed by the tracker-level refactor the moment the refactor ships, not when the deprecated columns drop.

---

## 11. Dependencies

- **Must land BEFORE E-043.** E-043's "ATS re-scan loop per tracker application" references this spec's per-application target context to route the home-widget score-delta display. E-043's spec will cite §4.3 `next_interview` to determine which tracker row's scores to surface on the Interview-Prepper home variant.
- **Independent of D-020** (missing `jd_hash` column). D-020's resolution can land before, after, or bundled with E-043; neither order blocks this spec's impl.
- **Spec #34 amendment.** PersonaPicker dropping the expansion block amends spec #34 §Solution "Interview-Prepper card expands on selection" contract. Amendment ships in the follow-up UI-cleanup slice referenced from §7.1.
- **Spec #53 amendment (AC-9).** Separate bookkeeping slice, docs-only, after this spec is approved. Covers LD-3 / LD-4 / OD-1 / OD-2 / OD-3.
- **Phase-6 cleanup slice.** Gated on the conditions in §10. Separately tracked; not a hard dep for this spec's impl.

---

## 12. Out of Scope

- **Multi-round interview scheduling** (child events table). If telemetry motivates, Shape 2 follows in its own spec.
- **PersonaPicker expansion-block removal.** Referenced from §7.1 as a follow-up UI-cleanup slice. Removing it in this impl slice would bundle frontend form work with backend schema work — kept separate.
- **Phase-6 deprecated-column drop.** Gated on the conditions in §10.
- **Countdown for non-Interview-Prepper personas.** `next_interview` is computed server-side regardless of persona; the widget chooses not to render for other personas (AC-5). If a future persona (e.g., Career-Climber) wants to see their nearest interview, that's a UI-only change.
- **Tracker row editor deep-link UX detail** (exact scroll/focus animation for `?focus={tracker_id}`). Implementation-slice detail.
- **PostHog cohort dashboard rework.** Cohort split note in §7.5 is a "nice to have" for the analytics skill; no spec-level change.
- **`jd_hash` / `jd_text` column adds.** Owned by E-043 / D-020.

---

## 13. R15

**E-042 is NOT closed by this spec.** Spec is the design contract; the implementation slice closes E-042 on merge. E-017 is subsumed by E-042's impl-slice commit (flipped to ✅ with a "subsumed by E-042 — no separate editor needed" one-liner). Per CLAUDE.md R15 / C4, the impl-slice commit message includes `closes E-042, closes E-017 (subsumed)`.

---

*End of spec. No code in this slice. Implementation begins at E-042's impl slice — separate prompt, separate commit.*
