# SPEC: Admin Analytics Dashboard

## Status: Draft

> Supersedes `docs/specs/phase-5/01-admin-analytics-early-draft.md` (empty
> template; erroneously marked Done — flagged as drift in `SESSION-STATE.md`
> and should be deleted in a subsequent spec-hygiene slice).

## Problem

Admins currently have no in-app view of how the product is performing. To
answer "how are we doing on conversion?", "which categories are dragging
retention?", "is the LLM bill trending up?", or "what are users asking for
that we don't have?", someone has to drop into PostHog, Stripe, and the
Postgres console, then paste results into a Slack thread. This is slow,
unshared, and nobody does it on a regular cadence — so product decisions
lag reality by weeks.

Three specific blockers today:
1. **No OKR visibility** — the PRD §1.4 OKRs (registered users, paying Pro,
   DAU/MAU, streak, ATS→Pro, churn) live only in the doc. Nobody can tell
   at a glance whether we are on, off, or ahead of target.
2. **No cost visibility** — LLM spend (Gemini, OpenAI fallback) is invisible
   until a bill arrives. A runaway prompt or a scraper hammering
   `/admin/cards/generate` would not be noticed until month-end.
3. **No signal loop** — `card_feedback_submitted` comments, NPS, and paywall
   dismissals are collected but never summarized. Enhancement requests drown
   in the raw event stream.

## Solution

A single admin-only dashboard at `/admin/analytics` surfacing five sections,
each section backed by a dedicated `GET /api/v1/admin/analytics/<section>`
endpoint. The backend aggregates from three sources:

- **Postgres** — owned tables (users, subscriptions, missions, card_feedback,
  usage_log, paywall_dismissal, stripe_event, registration_log).
- **PostHog Query API** — for event-based funnels and cohort retention.
- **LLM (fast tier)** — for clustering free-text comments into themes
  (section 5 only; cached for 24h).

All heavy aggregations are cached in Redis for 5 minutes keyed by
`(admin_id, section, date_range)` so a curious admin refreshing the page
does not slam the DB. The LLM-backed "feedback themes" section caches for
24h because clustering is expensive and the underlying signal moves slowly.

The dashboard is additive — it introduces no new user-facing behavior and
no changes to non-admin endpoints. It inherits all access control from the
existing `require_admin` dependency (see spec
`phase-0/03-user-role-admin.md`) and adds an **audit log** for every admin
analytics read (recommended precondition, see §Admin Access & Audit).

---

## Acceptance Criteria

- [ ] AC-1: **Route & access** — `GET /api/v1/admin/analytics/*` endpoints
  exist and require `Depends(require_admin)`. Non-admin → 403. Unauthenticated
  → 401. A matching frontend route `/admin/analytics` renders only when
  `user.role === 'admin'` (matches existing `AdminPanel.tsx` role-gate
  pattern at line 45).

- [ ] AC-2: **Metrics section (`GET /api/v1/admin/analytics/metrics`)**
  returns all six PRD OKR values plus 7-day and 30-day deltas:
  registered_users, paying_pro_users, dau_mau_ratio, avg_streak_length,
  ats_to_pro_conversion, monthly_churn. Each value includes the current
  number, the value 7 days ago, the value 30 days ago, and percentage deltas.
  Response matches `MetricsResponse` schema (§API Contract).

- [ ] AC-3: **Performance section
  (`GET /api/v1/admin/analytics/performance`)** returns a snapshot of LLM
  spend-to-date-this-month (estimated from `usage_log.tokens_used` × model
  price), p50/p95/p99 API latency for the top 10 routes (sourced from
  PostHog `$pageview` / backend-instrumented latency events), 5xx error
  rate over 24h, and webhook delivery success rate for Stripe (`stripe_event`
  table). All values are pure aggregations — no LLM calls.

- [ ] AC-4: **Behavior section (`GET /api/v1/admin/analytics/behavior`)**
  returns four funnels (Acquisition, Retention, Mission, Abuse — see
  `.agent/skills/analytics.md` §Key Funnels) with per-step conversion and
  drop-off counts for a requested date range (default last 30 days).
  Funnels are computed via PostHog Query API (`POST /api/projects/.../query`)
  using HogQL. Cached 5 minutes.

