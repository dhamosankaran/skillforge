# P5-S67 — Career-Climber role-intent capture (target_role + target_quarter + aggregate email framing)

## Status: 🟡 §12 amendment landed — D-1..D-14 locked (impl-ready)

| Field | Value |
|-------|-------|
| **Slice** | P5-S67 (BE-led + 1 FE surface extension + 1 email template extension; spec-author this slice) |
| **Phase** | 5D (persona-aware surface) |
| **Mode** | Mode 4 spec-author → followed by §12 amendment slice → impl slice (B-125 forward-filed) |
| **Filed at** | `d407e6e` (spec-author commit) |
| **BACKLOG row (impl, forward-filed)** | **B-125** 🔴 — filed at status 🔴 by this slice for the future implementation slice per R15(c). R17 watermark verified at filing. |
| **Closes** | **E-052** on impl-slice merge. |
| **Depends on** | spec #34 (PersonaPicker + persona-aware home; shipped) ▪ spec #57 (`homeState.context.next_interview` envelope; shipped `b13f410`) — orthogonal but referenced by the persona contract ▪ spec #6/13 phase-6 (Pro digest opt-out + `email_log` dedup; shipped `email_log` table) ▪ spec #6/14 phase-6 (`pro_digest_service` composer + `pro_digest.html` template; shipped) ▪ existing `PersonaPicker.tsx` capture surface ▪ existing `email_prefs.py` route shape ▪ B-038 (full-replace `PATCH /persona` bug — DO NOT extend; mint dedicated endpoint per B-038 option (b)). |
| **Blocks** | E-053 (CC habit ribbon — depends on E-052 for role-aware radar weighting; not a hard dependency, but radar weighting becomes role-aware only when E-052 ships per E-053 BACKLOG row). |
| **Cross-refs** | spec #34 (persona base — what fields exist on User; CC has no `interview_target_*` analogue today; this spec adds the CC-side fields via a separate table NOT a User column) ▪ spec #6/13 (`email_preferences` opt-out flag — same Pro-tier guard pattern reused) ▪ spec #6/14 (`pro_digest_service.compose_digest` — composer injection point for the aggregate block; `pro_digest.html` template extension) ▪ spec #22 (`MissingSkillsPanel` skill-name → category lookup precedent — re-used for the aggregate study-time-by-category source) ▪ B-038 (full-replace `PATCH /persona` bug — endpoint isolation rationale) ▪ `.agent/skills/design-system.md` (R12 token-only styling) ▪ `.agent/skills/analytics.md` (event catalog discipline) ▪ `.agent/skills/database-schema.md` (UUIDPrimaryKeyMixin precedent for the new table). |

---

## 1. Problem

