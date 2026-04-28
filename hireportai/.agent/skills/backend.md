---
description: Backend service-layer + FastAPI route conventions — signatures, error classes, transactions, auth chains, response shapes, and cross-service patterns
---
# Backend Skill

## Purpose

How services, routes, and schemas are wired in `hirelens-backend/`.
Read before authoring a new service or route, or when threading a new
parameter (auth, persona, tier) through an existing read path.

Adjacent skills carry domain-specific extensions of these conventions:
`study-engine.md` (FSRS scheduler), `analytics.md` (PostHog events +
dual-write tables), `admin-panel.md` (admin auth chain + audit log),
`database-schema.md` (column-level contracts), `db-migration.md`
(Alembic), `testing.md` (test layout + integration-marker discipline).
Anything those cover is canonical there; this skill covers the
generic backend layer.

## 1. Service-layer conventions

### File layout

- One file per domain, flat under `app/services/`. Subsystems are
  grouped by **filename prefix**, not directory: `quiz_item_*`,
  `lesson_*`, `admin_*`, `card_*`, etc.
- Shared error classes for a subsystem live in
  `app/services/admin_errors.py` (only admin so far). Per-service
  errors live in the service file as siblings of the public functions.
- Helpers stay co-located until the rule-of-three trips. Promote to a
  third module only when a third on-disk consumer materializes
  (slice 6.5 D-5 escape hatch).

### Function signatures

Async-first. Public functions take `db: AsyncSession` first
positional, then domain args, then **keyword-only** params:

```python
async def get_lesson_with_quizzes(
    lesson_id: str,
    db: AsyncSession,
    *,
    user: Optional[User] = None,
) -> LessonWithQuizzesResponse | None:
    ...
```

`*, user: Optional[User] = None` is the standard threading pattern for
read paths that need persona / tier filtering. Default to `None` for
back-compat at non-filter call sites (slice 6.5 R16 pattern). Required
auth is enforced at the route layer via `Depends(get_current_user)`
(see §2); the service stays compositional.

### Public vs private

Leading underscore = private. Private helpers and module constants
(`_DAILY_GOAL`, `_scheduler`, `_persona_visible_to`,
`_visible_persona_set`, `_allowed_tiers_for_user`, `_resolve_plan`,
`_utcnow`) stay co-located with their callers. Don't extract until a
third consumer surfaces.

### Error classes

Locally defined in the service file. Reuse over introduce — slice 6.5
extended `QuizItemForbiddenError` additively with a keyword-only
`reason='premium_deck'` rather than spawning a second tier-mismatch
class. The "ONE new error class per slice" discipline is the default;
exceeding it requires a spec-level lock.

Existing catalog (spot-check via
`rg "^class \w+Error" hirelens-backend/app/services/`):

| Service | Error classes |
|---|---|
| `quiz_item_study_service` | `QuizItemNotFoundError`, `QuizItemForbiddenError(reason='archived'\|'premium_deck')`, `QuizItemRetiredError`, `QuizItemNotVisibleError` |
| `admin_errors` (shared) | `DeckNotFoundError`, `DeckSlugConflictError`, `LessonNotFoundError`, `LessonSlugConflictError`, `LessonArchivedError`, `QuizItemNotFoundError`, `EditClassificationConflictError` |
| `seed_lessons_service` | `SeedLoadError` (base), `SlugMismatchError`, `UnexpectedH2SectionError`, `DuplicateQuestionHashError`, `MissingDeckMetaError` |
| `payment_service` | `PaymentError` (base), `InvalidSignatureError`, `UserNotFoundError`, `NotProSubscriberError` |
| `mission_service` | `MissionNotFoundError`, `MissionConflictError`, `MissionInvalidError(ValueError)`, `MissingGoneError` |
| `study_service` (legacy) | `CardNotFoundError`, `CardForbiddenError`, `DailyReviewLimitError` |
| `gpt_service` | `RewriteError`, `CoverLetterError` |
| `email_service` | `EmailSendError` |
| `gamification_service` | `InvalidXPSourceError(ValueError)` |
| `onboarding_checklist_service` | `WrongPersonaError` |

### Transaction patterns

Services own their session usage. Three patterns in flight:

- **Write paths that own the commit**: `db.add(row); await db.flush();
  await db.commit(); await db.refresh(row); return row`. Used by older
  services like `card_admin_service` and the auth flow.
- **Write paths that flush only**: `db.add(row); await db.flush()`.
  The `get_db` dependency's teardown commits as part of the request
  transaction (see `audit_admin_request` and the slice 6.4b admin
  services). Preferred for new routes — keeps the commit boundary at
  the request edge.
- **Savepoint-protected INSERTs**: `async with db.begin_nested(): ...`
  for partial-failure tolerance during bulk loads (slice 6.4.5
  `seed_lessons_service` D-10 — a single bad row aborts only its
  savepoint, not the whole load).

