---
slice: P5-S63 (spec) + P5-S63-impl (impl)
base_sha: 80f84e6
drafted: 2026-04-26
locked_decisions: LD-A (endpoint), LD-B (render surface), LD-C (scope)
unblocks: B-059 (this spec's impl row)
related: spec #50 (wall mechanic — submit-time 402), spec #60 / B-045 (Analyze pre-flight precedent), LD-001 (consume-on-review)
---

# SPEC: Pre-flight Daily-Review Wall Gate on `/learn/daily`

## Status: Draft

> **Authoring note (2026-04-26 R19 audit):** chat-Claude's slice prompt cited the
> queue endpoint as `GET /api/v1/study/daily-queue` and the response schema as
> `DailyQueueResponse`. On-disk reality: BE endpoint is `GET /api/v1/study/daily`
> and the BE schema is `DailyReviewResponse` (`app/schemas/study.py:30`). FE
> aliases the same shape as `DailyQueueResponse` in `src/types/index.ts:195`.
> Both names refer to the same payload; this spec uses BE-canonical
> `DailyReviewResponse` everywhere with FE-alias `DailyQueueResponse` called
> out at the wire. The R19 audit also surfaced that `TodaysReviewWidget.tsx:20`
> is a second consumer of `fetchDailyQueue` — see LD-A rationale.

## 1. Problem

LD-001 + spec #50 (P5-S22-WALL-b, shipped) wired the free-tier daily-review
wall as a **submit-time** gate: `study_service._check_daily_wall` raises
`DailyReviewLimitError` → HTTP 402 inside `POST /api/v1/study/review`, and
`QuizPanel.tsx` catches the 402 and opens `PaywallModal trigger="daily_review"`.
The wall is correct but **fires too late** in the daily flow:

A free user who has exhausted today's `Settings.free_daily_review_limit` (default
10 per LD-001 amendment 2026-04-26) can:

1. Navigate from `/home` or `StudyDashboard` to `/learn/daily`.
2. Watch `fetchDailyQueue()` resolve and the queue render.
3. See the first card flip animation.
4. Grade the card.
5. Hit the modal **only at submit**.

Steps 2–4 are wasted motion and pollute analytics — the user did UX work for a
review that was always going to be walled. UX parity gap: spec #60 / B-045
(`19326de` precedent) already solved the equivalent gap on `/prep/analyze` for
the lifetime-scan cap (free user at cap sees a full-page upsell on page load,
no upload form). This spec does the same for daily review.

Cross-spec dependencies:
- **spec #50** — submit-time wall mechanic. Unchanged by this spec; pre-flight
  is purely additive.
- **spec #60** — Analyze pre-flight pattern. Named precedent; this spec mirrors
  it field-for-field.
- **LD-001 (consume-on-review)** — this spec doesn't amend LD-001, it makes
  LD-001's state visible at page-load.
- **B-057** — `/pricing` chrome carve-out (already shipped, `19326de`); the
  walled view's "Upgrade to Pro" CTA relies on it for the back-out path.

## 2. Solution

### 2.1 Backend contract

Extend `DailyReviewResponse` (`app/schemas/study.py:30`) with one new field:

```python
class DailyStatus(BaseModel):
    """Free-tier daily-review wall state, attached to DailyReviewResponse so
    /learn/daily can pre-flight-gate before any review work.

    Mirrors the spec #60 / B-045 pre-flight pattern for /prep/analyze.
    """

    cards_consumed: int   # 0 for Pro / Enterprise / admin (informational)
    cards_limit: int      # Settings.free_daily_review_limit for free; -1 sentinel for unlimited
    can_review: bool      # cards_consumed < cards_limit (free); always True for unlimited/admin
    resets_at: datetime   # next user-local midnight as ISO8601 with tz offset


class DailyReviewResponse(BaseModel):
    cards: list[DailyCardItem]
    total_due: int
    session_id: str
    completed_today: bool = False
    daily_status: DailyStatus  # new field, additive
```

**LD-A semantics (unlimited / admin):**
- Pro / Enterprise: `cards_limit = -1`, `can_review = True`, `cards_consumed = 0`.
- Admin (`user.role == "admin"`): same as Pro regardless of plan.
- Free: real values from the same Redis key `_check_daily_wall` reads
  (`daily_cards:{user_id}:{YYYY-MM-DD}` in user-local tz).