The Career-Climber persona today is the silent half of the B2C product. Interview-Prepper users get `next_interview` capture (date + company), persona-aware copy on `/home` (spec #65), a live loop strip in AppShell (spec #66), and a pipeline of urgency-driven email reminders. Career-Climbers get **none** of those — a CC user who picks the "I want to stay sharp and get promoted" persona at `/onboarding/persona` lands on a `/home` whose copy says `"${streak}-day streak. ${dueCount} cards due today."` (spec #65 §8.3) and gets the same generic Pro digest as every other user.

The single field that unlocks the CC value prop is **target role + target quarter**. With those two strings on file, the daily email can shift from generic ("5 cards due") to peer-aspirational ("engineers targeting Staff this quarter spend 40% of study time on system design"). That copy is the CC retention lever — the longitudinal, peer-relative framing that no point tool offers.

This is **not** individual peer-comparison. CC users are senior engineers, some under NDAs; copy that names companies, individuals, or "your peers at $company" is legally fraught. Aggregate-only framing is the binding constraint — the spec locks ban-list + minimum-cell-size discipline in §11 ACs and §6 service-layer enforcement.

### 1.1 What's already shipped (out of scope this spec)

- **PersonaPicker** — `src/pages/PersonaPicker.tsx` (spec #34 / #53). The CC card today carries no expansion block (only IP gets the date + company expansion). This spec adds an optional CC expansion block.
- **`PATCH /persona` endpoint** — `app/api/v1/routes/auth.py` (spec #34). Full-replace semantics; B-038 documented the foot-gun. This spec mints a **separate** endpoint (`POST /api/v1/users/me/career-intent`) per B-038 option (b); the persona PATCH stays untouched.
- **`pro_digest_service.compose_digest`** — `app/services/pro_digest_service.py` (spec #6/14 / B-098). Composes the per-user payload from `cards_due` + `streak` + `mission_active` + `last_scan_score`. This spec adds an optional aggregate-block payload field consumed by the template.
- **`pro_digest.html` template** — `app/templates/pro_digest.html`. Three conditional sections (cards / mission / scan). This spec adds a fourth conditional section (aggregate intent block).
- **`email_preferences.daily_digest_opt_out`** — spec #6/13. Already gates the entire digest send. The aggregate block respects the same opt-out (no separate flag).
- **`email_log` dedup table** — spec #6/13. Same row gates same-day re-sends; no new dedup table needed for the aggregate variant.

### 1.2 What this spec ships

A new append-only BE table (`user_career_intents`), a dedicated capture endpoint (`POST /api/v1/users/me/career-intent`), a new BE service (`career_intent_service`) with three public functions (`set_intent` / `get_current_intent` / `get_aggregate_stats`), an extension to `pro_digest_service.compose_digest` to inject an aggregate block when the user has a current intent and the bucket meets ≥10 cell size, an extension to `pro_digest.html` adding a conditional section, an extension to `PersonaPicker.tsx`'s CC card with optional `target_role` + `target_quarter` fields, and a new "Career goal" section in `Profile.tsx`. Three new analytics events. One new alembic migration.

---

## 2. Goals

- **G-1** Capture `target_role` + `target_quarter` for Career-Climber users at PersonaPicker (optional) and from a dedicated Profile section (post-onboarding).
- **G-2** Persist intent history append-only — every change writes a new row; the prior row's `superseded_at` stamps the cutover. Supports the longitudinal narrative E-053 will eventually visualize.
- **G-3** Inject an aggregate study-time-by-category block into the daily Pro digest when the user has a current intent AND the `(target_role, target_quarter)` bucket has ≥10 distinct users.
- **G-4** Enforce aggregate-only framing at the service layer — `get_aggregate_stats` returns `None` below threshold; the composer omits the block silently. Copy uses ONLY aggregate phrasing; spec §11 AC-X enumerates a ban list of forbidden phrases.
- **G-5** Mint a dedicated `POST /api/v1/users/me/career-intent` endpoint per B-038 isolation discipline; do not extend the buggy full-replace `PATCH /persona`.

---

## 3. Non-goals

- **ML-driven personalization** beyond aggregate buckets (per E-052 BACKLOG row). The `(target_role, target_quarter)` bucket is the granularity; no model, no clustering, no per-user prediction.
- **LinkedIn integration** — no profile import, no role inference from LinkedIn data.
- **Resume-derived target role inference** — the user picks explicitly; we do not infer from resume content (avoids accidental down-leveling).
- **In-app surfaces of the aggregate stats** — the value is in email per Dhamo's "data gold" framing. The aggregate is computed only inside the digest composer; no `GET /api/v1/users/me/career-intent/aggregate` endpoint, no `<CareerIntentInsights>` component.
- **Team Lead persona variants** — `team_lead` users hitting the endpoint receive 422; no TL-specific intent shape this slice.
- **Interview-Prepper persona variants** — IP users hitting the endpoint receive 422; the IP capture surface is `interview_target_*` per spec #34, NOT this endpoint.
- **Changing existing daily-digest copy for users without intents** — users without a current intent see the unchanged digest (cards / mission / scan sections only). The aggregate block is purely additive.
- **A "compare to peers" individual surface** — explicitly forbidden by §11 AC-X ban list.
- **CSV export of aggregates for admin** — future admin surface; out of scope this slice.
- **Backfill of historical "implied" intents from user behavior** — no inference; intents start empty for all existing users.
- **Any change to `PATCH /persona`** — the B-038 foot-gun stays untouched; CC intent capture lives on the new endpoint.
- **Any change to `interview_target_company` / `interview_target_date`** — IP-side capture, orthogonal to this spec. CC users never write those columns.
- **`email_log` extension for the aggregate variant** — same `email_type='pro_digest'` row gates same-day re-sends; no separate `email_type='pro_digest_with_intent'`.
- **Per-`(target_role, target_quarter)` aggregate-block opt-out** — coarse-grained `daily_digest_opt_out` is sufficient; users who don't want the aggregate copy opt out of the entire digest.

---

## 4. Architecture

### 4.1 Component graph

```
┌── PersonaPicker.tsx (existing, extended) ─────────────────────┐
│  CC card → expansion block (NEW) → optional fields:           │
│    [target_role: select]   [target_quarter: select]           │
│  Submit calls:                                                 │
│    1. PATCH /api/v1/persona  (existing — persona only)        │
│    2. POST /api/v1/users/me/career-intent  (NEW — if filled)  │
└────────────────────────────────────────────────────────────────┘

┌── Profile.tsx (existing, extended) ────────────────────────────┐
│  NEW section "Career goal" (CC personas only) →                │
│    Current intent display + Edit affordance                    │
│    Edit form posts to POST /api/v1/users/me/career-intent      │
└────────────────────────────────────────────────────────────────┘

┌── POST /api/v1/users/me/career-intent (new route) ─────────────┐
│  app/api/v1/routes/career_intent.py                            │
│  Auth required; persona must be 'career_climber' (else 422)    │
│  Validates target_role enum + target_quarter regex + future    │
│  Calls career_intent_service.set_intent                        │
└────────────────────────────────────────────────────────────────┘

┌── career_intent_service (new) ─────────────────────────────────┐
│  app/services/career_intent_service.py                         │
│  - set_intent(db, user_id, target_role, target_quarter)        │
│      → supersedes prior current row (sets superseded_at=now)   │
│      → inserts new row                                         │
│  - get_current_intent(db, user_id) → row WHERE superseded_at   │
│      IS NULL or None                                           │
│  - get_aggregate_stats(db, target_role, target_quarter)        │
│      → returns AggregateStats or None (None if cohort < 10)    │
│      → ENFORCES privacy contract at the source                 │
└────────────────────────────────────────────────────────────────┘

┌── pro_digest_service.compose_digest (existing, extended) ──────┐
│  After existing payload composition, conditionally injects      │
│  aggregate_intent_block when:                                   │
│    1. get_current_intent(user_id) is not None                  │
│    2. get_aggregate_stats(intent.target_role, target_quarter)  │
│       returns non-None (cohort ≥ 10)                            │
│  DigestPayload gets new optional field aggregate_intent_block  │
└────────────────────────────────────────────────────────────────┘

┌── pro_digest.html (existing, extended) ────────────────────────┐
│  New conditional <div data-section="intent"> block with        │
│  {{intent_section_style}} display:none when block is None      │
│  Copy uses aggregate-only framing per §8.5 ban-list            │
└────────────────────────────────────────────────────────────────┘
```

### 4.2 Why a separate table, not User columns

Per E-052 BACKLOG row's locked decision (design-review risk #3), `user_career_intents` is **append-only history** from day one — NOT a `users.target_role` + `users.target_quarter` column pair.

Rationale:
- **Longitudinal narrative.** Every intent change is an event. The CC retention story is "you picked Staff in 2026-Q1, you're still on track in 2026-Q3." Column-overwrite loses that.
- **E-053 dependency.** The CC habit ribbon + skill-radar trend block (E-053) wants the longitudinal picture for role-aware radar weighting. Append-only history is the right shape.
- **Privacy preservation.** Aggregate queries can compute cohort stats at any historical point. Column-overwrite would force the aggregate to use only current state, losing temporal cohort definitions.

### 4.3 Why a dedicated endpoint, not extending `PATCH /persona`

B-038 documented the full-replace foot-gun: any client passing only `{persona: 'career_climber'}` would clobber `interview_target_company` and `interview_target_date` to NULL. B-038 option (b) — "mint a dedicated endpoint per affected field cluster" — was the locked mitigation.

This spec mints `POST /api/v1/users/me/career-intent` for the CC-side capture cluster. The persona PATCH is **not modified** by this slice. Two-call submit on PersonaPicker (PATCH persona then POST career-intent) is acceptable per §8.2 (two atomic operations, second is optional, idempotent across retries).

### 4.4 Privacy-contract enforcement point

The ≥10 minimum cell size enforcement lives in `career_intent_service.get_aggregate_stats` — the **single** entry point. The composer never bypasses; the composer never sees raw counts; the composer receives `AggregateStats | None` and gates rendering on `is None`.

Forbidden phrases per §11 AC-X (ban list) are enforced at template-render time via a snapshot test — `tests/test_pro_digest_intent_template.py::test_aggregate_block_does_not_contain_forbidden_phrases` asserts the rendered HTML does not contain any banned substring. Defence-in-depth: §6 service ENFORCES the threshold; §11 AC ENFORCES the copy.

---

## 5. Data model

### 5.1 New table `user_career_intents`

| Column | Type | Constraint | Notes |
|--------|------|------------|-------|
| `id` | `String(36)` | PK | Per `UUIDPrimaryKeyMixin` precedent |
| `user_id` | `String(36)` | FK `users.id` ON DELETE CASCADE; NOT NULL; indexed | Append-only; one user has many rows |
| `target_role` | `String(30)` | NOT NULL; validated in Pydantic against enum | See §5.3 enum |
| `target_quarter` | `String(7)` | NOT NULL; validated in Pydantic against regex `^\d{4}-Q[1-4]$` | e.g. `'2026-Q3'` |
| `created_at` | `DateTime(timezone=True)` | NOT NULL; `server_default=func.now()` | Insert time |
| `superseded_at` | `DateTime(timezone=True)` | NULLABLE | NULL = current row; non-NULL = stamped at the moment a newer row was inserted (or explicit "Clear my goal" was called) |

**Index:** composite `(user_id, superseded_at)` — drives the current-intent lookup `WHERE user_id = ? AND superseded_at IS NULL` (one row per user matches).

**Indexes for aggregate query:** composite `(target_role, target_quarter, superseded_at)` — drives `WHERE target_role = ? AND target_quarter = ? AND superseded_at IS NULL`.

### 5.2 ORM model

`app/models/user_career_intent.py`:

```python
class UserCareerIntent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "user_career_intents"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    target_role: Mapped[str] = mapped_column(String(30), nullable=False)
    target_quarter: Mapped[str] = mapped_column(String(7), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
```

No `back_populates` on `User.career_intents` — the relationship is queried via `career_intent_service`, not via lazy-loaded ORM relationship (avoids N+1 risk in the digest composer's per-user loop). User model stays byte-untouched.

### 5.3 Pydantic schemas

`app/schemas/career_intent.py`:

```python
ALLOWED_ROLES = frozenset({
    "staff", "senior_staff", "principal", "distinguished",
    "em", "sr_em", "director",
})

class CareerIntentCreate(BaseModel):
    target_role: str  # Validated against ALLOWED_ROLES via @field_validator
    target_quarter: str  # Validated against ^\d{4}-Q[1-4]$ + future-or-current

class CareerIntentResponse(BaseModel):
    id: str
    user_id: str
    target_role: str
    target_quarter: str
    created_at: datetime
    superseded_at: datetime | None
    model_config = ConfigDict(from_attributes=True)

class AggregateStats(BaseModel):
    """Returned by get_aggregate_stats when cohort >= 10. None otherwise."""
    target_role: str
    target_quarter: str
    cohort_size: int  # >= 10 by construction
    top_categories: list[CategoryShare]  # Top 3 by study-time share

class CategoryShare(BaseModel):
    category_name: str
    percent_of_study_time: float  # 0..100
```

### 5.4 Future-quarter validation

`target_quarter` must be the **current quarter** or a **future quarter** at insert time. Computed quarter from `datetime.now(timezone.utc)`:
- `Q1 = months 1-3`, `Q2 = 4-6`, `Q3 = 7-9`, `Q4 = 10-12`.
- Insert with `target_quarter < current_quarter` → 422 with `detail="target_quarter must be current or future"`.

Past quarters are forbidden because the value of intent is forward-looking; a user setting `'2024-Q1'` in 2026-Q3 is signalling history, not aspiration.

**Edge case:** intents written in 2026-Q3 with `target_quarter='2026-Q3'` (current) remain valid through Q3 — they do NOT auto-supersede on quarter rollover. Whether to auto-archive `target_quarter < current_quarter` rows on quarter rollover is locked at §12 D-9 (NO auto-archive — explicit user action required).

### 5.5 Persona-switch supersession semantics

When a user switches persona via `PATCH /persona` (any direction — CC → IP, IP → CC, etc.), the persona PATCH route does NOT cascade-supersede the user's current intent. Rationale: a CC → IP → CC switch should preserve the prior CC intent (user may be re-confirming, not resetting).

The current-intent row is superseded **only** by:
1. A new `POST /api/v1/users/me/career-intent` write (auto-supersedes prior current row).
2. An explicit "Clear my goal" affordance (writes a sentinel: stamp `superseded_at` on prior current row, do NOT insert a replacement).

Locked at §12 D-5.

---

## 6. Backend

### 6.1 New service `career_intent_service`

`app/services/career_intent_service.py`:

```python
async def set_intent(
    db: AsyncSession,
    user_id: str,
    target_role: str,
    target_quarter: str,
) -> UserCareerIntent:
    """Append-only write — supersedes prior current row, inserts new."""
    now = datetime.now(timezone.utc)

    # 1. Stamp prior current row if any.
    await db.execute(
        update(UserCareerIntent)
        .where(UserCareerIntent.user_id == user_id)
        .where(UserCareerIntent.superseded_at.is_(None))
        .values(superseded_at=now)
    )

    # 2. Insert new current row.
    intent = UserCareerIntent(
        user_id=user_id,
        target_role=target_role,
        target_quarter=target_quarter,
    )
    db.add(intent)
    await db.flush()
    return intent


async def get_current_intent(
    db: AsyncSession, user_id: str
) -> Optional[UserCareerIntent]:
    """Returns the row with superseded_at IS NULL (at most one per user)."""
    result = await db.execute(
        select(UserCareerIntent)
        .where(UserCareerIntent.user_id == user_id)
        .where(UserCareerIntent.superseded_at.is_(None))
    )
    return result.scalar_one_or_none()


async def clear_intent(db: AsyncSession, user_id: str) -> None:
    """Stamp prior current row with superseded_at=now; do NOT insert."""
    await db.execute(
        update(UserCareerIntent)
        .where(UserCareerIntent.user_id == user_id)
        .where(UserCareerIntent.superseded_at.is_(None))
        .values(superseded_at=datetime.now(timezone.utc))
    )


async def get_aggregate_stats(
    db: AsyncSession, target_role: str, target_quarter: str
) -> Optional[AggregateStats]:
    """Aggregate study-time-by-category for the cohort.

    Returns None when cohort < MIN_COHORT_SIZE (10). The single privacy-
    contract enforcement point per §4.4 — composer NEVER bypasses.
    """
    # 1. Cohort size — count distinct users with current intent in bucket.
    cohort_size = (await db.execute(
        select(func.count(distinct(UserCareerIntent.user_id)))
        .where(UserCareerIntent.target_role == target_role)
        .where(UserCareerIntent.target_quarter == target_quarter)
        .where(UserCareerIntent.superseded_at.is_(None))
    )).scalar_one()

    if cohort_size < MIN_COHORT_SIZE:
        return None

    # 2. Aggregate study-time-by-category for that cohort.
    # (Implementation queries quiz_review_events joined to cards joined to
    # categories, scoped to user_ids in the cohort, summed by category;
    # see §6.3 for SQL shape.)
    top_categories = await _query_top_categories(
        db, target_role, target_quarter
    )

    return AggregateStats(
        target_role=target_role,
        target_quarter=target_quarter,
        cohort_size=cohort_size,
        top_categories=top_categories,
    )
```

Constants:
- `MIN_COHORT_SIZE = 10` — locked at design review per E-052 BACKLOG row.
- `TOP_CATEGORIES_K = 3` — return top 3 categories by share. Hardcoded for v1; env-tunable promotion is post-launch only.

### 6.2 New route

`app/api/v1/routes/career_intent.py`:

```python
@router.post(
    "/users/me/career-intent",
    response_model=CareerIntentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def set_career_intent(
    body: CareerIntentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CareerIntentResponse:
    if user.persona != "career_climber":
        raise HTTPException(
            status_code=422,
            detail="Career intent capture is only available for "
                   "Career-Climber persona users.",
        )
    intent = await career_intent_service.set_intent(
        db, user.id, body.target_role, body.target_quarter
    )
    track(user.id, "career_intent_captured" if first_intent
          else "career_intent_updated", {...})
    return CareerIntentResponse.model_validate(intent)
```

R3 (auth required) honored via `Depends(get_current_user)`. No additional rate-limit override beyond global 100 req/min default — the endpoint is low-volume by nature (intents change quarterly).

GET endpoint (`GET /api/v1/users/me/career-intent`) returns the current intent or 404 — consumed by the Profile.tsx "Career goal" section to display current state.

DELETE endpoint (`DELETE /api/v1/users/me/career-intent`) calls `clear_intent` and returns 204. Consumed by the Profile.tsx "Clear my goal" affordance.

### 6.3 `pro_digest_service.compose_digest` extension

The composer gains one new step BEFORE the strict-empty-rule check:

```python
# Existing composer body...
cards_due = await _count_cards_due(db, user.id)
streak = await _get_streak(db, user.id)
mission_active, mission_days_left = await _mission_info(db, user.id)
last_scan_score, last_scan_delta = await _last_scan_info(db, user.id)

# NEW (E-052):
aggregate_intent_block = None
intent = await career_intent_service.get_current_intent(db, user.id)
if intent is not None:
    aggregate_intent_block = await career_intent_service.get_aggregate_stats(
        db, intent.target_role, intent.target_quarter
    )

# Existing strict empty-rule (extend to also check aggregate block):
if (
    cards_due == 0
    and not mission_active
    and last_scan_score is None
    and aggregate_intent_block is None
):
    return None

return DigestPayload(
    user_id=user.id,
    user_name=user.name or user.email or "there",
    user_email=user.email,
    cards_due=cards_due,
    streak=streak,
    mission_active=mission_active,
    mission_days_left=mission_days_left,
    last_scan_score=last_scan_score,
    last_scan_delta=last_scan_delta,
    aggregate_intent_block=aggregate_intent_block,  # NEW
)
```

`DigestPayload` gains one new optional field `aggregate_intent_block: AggregateStats | None`. Backward-compatible — existing template renders are unaffected when the field is None.

The strict-empty-rule extension is intentional: a CC user with no cards / no mission / no scan but WITH an aggregate intent block now receives the digest (the aggregate copy is the engagement signal). This is a behavior change vs spec #6/14 §12 D-7; locked here as an additive carveout.

### 6.4 No new dedup row

The existing `email_log` UNIQUE `(user_id, email_type='pro_digest', sent_date)` row gates same-day re-sends regardless of whether the digest contained an aggregate block. No `email_type='pro_digest_with_intent'` variant — same digest, same dedup row.

### 6.5 Failure-mode contract

`career_intent_service.get_aggregate_stats` errors (DB connection, query timeout) are caught at the composer boundary and treated as `None` (no aggregate block this digest tick). The user still receives the digest with the existing three sections. Telemetry: `pro_digest_intent_aggregate_failed {user_id, error_class, internal: True}` fires on the catch.

`career_intent_service.set_intent` errors propagate as 500 to the route. The route surfaces a generic 500 to the FE; no rollback of the persona PATCH (the two calls are independent — if the second fails, the persona is set but the intent is not, and the user retries from Profile).

---

## 7. Migration

New alembic migration `<rev_id>_phase5_e052_user_career_intents.py`:

```python
def upgrade():
    op.create_table(
        "user_career_intents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("target_role", sa.String(30), nullable=False),
        sa.Column("target_quarter", sa.String(7), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_user_career_intents_user_id",
                    "user_career_intents", ["user_id"])
    op.create_index("ix_user_career_intents_user_current",
                    "user_career_intents", ["user_id", "superseded_at"])
    op.create_index("ix_user_career_intents_bucket_current",
                    "user_career_intents",
                    ["target_role", "target_quarter", "superseded_at"])

def downgrade():
    op.drop_index("ix_user_career_intents_bucket_current")
    op.drop_index("ix_user_career_intents_user_current")
    op.drop_index("ix_user_career_intents_user_id")
    op.drop_table("user_career_intents")
```

`down_revision` = current alembic head (verified at impl Step 0 — current head at spec-author time is `f1a2b3c4d5e6` per `ls hirelens-backend/alembic/versions/ | tail`; impl slice MUST re-confirm at code time per slice 6.10 / E-043 foundation precedent).

Round-trip safe (reversible). No data backfill — existing users start with zero rows; the table fills as users opt in.

---

## 8. Frontend

### 8.1 PersonaPicker.tsx extension

The CC card today (`PersonaPicker.tsx:42-46`) gets an expansion block analogous to the IP card's `targetDate` + `targetCompany` block (`PersonaPicker.tsx:198-251`).

Shape:

```tsx
{selected === 'career_climber' && (
  <motion.div
    key="cc-extras"
    initial={{ opacity: 0, height: 0 }}
    animate={{ opacity: 1, height: 'auto' }}
    exit={{ opacity: 0, height: 0 }}
    transition={{ duration: 0.25 }}
    className="overflow-hidden"
  >
    <div className="mt-4 p-4 rounded-xl border border-border bg-bg-surface flex flex-col gap-3">
      <div>
        <label htmlFor="cc-target-role" ...>Target role</label>
        <select id="cc-target-role" data-testid="cc-target-role-input" ...>
          <option value="">Optional — pick later from Profile</option>
          <option value="staff">Staff Engineer</option>
          <option value="senior_staff">Senior Staff</option>
          <option value="principal">Principal Engineer</option>
          <option value="distinguished">Distinguished Engineer</option>
          <option value="em">Engineering Manager</option>
          <option value="sr_em">Senior EM</option>
          <option value="director">Director</option>
        </select>
      </div>
      <div>
        <label htmlFor="cc-target-quarter" ...>Target quarter</label>
        <select id="cc-target-quarter" data-testid="cc-target-quarter-input" ...>
          <option value="">Optional — pick later from Profile</option>
          {/* Computed list: current + 7 future quarters */}
        </select>
      </div>
    </div>
  </motion.div>
)}
```

Submit handler extension: after the existing `updatePersona` call succeeds with `persona='career_climber'`, if BOTH `targetRole` and `targetQuarter` are filled, fire `POST /api/v1/users/me/career-intent`. If only one is filled, omit the call — both fields are required by the endpoint per §5.3.

Errors on the second call (career-intent) do NOT block navigation — the user proceeds to `/first-action` or `/home`; the intent can be set later from Profile. Toast `"Goal not saved — set it from Profile."` on intent failure.

### 8.2 Profile.tsx "Career goal" section

New section, rendered ONLY when `user.persona === 'career_climber'`:

| State | Render |
|-------|--------|
| No current intent | Heading "Career goal" + body "Set your target role and quarter to get peer-aspirational copy in your daily digest." + button `[Set my goal →]` opens inline form |
| Has current intent | Heading "Career goal" + body "Targeting **{role_label}** by **{quarter_label}**." + buttons `[Edit]` `[Clear]` |

Inline form: same `target_role` + `target_quarter` selects as PersonaPicker (§8.1). Submit fires `POST /api/v1/users/me/career-intent`. Cancel closes the form without writes.

Clear: confirm modal `"Clear your career goal? You can set a new one anytime."` → `DELETE /api/v1/users/me/career-intent` → toast `"Goal cleared."` → re-render in no-intent state.

Inline-form-vs-modal modality locked at §12 D-2 (inline form).

### 8.3 Quarter picker labels

Display labels for `target_quarter` selects: `"YYYY Q[1-4]"` rendered as e.g. `"2026 Q3 (Jul-Sep)"` for clarity. Stored value is the canonical `'YYYY-Q[1-4]'` form for unambiguous backend parsing.

The select's option list is computed client-side from `Date.now()`: current quarter + next 7 quarters (covers ~2 years forward, sufficient for the typical 12-18 month career-climb horizon).

### 8.4 Loading / error semantics

- PersonaPicker: intent fields are optional; submit always works even when both are empty (only persona PATCH fires). Failure on the intent POST does NOT undo the persona PATCH (it stays committed).
- Profile: GET intent failure → render in no-intent state with a small `text-text-muted` "Could not load goal" line; DOES NOT block the rest of the Profile page.
- Profile Edit form: in-flight state shows submit button as `[Saving…]` disabled; success closes form + toasts; failure keeps form open with inline error.

### 8.5 Aggregate-block copy (template-level, NOT visible in app UI)

Copy shapes for the aggregate intent block in `pro_digest.html` (§9.3 binds to `top_categories` shape):

```
Engineers targeting {role_label} this quarter spend
  {pct_1}% of study time on {category_1},
  {pct_2}% on {category_2},
  and {pct_3}% on {category_3}.
```

Example rendered: `"Engineers targeting Staff this quarter spend 40% of study time on system design, 28% on distributed systems, and 18% on agentic AI."`

**Ban list — copy must NOT contain any of these substrings** (enforced by snapshot test §11 AC-X):
- `"your peers at"`
- `"engineers from {company}"` (any specific company name)
- `"users like you"`
- `"at companies like"`
- `"based on your background"`
- `"compared to"` followed by a name/identifier
- `"top performers"` (implies individual identification of high-performers)
- Any of the cohort users' names, emails, or company names.

The ban list is encoded in `tests/test_pro_digest_intent_template.py` as a Python tuple; impl-time additions trigger a snapshot review.

### 8.6 New `services/api.ts` functions

Three new exports:
- `setCareerIntent({target_role, target_quarter}): Promise<CareerIntentResponse>` → POST
- `getCurrentCareerIntent(): Promise<CareerIntentResponse | null>` → GET (404 → null)
- `clearCareerIntent(): Promise<void>` → DELETE

Auth headers via existing `apiClient` interceptor; no new auth wiring.

---

## 9. Telemetry

### 9.1 New events

| Event | Source | Properties | Fires |
|-------|--------|------------|-------|
| `career_intent_captured` | `app/api/v1/routes/career_intent.py` (BE) AND `src/pages/PersonaPicker.tsx` / `src/pages/Profile.tsx` (FE on success) | `{target_role, target_quarter, source: 'persona_picker' \| 'profile_edit'}` | First-time intent capture (no prior current row). BE fires with `source` derived from a request header `X-Capture-Source`; FE also fires (telemetry redundancy is acceptable — admin dashboard de-dups by user+timestamp) |
| `career_intent_updated` | Same as above | `{from_role, to_role, from_quarter, to_quarter, source}` | Subsequent intent change (prior current row exists and gets superseded) |
| `career_intent_email_block_rendered` | `pro_digest_service` (BE) on successful render of the aggregate block in a sent digest | `{target_role, target_quarter, cohort_size, top_category}` | Once per digest send that contained an aggregate block |

`top_category` in the email-block event is the highest-share category name (e.g. `"system design"`) — used for downstream A/B analysis on which category headlines drive digest engagement.

### 9.2 Existing events touched

- `pro_digest_sent` (spec #6/14) gets one new property `has_aggregate_block: bool` to enable cohort analysis on which sends contained the new copy.
- `persona_selected` (spec #34) unchanged — the intent capture is a separate event; persona pick + intent capture can be on the same submit but emit two distinct events.
- No changes to `email_unsubscribed` / `email_resubscribed`.

### 9.3 Failure events

- `pro_digest_intent_aggregate_failed` — fires from §6.5 catch path; payload `{user_id, error_class, internal: True}`.
- `career_intent_set_failed` — FE fires on POST 500/422; payload `{source, error_class}`. Supports the user-recovery toast flow.

### 9.4 Catalog updates

`.agent/skills/analytics.md` gains 5 new rows (3 success events + 1 success-event-property update + 2 failure events). All in the same patch as the new event rows. Catalog discipline preserves alphabetical-within-section ordering.

---

## 10. Tests

### 10.1 Test envelope (BE)

| Surface | Test count | Range |
|---------|-----------|-------|
| `user_career_intent` model + migration round-trip | 2 (1 model creation + 1 alembic round-trip integration-marked) | 2-3 |
| `career_intent_service.set_intent` (insert + supersede + idempotency) | 4 | 4-5 |
| `career_intent_service.get_current_intent` (none / one / after-supersede) | 3 | 3-4 |
| `career_intent_service.clear_intent` (clears current; no insert) | 2 | 2-3 |
| `career_intent_service.get_aggregate_stats` (below threshold returns None / at threshold / over threshold / cross-bucket isolation) | 4 | 4-5 |
| `POST /api/v1/users/me/career-intent` route (200 / 401 / 422 wrong-persona / 422 invalid-role / 422 past-quarter) | 5 | 5-6 |
| `GET /api/v1/users/me/career-intent` route (200 / 404 no-current) | 2 | 2-3 |
| `DELETE /api/v1/users/me/career-intent` route (204 / no-op when nothing to clear) | 2 | 2-3 |
| `pro_digest_service.compose_digest` extension (no-intent path unchanged / intent-but-cohort-too-small / intent-and-cohort-met-threshold) | 3 | 3-4 |
| `tests/test_pro_digest_intent_template.py::test_aggregate_block_does_not_contain_forbidden_phrases` snapshot | 1 | 1 |
| **Total BE** | **~28** | **+26..+34** |

### 10.2 Test envelope (FE)

| Surface | Test count | Range |
|---------|-----------|-------|
| `PersonaPicker` CC card expansion (renders on CC select / both fields optional / submits intent on success / does NOT submit on partial fill / persona PATCH success carries through even when intent POST fails) | 5 | 5-6 |
| `Profile` Career-goal section (no-intent state / has-intent state / Edit form opens / Clear confirms + DELETEs / non-CC personas don't see section) | 5 | 5-6 |
| `services/api.ts` new functions (POST happy / GET 404 → null / DELETE 204) | 3 | 3-4 |
| **Total FE** | **~13** | **+13..+16** |

### 10.3 New / extended files

- New `tests/test_career_intent_service.py` (~+13 BE)
- New `tests/test_career_intent_route.py` (~+9 BE)
- Extend `tests/services/test_pro_digest_service.py` (+3 BE)
- New `tests/test_pro_digest_intent_template.py` (+1 BE — ban-list snapshot)
- New `tests/test_e052_user_career_intents_migration.py` (+1 BE integration-marked)
- New `tests/integration/test_user_career_intents_round_trip.py` excluded; round-trip bundled in migration test.
- Extend `tests/PersonaPicker.test.tsx` (+5 FE)
- New `tests/Profile.career-goal.test.tsx` (+5 FE)
- Extend `tests/services/api.test.ts` (+3 FE)

### 10.4 Regression invariants

- `tests/services/test_pro_digest_service.py` 14 existing tests stay green (new code path is additive; no-intent users see byte-identical composer output).
- `tests/PersonaPicker.test.tsx` IP-side tests stay green (CC expansion is a new branch).
- `tests/test_persona_route.py` (PATCH /persona) tests stay green (route untouched per §4.3).
- `pro_digest.html` rendered HTML for users without current intent is byte-identical to current (verified via `tests/test_pro_digest_template.py` if it exists; otherwise add).

---

## 11. Acceptance criteria

| AC | Surface | Trigger | Expected behavior |
|----|---------|---------|-------------------|
| **AC-1** | `user_career_intents` model | Insert with valid `target_role` + `target_quarter` | Row persists with `superseded_at IS NULL`; auto `created_at` populated |
| **AC-2** | `set_intent` | Called twice for same user | Second call stamps prior `superseded_at` and inserts a new current row |
| **AC-3** | `get_current_intent` | After a user has 3 historical intents | Returns the row with `superseded_at IS NULL`; never the historical rows |
| **AC-4** | `clear_intent` | After a current intent exists | Stamps `superseded_at`; subsequent `get_current_intent` returns None |
| **AC-5** | `get_aggregate_stats` | Cohort has 9 users with same `(role, quarter)` | Returns None (below MIN_COHORT_SIZE) |
| **AC-6** | `get_aggregate_stats` | Cohort has 10 users | Returns `AggregateStats` with `cohort_size=10` and top-3 categories |
| **AC-7** | `get_aggregate_stats` | Cohort has 50 users in `(staff, 2026-Q3)` and 5 in `(staff, 2027-Q1)` | First call returns stats; second call returns None (bucket isolation) |
| **AC-8** | `POST /career-intent` | Auth missing | 401 |
| **AC-9** | `POST /career-intent` | Auth present, persona=`interview_prepper` | 422 with `detail` mentioning "career_climber" |
| **AC-10** | `POST /career-intent` | `target_role='vp'` (not in enum) | 422 with `detail` mentioning enum |
| **AC-11** | `POST /career-intent` | `target_quarter='2024-Q1'` (past) | 422 with `detail` "must be current or future" |
| **AC-12** | `POST /career-intent` | Valid body | 201 with `CareerIntentResponse`; `career_intent_captured` (or `_updated`) fires |
| **AC-13** | `compose_digest` | User has no current intent | Composer return shape unchanged; `aggregate_intent_block=None` |
| **AC-14** | `compose_digest` | User has current intent, cohort < 10 | `aggregate_intent_block=None` (silent suppression — no copy this tick) |
| **AC-15** | `compose_digest` | User has current intent, cohort ≥ 10 | `aggregate_intent_block` populated; rendered HTML contains the aggregate copy |
| **AC-16** | `pro_digest.html` rendered | Aggregate block present | `<div data-section="intent">` is visible (no `display:none`); contains percent + category text |
| **AC-17** | `pro_digest.html` rendered | Aggregate block absent | `<div data-section="intent">` has `display:none` style |
| **AC-X** | `pro_digest.html` rendered (any path) | Aggregate block populated | Rendered HTML does NOT contain any of the §8.5 ban-list substrings (snapshot test) |
| **AC-18** | `email_log` row | After successful send with aggregate block | One row with `email_type='pro_digest'`; same UNIQUE constraint gates re-send (no `'pro_digest_with_intent'` variant) |
| **AC-19** | PersonaPicker | CC selected, intent fields filled, submit | PATCH /persona succeeds; POST /career-intent succeeds; navigation proceeds |
| **AC-20** | PersonaPicker | CC selected, intent fields blank, submit | PATCH /persona succeeds; NO POST /career-intent; navigation proceeds |
| **AC-21** | PersonaPicker | CC selected, intent fields filled, POST /career-intent fails | PATCH /persona stays committed; toast "Goal not saved — set it from Profile."; navigation proceeds |
| **AC-22** | Profile | persona=`career_climber`, no current intent | "Career goal" section renders with `[Set my goal →]` CTA |
| **AC-23** | Profile | persona=`career_climber`, has current intent | "Career goal" section renders with `[Edit]` + `[Clear]` |
| **AC-24** | Profile | persona=`interview_prepper` | "Career goal" section does NOT render |
| **AC-25** | Profile | Clear confirmed | DELETE /career-intent fires; section re-renders in no-intent state |

AC-X (forbidden-phrases ban) is intentionally out-of-numeric-sequence to flag its critical-privacy nature.

---

## 12. Locked Decisions

D-1..D-14 lock the §14 OQ-1..OQ-14 author-hint defaults 1:1 (Dhamo
single-admin disposition; zero ambiguous hints).

- **D-1 — PersonaPicker capture timing:** auto-expand on CC select to surface the optional intent fields. Mirrors IP card precedent at `PersonaPicker.tsx:198-251`. Both fields stay optional; auto-expand is a discoverability win, not a forcing function.
- **D-2 — Profile edit modality:** inline form (in place). Mirrors existing Profile section affordances; modal would be heavier weight than warranted for a 2-field write.
- **D-3 — `get_aggregate_stats` query timing:** live per-digest-tick v1. Cache only if telemetry shows latency hit on bulk-send. Cron is sequential per §6.14 D-11; per-user latency budget is generous.
- **D-4 — Quarter selection ceiling:** current + 7 future (~2 years). Career-climb horizons typically 12-18 months; 2 years is generous.
- **D-5 — Persona-switch supersession semantics:** `PATCH /persona` does NOT auto-supersede the current intent. Preserve through CC → IP → CC churn. A returning CC user shouldn't lose their goal.
- **D-6 — Intent-clear affordance:** explicit `[Clear]` button writing `superseded_at` only (no replacement insert). Clearer affordance + distinct telemetry signal vs edit-as-clear which conflates revise vs abandon.
- **D-7 — Email template injection:** extend `pro_digest.html` with a 4th conditional section. Forking into `pro_digest_with_intent.html` would double template-maintenance surface; 4 conditional sections is well within precedent.
- **D-8 — Below-threshold (<10 cohort) email behavior:** silent suppression of the aggregate block. Explicit "Your goal is rare" copy reveals cohort sparsity and is bad for early-CC adoption.
- **D-9 — Quarter rollover behavior:** leave past-quarter current rows current; no auto-archive. User reaching a target quarter without explicit action is informative — they may be on track. Auto-archive is forward work in §13.
- **D-10 — Bucket grouping granularity:** `(target_role, target_quarter)` exact match only v1. No fall-back to `target_role` alone. Fallback complicates the cohort definition and dilutes the "this quarter" framing.
- **D-11 — `target_role` enum source-of-truth:** frozenset constant in `app/schemas/career_intent.py` + `@field_validator` in Pydantic schema. Easier to extend than DB CHECK; mirrors existing enum patterns at `app/schemas/study.py`.
- **D-12 — Re-onboarding flow when CC user without intent:** passive (Profile section only). No `/home` banner, no auto-prompt. Banner risks pestering; user discovers via Profile, or a future telemetry-driven nudge picks up the gap.
- **D-13 — `career_intent_email_block_rendered` event:** fire only on actual `email_service.send_email` success path. Test-run template renders MUST NOT pollute telemetry. Implementation gates the `analytics_track` call inside the orchestrator's post-send branch (§6 / spec #6/14 §6.5 precedent).
- **D-14 — Below-threshold telemetry:** silent (no event). Surfacing cohort sparsity in PostHog is an admin-dashboard concern, not a user-tied event-stream concern. Reconsider only if admin-side cohort-growth telemetry becomes a need.

---

## 13. Out of scope (forward work)

- **ML-driven personalization** — aggregate buckets only; no per-user prediction this slice.
- **LinkedIn integration** — no profile import.
- **Resume-derived target role inference** — explicit pick only.
- **In-app aggregate stats surface** — value is in email; no `<CareerIntentInsights>` component this slice.
- **Team Lead persona variants** — TL hits the endpoint, gets 422.
- **Interview-Prepper persona variants** — IP hits the endpoint, gets 422.
- **Auto-archive of past `target_quarter` rows on quarter rollover** — explicit user action only (§12 D-9).
- **Per-aggregate-block opt-out** — coarse `daily_digest_opt_out` covers it.
- **Backfill of historical implied intents** — none.
- **`PATCH /persona` extension** — endpoint stays untouched (B-038 isolation).
- **Admin observability of intent rows / aggregates** — out of scope; future admin surface.
- **CSV export of aggregates** — future admin surface.
- **`email_type='pro_digest_with_intent'` dedup variant** — same `'pro_digest'` row gates re-sends.
- **Phase-6 read consolidation** (e.g., merge career_intent into a `home_state_v2_service`) — deferred.

---

## 14. Open questions

All 14 OQs RESOLVED at this slice's §12 amendment (single-admin
disposition; author-hint defaults accepted 1:1).

| # | Question | Status |
|---|----------|--------|
| OQ-1 | PersonaPicker capture timing — should the CC card auto-expand on select to surface the optional intent fields? | → Locked at §12 D-1. |
| OQ-2 | Profile edit modality — inline form or modal overlay? | → Locked at §12 D-2. |
| OQ-3 | `get_aggregate_stats` query timing — live per-digest-tick or cached? | → Locked at §12 D-3. |
| OQ-4 | Quarter selection ceiling — current + 7 future or current + 11 future? | → Locked at §12 D-4. |
| OQ-5 | Persona-switch supersession semantics — should `PATCH /persona` auto-supersede the current intent? | → Locked at §12 D-5. |
| OQ-6 | Intent-clear affordance — explicit `[Clear]` button or edit-as-clear? | → Locked at §12 D-6. |
| OQ-7 | Email template injection — extend `pro_digest.html` or fork? | → Locked at §12 D-7. |
| OQ-8 | Below-threshold (<10 cohort) email behavior — silent suppression or explicit copy? | → Locked at §12 D-8. |
| OQ-9 | Quarter rollover behavior — auto-archive past-quarter rows or leave current? | → Locked at §12 D-9. |
| OQ-10 | Bucket grouping granularity — exact match only or fall back to role-alone? | → Locked at §12 D-10. |
| OQ-11 | `target_role` enum source-of-truth — Pydantic `Literal`, frozenset, or DB CHECK? | → Locked at §12 D-11. |
| OQ-12 | Re-onboarding flow when CC user without intent — auto-prompt or passive? | → Locked at §12 D-12. |
| OQ-13 | `career_intent_email_block_rendered` event — fire on send-success only or also on render-only? | → Locked at §12 D-13. |
| OQ-14 | Below-threshold telemetry — fire suppression event or stay silent? | → Locked at §12 D-14. |

---

## 15. Test plan summary

Test files (see §10.3):
- New `tests/test_career_intent_service.py` (~+13 BE)
- New `tests/test_career_intent_route.py` (~+9 BE)
- Extend `tests/services/test_pro_digest_service.py` (+3 BE)
- New `tests/test_pro_digest_intent_template.py` (+1 BE — ban-list snapshot)
- New `tests/test_e052_user_career_intents_migration.py` (+1 BE integration-marked)
- Extend `tests/PersonaPicker.test.tsx` (+5 FE)
- New `tests/Profile.career-goal.test.tsx` (+5 FE)
- Extend `tests/services/api.test.ts` (+3 FE)

**Test count envelope:** **~+28 BE (floor +26, ceiling +34)** + **~+13 FE (floor +13, ceiling +16)**.

**Regression set:** existing `pro_digest_service` 14 tests stay green; PersonaPicker IP-side tests stay green; `PATCH /persona` route tests stay green; `pro_digest.html` no-intent rendered HTML byte-identical to current.

### 15.1 Forward links

- **E-053** (CC habit ribbon + skill-radar 30-day trend block on `/home`) — depends on E-052 for role-aware radar weighting; not a hard dependency, but radar weighting becomes role-aware only when E-052 ships per E-053 BACKLOG row.
- **Future admin surface** — role-intent analytics dashboard (cohort distribution, intent-flux rate, aggregate-block engagement) — out of scope this slice; surfaces in a future Phase-6 admin slice.
- **Future generalization** — if `team_lead` or `interview_prepper` personas need similar capture, the same `user_career_intents` shape generalizes via a new column or via a sibling table. Not in scope this spec.

---

*End of spec #67. §12 amendment landed — D-1..D-14 locked. Implementation begins next slice (B-125 impl pickup).*
