---
slice: P5-S59 (spec) + P5-S59-impl (impl, separate slice)
base_sha: 1c768e9
drafted: 2026-04-23
backlog: B-0XX (to be filed in impl commit; see §Closes)
depends_on: spec #40 (state-aware home; mounts LastScanWidget surface), spec #44 (widget empty-state contract), spec #57 (recent tracker_applications_v2 schema change — 9543aa466524)
amends: none (net-new)
---

# SPEC: Scan persistence + Results page hydration from URL `scan_id`

## Status: Shipped (spec + impl) — closes B-035. Impl `0b35440` on 2026-04-24.

## 1. Problem

The `/home` **Last Scan** widget (`hirelens-frontend/src/components/home/widgets/LastScanWidget.tsx:17`)
reads a persisted tracker summary (`company`, `role`, `ats_score`, `scan_id`)
via `fetchUserApplications()` → `GET /api/v1/tracker`. Its "View results" CTA
links to `/prep/results?scan_id=<id>` (line 41-43).

`Results.tsx` reads the full analysis payload exclusively from
`useAnalysisContext()` (`src/pages/Results.tsx:41,46,140`). That context is a
plain `useReducer` with `initialState.result = null` and **no persistence
layer** — no `localStorage`, no `sessionStorage`, no API fallback. The URL
`scan_id` is read at `Results.tsx:88` only as a pass-through prop to
`MissingSkillsPanel` — never to fetch and hydrate the missing `result`.

The backend **never persists the full `AnalysisResponse`**. Only a summary
is stored on `tracker_applications_v2` (`app/models/tracker.py`): `company`,
`role`, `date_applied`, `ats_score`, `status`, `scan_id`, `skills_matched`,
`skills_missing`, `interview_date`. The rich sub-objects
(`keyword_chart_data`, `skill_gaps`, `bullet_analysis`, `formatting_issues`,
`job_fit_explanation`, `score_breakdown`, `skills_overlap_data`,
`top_strengths`, `top_gaps`, `missing_keywords`, `resume_text`) are returned
once at scan time and thrown away. A verbatim comment at
`src/hooks/useAnalysis.ts:55-57` acknowledges this: *"A client-side scan_id
is used purely for PostHog correlation — the backend doesn't persist scans
yet."*

**User-visible symptom:** a returning free user on a fresh session sees the
Last Scan widget populated with a real company + ATS score, clicks "View
results," and lands on the `/prep/results` empty state ("No Analysis
Yet — Upload your resume to see your results"). The widget's data and the
Results page's data come from two different sources that share only
`scan_id` as a key. Dead-end from a surface that looks interactive.

## 2. Locked design decisions

All locked by Dhamo 2026-04-23 in the authoring prompt. Restated here so
the spec is self-contained.

- **LD-1 — Persistence location: column, not table.** Add a single
  `analysis_payload JSONB NULL` column to `tracker_applications_v2`. 1:1
  with the tracker row; no new table, no join on read. Rationale: every
  scan already creates a tracker row (`app/api/routes/analyze.py:227-248`);
  a second table would duplicate that relationship. JSONB (not JSON)
  because Postgres JSONB supports indexed predicates if we ever need
  them; storage cost is the same for our access pattern.

- **LD-2 — Read-path deferral.** The ORM column is loaded with
  `sqlalchemy.orm.deferred()`. `GET /tracker` list responses (the widget's
  backing endpoint) **do not** load `analysis_payload` — list-view rows
  stay ~300 bytes each. The column is materialized only on explicit
  `.undefer()` or when an attribute access triggers a lazy load (which we
  avoid by routing reads through a purpose-built service function). Intent
  is a pay-for-what-you-use pattern: one scan's payload is ~15-40 KB of
  JSON, which would multiply list-tracker latency and bandwidth by the
  user's application count for no benefit.

- **LD-3 — Write path: same transaction as tracker summary.** `POST /analyze`
  writes the full `AnalysisResponse` into `analysis_payload` at the same
  point it writes the tracker summary row
  (`app/api/routes/analyze.py:227-248`). The same `db.flush()` already
  present covers both. Anonymous scans (current_user is None) get **no**
  tracker row today (line 227 guards on `current_user`) — therefore no
  `analysis_payload` either. Anonymous-scan persistence is out of scope
  here; see §Out-of-scope.