**Side-effect-free read** (LD-A invariant): the queue handler MUST NOT call
`Redis.INCR`. Use `Redis.GET` (or `_get_redis().get(key)` mirroring
`study_service._get_redis()` pattern). Counter mutation stays at submit-time
in `_check_daily_wall`.

**Reset semantics:** `resets_at` = next user-local midnight resolved via
`get_user_timezone(user.id, db)` (same helper `_check_daily_wall` uses); UTC
fallback when no `EmailPreference` row. Returned as ISO8601 with offset.

**Redis-outage fail-open** (mirror `_check_daily_wall` §Counter Storage):
when `_get_redis()` returns None or `.get` raises, return `cards_consumed=0`,
`can_review=True`. Same fail-open rationale as the wall — degrade to permissive
rather than wall-spam authenticated free users on infra hiccup. Log a warning;
the existing `daily_card_submit { counter_unavailable: true }` event still
fires at submit-time so observability is preserved.

### 2.2 Frontend contract

`DailyReview.tsx`:
- Reads `daily_status` from `fetchDailyQueue()` response (FE type alias
  `DailyQueueResponse` in `src/types/index.ts:195` extended additively).
- After fetch resolves: if `plan === 'free' && daily_status.can_review === false`,
  render `<DailyReviewWalledView resetsAt={...} cardsConsumed={...} cardsLimit={...} />`
  in place of the queue + `<QuizPanel>` mount. Pro / Enterprise / admin: render
  normally regardless of `daily_status` (defense-in-depth: BE returns
  `cards_limit=-1, can_review=true` for these plans, so the gate condition
  evaluates false, but the explicit plan check is the canonical UX gate per
  spec #60 §3.1 precedent).

Plan source: `useUsage()` `plan` + `isAdmin` (`UsageContext.tsx`). Mirrors
`Analyze.tsx:` 3-clause gate `!canScan && plan === 'free' && !isAdmin`.

Backwards-compat: existing FE callers that don't read `daily_status` (none
today besides `DailyReview.tsx` and — see LD-A — `TodaysReviewWidget.tsx`)
remain unbroken. The field is additive; old clients ignore it.

## 3. Render details — `DailyReviewWalledView`

**Component placement (locked at LD-B):** new component
`src/pages/DailyReviewWalledView.tsx` (or
`src/components/study/DailyReviewWalledView.tsx` — impl picks based on
test-import ergonomics; tracker spec doesn't pin this).

Rationale for extracting (vs inline branch in `DailyReview.tsx`):
- Testability: pre-flight branch is independently testable in
  `tests/pages/DailyReview.preflight.test.tsx` without mounting the full
  FSRS scheduler.
- Mirrors spec #60 / B-045 precedent which kept the gate-card inline (~10
  lines) but `DailyReview.tsx` is already 200+ lines — extracting reduces
  impl-slice diff churn.

**Props:**

```ts
interface DailyReviewWalledViewProps {
  resetsAt: string       // ISO8601 from daily_status.resets_at
  cardsConsumed: number  // for analytics + optional copy
  cardsLimit: number     // for analytics + optional copy
}
```

**Copy (locked):**
- Headline: **"You've used today's free reviews"**
- Subhead: live countdown via `formatResetsAt(resetsAt)` (≤12h relative
  "Resets in 4h 17m", >12h absolute "Resets at 12:00 AM").
- Body (optional, impl decides): "You've reviewed `{cardsConsumed}` of
  `{cardsLimit}` cards today. Upgrade to Pro for unlimited daily review."

**CTAs:**
- Primary: `<button>` "Upgrade to Pro" → `useNavigate()('/pricing')`. Note:
  B-057 carve-out (`19326de`) ensures the user lands on `/pricing` with chrome
  intact — they can navigate away after the upsell. **AC-7 verifies.**
- Secondary: `<Link to="/home">` "Back to home". Plain anchor, not
  `setShowPaywall(false)` — there's no modal to dismiss.

**Styling:** uses design tokens (`bg-bg-surface`, `text-text-primary`,
`text-text-secondary`, `bg-accent-primary` per Rule 12). No hardcoded hex.
Layout mirrors `Analyze.tsx`'s gate card (~line 132-144 post-`3c962d8`).

