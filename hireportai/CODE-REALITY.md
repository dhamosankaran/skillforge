# CODE-REALITY — SkillForge / HirePort AI

> **Purpose:** frozen-in-time map of the codebase for off-disk advisors (chat-Claude) to draft accurate prompts. If the header sha below doesn't match `git rev-parse --short HEAD`, regenerate this file.
> **Read-only artifact.** Nothing here authorizes code changes.

---

## Section 1 — Repo metadata

| Field | Value |
|-------|-------|
| Commit sha (short) | `78abe56` (post-slice-6.4b-2 targeted regen — closes B-067). **This regen scope:** §1 + §3 + §4 + §6 + §7 + §11 + §13 (the 7 sections with deltas since `7621b88`); §2 / §5 / §8 / §9 / §10 / §12 carried forward verbatim per LD-5. **8-commit staleness gap from `7621b88`** (`4fce036` slice 6.4 spec slice 2/2 — §12 OQ→D locks + spec status flip → "Partially shipped" + §9 +1 event row, no CR touch; `aeef9a3` SHA backfill; `de1e9a9` slice 6.4 spec slice 3/3 — D-19 modal-copy N drop + D-16 unified→per-entity vocab + AC-19 SUPERSEDED → CR regen deferred to B-067, no CR touch; `f0693e8` SHA backfill; `d6bda3b` slice 6.4b-1 BE impl — 4 admin services + 3 admin routes + lesson_service body swap + fixture deletion; `049dc3a` SHA backfill + analytics.md +11 admin events + admin-panel.md catalog updates; `634f633` slice 6.4b-2 FE impl — 3 admin components + lessonEdit.ts util + 4 hooks + 4 editor pages + types/api.ts/App.tsx extensions; `1d4f4dc` SHA backfill); below the LD-1 ~10-commit threshold so targeted, not full. **Deltas this pass:** §1 counts (BE services 33→37 +4, v1 routers 21→24 +3, endpoints 73→86 +13, FE pages 23→26 +3, FE components 70→73 +3, FE utils 6→7 +1 lessonEdit.ts, FE hooks 12→16 +4, BE tests 510→555 +45 net per close-lines, FE tests 345→372 +27 per close-lines, FE test files 58→65 +7); §3 +13 admin write routes under `/api/v1/admin/{decks,lessons,quiz-items}` + 3 new router-file summary rows; §4 +3 admin services + `admin_errors.py` + `lesson_service.py` body-swap note (selectinload per spec §12 D-15); §6 fixture deletion note (`app/data/lesson_fixtures.py` + `__init__.py` removed at slice 6.4b-1) + component graph 70→73 (+admin/MarkdownEditor + admin/ConfirmCascadeModal + admin/ConfirmPersonaNarrowingModal) + FE utils row notes lessonEdit.ts; §7 +3 net new admin editor pages (AdminDeckDetail / AdminLessonEditor / AdminQuizItems) + 6.4a placeholders AdminDecks / AdminLessons rewritten with editor content; §11 drift items refresh (item 19 partial-shipped recommendation now resolved-via-shipping, item 20 mystery regression closed via env-var lens, item 21 D-026 process lesson reaffirmed; +1 NEW item 22 §8 lag — admin write-shape interfaces shipped at `634f633` not yet captured in §8 carried-forward block; JC #6 admin-panel.md catalog drift absorbed into this slice per recommendation (a)); §13 phase-6 row #04 status text refresh (slice 6.4b shipped — both halves now closed; spec body Status line still reads "Partially shipped" — needs flip in next legitimate spec edit, item 19 disposition updated). **Lineage chain closing the 8-commit gap from `7621b88`:** `17bf188` (§3 + §4 regen, 2026-04-26) → `7109542` (§1 + §2 + §5 regen, 2026-04-26) → `d5f3d17` (§6 + §7 + §8 + §9 + §10 + §11 + §12 + §13 regen, 2026-04-27, slice 6.3 final pass) → `f99a6b3` (§1 + §6 + §7 + §11 + §13 targeted, post-slice-6.4a) → `7621b88` (SHA backfill of f99a6b3) → `4fce036` / `aeef9a3` / `de1e9a9` / `f0693e8` (slice 6.4 spec slice 2/2 + slice 3/3 spec amendments + SHA backfills — no CR touch) → `d6bda3b` / `049dc3a` (slice 6.4b-1 BE impl + SHA backfill) → `634f633` / `1d4f4dc` (slice 6.4b-2 FE impl + SHA backfill) → THIS commit (§1 + §3 + §4 + §6 + §7 + §11 + §13 targeted, 2026-04-27, post-slice-6.4b-2). |
| Branch | `main` (43 commits ahead of `origin/main`; not yet pushed) |
| Generated | 2026-04-27 (targeted regen, 7 of 13 sections — §1, §3, §4, §6, §7, §11, §13). LD-1 from B-049: targeted regen since gap = 8 commits, well below ~10 threshold; deltas bounded to slice 6.4 family (admin authoring BE/FE + spec amendments + SHA backfills) so targeted scope mirrors B-066 precedent. LD-2: counts via filesystem enumeration (`find` / `wc`, not estimation). LD-3: ambiguous fields flagged "unknown — flag for next regen" rather than guessed. LD-5: section content replaced (in scope) / carried forward verbatim (out of scope). |
| Backend model files | 23 (`app/models/*.py`, excl. `__init__`, `request_models`, `response_models`) — **unchanged since `7621b88`**. Verified via `find hirelens-backend/app/models -maxdepth 1 -name "*.py" -not -name "__init__.py" -not -name "request_models.py" -not -name "response_models.py" \| wc -l = 23`. (Slice 6.4b is a CRUD slice — admin write paths reuse the existing slice-6.1 `decks` / `lessons` / `quiz_items` / `quiz_item_progress` tables; no schema changes.) |
| Backend service files | 37 functional top-level (in `app/services/`, excl. `__init__.py`) + 3 under `services/llm/` = 40 — **+4 since prior regen**: `deck_admin_service.py` + `lesson_admin_service.py` + `quiz_item_admin_service.py` + `admin_errors.py` (all slice 6.4b-1, `d6bda3b`). `lesson_service.py` body-swap (slice 6.4b-1) NOT a file-count delta — same file, same exports; bodies of 4 functions swap from `lesson_fixtures` calls to DB queries with `selectinload(Lesson.quiz_items)` + `selectinload(Lesson.deck)` per spec §12 D-15 (signatures + response shapes byte-identical per D-2). Verified via `find hirelens-backend/app/services -maxdepth 1 -name "*.py" -not -name "__init__.py" \| wc -l = 37`. |
| Backend router files | 24 v1 + 6 legacy = 30 — **+3 since prior regen** (all v1): `admin_decks.py` + `admin_lessons.py` + `admin_quiz_items.py` (Phase 6 slice 6.4b-1, `d6bda3b`). Verified via `find hirelens-backend/app/api/v1/routes -name "*.py" -not -name "__init__.py" \| wc -l = 24`. |
| Backend endpoints (total) | **86 mount-point appearances** in §3 flat endpoint table — **+13 since prior regen** (all from slice 6.4b-1: 4 admin_decks + 5 admin_lessons + 4 admin_quiz_items, decorator counts verified via `grep -cE '^@router\.(get\|post\|put\|patch\|delete)'`). Two valid count conventions in this codebase: **(a) mount-point count = 86** (each row in §3 flat table, counts re-export double-mounts: `/api/analyze` + `/api/v1/analyze` count as 2); **(b) decorator-source count = 80** (`grep -rcE '^@router\.(get\|post\|put\|patch\|delete)'` over `hirelens-backend/app/api/`, counts unique decorator definitions; the 4 v1 re-export router files at `app/api/v1/routes/{analyze,cover_letter,interview,rewrite}.py` contribute 0 because they `from app.api.routes.X import router`). The flat-table convention (mount-point) is what users see at runtime, so this row tracks (a). The 4 re-export shims double-mount 6 paths (12 mount points; net delta from re-exports = +6 mount points beyond the decorator-source count). |
| Alembic revisions | 26 (Head = `57951e9f4cdc`) — **unchanged since prior regen**. Slice 6.4b is CRUD-only against existing slice-6.1 tables; no migration. Verified via `find hirelens-backend/alembic/versions -name "*.py" \| wc -l = 26`. |
| Frontend pages | 26 — **+3 since prior §1 anchor `7621b88`**: slice 6.4b-2 (`634f633`) added `pages/admin/AdminDeckDetail.tsx` + `pages/admin/AdminLessonEditor.tsx` + `pages/admin/AdminQuizItems.tsx`. Slice 6.4b-2 also rewrote `pages/admin/AdminDecks.tsx` + `pages/admin/AdminLessons.tsx` (overwriting the 6.4a "Coming in slice 6.4b" placeholders with actual editor content) — same file count, content replaced. Verified via `find hirelens-frontend/src/pages -name "*.tsx" -not -path "*/__tests__/*" \| wc -l = 26`. |
| Frontend components | 73 (excl. `__tests__/*`) — **+3 since prior §1 anchor `7621b88`**: slice 6.4b-2 (`634f633`) added `admin/MarkdownEditor.tsx` + `admin/ConfirmCascadeModal.tsx` + `admin/ConfirmPersonaNarrowingModal.tsx`. `find hirelens-frontend/src/components -name "*.tsx" -not -path "*/__tests__/*" \| wc -l = 73`. |
| Frontend utils (NEW) | `src/utils/wallCountdown.ts` (B-059, `20562ea`) + **`src/utils/lessonEdit.ts`** *(NEW — Phase 6 slice 6.4b-2, `634f633`. Exports `classifyEdit(before: string, after: string) → 'minor' \| 'substantive'` + `classifyLessonEdit(before, after)` aggregating across `concept_md` / `production_md` / `examples_md`. Pure-JS Levenshtein implementation (~30 lines, zero new deps per JC #1 — neither `fast-diff` nor `diff-match-patch` was a transitive dep). `SUBSTANTIVE_EDIT_THRESHOLD = 0.15` constant matches BE `app/services/admin_errors.py`. Advisory-only — BE re-validates per spec §7.1 + 409 `EditClassificationConflictError` is the authoritative gate. JSDoc divergence note documents Levenshtein vs BE `difflib.SequenceMatcher.ratio()` edge-case disagreements (transpositions, boundary inserts).)* — total 7 utility .ts files (verified via `find hirelens-frontend/src/utils -name "*.ts" -not -path "*/__tests__/*" \| wc -l = 7`). |
| Shared TS types | `src/types/index.ts` (~400 lines + 8 admin write-shape interfaces shipped at slice 6.4b-2 `634f633`: `DeckCreateRequest` / `DeckUpdateRequest` / `LessonCreateRequest` / `LessonUpdateRequest` / `LessonUpdateResponse` / `QuizItemCreateRequest` / `QuizItemUpdateRequest` / `EditClassification` literal + 3 per-entity `Admin*StatusFilter` aliases per D-16; **§8 table block carried forward verbatim from prior regen and does NOT yet enumerate these new types — see §11 NEW item 22 for the §8 lag note**) + `src/types/homeState.ts` (28 lines, unchanged) |
| Frontend hooks | 16 (`src/hooks/*.ts`, excl. `__tests__`) — **+4 since prior §1 anchor `7621b88`**: slice 6.4b-2 (`634f633`) added `useAdminDecks.ts` + `useAdminDeckDetail.ts` + `useAdminLessonEditor.ts` + `useAdminQuizItems.ts` (one hook per editor page; per JC #3/#4 from slice 6.4b-2 entry, lesson + deck resolved via paged admin-LIST since the slice ships no single-record admin GET). Verified via `find hirelens-frontend/src/hooks -name "*.ts" -not -path "*/__tests__/*" \| wc -l = 16`. |
| Skills (tracked) | 20 in `.agent/skills/*.md` — **unchanged file count since prior regen**. Slice 6.4b-1's SHA backfill commit (`049dc3a`) edited two existing skill files: `analytics.md` +11 admin event rows (`admin_deck_created` / `admin_deck_updated` / `admin_deck_archived` / `admin_deck_persona_narrowed` / `admin_lesson_created` / `admin_lesson_updated_minor` / `admin_lesson_substantively_edited` / `admin_lesson_published` / `admin_lesson_archived` / `admin_quiz_item_created` / `admin_quiz_item_retired`; all `internal: true` per admin-panel skill convention) + `admin-panel.md` Key Files block + admin-only PostHog event list extended for the same 11 events. **THIS slice (6.4b-3) absorbs JC #6 sweep:** refreshes `admin-panel.md` Key Files **Frontend** block — drops `pages/AdminPanel.tsx` (deleted slice 6.4a) + `pages/AdminAudit.tsx` (never shipped per §12 D-14) + adds 4 new admin editor pages (AdminDecks / AdminDeckDetail / AdminLessonEditor / AdminQuizItems) + 3 new admin components (MarkdownEditor / ConfirmCascadeModal / ConfirmPersonaNarrowingModal) + `lessonEdit.ts` utility reference. |
| Skills (untracked, not committed) | 3 directory-style under `.agent/skills/` — `stripe-best-practices/`, `stripe-projects/`, `upgrade-stripe/` (each contains `SKILL.md` and optionally `references/`); not in git, source unknown — see §10 |
| Specs | 84 across 7 phases (phase-0=6, phase-1=13, phase-2=8, phase-3=11, phase-4=6, phase-5=36, phase-6=4) — see §13. **Spec count unchanged since prior regen**; phase-6 row #04 (`04-admin-authoring.md`) accumulated 2 spec amendments (`4fce036` slice 6.4 spec slice 2/2 — §12 D-15..D-19 lock + status flip "Drafted" → "Partially shipped"; `de1e9a9` slice 6.4 spec slice 3/3 — D-16 per-entity vocab + D-19 modal-copy N drop + AC-19 SUPERSEDED) but is the same file. Phase-5 unchanged at 36. |
| Tests | BE **555** (was 510 at prior §1 anchor; net `+45`: slice 6.4 spec slice 2/2 baseline established 520 with production-default env vars `FREE_DAILY_REVIEW_LIMIT=10 FREE_LIFETIME_SCAN_LIMIT=1 FREE_MONTHLY_INTERVIEW_LIMIT=3` — closes the prior 520→510 mystery regression flag at §11 drift item 20 by recognizing it was env-var-dependent baseline drift, not a code regression; slice 6.4b-1 added +35 across 4 new test files: `test_admin_decks_routes.py` (+9) + `test_admin_lessons_routes.py` (+11) + `test_admin_quiz_items_routes.py` (+8) + `test_lesson_service_db_query.py` (+14, replacing 7-test `test_lesson_fixtures_routes.py` for net +7 from rename + +7 net new DB-seeded variants). Slice 6.4b-2 added 0 (FE-only). Without env vars, 10 pre-existing failures may surface — same set tracked at slice 6.4 spec author baseline note; not investigated this regen). FE **372** (was 345; net `+27`: slice 6.4b-2 added 7 new test files — `tests/admin/{AdminDecks,AdminDeckDetail,AdminLessonEditor,AdminQuizItems}.test.tsx` (+17) + `tests/components/admin/{ConfirmCascadeModal,ConfirmPersonaNarrowingModal}.test.tsx` (+5) + `tests/utils/lessonEdit.test.ts` (+5)). FE test-file count 58 → 65 (+7). Counts per close-lines; not re-run this slice (R14 exception (a), doc-only). |

---

## Section 2 — Backend models

### `admin_audit_log.py`
**Class:** `AdminAuditLog`  **Table:** `admin_audit_log`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| admin_id | String (FK `users.id` ON DELETE RESTRICT, indexed) | NOT NULL |
| route | String(255) | NOT NULL |
| method | String(10) | NOT NULL |
| query_params | JSONB | NOT NULL, server default `{}` |
| ip_address | String(45) | NOT NULL |
| created_at | DateTime(timezone=True) | NOT NULL, server default `now()` (indexed) |

**Indexes:** `ix_admin_audit_admin_created` on `(admin_id, created_at)`, `ix_admin_audit_route_created` on `(route, created_at)` — serve the two common audit-trail read patterns (per-admin trail, per-endpoint trail) used by `/api/v1/admin/audit`.

**Relationships:** none declared. `admin_id` ON DELETE RESTRICT is a forensic guardrail — a user row with audit history cannot be deleted without first purging audit rows.

Purpose: append-only audit trail for every admin-scoped HTTP request. Written via `core.deps.audit_admin_request` (router-level dep on `/api/v1/admin/*`). Also written by `auth.py::_log_role_reconciliation` on admin role promote/demote events (spec #54 E-040). Spec: `docs/specs/phase-5/38-admin-analytics.md`.

### `base.py`
**Mixins only:** `TimestampMixin` (`created_at`, `updated_at` via `func.now()` + `onupdate`), `UUIDPrimaryKeyMixin` (`id` UUID default `uuid.uuid4()`). No models.

### `card.py`
**Class:** `Card`  **Table:** `cards`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| category_id | String (FK `categories.id`) | NOT NULL |
| question | Text | NOT NULL |
| answer | Text | NOT NULL |
| difficulty | String(10) | NOT NULL |
| tags | JSON | NOT NULL, default: `[]` |
| embedding | Vector(1536) | nullable |
| deleted_at | DateTime | nullable (soft-delete) |
| created_at / updated_at | DateTime | NOT NULL |

**Relationships:** `category → Category` (back_populates `cards`).

### `card_feedback.py`
**Class:** `CardFeedback`  **Table:** `card_feedback`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| card_id | String (FK `cards.id`) | NOT NULL |
| vote | String(4) | NOT NULL |
| comment | Text | nullable |
| created_at | DateTime | NOT NULL |

**Relationships:** `user → User`, `card → Card`.

### `card_progress.py`
**Class:** `CardProgress`  **Table:** `card_progress`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| card_id | String (FK `cards.id`) | NOT NULL |
| state | String(20) | NOT NULL, default: `"new"` |
| stability | Float | NOT NULL, default: `0.0` |
| difficulty_fsrs | Float | NOT NULL, default: `0.0` |
| elapsed_days | Float | NOT NULL, default: `0.0` |
| scheduled_days | Float | NOT NULL, default: `0.0` |
| reps | Integer | NOT NULL, default: `0` |
| lapses | Integer | NOT NULL, default: `0` |
| fsrs_step | Integer | nullable |
| last_reviewed | DateTime | nullable |
| due_date | DateTime | NOT NULL, default: `now()` |
| created_at / updated_at | DateTime | NOT NULL |

**Unique:** `(user_id, card_id)`. **Relationships:** `user → User`, `card → Card`.

### `category.py`
**Class:** `Category`  **Table:** `categories`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| name | String(100) unique | NOT NULL |
| icon | String(10) | NOT NULL |
| color | String(30) | NOT NULL |
| display_order | Integer | NOT NULL, default: `0` |
| source | String(50) | nullable (`foundation` / `premium`) |
| tags | JSONB | NOT NULL, default: `[]` |

**Relationships:** `cards → list[Card]` (back_populates `category`).

### `deck.py`
**Class:** `Deck`  **Table:** `decks`  *(NEW — Phase 6 slice 6.1, `a989539`. Top-level curriculum bucket; replaces the role of `categories` for Phase 6 content. Spec: `docs/specs/phase-6/01-foundation-schema.md` §4.1.)*

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| slug | String(100) unique | NOT NULL |
| title | String(200) | NOT NULL |
| description | Text | NOT NULL |
| display_order | Integer | NOT NULL, default `0`, server default `"0"` |
| icon | String(10) | nullable |
| persona_visibility | String(20) | NOT NULL, default `"both"`, server default `"both"` *(ENUM-as-String per D-3: `'climber' \| 'interview_prepper' \| 'both'`)* |
| tier | String(20) | NOT NULL, default `"premium"`, server default `"premium"` *(ENUM-as-String per D-3: `'foundation' \| 'premium'`)* |
| created_at | DateTime(timezone=True) | NOT NULL, server default `now()` |
| updated_at | DateTime(timezone=True) | NOT NULL, server default `now()`, on update `now()` |
| archived_at | DateTime(timezone=True) | nullable *(soft-delete)* |

**Indexes:** `ix_decks_persona_display_active` on `(persona_visibility, display_order)` `WHERE archived_at IS NULL` — partial index for the Learn-page primary query (visible decks for a persona in display order).

**Relationships:** `lessons → list[Lesson]` (back_populates `deck`, lazy=`select`).

### `email_preference.py`
**Class:** `EmailPreference`  **Table:** `email_preferences`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| user_id | String (PK, FK `users.id`) | NOT NULL |
| daily_reminder | Boolean | NOT NULL, default: `True` |
| timezone | String(50) | NOT NULL, default: `"UTC"` |
| unsubscribe_token | String(64) unique | NOT NULL, default: `secrets.token_hex(32)` |
| created_at / updated_at | DateTime | NOT NULL |

**Relationships:** `user → User`.

### `gamification.py`
Three models in one module.

**`GamificationStats`  Table:** `gamification_stats`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| user_id | String (PK, FK `users.id`) | NOT NULL |
| current_streak | Integer | NOT NULL, default: `0` |
| longest_streak | Integer | NOT NULL, default: `0` |
| total_xp | Integer | NOT NULL, default: `0` |
| last_active_date | Date | nullable |
| freezes_available | Integer | NOT NULL, default: `0` |
| freeze_week_start | Date | nullable |
| created_at / updated_at | DateTime | NOT NULL |

**`Badge`  Table:** `badges`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | String(64) (PK) | — |
| name | String(128) | NOT NULL |
| description | String(512) | NOT NULL |
| threshold_type | String(32) | NOT NULL |
| threshold_value | Integer | NOT NULL, default: `0` |
| created_at | DateTime | NOT NULL |

**`UserBadge`  Table:** `user_badges`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| badge_id | String (FK `badges.id`) | NOT NULL |
| earned_at | DateTime | NOT NULL, default: `now()` |

**Unique:** `(user_id, badge_id)`. **Relationships:** `UserBadge.badge → Badge`.

### `interview_question_set.py`
**Class:** `InterviewQuestionSet`  **Table:** `interview_question_sets`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| jd_hash | String(64) | NOT NULL |
| jd_text | Text | NOT NULL |
| questions | JSONB | NOT NULL |
| generated_at | DateTime | NOT NULL, default: `now()` |
| model_used | String(50) | nullable |

**Unique:** `(user_id, jd_hash)`.

### `lesson.py`
**Class:** `Lesson`  **Table:** `lessons`  *(NEW — Phase 6 slice 6.1, `a989539`. Unit of teaching content; one lesson = one card on the Learn page (concept + production + examples + quiz panel). Spec: `docs/specs/phase-6/01-foundation-schema.md` §4.2.)*

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| deck_id | String(36) (FK `decks.id` ON DELETE RESTRICT, indexed) | NOT NULL |
| slug | String(100) | NOT NULL |
| title | String(200) | NOT NULL |
| concept_md | Text | NOT NULL |
| production_md | Text | NOT NULL |
| examples_md | Text | NOT NULL |
| display_order | Integer | NOT NULL, default `0`, server default `"0"` |
| version | Integer | NOT NULL, default `1`, server default `"1"` |
| version_type | String(20) | NOT NULL, default `"initial"`, server default `"initial"` *(ENUM-as-String per D-3: `'initial' \| 'minor_edit' \| 'substantive_edit'`)* |
| published_at | DateTime(timezone=True) | nullable *(NULL = draft)* |
| generated_by_model | String(64) | nullable |
| source_content_id | String(36) | nullable, **NO FK constraint** *(D-2: target table `source_content` is created in slice 6.9; the FK is added in 6.9's migration once the target exists)* |
| quality_score | Numeric(3,2) | nullable *(D-4: deterministic rounding for product analytics)* |
| created_at | DateTime(timezone=True) | NOT NULL, server default `now()` |
| updated_at | DateTime(timezone=True) | NOT NULL, server default `now()`, on update `now()` |
| archived_at | DateTime(timezone=True) | nullable *(soft-delete)* |

**Unique:** `(deck_id, slug)` named `uq_lessons_deck_slug`.

**Indexes:** `ix_lessons_deck_display_active` on `(deck_id, display_order)` `WHERE archived_at IS NULL` (deck-detail primary query); `ix_lessons_review_queue` on `(published_at)` `WHERE published_at IS NULL` (admin review queue); `ix_lessons_deck_archived` on `(deck_id, archived_at)`; `ix_lessons_source_content` on `(source_content_id)` (slice 6.9 forward-link queries).

**Relationships:** `deck → Deck` (back_populates `lessons`, lazy=`select`); `quiz_items → list[QuizItem]` (back_populates `lesson`, lazy=`select`).

### `mission.py`
Two models + one secondary table (`mission_categories`).

**`Mission`  Table:** `missions`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| title | String(200) | NOT NULL |
| target_date | Date | NOT NULL |
| daily_target | Integer | NOT NULL |
| status | String(20) | NOT NULL, default: `"active"` |
| created_at / updated_at | DateTime | NOT NULL |

**Relationships:** `user → User`, `categories → list[Category]` (secondary `mission_categories`), `days → list[MissionDay]` (back_populates `mission`).

**`MissionDay`  Table:** `mission_days`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| mission_id | String (FK `missions.id`) | NOT NULL |
| day_number | Integer | NOT NULL |
| date | Date | NOT NULL |
| cards_target | Integer | NOT NULL |
| cards_completed | Integer | NOT NULL, default: `0` |

**Unique:** `(mission_id, day_number)`, `(mission_id, date)`.

### `payment.py`
**Class:** `Payment`  **Table:** `payments`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| stripe_payment_intent_id | String(255) unique | NOT NULL |
| amount | Integer | NOT NULL |
| currency | String(3) | NOT NULL, default: `"usd"` |
| status | String(30) | NOT NULL |
| created_at | DateTime | NOT NULL |

### `paywall_dismissal.py`
**Class:** `PaywallDismissal`  **Table:** `paywall_dismissals`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id` ON DELETE CASCADE) | NOT NULL |
| trigger | String(64) | NOT NULL |
| dismissed_at | DateTime(timezone=True) | NOT NULL, server default `now()` |
| action_count_at_dismissal | Integer | nullable (telemetry only) |

**Indexes:** `ix_paywall_dismissals_user_trigger_time` on `(user_id, trigger, dismissed_at)` — serves the 60s LD-8 dedup read and the "dismissal exists?" check inside `paywall_service.should_show_paywall`.

**Relationships:** none (no back_populates — `User` does not expose a `dismissals` collection; the table is read/written exclusively through `paywall_service`).

Purpose: append-only log of user paywall dismissals. Consumed by `paywall_service` (see §4) to drive the per-trigger 3-attempt grace window. Win-back consumption is deferred (BACKLOG E-031). Spec: `docs/specs/phase-5/42-paywall-dismissal.md`.

### `quiz_item.py`
**Class:** `QuizItem`  **Table:** `quiz_items`  *(NEW — Phase 6 slice 6.1, `a989539`. Atomic FSRS-reviewable recall unit; a lesson has 1+ quiz_items. Substantive edits retire the row (set `retired_at`, link `superseded_by_id` to the new row) — keeps FSRS state on the OLD row queryable for analytics while preventing new progress rows. The "no new quiz_item_progress rows against retired quiz_items" invariant is enforced at the service layer (slice 6.5 / shipped early in 6.2's `quiz_item_study_service`), NOT via DB constraint. Spec: `docs/specs/phase-6/01-foundation-schema.md` §4.3.)*

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| lesson_id | String(36) (FK `lessons.id` ON DELETE CASCADE, indexed) | NOT NULL |
| question | Text | NOT NULL |
| answer | Text | NOT NULL |
| question_type | String(20) | NOT NULL, default `"free_text"`, server default `"free_text"` *(ENUM-as-String per D-3: `'mcq' \| 'free_text' \| 'code_completion'`)* |
| distractors | JSONB | nullable |
| difficulty | String(10) | NOT NULL, default `"medium"`, server default `"medium"` *(ENUM-as-String per D-3: `'easy' \| 'medium' \| 'hard'` — authored hint, not FSRS-managed difficulty)* |
| display_order | Integer | NOT NULL, default `0`, server default `"0"` |
| version | Integer | NOT NULL, default `1`, server default `"1"` |
| superseded_by_id | String(36) (self-ref FK `quiz_items.id` ON DELETE SET NULL) | nullable *(AC-4: old row → new row when a substantive edit fires)* |
| retired_at | DateTime(timezone=True) | nullable *(soft-retire)* |
| generated_by_model | String(64) | nullable |
| created_at | DateTime(timezone=True) | NOT NULL, server default `now()` |
| updated_at | DateTime(timezone=True) | NOT NULL, server default `now()`, on update `now()` |

**Indexes:** `ix_quiz_items_lesson_active_order` on `(lesson_id, display_order)` `WHERE retired_at IS NULL` (active-quiz lookup primary query); `ix_quiz_items_superseded_by` on `(superseded_by_id)` (forward-linkage queries).

**Relationships:** `lesson → Lesson` (back_populates `quiz_items`, lazy=`select`).

### `quiz_item_progress.py`
**Class:** `QuizItemProgress`  **Table:** `quiz_item_progress`  *(NEW — Phase 6 slice 6.1, `a989539`. Per-user FSRS scheduling state for each quiz_item. Direct analog of `card_progress` with the FK retargeted from `cards` to `quiz_items` — column shape is **byte-identical** to `card_progress` modulo the FK swap (D-1 + AC-6, verified by `tests/test_phase6_schema.py::test_quiz_item_progress_mirrors_card_progress`). This intentional symmetry lets `quiz_item_study_service` (slice 6.2) port `study_service`'s FSRS reconstruction logic verbatim. Spec: `docs/specs/phase-6/01-foundation-schema.md` §4.4.)*

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String(36) (FK `users.id` ON DELETE CASCADE, indexed) | NOT NULL |
| quiz_item_id | String(36) (FK `quiz_items.id` ON DELETE CASCADE, indexed) | NOT NULL |
| state | String(20) | NOT NULL, default `"new"`, server default `"new"` *(`new \| learning \| review \| relearning`)* |
| stability | Float | NOT NULL, default `0.0`, server default `"0.0"` |
| difficulty_fsrs | Float | NOT NULL, default `0.0`, server default `"0.0"` |
| elapsed_days | Float | NOT NULL, default `0.0`, server default `"0.0"` |
| scheduled_days | Float | NOT NULL, default `0.0`, server default `"0.0"` |
| reps | Integer | NOT NULL, default `0`, server default `"0"` |
| lapses | Integer | NOT NULL, default `0`, server default `"0"` |
| fsrs_step | Integer | nullable *(py-fsrs v6 learning/relearning step index; None when in Review state)* |
| last_reviewed | DateTime(timezone=True) | nullable |
| due_date | DateTime(timezone=True) | NOT NULL, server default `now()` *(D-1: NOT NULL with `server_default=now()` mirrors `card_progress.due_date` so the daily-review WHERE clause `due_date <= now` needs no null branch)* |
| created_at / updated_at | DateTime(timezone=True) | NOT NULL |

**Unique:** `(user_id, quiz_item_id)` named `uq_quiz_item_progress_user_quiz` (mirrors `uq_card_progress_user_card`).

**Indexes:** `ix_quiz_item_progress_user_due` on `(user_id, due_date)` (daily-review primary query, mirrors `card_progress` index pattern); `ix_quiz_item_progress_quiz_item` on `(quiz_item_id)` (per-quiz reviewer / analytics lookups).

**Relationships:** `user → User` (lazy=`select`); `quiz_item → QuizItem` (lazy=`select`). No back_populates collection on `User` or `QuizItem` — service-layer access only.

### `registration_log.py`
**Class:** `RegistrationLog`  **Table:** `registration_logs`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| ip_address | String(45) | NOT NULL (indexed) |
| google_email | String(320) | NOT NULL |
| created_at | DateTime | NOT NULL (indexed) |

### `resume_model.py`
**Class:** `Resume`  **Table:** `resumes`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL |
| original_content | Text | NOT NULL |
| optimized_content | Text | nullable |
| template_type | String(50) | nullable |
| embedding | Vector(1536) | nullable |
| created_at / updated_at | DateTime | NOT NULL |

**Relationships:** `user → User` (back_populates `resumes`).

### `stripe_event.py`
**Class:** `StripeEvent`  **Table:** `stripe_events`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | String(255) (PK — Stripe `evt_…` id) | — |
| event_type | String(100) | NOT NULL |
| processed_at | DateTime | NOT NULL |
| created_at | DateTime | NOT NULL |

### `subscription.py`
**Class:** `Subscription`  **Table:** `subscriptions`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) unique | NOT NULL |
| plan | String(20) | NOT NULL, default: `"free"` |
| status | String(20) | NOT NULL, default: `"active"` |
| stripe_customer_id | String(255) unique | nullable |
| stripe_subscription_id | String(255) unique | nullable |
| current_period_end | DateTime | nullable |
| created_at / updated_at | DateTime | NOT NULL |

**Relationships:** `user → User` (uselist=False).

### `tracker.py`
**Class:** `TrackerApplicationModel`  **Table:** `tracker_applications_v2`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | nullable |
| company | String(200) | NOT NULL |
| role | String(200) | NOT NULL |
| date_applied | String(20) | NOT NULL |
| ats_score | Integer | NOT NULL, default: `0` |
| status | String(20) | NOT NULL, default: `"Applied"` |
| scan_id | String(36) | nullable, indexed |
| skills_matched | Text | nullable |
| skills_missing | Text | nullable |
| **interview_date** | **Date** | **nullable** *(NEW since prior regen — alembic `9543aa466524`, E-042-impl-BE; partial index `ix_tracker_apps_user_interview_date` on `(user_id, interview_date)`. Backfilled from `users.interview_target_date` via `eb59d4fc1f7e`. FE consumers pending — `home_state_service.get_next_interview` reads this; CountdownWidget + MissionDateGate still read `user.interview_target_date`)* |
| **analysis_payload** | **JSONB** | **nullable, deferred-load** *(NEW since prior regen — alembic `30bf39fa04f8`, B-035 / spec #59; persists the full `AnalysisResponse` JSON for `/prep/results?scan_id=...` hydration. Declared with `sqlalchemy.orm.deferred()` so `GET /tracker` list responses do not inflate. Read via `GET /api/v1/analyze/{scan_id}` 200/410/404 ownership-checked endpoint)* |
| created_at | DateTime | NOT NULL |

**No `jd_hash` column** (see §11 drift flag). **Relationships:** `user → User | None` (back_populates `tracker_applications`).

### `usage_log.py`
**Class:** `UsageLog`  **Table:** `usage_logs`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| user_id | String (FK `users.id`) | NOT NULL (indexed) |
| feature_used | String(100) | NOT NULL |
| tokens_consumed | Integer | NOT NULL, default: `0` |
| created_at | DateTime | NOT NULL (indexed) |

**Relationships:** `user → User` (back_populates `usage_logs`).

### `user.py`
**Class:** `User`  **Table:** `users`

| Column | Type | Nullable / Default |
|--------|------|--------------------|
| id | UUID (PK) | — |
| google_id | String(255) unique | NOT NULL |
| email | String(320) unique | NOT NULL |
| name | String(255) | NOT NULL |
| avatar_url | String(2048) | nullable |
| role | String(20) | NOT NULL, default: `"user"` |
| persona | String(30) | nullable (3-value enum in code) |
| onboarding_completed | Boolean | NOT NULL, default: `False` |
| interview_target_company | String(100) | nullable |
| interview_target_date | Date | nullable *(deprecation pending — E-042 moves the canonical target to `tracker_applications_v2.interview_date`; user-level field stays for read compat until FE migrates per E-042 Phase-6 cleanup)* |
| downgraded_at | DateTime(timezone=True) | nullable, default `None` (set by `customer.subscription.deleted` webhook per spec #42 LD-5; dormant until win-back slice E-031 activates) |
| home_first_visit_seen_at | DateTime(timezone=True) | nullable, default `None` (B-016; stamped on first `/home` load via idempotent `POST /api/v1/users/me/home-first-visit`; flips greeting copy "Welcome" → "Welcome back". B-027 patched the FE to snapshot on mount so in-mount stamp doesn't flip the rendered copy within a single session) |
| created_at | DateTime | NOT NULL |

**Relationships:** `subscription → Subscription` (uselist=False), `resumes → list[Resume]`, `usage_logs → list[UsageLog]`, `tracker_applications → list[TrackerApplicationModel]`.

> `UsageLimit` (plan × feature cap) is referenced in AGENTS.md but **no model file exists** on disk; see §11 drift #6.

---

## Section 3 — Backend routes

Both `/api/*` (legacy) and `/api/v1/*` (authoritative) are mounted in `app/main.py`. Router files define paths directly on decorators (no `APIRouter(prefix=...)`), so the full effective path is `prefix` + decorator path. The v1 mounts for `analyze`, `cover_letter`, `interview`, `rewrite` are **re-export shims** (`from app.api.routes.X import router`), so the same handler appears at both `/api/X` and `/api/v1/X` and any change to the legacy file changes both endpoints.

### Router-file summary

| Effective mount | File | Endpoints | Auth deps observed |
|-----------------|------|-----------|---------------------|
| `/api/analyze` | `app/api/routes/analyze.py` | 2 | `get_current_user_optional` *(new since prior regen: `GET /analyze/{scan_id}` for B-035 scan hydration)* |
| `/api/cover-letter` | `app/api/routes/cover_letter.py` | 1 | `get_current_user` *(spec #58 / B-033 — 402 on cap hit, `cover_letter_limit` trigger)* |
| `/api/interview-prep` | `app/api/routes/interview.py` | 1 | `get_current_user_optional` |
| `/api/rewrite` | `app/api/routes/rewrite.py` | 2 | `get_current_user` *(spec #58 / B-033 — shared `"rewrite"` bucket for `/rewrite` and `/rewrite/section`, `rewrite_limit` trigger)* |
| `/api/v1/onboarding` | `app/api/routes/onboarding.py` *(legacy folder, v1 mount)* | 2 | `get_current_user` |
| `/api/v1/payments` | `app/api/routes/payments.py` *(legacy folder, v1 mount)* | 7 | `get_current_user` (5), none (2) |
| `/api/v1/admin` | `app/api/v1/routes/admin.py` | 9 | `audit_admin_request` (router-level, chains `require_admin`) |
| `/api/v1/admin/analytics` | `app/api/v1/routes/admin_analytics.py` | 2 | `audit_admin_request` (router-level, chains `require_admin`) |
| `/api/v1/admin/decks` | `app/api/v1/routes/admin_decks.py` | 4 | `audit_admin_request` (router-level, chains `require_admin`) *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Mounted via `app.include_router(v1_admin_decks.router, prefix="/api/v1", tags=["v1 Admin Decks"])` — per-router `prefix` is `/api/v1` not `/api/v1/admin`; absolute `/admin/decks/...` paths in route decorators per on-disk convention (matches `admin.py` + `admin_analytics.py`). Endpoints: POST create / PATCH update (with persona-narrowing detection) / POST archive (idempotent) / GET admin-LIST `?status=active|archived|all` per spec §12 D-16.)* |
| `/api/v1/admin/lessons` | `app/api/v1/routes/admin_lessons.py` | 5 | `audit_admin_request` (router-level, chains `require_admin`) *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Endpoints: POST create / GET admin-LIST `?status=active|drafts|published|archived|all` per D-16 / PATCH update (with substantive-edit cascade-retire of active quiz_items per spec §7.3 D-18; 409 `EditClassificationConflictError` when payload `edit_classification` disagrees with server `_classify` result per spec §7.1) / POST publish (sets `published_at`, idempotent on re-publish) / POST archive (sets `archived_at`, no cascade-retire per D-18 / spec §7.5).)* |
| `/api/v1/admin/quiz-items` | `app/api/v1/routes/admin_quiz_items.py` | 4 | `audit_admin_request` (router-level, chains `require_admin`) *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Endpoints: POST create / GET admin-LIST per-lesson `?status=active|retired|all` per D-16 / PATCH update (substantive → retire-and-replace: insert new `version+1` row, set `old.superseded_by_id = new.id`, set `old.retired_at = now()`; minor → in-place per D-18) / POST retire (idempotent; preserves existing `quiz_item_progress` rows per slice 6.2 §4.6 D-4).)* |
| `/api/v1/analyze` | `app/api/v1/routes/analyze.py` *(re-exports legacy)* | 2 | `get_current_user_optional` |
| `/api/v1/auth` | `app/api/v1/routes/auth.py` | 4 | `get_current_user` (1), none (3) |
| `/api/v1/cards` | `app/api/v1/routes/cards.py` | 4 | `get_current_user` (4) |
| `/api/v1/cover-letter` | `app/api/v1/routes/cover_letter.py` | 1 *(re-exports legacy)* | `get_current_user` *(spec #58)* |
| `/api/v1/decks` | `app/api/v1/routes/decks.py` | 2 | `get_current_user` (2) *(NEW — Phase 6 slice 6.3, `ba00331`; fixture-data read-only routes; legacy `study/QuizPanel.tsx` unaffected)* |
| `/api/v1/email-preferences` | `app/api/v1/routes/email_prefs.py` | 2 | `get_current_user` (2) |
| `/api/v1/feedback` + `/api/v1/admin/feedback` | `app/api/v1/routes/feedback.py` | 3 | `get_current_user` (1), `require_admin` (2) |
| `/api/v1/gamification` | `app/api/v1/routes/gamification.py` | 1 | `get_current_user` |
| `/api/v1/home` | `app/api/v1/routes/home.py` | 1 | `get_current_user` |
| `/api/v1/interview-prep` | `app/api/v1/routes/interview.py` | 1 *(re-exports legacy)* | `get_current_user_optional` |
| `/api/v1/lessons` | `app/api/v1/routes/lessons.py` | 1 | `get_current_user` (1) *(NEW — Phase 6 slice 6.3, `ba00331`; bundles lesson body + ordered active quiz_items + lifted deck top-level fields; fixture-data read-only)* |
| `/api/v1/missions/*` | `app/api/v1/routes/mission.py` | 4 | `get_current_user` (4) |
| `/api/v1/progress` | `app/api/v1/routes/progress.py` | 2 | `get_current_user` (2) |
| `/api/v1/quiz-items` | `app/api/v1/routes/quiz_items.py` | 3 | `get_current_user` (3) *(NEW — Phase 6 slice 6.2, `7b654fb`; FSRS spaced-repetition daily review against `quiz_item_progress`; 404/403/409 error paths on POST `/review` map to `QuizItemNotFoundError` / `QuizItemForbiddenError` / `QuizItemRetiredError`)* |
| `/api/v1/resume` | `app/api/v1/routes/resume.py` | 4 | `get_current_user` (3), `require_plan` (1) |
| `/api/v1/rewrite` | `app/api/v1/routes/rewrite.py` | 2 *(re-exports legacy)* | `get_current_user` *(spec #58)* |
| `/api/v1/study` | `app/api/v1/routes/study.py` | 4 | `get_current_user` (4) |
| `/api/v1/tracker` | `app/api/v1/routes/tracker.py` | 4 | `get_current_user` (4) |
| `/api/v1/users` | `app/api/v1/routes/users.py` | 2 | `get_current_user` (2) |

### Flat endpoint table

| Method | Path | Handler | Auth | Tags |
|--------|------|---------|------|------|
| POST | /api/analyze | analyze_resume | get_current_user_optional | Analysis *(spec #56, B-031 — 402 quota branch via `check_and_increment(..., "analyze", window="lifetime")` for authenticated free users; anonymous + Pro + Enterprise + admin bypass)* |
| GET | /api/analyze/{scan_id} | get_analysis_by_id | get_current_user | Analysis *(NEW since prior regen — B-035 / spec #59; ownership-checked, returns 200 / 410 (no payload) / 404 (not owner))* |
| POST | /api/cover-letter | generate_cover_letter | get_current_user | Cover Letter *(spec #58 / B-033 — 402 `free_tier_limit` / `cover_letter_limit` for free plan)* |
| POST | /api/interview-prep | generate_interview_prep | get_current_user_optional | Interview Prep |
| POST | /api/rewrite | rewrite_resume | get_current_user | Rewrite *(spec #58 / B-033 — 402 `free_tier_limit` / `rewrite_limit` with `attempted_action='full'` for free plan)* |
| POST | /api/rewrite/section | rewrite_section | get_current_user | Rewrite *(spec #51, B-001 impl + spec #58 / B-033 — shares `"rewrite"` bucket; 402 envelope `attempted_action='section'`)* |
| GET | /api/v1/admin/cards | list_cards | require_admin | v1 Admin |
| POST | /api/v1/admin/cards | create_card | require_admin | v1 Admin |
| PUT | /api/v1/admin/cards/{card_id} | update_card | require_admin | v1 Admin |
| DELETE | /api/v1/admin/cards/{card_id} | delete_card | require_admin | v1 Admin |
| POST | /api/v1/admin/cards/generate | generate_card | require_admin | v1 Admin |
| POST | /api/v1/admin/cards/import | import_cards | require_admin | v1 Admin |
| GET | /api/v1/admin/feedback | list_feedback | require_admin | v1 Feedback |
| GET | /api/v1/admin/feedback/summary | feedback_summary | require_admin | v1 Feedback |
| GET | /api/v1/admin/ping | admin_ping | require_admin | v1 Admin |
| GET | /api/v1/admin/registration-logs | list_registration_logs | require_admin | v1 Admin |
| GET | /api/v1/admin/audit | list_admin_audit_log | audit_admin_request → require_admin | v1 Admin *(spec #38 E-018a)* |
| GET | /api/v1/admin/analytics/metrics | metrics_endpoint | audit_admin_request → require_admin | v1 Admin Analytics *(spec #38 E-018b)* |
| GET | /api/v1/admin/analytics/performance | performance_endpoint | audit_admin_request → require_admin | v1 Admin Analytics *(spec #38 E-018b)* |
| GET | /api/v1/admin/decks | list_admin_decks_route | audit_admin_request → require_admin | v1 Admin Decks *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Returns `list[DeckResponse]`. `?status=active\|archived\|all` Literal-typed via `AdminDeckStatusFilter` per spec §12 D-16; FastAPI 422s invalid values. Default `active`. Fires `admin_deck_listed`-style events not catalogued — list endpoints in §9 catalog don't emit per admin-panel skill convention.)* |
| POST | /api/v1/admin/decks | create_deck_route | audit_admin_request → require_admin | v1 Admin Decks *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Creates a deck. 201 → `DeckResponse`; 409 `DeckSlugConflictError` on duplicate slug. Service emits `admin_deck_created` PostHog event with `internal: true` per §9.)* |
| PATCH | /api/v1/admin/decks/{deck_id} | update_deck_route | audit_admin_request → require_admin | v1 Admin Decks *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Partial update. Persona-narrowing detection: when `payload.persona_visibility` removes a persona from the active set, service emits `admin_deck_persona_narrowed` event with `{deck_id, removed_personas, before_count, after_count}` per spec §12 D-19 (de1e9a9-amended copy). Standard `admin_deck_updated` always fires with `persona_visibility_narrowed: bool` flag. 404 / 409 on slug collision. FE `ConfirmPersonaNarrowingModal` (slice 6.4b-2) gates the PATCH client-side; BE permits without gating per §4.1.1 service-layer warning-free invariant.)* |
| POST | /api/v1/admin/decks/{deck_id}/archive | archive_deck_route | audit_admin_request → require_admin | v1 Admin Decks *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Sets `archived_at`. Idempotent on re-archive (no-op + no event re-emit). Service emits `admin_deck_archived` event on first archive only. Does NOT cascade-retire lessons/quiz_items per spec §7.5 (archive ≠ substantive edit).)* |
| GET | /api/v1/admin/decks/{deck_id}/lessons | list_admin_lessons_route | audit_admin_request → require_admin | v1 Admin Lessons *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Returns `list[LessonResponse]` for the deck. `?status=active\|drafts\|published\|archived\|all` Literal-typed via `AdminLessonStatusFilter` per D-16; lessons are the only entity with the full 5-value vocab since they have both `published_at` and `archived_at` lifecycles. Default `active`. 404 if deck not found.)* |
| POST | /api/v1/admin/decks/{deck_id}/lessons | create_lesson_route | audit_admin_request → require_admin | v1 Admin Lessons *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Creates a lesson nested under deck. 201 → `LessonResponse`; 404 deck not found; 409 lesson-slug conflict within deck. Service emits `admin_lesson_created` event.)* |
| PATCH | /api/v1/admin/lessons/{lesson_id} | update_lesson_route | audit_admin_request → require_admin | v1 Admin Lessons *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Partial update with substantive-edit detection per spec §7. Server `_classify(...)` checks character-delta on `concept_md` / `production_md` / `examples_md` against `SUBSTANTIVE_EDIT_THRESHOLD = 0.15` (`difflib.SequenceMatcher.ratio()` per JC #3 of slice 6.4b-1). 409 `EditClassificationConflictError` envelope `{error: "edit_classification_mismatch", expected, claimed, fields}` when payload `edit_classification` disagrees. On substantive: cascade-retires all active `quiz_items` for the lesson in same DB transaction (sets `qi.retired_at = func.now()`), increments `lesson.version`, sets `version_type='substantive_edit'`. Returns `LessonUpdateResponse` extending `LessonResponse` with `quiz_items_retired_count` + `quiz_items_retired_ids`. Emits `admin_lesson_updated_minor` OR `admin_lesson_substantively_edited` event per outcome.)* |
| POST | /api/v1/admin/lessons/{lesson_id}/archive | archive_lesson_route | audit_admin_request → require_admin | v1 Admin Lessons *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Sets `archived_at`. Idempotent. Does NOT cascade-retire quiz_items per spec §7.5. Emits `admin_lesson_archived` event.)* |
| POST | /api/v1/admin/lessons/{lesson_id}/publish | publish_lesson_route | audit_admin_request → require_admin | v1 Admin Lessons *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Sets `published_at`. Idempotent on re-publish (no-op). 409 `LessonArchivedError` if lesson is archived. Emits `admin_lesson_published` event on first publish only.)* |
| GET | /api/v1/admin/lessons/{lesson_id}/quiz-items | list_admin_quiz_items_route | audit_admin_request → require_admin | v1 Admin Quiz Items *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Returns `list[QuizItemResponse]` for the lesson. `?status=active\|retired\|all` Literal-typed via `AdminQuizItemStatusFilter` per D-16. Default `active` excludes retired. 404 if lesson not found.)* |
| POST | /api/v1/admin/lessons/{lesson_id}/quiz-items | create_quiz_item_route | audit_admin_request → require_admin | v1 Admin Quiz Items *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Creates quiz_item nested under lesson. 201 → `QuizItemResponse`; 404 lesson not found; 409 `LessonArchivedError` if lesson is archived. Pydantic `model_validator` enforces distractors-required-when-mcq. Emits `admin_quiz_item_created` event.)* |
| PATCH | /api/v1/admin/quiz-items/{quiz_item_id} | update_quiz_item_route | audit_admin_request → require_admin | v1 Admin Quiz Items *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Substantive PATCH = retire-and-replace per D-18: inserts new row with `version = old.version + 1`, sets `old.superseded_by_id = new.id`, sets `old.retired_at = now()`; returns NEW row's `QuizItemResponse`. Minor PATCH = in-place mutation. Same 409 `EditClassificationConflictError` envelope as lesson PATCH. Existing `quiz_item_progress` rows preserved per slice 6.2 §4.6 D-4 (no FK-based cleanup; service-layer invariant). Emits `admin_quiz_item_retired` (with `retire_reason: 'retire_and_replace'`) on substantive path.)* |
| POST | /api/v1/admin/quiz-items/{quiz_item_id}/retire | retire_quiz_item_route | audit_admin_request → require_admin | v1 Admin Quiz Items *(NEW — Phase 6 slice 6.4b-1, `d6bda3b`. Direct retire. Optional `superseded_by_id` body field links the retired row to a replacement (admin-curated supersession). Idempotent on re-retire. Emits `admin_quiz_item_retired` event with `retire_reason: 'direct'` or `'superseded'` per body presence. `quiz_item_progress` rows preserved.)* |
| POST | /api/v1/analyze | analyze_resume | get_current_user_optional | v1 Analysis *(re-exports legacy)* |
| GET | /api/v1/analyze/{scan_id} | get_analysis_by_id | get_current_user | v1 Analysis *(re-exports legacy; B-035 / spec #59)* |
| POST | /api/v1/auth/google | google_auth | none | v1 Auth |
| POST | /api/v1/auth/logout | logout | get_current_user | v1 Auth |
| GET | /api/v1/auth/me | get_me | get_current_user | v1 Auth |
| POST | /api/v1/auth/refresh | refresh_access_token | none | v1 Auth |
| GET | /api/v1/cards | list_categories | get_current_user | v1 Cards |
| GET | /api/v1/cards/category/{category_id} | get_category_cards | get_current_user | v1 Cards |
| GET | /api/v1/cards/search | search_cards | get_current_user | v1 Cards |
| GET | /api/v1/cards/{card_id} | get_card | get_current_user | v1 Cards |
| POST | /api/v1/cards/{card_id}/feedback | submit_feedback | get_current_user | v1 Feedback |
| POST | /api/v1/cover-letter | generate_cover_letter | get_current_user | v1 Cover Letter *(spec #58 / B-033)* |
| GET | /api/v1/decks/{deck_id} | get_deck_route | get_current_user | v1 Decks *(NEW — Phase 6 slice 6.3, `ba00331`. Returns `DeckResponse` (slice 6.1 schema reused as-is). 404 on unknown / archived `deck_id`. Fixture-data read-only — slice 6.4 swaps `lesson_service.get_deck_with_meta` body to a DB query without changing route surface or response shape (D-4).)* |
| GET | /api/v1/decks/{deck_id}/lessons | list_deck_lessons_route | get_current_user | v1 Decks *(NEW — Phase 6 slice 6.3, `ba00331`. Returns `DeckLessonsResponse` (deck shell + ordered active lessons by `display_order`). Empty `lessons` list returns 200, not 404, when the deck exists but has no lessons. 404 on unknown / archived `deck_id`.)* |
| GET | /api/v1/email-preferences | get_email_preferences | get_current_user | v1 Email Preferences |
| PUT | /api/v1/email-preferences | update_email_preferences | get_current_user | v1 Email Preferences |
| GET | /api/v1/gamification/stats | get_gamification_stats | get_current_user | v1 Gamification |
| GET | /api/v1/home/state | get_home_state | get_current_user | v1 Home |
| POST | /api/v1/interview-prep | generate_interview_prep | get_current_user_optional | v1 Interview Prep |
| GET | /api/v1/lessons/{lesson_id} | get_lesson_route | get_current_user | v1 Lessons *(NEW — Phase 6 slice 6.3, `ba00331`. Returns `LessonWithQuizzesResponse`: lesson body + ordered active quiz_items + lifted top-level `deck_id` / `deck_slug` / `deck_title` for FE breadcrumb. 404 on unknown / archived `lesson_id`. Fixture-data read-only — slice 6.4 swaps `lesson_service.get_lesson_with_quizzes` body to a DB query without changing route surface or response shape (D-4).)* |
| POST | /api/v1/missions/complete-day | complete_day | get_current_user | v1 Mission |
| POST | /api/v1/missions/create | create_mission | get_current_user | v1 Mission |
| GET | /api/v1/missions/active | get_active_mission | get_current_user | v1 Mission |
| GET | /api/v1/missions/daily | get_daily_cards | get_current_user | v1 Mission |
| GET | /api/v1/onboarding/checklist | get_checklist_endpoint | get_current_user | v1 Onboarding |
| GET | /api/v1/onboarding/recommendations | get_recommendations | get_current_user | v1 Onboarding |
| POST | /api/v1/payments/checkout | create_checkout | get_current_user | v1 Payments |
| GET | /api/v1/payments/pricing | get_pricing_endpoint | none | v1 Payments |
| POST | /api/v1/payments/portal | create_portal | get_current_user | v1 Payments |
| POST | /api/v1/payments/paywall-dismiss | paywall_dismiss | get_current_user | v1 Payments *(spec #42, P5-S26b — fires `paywall_dismissed` PostHog on logged=true; LD-8 60s dedup)* |
| GET | /api/v1/payments/should-show-paywall | should_show_paywall | get_current_user | v1 Payments *(spec #42 + spec #56 LD-4 carve-out — `trigger='scan_limit'` always returns `{show: true, attempts_until_next: 0}` for free users)* |
| GET | /api/v1/payments/usage | get_usage | get_current_user | v1 Payments *(spec #56 / B-031 + spec #58 / B-033 — flat `{plan, is_admin, scans_{used,remaining,max}, rewrites_{used,remaining,max}, cover_letters_{used,remaining,max}}` with `-1` sentinel for unlimited)* |
| POST | /api/v1/payments/webhook | stripe_webhook | none | v1 Payments *(spec #43 idempotency; spec #42 — `customer.subscription.deleted` branch stamps `user.downgraded_at`)* |
| GET | /api/v1/progress/heatmap | get_heatmap | get_current_user | v1 Progress |
| GET | /api/v1/progress/radar | get_radar | get_current_user | v1 Progress |
| GET | /api/v1/quiz-items/daily | get_daily_quiz_items | get_current_user | v1 Quiz Items *(NEW — Phase 6 slice 6.2, `7b654fb`. Returns `DailyQuizReviewResponse`. Two-pass queue: overdue progress rows ordered `due_date ASC` then fresh-fill ordered `created_at ASC`, both filtering retired quiz_items + archived lessons + archived decks. Daily goal `_DAILY_GOAL=5` (spec D-3). `daily_status` is the permissive sentinel `cards_limit=-1, can_review=true` always — slice 6.7 wires the real wall (D-4).)* |
| POST | /api/v1/quiz-items/review | submit_quiz_review | get_current_user | v1 Quiz Items *(NEW — Phase 6 slice 6.2, `7b654fb`. Submits an FSRS rating (1=Again, 2=Hard, 3=Good, 4=Easy) for a single quiz_item; advances `quiz_item_progress` state. Errors: 400 rating outside [1,4] / time_spent_ms outside [0, 300_000]; 403 archived lesson or deck (`QuizItemForbiddenError`); 404 unknown `quiz_item_id` (`QuizItemNotFoundError`); 409 retired-without-existing-progress (`QuizItemRetiredError`). Service-layer fires `quiz_item_progress_initialized` (first review) + `quiz_item_reviewed` (every review) PostHog events; FE side does NOT duplicate (spec 6.3 §9). Service ports `study_service.review_card` byte-for-byte modulo D-1 (FK swap) / D-4 (no wall) / D-7 (no XP).)* |
| GET | /api/v1/quiz-items/progress | get_quiz_progress | get_current_user | v1 Quiz Items *(NEW — Phase 6 slice 6.2, `7b654fb`. Returns `QuizProgressResponse`: aggregate `quiz_item_progress` rows by FSRS state plus `total_reviewed`, `total_reps`, `total_lapses`. Quiz items the user has never touched are not in the counts.)* |
| GET | /api/v1/resume/{resume_id} | get_resume | get_current_user | v1 Resume |
| GET | /api/v1/resume/{resume_id}/diff | get_resume_diff | get_current_user | v1 Resume |
| POST | /api/v1/resume/{resume_id}/optimize | optimize_resume | require_plan | v1 Resume |
| POST | /api/v1/resume/upload | upload_resume | get_current_user | v1 Resume |
| POST | /api/v1/rewrite | rewrite_resume | get_current_user | v1 Rewrite *(spec #58 / B-033 — shared `"rewrite"` bucket)* |
| POST | /api/v1/rewrite/section | rewrite_section | get_current_user | v1 Rewrite *(spec #51, B-001 + spec #58)* |
| GET | /api/v1/study/daily | get_daily_review | get_current_user | v1 Study *(spec #63 / B-059 — response shape extended with `daily_status: DailyStatus {cards_consumed, cards_limit, can_review, resets_at}`. Read-side mirror of the same Redis key `_check_daily_wall` writes on submit. Side-effect-free GET (no INCR), fail-open on Redis outage. Pro / Enterprise / admin → `cards_limit=-1, can_review=true`. `daily_status` is `Optional[DailyStatus]` — only populated when `user is not None`. No new route.)* |
| POST | /api/v1/study/experience | generate_experience | get_current_user | v1 Study |
| GET | /api/v1/study/progress | get_progress | get_current_user | v1 Study |
| POST | /api/v1/study/review | submit_review | get_current_user | v1 Study *(spec #50, P5-S22-WALL-b — 402 `DailyReviewLimitError` for free users at daily cap)* |
| GET | /api/v1/tracker | list_applications | get_current_user | v1 Tracker |
| POST | /api/v1/tracker | create_app | get_current_user | v1 Tracker |
| PATCH | /api/v1/tracker/{app_id} | update_app | get_current_user | v1 Tracker |
| DELETE | /api/v1/tracker/{app_id} | delete_app | get_current_user | v1 Tracker |
| PATCH | /api/v1/users/me/persona | update_persona | get_current_user | v1 Users |
| POST | /api/v1/users/me/home-first-visit | mark_home_first_visit | get_current_user | v1 Users *(B-016; idempotent stamp — flips greeting copy)* |

---

## Section 4 — Backend services

### Top-level `app/services/`

| File | Purpose | Public names | External deps |
|------|---------|--------------|---------------|
| ai_card_service.py | AI card generation service — generates flashcard drafts via LLM. | generate_card_draft | LLM-router |
| ai_service.py | AI service — LLM-powered resume optimization. **Duplicates `gpt_service.py`** (see `[S47-defer]` and §9). Only consumed by `/api/v1/resume/{id}/optimize` enterprise path. | generate_job_fit_explanation, generate_resume_rewrite, generate_cover_letter, generate_interview_questions, rewrite_bullets_gpt | LLM-router |
| bullet_analyzer.py | Bullet point analyzer and strength scorer. | score_bullet, identify_issues, rewrite_bullet_locally, analyze_bullets | — |
| card_admin_service.py | Admin card CRUD — create, update, delete, list, bulk import. | create_card, update_card, delete_card, list_cards, bulk_import_csv | — |
| admin_analytics_service.py | Admin analytics aggregations (spec #38 E-018b). Six-OKR metrics with 7d/30d deltas; performance snapshot with LLM spend estimate (Postgres `usage_logs.tokens_consumed` × `llm_router.TIER_PRICE_USD_PER_1M_TOKENS`) and Stripe webhook success rate. `api_latency` + `error_rate_24h_pct` are deferred placeholders. Redis-cached 5 min with graceful degradation. | get_metrics_summary, get_performance_summary, CACHE_TTL_SECONDS | Redis |
| admin_errors.py | **NEW — Phase 6 slice 6.4b-1 (`d6bda3b`).** Shared admin-error class module per spec §12 D-11 — keeps cross-service error types out of any single service file. Declares `DeckSlugConflictError`, `DeckNotFoundError`, `LessonSlugConflictError`, `LessonNotFoundError`, `LessonArchivedError`, `QuizItemNotFoundError`, `EditClassificationConflictError` (carries `expected`, `claimed`, `fields` attrs to populate the 409 envelope on `update_lesson_route` + `update_quiz_item_route`). Also declares `SUBSTANTIVE_EDIT_THRESHOLD = 0.15` constant per spec §12 D-17 — BE half of the FE `lessonEdit.ts` shared threshold. The `_is_substantive_change(before, after) → bool` helper uses `difflib.SequenceMatcher(None, before, after).ratio()` and compares `1 - ratio` against the threshold (per JC #3 of slice 6.4b-1: stdlib choice over Levenshtein for normalized [0..1] semantics). | DeckSlugConflictError, DeckNotFoundError, LessonSlugConflictError, LessonNotFoundError, LessonArchivedError, QuizItemNotFoundError, EditClassificationConflictError, SUBSTANTIVE_EDIT_THRESHOLD, _is_substantive_change | — |
| deck_admin_service.py | **NEW — Phase 6 slice 6.4b-1 (`d6bda3b`).** Deck-admin CRUD service backing `app/api/v1/routes/admin_decks.py`. `create_deck` raises `DeckSlugConflictError` on duplicate slug. `update_deck` performs persona-narrowing detection (computes `removed_personas` between old + new `persona_visibility`); when non-empty, fires `admin_deck_persona_narrowed` event in addition to standard `admin_deck_updated` (with `persona_visibility_narrowed: bool` flag) per spec §12 D-19. `archive_deck` is idempotent (no-op + no event re-emit on re-archive); does NOT cascade per §7.5. `list_admin_decks` honors `AdminDeckStatusFilter` Literal `'active'/'archived'/'all'` per D-16. All mutations followed by `db.refresh(obj)` after `flush()` to populate server-defaults like `created_at`/`updated_at` before `model_validate` (slice 6.4b-1 JC #4 — same `MissingGreenlet`-avoidance pattern as slice 6.2). Emits 4 PostHog events (`admin_deck_created`, `admin_deck_updated`, `admin_deck_archived`, `admin_deck_persona_narrowed`) all with `internal: true`. | create_deck, update_deck, archive_deck, list_admin_decks | — |
| lesson_admin_service.py | **NEW — Phase 6 slice 6.4b-1 (`d6bda3b`).** Lesson-admin CRUD service backing `app/api/v1/routes/admin_lessons.py`. `create_lesson` validates parent deck exists + non-archived. `update_lesson` is the substantive-edit cascade orchestrator: server-side `_is_substantive_change()` comparison vs payload `edit_classification` claim raises `EditClassificationConflictError(expected, claimed, fields)` on mismatch (per spec §7.1 + §7.3); on substantive path, retires all active `quiz_items` for the lesson in same DB transaction via `qi.retired_at = func.now()` query + bumps `lesson.version` + sets `version_type='substantive_edit'`. Returns `LessonUpdateResponse` extending `LessonResponse` with cascade outcome (`quiz_items_retired_count` + `quiz_items_retired_ids`) per spec §6.6. `publish_lesson` idempotent + raises `LessonArchivedError` on archived target. `archive_lesson` does NOT cascade-retire per §7.5. `list_admin_lessons` honors `AdminLessonStatusFilter` Literal full 5-value vocab. Emits 5 PostHog events (`admin_lesson_created`, `admin_lesson_updated_minor`, `admin_lesson_substantively_edited`, `admin_lesson_published`, `admin_lesson_archived`) per outcome branch. | create_lesson, update_lesson, publish_lesson, archive_lesson, list_admin_lessons | — |
| quiz_item_admin_service.py | **NEW — Phase 6 slice 6.4b-1 (`d6bda3b`).** Quiz-item admin CRUD service backing `app/api/v1/routes/admin_quiz_items.py`. `create_quiz_item` validates parent lesson exists + non-archived. `update_quiz_item` distinguishes substantive vs minor per spec §7 + D-18: substantive path = retire-and-replace (insert new row with `version = old.version + 1`, set `old.superseded_by_id = new.id`, set `old.retired_at = now()`, return NEW row); minor path = in-place mutation. Same `EditClassificationConflictError` semantics as `lesson_admin_service.update_lesson`. `retire_quiz_item` accepts optional `superseded_by_id` for admin-curated supersession; idempotent on re-retire. **Critical invariant** (slice 6.2 §4.6 D-4): existing `quiz_item_progress` rows are NEVER cleaned up on retire — kept queryable for FSRS analytics; the "no new progress rows against retired quiz_items" rule is enforced at the read-time service layer in `quiz_item_study_service`, NOT here. Emits 2 PostHog events (`admin_quiz_item_created`, `admin_quiz_item_retired`) — `retire_reason` discriminator distinguishes `direct` (route-level POST retire), `cascade` (called from `lesson_admin_service` on substantive lesson edit), `retire_and_replace` (substantive PATCH path), `superseded` (POST retire with `superseded_by_id`). | create_quiz_item, update_quiz_item, retire_quiz_item, list_admin_quiz_items | — |
| card_service.py | Card and category read service with plan-gated access. | list_categories, get_cards_by_category, get_card, search_cards | LLM-direct |
| email_service.py | Thin wrapper around the Resend API for transactional email with retry logic. | send_email, EmailSendError | Resend |
| experience_service.py | AI experience generator — turns study history into resume-ready narratives. | generate_experience | LLM-router |
| formatter_check.py | ATS formatting compliance checker for resume documents. | check_formatting | — |
| gamification_service.py | XP, streaks, and badges. | update_streak, reset_streak_if_missed, award_xp, get_stats, BadgeDef, InvalidXPSourceError, StatsView | — |
| gap_detector.py | Skill gap detection. | detect_gaps, classify_importance, get_skills_overlap_data | — |
| gap_mapping_service.py | ATS gap → card category mapping. | map_gaps_to_categories, RecommendedCategory, GapMapping | LLM-direct |
| geo_pricing_service.py | Geo-based pricing showing USD by default, INR for India. | get_pricing | HTTP-external, Redis |
| gpt_service.py | AI resume-optimization features delegating to multi-model LLM router. Post-B-001 (`167b70f`, spec #51): `generate_resume_rewrite` returns `Tuple[RewriteResponse, path_str]` where `path_str ∈ {"chunked", "fallback_full"}` (D-014). Per-section regen via `generate_section_rewrite`. `RewriteError` on truncation / malformed JSON. Chunking uses asyncio semaphore `PARALLEL_SECTION_LIMIT=4`. Post-B-002 (`825eb0e`, spec #52): `generate_cover_letter` returns structured `CoverLetterResponse`; `full_text` assembled server-side via `_join_cover_letter`. `body_paragraphs` Pydantic-pinned to `len==3`. Post-B-014 (`067c232`): `SECTION_MAX_TOKENS=4000` + `SECTION_THINKING_BUDGET=800`. Post-B-022 (`fa1871e`): `generate_job_fit_explanation` routed through reasoning tier (`JOB_FIT_MAX_TOKENS=3500`, `JOB_FIT_THINKING_BUDGET=800`). Post-B-023 (`79f76b4`): `_extract_candidate_name` rejects pure-uppercase lines. | generate_job_fit_explanation, generate_resume_rewrite, generate_resume_rewrite_async, generate_section_rewrite, generate_cover_letter, generate_interview_questions, rewrite_bullets_gpt, RewriteError, _join_cover_letter, _extract_candidate_name, SECTION_MAX_TOKENS, SECTION_THINKING_BUDGET, JOB_FIT_MAX_TOKENS, JOB_FIT_THINKING_BUDGET | LLM-router |
| home_state_service.py | State-aware home dashboard evaluator. Post-E-042-impl-BE: `get_next_interview` reads `tracker_applications_v2.interview_date` (nearest upcoming, partial-index-served); tracker route writers call `home_state_service.invalidate` to bust the Redis cache. | evaluate_state, get_next_interview, invalidate | Redis |
| interview_storage_service.py | Interview question set storage + cache-aware generation. | generate_or_get_interview_set, InterviewGenerationResult | LLM-router |
| keywords.py | TF-IDF keyword extraction and matching. | extract_keywords, match_keywords, get_keyword_chart_data | — |
| lesson_service.py | **Body-swapped to DB queries — Phase 6 slice 6.4b-1 (`d6bda3b`).** All four functions previously called `lesson_fixtures` (slice 6.3, `ba00331`); now query Postgres via SQLAlchemy with `selectinload(Lesson.quiz_items)` + `selectinload(Lesson.deck)` per spec §12 D-15 (mirrors `quiz_item_study_service` slice-6.2 precedent). Function signatures + response shapes byte-identical to slice 6.3 per spec §12 D-2 (verified at slice 6.4b-1 close: existing `decks.py` + `lessons.py` user-facing routes return identical JSON post-swap). Filters: only non-archived rows surface; `get_lesson_with_quizzes` filters retired quiz_items in active list; unpublished (NULL `published_at`) lessons treated as 404 in user-facing routes per slice 6.3 §5 (admin-LIST `?status=drafts` is the path admins use). `app/data/lesson_fixtures.py` (185 lines) + `app/data/__init__.py` (empty marker) **deleted** in same commit per spec §4.3 + slice 6.3 D-4 cash-in. `app/data/` directory left in place per §4.3 — slice 6.4.5 reintroduces as `app/data/decks/seed_lessons/*.md`. | get_lesson_with_quizzes, get_deck_with_meta, list_lessons_in_deck, get_deck_lessons_bundle | — |
| mission_service.py | Mission Mode — time-bound study sprints with FSRS-prioritised cards. | create_mission, get_active_mission, get_mission_daily_cards, complete_mission_day, MissionNotFoundError, MissionConflictError, MissionInvalidError, MissionGoneError | — |
| nlp.py | NLP pipeline using spaCy. Post-B-021 (`e7c6d73`) + B-024 (`50e3c3c`): `_extract_company_name` is a three-layer orchestrator — LLM primary (`company_name_extraction` FAST task, null-on-unclear), regex fallback on LLM infra failure, deny-list + 100-char cap. `extract_job_requirements` returns `company_name: str \| None`. | get_nlp, extract_entities, extract_skills, extract_job_requirements, calculate_similarity, _extract_company_name, _extract_company_name_regex | LLM-router |
| onboarding_checklist_service.py | Interview-Prepper onboarding checklist from telemetry-derived state. | get_checklist, WrongPersonaError | — |
| parser.py | Resume parser supporting PDF and DOCX. | parse_pdf, parse_docx, detect_sections, extract_bullets, extract_contact_info | — |
| payment_service.py | Thin wrapper around Stripe. `_handle_subscription_deleted` writes `user.downgraded_at` per spec #42 LD-5. | create_checkout_session, create_billing_portal_session, handle_webhook, PaymentError, InvalidSignatureError, UserNotFoundError, NotProSubscriberError | Stripe |
| paywall_service.py | Paywall dismissal service (spec #42). `record_dismissal` with LD-8 60s idempotency per (user_id, trigger); `should_show_paywall` with Pro/admin bypass + Strategy A grace counter. Hard-wall carve-outs (amend spec #42 LD-1): trigger set is `{scan_limit, rewrite_limit, cover_letter_limit}` — for any of those three on a free user, always returns `{show: True, attempts_until_next: 0}`. Win-back send DEFERRED to E-031. | record_dismissal, should_show_paywall, RecordDismissalResult, ShouldShowPaywallResult, GRACE_ATTEMPTS, IDEMPOTENCY_WINDOW_SECONDS | — |
| progress_service.py | Progress analytics with category radar and activity heatmap. | get_category_coverage, get_activity_heatmap | — |
| quiz_item_study_service.py | **NEW — Phase 6 slice 6.2 (`7b654fb`).** First FSRS consumer of slice 6.1's `quiz_item_progress` table. Module-level `_DAILY_GOAL=5` (D-3), `_scheduler = Scheduler()`, `_STATE_TO_FSRS` / `_FSRS_TO_STATE` mirror `study_service`. Helpers `_build_fsrs_quiz_card` + `_apply_fsrs_result_to_quiz_item` ported byte-for-byte from `study_service` modulo FK swap (D-2). `_next_local_midnight` duplicated locally per OQ-3 (slice 6.15 `git rm` cleanliness). `get_daily_quiz_items` two-pass queue (overdue `due_date ASC` then fresh-fill `created_at ASC`, both filtering retired quiz_items + archived lessons + archived decks). `review_quiz_item` raises `QuizItemNotFoundError` / `QuizItemForbiddenError` / `QuizItemRetiredError` mapped by route to 404/403/409. `_compute_daily_quiz_status` returns the permissive sentinel `cards_limit=-1, can_review=true` per D-4 (slice 6.7 owns the real wall). `_resolve_plan` inspects SQLAlchemy state via `inspect(user).unloaded` — returns None when `user.subscription` is not eagerly loaded (avoids `MissingGreenlet` in sync test paths; production callers go through `get_current_user`'s `selectin`). Analytics events `quiz_item_progress_initialized` (first review, creates row) + `quiz_item_reviewed` (every review) fire post-flush per spec 6.2 §8. NO XP / streak call (D-7 — `study_service.review_card`'s `gamification_service.award_xp` intentionally absent). | get_daily_quiz_items, review_quiz_item, get_quiz_progress, QuizItemNotFoundError, QuizItemForbiddenError, QuizItemRetiredError, _build_fsrs_quiz_card, _apply_fsrs_result_to_quiz_item, _compute_daily_quiz_status, _next_local_midnight, _resolve_plan, _state_before, _DAILY_GOAL, _scheduler, _STATE_TO_FSRS, _FSRS_TO_STATE | — |
| reminder_service.py | Daily email reminder service. | get_users_needing_reminder, build_email_body, build_subject, send_daily_reminders | Resend |
| resume_templates.py | Resume template definitions for AI rewriting. | get_template, get_template_names, auto_select_template | — |
| scorer.py | ATS scoring engine. | ATSScorer | — |
| study_service.py | FSRS spaced-repetition study service. Enforces free-tier daily-card review wall (spec #50) via `_check_daily_wall` — Redis INCR keyed `daily_cards:{user_id}:{YYYY-MM-DD}` in user-local tz, 48h TTL, fail-open on Redis outage; admin + Pro/Enterprise bypass. Post-`d19103c`: `_check_daily_wall` replaces the prior `_DAILY_CARD_LIMIT` module constant with a function-local `get_settings().free_daily_review_limit` read so monkeypatched env vars propagate live. Post-B-059 (`20562ea`, spec #63): new `_compute_daily_status(user, db) → DailyStatus` helper performs side-effect-free Redis GET (no INCR) for the pre-flight gate read; `get_daily_review` signature gained kw-only `user: User \| None = None` (default keeps the 6 pre-existing test callers green) and the response now includes `daily_status` when `user is not None`. | get_daily_review, create_progress, review_card, get_progress, _compute_daily_status, CardNotFoundError, CardForbiddenError, DailyReviewLimitError | Redis |
| tracker_service_v2.py | SQLAlchemy-backed job application tracker. `create_application` accepts optional `analysis_payload: dict` kwarg (B-035 / spec #59). | create_application, find_by_scan_id, get_applications, get_application_by_id, update_application, delete_application | — |
| usage_service.py | Usage tracking + plan-limit enforcement. Per spec #56 / B-031: `PLAN_LIMITS["free"]["analyze"] = 1` (lifetime). `check_and_increment` accepts `window: Literal["monthly","lifetime"] = "monthly"` — analyze + rewrite + cover_letter pass `"lifetime"`. Admin bypass via in-helper User role fetch; short-circuits `allowed=True, limit=-1`. Per spec #58 / B-033: `get_analyze_usage` replaced by `get_usage_snapshot` (back-compat alias). New `_counter_triple(used, max, is_admin)` helper centralizes `-1` sentinel. `/rewrite` + `/rewrite/section` share `"rewrite"` feature key (spec #58 §4.1 Option a). Post-`d19103c` (env-tunable testing affordance): `PLAN_LIMITS` dict seeded from `get_settings()` at import; new `_plan_limits(plan)` helper re-reads the two free-cell entries (`analyze`/`lifetime`, `interview_prep`/`monthly`) live so test monkeypatching of settings propagates without rebuilding the dict. Pro/Enterprise rows stay literal. | log_usage, check_usage_limit, check_and_increment, get_usage_summary, get_usage_snapshot, get_analyze_usage (alias), _counter_triple, _plan_limits, PLAN_LIMITS, Window | — |
| user_service.py | User CRUD + admin-role reconciliation. Post-E-040: `reconcile_admin_role(user, admin_emails_set) -> (action, prior_role, new_role)` is a pure mutation. Action ∈ `{"promoted", "demoted", "unchanged"}`. Invoked from `auth.py::google_auth` on every login. | get_or_create_user, get_user_by_id, reconcile_admin_role | — |

### `app/services/llm/` (legacy provider factory — do not extend)

| File | Purpose | Public names | External deps |
|------|---------|--------------|---------------|
| factory.py | LLM provider factory. *(Legacy; Phase-6 cleanup target per Tech Debt.)* | get_llm_provider | — |
| claude_provider.py | Claude LLM provider — wraps Anthropic SDK. | ClaudeProvider | LLM-direct |
| gemini_provider.py | Gemini LLM provider — wraps Google Generative AI SDK. | GeminiProvider | LLM-direct |

---

## Section 5 — Alembic revisions

| # | Short revision | Description | down_revision |
|---|----------------|-------------|---------------|
| 1 | 0001_pg_init | initial postgres schema with pgvector | None |
| 2 | ed902312e4ac | add role column to users | 0001_pg_init |
| 3 | 9bb18657d55d | add cards and categories tables | ed902312e4ac |
| 4 | 638a23f7c9ed | add card_progress table | 9bb18657d55d |
| 5 | fdc5af6f825f | add fsrs_step to card_progress | 638a23f7c9ed |
| 6 | 802d5ba2e219 | add gamification tables | fdc5af6f825f |
| 7 | c9863b51075d | add email_preferences table | 802d5ba2e219 |
| 8 | b1674f79f780 | add cards.deleted_at for soft delete | c9863b51075d |
| 9 | d3a7e2f91c04 | add persona and onboarding_completed to users | b1674f79f780 |
| 10 | e5b2c8d4a1f7 | add card_feedback table | d3a7e2f91c04 |
| 11 | 83a02cb65464 | add stripe_events table for webhook idempotency | e5b2c8d4a1f7 |
| 12 | a4f1d8e73b92 | add missions and mission_days tables | 83a02cb65464 |
| 13 | 74a6fb27a181 | add target_company and target_date to users | a4f1d8e73b92 |
| 14 | f75789e4967f | add registration_logs table | 74a6fb27a181 |
| 15 | e4eab11b8e33 | add scan_id + skills_matched + skills_missing to tracker | f75789e4967f |
| 16 | d16ca29a5d08 | add categories.tags + cards partial index for active rows | e4eab11b8e33 |
| 17 | 59795ca196e9 | add IVFFlat ANN index on cards.embedding | d16ca29a5d08 |
| 18 | 02bf7265b387 | rename users target columns + migrate persona enum values | 59795ca196e9 |
| 19 | f3350dcba3a5 | add interview_question_sets table | 02bf7265b387 |
| 20 | 1176cc179bf0 | add paywall_dismissals and user.downgraded_at | f3350dcba3a5 |
| 21 | 508df0110037 | add users.home_first_visit_seen_at — B-016 | 1176cc179bf0 |
| 22 | 538fe233b639 | add admin_audit_log — E-018a | 508df0110037 |
| 23 | 9543aa466524 | add interview_date to tracker_applications_v2 + partial index — E-042-impl-BE | 538fe233b639 |
| 24 | eb59d4fc1f7e | backfill tracker.interview_date from users.interview_target_date | 9543aa466524 |
| 25 | 30bf39fa04f8 | add analysis_payload (JSONB, deferred) to tracker_applications_v2 — B-035 / spec #59 | eb59d4fc1f7e |
| 26 | 57951e9f4cdc | phase6 foundation schema — decks, lessons, quiz_items, quiz_item_progress (B-061 / Phase 6 slice 6.1) | 30bf39fa04f8 |

Head = `57951e9f4cdc`. **Delta since `8a0402e` baseline: +1 revision** (row 26 — `57951e9f4cdc` Phase 6 foundation schema). Row 26 was added to §5 in-place at the slice-6.1 impl commit (`a989539`) per R19 targeted regen; this regen merely refreshes the footer copy to be accurate as of HEAD `17bf188`.

---

## Section 6 — Frontend routes (live component graph)

Configured in `src/App.tsx`. Top-level wrappers: `<AppShell>` (always), `<ProtectedRoute>` (auth gate) which wraps `<PersonaGate>` (persona null → `/onboarding/persona`), `<Suspense>` for lazy pages.

| Path | Component | Layout wrapper | Auth / persona guard | Notes |
|------|-----------|----------------|----------------------|-------|
| `/` | `HomeRoute` → `LandingPage` (guest) / `<Navigate to="/home">` (auth) | AppShell (chromeless) | none | — |
| `/login` | `LoginPage` | AppShell (chromeless) | none | — |
| `/pricing` | `Pricing` | AppShell (chromeless for guest, **chrome for authed users**) | none | B-057 (`19326de`) — auth-aware carve-out; authed users hitting paywall flows (StudyDashboard quota → /pricing) keep nav so they can navigate away |
| `/home` | `HomeDashboard` | AppShell | ProtectedRoute → PersonaGate | — |
| `/onboarding` | `Onboarding` | AppShell | ProtectedRoute → PersonaGate | — |
| `/onboarding/persona` | `PersonaPicker` | AppShell (chromeless) | ProtectedRoute (PersonaGate allow-listed) | — |
| `/first-action` | `FirstAction` | AppShell (chromeless) | ProtectedRoute → PersonaGate | — |
| `/learn` | `StudyDashboard` | AppShell | ProtectedRoute → PersonaGate | — |
| `/learn/daily` | `DailyReview` | AppShell | ProtectedRoute → PersonaGate | — |
| `/learn/category/:id` | `CategoryDetail` | AppShell | ProtectedRoute → PersonaGate | — |
| `/learn/card/:id` | `CardViewer` | AppShell | ProtectedRoute → PersonaGate | — |
| `/learn/lesson/:id` | `Lesson` | AppShell | ProtectedRoute → PersonaGate | NEW — Phase 6 slice 6.3 (`ba00331`). Eager-loaded inside `/learn/*` block (D-10). Fires `lesson_viewed` once per mount. 404 → "Lesson not found" + Back-to-Learn link (OQ-6). |
| `/prep` → `/prep/analyze` | `<Navigate replace>` | AppShell | ProtectedRoute | B-034 fix |
| `/prep/analyze` | `Analyze` | AppShell | ProtectedRoute → PersonaGate | spec #60 / B-045 — pre-flight scan-exhausted gate |
| `/prep/results` | `Results` | AppShell | ProtectedRoute → PersonaGate | B-035 / spec #59 — `?scan_id=` URL hydration |
| `/prep/rewrite` | `Rewrite` | AppShell | ProtectedRoute → PersonaGate | — |
| `/prep/interview` | `Interview` | AppShell | ProtectedRoute → PersonaGate | — |
| `/prep/tracker` | `Tracker` | AppShell | ProtectedRoute → PersonaGate | — |
| `/profile` | `Profile` (lazy) | AppShell | ProtectedRoute → PersonaGate | — |
| `/admin` | `<AdminLayout>` (lazy) — sidebar shell with nested `<Outlet />`; `<Route index>` redirects to `/admin/cards` | AppShell | ProtectedRoute → `AdminGate` | NEW shape — Phase 6 slice 6.4a (`b0806d0`). Was `<AdminPanel>` (lazy, 868-line monolith); extracted per spec #04 §12 D-12 — old `pages/AdminPanel.tsx` deleted. `<AdminGate>` continues wrapping all `/admin/*` routes per AC-4 (E-040 behavior preserved). Sidebar navigates to **4** child routes (Cards / Decks / Lessons / Analytics); `/admin/audit` link is **intentionally absent** per spec #04 §12 D-14 — BE endpoint `GET /api/v1/admin/audit` (E-018a, `3b43772`) is live and un-consumed; FE consumer never built. Future FE consumer = file new BACKLOG row when product demand surfaces. |
| `/admin/cards` | `<AdminCards>` (lazy) | AppShell + AdminLayout `<Outlet />` | ProtectedRoute → `AdminGate` (inherited from parent) | Phase 6 slice 6.4a — extracted cards CRUD + AI draft + bulk-import from old `AdminPanel.tsx`; byte-identical behavior at the new mount per AC-2. |
| `/admin/decks` | `<AdminDecks>` (lazy) | AppShell + AdminLayout `<Outlet />` | ProtectedRoute → `AdminGate` (inherited) | Phase 6 slice 6.4b-2 (`634f633`) — overwrites the 6.4a "Coming in slice 6.4b" placeholder with deck-list editor surface. Lists decks with `?status=` filter, create-deck button, row links to `/admin/decks/:deckId`. Uses `useAdminDecks` hook backed by `adminListDecks(status)` API helper. Fires `admin_decks_view` event (internal). |
| `/admin/decks/:deckId` | `<AdminDeckDetail>` (lazy) | AppShell + AdminLayout `<Outlet />` | ProtectedRoute → `AdminGate` (inherited) | NEW — Phase 6 slice 6.4b-2 (`634f633`). Deck-detail editor: form for `slug` / `title` / `description` / `display_order` / `icon` / `persona_visibility` / `tier`; PATCH triggers `<ConfirmPersonaNarrowingModal>` when `persona_visibility` narrows (helper `computeRemovedPersonas` co-located in modal file); modal uses D-19 amended copy per `de1e9a9` ("personas X, Y" array delta, no N count, no preview endpoint). Lessons sub-list with link to `/admin/lessons/:lessonId` (state-threads `deckId` per JC #3). Uses `useAdminDeckDetail` hook resolving deck via `adminListDecks('all')` paged scan (slice ships no single-record admin GET — JC #4). Archive button calls `adminArchiveDeck`. |
| `/admin/lessons` | `<AdminLessons>` (lazy) — placeholder | AppShell + AdminLayout `<Outlet />` | ProtectedRoute → `AdminGate` (inherited) | Phase 6 slice 6.4b-2 (`634f633`) — overwrites the 6.4a "Pick a deck to author lessons" placeholder; current scope renders deck-list redirect surface or guidance copy (real authoring UX is at `/admin/lessons/:lessonId` per the editor pattern). |
| `/admin/lessons/:lessonId` | `<AdminLessonEditor>` (lazy) | AppShell + AdminLayout `<Outlet />` | ProtectedRoute → `AdminGate` (inherited) | NEW — Phase 6 slice 6.4b-2 (`634f633`). Lesson editor: `<MarkdownEditor>` instances for `concept_md` / `production_md` / `examples_md` (edit/preview tabs via `react-markdown` + `remark-gfm`). Substantive-edit detection via `classifyLessonEdit(before, after)` from `src/utils/lessonEdit.ts` — opens `<ConfirmCascadeModal>` pre-PATCH when threshold exceeded. Modal renders cascade warning ("retiring N active quiz_items") + post-PATCH results-view per spec §6.6 D-8. 409 retry path uses one-shot `conflictRetry` guard (JC #2 of slice 6.4b-2): flips classification on the pending PATCH and re-fires the cascade modal. Publish + Archive buttons hit `adminPublishLesson` / `adminArchiveLesson`. `useAdminLessonEditor` resolves lesson via `adminListLessons(deckId, 'all')` paged scan; `deckId` threads via React Router `state` from AdminDeckDetail (JC #3). |
| `/admin/lessons/:lessonId/quiz-items` | `<AdminQuizItems>` (lazy) | AppShell + AdminLayout `<Outlet />` | ProtectedRoute → `AdminGate` (inherited) | NEW — Phase 6 slice 6.4b-2 (`634f633`). Quiz-item editor: list active + retired quiz_items for the lesson; create-quiz-item form with `question_type` enum select + distractors-required-when-mcq UX; PATCH dispatches retire-and-replace via 409 mismatch flow same as lesson PATCH; retire button calls `adminRetireQuizItem`. `useAdminQuizItems` hook + `adminListQuizItems(lessonId, status)` API helper. |
| `/admin/analytics` | `<AdminAnalytics>` (lazy) | AppShell + AdminLayout `<Outlet />` | ProtectedRoute → `AdminGate` (inherited) | spec #38 E-018b. Mount preserved post-6.4a — moved from top-level route to nested-child of `<AdminLayout>` per AC-3. |
| `/analyze` → `/prep/analyze` | `<Navigate replace>` | AppShell | none | transitional |
| `/results` → `/prep/results` | `<Navigate replace>` | AppShell | none | transitional |
| `/rewrite` → `/prep/rewrite` | `<Navigate replace>` | AppShell | none | transitional |
| `/interview` → `/prep/interview` | `<Navigate replace>` | AppShell | none | transitional |
| `/tracker` → `/prep/tracker` | `<Navigate replace>` | AppShell | none | transitional |
| `/study` → `/learn` | `<Navigate replace>` | AppShell | none | transitional |
| `/study/daily` → `/learn/daily` | `<Navigate replace>` | AppShell | none | transitional |
| `/study/category/:id` → `/learn/category/:id` | `RedirectWithParam` | AppShell | none | transitional |
| `/study/card/:id` → `/learn/card/:id` | `RedirectWithParam` | AppShell | none | transitional |
| `/mission` → `/learn/mission` | `<Navigate replace>` | AppShell | none | transitional |
| `*` | `<Navigate to="/" replace>` | AppShell | none | catch-all |

Nav chrome rendered by `AppShell` (`TopNav` desktop, `MobileNav` mobile). Chromeless-by-default paths in `AppShell.CHROMELESS_PATHS`: `/`, `/login`, `/onboarding/persona`, `/first-action`. **Auth-aware carve-out (B-057, `19326de`):** `/pricing` is chromeless when `user === null` (guest) but renders chrome when authed — implemented as `pathname === '/pricing' && user === null` in both `AppShell.tsx` (`useAuth()` import) and `MobileNav.tsx` (its own `HIDDEN_PATHS = ['/', '/login']` set + the same one-line carve-out for `/pricing`). The two carve-outs are duplicated rather than lifted to a shared module — see §11 drift item B-058.

**TopNav composition (desktop, `md:block`):** wordmark `SKILL/FORGE` → `/home`; nav links (`Home` / `Learn` / `Prep` / `Admin` if admin — `Profile` removed in B-029); right = `<UserMenu />` (avatar dropdown — Profile + `Sign out` button; B-028, B-029).

**MobileNav composition (`md:hidden`):** five-tab bottom bar (Home/Learn/Prep/Profile/Admin) — no sign-out surface; mobile users sign out via Profile → Account section.

**Wall-aware components (spec #50 + spec #63):** `src/components/study/QuizPanel.tsx` is the single submit chokepoint for `POST /api/v1/study/review` — consumed by `DailyReview`, `CardViewer`, `MissionMode`. On a 402 with `detail.trigger === 'daily_review'`, opens `PaywallModal trigger="daily_review"` and fires `daily_card_wall_hit { surface: "daily_review_submit" }`. **Pre-flight (B-059, `20562ea`):** `src/components/study/DailyReviewWalledView.tsx` renders full-page upsell on `/learn/daily` mount when `plan==='free' && !isAdmin && daily_status.can_review===false`; fires `daily_card_wall_hit { surface: "daily_review_page_load" }` once per mount via `useRef` guard. `formatResetsAt` / `hoursUntil` lifted from private `QuizPanel.tsx` to `src/utils/wallCountdown.ts` for reuse.

### Component graph (73 components, organized by directory)

> **BE-side note (slice 6.4b-1, `d6bda3b`):** `app/data/lesson_fixtures.py` (185 lines) + `app/data/__init__.py` removed in lockstep with `lesson_service.py` body-swap to DB queries (selectinload per spec §12 D-15). FE component graph below is FE-only; the deletion is recorded in §4 `lesson_service.py` row + §1 BE service-files counter.

| Directory | Components |
|-----------|-----------|
| **`admin/`** *(slice 6.4a, `b0806d0`; +3 components slice 6.4b-2, `634f633`)* | **AdminLayout** *(slice 6.4a — multi-route admin shell. Renders `<nav aria-label="Admin sections">` sidebar with 4 `<NavLink>` children (Cards / Decks / Lessons / Analytics; `/admin/audit` absent per spec #04 §12 D-14) + `<Outlet />` for nested admin route children. Wrapped externally by `<ProtectedRoute><AdminGate>` in `App.tsx` per AC-4. Active link surfaces via `aria-current="page"` (set automatically by react-router `<NavLink>`). Consumes `<PageWrapper>` for chrome.)*, **MarkdownEditor** *(NEW — slice 6.4b-2. Edit/preview-tab markdown editor backed by `react-markdown` + `remark-gfm` (slice-6.3 transitive dep, no new install). Used by `AdminLessonEditor` for `concept_md` / `production_md` / `examples_md` fields. Internal tab state, no external state required. Token-only styling per R12.)*, **ConfirmCascadeModal** *(NEW — slice 6.4b-2. Pre-PATCH cascade warning + post-PATCH results-view per spec §6.6 D-8. Two-phase: (1) confirm with cascade-impact summary ("retiring N active quiz_items"), (2) post-PATCH renders `LessonUpdateResponse.quiz_items_retired_count` + IDs. Used by `AdminLessonEditor` substantive-edit flow + post-409 retry path.)*, **ConfirmPersonaNarrowingModal** *(NEW — slice 6.4b-2. D-19 amended-copy modal per `de1e9a9`: "Narrowing persona visibility will hide this deck from learners currently in personas X, Y. Their existing FSRS progress on quiz_items in this deck is preserved but they will no longer see the deck in /learn surfaces. Continue?" — array-delta copy, NO N-count, NO preview endpoint per §4.1.1 service-layer warning-free invariant. Co-located helper `computeRemovedPersonas(before, after) → string[]` exported alongside the modal component. Used by `AdminDeckDetail` PATCH flow.)* |
| `auth/` | AdminGate |
| `dashboard/` (Results page sub-components) | ATSScoreGauge, BulletAnalyzer, FormattingIssues, ImprovementSuggestions, JobFitExplanation, KeywordChart, MissingSkillsPanel, PanelSection, ScoreBreakdown, SkillOverlapChart |
| `home/` | DashboardWidget, InterviewDateModal *(B-037 — inline date editor)*, StateAwareWidgets *(B-051 — switched from internal `useHomeState` call to prop-driven, accepts `{persona, data, isLoading, error}` so HomeDashboard's single hook call feeds both this component and §3 composition-suppression flags)* |
| `home/widgets/` (15 widgets) | CountdownWidget *(B-051: gained `suppressedByMissionState` prop — suppressed when state slot fires AND `context.mission_target_date === user.interview_target_date`, per-mission carve-out per spec #61 §3.1)*, FirstSessionDoneWidget, InactiveReturnerWidget, InterviewPrepperChecklist, InterviewTargetWidget *(B-051: `suppressedByMissionState` prop — broader rule, suppressed whenever Mission state slot renders per LD-3)*, LastScanWidget *(B-051: `suppressed` prop — suppressed when StudyGapsPromptWidget eligibility resolves true; scan content rolled into the prompt body, audit #3)*, MissionActiveWidget *(B-051: gained Pro stale-scan footer per spec #61 §6)*, MissionOverdueWidget, ResumeStaleWidget *(B-051: free users now route to `setShowUpgradeModal` / PaywallModal instead of inline upgrade copy)*, StreakAtRiskWidget, StreakWidget, **StudyGapsPromptWidget** *(NEW — B-051, `ecef895`. Renders for `plan==='free' && !isAdmin && has_recent_scan && !has_active_mission`. Primary CTA `/learn?source=last_scan` (LD-1 LOCKED), secondary upgrade CTA opens PaywallModal `trigger='skill_gap_study'`. Fires `home_study_gaps_prompt_shown` on mount + `home_study_gaps_clicked {cta: 'primary'\|'secondary_upgrade'}` on click. Closes audit #3, #4, #5)*, TeamComingSoonWidget, TodaysReviewWidget, WeeklyProgressWidget |
| `layout/` | AppShell *(B-057: added `useAuth` import + `pathname === '/pricing' && user === null` guest-only carve-out alongside `CHROMELESS_PATHS = {'/', '/login', '/onboarding/persona', '/first-action'}`)*, MobileNav *(B-057: same one-line carve-out + `useAuth` import; `HIDDEN_PATHS = {'/', '/login'}`; the duplicated set is tracked at §11 drift item B-058)*, **Navbar** *(orphan; see §9)*, PageWrapper, TopNav, UserMenu |
| `lesson/` | **LessonRenderer** *(NEW — Phase 6 slice 6.3, `ba00331`. Four-section lesson card: concept_md / production_md / examples_md / quiz panel. `react-markdown` + `remark-gfm` (D-3) — no `dangerouslySetInnerHTML`. Mobile-first concept-expanded-by-default with collapse toggle that fires `lesson_section_expanded`; desktop renders all sections via `hidden md:block` per OQ-3.)*, **QuizItemPanel** *(NEW — Phase 6 slice 6.3, `ba00331`. Quiz-submit panel scoped to a single `quiz_item`. State machine: idle → revealed → submitting → done/error. Posts to `POST /api/v1/quiz-items/review` (slice 6.2 endpoint, D-5). mcq renders answer + distractors as 4 radios. 409 / 403 surface inline error per OQ-4. NOT a rename of `study/QuizPanel.tsx` — both coexist until slice 6.15 retires the legacy card flow per D-7.)* |
| `mission/` | Countdown, DailyTarget, MissionDateGate, MissionSetup |
| `onboarding/` | **GuidedTour** *(orphan; see §9)* |
| `profile/` | StreakBadge, XPBar |
| `progress/` | ActivityHeatmap, SkillRadar |
| `rewrite/` | CoverLetterViewer, ResumeEditor, **ResumePDFTemplate** *(orphan; see §9)* |
| `settings/` | EmailPreferences, ThemePicker |
| `study/` | CategoryCard, **DailyReviewWalledView** *(NEW — B-059, `20562ea`. Full-page upsell rendered by `DailyReview.tsx` when free user is at cap. Props-only, no context deps. Locked headline "You've used today's free reviews" + countdown subhead via `formatResetsAt` + Upgrade-to-Pro CTA → `/pricing` (relies on B-057 chrome carve-out, AC-7) + Back-to-home CTA. Mirrors spec #60 / B-045 Analyze pre-flight pattern)*, FlipCard, QuizPanel *(B-059: submit-time `capture('daily_card_wall_hit')` payload now includes `surface: 'daily_review_submit'` per AC-6 regression-pin)*, WallInlineNudge |
| `tracker/` | ApplicationCard, KanbanBoard |
| `ui/` | AnimatedCard, GlowButton, ProgressBar, ScoreBadge, SkeletonLoader, Tooltip, UpgradeModal |
| `upload/` | JDInput, ResumeDropzone |
| `components/` (root) | PaywallModal, PersonaGate |

---

## Section 7 — Frontend pages

| File | Default export | Top-level data hooks | API calls | PostHog events |
|------|----------------|----------------------|-----------|----------------|
| **admin/AdminCards.tsx** *(NEW — Phase 6 slice 6.4a, `b0806d0`)* | AdminCards | — | fetchAdminCards, fetchCategories, createAdminCard, updateAdminCard, deleteAdminCard, generateCardDraft, importCardsCSV | — | Extracted from old `pages/AdminPanel.tsx` (deleted) per spec #04 §12 D-12. Cards CRUD + AI draft + CSV import surface — byte-identical at the new `/admin/cards` mount per AC-2. Redundant in-page auth gate (was unreachable since `<AdminGate>` 403s non-admins) dropped during extraction. |
| **admin/AdminDecks.tsx** *(slice 6.4a placeholder; rewritten slice 6.4b-2, `634f633`)* | AdminDecks | useAdminDecks | adminListDecks (via hook) | admin_decks_view | Phase 6 slice 6.4b-2 — overwrites the 6.4a "Coming in slice 6.4b" placeholder with deck-list editor. `?status=active\|archived\|all` filter dropdown bound to `useAdminDecks(status)`; row links to `/admin/decks/:deckId`; create-deck inline form posts to `adminCreateDeck`. Token-only styling per R12. `react-hook-form` for the create form per D-13. |
| **admin/AdminDeckDetail.tsx** *(NEW — Phase 6 slice 6.4b-2, `634f633`)* | AdminDeckDetail | useAdminDeckDetail | adminUpdateDeck, adminArchiveDeck | admin_deck_detail_view, admin_deck_persona_narrow_confirm | Deck-detail editor page mounted at `/admin/decks/:deckId`. Form for all `Deck` writable fields; PATCH triggers `<ConfirmPersonaNarrowingModal>` when persona-visibility narrows (helper `computeRemovedPersonas` co-located in modal file); modal copy per D-19 amended `de1e9a9`. Lessons sub-list links to `/admin/lessons/:lessonId` with `state={{deckId}}` per JC #3. Hook resolves deck via `adminListDecks('all')` paged scan since slice ships no single-record admin GET (JC #4). 404 surface "Deck not found" + back-to-`/admin/decks` link. |
| **admin/AdminLessons.tsx** *(slice 6.4a placeholder; rewritten slice 6.4b-2, `634f633`)* | AdminLessons | — | — | — | Phase 6 slice 6.4b-2 — overwrites the 6.4a "Pick a deck to author lessons" placeholder. Current scope renders top-level lessons-namespace landing surface; real authoring UX lives at `/admin/lessons/:lessonId` via `<AdminLessonEditor>`. |
| **admin/AdminLessonEditor.tsx** *(NEW — Phase 6 slice 6.4b-2, `634f633`)* | AdminLessonEditor | useAdminLessonEditor | adminUpdateLesson, adminPublishLesson, adminArchiveLesson | admin_lesson_editor_view, admin_lesson_substantive_confirm, admin_lesson_409_retry | Lesson editor mounted at `/admin/lessons/:lessonId`. Three `<MarkdownEditor>` instances for `concept_md` / `production_md` / `examples_md`. FE-side classification via `classifyLessonEdit(before, after)` from `src/utils/lessonEdit.ts` — pre-PATCH `<ConfirmCascadeModal>` opens when threshold exceeded. Post-PATCH modal renders cascade outcome from `LessonUpdateResponse.quiz_items_retired_*`. 409 `EditClassificationConflictError` retry path uses one-shot `conflictRetry` guard per JC #2 of slice 6.4b-2 — flips classification on the pending PATCH and re-fires the cascade modal; second 409 surfaces inline error rather than infinite-looping. Hook resolves lesson via `adminListLessons(deckId, 'all')` paged scan; `deckId` threads from `AdminDeckDetail` → `AdminLessonEditor` via React Router `<Link state>` per JC #3. `react-hook-form` per D-13 for non-markdown fields. |
| **admin/AdminQuizItems.tsx** *(NEW — Phase 6 slice 6.4b-2, `634f633`)* | AdminQuizItems | useAdminQuizItems | adminListQuizItems, adminCreateQuizItem, adminUpdateQuizItem, adminRetireQuizItem | admin_quiz_items_view, admin_quiz_item_retire_confirm | Quiz-item editor at `/admin/lessons/:lessonId/quiz-items`. Lists active + retired quiz_items via `?status=` filter; create-quiz-item form with `question_type` enum select + distractors-required-when-mcq Pydantic-mirrored UX; PATCH dispatches retire-and-replace via 409-mismatch flow (same shape as lesson PATCH). Retire button calls `adminRetireQuizItem` with optional `superseded_by_id` for admin-curated supersession. `react-hook-form` per D-13. |
| AdminAnalytics.tsx | AdminAnalytics | useAuth | fetchAdminAnalyticsMetrics, fetchAdminAnalyticsPerformance | admin_analytics_segment_changed | Mount path `/admin/analytics` preserved post-6.4a; route now nested under `<AdminLayout>` `<Outlet />` per AC-3. Page component itself unchanged. |
| Analyze.tsx | Analyze | useAnalysis, useUsage | — | paywall_hit *(spec #60 / B-045 — `{trigger: 'scan_limit', surface: 'analyze_page_load', plan: 'free'}` once-on-mount via `useRef` guard when `!canScan && plan==='free' && !isAdmin`)* |
| CardViewer.tsx | CardViewer | useCardViewer, useGamification | — | card_viewed |
| CategoryDetail.tsx | CategoryDetail | — | fetchCardsByCategory | category_detail_viewed |
| DailyReview.tsx | DailyReview | useGamification, useAuth, useUsage | fetchDailyQueue | daily_review_started, daily_review_completed, daily_card_wall_hit *(B-059 — fires once on walled mount via `useRef` guard with `surface: 'daily_review_page_load'`; only when `plan==='free' && !isAdmin && data.daily_status.can_review===false`)*. **Pre-flight gate (B-059, `20562ea`):** if free user is at cap, renders `<DailyReviewWalledView resetsAt={resetsAt} />` in place of queue. Imports `hoursUntil` from `@/utils/wallCountdown`. |
| FirstAction.tsx | FirstAction | useAuth | — | first_action_viewed, first_action_primary_clicked, first_action_secondary_clicked |
| HomeDashboard.tsx | HomeDashboard | useAuth, useUsage, useHomeState *(single call, B-051; was internal to StateAwareWidgets)* | markHomeFirstVisit *(B-016)*, fetchActiveMission, fetchUserApplications | home_dashboard_viewed. Greeting fork: `isFirstVisit` snapshotted on mount via `useState(() => user.home_first_visit_seen_at == null)` (B-027). **Composition refactor (B-051, `ecef895`, spec #61 §3):** single `useHomeState()` call resolves at the page level; derives `topState` + `missionStateActive` + `missionTargetMatchesUser`; passes three suppression flags down to `InterviewPrepperMode` (`countdownSuppressedByMissionState`, `interviewTargetSuppressedByMissionState`, `lastScanSuppressed`). State-slot data flows to `StateAwareWidgets` as a prop (no double-fetch). Free-tier `StudyGapsPromptWidget` mounts on `plan==='free' && !isAdmin` branches; its eligibility predicate (`has_recent_scan && !has_active_mission`) feeds back into `lastScanSuppressed`. CareerClimber + TeamLead modes preserved verbatim. |
| Interview.tsx | Interview | useAnalysisContext, useUsage, useInterview | generateInterviewPrep | interview_questions_regenerated, interview_questions_cached_served |
| LandingPage.tsx | LandingPage | useAuth, usePricing | — | landing_page_viewed, cta_clicked |
| Lesson.tsx | LessonPage | useLesson, useAuth, useUsage | fetchLesson *(via `useLesson`)* | lesson_viewed *(NEW — Phase 6 slice 6.3, `ba00331`. Fires once per mount via `useRef` idempotency guard. Payload: `{lesson_id, deck_id, deck_slug, version, persona, plan}`. Mirrors `home_dashboard_viewed` precedent. NOTE: lesson_section_expanded is fired by the child `LessonRenderer` component, not the page; quiz_item_progress_initialized + quiz_item_reviewed fire from BE service-layer on submit per spec 6.3 §9 — no FE-side duplicate.)* |
| LoginPage.tsx | LoginPage | useAuth | signIn | — |
| MissionMode.tsx | MissionMode | useMission, useGamification | — | mission_created, mission_day_completed, mission_completed |
| Onboarding.tsx | Onboarding | useAnalysisContext | fetchOnboardingRecommendations | onboarding_started, onboarding_completed, gap_card_clicked |
| PersonaPicker.tsx | PersonaPicker | useAuth | updatePersona | persona_picker_shown, persona_selected, interview_target_date_added *(B-018, B-037)* |
| Pricing.tsx | Pricing | useUsage, usePricing, useSearchParams | createCheckoutSession | checkout_started, payment_completed |
| Profile.tsx | Profile | useAuth (incl. signOut), useUsage, useGamification | generateExperience, createBillingPortalSession, api.get | profile_viewed, subscription_portal_opened, experience_generated, sign_out_clicked *(B-028 — `{source: 'profile_page'}`)* |
| Results.tsx | Results | useAnalysisContext, useUsage | fetchOnboardingRecommendations, fetchAnalysisById *(B-035 / spec #59 — URL `?scan_id=` hydration with three-way empty-state)* | job_fit_explanation_viewed, results_tooltip_opened *(via `PanelSection`, 9-section enum)*, scan_rehydrated *(B-035)*. **Layout fix (B-055, `4b7f862`):** added `xl:row-end-5` to `ImprovementSuggestions` grid item (line 482) to distribute its height across rows 3–4 of col-3 instead of inflating row-3 alone. Closes the xl-breakpoint vertical void below Skills Radar / Jump-nav. DOM, ordering test invariants, 9 section IDs, and verbatim spec #21 tooltip copy all unchanged. |
| Rewrite.tsx | Rewrite | useAnalysisContext, useRewrite, useUsage | rewriteSection *(via `useRewrite.regenerateSection`)* | rewrite_requested, rewrite_section_regenerated. BE also emits `rewrite_succeeded` / `rewrite_failed` with `strategy=chunked\|fallback_full`. |
| StudyDashboard.tsx | StudyDashboard | useStudyDashboard, useAuth, useUsage, useGamification, useSearchParams | — | study_dashboard_viewed, locked_tile_clicked, category_tile_clicked, **study_dashboard_source_hint_shown** *(NEW — B-052/B-053, `df035e1`. `{source: 'last_scan', persona, copy_variant: '6A'}` — fires once per mount via `useRef` idempotency when URL has `?source=last_scan`. Param is attribution-only — does NOT filter the category grid; only renders a `motion.div` hero hint between header and "Your Goal" card with a dismiss × button. Component-state dismissal (no sessionStorage). URL preserved (no `setSearchParams`). Locked variant `'6A'` neutral copy per spec #62 §10 OQ-1.)* |
| Tracker.tsx | Tracker | useTracker | — | — |

---

## Section 8 — Frontend shared types

`src/types/index.ts` (506 lines, authoritative for API DTOs) + `src/types/homeState.ts` (28 lines, home dashboard only).

| Type | Shape (compact) | Import count |
|------|-----------------|--------------|
| `ATSScoreBreakdown` | `{ keyword_match, skills_coverage, formatting_compliance, bullet_strength: number }` | 2 |
| `SkillGap` | `{ skill: string, category: Technical\|Soft\|Certification\|Tool, importance: critical\|recommended\|nice-to-have }` | 3 |
| `BulletAnalysis` | `{ original, rewritten: string, score: number, issues: string[] }` | — |
| `FormattingIssue` | `{ issue: string, severity: critical\|warning\|info, fix: string }` | — |
| `KeywordChartData` | `{ keyword: string, resume_count, jd_count: number, matched: boolean }` | — |
| `SkillOverlapData` | `{ subject: string, resume, jd: number }` | — |
| `AnalysisResponse` | `{ scan_id?, ats_score, grade, score_breakdown, matched_keywords, missing_keywords, skill_gaps, bullet_analysis, formatting_issues, job_fit_explanation, top_strengths, top_gaps, keyword_chart_data, skills_overlap_data, resume_text? }` | 2 |
| `RewriteEntry` | `{ org, location, date, title: string, bullets, details: string[] }` | — |
| `RewriteSection` | `{ title, content: string, entries: RewriteEntry[] }` | — |
| `RewriteHeader` | `{ name, contact: string }` | — |
| `RewriteResponse` | `{ header, sections, full_text, template_type }` | 6 |
| `CoverLetterRecipient` | `{ name, company: string }` | — |
| `CoverLetterResponse` | `{ date, greeting, signoff, signature, tone, full_text: string, recipient: CoverLetterRecipient, body_paragraphs: string[] (len==3) }` | 5 |
| `InterviewQuestion` | `{ question: string, star_framework: string }` | 1 |
| `InterviewPrepResponse` | `{ questions: InterviewQuestion[], cached?, generated_at?, model_used? }` | 3 |
| `ApplicationStatus` | `Applied\|Interview\|Offer\|Rejected` | — |
| `TrackerApplication` | `{ id, company, role, date_applied, status, ats_score, scan_id?, skills_matched?[], skills_missing?[], created_at }` | 6 |
| `Category` | `{ id, name, icon, color, display_order, source: foundation\|premium, card_count, studied_count, locked }` | 16 |
| `Card` | `{ id, category_id, category_name, question, answer, difficulty, tags[], created_at, updated_at }` | 28 |
| `FsrsRating` | `1\|2\|3\|4` | — |
| `ReviewRequest` | `{ card_id, session_id: string, rating: FsrsRating, time_spent_ms? }` | — |
| `ReviewResponse` | `{ card_id, fsrs_state, due_date, stability, difficulty, reps, lapses, scheduled_days }` | — |
| `DailyCard` | `{ card_id, question, answer, category_id, category_name, difficulty, tags[], fsrs_state, due_date, reps, lapses }` | 3 |
| `DailyStatus` *(NEW — B-059)* | `{ cards_consumed: number, cards_limit: number, can_review: boolean, resets_at: string }` — read-side mirror of free-tier daily-card wall counter. `cards_limit === -1` is the unlimited sentinel for Pro / Enterprise / admin (matches `usage_service` / `UsageContext` `-1` convention). FE-canonical name; BE-canonical is `app/schemas/study.py::DailyStatus`. | 1 |
| `DailyQueueResponse` *(B-059 — additive)* | `{ cards: DailyCard[], total_due: number, session_id: string, daily_status?: DailyStatus }` — `daily_status` is optional (only populated by `GET /api/v1/study/daily` when authed; `null`/`undefined` for legacy callers and unauthed paths). | — |
| `MissionDayView` | `{ day_number, date, cards_target, cards_completed }` | — |
| `MissionResponse` | `{ id, title, target_date, category_ids[], daily_target, total_cards, days_remaining, status: active\|completed\|abandoned, progress_pct, created_at }` | 3 |
| `MissionDetailResponse` | `MissionResponse + { days: MissionDayView[] }` | — |
| `MissionDailyCard` | `{ id, question, answer, category, difficulty }` | — |
| `MissionDailyResponse` | `{ mission_id, day_number, date, cards_target, cards_completed, cards[] }` | — |
| `MissionDayCompleteResponse` | `{ mission_id, day_number, cards_completed, cards_target, xp_awarded, mission_status }` | — |
| `MissionCreateRequest` | `{ title, target_date: string, category_ids: string[] }` | — |
| `RecommendedCategory` | `{ category_id, name, icon, color, matched_card_count, similarity_score\|null }` | — |
| `GapMapping` | `{ gap, match_type: tag\|semantic\|none, matching_categories: RecommendedCategory[] }` | — |
| `OnboardingRecommendationsResponse` | `{ scan_id\|null, results: GapMapping[] }` | — |
| `BadgeView` | `{ badge_id, name, earned_at }` | — |
| `GamificationStats` | `{ user_id, current_streak, longest_streak, total_xp, last_active_date\|null, freezes_available, badges[] }` | 3 |
| `EmailPreference` | `{ user_id, daily_reminder, timezone }` | 4 |
| `EmailPreferenceUpdate` | `{ daily_reminder?, timezone? }` | — |
| `AdminCard` | `{ id, category_id, category_name, question, answer, difficulty, tags[], embedding_status: pending\|ready, created_at, updated_at }` | 3 |
| `AdminCardListResponse` | `{ cards, total, page, per_page, pages }` | — |
| `AdminCardCreateRequest` | `{ category_id, question, answer, difficulty, tags }` | — |
| `AdminCardUpdateRequest` | `Partial<AdminCardCreateRequest>` | — |
| `CardDraft` | `{ question, answer, difficulty, tags }` | 3 |
| `CardImportResponse` | `{ created_count, skipped_count, errors[] }` | — |
| `AnalysisState` | `{ isLoading, error, result, resumeFile, jobDescription }` | — |
| `AnalysisAction` | discriminated union (6 action types) | — |
| `PersonaVisibility` *(NEW — Phase 6 slice 6.3)* | `'climber' \| 'interview_prepper' \| 'both'` — mirrors `app/schemas/deck.py::PersonaVisibility` Literal. | 1 |
| `DeckTier` *(NEW — Phase 6 slice 6.3)* | `'foundation' \| 'premium'` — mirrors `app/schemas/deck.py::DeckTier`. Drives free-vs-Pro deck filtering in slice 6.7. | 1 |
| `LessonVersionType` *(NEW — Phase 6 slice 6.3)* | `'initial' \| 'minor_edit' \| 'substantive_edit'` — mirrors `app/schemas/lesson.py::LessonVersionType`. Substantive edits retire quiz_items. | 1 |
| `QuestionType` *(NEW — Phase 6 slice 6.3)* | `'mcq' \| 'free_text' \| 'code_completion'` — mirrors `app/schemas/quiz_item.py::QuizQuestionType`. `mcq` is the only variant that uses `distractors`. | 1 |
| `QuizDifficulty` *(NEW — Phase 6 slice 6.3)* | `'easy' \| 'medium' \| 'hard'` — mirrors `app/schemas/quiz_item.py::QuizDifficulty` (authored hint, NOT FSRS-managed difficulty — that lives on `quiz_item_progress.difficulty_fsrs`). | 1 |
| `Deck` *(NEW — Phase 6 slice 6.3)* | `{ id, slug, title, description, display_order: number, icon: string\|null, persona_visibility: PersonaVisibility, tier: DeckTier, created_at, updated_at, archived_at: string\|null }` — field-for-field mirror of `app/schemas/deck.py::DeckResponse`. | 1 |
| `Lesson` *(NEW — Phase 6 slice 6.3)* | `{ id, deck_id, slug, title, concept_md, production_md, examples_md, display_order, version: number, version_type: LessonVersionType, published_at: string\|null, generated_by_model: string\|null, source_content_id: string\|null, quality_score: number\|null, created_at, updated_at, archived_at: string\|null }` — field-for-field mirror of `app/schemas/lesson.py::LessonResponse`. `quality_score` is `number\|null` on FE; BE Pydantic ships as `Decimal` and serializes to JSON number. | 2 |
| `QuizItem` *(NEW — Phase 6 slice 6.3)* | `{ id, lesson_id, question, answer, question_type: QuestionType, distractors: string[]\|null, difficulty: QuizDifficulty, display_order, version: number, superseded_by_id: string\|null, retired_at: string\|null, generated_by_model: string\|null, created_at, updated_at }` — field-for-field mirror of `app/schemas/quiz_item.py::QuizItemResponse`. | 2 |
| `LessonWithQuizzes` *(NEW — Phase 6 slice 6.3)* | `{ lesson: Lesson, quiz_items: QuizItem[], deck_id, deck_slug, deck_title }` — top-level deck fields lifted for FE breadcrumb / back-link without a second round-trip. Returned by `GET /api/v1/lessons/{id}`. Mirror of `app/schemas/lesson.py::LessonWithQuizzesResponse`. | 2 |
| `DeckWithLessons` *(NEW — Phase 6 slice 6.3)* | `{ deck: Deck, lessons: Lesson[] }` — returned by `GET /api/v1/decks/{id}/lessons`. Mirror of `app/schemas/deck.py::DeckLessonsResponse`. | 1 |
| `QuizReviewRequest` *(NEW — Phase 6 slice 6.3, FE-side mirror of slice 6.2 BE)* | `{ quiz_item_id, rating: 1\|2\|3\|4, session_id: string, time_spent_ms? }` — mirrors `app/schemas/quiz_item.py::QuizReviewRequest` (slice 6.2). FE re-declares the type rather than reaching into study-engine types per spec 6.3 §8.1. | 2 |
| `QuizReviewResponse` *(NEW — Phase 6 slice 6.3, FE-side mirror of slice 6.2 BE)* | `{ quiz_item_id, fsrs_state: 'learning'\|'review'\|'relearning', stability, difficulty, due_date: string, reps, lapses, scheduled_days: number }` — mirrors `app/schemas/quiz_item.py::QuizReviewResponse`. All values reflect post-review state; `scheduled_days` is fractional days from now to `due_date`. | 2 |

### Persona / auth types (defined in `src/context/AuthContext.tsx` — not in `types/`)

| Type | Shape | Notes |
|------|-------|-------|
| `Persona` | `'interview_prepper' \| 'career_climber' \| 'team_lead'` | imported by 24 files |
| `AuthUser` | `{ id, email, name, avatar_url\|null, role: user\|admin, persona: Persona\|null, onboarding_completed, interview_target_company?, interview_target_date? }` | direct import count 2; widely consumed indirectly via `useAuth()` |

### Home-state types (`src/types/homeState.ts`)

| Type | Shape |
|------|-------|
| `HomeStateName` | `'mission_overdue' \| 'streak_at_risk' \| 'mission_active' \| 'resume_stale' \| 'inactive_returner' \| 'first_session_done'` |
| `HomeStateContext` | `{ current_streak, last_review_at\|null, active_mission_id\|null, mission_target_date\|null, last_scan_date\|null, plan: free\|pro\|enterprise, last_activity_at\|null }` |
| `HomeStateResponse` | `{ persona, states: HomeStateName[], context: HomeStateContext }` |

> **§13 cross-ref:** `UsageContext` shape (FE state, not API DTO) — `scansRemaining` field DEFERRED per B-047 (gated on pre-existing `UsageContext.tsx` working-tree dirt resolution).

---

## Section 9 — Known-dead or transitional code

| Path | Why flagged | Suggested action |
|------|-------------|------------------|
| `hirelens-frontend/src/components/layout/Navbar.tsx` | `AppShell` only imports `TopNav`/`MobileNav`; no file imports `Navbar`. SESSION-STATE lists as Phase-6 cleanup (B-010). | delete |
| `hirelens-frontend/src/components/onboarding/GuidedTour.tsx` | Only self-reference; no page or component imports it. | delete (or migrate if there's design intent — see §12 Q1) |
| `hirelens-frontend/src/components/rewrite/ResumePDFTemplate.tsx` | Only self-reference. PDF export is generated inline via jsPDF in `Rewrite.tsx`. | delete (see §12 Q2) |
| `hirelens-backend/app/services/ai_service.py` | Duplicates `gpt_service.py` public API verbatim. Only consumed by the enterprise-only `/api/v1/resume/{id}/optimize` path. `[S47-defer]` in SESSION-STATE Deferred Hygiene flags it pending traffic check. | leave (tracked) |
| `hirelens-backend/app/services/llm/` directory (factory.py + claude_provider.py + gemini_provider.py) | Legacy provider abstraction parallel to `app/core/llm_router.py`. Phase-6 consolidation in Tech Debt. May still be imported by a non-router-aware path. | leave (Phase-6) |

No components found behind a `{false && …}` guard or dormant feature flag. Verified against current HEAD.

---

## Section 10 — Skills inventory

### Tracked skills (`.agent/skills/*.md`, 20 files)

| File | Description |
|------|-------------|
| admin-panel.md | Card CRUD, bulk import, AI-assisted card generation (Phase 3) |
| analytics.md | PostHog event catalog (frontend + backend), funnels, conventions |
| ats-card-bridge.md | Maps ATS scan skill gaps to study cards, powers onboarding flow |
| ats-scanner.md | ATS resume scanning, scoring, keyword extraction, bullet rewriting, auto-tracker |
| card-extraction.md | JSX → PostgreSQL card extraction pipeline |
| content-pipeline.md | End-to-end content pipeline — card extraction, AI generation, admin CRUD, bulk import |
| database-schema.md | Living reference of all database tables, columns, types, indexes, and relationships |
| db-migration.md | Database migration conventions, Alembic patterns, and schema change rules |
| design-system.md | Theme tokens, multi-theme switching, Tailwind integration, no-flash init |
| experience-gen.md | "My Experience" AI generation — personalized study narratives based on user's learning history |
| gamification.md | Streaks, XP, badges, skill radar, activity heatmap |
| geo-pricing.md | IP-based geo pricing (INR vs USD) with Redis caching and Stripe price ID routing |
| home.md | State-aware home dashboard — priority slot, state evaluator, Redis cache, invalidation |
| llm-strategy.md | LLM task tiering, provider routing, and the generate_for_task() interface |
| mission-mode.md | Interview sprint — countdown timer, daily targets, focused card set |
| notifications.md | Daily email reminders, email preferences, SendGrid/Resend integration |
| payments.md | Stripe checkout, webhooks, plan gating, free tier limits, geo pricing, usage caps |
| security.md | Auth hardening, rate limiting, CORS, request size, webhook idempotency, abuse prevention |
| study-engine.md | **(frontmatter has no `description:` field — see §11 drift #8; tracked at B-039 audit doc `docs/audits/SKILLS-SPECS-ALIGNMENT-2026-04-21.md`)** |
| testing.md | Test patterns, fixtures, mocks for SkillForge |

### Untracked skill surfaces (carried forward — unchanged this regen)

Three directory-style skills are **on disk but not tracked in git** (each shows as `??` in `git status`). Source/intent unknown — appeared 2026-04-21 per filesystem mtime, not authored via any documented slice. The set is **unchanged since the prior regen at `8a0402e`**: same 3 directories, same filenames, no slice has touched them. Disk-vs-tracked file delta = 8 (`find .agent/skills -name "*.md" \| wc -l = 28`; `git ls-files .agent/skills \| wc -l = 20`). The 8 untracked files are:

| Path | Files | Status |
|------|-------|--------|
| `.agent/skills/stripe-best-practices/SKILL.md` | + `references/` (5 entries: billing.md, connect.md, payments.md, security.md, treasury.md) | UNTRACKED — not in git |
| `.agent/skills/stripe-projects/SKILL.md` | (single file) | UNTRACKED — not in git |
| `.agent/skills/upgrade-stripe/SKILL.md` | (single file) | UNTRACKED — not in git |

Action needed (see §12 Q8): decide whether to (a) commit them as legitimate skills, (b) add to `.gitignore` as out-of-scope external resources, or (c) delete. The `SKILL.md` filename pattern (uppercase) is not the canonical SkillForge convention (lowercase slug) — suggests external provenance.

Skill discovery tooling that walks `.agent/skills/*.md` will **miss** these (they're under sub-directories, not top-level `.md` files). So they are also non-discoverable via the documented Skill loader pattern.

**No new tracked skill files added by slices 6.1 / 6.2 / 6.3** — all three Phase 6 slices shipped without authoring or extending a skill file. The relevant skill surface for slice 6.3 was `analytics.md` (already tracked); no edit was required because the new `lesson_viewed` / `lesson_section_expanded` events follow the same pattern as `home_dashboard_viewed`.

---

## Section 11 — Drift flags (AGENTS.md / master-doc vs code)

High-signal output — re-verified against HEAD `78abe56` this targeted regen (carry-forward of 21 prior items + 1 NEW item 22 — §8 lag — surfaced this pass; items 19 / 20 / 21 status updates per slice-6.4b family closure). **Reconciled against post-B-048 SOP state:** R3 = "Never skip auth" (auth only); R19 = push-back; R18 retired (merged into R15(c)); SOP-8 = concurrent-session detection (codified `2504d6b`); SOP-9 = no concurrent CC sessions on one tree (added by B-048, `e2714b4`); H1–H4 = chat-Claude ↔ CC handoff section (added by B-048).

1. **AGENTS.md legacy routers table says `/api/cover_letter` (underscore).** `app/api/routes/cover_letter.py:11` decorates `@router.post("/cover-letter", …)` (hyphen). Effective path is `/api/cover-letter`. Same drift: `/api/interview` vs actual `/api/interview-prep`. **Status: still drifted.**

2. **AGENTS.md legacy routers table lists `/api/v1/onboarding` and `/api/v1/payments` as v1 routers, but the files live in the legacy folder.** `from app.api.routes import onboarding, payments` + `include_router(... prefix="/api/v1")` at `app/main.py:147-148`. Files sit in `app/api/routes/` not `app/api/v1/routes/`. **Status: still drifted.**

3. **AGENTS.md Models table User row still lists `target_company`, `target_date`** (line 270). On disk: `interview_target_company` (String(100)) and `interview_target_date` (Date). Migration `02bf7265b387` did the rename. SESSION-STATE Deferred Hygiene S16 retrofit. **Status: still drifted; bumped urgency by E-042 — `interview_target_date` is now also being deprecated in favor of `tracker_applications_v2.interview_date`, so the AGENTS.md row will need a second update once E-042 FE ships.**

4. **AGENTS.md Routes table references `/api/v1/mission` (singular)** (line 213). Actual mount prefix `/api/v1` + decorators `/missions/create`, `/missions/active`, `/missions/daily`, `/missions/complete-day` — plural. Captured as `[S35-flag]`. **Status: still drifted.**

5. **AGENTS.md says `Category` has a `source` column.** True, but it also has a `tags` JSONB column (migration `d16ca29a5d08`). AGENTS.md does not mention `categories.tags`. **Status: still drifted.**

6. **AGENTS.md Models table references `UsageLimit`** (line 276). No `UsageLimit` model file on disk. Usage limits are enforced in `usage_service.py::PLAN_LIMITS` dict logic, not a DB table. **Status: still drifted (phantom).**

7. **Email-preferences route path mismatch.** `app/api/v1/routes/email_prefs.py` uses `/email-preferences`; FE `services/api.ts` calls `/api/v1/email-preferences`. AGENTS.md table line 212 shows `/api/v1/email-prefs`. **Status: still drifted.**

8. **`study-engine.md` skill file has no `description:` frontmatter.** Other 19 skill files have one. Captured in `docs/audits/SKILLS-SPECS-ALIGNMENT-2026-04-21.md` as critical fix. **Status: still drifted.**

9. **Tracker auto-save JD dedupe documented as locked but not implemented.** `tracker_applications_v2` has no `jd_hash` column (§2 verified); `tracker_service_v2.py` does not import `hash_jd`; `app/utils/text_hash.py::hash_jd` exists but only `interview_storage_service.py` consumes it. Captured as `[5.17-follow] tracker jd_hash dedupe`. **Status: still drifted.**

10. **Four legacy `/api/*` routers still mounted alongside v1 counterparts.** `analyze`, `rewrite`, `cover_letter`, `interview` in `app/main.py:121-124`. The v1 equivalents are *re-exports* of the legacy router objects (see §3), so deprecating the legacy mount requires moving the handlers first. **Status: still drifted.**

11. **NEW post-B-048 — AGENTS.md and skills do not reference R19 / SOP-8 / SOP-9 / H1–H4.** AGENTS.md was not swept during B-048. If AGENTS.md contains references to the retired R18 or the second R3, those are stale; but a quick grep shows AGENTS.md does not currently cite these rule numbers, so this is a "no-stale-citations" finding rather than a drift to fix. **Status: confirmed clean — AGENTS.md is rule-citation-free.**

12. **NEW — three untracked skill directories** (`stripe-best-practices/`, `stripe-projects/`, `upgrade-stripe/`) under `.agent/skills/`. See §10 for filesystem detail and §12 NEW Q8. **Status: NEW this regen — surfaced via filesystem walk.**

13. **NEW — N1-SUPPLEMENT → N9 promotion deferred** (per B-048 close-line). 6 callsites flagged in SESSION-STATE Deferred Hygiene Items; will need a sweep slice. **Status: NEW; tracked.**

14. **NEW — spec section header rename `## 12. R15` / `## 13. R15` across 5 spec files** deferred per B-048. TOC anchors; rename silently breaks external cross-refs if any. **Status: NEW; tracked in SESSION-STATE Deferred Hygiene.**

15. **Pre-existing dirty files (long-standing):** `Enhancements.txt`, `hirelens-backend/scripts/wipe_local_user_data.py`, `../.DS_Store`. None bundled into commits per C2/C5. Plus untracked items: `docs/audits/`, `docs/status/E2E-READINESS-2026-04-21.md`, `skills-lock.json`, `.gitattributes`, `.agent/skills/{stripe-*,upgrade-stripe}/`. **Status: long-standing; not blocking.**

16. **NEW (B-058) — duplicated chromeless-paths sets across `AppShell.tsx` + `MobileNav.tsx`.** B-057 (`19326de`) carved out `/pricing` chrome behavior in two places — `AppShell.CHROMELESS_PATHS = {'/', '/login', '/onboarding/persona', '/first-action'}` plus `pathname === '/pricing' && user === null` guest-only carve-out, and `MobileNav.HIDDEN_PATHS = {'/', '/login'}` plus the same one-line `/pricing` guest carve-out. The `MobileNav` set is intentionally narrower (no onboarding/first-action — bottom-bar is not mounted there anyway), but the `/pricing` rule is duplicated. Drift risk: any future change to chromeless-paths policy must be made in two places. **Tracked at BACKLOG B-058** (P3 nav cleanup) — close shape: lift to `src/components/layout/chromeless.ts` exporting `CHROMELESS_PATHS` + `MOBILE_HIDDEN_PATHS` + shared `isChromeless(pathname, user)` helper. **Status: NEW — surfaced via R19 push-back during B-057 impl.**

17. **NEW (`d19103c` + `b8d0c8c`) — three free-tier paywall env vars not yet reflected in AGENTS.md env-vars table.** `d19103c` plumbed: `Settings.free_daily_review_limit` (env `FREE_DAILY_REVIEW_LIMIT`), `Settings.free_lifetime_scan_limit` (default `1`, env `FREE_LIFETIME_SCAN_LIMIT`), `Settings.free_monthly_interview_limit` (default `3`, env `FREE_MONTHLY_INTERVIEW_LIMIT`). `b8d0c8c` (LD-001 cap tightening, Slice B) flipped `free_daily_review_limit` default from `15` → `10` so the in-code default now matches LD-001's amended cap. Flipping any of the three env vars locally hits the corresponding paywall in seconds without burning real quota. `payments.md` skill records the three under "Free Tier Limits" but `AGENTS.md` env-vars table (canonical source per its own header) does not. **Status: NEW — drift only on the AGENTS.md doc surface; no code drift.**

18. ~~**NEW (slices 6.1 / 6.2 / 6.3) — phase-6 spec body Status lines stuck at `Drafted, not shipped` despite impl ship.** All three on-disk phase-6 specs (`docs/specs/phase-6/01-foundation-schema.md`, `02-fsrs-quiz-item-binding.md`, `03-lesson-ux.md`) declare `## Status: Drafted, not shipped` at line 3.~~ **✅ RESOLVED 2026-04-27 by `95bb3c5`** — chore(specs): flip Status lines on shipped phase-5 + phase-6 specs sweep flipped 9 spec Status lines (6 phase-5 + 3 phase-6) to canonical `Shipped (spec + impl) — closes B-0##. Impl <SHA> on YYYY-MM-DD.` form, mirroring spec #58's template. Verified post-flip on disk: phase-6/01 / 02 / 03 all read `Shipped (spec + impl) — closes B-0##` at line 3. **NOTE:** spec #04 (admin-authoring) is NOT covered by this resolution — it was authored 2026-04-27 (post-`95bb3c5`) and is now in a partial-shipped state (slice 6.4a shipped via `b0806d0`; slice 6.4b pending B-065). See NEW item 19 below.

19. **Spec status convention gap for split-impl specs.** Spec #04 (`docs/specs/phase-6/04-admin-authoring.md`) was authored 2026-04-27 (`309f6c4`) covering both slice 6.4a (B-064) and slice 6.4b (B-065) per §12 D-1 split. Slice 6.4a shipped via `b0806d0` (closes B-064); slice 6.4 spec slice 2/2 (`4fce036`) flipped Status line to `Partially shipped — slice 6.4a shipped (closes B-064 by b0806d0); slice 6.4b pending B-065`; slice 6.4b BE half shipped via `d6bda3b` (B-065 status note); slice 6.4b FE half shipped via `634f633` (closes B-065 + B-068). **Status: SHIPPING-RESOLVED 2026-04-27** — both halves of spec #04 are now shipped, so the partial-shipped form is no longer needed for #04 specifically. The recommendation to add a canonical `Partially shipped — slice Na shipped …; slice Nb pending …` Status string to the §13 legend stands as a forward-looking convention for future split-impl specs (none on the horizon currently). Spec #04's Status line on disk still reads "Partially shipped — … pending B-065" — **stale** since `634f633` closed B-065 + B-068; needs flip to canonical `Shipped (spec + impl) — closes B-064 + B-065 + B-068. Impl 6.4a `b0806d0`, 6.4b BE `d6bda3b`, 6.4b FE `634f633`.` form on next legitimate spec edit (NOT in this regen — CR is read-only audit artifact, doesn't edit spec source). Tracked at §13 phase-6 row #04 annotation. No BACKLOG row pre-allocated; flip can ride on next spec touch.

20. **BE test count "regression" `520 → 510` was env-var dependent baseline drift, not a code regression.** 10 tests in `tests/test_study_api.py::TestDailyStatusPreflight` + `tests/test_usage_limits.py` were observed failing at slice 6.4 spec-author baseline (`pytest -m "not integration"` without env vars). Slice 6.4 spec slice 2/2 (`4fce036`) entry SESSION-STATE pre-flight clarified the picture: `pytest -m "not integration"` with **production-default env vars** (`FREE_DAILY_REVIEW_LIMIT=10 FREE_LIFETIME_SCAN_LIMIT=1 FREE_MONTHLY_INTERVIEW_LIMIT=3`) yields **520 passed / 1 skipped / 7 deselected** — the 510 baseline was missing-env-vars-induced. Slice 6.4b-1 ran the same env-var-set invocation and added +35 to land at **555 passed**. So the "10-test mystery regression" was test-fixture / env-default coupling, not a true code regression — slice B's LD-001 cap tightening (15 → 10) flipped defaults that these tests pin. **Status: ✅ EXPLAINED 2026-04-27** — pre-existing 10 failures are env-var-default coupled and not blocking; tracked at slice 6.4 spec slice 2/2 + slice 6.4a + slice 6.4b-1 entries' drift call-outs. No BACKLOG row needed; the test files now run green when production env vars are set, which is the canonical CI invocation. (Could file a P3 hygiene row to make the tests env-default-agnostic; not blocking.)

21. **(process-improvement candidate) — D-026 cross-ref: spec authors must verify FE files referenced in mount-paths actually exist on disk, not just BE endpoints.** Slice 6.4 spec author at `309f6c4` referenced `pages/AdminAudit.tsx` in §8.5 + §11 6.4a AC-3 + §10.1 based on the existence of the BE endpoint `GET /api/v1/admin/audit` (E-018a, `3b43772`). Disk reality: only `pages/AdminAnalytics.tsx` + `pages/AdminPanel.tsx` existed at the time; no `AdminAudit.tsx`. Slice 6.4a impl R19 fired at Step 1 audit, resolved via in-slice spec amendment per §12 D-14 (`cbf878f`) — `/admin/audit` dropped from sidebar, sidebar reduced 5 → 4 links; impl `b0806d0` honors the amended AC-3. Logged in SESSION-STATE Drift Flags as D-026 (RESOLVED). **Suggested SOP-5 enhancement (authored hint, not yet a rule):** when spec text says "Page X (Phase N) — untouched", `grep src/pages/` for `X.tsx` before signing off the spec. Filed as recommendation; Dhamo to lift to a numbered rule (R-class) if the pattern recurs. **Status: REAFFIRMED 2026-04-27** — process lesson stands; not yet promoted to R-rule because the pattern hasn't recurred since. Slice 6.4b family caught no new spec-vs-disk FE drift of this class.

22. **NEW — §8 Frontend shared types lags `src/types/index.ts` reality.** Slice 6.4b-2 (`634f633`) shipped 8 new admin write-shape interfaces in `src/types/index.ts` (`DeckCreateRequest`, `DeckUpdateRequest`, `LessonCreateRequest`, `LessonUpdateRequest`, `LessonUpdateResponse`, `QuizItemCreateRequest`, `QuizItemUpdateRequest`, `EditClassification` literal alias) plus 3 per-entity status-filter aliases (`AdminDeckStatusFilter`, `AdminLessonStatusFilter`, `AdminQuizItemStatusFilter` per spec §12 D-16). §8 of CR carries forward verbatim from prior regen per LD-5 (B-067 row scope explicitly excluded §8) — so the §8 table block does NOT enumerate any of these 11 new type entries. §1 metadata Shared TS types row notes the addition explicitly + cross-refs this drift item. **Status: NEW — surfaced this regen.** Close shape: next CR regen with §8 in scope picks them up; no BACKLOG row pre-allocated. JC for this regen: kept §8 strictly out of scope to honor B-067 row's explicit scope ceiling and avoid scope creep.

---

## Section 12 — Open questions for Dhamo

1. `components/onboarding/GuidedTour.tsx` has zero imports. Is this (A) dead code safe to delete, or (B) a scaffold you're saving for a future onboarding tour spec? *(carried from prior regen)*
2. `components/rewrite/ResumePDFTemplate.tsx` has zero imports and PDF generation is inline in `Rewrite.tsx`. Delete in next cleanup slice — yes/no? *(carried from prior regen)*
3. Is `UsageLimit` supposed to exist as a DB-backed model, or is the AGENTS.md Models table row stale and should be removed? *(carried from prior regen)*
4. ~~`AdminPanel` (`/admin`) has no route-level admin guard~~ ✅ **RESOLVED by E-040** (`1148354`, spec #54) — `<AdminGate>` wraps both `/admin` and `/admin/analytics`; non-admins see a 403 view and lazy chunks are not downloaded. *(resolved prior regen — kept here for traceability; will drop after one more regen if no follow-up surfaces)*
5. `study-engine.md` skill file is missing `description:` frontmatter — backfill to match the other 19 skills? (One-line edit.) *(carried)*
6. `ai_service.py` duplicates `gpt_service.py` verbatim and is consumed only by an enterprise-tier endpoint (`/api/v1/resume/{id}/optimize`). Safe to delete now, or wait on production traffic check per `[S47-defer]`? *(carried)*
7. Legacy mounts `/api/analyze`, `/api/rewrite`, `/api/cover-letter`, `/api/interview-prep` — known external caller relying on these paths, or purely FE-migration holdovers that can be dropped once FE references are swept? *(carried)*
8. **NEW** — Three untracked skill directories appeared on 2026-04-21 (`stripe-best-practices/`, `stripe-projects/`, `upgrade-stripe/`). Source/intent unknown. (a) Commit and treat as legit skills, (b) `.gitignore` as external resources, or (c) delete? Their `SKILL.md` (uppercase) filename does not match SkillForge convention (lowercase slug `name.md`).
9. **NEW** — E-042 deprecates `users.interview_target_company` and `users.interview_target_date` in favor of `tracker_applications_v2.interview_date` (BE shipped 2026-04-23 per `9543aa466524`/`eb59d4fc1f7e`). FE consumers (CountdownWidget, MissionDateGate) still read the user-level fields. Phase-6 cleanup intent confirmed, or accelerate to the next slice?

No status changes this regen — Q1–Q9 carry forward verbatim from `8a0402e`. Q4 stays ✅ RESOLVED (one more regen window before drop). No new OQs surfaced this regen — the four Phase 6 product decisions chat sometimes refers to (cron arch G2, file storage H1, events sink I1, `card_quality_signals` J2) live in **SESSION-STATE Phase 6 locked-decisions block**, not here, and are already locked / pending re-confirm at slice 6.5 spec time.

---

## Section 13 — Specs inventory

Walked `docs/specs/**/*.md` — **84 spec files across 7 phases** (unchanged file count since prior regen at `7621b88`; phase-6 spec #04 accumulated 2 in-slice amendments since: `4fce036` slice 6.4 spec slice 2/2 — §12 D-15..D-19 lock + Status flip + §9 +1 event row; `de1e9a9` slice 6.4 spec slice 3/3 — D-16 per-entity vocab + D-19 modal-copy N drop + AC-19 SUPERSEDED → CR regen deferred to B-067). Status field = `^## Status` line OR `^**Status:**` bolded line at the top of the spec body — both styles are observed on disk; tooling that grepped only `^## Status` would undercount by 2 (specs #61, #62 use the `**Status:**` bolded form). Specs without either form are flagged "no status".

### Per-phase counts
| Phase | Files | With explicit Status line | No status field |
|-------|-------|---------------------------|-----------------|
| phase-0 | 6 | 6 | 0 |
| phase-1 | 13 | 6 | 7 |
| phase-2 | 8 | 7 | 1 |
| phase-3 | 11 | 8 | 3 |
| phase-4 | 6 | 6 | 0 |
| phase-5 | 36 | 14 | 22 |
| phase-6 | 4 | 4 | 0 |
| **Total** | **84** | **51** | **33** |

**Delta since prior regen at `7621b88`**: spec file count unchanged (84 across 7 phases). Phase-6 row #04 (`04-admin-authoring.md`) accumulated 2 in-slice spec amendments without changing file count: `4fce036` (slice 6.4 spec slice 2/2 — §12 D-15..D-19 OQ-locks + Status flip "Drafted, not shipped" → "Partially shipped — slice 6.4a shipped …; slice 6.4b pending B-065" + §9 +1 event row `admin_deck_persona_narrowed` per D-19) and `de1e9a9` (slice 6.4 spec slice 3/3 — D-16 unified→per-entity vocab + D-19 modal-copy N drop + AC-19 SUPERSEDED → CR regen deferred to B-067). Both halves of slice 6.4b are now SHIPPED (BE `d6bda3b` + FE `634f633`); spec body Status line is **stale** at "Partially shipped" and needs flip to canonical `Shipped (spec + impl) — closes B-064 + B-065 + B-068.` form on next legitimate spec edit (see §11 item 19; CR is read-only audit artifact and does NOT edit spec source). Phase-5 unchanged at 36 / 14 / 22.

### Status legend (canonical strings observed on disk)
`Done` · `Complete` · `Implemented — Spec Backfill Pending (P5-S###)` · `Draft` · `Drafted, not shipped` · `Shipped (spec + impl)` · `Done — Shipped in <sha>` · `Partially Done` · `Planned — Known-Broken` · `Deferred` · `Complete — Spec Backfill Pending`

### phase-0 (Phase 0 / foundation)
| File | Status |
|------|--------|
| 00-postgresql-migration.md | Done |
| 01-alembic-setup.md | Done |
| 02-auth-unification.md | Done |
| 02a-skeleton-deploy.md | Done |
| 02b-cicd-pipeline.md | Done |
| 03-user-role-admin.md | Done |

### phase-1
| File | Status |
|------|--------|
| 03-card-extraction.md | Partially Done — gaps to close in P1-S1 |
| 04-cards-api.md | Done |
| 05-fsrs-daily-review.md | (no status field) |
| 06-study-dashboard-ui.md | (no status field) |
| 07-card-viewer-ui.md | (no status field) |
| 08-ats-card-mapping.md | (no status field) |
| 09-onboarding-flow.md | (no status field) |
| 10-posthog-analytics.md | (no status field) |
| 11-stripe-integration.md | (no status field) |
| 11a-free-tier-limits.md | Implemented — Spec Backfill Pending (P5-S6) |
| 11b-tracker-autopopulate.md | Implemented — Spec Backfill Pending (P5-S5) |
| 11c-ip-registration-blocking.md | Implemented — Spec Backfill Pending (P5-S4) |
| 11d-llm-router.md | Implemented — Spec Backfill Pending (P5-S1) |

### phase-2
| File | Status |
|------|--------|
| 10-streaks-xp-badges.md | Done |
| 11-gamification-ui.md | Done |
| 13-skill-radar-heatmap.md | (no status field) |
| 14-mission-mode.md | Done |
| 14a-mission-mode-api.md | Done |
| 14b-mission-mode-ui.md | Done |
| 15-daily-email.md | Done |
| 16-email-preferences.md | Done |

### phase-3
| File | Status |
|------|--------|
| 15-ats-scorer-upgrade.md | Done |
| 16-experience-generator-api.md | Done |
| 17-admin-card-crud.md | Done |
| 18-ai-card-generation.md | Done |
| 19-landing-page.md | (no status field) |
| 20-onboarding-polish.md | (no status field) |
| 20b-design-system-themes.md | Implemented — Spec Backfill Pending (P5-S2) |
| 20c-resume-cover-letter-fix.md | Planned — Known-Broken, awaiting P5-S9 + P5-S10 |
| 21-card-feedback.md | Done |
| 22-my-experience.md | Done |
| 25-feedback-nps-system.md | Done |

### phase-4
| File | Status |
|------|--------|
| 20-ai-feedback-digest.md | Deferred |
| 22-error-monitoring.md | Done |
| 23-error-monitoring.md | Complete |
| 24-posthog-dashboards.md | Complete |
| 25-performance-hardening.md | Complete |
| 25a-custom-domain-golive.md | Complete — Spec Backfill Pending (P4-S4 retrospective) |

### phase-5 (most active phase)
| File | Status |
|------|--------|
| 01-admin-analytics-early-draft.md | Done |
| 09-resume-rewrite-fix.md | (no status field) |
| 10-cover-letter-format-fix.md | (no status field) |
| 11-generate-experience-fix.md | (no status field) |
| 12-navigation-restructure.md | (no status field) |
| 21-analysis-results-improvements.md | Done — Shipped in `1c0817a` (P5-S21b) on 2026-04-19 |
| 22-plan-aware-missing-skills-cta.md | Draft |
| 27-geo-pricing.md | (no status field — NEW since prior regen, authored `c16f544` / E-023; behavior contract + Gap B/D/E fix anchors) |
| 34-persona-picker-and-home.md | (no status field) |
| 35-home-dashboard-and-widgets.md | (no status field) |
| 36-subscription-cancellation.md | (no status field) |
| 38-admin-analytics.md | Draft |
| 40-home-dashboard-state-aware.md | (no status field — but see SESSION-STATE: P5-S18b retrofit flipped to "Done — Backfilled" by 2026-04-19 process note; spec body status field needs a second touch) |
| 41-interview-prepper-checklist.md | (no status field) |
| 42-paywall-dismissal.md | (no status field) |
| 43-stripe-webhook-idempotency.md | (no status field) |
| 44-home-widget-empty-states.md | (no status field) |
| 45-legacy-route-cleanup.md | (no status field) |
| 46-post-persona-first-action.md | (no status field) |
| 47-resume-rewrite-content-preservation.md | (no status field) |
| 48-doc-audit-pattern.md | (no status field) |
| 49-interview-question-storage.md | (no status field) |
| 50-free-tier-daily-card-wall.md | Draft *(amended `b8d0c8c` 2026-04-26 Slice B — LD-001 cap tightening 15→10. Spec body retained `## Status: Draft` with an in-place amendment block at line 13 documenting the cap flip; AC shapes / payload fields / behavior / edge cases UNCHANGED — only the integer literal moves. `daily_card_wall_hit` payload also extended additively by B-059 / `20562ea` with `surface` enum.)* |
| 51-ai-rewrite-section-preservation.md | (no status field — but B-001 closed `688529d` per BACKLOG; spec needs status line) |
| 52-cover-letter-format-enforcement.md | (no status field — but B-002 closed per BACKLOG; spec needs status line) |
| 53-interview-target-optional-fields.md | (no status field — but B-018 shipped `724e5cd`; spec needs status line) |
| 54-admin-email-whitelist.md | Draft |
| 55-reanalyse-paywall-gate.md | Draft |
| 56-free-tier-scan-lifetime-cap.md | Draft |
| 57-tracker-level-interview-date.md | (no status field — E-042 BE shipped 2026-04-23; FE pending; spec needs status line) |
| 58-legacy-rewrite-router-auth-quota.md | Shipped (spec + impl) — closes B-033. Impl half landed 2026-04-23. |
| 59-scan-persistence.md | Drafted, not shipped. *(actually shipped per BACKLOG B-035 closed `0b35440` on 2026-04-24 — spec status line needs update)* |
| 60-analyze-page-preflight-gate.md | (no status field — B-045 closed `3c962d8`; spec needs status line) |
| 61-home-dashboard-composition-rules.md | **Status:** Drafted, not shipped *(NEW — B-051 spec half `1262c26`. Impl shipped `ecef895` 2026-04-25 closing B-051 + E-048 — spec status line not flipped on impl-merge; matches pattern observed elsewhere in §13.)* |
| 62-study-dashboard-source-hint.md | **Status:** Drafted, not shipped *(NEW — B-052 spec half `ffd66f7`. Impl shipped `df035e1` 2026-04-26 closing B-052 + B-053 per spec §10 OQ-5 dual-tracking — spec status line not flipped on impl-merge.)* |
| 63-daily-review-preflight-gate.md | Draft *(NEW — B-059 spec half `42a236b`. Impl shipped `20562ea` 2026-04-26 closing B-059 — spec status line not flipped on impl-merge. Authoring note records the chat-Claude vs disk-reality drift on endpoint name (`/study/daily-queue` cited but disk is `/study/daily`) and `formatResetsAt` reuse claim (cited as importable but was private to QuizPanel — impl had to lift to `wallCountdown.ts`); R19 audit notes preserved in spec body.)* |

### phase-6 (Curriculum Platform)
| File | Status |
|------|--------|
| 01-foundation-schema.md | Shipped (spec + impl) — closes B-061. Impl `a989539` on 2026-04-26. *(Status line flipped from `Drafted, not shipped` by `95bb3c5` 2026-04-27 — closes prior CR §11 drift item 18 for this spec. Adds 4 tables `decks` / `lessons` / `quiz_items` / `quiz_item_progress` via single Alembic migration `57951e9f4cdc`.)* |
| 02-fsrs-quiz-item-binding.md | Shipped (spec + impl) — closes B-062. Impl `7b654fb` on 2026-04-27. *(Status line flipped by `95bb3c5`. First FSRS consumer of slice 6.1's `quiz_item_progress` table; new service `quiz_item_study_service.py` + new router `quiz_items.py` mounted at `/api/v1/quiz-items` with 3 endpoints (`GET /daily`, `POST /review`, `GET /progress`). Service ports `study_service` byte-for-byte modulo D-1 / D-4 / D-7.)* |
| 03-lesson-ux.md | Shipped (spec + impl) — closes B-063. Impl `ba00331` on 2026-04-27. *(Status line flipped by `95bb3c5`. FE-first slice — page `pages/Lesson.tsx` at `/learn/lesson/:id` + `components/lesson/{LessonRenderer,QuizItemPanel}.tsx` + 3 new BE read-only routes returning fixture data from `app/data/lesson_fixtures.py` (slice 6.4b swaps loader → DB query). `remark-gfm` net-new dep (singular per D-3).)* |
| 04-admin-authoring.md | Partially shipped — slice 6.4a shipped (closes B-064 by `b0806d0`); slice 6.4b pending B-065 *(spec body Status line — current on-disk text post-`4fce036` slice 6.4 spec slice 2/2 status flip; **STALE** as of 2026-04-27 since slice 6.4b BE half shipped via `d6bda3b` (B-065 status note) + slice 6.4b FE half shipped via `634f633` closing B-065 + B-068. Reality on disk: spec #04 fully shipped — both halves done. Spec body Status needs flip to canonical `Shipped (spec + impl) — closes B-064 + B-065 + B-068. Impl 6.4a b0806d0 on 2026-04-27, 6.4b BE d6bda3b on 2026-04-27, 6.4b FE 634f633 on 2026-04-27.` form on next legitimate spec edit. Spec content history: authored `309f6c4` 2026-04-27 + in-slice amendment `cbf878f` in slice 6.4a impl (D-14 — drop AdminAudit sidebar link); amended `4fce036` slice 6.4 spec slice 2/2 (§12 D-15..D-19 lock + Status flip + §9 +1 event); amended `de1e9a9` slice 6.4 spec slice 3/3 (D-16 unified→per-entity vocab + D-19 modal-copy N drop + AC-19 SUPERSEDED). Implementation history: 6.4a impl `b0806d0` (multi-route AdminLayout shell + AdminCards extraction + AdminDecks/AdminLessons placeholders + App.tsx route rewire; `pages/AdminPanel.tsx` deleted per D-12). 6.4b BE `d6bda3b` (3 admin services + admin_errors.py + 3 admin route files / 13 admin endpoints + lesson_service body swap with selectinload per D-15 + fixture deletion + write schemas + 11 admin events). 6.4b FE `634f633` (3 admin components + lessonEdit.ts + 4 hooks + 4 editor pages + 8 write-shape types + 13 api helpers + App.tsx route updates). CR regen tracked at B-067 (this slice — 6.4b-3) per AC-19 supersession at `de1e9a9`; mirrors B-066 standalone-CR-regen pattern. See §11 item 19 for status-flip recommendation; item 22 for §8 shared-types lag.)* |

### Numbering anomalies / duplicates / gaps

- **phase-3 spec numbering:** `20-onboarding-polish.md`, `20b-design-system-themes.md`, `20c-resume-cover-letter-fix.md` — three specs sharing the `20*` slot via letter suffixes. Convention is consistent with phase-1 `11a/b/c/d`.
- **phase-4 numbering:** `22-error-monitoring.md` and `23-error-monitoring.md` — two specs with the SAME title "error-monitoring" at adjacent numbers. One marked Done, one Complete. Likely supersession or duplicate authoring; needs clarification.
- **phase-5 numbering gaps:** `01`, then `09–12`, then `21–22`, then `27`, then `34–63` (with remaining gaps at 23–26, 28–33, 37, 39). Many gaps suggest reserved-but-not-authored slots; only worth investigating if a citation references a missing number.
- **phase-5 number `1` reuse:** `01-admin-analytics-early-draft.md` (Done) is superseded by `38-admin-analytics.md` (Draft) per the same OKR surface. Consider archiving #01 or marking it `Superseded`.
- **Total spec status hygiene gap:** 33 of 84 specs (39%) have no Status line. Concentration in phase-1 (7), phase-3 (3), phase-5 (22). The phase-6 sweep at `95bb3c5` flipped specs #01/#02/#03 to canonical post-ship form (closing prior CR §11 drift item 18 for those three specs), and also flipped phase-5 specs #53/#59/#60/#61/#62/#63. Phase-5 specs #51, #52, #57 remain unflipped despite shipping per BACKLOG — recommend follow-up sweep. Spec #04 (phase-6 admin-authoring) Status line currently reads "Partially shipped" (set at `4fce036` slice 6.4 spec slice 2/2) but is now **stale** — both 6.4a + 6.4b have shipped (`b0806d0` + `d6bda3b` + `634f633`); needs flip to canonical `Shipped (spec + impl) — closes B-064 + B-065 + B-068.` form on next legitimate spec edit (see §11 item 19 disposition update).
- **Spec-body Status format inconsistency:** `## Status:` (heading-2) vs `**Status:**` (bolded paragraph) appear interchangeably; tooling that greps only one form will miscount. Standardize on the heading-2 form to align with template (spec #50, #63 use it; #61, #62 use the bolded form).

---

*End of snapshot. Generated 2026-04-27 at HEAD `78abe56` — targeted regen post-slice-6.4b-2 (closes B-067). Sections in scope: §1 (header SHA + lineage + counts: BE services 33→37, v1 routers 21→24, endpoints 73→86, FE pages 23→26, FE components 70→73, FE utils 6→7, FE hooks 12→16, BE tests 510→555, FE tests 345→372), §3 (+13 admin write routes + 3 router-file rows), §4 (+4 admin services: deck_admin / lesson_admin / quiz_item_admin / admin_errors + lesson_service body-swap note), §6 (admin route block expanded for `/admin/decks/:deckId` + `/admin/lessons/:lessonId` + `/admin/lessons/:lessonId/quiz-items`; component graph 70→73 +admin/MarkdownEditor +admin/ConfirmCascadeModal +admin/ConfirmPersonaNarrowingModal; fixture-deletion BE-side note), §7 (4 admin editor page rows: AdminDecks rewritten + AdminDeckDetail / AdminLessonEditor / AdminQuizItems new + AdminLessons rewritten), §11 (items 19 / 20 / 21 status updates; +NEW item 22 §8 lag), §13 (phase-6 row #04 status text refresh; spec file count unchanged at 84). Sections carried forward verbatim per LD-5: §2 (BE models — no schema changes; CRUD slice against existing slice-6.1 tables), §5 (Alembic — no migration), §8 (FE shared types — admin write-shape interfaces shipped at `634f633` not yet enumerated; tracked at §11 item 22), §9 (known-dead — no new dead code), §10 (skills — `admin-panel.md` catalog refresh absorbed into THIS slice's commit per JC #6 disposition (a) but the §10 CR table block carries forward), §12 (open questions — Q1–Q9 unchanged). **Lineage chain:** `17bf188` (§3 + §4 regen) → `7109542` (§1 + §2 + §5 regen) → `d5f3d17` (§6 + §7 + §8 + §9 + §10 + §11 + §12 + §13 regen, slice 6.3 final pass) → `f99a6b3` (§1 + §6 + §7 + §11 + §13 targeted, post-slice-6.4a) → `7621b88` (SHA backfill of f99a6b3) → 4 spec-amendment + SHA-backfill commits with no CR touch (`4fce036` / `aeef9a3` / `de1e9a9` / `f0693e8`) → `d6bda3b` (slice 6.4b-1 BE impl) → `049dc3a` (SHA backfill) → `634f633` (slice 6.4b-2 FE impl) → `1d4f4dc` (SHA backfill) → THIS commit (§1 + §3 + §4 + §6 + §7 + §11 + §13 targeted, post-slice-6.4b-2 — closes B-067). **Next regen recommended after slice 6.4.5 / 6.5 ships** — slice 6.4.5 reintroduces `app/data/decks/seed_lessons/*.md` for the 12 locked-deck seeds (per Phase 6 LD H1); slice 6.5 owns the read-time service-layer invariant for "no new progress rows against retired quiz_items"; both will touch §4 + §6 + §13. The §8 lag (item 22) should be picked up by the next regen with §8 in scope.*
