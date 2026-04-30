"""Integration LLM tests — gated by `@pytest.mark.integration` per R13.

CI runs `pytest -m "not integration"` so these are deselected by default.
Run locally before merging changes that touch ingestion / extraction /
embeddings / cross-model dispatch.
"""
