# Spec #49 — Interview Question Storage per JD

**Status:** Backend slice — ✅ SHIPPED (frontend wiring deferred as 5.17b)
**Owner:** Dhamo
**Created:** 2026-04-19
**Phase:** 5 (v2.1 item 5.17)
**Closes:** v2.1 5.17 (backend half). 5.17b will close the frontend half (force_regenerate wiring + cached-result UX).

## 1. Problem

Every call to `POST /api/interview-prep` re-runs the reasoning-tier LLM (`interview_questions` task, Gemini 2.5 Pro by default). A user who revisits the Interview Prep page for the same job description pays the LLM cost again and loses their prior prep history — the generated STAR-framework answers disappear when the component unmounts. Two problems: (a) cost leak on every Pro revisit, (b) no persistence of the user's interview prep set per JD.

The v2.1 playbook flagged this as 🔴 PENDING (see `docs/PHASE-5-STATUS.md` row 5.17) and named the fix shape: pair a `hash_jd` normalization primitive with a storage table keyed on `(user_id, jd_hash)` and return cached on hit.

## 2. Audit of existing state (Step-2, 2026-04-19)

- **Endpoint:** `POST /api/interview-prep` (`app/api/routes/interview.py`); `app/api/v1/routes/interview.py` re-exports the same router so `POST /api/v1/interview-prep` is an alias. No second code path.
- **Service:** `app/services/gpt_service.py::generate_interview_questions`. Calls `generate_for_task(task="interview_questions", ...)`. The `interview_questions` task is already in the REASONING tier (`app/core/llm_router.py`) — question quality is already on the Pro-tier model.
- **Free-tier gate:** `app/services/usage_service.py::check_and_increment(user_id, "interview_prep", db)` is called first; free tier is capped at 3/month, Pro is unlimited (`PLAN_LIMITS`). The function both checks **and** writes a `usage_logs` row when it allows — so a naive "cache then gate" ordering would double-count for uncached calls. Ordering in this spec: *cache-lookup → gate → generate → persist*.
- **`hash_jd` primitive:** **does not exist today.** Zero grep matches in `hirelens-backend/` for `hash_jd`, `jd_hash`, `normalize_jd`. The tracker auto-populate Locked Decision (SESSION-STATE Locked Decisions) specs the normalization (`whitespace-normalized → casefold → SHA256`) and explicitly authorizes creating it at `app/utils/text_hash.py` when the first consumer needs it. Interview storage is that first consumer; scan-tracker auto-populate can adopt the same util later.
- **Storage:** no `interview_question_sets`, no `interview_generations` table. No cache layer on this path today.
- **Frontend call-sites (informational, 5.17b only):** `src/services/api.ts:193 generateInterviewPrep()` → `src/hooks/useInterview.ts:24` → `src/pages/Interview.tsx:126`. Today the "Regenerate Questions" button (line 364) calls the same endpoint with no `force_regenerate` flag; wiring it is 5.17b's job.

## 3. Solution

### 3.1 Data model

New ORM model: `app/models/interview_question_set.py`.

```
CREATE TABLE interview_question_sets (
    id             UUID PRIMARY KEY,
    user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    jd_hash        VARCHAR(64) NOT NULL,           -- SHA256 hex of normalized JD
    jd_text        TEXT NOT NULL,                  -- full original JD (display/edit use in 5.17b)
    questions      JSONB NOT NULL,                 -- [{question, star_framework}, ...]
    generated_at   TIMESTAMP NOT NULL DEFAULT now(),
    model_used     VARCHAR(50),                    -- audit trail, nullable (LLM provider may not surface model id)

    CONSTRAINT uq_interview_sets_user_jd UNIQUE (user_id, jd_hash)
);
CREATE INDEX ix_interview_sets_user_id ON interview_question_sets(user_id);
```

Notes:
- `jd_hash` is the SHA256 **hex** digest of the normalized JD. Normalization: collapse all whitespace runs to a single space → `strip()` → `casefold()`. This aligns with the scan-tracker Locked Decision ("whitespace-normalized, casefold, then SHA256").
- `questions` stores the exact list of `{question, star_framework}` objects the service produced, so replay is literal (no re-inference on read).
- `model_used` records `settings.llm_reasoning_model` at generation time (best-effort audit trail — empty string fallback if unavailable).

