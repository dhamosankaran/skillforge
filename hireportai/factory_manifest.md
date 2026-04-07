# 🏭 SkillForge Factory Manifest

> The operating manual for building SkillForge with Claude Code.
> Read this before every coding session.

---

## 🛡️ The Context-Slice-Test-Ship Mantra

### Step 1: CONTEXT (Anchor the AI)

**Prompt template:**
```
Read AGENTS.md.
Read .agent/skills/[relevant-skill].md.
Read docs/specs/phase-X/[spec-number]-[spec-name].md.
```

### Step 2: SLICE (Scope the task to ~30 minutes)

**Prompt template:**
```
We are executing AC-[N] from the spec.
Write the [SQLAlchemy model / Pydantic schema / service method / API route / React component].
Write the Pytest/Vitest test for it.
Do NOT implement [the next thing] yet.
```

### Step 3: TEST (Prove it works)

**Prompt template:**
```
Run python -m pytest tests/test_[name].py -v
Fix any errors.
```

> [!CAUTION]
> **3-Strike Rule**: If a test fails 3 times in a row, STOP.
> Do NOT attempt another fix. Print the error, list 2-3 root cause
> hypotheses, and wait for human intervention.

### Step 4: SHIP (Lock it in)

**Prompt template:**
```
The tests passed. Run:
git add -A
git commit -m "feat([scope]): [description] — closes spec #[NN]"
```

### Step 5: REPEAT

Move to the next Acceptance Criterion in the spec.
When all ACs are complete, mark the spec status as `Done`.

---

## 📋 Current Sprint Status

| Phase | Status | Specs |
|-------|--------|-------|
| Phase 0: Foundation Surgery | ⬜ Not Started | 00-03 |
| Phase 1: Core Study Engine | ⬜ Not Started | 04-09 |
| Phase 2: Gamification + Admin | ⬜ Not Started | 10-14 |
| Phase 3: ATS Bridge + Mission | ⬜ Not Started | 15-19 |
| Phase 4: Polish + Launch | ⬜ Not Started | 20-22 |

## 🗂️ Quick Reference

| Need To... | Do This |
|------------|---------|
| Add a feature | Read `.agent/workflows/new-feature.md` |
| Add an API route | Read `.agent/workflows/new-api-route.md` |
| Add a UI page | Read `.agent/workflows/new-ui-page.md` |
| Run tests | `python -m pytest tests/ -v --tb=short` |
| Create a migration | `alembic revision --autogenerate -m "desc"` |
| Test a migration | `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` |
| Start backend | `cd hirelens-backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000` |
| Start frontend | `cd hirelens-frontend && npm run dev -- --port 5199` |