- **LD-4 — Read path endpoint: `GET /api/v1/analyze/{scan_id}`.** Auth:
  `Depends(get_current_user)`. Ownership check: `scan_id` must match a
  tracker row where `user_id == current_user.id`. Mismatch → **404 Not
  Found** (not 403). Rationale: 403 leaks that the scan exists but
  belongs to someone else. 404 is correct both for "no such scan_id"
  and "scan_id owned by another user" — indistinguishable to the caller.

- **LD-5 — Legacy rows: 410 Gone.** Scans written before the migration have
  `analysis_payload = NULL`. The endpoint returns **410 Gone** with a
  machine-readable detail body:

  ```json
  { "error": "scan_payload_unavailable",
    "code": "legacy_scan_pre_persistence",
    "scan_id": "<uuid>",
    "message": "This scan was created before full results were stored." }
  ```

  410 (not 404, not 204, not 200-with-null) because the resource exists
  conceptually (the tracker row is there) but the payload representation
  is permanently unavailable for that id. 410 signals "gone, not coming
  back" unambiguously. The frontend tolerates this via distinct empty-
  state copy (LD-6).

- **LD-6 — Frontend hydration on `Results.tsx` mount.** When
  `result === null && urlScanId` is true, fire `GET /api/v1/analyze/{scan_id}`
  inside a `useEffect`. On success, `dispatch({ type: 'SET_RESULT', payload })`
  and render normally. On 410, render a **specific** empty-state copy:
  *"This scan is from before we stored full results — re-scan to view."*
  with a "Start Analysis" CTA. On 404, render the **generic** empty-state
  copy (existing "No Analysis Yet" body) because the scan was never
  viewable. On network/5xx, render an error variant with retry.

- **LD-7 — LastScanWidget stays as-is.** The link already carries
  `?scan_id=…`. No change to widget code; the bug closes once Results
  hydrates. The widget remains the canonical home-surface entry into the
  re-view flow.