### 3.2 Shared util — `app/utils/text_hash.py`

New module — implements `hash_jd(text: str) -> str` and `_normalize_jd(text: str) -> str`. Scan-tracker auto-populate can adopt this in a later slice; this spec is the first consumer.

```python
def _normalize_jd(text: str) -> str:
    # Collapse consecutive whitespace (incl. newlines, tabs) to a single space,
    # then strip leading/trailing space, then casefold. Stable across copy/paste.
    return " ".join(text.split()).strip().casefold()

def hash_jd(text: str) -> str:
    return hashlib.sha256(_normalize_jd(text).encode("utf-8")).hexdigest()
```

### 3.3 API contract

**Modify existing endpoint in place.** Do **not** add a new path — the frontend calls `/api/interview-prep` and Rule 2 (backend-only slice) requires FE keeps working unmodified.

`POST /api/interview-prep` — body gains an **optional** `force_regenerate`:

```jsonc
// request
{
  "resume_text": "...",
  "job_description": "...",
  "force_regenerate": false   // optional, default false
}

// response — additive fields
{
  "questions": [...],         // existing
  "cached": true,             // NEW — true when served from the table
  "generated_at": "2026-...", // NEW — ISO-8601 UTC; when the set was (re)generated
  "model_used": "gemini-2.5-pro"  // NEW — best-effort audit, may be ""
}
```

Authenticated flow (`current_user` present):

1. Compute `jd_hash = hash_jd(body.job_description)`.
2. `SELECT` from `interview_question_sets WHERE user_id = ? AND jd_hash = ?`.
3. If row found **and** `not force_regenerate`:
   - **Return cached.** No LLM call, no `check_and_increment` — cache hit does **not** decrement the free-tier counter (AC-5).
4. Else:
   - `check_and_increment(user_id, "interview_prep", db)` → 403 `LIMIT_REACHED` if denied (unchanged from today).
   - `generate_interview_questions(resume_data, jd_requirements)` — reasoning tier.
   - `UPSERT` the row (on `(user_id, jd_hash)` conflict, overwrite questions/generated_at/model_used/jd_text — jd_text kept fresh in case whitespace changed but the normalized hash held).
   - Return with `cached=False`.

Unauthenticated flow (`current_user is None` — the legacy path still allows anon callers for backward compat): skip cache entirely, generate fresh, respond with `cached=False` and `generated_at=<now>`. Anonymous callers get today's behavior.

### 3.4 Free-tier interaction

- **Cache hit** → no `check_and_increment` call → no row in `usage_logs` → **does not count against the free-tier 3/month cap.**
- **New generation (cache miss or `force_regenerate=true`)** → `check_and_increment` runs → writes one `usage_logs` row → counts against the cap. 4th generation in a month returns 403 `LIMIT_REACHED` unchanged.

This mirrors the user's intuition: the expensive thing is the LLM call, not the API call, so the free-tier budget tracks LLM calls. A Pro user with `limit=-1` is unaffected regardless — the cache still saves LLM tokens for them.

### 3.5 Cache invalidation

- JD edit changes the normalized hash → cache miss → new row inserted (old row preserved).
- Whitespace-only changes (extra newline, leading/trailing spaces, case differences) do **not** change the hash — cache hits. Pinned by AC-4.
- Different users with the same JD get separate rows (unique index is `(user_id, jd_hash)`, not `(jd_hash)` alone — AC-3, no cross-tenant leak).
- Rows are never auto-deleted in this slice. Cascade-delete on `users.id` only (GDPR-style user deletion).

## 4. Acceptance Criteria