### Analytics emission

Emit **post-flush**, never pre-flush. The `quiz_item_reviewed` +
`quiz_item_progress_initialized` calls in `quiz_item_study_service.
review_quiz_item:514-551` are the canonical shape: compute the
properties dict once, then emit each event inside its own
`try/except Exception` so a `track()` failure cannot corrupt the
user-facing response (slice 6.0 D-7).

`app/core/analytics.track()` is itself defensive (silent no-op when
`POSTHOG_API_KEY` is unset); the per-call-site wrapper is structural
on top of that and intentional. Don't simplify it away.

For the Postgres dual-write pair (`quiz_review_events`,
`lesson_view_events`), call into `analytics_event_service.write_*`
inside a second `try/except` — see slice 6.0 §6.2 / I1 and the
emission shape at `quiz_item_study_service.review_quiz_item:553-575`.

## 2. Route handler conventions

### File location

- v1 routes: `app/api/v1/routes/<domain>.py`. New work goes here.
- Legacy routes: `app/api/routes/<domain>.py`. Read-only — only
  retained for backward-compat re-exports (`/api/...`). Don't add
  new endpoints there.

### Mount registration

In `app/main.py`, every v1 router is mounted with
`prefix="/api/v1"`, no per-router prefix:

```python
app.include_router(v1_lessons.router, prefix="/api/v1", tags=["v1 Lessons"])
```

Routes themselves declare paths starting at the resource
(`@router.get("/lessons/{lesson_id}")`). On-disk convention is
canonical; spec drift on this point (e.g. spec asking for
`prefix="/api/v1/decks"` on the router) was reconciled to disk during
slice 6.4b-1.

### Auth chain

- `Depends(get_current_user)` — required user. Default for any route
  serving user data. R3 (CLAUDE.md) makes this non-negotiable absent a
  tracked rationale.
- `Depends(get_current_user_optional)` — public/anonymous-tolerated
  routes that personalize when authed. Returns `None` instead of 401.
- `Depends(require_admin)` — chains `get_current_user`, then 403s
  non-admins.
- `Depends(audit_admin_request)` — chains `require_admin`, then writes
  one `admin_audit_log` row per request via `BackgroundTasks`.
  Attach at the **router level** for admin routers
  (`APIRouter(dependencies=[Depends(audit_admin_request)])`) so every
  route inherits without a per-handler decoration.
- `Depends(require_plan("pro"))` — plan-gated routes; reads the
  `subscriptions` row live (no plan claim in JWT).

### Error mapping

The route handler is the only place that maps service-layer errors
to HTTPException. Convention:

| Service error type | HTTP status |
|---|---|
| `*NotFoundError` | 404 |
| `*ForbiddenError` (archive guard, tier mismatch) | 403 |
| `*NotVisibleError` (persona mismatch) | 404 (info-leakage minimization, slice 6.5 §12 D-7) |
| `*RetiredError` | 409 |
| `*SlugConflictError` / `*ConflictError` | 409 |
| `*ArchivedError` (write against archived target) | 409 |
| `EditClassificationConflictError` | 409 (with structured `detail`) |

Preserve `str(exc)` as the detail body — service `__init__` already
formats the user-facing message. See
`app/api/v1/routes/lessons.py:38-47` and `admin_decks.py:38-78` for
canonical mappings.

### Response shapes

Pydantic v2 schemas in `app/schemas/<domain>.py`. Read schemas and
write schemas (Create/Update request bodies) live in the same file
(slice 6.4b-1 precedent). `response_model=` on the decorator drives
serialization; service layer returns the Pydantic model directly via
`.model_validate(orm_obj)` rather than a dict.

### Eager loading

Place `selectinload(...)` in the **service layer** at the query, not
in the route. The response schema's traversal pattern dictates which
relationships need eager loading — `lesson_service.get_lesson_with_
quizzes:106-112` shows the canonical shape (one `selectinload` per FK
chain the response walks). Slice 6.4 D-15 locked this convention.

## 3. Service ↔ route ↔ schema cross-references

### `user` threading

```
Depends(get_current_user)  →  user: User
                              ↓
service(domain_args, db, *, user=user)
                              ↓
SQL filter: Deck.persona_visibility.in_(_visible_persona_set(user))
SQL filter: Deck.tier.in_(_allowed_tiers_for_user(user))
```

Default `user=None` at the service layer keeps non-route callers
(scripts, fixtures) from needing to fabricate a User. Filters
collapse to the most-restrictive set when `user is None` (sees only
`'both'` persona, `'foundation'` tier).

### Cross-service calls

