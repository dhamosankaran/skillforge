# E2E Bug Diagnosis — 2026-04-21

> Read-only trace. No fixes in this slice.
> HEAD at audit: `360b0a7`. Log source: `hireportai/logs/backend.log` (881 lines, 2026-04-21 session).
> Skills referenced: `ats-scanner.md`, `study-engine.md`, `llm-strategy.md`, `payments.md`.

---

## Bug (a) — "Regenerate with Resume" → "Something went wrong"

### Status: **confirmed root cause in logs** — regression from spec #51's own fix.

### What the log says (lines 149–178)

```
149  Gemini returned empty text (model=gemini-2.5-pro, json_mode=True, max_tokens=2500);
     raw response=GenerateContentResponse(
152    candidates=[Candidate(content=Content(role='model'),
156      finish_reason=<FinishReason.MAX_TOKENS: 'MAX_TOKENS'>, index=0)],
160    model_version='gemini-2.5-pro',
165    usage_metadata=GenerateContentResponseUsageMetadata(
166      prompt_token_count=1858,
173      thoughts_token_count=2497,
174      total_token_count=4355
      )
    )
177  rewrite_failed: reason=rewrite_parse_error resume_chars=12164
178  "POST /api/rewrite HTTP/1.1" 502 Bad Gateway
```

**The smoking gun:** `thoughts_token_count=2497` consumed nearly the entire `max_tokens=2500` cap → output text was empty → `FinishReason.MAX_TOKENS`. This is exactly the B-001 "thinking-budget contention" failure mode that spec #51 was supposed to have fixed.

### Why spec #51 didn't catch it here

Spec #51 added two paths:
- **Option B (section chunking)** — primary. Each section gets its own LLM call at `SECTION_MAX_TOKENS=2500`.
- **Option A (full-rewrite fallback)** — safety net. Single call at `FULL_REWRITE_FALLBACK_MAX_TOKENS=16000` with a `thinking_budget=FULL_REWRITE_THINKING_BUDGET` cap to stop thinking from starving output.

The **section path is missing the `thinking_budget` kwarg** at `hirelens-backend/app/services/gpt_service.py:380-387`:

```python
text = await asyncio.to_thread(
    generate_for_task,
    task="resume_rewrite_section",
    prompt=prompt,
    json_mode=True,
    max_tokens=SECTION_MAX_TOKENS,   # 2500
    temperature=0.4,
)                                     # ← NO thinking_budget
```

Contrast with the fallback path at `gpt_service.py:487-495` which correctly passes `thinking_budget=FULL_REWRITE_THINKING_BUDGET`.

The per-section `generate_section_rewrite` at `gpt_service.py:620` has the same omission (same missing kwarg).

### Why the FE shows "Something went wrong"

1. BE returns **HTTP 502** with a structured AC-5 error envelope: `{error_code: "rewrite_parse_error", message: ..., retry_hint: "retry"}`.
2. FE axios response interceptor at `hirelens-frontend/src/services/api.ts:127-133` fires a global `toast.error` for any non-401 error:

   ```ts
   const message =
     error.response?.data?.error ||
     error.response?.data?.detail ||
     error.message ||
     'An unexpected error occurred'
   toast.error(message)
   ```

3. For a 502 with the structured envelope, `error.response.data.error` is `"rewrite_parse_error"` (a machine-readable code, not user copy). That string gets toasted verbatim → user sees a cryptic code or, if the shape differs, falls through to `'An unexpected error occurred'`.

4. `useRewrite.runRewrite` at `hirelens-frontend/src/hooks/useRewrite.ts:13-24` has **no catch block** — the error re-throws as an unhandled promise rejection. `Rewrite.tsx:90-96` `handleGenerate` doesn't `.catch()` or `await` either. Result: toast fires, spinner stops, no retry UX, no B-001-style structured error surface.

### Contributing factors on this specific call