- **AC-1 — Second call with same JD returns cached.** Calling the service twice with the same `(user_id, job_description)` returns the same question set on the second call, `cached=True`, and the LLM is **not** invoked the second time.
- **AC-2 — `force_regenerate=True` bypasses cache.** Sets `cached=False`, invokes the LLM, and overwrites the stored row (same `(user_id, jd_hash)` key).
- **AC-3 — Cross-user isolation.** User A and User B submitting the same JD each get their own row. User B's first call is a cache miss (returns `cached=False`) even if User A cached it first. No leak across tenants.
- **AC-4 — Whitespace-insensitive cache hits.** Submitting the same JD with whitespace/newline/case variations (e.g., added trailing blank line, double spaces, `ALLCAPS` vs `allcaps`) hits the existing cache row — `cached=True`, no LLM call.
- **AC-5a — Cached hits do not decrement the counter.** Two cache-hit calls in a row do not write to `usage_logs` (so a free user who revisits their one cached JD 10 times still has `remaining=2` after the first generation).
- **AC-5b — New generations decrement the counter.** Each cache-miss or `force_regenerate=True` call writes exactly one `usage_logs` row with `feature_used="interview_prep"`.

## 5. Test Plan

| AC | Test | File |
|---|---|---|
| AC-1 | `test_second_call_returns_cached` | `tests/services/test_interview_storage.py` |
| AC-2 | `test_force_regenerate_bypasses_cache` | `tests/services/test_interview_storage.py` |
| AC-3 | `test_different_users_get_separate_sets` | `tests/services/test_interview_storage.py` |
| AC-4 | `test_whitespace_normalization_hits_cache` | `tests/services/test_interview_storage.py` |
| AC-5a | `test_cached_hit_does_not_decrement_free_tier` | `tests/services/test_interview_storage.py` |
| AC-5b | `test_new_generation_decrements_free_tier` | `tests/services/test_interview_storage.py` |

All six tests mock `app.services.gpt_service.generate_interview_questions` so they stay in the non-integration CI lane. They assert on: (a) whether the mock was called, (b) the `cached` flag in the return value, (c) the `usage_logs` row count for the test user. Test for `hash_jd` util (normalization + hash stability) lives next door as `test_text_hash.py::test_normalization_is_whitespace_and_case_insensitive` — small, direct, completes the Rule-14 coverage loop.

## 6. Out of Scope

- **Frontend wiring (tracked as 5.17b).** `useInterview.ts` does not yet pass `force_regenerate`; `Interview.tsx`'s "Regenerate Questions" button still calls the plain endpoint. This slice returns the `cached` and `generated_at` fields in the response, but nothing reads them until 5.17b. The JSON is additive, so the existing Pydantic type on the frontend (`InterviewPrepResponse`) keeps parsing — the extra fields are ignored by TypeScript's structural typing.
- **`GET /api/v1/interview/sets` (set listing endpoint).** Audit found no UI need for "list my past interview prep sets" today; the current frontend only ever renders one set at a time. Deferred to 5.17b if a listing UI ships.
- **Set deletion / sharing.** Not specced. Cascade-delete on user deletion is the only delete path.
- **Resume-text as a cache input.** The key is `(user_id, jd_hash)` — same JD with a different resume returns the cached questions from the first generation. Rationale: the prompt is JD-driven (skills extracted from JD + role title); the resume is used for flavor (`resume_text[:800]`). Returning cached is correct for the cost-leak fix; a "resume changed → regen" UX is a 5.17b product call.
- **Adopting `text_hash.hash_jd` in `tracker_service_v2`.** The scan-tracker auto-populate Locked Decision anticipated this util but never consumed it. This slice creates the util; retrofitting the tracker is a separate slice.
- **Unauthenticated caller caching.** The endpoint continues to accept anonymous callers (`current_user_optional`), but caching is keyed on `user_id` — anon callers always regenerate. Closing anonymous access is a separate auth-hardening concern.
- **Consolidating `ai_service.generate_interview_questions` (duplicate per S47-defer).** Dormant path, no FE caller.

## 7. Provenance

v2.1 item 5.17 flagged as 🔴 PENDING in `docs/PHASE-5-STATUS.md` (spec #48 doc-audit pattern, 2026-04-19). PHASE-5-STATUS surprise row: "no storage code **and** no dedicated spec file." This slice creates both — spec + code. Modeled on spec #35's pattern of reusing a stable JD hash; first actual implementation of that pattern.