- [ ] AC-5: **Enhancement signal section
  (`GET /api/v1/admin/analytics/signals`)** returns four counters for a
  requested date range: paywall dismissals grouped by trigger
  (`paywall_dismissal` table), most-frequent search queries that returned
  zero results (requires a new `search_no_results` event — added in this
  spec, see §New Events), NPS score distribution (sourced from
  `card_feedback` votes as a proxy — `vote=up` positive,
  `vote=down` detractor, neutral otherwise), and top 10 categories by
  `locked_tile_clicked` (signals demand that is paywalled).

- [ ] AC-6: **Feedback themes section
  (`GET /api/v1/admin/analytics/themes`)** returns 5-10 LLM-generated theme
  clusters from `card_feedback.comment` rows written in the last 30 days.
  Each cluster contains `{ theme, count, representative_quotes: list[3] }`.
  The LLM call goes through `generate_for_task(task="admin_feedback_cluster",
  tier="fast", ...)` per R11. Results cache for 24h keyed by
  `(date_range, comment_row_count)` so cluster labels stay stable
  across same-day refreshes.

- [ ] AC-7: **Frontend dashboard** renders all five sections at
  `/admin/analytics` with a shared date-range picker (7d / 30d / 90d / YTD,
  default 30d). Each section is independently loading and independently
  errored (one failing section does not block the others). Matches existing
  `AdminPanel.tsx` tab visual language (neutral panels on `bg-bg-surface/60`,
  `border-contrast/[0.06]`, `text-text-primary`, etc.) — **no hardcoded
  colors** per R12.

- [ ] AC-8: **PostHog events** fire for admin dashboard opens and section
  drills: `admin_analytics_viewed`, `admin_analytics_section_drilled`,
  `admin_analytics_export_clicked` (CSV export — AC-10). Events are
  identified with `admin_id` and tagged `internal: true` so they can be
  excluded from user-facing funnels in PostHog.

- [ ] AC-9: **Audit log** — every admin analytics GET writes a row to a
  new `admin_audit_log` table with `(admin_id, route, query_params,
  timestamp, ip_address)`. See §Data Model Changes.

- [ ] AC-10: **CSV export** — each section has a "Download CSV" button
  that hits `GET /api/v1/admin/analytics/<section>?format=csv` and returns
  a `text/csv` response with the raw tabular data (not the chart view).
  Export is audit-logged with the section name in `query_params`.

- [ ] AC-11: **Rate limit on themes endpoint** — `/themes` is limited to
  `10/hour` per admin via the existing `limiter` decorator (mirrors
  `/admin/cards/generate` at 5/minute). Protects against accidental
  refresh-loop LLM spend.

---

## API Contract

### Auth & Conventions

All endpoints under `/api/v1/admin/analytics/*`:
- Require `Authorization: Bearer <access_token>` + `Depends(require_admin)`.
- Accept optional `?from=YYYY-MM-DD&to=YYYY-MM-DD` (default last 30d). If
  only one bound is given, the other defaults to today / 30-days-ago.
- Accept optional `?format=csv` to stream a CSV response instead of JSON.
- Return `429` if the admin exceeds the route's rate limit.
- All mutations emit an audit log row (writes are the audit itself; reads
  are audit-logged too per AC-9).

### 1. `GET /api/v1/admin/analytics/metrics`

**Response 200 — `MetricsResponse`**
```python
class MetricValue(BaseModel):
    current: float
    d7_ago: float
    d30_ago: float
    delta_7d_pct: float         # ((current - d7_ago) / d7_ago) * 100, 0 if d7_ago == 0
    delta_30d_pct: float

class MetricsResponse(BaseModel):
    registered_users: MetricValue
    paying_pro_users: MetricValue
    dau_mau_ratio: MetricValue        # 0.0–1.0
    avg_streak_length: MetricValue    # days
    ats_to_pro_conversion: MetricValue  # 0.0–1.0, (payment_completed / ats_scanned) windowed 30d
    monthly_churn: MetricValue        # 0.0–1.0, (subscriptions_cancelled_30d / active_subs_at_start_30d)
    generated_at: datetime
    from_cache: bool                   # true if served from Redis
```

