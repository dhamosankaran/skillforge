---
description: How to add a backend API route
---
## Steps
1. Create Pydantic schemas in `app/schemas/feature_name.py`
2. Create service in `app/services/feature_service.py`
3. Create route in `app/api/routes/feature.py`
4. Register router in `app/main.py`:
   `app.include_router(feature_router, prefix="/api/v1/feature", tags=["feature"])`
5. Add auth: `current_user: User = Depends(get_current_user)`
6. Add PostHog event tracking in the service layer
7. Write tests: happy path, 401, 422, 403 (if plan-gated)
8. Run: `python -m pytest tests/test_feature_api.py -v`
