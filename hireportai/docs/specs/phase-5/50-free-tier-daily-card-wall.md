---
slice: P5-S22-WALL-a (spec) + P5-S22-WALL-b (impl)
base_sha: 72dfab4
drafted: 2026-04-19
locked_decisions: LD-001
unblocks: P5-S22b (spec #22), P5-S26b (spec #42 — paywall dismissal)
---

# SPEC: Free-Tier Daily-Card Review Wall

## Status: Draft

> **Amended 2026-04-26 (Slice B — LD-001 cap tightening):** Cap value `15 → 10` cards/day. All AC shapes, payload fields, behavior, edge cases UNCHANGED — only the integer literal moves. Test count unchanged (the AC tests parameterize against the active limit, not the literal 15). Cross-ref: SESSION-STATE LD-001 amendment 2026-04-26. Spec body below has been updated in-place; historical citations to "15-card budget" in earlier-authored spec #22 / spec #56 / E2E status docs are intentionally NOT touched in Slice B (they describe history at their authoring date) — they will read as stale until those specs are independently amended.

## Problem

LD-001 (2026-04-19, `hireportai/SESSION-STATE.md`; amended 2026-04-26, cap tightened 15 → 10) locked the policy that "daily review consumes the free-tier daily-card budget" (α). The codebase enforces **nothing** of the sort today:

- `app/services/usage_service.py::PLAN_LIMITS` has no `daily_review` / `card_view` entry — the quota dict tracks only `analyze`, `rewrite`, `cover_letter`, `interview_prep`, `resume_optimize`.
- `app/services/study_service.py::review_card` (line 249-) gates free users only on `Category.source == "foundation"` (line 284). No per-user card counter is incremented.
- `app/api/v1/routes/study.py::submit_review` translates `CardForbiddenError` → 403, `CardNotFoundError` → 404. There is no 402 / payment-required branch.
- `hirelens-frontend/src/components/PaywallModal.tsx` defines a `daily_review` trigger in its `PaywallTrigger` union type (line 25) with ready-to-use copy ("Daily Review is a Pro feature"), but grep across `src/` finds no component that passes `trigger="daily_review"`. Dead scaffold awaiting a caller.

This gap blocks two downstream slices:

- **P5-S22b** (plan-aware Missing Skills CTA) — its free-user CTA routes users into `/learn` with copy "Study these cards — free preview". The "preview" framing presumes an existing wall they will eventually hit. Without the wall, free users get unlimited reviews via the Missing-Skills path, contradicting LD-001 and the CTA's own semantics.
- **P5-S26b** (paywall dismissal + win-back) — its §AC-1 depends on a free user "hitting the daily-card wall"; dismissal logic needs a real paywall to dismiss.

Close the gap: wire the counter, raise the 402, and hook the existing `daily_review` PaywallModal trigger.

### Interpretation note (LD-001 wording)

LD-001 contains two phrasings whose strict readings are in tension:

- "The free-tier daily-card/day budget is consumed by the daily review flow" → suggests **per-day** cap (resets daily).
- "Free users complete N days of active daily review (5 cards/day × N) before hitting the paywall wall" → mathematically only holds if the cap is **lifetime total** (5/day × N days before walled).

This slice's authoring prompt (P5-S22-WALL-a) resolves the ambiguity explicitly toward the **per-day, resets at local midnight** reading. All ACs below follow that reading.

Drift flag implication — `.agent/skills/payments.md:78` also reads "Foundation cards: **15 lifetime**", which aligns with LD-001's second phrasing but contradicts this spec's per-day reading. That skill-doc line will need amendment in the P5-S22-WALL-b commit (or a follow-up docs-sync slice) to say "10 per day (user-local midnight reset)". This amendment is **not** in scope for P5-S22-WALL-a (spec only). Logged as a spec-author observation; a Drift flag can be appended by the impl slice when it lands.

**Resolution:** Ambiguity resolved in the follow-up amendment commit. LD-001 now unambiguously states per-day budget with user-local-midnight reset. `.agent/skills/payments.md` line updated in the same commit. See Ops Log entry dated 2026-04-19.

## Solution

Per-user per-day counter that increments on FSRS review submit. When the counter reaches the active free-tier cap (`Settings.free_daily_review_limit`, default 10 per LD-001 amendment 2026-04-26) for a free user on their local calendar day, the next submit returns HTTP 402 with a structured paywall payload. Counter resets at the user's local midnight. Pro / Enterprise / admin bypass the check entirely.

Storage: Redis `INCR` with a key scoped by `user_id + YYYY-MM-DD` (date in user's timezone). Reuses the `_get_redis()` fail-open pattern already live in `app/services/home_state_service.py` and `app/services/geo_pricing_service.py`.

Enforcement point: inside `study_service.review_card`, immediately **before** the FSRS advance / DB flush so that a walled review does **not** mutate `card_progress`. The existing plan-gate check at line 284 (`is_free and category.source != "foundation"`) runs first; the wall check runs next; FSRS advance runs after both pass.

Exception type: a new `DailyReviewLimitError` in `study_service.py`, parallel to the existing `CardForbiddenError` / `CardNotFoundError`. The route maps it to a 402.

Convention note: the existing free-tier-cap precedent (`.agent/skills/payments.md:80-81`) returns 403 for `check_and_increment` breaches — the interview-prep monthly cap, for example. This spec uses **402** because HTTP 402 is semantically correct for "payment would resolve this response" (Mozilla MDN §402) and because the frontend needs a dispatch code that does not collide with 403's existing "forbidden category" semantics on the same endpoint. P5-S22-WALL-b SHOULD consider whether `check_and_increment` call-sites should migrate from 403 to 402 in a follow-up for consistency; that migration is **explicitly out of scope here**.

## Acceptance Criteria

- **AC-1** — A free-plan user submitting their 1st through 10th daily review within a single user-local calendar day receives `200 OK` with the existing `ReviewResponse` payload. No behavior change for reviews 1–10. Verified by pytest that seeds 10 submissions and asserts each returns 200.
- **AC-2** — A free-plan user submitting their 11th daily review within the same user-local calendar day receives `402 Payment Required` with JSON body:
  ```json
  {
    "error": "free_tier_limit",
    "trigger": "daily_review",
    "cards_consumed": 10,
    "cards_limit": 10,
    "resets_at": "<ISO 8601 timestamp, user-local midnight + 1 day, with tz offset>"
  }
  ```
  The FSRS progress row for that card is NOT mutated (the review did not happen). Verified by pytest: seed 10 submissions; submit the 11th; assert 402 + exact payload shape + `card_progress` row unchanged.
- **AC-3** — Pro and Enterprise users never hit the 402 path regardless of count. Per §Counter Scope below (Option 2), the counter does **not** increment for Pro / Enterprise — the wall check is skipped entirely when `_is_free(user) is False`. Verified by pytest: submit 20 Pro-user reviews in one day, assert all 200.
- **AC-4** — Counter resets at the user's local midnight, resolved from `EmailPreference.timezone`. Users without an `EmailPreference` row or with `timezone IS NULL` default to UTC. Verified by pytest: freeze `datetime.now(timezone.utc)` to 23:30 UTC, set user timezone to `America/Los_Angeles` (UTC-8, so it's still 15:30 local), seed up-to-cap reviews, attempt the next → 402. Advance frozen time to 00:30 UTC (now 16:30 local, same calendar day) → still 402. Advance to 08:01 UTC (00:01 local next day) → 200.
- **AC-5** — Mission Mode reviews do not consume this counter. Rationale: Mission Mode is already Pro-gated (`/learn/mission` lazy-loads `MissionMode` which is Pro-only per `.agent/skills/mission-mode.md`). Since only Pros reach it, and Pros skip the wall per AC-3, this is a correctness property, not new logic. Verified by inspection: the Mission-submit code path (if distinct from `/api/v1/study/review`) does not invoke the wall-check helper.
- **AC-6** — Streak-freeze tokens (`GamificationStats.freezes_available`) have no interaction with the wall. Freezes affect streak continuity only. Verified by pytest negative assertion: walled-16th submit does not consume a freeze, does not change `freezes_available`, does not affect `current_streak`.
- **AC-7** — `PaywallModal` renders on the 402 response with `trigger="daily_review"`, displaying a human-readable `resets_at` time ("resets in 4h 17m" / "resets at 12:00 AM") and the existing "Upgrade to Pro" CTA. The existing `PaywallTrigger` union already permits `'daily_review'`; no new trigger is added. Verified by Vitest test that mocks a 402 response and asserts modal open + copy + CTA.
- **AC-8** — On Pro upgrade via Stripe webhook mid-wall, the counter is **not** reset — it's simply ignored thereafter because `_is_free(user)` returns False after the subscription activates. Verified by pytest: user hits 402 at 16th review; simulate `payment_service.handle_webhook` upgrading the subscription; 17th submit returns 200 without Redis key mutation.
- **AC-9** — Admin users (`User.role == "admin"`) bypass the wall regardless of `_is_free(user)`'s return value. Rationale: admins need unobstructed test traversal. The bypass check is an early-exit in the wall-check helper. Verified by pytest: admin + plan=free + 20 submissions → all 200.
- **AC-10** — PostHog analytics:
  - `daily_card_submit` fires on every submit attempt — including walled — with props `{ plan: "free" | "pro" | "enterprise", count_after: int, was_walled: bool }`. For walled submits, `count_after` equals the active cap (`Settings.free_daily_review_limit`, default 10) and `was_walled: true`. Fires from the **backend** (consistent with `card_reviewed` from `.agent/skills/study-engine.md`, also backend-fired).
  - `daily_card_wall_hit` fires only on 402 response, from the **frontend** when `PaywallModal` opens with `trigger="daily_review"` (consistent with the existing `paywall_hit` convention in `PaywallModal.tsx`, which also fires FE-side). Props: `{ resets_at_hours_from_now: int }` (integer hours, rounded toward zero).
  - Both events MUST be added to `.agent/skills/analytics.md` in the impl commit per the P5-S21b convention (catalog updated alongside event introduction).

## Counter Storage

**Redis `INCR` keyed by user + user-local date.**

- Key format: `daily_cards:{user_id}:{YYYY-MM-DD}` where `YYYY-MM-DD` is the user's **local** calendar date at the moment the review is submitted (not UTC).
- TTL: 48 hours, set on first `INCR` per key. 48h is a safety floor — the key's date rolls forward at user-local midnight, so a fresh key is allocated daily and the 48h TTL on the old key naturally ages it out. TTL does NOT need to align with the day boundary; it only needs to be longer than the longest plausible timezone swing (~14 hours between UTC-12 and UTC+14) plus headroom.
- Value: integer. `INCR` is atomic.
- Read for AC check: `GET` key, parse int, compare to the active cap (`Settings.free_daily_review_limit`, default 10). `INCR` returns the new value, so the service can read the post-increment count in a single round-trip when incrementing.

### Rationale for Redis over DB

- Increment is on the hot path of every review submit. Redis `INCR` is ~10× faster than a DB `UPDATE ... RETURNING` under async SQLAlchemy, and it atomically handles the concurrent-submit race (see §Edge Cases).
- Analytics is handled by PostHog (via the `daily_card_submit` / `daily_card_wall_hit` events); we do not need to query historical counter values from the application DB.
- The reset-at-midnight behavior is implicit in the date-keyed key — no cron job, no nightly reset. A fresh calendar day gets a fresh key; the old key ages out naturally.

### Fail-open on Redis outage

If `_get_redis()` returns `None` (same convention as `home_state_service.py:61-76` and `geo_pricing_service.py:35-`), the wall-check helper logs a warning at `logger.warning` level (not error) and returns "allowed" — the review proceeds. Rationale: a Redis outage during production traffic should degrade to the pre-wall behavior (unlimited free reviews) rather than fail-closed and 402-spam every authenticated free user. The PostHog event `daily_card_submit` still fires with `was_walled: false` and a new prop `counter_unavailable: true` so the outage is visible in analytics.

## Counter Scope

**Option 2 — counter increments ONLY for free users; Pro / Enterprise skip the Redis call entirely.**

Rejected Option 1 — increment for all plans, 402 only for free. The analytics benefit (seeing "how many Pros would have hit the wall") is already available via PostHog's `card_reviewed` event (which fires for every plan per `.agent/skills/study-engine.md:43`); duplicating it in Redis is write-amplification without read benefit. Option 2 keeps the hot path free of Redis IO for paying users.

Implementation consequence: the wall-check helper's first branch is `if not _is_free(user): return allowed=True, count=None, ...`. Redis is only consulted for free users.

## Timezone Handling

User's local midnight is the day-boundary. Resolution order:

1. Read `EmailPreference.timezone` for the user. If set (non-null) → use that IANA tz.
2. If no `EmailPreference` row or `timezone IS NULL` → default to `UTC`.
3. Do **not** add a timezone field on `User` in this slice. `EmailPreference.timezone` is the authoritative user-timezone store (established by spec #16 email-preferences).

Helper: the impl slice adds `get_user_timezone(user_id: str, db: AsyncSession) -> ZoneInfo` in `app/core/timezone.py` (new file) or `app/utils/` — P5-S22-WALL-b's Step 1 audit picks the canonical location. No such helper exists today (grep of `app/` returned zero `ZoneInfo` imports and zero `pytz` imports; the codebase is UTC-only today).

### Known inconsistency flagged for follow-up

`.agent/skills/gamification.md:14` specifies "Streak resets to 0 if a day is missed (**midnight UTC**)". Streak boundaries are UTC; this spec's wall boundaries are user-local. For a user in UTC-8:

- 16:00 UTC = 08:00 local → mid-morning local. Streak-day is UTC-indexed and ticks over at midnight UTC = 16:00 local.
- The wall-day is local-indexed and ticks over at midnight local = 08:00 UTC.

Result: a user in UTC-8 whose free budget resets at 08:00 UTC sees their streak continue running on the same UTC-date until 24:00 UTC, which is 16:00 local. The two clocks run on different midnights for 8 hours of the day. This is a product inconsistency but **not a blocker** — it only manifests if a user studies near either boundary. Resolution: either align both to user-local midnight (preferred; gamification would migrate), or align both to UTC (simpler). Out of scope for this spec. Flagged for a product decision and potential follow-up Locked Decision. P5-S22-WALL-b's Step 1 audit should surface the inconsistency in its output so product can decide before ship.

## API Contract

No new endpoints. The existing `POST /api/v1/study/review` endpoint (`app/api/v1/routes/study.py:76-117`) gains a third error branch:

```python
except study_service.CardNotFoundError as exc:          # existing → 404
    raise HTTPException(status_code=404, detail=str(exc))
except study_service.CardForbiddenError as exc:         # existing → 403
    raise HTTPException(status_code=403, detail=str(exc))
except study_service.DailyReviewLimitError as exc:      # new → 402
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail=exc.payload,  # dict per AC-2
    )
```

`DailyReviewLimitError` carries a `.payload` attribute holding the AC-2 JSON shape. FastAPI serializes `HTTPException.detail` when it's a dict — no Pydantic schema change needed. If the impl slice prefers a typed response model, adding a `DailyReviewLimitResponse` to `app/schemas/study.py` is acceptable but not required.

### Backwards compatibility

- Pro users — zero change. All existing Pro-user integration tests remain green.
- Free users submitting ≤cap reviews per day — zero change. All existing free-user integration tests submit ≤1 review per user-day (audit of `tests/test_study_service.py` and `tests/test_study_api.py` confirms: `test_review_card_returns_fsrs_state`, `test_review_advances_schedule`, `test_first_review_creates_progress_row`, `test_review_nonexistent_card_returns_404`, `test_review_invalid_rating_returns_422`, `test_free_user_review_premium_card_returns_403`, `test_review_card_awards_xp` all submit ≤1 review). No test requires adjustment to remain green under the wall.
- Free users submitting >cap reviews per day — the (cap+1)th and beyond will 402 post-ship. Any external client hammering the endpoint as a benchmark will break; no such client exists.

## Data Model Changes

None. No SQL migration. Redis schema documented above.

## Plan Detection

Reuse existing `_is_free(user: User) -> bool` in `app/api/v1/routes/study.py:34-45`. That helper already checks `user.subscription.status == "active"` and `plan == "free"`. The wall-check helper consumes it.

Admin bypass (AC-9): check `user.role == "admin"` before `_is_free`. If admin, return allowed regardless.

## UI/UX

- 402 response from `POST /api/v1/study/review` is caught by the existing review-submit handler in `hirelens-frontend/src/pages/DailyReview.tsx` (or wherever the submit call lives per P5-S22-WALL-b's Step 1 audit — likely `useStudyDashboard` or a sibling hook).
- Caught 402 opens `PaywallModal` with `trigger="daily_review"`. The existing modal copy ("Daily Review is a Pro feature" / "Daily Review uses FSRS to schedule the exact cards you need to revisit. Pro unlocks the full queue.") is re-used — no copy change in this slice. A follow-up slice may refine the copy to mention the daily-card budget and the reset time; out of scope here.
- Modal MUST surface `resets_at` in a human-readable format. Two options, impl picks:
  - "Resets in 4h 17m" (relative).
  - "Resets at 12:00 AM" (absolute, user-local).
  Recommendation: relative for ≤12h remaining, absolute otherwise. Uses existing date-fns helpers (the codebase already has `date-fns` per `package.json`).
- CTAs: existing "Upgrade to Pro" (drives `createCheckoutSession`) + a new secondary "Come back tomorrow" button that calls `onClose`. The secondary CTA emits `daily_card_wall_hit` with a follow-up `dismiss_reason: "come_back_tomorrow"` prop — **only if** the P5-S26b spec #42 flow is already live at impl time; otherwise the secondary CTA is plain close and the dismissal-analytics half is a P5-S26b concern.
- Dismissal behavior (how often the modal re-appears after close) is owned by P5-S26b. This spec does NOT define it. If P5-S26b has not shipped by the time P5-S22-WALL-b goes out, the modal re-appears on every walled submit (current `PaywallModal` behavior).

Design-system tokens: no new tokens expected. The existing `PaywallModal` already uses design tokens per Rule 12.

## Analytics Events

Two new events; both must land in `.agent/skills/analytics.md` in the P5-S22-WALL-b commit (same pattern as P5-S21b's `results_tooltip_opened`).

- **`daily_card_submit`** — backend-fired on every review submit attempt.
  Props: `{ plan: "free" | "pro" | "enterprise", count_after: int | null, was_walled: bool, counter_unavailable: bool }`.
  - `count_after` is `null` for non-free (Option 2 — no Redis interaction); integer for free.
  - `counter_unavailable: true` is the fail-open sentinel (Redis down).
- **`daily_card_wall_hit`** — frontend-fired on `PaywallModal` open with `trigger="daily_review"`.
  Props: `{ resets_at_hours_from_now: int }`.
  - If P5-S26b dismissal analytics has shipped, add `dismiss_reason` on modal close via the existing dismissal event (not this one).

The existing `card_reviewed` event (per `.agent/skills/study-engine.md:43`) fires from the service on successful review — keep as-is. A 402-walled submit does NOT fire `card_reviewed` (no review happened).

## Edge Cases

- **User changes timezone mid-day**: `EmailPreference.timezone` updates → next submit computes a new local date key → user could theoretically regain budget by jumping to a later timezone. Accepted — attack surface is minimal; closing it adds state complexity for a vanishingly small exploit population.
- **Admin bypass** (AC-9): `user.role == "admin"` early-exits before the Redis call. Admin + free plan is valid (dev / test accounts).
- **Concurrent submits at count=cap-1 and count=cap**: Redis `INCR` is atomic. Two concurrent callers see post-values `cap` and `cap+1` respectively. The `cap`-call succeeds; the `cap+1`-call 402s. Correct by design.
- **Redis outage**: fail-open per §Counter Storage. `daily_card_submit` fires with `counter_unavailable: true`. Monitor via PostHog; if seen, page ops.
- **User upgrades mid-wall** (AC-8): next submit's `_is_free(user)` returns False → wall-check early-exits → review proceeds. Redis key is orphaned but ages out via its 48h TTL.
- **Free user on day 1 at 14:00 UTC submits up-to-cap reviews, at 18:00 UTC (same local day) attempts the next**: walled correctly. At 00:01 next local day → new key, `INCR` returns 1, allowed.
- **Rating submit of a card the user has already reviewed today**: still counts. The wall is a **submit counter**, not a **unique-card counter**. Rationale: FSRS re-reviews (due-again cards) are reviews for budget purposes; undercounting them would let a user loop "Again" on the same card for free unlimited review.
- **Card FSRS state mutated by the service BEFORE the wall raises**: do NOT. The wall check MUST run before any FSRS / `card_progress` mutation. P5-S22-WALL-b's test suite explicitly asserts the 402-path leaves `card_progress` untouched (AC-2).
- **User in a locale whose timezone is not in the IANA tzdb** (or malformed `EmailPreference.timezone` string): `ZoneInfo(tz_string)` raises `ZoneInfoNotFoundError`. Catch and default to UTC; log a warning with the bad tz string so we can clean it up.

## Dependencies

- **LD-001** (SESSION-STATE.md 2026-04-19) — this spec is the implementation contract for LD-001. If LD-001 is ever reversed, this spec's entire premise dissolves.
- **Existing `PaywallModal.tsx` `daily_review` trigger scaffold** — union-type value + HEADLINE + SUBLINE are live; this spec wires the consumer. No modal refactor needed.
- **Existing `EmailPreference.timezone` field** — reused. If this field is ever dropped or migrated, the wall's timezone resolution breaks.
- **Existing `_is_free(user)` helper** in `app/api/v1/routes/study.py:34-45` — reused. If plan-resolution logic migrates to a shared helper (e.g., `app/core/deps.py`), the wall-check follows.
- **Existing Redis infrastructure** (`settings.redis_url`, `_get_redis()` fail-open pattern) — reused from `home_state_service.py` / `geo_pricing_service.py`.
- **Unblocks P5-S22b** (spec #22, AC-4 / AC-5 — the free-user CTA's "free preview" semantics require the wall to exist).
- **Unblocks P5-S26b** (spec #42, AC-1 — paywall dismissal needs a real paywall to dismiss).

## Test Plan

### Backend pytest (to be written in P5-S22-WALL-b BEFORE implementation per Rule 1)

- `test_free_user_review_up_to_cap_succeed` — AC-1. Seeds `cap` foundation-card submissions; asserts each returns 200 + `card_progress` row updates. `cap` reads `Settings.free_daily_review_limit` so the test follows the LD-001 default (currently 10 after the 2026-04-26 amendment).
- `test_first_review_over_cap_returns_402_with_correct_payload` — AC-2. Seeds `cap`; submits the next; asserts 402 + exact JSON shape + `card_progress` row unchanged.
- `test_pro_user_never_hits_wall` — AC-3. Submits 20 Pro-user reviews (above any plausible cap); asserts all 200; asserts Redis key absent (Option 2 → no increment for Pros).
- `test_admin_bypasses_wall_regardless_of_plan` — AC-9. User with `role="admin"` and `plan="free"`; 20 submissions; all 200.
- `test_counter_resets_at_user_local_midnight_tz_la` — AC-4. `freezegun` + user tz=`America/Los_Angeles`; `cap` submissions at 15:30 local; attempt the next at 16:30 local (same day); still 402; advance to 00:01 local next day; 200.
- `test_counter_defaults_to_utc_when_user_has_no_timezone` — AC-4 default path. User without `EmailPreference` row; wall boundary = UTC midnight.
- `test_redis_outage_fails_open` — §Counter Storage fail-open. Monkeypatch `_get_redis()` → None; 20 free-user submissions; all 200; `daily_card_submit` events emit `counter_unavailable: true`.
- `test_concurrent_submits_at_boundary_increment_atomically` — §Edge Cases. Two `asyncio.gather`'d submits with the counter pre-seeded to `cap-1`; one returns post=`cap` and succeeds, the other returns post=`cap+1` and 402s. Exact assertion: exactly one wall raise across the pair.
- `test_pro_upgrade_mid_wall_bypasses_immediately` — AC-8. User hits 402 at the (cap+1)th submit; simulate Stripe webhook upgrading to Pro; the next submit returns 200; Redis key untouched.
- `test_posthog_daily_card_submit_fires_with_correct_props` — AC-10 (BE side). Stub PostHog client; submit one free review; assert event name + props.
- `test_walled_submit_does_not_consume_streak_freeze` — AC-6. Set `freezes_available=3`; hit wall on the (cap+1)th; assert `freezes_available` unchanged.

Expected backend test count delta at P5-S22-WALL-b ship: **+11** (248 → 259 non-integration).

### Frontend Vitest

- `test_paywall_modal_renders_on_402_with_daily_review_trigger` — AC-7. Mock submit call to return 402 with AC-2 payload; assert `PaywallModal` opens with `trigger="daily_review"`.
- `test_modal_shows_resets_at_time_in_relative_format` — UI/UX helper. `resets_at` 4h from now → "Resets in 4h".
- `test_modal_shows_resets_at_time_in_absolute_format_for_long_waits` — UI/UX helper. `resets_at` 20h from now → "Resets at 12:00 AM".
- `test_upgrade_cta_routes_to_existing_stripe_flow` — CTA smoke. Assert click invokes `createCheckoutSession`.
- `test_daily_card_wall_hit_fires_on_modal_open` — AC-10 (FE side). Assert PostHog `capture` called with event name + `resets_at_hours_from_now`.

Expected frontend test count delta at P5-S22-WALL-b ship: **+5** (142 → 147).

### Manual post-deploy

- **Free user (Pro needed as contrast)**: log in as a test free user with `EmailPreference.timezone = "Asia/Kolkata"` (IST, UTC+5:30). Submit up-to-cap (10) foundation-card reviews. Attempt the next — see `PaywallModal` with `daily_review` trigger and a sensible "resets in Xh" or "resets at 12:00 AM" string. Wait past local midnight (or advance the test user's timezone), submit again, succeed.
- **Pro user**: submit 20+ reviews in a day, never see the modal. Verify `PaywallModal` never opens.
- **Admin user**: same as Pro.
- **Redis outage simulation** (staging only): kill Redis; submit 20 free-user reviews; all succeed; PostHog shows `daily_card_submit` events with `counter_unavailable: true`.

## Out of Scope / Follow-ups

- **Proactive counter display** (e.g., "8 of 10 reviewed today" banner on `/learn/daily`) — adds design surface; ship only if PostHog data shows the wall-hit rate is high and users report surprise.
- **Streak-freeze "buy-back a review" mechanic** — speculative feature; not planned.
- **Per-category wall limits** — current design is flat cap/day across all foundation cards (see `Settings.free_daily_review_limit`). Premium-category access remains gated by `Category.source` (existing 403 path, untouched).
- **Redis counter persistence for historical analytics** — PostHog handles analytics; don't duplicate. The 48h TTL is intentional — the key is transient session state, not a log.
- **Grace period on first-day-of-wall** (e.g., warn at 8, wall at 10) — simpler to ship without; revisit if wall-hit UX testing shows friction.
- **Migrating `check_and_increment` call-sites from 403 → 402** for free-tier-cap consistency — separate cleanup slice; this spec explicitly uses 402 for the wall while leaving other caps at 403 for now.
- **403→402 migration for the existing interview-prep monthly cap** — tracked as future hygiene; not in this slice, not in P5-S22-WALL-b.
- **Streak-vs-wall midnight alignment** — flagged in §Timezone Handling as a product inconsistency. Needs a Locked Decision (unify both to user-local midnight, or unify both to UTC). Not blocking P5-S22-WALL-b ship.
- **`.agent/skills/payments.md:78` "Foundation cards: 15 **lifetime**" amendment** — needs update to "10 per day (user-local midnight reset)" per this spec's Interpretation note + LD-001 amendment 2026-04-26. Include in P5-S22-WALL-b commit or a follow-up docs-sync slice.
- **`.agent/skills/study-engine.md` Daily-5 line update** — already flagged in the existing 2026-04-18 Locked Decision §1B implementation note ("Update study-engine.md skill: change 'Daily 5 = ... LIMIT 5' line to reflect 20-cap"). Orthogonal to this spec; bundled cleanup candidate if P5-S22-WALL-b touches that skill file anyway.