- Prompt token count (1858) was high relative to the 2500 cap. A shorter section would have more headroom for output. `_section_rewrite_prompt` at `gpt_service.py:285` embeds the section content + JD title + missing keywords — long resumes (Dhamo's was 12,164 chars) push prompt tokens up section-by-section.
- Gemini 2.5 Pro's thinking pool is not bounded by `max_output_tokens`; without `thinking_budget`, it uses whatever it wants.

### Minimum repro

1. Go to `/prep/analyze`, upload a resume ≥ ~8k chars with multiple distinct sections, paste a JD, submit.
2. On `/prep/results`, click through to `/prep/rewrite`.
3. Click the primary "Regenerate with Resume" button (`handleGenerate`).
4. BE log will show `Gemini returned empty text` + `rewrite_failed: reason=rewrite_parse_error` + `POST /api/rewrite 502`.
5. FE will show a toast (message varies depending on envelope shape).

### Fix-slice estimate

**Small.** One-file change to `gpt_service.py`:
- Pass `thinking_budget=SECTION_THINKING_BUDGET` (new constant, suggest 500–800) to the two section-path `generate_for_task` calls at lines 381-387 and 617-623.
- Adjust `SECTION_MAX_TOKENS` upward (e.g., 3500–4000) if needed — 2500 was chosen pre-thinking-budget-cap and is now tight.
- Add regression test under `tests/services/test_resume_rewrite.py` asserting the section call passes `thinking_budget` (guard against future drift).

No spec slice needed — this is a pure implementation bug, falls under CLAUDE.md R14 exception (b) "pure bug fixes with no design surface." Spec #51 LD-4 already authorizes the thinking-budget mechanism; we're just applying it consistently. **Candidate BACKLOG row:** new B-014 or amend B-001 closed-notes to log the regression. Given B-001 is ✅ closed, prefer a new B-014 "resume rewrite section-path missing thinking_budget cap" P0.

---

## Bug (b) — "5th card review → something went wrong"

### Status: **partial root cause found in logs + code.** "5th card" framing is misleading — actual trigger was review #16 (spec #50 wall), surfaced via a noisy FE interceptor.

### What the log says (lines 700–865)

Total successful `POST /api/v1/study/review 200` responses from Dhamo's session:

| Lines | Count |
|-------|-------|
| 700, 702, 704, 706, 708 | 5 |
| 726, 728, 730, 732, 734 | 5 |
| 805, 841, 859, 861, 863 | 5 |
| **Subtotal: 15 successful reviews** | |
| **Line 865:** `POST /api/v1/study/review HTTP/1.1 402 Payment Required` — the **16th review** | |

This is spec #50 LD-001 working **exactly as designed**: `_DAILY_CARD_LIMIT=15`, `count_after > 15 → raise DailyReviewLimitError` (see `hirelens-backend/app/services/study_service.py:243-263`). The FE's perceived "5th card" was probably the 5th card of the 4th mini-session (Daily Review queue is `LIMIT 5` per fetch per `study-engine.md:32`), not the absolute count.

### Why the FE shows an error toast instead of `PaywallModal`

The BE returns HTTP 402 with:
```json
{"detail": {
  "error": "free_tier_limit",
  "trigger": "daily_review",
  "cards_consumed": 15,
  "cards_limit": 15,
  "resets_at": "2026-04-22T00:00:00+00:00"
}}
```

`QuizPanel.tsx:97-108` extracts this correctly (`extractWallPayload` returns the payload for 402 with `detail.trigger === 'daily_review'`). But **before** QuizPanel's handler runs, the axios response interceptor at `api.ts:127-133` fires a global toast:

```ts
if (error.response?.status !== 401) {
  const message =
    error.response?.data?.error ||          // undefined — 'error' is nested under detail
    error.response?.data?.detail ||         // the wall payload OBJECT, not a string
    error.message ||
    'An unexpected error occurred'
  toast.error(message)                       // toasts an object → "[object Object]"
}
```

`error.response.data.detail` is the object `{error: "free_tier_limit", trigger: "daily_review", ...}`. Passing an object to `toast.error(message)` either renders `"[object Object]"` or coerces to a JSON-stringified payload — either way, the user sees a cryptic string before (or alongside) whatever QuizPanel renders.

### Supporting log evidence

After the 402 at line 865, I expected to see `GET /api/v1/payments/should-show-paywall?...` per `QuizPanel.tsx:211` — but **none appears** in lines 866–881. Instead:
- Line 866–867: `GET /api/v1/payments/pricing` (×2) — consistent with the user navigating to `/pricing`
- Line 868–869: `GET /api/v1/auth/me` — Pricing-page auth refetch

So Dhamo did NOT see the `PaywallModal` in any useful way — either the modal never rendered (QuizPanel race / extract returned null) or he dismissed it + navigated to pricing. Without browser devtools we can't fully disambiguate. But the most likely chain is: **interceptor toast fires** → Dhamo reads "[object Object]" or "An unexpected error occurred" → **perceives as generic error** → navigates away before the PaywallModal renders (or it doesn't render at all because `shouldShowPaywall` was never called — the log shows no such GET).

### The deeper design issue

The axios interceptor is **not wall-aware**. Spec #50 + spec #42 assume `QuizPanel` owns the wall UX (modal + nudge orchestration). The interceptor short-circuits that by toasting first. Every 402 anywhere in the app currently triggers a spurious toast. This likely also breaks the paywall-dismissal flow in spec #42 whenever the BE returns the dismissal payload.

