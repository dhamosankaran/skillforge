# SESSION-STATE.md
## Current Status
Last updated: 2026-04-17
Phase: 1
Current session: P1-S2 (Spec — Cards API)
Last completed slice: P1-S1b — IVFFlat ANN index + extraction unit tests (parent P1-S1 now ✅ Done)
Next slice to run: P1-S2 — Spec for user-facing Cards API (`/api/v1/cards` read endpoints)

### Pending slices
- **P1-S2** — Cards API spec + implementation (list/categories/semantic search endpoints, free-tier gating, Pydantic schemas, tests)

## Phase Completion Tracker
- Phase 0: ✅ Complete (local) / ⬜ Production deploy deferred (S1–S8)
  - Note: P0-S6 and P0-S8 were marked done based on deploy-ready files existing in codebase, but Railway + Vercel were never actually provisioned. Production deployment is deferred until Phase 1 is functionally complete locally.
- Phase 1: 🔄 In Progress (S1 complete 2026-04-17 — S1a on 2026-04-16, S1b on 2026-04-17; S2 pending)
- Phase 2–4: ⬜ Not started

## Deferred Work

### DEFERRED-1: Production Deployment (Railway + Vercel)
**Original phase:** P0-S6 through P0-S8
**Status:** ⬜ Not started — deploy-ready files exist but no Railway/Vercel projects provisioned
**Trigger:** After Phase 1 is functionally complete and tested locally
**Scope:**
- Create Railway project with pgvector PostgreSQL + Redis
- Verify pgvector version on Railway (determines HNSW vs IVFFlat for ANN index)
- Deploy backend to Railway (env vars, release command, CORS)
- Deploy frontend to Vercel (env vars, API base URL)
- Configure Google OAuth redirect URIs for production domain
- Configure Stripe webhook URL for production domain
- Configure custom domain (theskillsforge.dev) + SSL
- Verify end-to-end: curl production /health → 200, frontend loads, CORS works
**Estimated time:** 1-2 hours of dashboard setup + debugging
**Risk if deferred too long:** Every Phase 1 feature is tested only on localhost. CORS, connection pooling, env var mismatches, and Stripe webhook URL issues will all surface on first real deploy. The playbook strongly recommends deploying early to catch these incrementally rather than all at once.
**Playbook reference:** Phase 0 Tasks 0.6-0.8, CI/CD Section 8

## Decisions Made
| Decision | Rationale | Date |
|----------|-----------|------|
| Free tier limit reduced from 15 to 5 Foundation cards | Original 15 was sized for a 177-card library; with 15 total cards in launch deck, 15-card free tier = no paywall. 5 keeps a meaningful free-vs-Pro distinction. Will revisit when library grows past 50 cards. | 2026-04-16 |
| Option A on content scaling — accept 15-card reality, defer bulk authoring | Content creation throughput (5–12 hours admin review for 150 cards) made Option B a multi-week side quest; Option C (defer paywall) loses Phase 1 revenue signal; Option A keeps Phase 1 on-plan with an honest pricing story (feature-driven Pro + growing library). | 2026-04-16 |
| P1-S1 split into P1-S1a + P1-S1b | Original scope (3 migrations + 3 tests + extract_cards patch) estimated 55–70 min — exceeds the 30-min slice budget. Split along theme: S1a = schema + soft-delete; S1b = ANN index + extraction tests. | 2026-04-16 |
| Soft-delete filter test lives in the integration suite, not CI subset | The spec left two landing zones open (CI subset via `TEST_DATABASE_URL` vs the existing integration file). Kept it alongside the other card-extraction tests in `tests/test_card_extraction.py` with `@pytest.mark.integration`, using the existing `dev_session` fixture (which never commits, so the two inserts roll back). Matches the surrounding file's pattern. | 2026-04-16 |
| Production deploy deferred until Phase 1 complete locally | Railway + Vercel never provisioned despite P0-S6 being marked done. Trade-off: faster Phase 1 development velocity now, but deploy issues will cluster at the end instead of being caught incrementally. Accepted risk. | 2026-04-17 |
| ANN index: use IVFFlat (not HNSW) | Production pgvector version unknown since Railway not provisioned. IVFFlat works on all pgvector >= 0.4.0. Performance difference negligible at 15-200 card scale. Revisit HNSW when: (a) prod pgvector version verified >= 0.5.0, AND (b) card volume > 1000. | 2026-04-17 |

## Enhancement Status
- ENH-1 LLM router: ⬜ (build in P1-S4)
- ENH-2 Geo pricing: ⬜ (build in P1-S22)
- ENH-3 IP blocking: ⬜ (build in P1-S19)
- ENH-4 Card soft-delete: ✅ (column + partial index `ix_cards_category_id_active` + filter test landed in P1-S1a on 2026-04-16)
- ENH-5 Design system: ⬜ (build in P3-S3)
- ENH-6 Free tier interview limits: ⬜ (build in P1-S19)
- ENH-7 Tracker auto-populate: ⬜ (build in P1-S20)
- ENH-8 Resume/cover letter fix: ⬜ (build in P3-S7)