Services may call other services directly when one is structurally a
subroutine of the other (e.g.
`lesson_service.get_deck_lessons_bundle` calls `get_deck_with_meta` +
`list_lessons_in_deck` from the same module). Cross-module calls are
allowed but rare — circular-import risk is mitigated by importing
inside the calling function (`from app.models.subscription import
Subscription` inside `require_plan._check`) when the callee's module
graph would create a cycle at import time.

Importing error classes across services is the common cross-module
pattern (`from app.services.quiz_item_study_service import
QuizItemForbiddenError` in `lesson_service`). Errors are part of the
service contract and are stable across slices.

### Helper extraction (rule of three)

Duplicate a private helper into a second service when the second
consumer surfaces; promote to a shared module only on the third.
`_persona_visible_to` / `_visible_persona_set` /
`_allowed_tiers_for_user` are duplicated between
`quiz_item_study_service` and `lesson_service` per slice 6.5 D-5;
`deck_admin_service._PERSONA_EXPANSION` is the inverse direction
(deck → user-set, not user → deck-set) so the rule-of-three threshold
is not yet tripped.

## 4. Common gotchas

### `MissingGreenlet` on lazy-loaded relationships

SQLAlchemy 2.0 async raises `MissingGreenlet` when a sync function
body touches an unloaded relationship. Symptom: a service helper
that reads `user.subscription` throws inside a sync code path.

Fix: guard with `sqlalchemy.inspect(obj).unloaded` and short-circuit
to a sentinel rather than triggering the lazy load.
`quiz_item_study_service._resolve_plan:589-607` and
`lesson_service._resolve_plan:64-76` are the canonical pattern:

```python
state = inspect(user)
if "subscription" in state.unloaded:
    return None  # don't trigger lazy load
```

The alternative is to `selectinload(User.subscription)` at the
fetch site, but that couples every read path to the subscription
graph. The unloaded-guard keeps the analytics path opportunistic.

### Test fixture transaction scope

`tests/` uses two fixtures with different teardown semantics:

- `db_session` — rolls back on teardown. Right for service-layer
  tests that don't own `db.commit()`.
- `curriculum_db` (or `seed_db`, slice 6.4.5) — TRUNCATE-CASCADE
  teardown. Required when the service under test calls `db.commit()`
  or relies on visibility across nested transactions
  (`begin_nested` savepoint flush behavior).

Picking the wrong fixture is one of the top sources of "passes
locally, fails in CI" — slice 6.4.5 JC #6 codified this. Match the
fixture to whether the service owns the commit.

### Phantom error-class names

Always `rg "class <Name>Error" hirelens-backend/app/services/`
before naming an error class in a prompt or commit message. Spec
mappings (`§5`) are authoritative; chat memory can drift. Slice 6.5
JC #1 burned a roll because the prompt named
`ProDeckRequiresUpgradeError` — a class that does not exist on disk
and was never authored. Resolution: reuse
`QuizItemForbiddenError(reason='premium_deck')` per spec §5.

### CI invocation

Prod-default env vars are part of the contract. The canonical
invocation is:

```bash
FREE_DAILY_REVIEW_LIMIT=10 \
FREE_LIFETIME_SCAN_LIMIT=1 \
FREE_MONTHLY_INTERVIEW_LIMIT=3 \
python -m pytest tests/ -m "not integration" --tb=short
```

Tests that need a different free-tier limit must `monkeypatch.setenv`
inside the test, not assume a default. CR §11 item 20 tracks this.

### Integration-marker gating

Tests touching live LLM / embeddings / Stripe must be decorated
`@pytest.mark.integration` (R13). CI deselects them via
`-m "not integration"`. Run them locally before merging changes that
touch `gpt_service`, `experience_service`, `gap_mapping_service`, or
the `llm/` providers package.

### Don't add `pytest-cov`

Coverage is deliberately not installed (R13). Adding `--cov=` flags
without updating `requirements-dev.txt` and getting sign-off will
break CI silently — pytest treats the unknown flag as an error in
some plugins' load order.

## 5. Cross-references

- `study-engine.md` — FSRS scheduler details, daily-queue shape,
  card-rating API contract.
- `analytics.md` — full PostHog event catalog, Postgres dual-write
  contract, deprecated-event preservation rule.
- `admin-panel.md` — admin auth chain, audit-log row shape,
  admin-only event conventions, AI card generation.
- `database-schema.md` — column-level contracts, FK shapes, index
  inventory.
- `db-migration.md` — Alembic conventions, autogen vs handwritten,
  migration ordering.
- `testing.md` — test-file naming, fixture catalog, integration
  marker.
- `llm-strategy.md` — `generate_for_task` contract (R11), task-name
  registry, tier selection.
- `prd.md` — product surfaces and persona model.
- `skillforge_playbook_v2.md` — phase plan, slice cadence, spec
  template (§3.2).