### 2. `GET /api/v1/admin/analytics/performance`

**Response 200 — `PerformanceResponse`**
```python
class RouteLatency(BaseModel):
    route: str                         # e.g. "POST /api/v1/analyze"
    p50_ms: float
    p95_ms: float
    p99_ms: float
    request_count: int

class PerformanceResponse(BaseModel):
    llm_spend_estimate_usd: float      # month-to-date, per pricing table in llm_router.py
    llm_spend_breakdown: dict[str, float]  # {"gemini-2.5-flash": 12.34, "gpt-4o-mini": 0.00}
    api_latency: list[RouteLatency]    # top 10 routes by volume
    error_rate_24h_pct: float          # 5xx / total requests, last 24h
    stripe_webhook_success_24h_pct: float
    generated_at: datetime
    from_cache: bool
```

LLM spend uses the per-model prices already encoded in `app/core/llm_router.py`
(or `app/core/config.py` if the prices live there — pick the existing source,
do not introduce a second price table).

### 3. `GET /api/v1/admin/analytics/behavior`

**Response 200 — `BehaviorResponse`**
```python
class FunnelStep(BaseModel):
    event: str                         # e.g. "landing_page_viewed"
    count: int
    conversion_from_prev_pct: float    # 0.0–1.0, 1.0 for the first step

class Funnel(BaseModel):
    name: Literal["acquisition", "retention", "mission", "abuse"]
    date_range: tuple[date, date]
    steps: list[FunnelStep]

class BehaviorResponse(BaseModel):
    funnels: list[Funnel]
    generated_at: datetime
    from_cache: bool
```

Funnel definitions match `.agent/skills/analytics.md` §Key Funnels. The
PostHog project id and personal API key live in env vars (see §Config
Changes).

### 4. `GET /api/v1/admin/analytics/signals`

**Response 200 — `SignalsResponse`**
```python
class PaywallDismissalBucket(BaseModel):
    trigger: str                       # e.g. "daily_review", "category_locked"
    count: int

class ZeroResultSearch(BaseModel):
    query: str
    count: int

class NPSBucket(BaseModel):
    vote: Literal["up", "down", "none"]
    count: int

class LockedCategoryDemand(BaseModel):
    category_id: str
    category_name: str
    click_count: int

class SignalsResponse(BaseModel):
    paywall_dismissals: list[PaywallDismissalBucket]
    zero_result_searches: list[ZeroResultSearch]  # top 20
    nps: list[NPSBucket]
    locked_category_demand: list[LockedCategoryDemand]  # top 10
    generated_at: datetime
    from_cache: bool
```

### 5. `GET /api/v1/admin/analytics/themes`

**Response 200 — `ThemesResponse`**
```python
class FeedbackTheme(BaseModel):
    theme: str                          # e.g. "Answer wording too academic"
    count: int                          # number of comments in this cluster
    representative_quotes: list[str]    # up to 3 verbatim quotes, PII-scrubbed

class ThemesResponse(BaseModel):
    themes: list[FeedbackTheme]         # 5–10 themes
    total_comments_analyzed: int
    generated_at: datetime
    from_cache: bool                    # 24h cache
```

**LLM prompt (reference, not binding):**
```
You are clustering user feedback comments from a learning product.
Given the list below, output 5-10 distinct themes as JSON: [{theme, count,
representative_quotes: [up to 3]}]. Do not include quotes containing
emails, full names, or URLs. Themes should be specific ("answer too long"
not "feedback about answers").
```

Prompt + schema are cached in Redis under
`admin:themes:{date_from}:{date_to}:{row_count_bucket}` with 24h TTL.

### 6. Error codes (all endpoints)

| Status | Condition |
|--------|-----------|
| 401    | Missing or invalid token |
| 403    | Authenticated user is not an admin |
| 422    | Invalid `from`/`to` query params |
| 429    | Rate limit exceeded (themes endpoint only at launch) |
| 502    | PostHog / LLM upstream failure (rare; error propagates per-section) |

---

## Data Model Changes

### New table: `admin_audit_log`

```python
class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    admin_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    route: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)   # GET/POST/PUT/DELETE
    query_params: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
```