## Future Considerations

### Content scaling timeline
- Launch: 15 cards (current state from cards.js)
- Pre-launch additions: user has a separate content plan to add more cards before paid launch
- Phase 3: admin panel + AI card generation enables ongoing content scaling
- Phase 1 paywall sized for current library (5 free / 15 total); revisit limits when library > 50

### Free tier gating code surface area (for Task 1.12)
The "5 Foundation cards" cap does not yet exist in code. Today's gate is category-level only:
- `app/services/card_service.py` — 6 call sites filtering on `Category.source == "foundation"`
- `app/services/study_service.py` — 4 call sites with the same filter
- `app/api/v1/routes/study.py:66` — docstring reference
- `.agent/skills/testing.md:10` — `client_free_tier` fixture

Task 1.12 will need to layer a per-user card-count cap on top of these filters.

## What Was Built Last Session
- P1-S1b landed (commit `e3c0c90`): hand-authored Alembic migration `59795ca196e9` creates `ix_cards_embedding_ivfflat ON cards USING ivfflat (embedding vector_cosine_ops) WITH (lists = 4) WHERE deleted_at IS NULL`; downgrade uses `DROP INDEX IF EXISTS`; upgrade is idempotent via `CREATE INDEX IF NOT EXISTS`. New `tests/test_extract_cards_unit.py` with 9 CI-safe tests (UUID5 determinism for `cat_uuid` / `card_uuid` + `_synthetic_embedding` dimensionality / determinism / distinctness / non-zero magnitude). New integration test `test_ivfflat_index_used_in_semantic_search` in `tests/test_card_extraction.py` — `SET LOCAL enable_seqscan = OFF` + `SET LOCAL enable_sort = OFF` + EXPLAIN asserts `ix_cards_embedding_ivfflat` appears in the plan.
- Verified locally: migration module imports cleanly; full upgrade → downgrade -1 → upgrade cycle on `hireport_test`; `\di ix_cards_embedding_ivfflat` + `pg_indexes.indexdef` confirm `USING ivfflat (embedding vector_cosine_ops) WITH (lists='4') WHERE (deleted_at IS NULL)`; CI subset 167 passed / 6 deselected (up from 158/5 — +9 unit tests); integration subset 6/6 passed (including the new EXPLAIN test).
- CI green on push: Migration Rollback + Backend Tests + Frontend Tests all ✓ (run `24563497209`).
- Previous: P1-S1a landed `fa10338` (categories.tags + partial index); Phase 0 closed; CI marker-gating for integration tests.

## Known Issues
- `docs/specs/phase-1/03-card-extraction.md` was stale (said 177 cards, Done status). Rewritten 2026-04-16 to reflect reality (15 cards / 14 categories), marked partially-done, split work into S1a/S1b.
- Card-extraction skill file (`.agent/skills/card-extraction.md`) still says "177 study cards" — update when the deck is authored post-P1 UX.

## Known Traps

### Deploy-ready ≠ deployed
Claude Code audits confirmed P0-S6 as "✅ Done" because deploy-ready files existed (railway.toml, CORS config, URL scheme handling). But no Railway or Vercel project was ever created. Lesson: for deploy tasks, always verify against the actual infrastructure (curl the URL, check the dashboard), not just the codebase.

### `SET LOCAL enable_seqscan = OFF` alone is not enough to force an ANN index at low row counts
With 15 rows, forcing the IVFFlat index for an `ORDER BY embedding <=> … LIMIT N` query requires disabling **both** `enable_seqscan` **and** `enable_sort`. Disabling seqscan alone still leaves the planner free to pick the small partial B-tree index `ix_cards_category_id_active` (from P1-S1a) and do an explicit Sort step, which is cheaper than IVFFlat at tiny scale. Disabling sort forces the planner to pick an index whose AM supports `amcanorderbyop` — which is IVFFlat/HNSW. See `tests/test_card_extraction.py::test_ivfflat_index_used_in_semantic_search`.

### Zero vectors and cosine distance
A 1536-dim all-zero vector has undefined cosine similarity (zero magnitude → division by zero). When writing EXPLAIN-only tests, prefer `[1, 0, 0, …, 0]` or any single-non-zero vector over `[0, 0, …, 0]` to keep the distance expression well-defined even if the query result is never executed.

## Start-of-Next-Session Prompt
Read AGENTS.md. Read CLAUDE.md. Read SESSION-STATE.md. P1-S1 (cards data-layer foundations) is complete. Next slice is **P1-S2 — Cards API spec**: write/review `docs/specs/phase-1/04-cards-api.md` for the user-facing `/api/v1/cards` read endpoints (list, by category, semantic search) with free-tier gating on top of the existing `Category.source == "foundation"` filter + the forthcoming per-user card-count cap (ENH-6, Task 1.12). The ANN index from P1-S1b is available — semantic search can wire up directly. Production deployment (Railway + Vercel) is still deferred — see `Deferred Work > DEFERRED-1`.
