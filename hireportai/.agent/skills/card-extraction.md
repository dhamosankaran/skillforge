---
description: JSX → PostgreSQL card extraction pipeline
---
# Card Extraction Skill
## Overview
Extract 177 study cards currently hardcoded in JSX components
into the PostgreSQL cards table with embeddings.
## Pipeline
1. Parse JSX files → extract card content (question, answer, category, difficulty, tags)
2. INSERT into cards table
3. Generate embeddings via Gemini/OpenAI → UPDATE cards SET embedding = Vector(1536)
4. Verify: SELECT count(*) FROM cards = 177, all embeddings non-null
## Key Files
- Script: `scripts/extract_cards.py`
- Source: `hirelens-frontend/src/data/` or wherever JSX cards live