### Minimum repro

1. Log in as a free user.
2. Submit 15 card reviews in any mix of `/learn/daily`, `/learn/card/:id`, `/learn/mission` (all route through `QuizPanel`).
3. Submit the 16th.
4. BE log: `POST /api/v1/study/review 402`.
5. FE console + toast: interceptor fires a toast with either `[object Object]` or a truncated string. `PaywallModal` may or may not render depending on timing.

### Fix-slice estimate

**Small — but two separable fixes.**

1. **Interceptor exception for 402 with known trigger shapes.** Amend `api.ts:127-133` to skip the toast when `error.response?.data?.detail?.trigger` is one of the known wall triggers (`daily_review`, `paywall_hit`, etc.). Let downstream handlers (QuizPanel, MissingSkillsPanel) own the UX. No spec change needed — specs #50 and #42 already assert component-level ownership. **Prefer this first.**
2. **Interceptor object-coercion guard.** Change the fallback chain to extract a string from `detail` when it's an object (e.g., `detail.message || 'An unexpected error occurred'`). Prevents "[object Object]" toasts regardless of trigger. Orthogonal to #1 and cleaner.

**Candidate BACKLOG row:** new **B-015** "axios response interceptor toasts raw wall-payload objects on 402" P1 (launch-adjacent — breaks the spec #50 + #42 designed UX for every free user hitting the wall).

No spec slice needed. R14 exception (b) applies.

### Secondary question: did QuizPanel's `PaywallModal` render at all?

The log has no GET `/should-show-paywall` call between lines 865 and 881, which means one of:
- QuizPanel's `extractWallPayload` returned `null` (shape mismatch we haven't spotted) — but code inspection says it should match.
- The user unmounted QuizPanel before the async `shouldShowPaywall` fired (navigation away).
- `setWall(payload)` fired but the effect that triggers `shouldShowPaywall` didn't run (state racing).

**Needs browser repro with network tab open** to confirm. Flagged as follow-up for Dhamo's next walkthrough.

---

## Reproduction plan (single session, both bugs)

```
1. ./scripts/dev-start.sh  (or ../scripts/dev-start.sh from hireportai/)
2. Log in. Ensure account is on free plan.
3. /prep/analyze → upload resume (≥ 8k chars, 3+ clear sections) + paste JD → submit.
4. On /prep/results → click "Generate Rewrite" or equivalent → /prep/rewrite → click "Regenerate".
5. Observe BE log: expect "Gemini returned empty text" + "rewrite_failed: reason=rewrite_parse_error" + 502.
6. Observe FE: expect toast, no structured error UI.
7. Navigate to /learn/daily. Review cards. After 15 cumulative reviews (across sessions):
8. Submit a 16th review → expect BE log "POST /study/review 402".
9. Observe FE console: expect a toast fired by the global interceptor. PaywallModal behaviour needs network tab.
```

---

## Summary table

| Bug | Surface | Root cause | BE log evidence | FE code evidence | Fix size |
|-----|---------|------------|-----------------|------------------|----------|
| (a) Rewrite 502 | `POST /api/rewrite` | Section-path `generate_for_task` call missing `thinking_budget` kwarg; Gemini 2.5 Pro thinking pool consumed 2497/2500 output tokens | logs/backend.log:149-178 | gpt_service.py:381-387 + useRewrite.ts:13-24 (no catch) | small (1-file BE + test) |
| (b) 402 surfaces as generic toast | axios response interceptor | Interceptor is not wall-aware; toasts `error.response.data.detail` when it's an object, not a string | logs/backend.log:865 + no follow-up /should-show-paywall GET | api.ts:127-133 + QuizPanel.tsx:97-108 | small (1-file FE, 2 separable fixes) |

Neither bug needs a new spec. Both are implementation-level regressions inside shipped specs (#51 and #50/#42 respectively).

---

## Meta

| Field | Value |
|-------|-------|
| HEAD at audit | `360b0a7` |
| BE log lines scanned | 881 (full file) |
| Files read | `logs/backend.log`, `hirelens-backend/app/services/gpt_service.py`, `hirelens-backend/app/services/study_service.py`, `hirelens-frontend/src/services/api.ts`, `hirelens-frontend/src/hooks/useRewrite.ts`, `hirelens-frontend/src/pages/Rewrite.tsx`, `hirelens-frontend/src/components/study/QuizPanel.tsx` |
| N6 check | ✅ Every claim has a file:line or log:line citation. Where behavior needed to be inferred without browser access (bug b's modal render), stated as "needs browser repro". |
