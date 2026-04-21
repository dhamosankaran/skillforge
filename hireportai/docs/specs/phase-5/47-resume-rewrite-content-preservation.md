# Spec #47 — Resume Rewrite: Content Preservation

**Status:** Retroactive spec + prompt-contract regression test (v2.1 flag closure)
**Owner:** Dhamo
**Created:** 2026-04-19
**Phase:** 5 (v2.1 flag audit)
**Depends on:** Spec #09 (input-truncation fix — P5-S9). This spec does **not** re-fix that bug; it documents why the bug no longer reproduces and hardens the preservation contract with a second regression test.

## 1. Background — the v2.1 flag

The v2.1 playbook flagged the resume-rewrite feature as 🟡 PARTIAL with a "missing original content" symptom: premium users running **Generate AI Rewrite** on `/prep/rewrite` received an output that read like a summary, with later sections (Education, Certifications, earliest Experience entries) dropped. The playbook entry predates the P5-S9 fix.

A Step-2 audit against the current `main` branch (`fc933d1` — 2026-04-19) finds the bug **does not reproduce**. The two input/output caps that caused it are already lifted, the prompt is explicit about preservation, and an input-side regression test (P5-S9) pins the caps. What is **not** pinned today is the prompt's preservation contract itself — a future prompt refactor that simplifies the rules could silently reintroduce content loss with no CI signal. This spec closes that gap.

## 2. Current implementation (what prevents the bug today)

### 2.1 Live path

```
FE /prep/rewrite (src/pages/Rewrite.tsx)
  → useRewrite (src/hooks/useRewrite.ts)
  → rewriteResume (src/services/api.ts:154)
  → POST /api/rewrite (unauth; FE gates on canUsePremium)
  → app/api/routes/rewrite.py::rewrite_resume
  → app/services/gpt_service.py::generate_resume_rewrite
  → app/core/llm_router.py::generate_for_task(task="resume_rewrite", …)
  → REASONING tier (Gemini 2.5 Pro by default)
```

`app/api/v1/routes/rewrite.py` re-exports the legacy router (line 2), so `/api/v1/rewrite` is the same endpoint — no second code path. The dormant enterprise-only `POST /api/v1/resume/{id}/optimize` in `app/api/v1/routes/resume.py:66` uses `app/services/ai_service.py::generate_resume_rewrite` (a duplicate of the live function) and is **not** consumed by the frontend; parity is a best-effort soft constraint, not the focus of this spec.

### 2.2 Caps (fixed by P5-S9 / spec #09)

| Location | Value | Bug before P5-S9 |
|---|---|---|
| `app/services/gpt_service.py:100` | `resume_text = resume_data.get("full_text", "")[:40000]` | was `[:4000]` — dropped tail sections |
| `app/services/gpt_service.py:125` | `max_tokens=8000` | was `4000` — output ran out on long resumes |

### 2.3 Prompt preservation contract (`gpt_service.py:104-121`)

```
You are an expert resume writer specializing in ATS optimization.
Rewrite the following resume to maximize ATS compatibility for the target role.

Rules:
1. Maintain the EXACT same sections as the original (Summary, Experience, Skills, Education, etc.)
2. Improve bullet points with quantified achievements (numbers, percentages, dollar amounts)
3. Incorporate the missing keywords naturally into relevant sections
4. Use strong action verbs at the start of each bullet
5. Keep the tone professional and confident
6. Output in clean markdown with ## headers for each section, - for bullet points
7. Do NOT add sections that weren't in the original resume
8. Do NOT remove any jobs, education entries, or skills — only improve the language

Missing keywords to incorporate: {missing_kw_str}
Target role: {jd_title}

Original resume:
{resume_text}
```

Rules 1, 7, and 8 are the **preservation contract**. They say: keep every section, add nothing, remove nothing, only improve the language. Rule 2 ("improve … with quantified achievements") is the rewriting license; paired with Rule 8 ("only improve the language") the LLM is steered toward rephrasing rather than fabricating. Temperature is 0.4 — conservative, which reinforces preservation over creativity.

## 3. Why the v2.1 bug no longer reproduces