- **LD-8 — No expiry, no TTL.** Payloads live as long as the tracker row
  lives. Tracker rows are deleted by user action only
  (`DELETE /api/v1/tracker/{id}`). No garbage collection policy in this
  spec. A future slice may add expiry (e.g., "scans older than 12 months
  get pruned") when storage cost becomes material; see §Out-of-scope.

- **LD-9 — No version field.** `AnalysisResponse` is already Pydantic-
  versioned by schema evolution (additive fields default-gracefully; we
  have not removed a field yet). A `schema_version` inside the JSONB
  payload would be premature. Future slice can add one when the first
  breaking change is proposed.

- **LD-10 — `CODE-REALITY.md` regen required at impl time.** One new
  route (`GET /api/v1/analyze/{scan_id}`), one new service function, one
  model change (column add), one new frontend hydration effect.
  `App.tsx` / layout unchanged.

## 3. Step-0 audit summary (accepted)

Re-verified at HEAD `1c768e9`:

- **LastScanWidget data source:** `fetchUserApplications()` →
  `GET /api/v1/tracker` → `TrackerApplication[]` summary. "View results"
  → `/prep/results?scan_id=<id>` or `/prep/tracker` if no scan_id.
- **Results.tsx decision:** `!result` → empty state at lines 140-154.
  `useSearchParams` reads `scan_id` but only passes through to
  `MissingSkillsPanel.scanId` (line 88, line 271). No fetch, no hydrate.
- **AnalysisContext:** `useReducer` + `initialState.result = null`. Only
  writer: `useAnalysis.ts:52` `SET_RESULT` after live `POST /analyze`.
  No localStorage / sessionStorage / API fallback anywhere in `src/`.
- **Backend persistence:** `tracker_applications_v2` stores summary only
  (`app/models/tracker.py`). `POST /analyze` at
  `app/api/routes/analyze.py:47` returns `AnalysisResponse` directly
  and writes only a `TrackerApplicationCreate` (summary fields + skills
  lists). No GET-by-scan_id endpoint anywhere. `app/api/v1/routes/analyze.py`
  is empty of route handlers (grep `@router.` returns nothing).
- **Smoking gun:** `src/hooks/useAnalysis.ts:55-57` literal comment:
  *"the backend doesn't persist scans yet."*
- **Alembic head:** `eb59d4fc1f7e` (backfill tracker interview_date,
  spec #57). New revision will `down_revision = 'eb59d4fc1f7e'`.
- **Related rows / patterns:** B-017 (widget CTA → unreachable capture
  surface), B-019 (TodaysReviewWidget completed-state mismatch) —
  same "widget promises a surface the page can't fulfill" family.
  `home.md` Widget Empty-State Contract rule is the umbrella.

## 4. Solution overview

Three moving parts.

### 4.1 Backend — persistence column + write path

`tracker_applications_v2` gains `analysis_payload JSONB NULL`, loaded with
`sqlalchemy.orm.deferred()` in `app/models/tracker.py`. `POST /analyze`
(`app/api/routes/analyze.py:227-248`) writes the full `AnalysisResponse`
into the new column at the same point it creates the tracker summary row.
The `create_application` service in
`app/services/tracker_service_v2.py:54-78` gains an
`analysis_payload: Optional[dict]` kwarg; the ORM model field is set inside
the constructor.

### 4.2 Backend — read endpoint + ownership check

New route `GET /api/v1/analyze/{scan_id}` in a new
`app/api/v1/routes/analyze.py` (currently empty). Response model:
`AnalysisResponse` (reused verbatim — no new Pydantic type). Ownership
check: service function `get_scan_by_id(scan_id, db, user_id)` performs
a single query joining on `(scan_id, user_id)` with `.undefer(analysis_payload)`
applied. Three outcomes:

1. No row → 404.
2. Row exists, `analysis_payload IS NULL` → 410 (legacy).
3. Row exists, payload loaded → 200 + payload unpacked into
   `AnalysisResponse`.

### 4.3 Frontend — Results hydration effect

`Results.tsx` gains a `useEffect` mounted on `[urlScanId, result]`. If
`result === null && urlScanId` and no hydrate attempt already in flight,
call a new `fetchScanById(scanId)` from `services/api.ts`. On success,
`dispatch({ type: 'SET_RESULT', payload })`. On 410, set local state
`hydrateStatus: 'legacy'`. On 404, `hydrateStatus: 'not_found'`. On
network error, `hydrateStatus: 'error'`. Empty-state branch chooses copy
from `hydrateStatus`.

`LastScanWidget.tsx` unchanged.

## 5. Alembic migration sketch

New revision file `alembic/versions/<hash>_add_analysis_payload_to_tracker.py`.

```python
"""add analysis_payload to tracker_applications_v2

Revision ID: <autogen>
Revises: eb59d4fc1f7e
Create Date: 2026-04-XX

Spec #59 — persist full AnalysisResponse per scan so /prep/results can
hydrate from URL scan_id on a fresh session. JSONB NULL; loaded via
sqlalchemy.orm.deferred() on the ORM so GET /tracker list stays cheap.
No backfill — legacy rows stay NULL and trigger 410 on read.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "<autogen>"
down_revision: Union[str, Sequence[str], None] = "eb59d4fc1f7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — add nullable analysis_payload JSONB column."""
    op.add_column(
        "tracker_applications_v2",
        sa.Column(
            "analysis_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema — drop analysis_payload column."""
    op.drop_column("tracker_applications_v2", "analysis_payload")
```

**No backfill.** Legacy rows stay `NULL`. No index added — access is
exclusively by `(user_id, scan_id)` which is already covered by the
existing `ix_tracker_applications_v2_scan_id` index + the unique
`(user_id, id)` path.

## 6. ORM model change

`app/models/tracker.py`:

```python
from sqlalchemy import JSON  # JSONB via postgresql.JSONB on the column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import deferred, mapped_column

class TrackerApplicationModel(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "tracker_applications_v2"
    # … existing fields …

    # Spec #59 — full AnalysisResponse payload for scan re-view. Loaded
    # via deferred() so list-tracker responses do not inflate. Access
    # through tracker_service_v2.get_scan_by_id (uses undefer).
    analysis_payload: Mapped[dict | None] = deferred(
        mapped_column(JSONB, nullable=True)
    )
```

## 7. New route signature

`app/api/v1/routes/analyze.py` (today empty of handlers):

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.responses import AnalysisResponse
from app.services import tracker_service_v2

router = APIRouter(prefix="/api/v1/analyze", tags=["analyze"])


@router.get("/{scan_id}", response_model=AnalysisResponse)
async def get_scan_by_id(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """Return the full stored AnalysisResponse for a scan owned by the
    current user. 404 if unknown / not owner; 410 if payload is NULL
    (legacy scan written before persistence shipped).
    """
    row = await tracker_service_v2.get_scan_by_id(
        scan_id=scan_id, db=db, user_id=current_user.id
    )
    if row is None:
        raise HTTPException(status_code=404, detail={
            "error": "scan_not_found",
            "scan_id": scan_id,
        })
    if row.analysis_payload is None:
        raise HTTPException(status_code=410, detail={
            "error": "scan_payload_unavailable",
            "code": "legacy_scan_pre_persistence",
            "scan_id": scan_id,
            "message": "This scan was created before full results were stored.",
        })
    return AnalysisResponse(**row.analysis_payload)
```

Mount in `app/main.py` alongside the other v1 routers.

**Amendment (2026-04-24, post-impl):** Shipped 2026-04-23 in commit
`0b35440` on the existing shared legacy router (the same router that
hosts `POST /analyze`) with `/api/v1` re-export, **not** a new
v1-specific router as originally specced above. Matches the existing
`POST /analyze` pattern — same path surface (canonical FE path
`/api/v1/analyze/{scan_id}` is unchanged), one source of truth for the
`/analyze/*` routes, smaller diff. Recorded as judgment call #1 in the
P5-S59-impl final report. The original §7 sketch above is preserved as
the author-time intent; the amendment is the as-shipped reality.

## 8. Service ownership check

`app/services/tracker_service_v2.py`:

```python
from sqlalchemy.orm import undefer

async def get_scan_by_id(
    scan_id: str,
    db: AsyncSession,
    user_id: str,
) -> Optional[TrackerApplicationModel]:
    """Return the ORM row (not the Pydantic TrackerApplication summary)
    so the route can access analysis_payload directly. Ownership is
    enforced by matching user_id; rows owned by other users return None.
    """
    _require_user_id(user_id)
    stmt = (
        select(TrackerApplicationModel)
        .where(TrackerApplicationModel.scan_id == scan_id)
        .where(TrackerApplicationModel.user_id == user_id)
        .options(undefer(TrackerApplicationModel.analysis_payload))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
```

Note: this returns the **ORM model** (not the Pydantic `TrackerApplication`
summary used elsewhere in this service) because the route needs
`analysis_payload` which is not on the summary schema. This is the single
exception; all other tracker-service functions continue to return
`TrackerApplication`.

## 9. POST /analyze write path change

`app/api/routes/analyze.py:234-248`:

```python
tracker_data = TrackerApplicationCreate(
    company=company[:200],
    role=position[:200],
    date_applied=date.today().isoformat(),
    ats_score=score_result["total"],
    status="Applied",
    scan_id=scan_id,
)
analysis_response = AnalysisResponse(
    scan_id=scan_id,
    ats_score=score_result["total"],
    # … same fields as the final return below …
)
await create_application(
    tracker_data,
    db,
    user_id=current_user.id,
    skills_matched=matched_keywords,
    skills_missing=missing_keywords,
    analysis_payload=analysis_response.model_dump(mode="json"),
)
```

The `AnalysisResponse` is constructed once, persisted, then returned
verbatim — guaranteeing the re-view payload is byte-identical to what
the user saw at scan time.

`create_application` in `tracker_service_v2.py` gains an
`analysis_payload: Optional[dict] = None` kwarg and sets the model field.

## 10. Frontend hydration effect sketch

`src/services/api.ts` — new helper:

```typescript
export async function fetchScanById(scanId: string): Promise<AnalysisResponse> {
  const response = await api.get<AnalysisResponse>(
    `/api/v1/analyze/${encodeURIComponent(scanId)}`
  )
  return response.data
}
```

`src/pages/Results.tsx` — new hydration state + effect:

```typescript
type HydrateStatus = 'idle' | 'fetching' | 'success' | 'not_found' | 'legacy' | 'error'
const [hydrateStatus, setHydrateStatus] = useState<HydrateStatus>('idle')

useEffect(() => {
  if (result || !urlScanId || hydrateStatus !== 'idle') return
  setHydrateStatus('fetching')
  fetchScanById(urlScanId)
    .then((payload) => {
      dispatch({ type: 'SET_RESULT', payload })
      setHydrateStatus('success')
      capture('scan_rehydrated', {
        scan_id: urlScanId,
        scan_age_days: /* derived from tracker row created_at if we include it;
                         else 'unknown' — see §Telemetry */
      })
    })
    .catch((err) => {
      const status = axios.isAxiosError(err) ? err.response?.status : undefined
      const next: HydrateStatus =
        status === 410 ? 'legacy'
          : status === 404 ? 'not_found'
            : 'error'
      setHydrateStatus(next)
      capture('scan_rehydrate_failed', {
        scan_id: urlScanId,
        reason: next,
        http_status: status ?? 0,
      })
    })
}, [result, urlScanId, hydrateStatus, dispatch])
```

Empty-state branch:

```typescript
if (!result) {
  if (hydrateStatus === 'fetching') return <SkeletonDashboard />
  const copy = {
    legacy: {
      heading: 'Results Not Available',
      body: 'This scan is from before we stored full results — re-scan to view.',
      cta: 'Re-scan resume',
    },
    not_found: {
      heading: 'No Analysis Yet',
      body: 'Upload your resume to see your results.',
      cta: 'Start Analysis',
    },
    error: {
      heading: 'Couldn\'t Load Results',
      body: 'We hit a snag fetching your scan. Try again in a moment.',
      cta: 'Retry',
    },
    idle: {
      heading: 'No Analysis Yet',
      body: 'Upload your resume to see your results.',
      cta: 'Start Analysis',
    },
    success: null, // unreachable — result would be set
  }[hydrateStatus]
  return <EmptyStateCard {...copy} />
}
```

The `error` CTA re-runs the effect by resetting `hydrateStatus` to `idle`.
The `legacy` and `not_found` CTAs navigate to `/prep/analyze`.

## 11. Test plan

### 11.1 Backend unit tests

`tests/test_tracker_service_scan_payload.py` (new):

- `get_scan_by_id` returns `None` for unknown `scan_id` (→ 404 branch).
- `get_scan_by_id` returns `None` when scan_id is owned by a different
  user (→ 404 branch, not 403 — tests that ownership leak is closed).
- `get_scan_by_id` returns the ORM row with `analysis_payload` materialized
  when `undefer` is applied.
- `create_application` persists `analysis_payload` when the kwarg is
  provided; leaves NULL when omitted.

### 11.2 Backend integration tests

`tests/test_analyze_scan_by_id.py` (new):

- Happy path: `POST /api/analyze` with mocked LLM → capture `scan_id`
  from response → `GET /api/v1/analyze/{scan_id}` → 200 + same payload
  shape + field equality on `ats_score`, `grade`, at least one nested
  list (`skill_gaps`).
- 404 anonymous: `GET /api/v1/analyze/{random_uuid}` without auth → 401
  (auth precedes ownership check).
- 404 unknown scan_id: authed user requests `{random_uuid}` → 404.
- 404 cross-user: user A creates scan, user B requests it → 404 (not 403).
- 410 legacy: manually insert a tracker row with `scan_id=X,
  analysis_payload=NULL` → `GET /api/v1/analyze/X` → 410 with
  `detail.code == "legacy_scan_pre_persistence"`.
- List-tracker unchanged: `GET /api/v1/tracker` before and after scan
  write returns equal serialized bytes (excluding timestamps) + no
  `analysis_payload` key anywhere in the response (guards LD-2 deferred).

### 11.3 Frontend tests

`src/pages/__tests__/Results.hydration.test.tsx` (new):

- `result === null && urlScanId` present + mocked `fetchScanById`
  resolves → full dashboard renders + `scan_rehydrated` PostHog capture
  fires once.
- Mock returns 410 → legacy empty-state copy verbatim + CTA to
  `/prep/analyze`.
- Mock returns 404 → generic empty-state copy verbatim.
- Mock rejects with network error → error empty-state + retry works
  (second fetch attempt fires on CTA click).
- `result !== null` on mount → no fetch attempted (no MSW call intercepted).
- `urlScanId` absent → no fetch attempted.
- Fetch fires once, not on every render (idempotency guard via
  `hydrateStatus !== 'idle'`).

## 12. Telemetry

Two new PostHog events wired frontend-side (capture emitted from
`Results.tsx`, no backend emitter). Adds to `.agent/skills/analytics.md`
catalog.

### `scan_rehydrated`
Fired after `GET /api/v1/analyze/{scan_id}` returns 200 and
`SET_RESULT` dispatches. Properties:

| Property | Type | Source |
|---|---|---|
| `scan_id` | string | URL param |
| `scan_age_days` | integer \| null | derived from tracker row `created_at` if exposed in the response envelope; **null** if not — see §Note below |
| `entry_surface` | string | `'last_scan_widget'` when referrer is `/home`, else `'direct'` |

### `scan_rehydrate_failed`
Fired on any non-200 response from the same endpoint. Properties:

| Property | Type | Source |
|---|---|---|
| `scan_id` | string | URL param |
| `reason` | string | one of `'legacy'`, `'not_found'`, `'error'` |
| `http_status` | integer | axios response status (0 on network error) |

**Note on `scan_age_days`:** the current `AnalysisResponse` schema does
not carry `created_at`. Impl slice has two choices: (a) add
`scan_created_at: datetime | None` to `AnalysisResponse` (additive, safe)
and derive age client-side, or (b) leave the property `null` for this
slice and revisit when a follow-up surfaces the need. **Recommendation:**
(a) — a 4-line additive change; supports retention analytics.

## 13. Out of scope (explicit)

1. **Backfilling legacy scans.** Rows written before the migration stay
   `analysis_payload = NULL` forever. If legacy-scan re-view becomes a
   priority, a separate spec would need to back-derive the payload (or
   accept a lossy reconstruction from stored summary fields, which is
   product-level lossy — not a drop-in fix).
2. **Cross-device sync of in-flight scans.** If a user starts a scan on
   device A then opens `/home` on device B before the scan finishes, the
   widget on B won't show the in-flight scan. This slice only covers
   post-persist re-view. Real-time cross-device is a separate, larger
   change (websockets or poll-on-widget-mount).
3. **Scan expiry / TTL / storage-cost policy.** Payloads live as long as
   the tracker row. A future slice will add "scans older than N months
   get pruned" once storage becomes material — probably tied to a user-
   visible "older scan — upgrade to extend storage" Pro perk.
4. **Scan list / history page.** No `/prep/scans` index view is added. The
   Last Scan widget + the tracker page cover today's entry surfaces.
   Surfacing more than the most-recent scan in a dedicated list is a
   separate product slice.
5. **Anonymous scan persistence.** Anonymous (not-logged-in) scans do not
   create tracker rows today (`app/api/routes/analyze.py:227` guard) and
   therefore no `analysis_payload`. Out of scope; folding anonymous
   scans into persistence would need a session-keyed storage path.
6. **Schema versioning of the JSONB payload.** No `schema_version` field
   inside the payload. Will be added when the first breaking change to
   `AnalysisResponse` is proposed (LD-9).
7. **Admin-side scan inspection.** No admin dashboard view of stored
   payloads for debugging. Add later if support needs it.
8. **LastScanWidget changes.** Widget unchanged — link already carries
   `scan_id`, and the widget's data contract is already met.

## 14. Acceptance criteria

- **AC-1** — `POST /analyze` persists the full `AnalysisResponse` to
  `analysis_payload` on the tracker row it creates (authed users). The
  persisted payload `model_dump(mode="json")` round-trips via
  `AnalysisResponse(**payload)` to a byte-identical model.
- **AC-2** — `GET /api/v1/analyze/{scan_id}` returns the full
  `AnalysisResponse` for the owning user with 200 + all rich sub-objects
  populated (keyword chart, skill gaps, bullet analysis, formatting
  issues, job-fit explanation, score breakdown).
- **AC-3** — `GET /api/v1/tracker` response size is unchanged
  (<5% byte delta vs pre-migration on a user with N=10 scans); the
  `analysis_payload` key does not appear in the response envelope.
  Enforced by LD-2 (`deferred()`).
- **AC-4** — Non-owner or unknown `scan_id` returns **404** (not 403).
  Tested explicitly in §11.2.
- **AC-5** — Legacy scan (`analysis_payload IS NULL`) returns **410** with
  `detail.error == "scan_payload_unavailable"` and
  `detail.code == "legacy_scan_pre_persistence"`.
- **AC-6** — `Results.tsx` hydrates from URL `scan_id` when
  `AnalysisContext.result === null`. Three distinct empty-state copies
  render on 410 vs 404 vs network-error; the 200 path renders the full
  dashboard identical to the post-scan-live render.
- **AC-7** — Returning free user on a fresh session can click "View
  results" from `LastScanWidget` and see the full Results page — ATS
  score, job-fit explanation, skill gaps, keyword chart — the same
  payload they saw at scan time. Manually verifiable by:
  (a) scan as user X; (b) log out; (c) log back in; (d) `/home` →
  LastScanWidget → "View results"; (e) observe full dashboard renders
  without another `POST /analyze`.

## 15. Blast radius

| Surface | Change |
|---|---|
| `alembic/versions/<hash>_add_analysis_payload_to_tracker.py` | New file |
| `app/models/tracker.py` | +1 column, `deferred()` |
| `app/services/tracker_service_v2.py` | +`analysis_payload` kwarg on `create_application`; new `get_scan_by_id` returning ORM model |
| `app/api/routes/analyze.py` | Write `analysis_payload` alongside tracker summary |
| `app/api/v1/routes/analyze.py` | New `GET /{scan_id}` route (file currently empty) |
| `app/main.py` | Mount the new router |
| `src/services/api.ts` | `fetchScanById` helper |
| `src/pages/Results.tsx` | Hydration effect + empty-state copy switch |
| `src/types/index.ts` | No change — `AnalysisResponse` already typed |
| Tests (BE) | +~10 new (service + integration) |
| Tests (FE) | +~6 new (`Results.hydration.test.tsx`) |
| `.agent/skills/analytics.md` | +2 events (`scan_rehydrated`, `scan_rehydrate_failed`) |
| `CODE-REALITY.md` | Route table row, model row, services row |

**Not touched:** `LastScanWidget.tsx`, `AnalysisContext.tsx`,
`useAnalysis.ts`, any other widget, any other page, auth stack,
rate-limit stack, usage gating, paywall.

## 16. Closes

- **B-0XX** (to be filed in the P5-S59-impl commit) — `home | LastScanWidget
  View-results dead-ends for returning free user — scan payload never
  persisted | P1 | 🔴`. Row filing + closure happen in the impl commit
  per R15 closure rule; this spec slice does not touch BACKLOG.md.

## 17. Open questions (none blocking)

- Should `AnalysisResponse` gain `scan_created_at: datetime | None` for
  the `scan_age_days` telemetry property? Recommended yes (LD-9 §12
  Note). Decide at impl time; trivial additive change.
- Should the 410 body include a "last time this scan was viewed" hint to
  make the "re-scan to view" CTA less abrupt? Nice-to-have, not
  blocking. Could ship in the same impl slice if the payload is easy to
  derive; else defer.