Index: `(admin_id, created_at DESC)` for per-admin trails; `(route, created_at DESC)`
for per-endpoint audits. `ondelete="RESTRICT"` so an admin row cannot be
deleted while audit rows exist (forensic requirement).

Alembic: `alembic revision --autogenerate -m "add admin_audit_log"`.

Write path: a single FastAPI dependency `audit_admin_request` appended to
every admin route (`Depends(audit_admin_request)`). Writes are
fire-and-forget (scheduled via `BackgroundTasks`) so audit I/O never blocks
the response.

### New event: `search_no_results`

Frontend-emitted from the card-browser search (today in
`hirelens-frontend/src/pages/StudyDashboard.tsx` — confirm exact file during
implementation). Fires when a non-empty search query returns zero cards.

```ts
capture('search_no_results', { query: normalizedQuery, surface: 'study_dashboard' })
```

Add to `.agent/skills/analytics.md` catalog in the implementation slice.

### No changes to existing tables.

Metric aggregations query existing columns:
- `users.created_at` — registered users over time
- `subscriptions.status, subscriptions.plan_tier, subscriptions.cancelled_at`
  — paying / churn
- `user_card_states` + `card_reviews` — DAU/MAU, streak
- `usage_log` — ATS scan counts for conversion
- `card_feedback.vote, card_feedback.comment` — NPS + themes input
- `paywall_dismissal` — dismissal signals
- `stripe_event` — webhook success

---

## UI/UX

### Route & navigation

- **New route**: `/admin/analytics` (protected by same role-gate as
  `AdminPanel.tsx`).
- **Admin sub-nav**: Extend `AdminPanel.tsx` — or introduce a parent
  `AdminLayout` — with a top-level tab set: `Cards` | `Analytics` |
  `Registration Logs` | `Audit` (Audit added in this spec). Current
  `AdminPanel.tsx` tabs (`cards`, `create`, `generate`, `import`) become
  sub-tabs of `Cards`.
- **Top-nav entry**: the existing admin nav item (`nav_clicked` event
  with `namespace: 'admin'`) continues to deep-link to `/admin/cards` for
  existing users; pin `/admin/analytics` as the new default landing once
  this ships.

### Page layout

1. **Sticky header**: title ("Analytics"), date-range picker (7d / 30d /
   90d / YTD — segmented control), "Download CSV" button (active section).
2. **Five collapsible sections** in a single scroll:
   - **Metrics** — 6 large KPI tiles in a 3×2 grid. Each tile shows current
     value, 7d delta (▲/▼ colored via design tokens — `text-emerald-*`
     banned, use `text-accent-success` / `text-accent-danger` after these
     are added to tokens), 30d delta, and a sparkline of last-30d daily
     values.
   - **Performance** — LLM spend tile (large), route-latency table (top
     10), error-rate tile, webhook-success tile.
   - **Behavior** — four funnel cards side-by-side (stack on mobile). Each
     card shows step counts + conversion bars.
   - **Enhancement signals** — stacked: paywall dismissals bar chart,
     zero-result searches top-20 list, NPS distribution donut,
     locked-category demand top-10.
   - **Feedback themes** — card grid, each card shows theme title, count,
     up to 3 representative quotes. 24h freshness indicator.
3. **Loading + error states per section** — independent skeleton loaders;
   error state shows a muted "Couldn't load this section — retry" button.

### Styling

All colors via design tokens per R12. Tiles use `bg-bg-surface/60`,
`border-contrast/[0.06]`, `rounded-xl` — matching the existing AdminPanel
visual language. Charts use a small wrapper around `recharts` or `visx`
(pick one during implementation — prefer `recharts` if not already in the
repo). Chart colors come from the existing accent palette.

### Mobile

Dashboard is desktop-primary. On mobile (<768px) sections stack full-width;
charts switch to single-column layout; long tables get horizontal scroll.
No feature parity loss — just reflow.

---

## Admin Access & Audit

### Current access model (unchanged, documented for reference)

- **Authentication**: admins sign in with the same Google OAuth flow as
  users. No separate admin login.
- **Authorization**: `users.role` column checked by `require_admin` dep
  (`app/core/deps.py:87`). `AdminPanel.tsx` line 45 redirects non-admins.