### 3.1 `formatResetsAt` lift

`formatResetsAt` is currently a **private function** in
`QuizPanel.tsx:117` (no `export` keyword). Its sibling `hoursUntil`
helper at `QuizPanel.tsx:111` is also private. Both are needed by
`DailyReviewWalledView` (subhead + analytics prop respectively).

**Impl-slice sub-task (locked):** lift both helpers to a new shared util at
`src/utils/formatResetsAt.ts` (or `src/utils/wallCountdown.ts` — impl picks
the name) exporting `formatResetsAt` and `hoursUntil`. Update the existing
`QuizPanel.tsx` import to consume from the new module. New
`DailyReviewWalledView.tsx` imports the same module. **Zero behavior change**
to the wall modal; this is a pure code-org move enabling reuse. Test file
`tests/components/QuizPanel.wall.test.tsx` MUST stay green unchanged
(the existing 5 tests pin observable copy/behavior, not import paths).

## 4. Analytics

Reuse the existing `daily_card_wall_hit` event (cataloged from spec #50 /
P5-S22-WALL-b). **Extend the payload**, do not introduce a new event.

Current payload (per `.agent/skills/analytics.md`):
`daily_card_wall_hit { resets_at_hours_from_now: int }`

Extended payload (this spec):
`daily_card_wall_hit { resets_at_hours_from_now: int, surface: "daily_review_submit" | "daily_review_page_load" }`

- `surface = "daily_review_submit"` — fired on `PaywallModal` open after a
  402 submit response (existing behavior, preserve verbatim — **AC-6
  regression guard**).
- `surface = "daily_review_page_load"` — fired once on
  `DailyReviewWalledView` mount via `useRef` idempotency guard (mirror
  `paywall_hit` once-on-mount pattern from B-045's
  `Analyze.tsx`).

**Do NOT fire `paywall_hit`** — that event is the Analyze-flow analytics row
per spec #56 / spec #60 catalog conventions. Daily flow has its own.

Catalog update sub-task: `.agent/skills/analytics.md` row for
`daily_card_wall_hit` updated to document the new `surface` enum. Same
mechanism used by spec #60 to extend `paywall_hit`.

Backwards-compat: existing wall-hit events that fire from `QuizPanel.tsx`
on submit-modal-open MUST gain the `surface: "daily_review_submit"` field at
impl time. PostHog ingests additive props without schema migration; old
event rows that lack `surface` simply have null in queries.

## 5. Acceptance Criteria

- **AC-1 (pre-flight gate fires)** — A free user with `daily_status.can_review === false`
  navigates to `/learn/daily` → `DailyReviewWalledView` renders, no `<QuizPanel>`
  mount, no card-flip UI, no FSRS scheduler invocation. The `fetchDailyQueue`
  call resolves once and is not retried.
- **AC-2 (regression — under-cap free user)** — Free user with
  `cards_consumed < cards_limit` → existing review UI renders unchanged. `<QuizPanel>`
  mounts; submit path still uses spec #50 wall.
- **AC-3 (defense-in-depth — Pro)** — Pro user at any consumption level
  (BE returns `cards_limit === -1, can_review === true`) → review UI renders.
  Verified via dual-gate: BE-side (`can_review === true`) and FE-side
  (`plan !== 'free'` short-circuits before reading `can_review`).
- **AC-4 (defense-in-depth — admin)** — Admin user (`isAdmin === true`,
  `role === "admin"` BE-side) → review UI renders regardless of plan.
- **AC-5 (analytics — page-load fire)** — When `DailyReviewWalledView`
  mounts, `daily_card_wall_hit` fires exactly once with
  `{ resets_at_hours_from_now: int, surface: "daily_review_page_load" }`.
  Re-render of the same component (e.g. `daily_status` polling refresh —
  out of scope but conceptually possible) does NOT re-fire — `useRef`
  idempotency guard.
- **AC-6 (REGRESSION GUARD — submit-time event preserved)** — Existing
  submit-time wall flow (free user under cap navigates to `/learn/daily`,
  reviews to cap, submits the (cap+1)th card) STILL fires `daily_card_wall_hit`
  with `{ resets_at_hours_from_now, surface: "daily_review_submit" }`.
  Existing `tests/components/QuizPanel.wall.test.tsx` tests remain green
  with the additional `surface` prop assertion.
