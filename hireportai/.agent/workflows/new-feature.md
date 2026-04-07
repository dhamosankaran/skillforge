---
description: How to add a new feature to SkillForge end-to-end
---

## Steps

1. **Write the spec** in `docs/specs/phase-N/NN-feature-name.md`
   using the template from AGENTS.md

2. **Create the Alembic migration** (if new tables/columns needed)
// turbo
3. Run `cd hirelens-backend && alembic revision --autogenerate -m "add feature_name tables"`
// turbo
4. Run `cd hirelens-backend && alembic upgrade head`

5. **Write backend tests first** in `tests/test_feature_name.py`
   - Happy path test
   - Auth failure test (401)
   - Validation error test (422)
   - Plan gating test (403 for free users if applicable)

6. **Implement backend service** in `app/services/feature_service.py`
// turbo
7. Run `cd hirelens-backend && python -m pytest tests/test_feature_name.py -v`

8. **Implement API routes** in `app/api/routes/feature.py`
   - Register router in `main.py`
// turbo
9. Run `cd hirelens-backend && python -m pytest tests/ -v`

10. **Implement frontend page/component**
    - Create page in `src/pages/FeatureName.tsx`
    - Add route in `App.tsx`
    - Add API client method in `services/api.ts`

// turbo
11. Run `cd hirelens-frontend && npx vitest run`

12. **Manual verification**
    - Open browser, test the feature end-to-end
    - Test on mobile viewport

13. **Git commit**
    ```bash
    git add -A
    git commit -m "feat(feature): add feature_name — closes spec #NN"
    ```