| Bug precondition (v2.1) | State on `main` (2026-04-19) |
|---|---|
| Resume truncated to 4k chars before prompting → LLM never sees tail sections | Fixed: `[:40000]` (spec #09) |
| `max_tokens=4000` cuts generation mid-output on long resumes | Fixed: `max_tokens=8000` (spec #09) |
| Prompt lacks explicit "keep every section" language | Already present: rules 1 + 7 + 8 |
| Low-reasoning model (Gemini Flash) used for long-form rewrite | Fixed: `resume_rewrite` is in the reasoning-tier task list (`llm_router.py`) → Gemini 2.5 Pro by default |

The input-truncation regression is pinned by `tests/services/test_resume_rewrite.py::test_full_resume_reaches_llm_prompt` (12k-char fixture → every section heading + every org name must appear in the LLM-bound prompt). That test was added in P5-S9.

## 4. Gap this spec closes — prompt-contract regression test

The P5-S9 test pins *input size* but not *prompt wording*. If a future refactor of `generate_resume_rewrite` dropped rules 1, 7, or 8 (e.g., to simplify the prompt, shorten it for a fast-tier model, or unify with a different style guide), the LLM would become more likely to drop or fabricate content and CI would stay green.

This spec adds one new test — `test_prompt_includes_preservation_rules` — that asserts the rendered prompt contains the verbatim preservation clauses. The test belongs next to the existing `test_full_resume_reaches_llm_prompt` in `tests/services/test_resume_rewrite.py` because both pin different facets of the same anti-regression invariant: *"the LLM receives the full resume with instructions that forbid dropping content."*

## 5. Acceptance Criteria

- **AC-1 — Input survives to the prompt.** Every section heading and every org name from a ≥10k-char fixture appears in the prompt passed to `generate_for_task`, and `max_tokens` is not set below 8000. Covered by: `test_full_resume_reaches_llm_prompt` (existing, spec #09).
- **AC-2 — Preservation rules survive in the prompt.** The rendered prompt contains the verbatim phrases:
  - `"Maintain the EXACT same sections as the original"`
  - `"Do NOT add sections that weren't in the original resume"`
  - `"Do NOT remove any jobs, education entries, or skills"`
  **New this spec.** Covered by: `test_prompt_includes_preservation_rules` (new, added alongside the existing test).

## 6. Test Plan

| Test | File | AC |
|---|---|---|
| `test_full_resume_reaches_llm_prompt` (existing) | `tests/services/test_resume_rewrite.py` | AC-1 |
| `test_prompt_includes_preservation_rules` (**new this slice**) | `tests/services/test_resume_rewrite.py` | AC-2 |

Run: `python -m pytest tests/services/test_resume_rewrite.py -v`. Full backend suite: `python -m pytest tests/ -v --tb=short -m "not integration"`.

No frontend changes. `ResumeEditor`/`MarkdownPreview` render `full_text` verbatim; no client-side content mutation is possible. Frontend test count unchanged.

## 7. Out of Scope

- **Prompt rewrite.** The existing rules are sufficient; strengthening them (e.g. "preserve every metric/number/company/date literally") is a separate hardening slice, not required to close the v2.1 flag.
- **Consolidating `ai_service.generate_resume_rewrite` with `gpt_service.generate_resume_rewrite`.** The ai_service variant is dormant (enterprise-only; no FE caller) and ships the same prompt structure. Duplication is Phase-6 cleanup tech debt, not a preservation concern.
- **Authenticating `/api/rewrite`.** Called out as out-of-scope in spec #09 §Out of Scope; still tracked.
- **Output-side assertions against a real LLM.** Spec #09's approach (mock `generate_for_task`, assert on the prompt text fed into the router) remains the correct pattern — we cannot make CI-stable assertions about model outputs without live API keys, and `pytest.mark.integration` would deselect such tests in CI anyway (CLAUDE.md Rule 13).
- **Extending this test to `app/services/ai_service.py`.** That function is on the dormant enterprise path; duplicating the test there would be cargo-culted coverage. If and when the enterprise path is wired up in frontend, add parallel coverage then.
- **Migrating the live endpoint to the v1 namespace.** `app/api/v1/routes/rewrite.py` re-exports the legacy router today; consolidation is Phase-6 cleanup.

## 8. Provenance

> **⚠ SUPERSEDED-IN-PART BY SPEC #51 (2026-04-21)**
>
> The "flag closed / bug gone" claim in this section is stale. Investigation 2026-04-21 (`docs/audit/2026-04-b001-rewrite-investigation.md`) confirmed the B-001 bug still manifests via a different dominant root cause — output-side thinking-budget contention + empty `sections` + broken export paths. Spec #51 supersedes the resolution claim. This spec's AC-2 preservation-regression test remains valid and is inherited by #51.

v2.1 playbook flagged the feature as 🟡 PARTIAL with "missing original content". Spec #09 (P5-S9, 2026-04-17) fixed the underlying input-truncation + max-tokens caps. This spec is a retroactive closure of the v2.1 flag: Step-2 audit confirmed the fix still holds on `main` (`fc933d1`), the feature is 🟢 GREEN, and this document adds AC-2 as a prompt-contract regression guard. Models the Rule-14 doc-sync pattern used by spec #43.