- **Promotion**: by direct DB update (`UPDATE users SET role='admin' WHERE
  email=...`), no UI.
- **Session**: JWT-based, same TTL as regular users; role is re-read from
  DB on every request (no embedded role claim), so demotion takes effect
  immediately.

### This spec adds

- `admin_audit_log` table (see §Data Model Changes), populated on every
  admin request.
- `/admin/audit` read-only view (new tab in admin layout) — paginated list
  of audit rows, filterable by `admin_id` and date range. This surface is
  itself audited.
- `admin_analytics_viewed` / `admin_analytics_section_drilled` /
  `admin_analytics_export_clicked` PostHog events for product observability.

### Out of scope — flagged as follow-up spec candidates

The admin-access-hardening umbrella originally listed here has been
partially landed by **`docs/specs/phase-5/54-admin-email-whitelist.md`**
(E-040) — env-driven `ADMIN_EMAILS` whitelist reconciled on login +
frontend `<AdminGate>` wrapper. That closes the "no declarative
source of truth / manual DB promotion" concern. The remaining items
below are still open follow-ups under a narrower hardening umbrella
and should each be authored as their own spec before this dashboard
surfaces anything beyond aggregate counts (i.e. before any per-user
drill-downs):

- **MFA for admin role** — require TOTP on admin sign-in before
  `role=admin` is honored. Matters once the dashboard can drill into
  individual user records. Explicitly deferred in spec #54 LD-1.
- **Admin session IP pinning / short TTL** — admin JWTs expire in 1h
  instead of 30d; re-auth on IP change. Pairs with the live-session
  demotion lag documented in spec #54 §Known Limitations
  (tracked separately as **E-040-follow**).
- **Admin-scoped rate limit profile** — higher LLM ceilings but audit-heavy.
- **PII-scrubbed representative quotes** (partial in this spec for themes;
  should generalize).

None of these block this spec, but the audit log (AC-9) is a hard
prerequisite and is included. Admin promotion UI — previously listed
here — is explicitly **rejected** by spec #54 LD-2 (the env var is
the only promotion path); do not re-author.

---

## Config Changes

New env vars (non-secret placeholders in `hirelens-backend/.env.example`;
secrets in Railway):

```bash
# PostHog — for admin analytics funnel queries
POSTHOG_PROJECT_ID=""
POSTHOG_PERSONAL_API_KEY=""  # distinct from the existing POSTHOG_API_KEY (ingest key)

# Redis cache TTLs
ADMIN_ANALYTICS_CACHE_TTL_SECONDS=300      # metrics/performance/behavior/signals
ADMIN_ANALYTICS_THEMES_CACHE_TTL_SECONDS=86400  # themes
```

Add to `app/core/config.py` with sensible defaults and a `SKIP_POSTHOG=true`
fallback so local dev without a personal API key still boots (sections
requiring PostHog degrade to "unavailable" cards rather than 500s).

---

## Dependencies

Must be Done before this spec:
- `phase-0/03-user-role-admin.md` — **Done** (role, require_admin dep)
- `phase-3/17-admin-card-crud.md` — **Done** (admin router + AdminPanel.tsx shell)
- `.agent/skills/analytics.md` event catalog — **Up to date as of HEAD**

Uses existing infrastructure:
- `app/core/llm_router.py` — `generate_for_task` for themes clustering
- `app/core/rate_limit.py` — `limiter` for themes endpoint
- `app/core/analytics.py` — `track()` for PostHog events
- Redis connection (already used by rate-limit + daily-card-wall counter)

---

## Edge Cases

- **Empty dataset** — a freshly seeded DB has zero feedback comments; the
  themes endpoint returns `{ themes: [], total_comments_analyzed: 0 }` with
  no LLM call (skip if `count < 5`).
- **PostHog outage** — behavior funnels return `{ funnels: [], error:
  "posthog_unavailable" }` per-funnel; the rest of the page renders normally.
- **LLM outage** — themes endpoint returns the last successful cached
  response (`from_cache: true`) with a stale-for banner on the frontend. If
  no cache exists, returns 502 for that section only.
- **Date range crosses DST** — all queries use UTC timestamps; the frontend
  converts for display. Deltas are computed day-aligned in UTC.