- **AC-7 (B-057 chrome carve-out applies)** — Walled user clicks "Upgrade to
  Pro" → navigates to `/pricing`. Authed `/pricing` view shows TopNav +
  MobileNav per B-057 (`19326de`). User is not stranded.
- **AC-8 (back-out CTA)** — Walled user clicks "Back to home" → navigates
  to `/home`. No analytics event; no state mutation.
- **AC-9 (countdown formatting)** — `formatResetsAt(resets_at)` renders
  "Resets in Xh Ym" for ≤12h remaining, "Resets at H:MM AM/PM" otherwise.
  Behavior locked by existing `QuizPanel` lift; this AC is a regression pin
  on the lifted util.
- **AC-10 (BE backwards-compat)** — `GET /api/v1/study/daily` response
  shape extension is **purely additive** — old FE clients without a
  `daily_status` consumer continue working. Verified by an explicit unit
  assertion: prior `DailyReviewResponse` fields (`cards`, `total_due`,
  `session_id`, `completed_today`) remain present and unchanged in shape.
- **AC-11 (Redis-outage fail-open)** — `GET /api/v1/study/daily` for a free
  user when `_get_redis()` returns None → `daily_status` returns
  `cards_consumed=0, can_review=true, cards_limit=Settings.free_daily_review_limit,
  resets_at=<next-local-midnight>`. Same fail-open the wall already uses
  (spec #50 §Counter Storage).
- **AC-12 (counter side-effect-free)** — `GET /api/v1/study/daily` for a free
  user does NOT INCR the Redis counter. Verified by snapshotting the
  `daily_cards:{user_id}:{YYYY-MM-DD}` value before and after a queue fetch.

## 6. Test plan

### 6.1 Backend pytest

Extend `hirelens-backend/tests/test_study_api.py` (the existing daily-queue
test file — confirmed by `rg -l "study/daily" hirelens-backend/tests`):

- `test_daily_queue_returns_daily_status_for_free_under_cap` — AC-2 BE-side.
  Free user with `cards_consumed = 0` → `daily_status.can_review === True`,
  `cards_consumed === 0`, `cards_limit === settings.free_daily_review_limit`.
- `test_daily_queue_returns_daily_status_for_free_at_cap` — AC-1 BE-side.
  Pre-seed Redis counter to `cap` for free user → `can_review === False`,
  `cards_consumed === cap`.
- `test_daily_queue_returns_unlimited_sentinel_for_pro` — AC-3 BE-side.
  Pro user → `cards_limit === -1`, `can_review === True`, regardless of any
  Redis state.
- `test_daily_queue_returns_unlimited_sentinel_for_enterprise` — Enterprise
  matches Pro semantics.
- `test_daily_queue_returns_unlimited_sentinel_for_admin` — AC-4 BE-side.
  Admin + plan=free → `cards_limit === -1, can_review === True`.
- `test_daily_queue_resets_at_is_iso8601_future_user_local_midnight` —
  AC-9 BE-side. `resets_at` parses as ISO8601, is in the future, matches
  next user-local midnight per `EmailPreference.timezone`. Use
  `monkeypatch.setattr(study_service, "_utcnow", ...)` to freeze time
  (existing pattern in `tests/test_wall.py`).
- `test_daily_queue_get_does_not_incr_counter` — AC-12. Snapshot Redis
  store before + after `client.get('/api/v1/study/daily')`; assert
  `incr_calls == 0` and the day-key value is unchanged.
- `test_daily_queue_redis_outage_fails_open` — AC-11. Monkeypatch
  `_get_redis()` → None; free user GET → `daily_status.can_review === True`,
  `cards_consumed === 0` (sentinel-failsafe).
- `test_daily_queue_response_shape_backcompat` — AC-10 BE-side. Existing
  fields (`cards`, `total_due`, `session_id`, `completed_today`) unchanged
  in shape; `daily_status` is additive.

Estimated BE delta: **+9 tests** in `test_study_api.py`.

### 6.2 Frontend Vitest

New file `hirelens-frontend/tests/pages/DailyReview.preflight.test.tsx`:

- `test_walled_free_user_sees_upsell_not_review_ui` — AC-1.
- `test_under_cap_free_user_sees_review_ui` — AC-2.
- `test_pro_user_always_sees_review_ui` — AC-3.
- `test_admin_user_always_sees_review_ui` — AC-4.
- `test_daily_card_wall_hit_fires_once_on_walled_mount` — AC-5; assert
  `posthog.capture` called once with
  `{ resets_at_hours_from_now: int, surface: 'daily_review_page_load' }`.
- `test_upgrade_cta_navigates_to_pricing` — AC-7 FE-side; `useNavigate`
  spy.
- `test_back_to_home_cta_navigates_to_home` — AC-8.
- `test_resets_at_under_12h_renders_relative` — AC-9.
- `test_resets_at_over_12h_renders_absolute` — AC-9.

Estimated FE delta: **+9 tests** in new
`tests/pages/DailyReview.preflight.test.tsx`.

### 6.3 Regression set (must stay green)

- `hirelens-backend/tests/test_wall.py` — the 11 spec #50 wall tests
  (parameterized via `CAP = get_settings().free_daily_review_limit`).
- `hirelens-backend/tests/test_free_tier_limit_config.py` — Slice A's 3
  env-override tests.
- `hirelens-frontend/tests/components/QuizPanel.wall.test.tsx` — the 5
  spec #50 modal-render tests. AC-6 mandates these stay green; the impl
  slice MUST add the `surface: "daily_review_submit"` prop assertion to
  the existing `daily_card_wall_hit` test without breaking the others.

## 7. R16 audit checklist (for impl slice's Step 1)

Run these `rg` calls and surface findings before editing:

- `rg "fetchDailyQueue" hirelens-frontend/src` — expected hits:
  - `services/api.ts:305` (declaration)
  - `pages/DailyReview.tsx:206` (consumer)
  - `components/home/widgets/TodaysReviewWidget.tsx:20` (second consumer
    — see LD-A note below)
- `rg "study/daily" hirelens-backend/app/api` — expected single route
  handler at `api/v1/routes/study.py:52`.
- `rg "DailyReviewResponse|DailyQueueResponse|daily_queue_response"
  hirelens-{backend,frontend}/src` — expected hits:
  - BE: `app/schemas/study.py:30` (declaration), `app/api/v1/routes/study.py`
    (consumer), `app/services/study_service.py` (consumer).
  - FE: `src/types/index.ts:195` (FE alias), `src/services/api.ts`
    (consumer).
- `rg "formatResetsAt|hoursUntil" hirelens-frontend/src` — expected single
  hit at `components/study/QuizPanel.tsx:111-129` (private declarations).
  Impl-slice must lift to shared util per §3.1.
- `rg "_check_daily_wall|_DAILY_CARD_KEY_TTL_SECONDS" hirelens-backend/app`
  — expected hits in `services/study_service.py` only (the helper is
  module-private).

If any of these surface unexpected callers (third consumer of
`fetchDailyQueue`, additional `formatResetsAt` private duplicates
elsewhere, etc.), STOP and flag — that's net-new scope per R19.

## 8. Out of scope (explicit)

- Any change to `_check_daily_wall` submit-time logic. Pre-flight is
  read-side only.
- CardViewer (`/learn/card/:id`) pre-flight gate. LD-001 + LD-C scope:
  card view is browse, not review consumption — no pre-flight by design.
- MissionMode (`/learn/mission`) pre-flight gate. Page is Pro-only at
  the route level; free users can't reach it.
- Lifting duplicated `chromeless-paths` sets between `AppShell` and
  `MobileNav` — tracked at B-058 (filed `80f84e6`).
- Changes to `PaywallModal` / `WallInlineNudge` components. The pre-flight
  view is a distinct surface, not a modal.
- Streak-vs-wall midnight inconsistency. Existing future-decision item
  flagged in spec #50 §Timezone Handling.
- `TodaysReviewWidget` consumption of the new `daily_status` field.
  Tracked at B-020 (already in BACKLOG); the additive payload makes B-020
  cheaper but is not closed by this spec.
- Modal-on-mount or redirect-to-home alternatives. LD-B locked the
  full-page upsell shape.

## 9. Locked Decisions cross-reference

- **LD-001** (free-tier daily-review consumes the daily-card budget; α)
  — unchanged. This spec makes LD-001's state visible at page-load
  rather than submit-time only.
- **Spec #50** (wall mechanic — submit-time 402) — unchanged. Submit-time
  wall remains canonical for browse + mission paths and for the under-cap
  → walled transition mid-session.
- **Spec #56 / Spec #60 / B-045** (`/prep/analyze` lifetime-scan pre-flight)
  — named precedent. This spec mirrors spec #60's render shape, the
  3-clause plan gate, and the `paywall_hit { surface: 'analyze_page_load' }`
  → `daily_card_wall_hit { surface: 'daily_review_page_load' }` analytics
  pattern.
- **B-057** (`/pricing` chrome carve-out for authed users, `19326de`) —
  hard dependency for AC-7. If B-057 is ever reverted, this spec's
  "Upgrade to Pro" CTA strands the user.
- **LD-001 amendment 2026-04-26** (cap 15 → 10) — unchanged; the
  pre-flight gate reads `Settings.free_daily_review_limit` and follows
  the active cap automatically. No literal `10` (or `15`) appears in
  spec body.
- **LD-A (this slice — endpoint reuse)** — extend
  `GET /api/v1/study/daily` response. Rationale **revised post-R19**:
  `fetchDailyQueue` already has TWO consumers (`DailyReview.tsx`,
  `TodaysReviewWidget.tsx`), so adding `daily_status` to the response
  serves both for free — `TodaysReviewWidget` can use the field later
  (B-020 follow-up to surface walled state on the home dashboard) without
  a second endpoint round-trip. A standalone `/study/daily-status`
  endpoint would force two callers to hit two endpoints. The chat-Claude
  prompt's YAGNI counter ("TodaysReviewWidget reads gamification, not
  wall state — not a second consumer") was built on a false premise
  surfaced by R16 audit; conclusion still holds, rationale rewritten.
- **LD-B (this slice — full-page upsell, not modal-on-mount, not
  redirect)** — locked. Mirrors spec #60 / `Analyze.tsx`. Modal-on-mount
  has the close-modal-stare-at-broken-UI failure mode; redirect punishes
  deliberate navigation.
- **LD-C (this slice — DailyReview.tsx scope only)** — locked. CardViewer
  is browse, MissionMode is Pro-only.

## 10. BACKLOG row

Filed in this slice as a new 🔴 row (R17 verified — B-058 highest in-use,
B-059 free):

```
| B-059 | study | Daily-review pre-flight gate on /learn/daily — UX parity with Analyze | P1 | 🔴 | docs/specs/phase-5/63-daily-review-preflight-gate.md | (filed by 2026-04-26 P5-S63 spec slice) | …
```

See `BACKLOG.md` for the full row text. Closes on impl-merge per R15.

## 11. Implementation slice plan (forward pointer, not in this slice's scope)

For the impl slice (P5-S63-impl) at execution time:

1. R16 audit per §7 of this spec.
2. BE: extend `DailyStatus` schema + handler. Update
   `app/services/study_service.py::get_daily_review` to populate the
   field. Side-effect-free Redis read.
3. BE tests per §6.1.
4. FE: lift `formatResetsAt` + `hoursUntil` per §3.1. Update
   `QuizPanel.tsx` import; existing `tests/components/QuizPanel.wall.test.tsx`
   stays green (refactor-only).
5. FE: extend `DailyQueueResponse` interface (`src/types/index.ts:195`)
   with `daily_status`.
6. FE: build `DailyReviewWalledView.tsx`; wire 3-clause gate in
   `DailyReview.tsx`.
7. FE tests per §6.2.
8. Update `.agent/skills/analytics.md` `daily_card_wall_hit` row with
   `surface` enum.
9. Update `QuizPanel.tsx` submit-time `daily_card_wall_hit` capture to
   add `surface: "daily_review_submit"` (AC-6).
10. R15 close: B-059 🔴 → ✅ in same commit.

Estimated impl-slice cost: BE +9 / FE +9 (new file) + small refactor in
2 FE files + 1 BE service file. Two-commit pattern (impl + SHA backfill).