- **Admin promoted mid-session** — takes effect on next request (role is
  re-read from DB per `get_current_user`). Audit log records the request
  under the new role.
- **Very large exports** — CSV export is capped at 10k rows. Above that
  the endpoint returns 400 with guidance to narrow the date range.
- **Concurrent refreshes** — cache is keyed by date range but not by admin,
  so two admins on the same range share the cached response. Admin id is
  logged separately (audit) so we still see who viewed what.
- **PII in feedback comments** — themes endpoint runs a regex scrubber
  (email / phone / URL) over each comment before sending to the LLM. The
  original comment is never returned in the response — only quotes the
  LLM echoed back, which were themselves scrubbed.

---

## Test Plan

### Unit tests (`tests/test_admin_analytics.py`)

- `test_metrics_ok` — seed 5 users, 2 subs, stub DAU→assert structure and
  deltas computed correctly.
- `test_metrics_divide_by_zero` — 0 users 7d ago; assert
  `delta_7d_pct == 0.0` not `inf`.
- `test_performance_llm_spend_breakdown` — seed `usage_log` rows with
  known token counts; assert spend matches prices × tokens.
- `test_behavior_funnels_mocked_posthog` — patch PostHog client; assert
  four funnels returned in order.
- `test_signals_nps_bucket_math` — seed `card_feedback` rows with known
  vote distribution; assert up/down/none counts.
- `test_themes_skips_when_below_threshold` — 3 comments in range; assert
  empty themes and no LLM call.
- `test_themes_strips_pii` — inject "contact me at x@y.com"; assert email
  absent from any representative_quote.
- `test_cache_hit_second_call` — call metrics twice; second call returns
  `from_cache: true` and does not re-query DB.
- `test_csv_export_shape` — `?format=csv` → assert `text/csv` content-type
  and expected headers.
- `test_non_admin_blocked` — parametrized over all 5 endpoints; assert
  403.
- `test_unauthenticated_blocked` — parametrized; assert 401.
- `test_themes_rate_limit` — 11 calls in an hour; 11th returns 429.

### Integration tests (`tests/test_admin_analytics_integration.py`)

These run under `@pytest.mark.integration` (live LLM + live PostHog keys):
- `test_themes_live_llm` — seed 20 real-sounding comments; assert 5-10
  theme clusters returned with distinct themes.
- `test_behavior_live_posthog` — run against a seed PostHog project; assert
  a known acquisition funnel returns expected step counts.
- `test_audit_log_row_written` — hit any admin endpoint; assert a matching
  row exists in `admin_audit_log` with correct admin_id and route.

### Manual verification

1. `alembic upgrade head` — confirm `admin_audit_log` table exists via
   `\d admin_audit_log`.
2. Promote self to admin via `UPDATE users SET role='admin' WHERE email='...'`.
3. Visit `/admin/analytics` — verify all five sections render.
4. Click "Download CSV" on Metrics — verify download with correct columns.
5. Refresh page — verify `from_cache: true` on the second request (check
   browser devtools response body).
6. Hit `/admin/analytics` as a non-admin — verify redirect to
   `/prep/analyze`.
7. Query `SELECT * FROM admin_audit_log ORDER BY created_at DESC LIMIT 10`
   — verify one row per request above.
8. Spam themes endpoint 11 times in an hour → 429 on the 11th.

---

## Rollout

Ship in 4 slices (separate commits, separate PRs):
1. **Slice 1 — foundations**: `admin_audit_log` migration, audit dependency,
   `GET /api/v1/admin/audit` listing endpoint, PostHog events
   registration (`admin_analytics_viewed`).
2. **Slice 2 — metrics + performance**: endpoints + Redis caching + UI
   tiles. No LLM, no PostHog Query API dependency.
3. **Slice 3 — behavior + signals**: PostHog Query API integration, funnel
   endpoint, signals endpoint, `search_no_results` event wired in
   `StudyDashboard.tsx`, UI charts.
4. **Slice 4 — themes**: LLM clustering endpoint, PII scrubber, 24h cache,
   UI theme cards, themes rate limit.

Each slice closes a child BACKLOG row under E-018 (to be created by Dhamo
when this spec lands — per R15 this spec does not create BACKLOG rows).
