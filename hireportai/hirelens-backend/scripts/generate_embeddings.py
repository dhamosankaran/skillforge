#!/usr/bin/env python3
"""
Generate embeddings for all cards in PostgreSQL.

Embedding model : gemini-embedding-exp-03-07 (output_dimensionality=1536)
Fallback        : deterministic synthetic embeddings when GEMINI_API_KEY is
                  absent or invalid (dev / CI environments without API access)

RUN
  cd hireportai/hirelens-backend
  source venv/bin/activate
  python scripts/generate_embeddings.py

IDEMPOTENT — only processes cards where embedding IS NULL.
"""

import asyncio
import hashlib
import math
import os
import struct
import sys
import time
from pathlib import Path
from typing import Optional

# ── sys.path so app.* imports work ─────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

# ── Constants ───────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "gemini-embedding-exp-03-07"
EMBEDDING_DIMS = 1536
BATCH_SIZE = 20
RATE_LIMIT_SLEEP = 0.5   # seconds between batches (avoid 429s)


# ── Embedding helpers ────────────────────────────────────────────────────────

def _synthetic_embedding(text_input: str, dims: int = EMBEDDING_DIMS) -> list[float]:
    """Deterministic, normalized fake embedding from SHA-256.

    Used when GEMINI_API_KEY is absent or invalid.  Vectors are reproducible
    (same text → same vector) and unit-length, so cosine similarity queries
    work structurally even though they carry no semantic meaning.
    """
    values: list[float] = []
    seed = 0
    while len(values) < dims:
        digest = hashlib.sha256(f"{seed}:{text_input}".encode()).digest()
        for i in range(0, len(digest) - 3, 4):
            if len(values) >= dims:
                break
            (raw,) = struct.unpack(">f", digest[i : i + 4])
            if math.isfinite(raw):
                values.append(raw)
        seed += 1
    values = values[:dims]
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def _probe_gemini() -> Optional[object]:
    """Return an initialised Gemini client, or None if the key is missing/bad."""
    try:
        from google import genai

        key = get_settings().gemini_api_key
        if not key:
            return None
        client = genai.Client(api_key=key)
        # Cheap probe — 1-token embedding
        from google.genai import types
        client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents="probe",
            config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMS),
        )
        return client
    except Exception:
        return None


def _gemini_embed(client, texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using the Gemini API."""
    from google.genai import types

    results = []
    for t in texts:
        resp = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=t,
            config=types.EmbedContentConfig(
                task_type="SEMANTIC_SIMILARITY",
                output_dimensionality=EMBEDDING_DIMS,
            ),
        )
        results.append(resp.embeddings[0].values)
    return results


# ── Main pipeline ────────────────────────────────────────────────────────────

async def generate_embeddings() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Decide which embedding backend to use
    print("Probing Gemini API…", flush=True)
    gemini_client = await asyncio.to_thread(_probe_gemini)
    if gemini_client:
        print(f"  ✓ Gemini API available — using {EMBEDDING_MODEL} ({EMBEDDING_DIMS} dims)")
        use_synthetic = False
    else:
        print(
            "  ⚠  Gemini API unavailable (key missing or invalid).\n"
            "     Using deterministic synthetic embeddings for dev/CI.\n"
            "     Re-run with a valid GEMINI_API_KEY to get real embeddings."
        )
        use_synthetic = True

    # Fetch cards with no embedding
    async with factory() as session:
        rows = (
            await session.execute(
                text("SELECT id, question, answer FROM cards WHERE embedding IS NULL")
            )
        ).fetchall()

    if not rows:
        print("\nAll cards already have embeddings — nothing to do.")
        await engine.dispose()
        return

    print(f"\nGenerating embeddings for {len(rows)} card(s)…")

    updated = 0
    errors = 0

    for batch_start in range(0, len(rows), BATCH_SIZE):
        batch = rows[batch_start : batch_start + BATCH_SIZE]
        ids = [r[0] for r in batch]
        texts = [f"{r[1]}\n\n{r[2]}" for r in batch]  # question + answer

        # Embed the batch
        try:
            if use_synthetic:
                vectors = [_synthetic_embedding(t) for t in texts]
            else:
                vectors = await asyncio.to_thread(_gemini_embed, gemini_client, texts)
        except Exception as exc:
            print(f"  ERROR embedding batch {batch_start // BATCH_SIZE + 1}: {exc}")
            errors += len(batch)
            continue

        # Write to DB
        async with factory() as session:
            for card_id, vector in zip(ids, vectors):
                vec_literal = f"[{','.join(str(v) for v in vector)}]"
                await session.execute(
                    text(
                        "UPDATE cards SET embedding = CAST(:vec AS vector) "
                        "WHERE id = :id"
                    ),
                    {"vec": vec_literal, "id": card_id},
                )
            await session.commit()

        updated += len(batch)
        print(
            f"  Batch {batch_start // BATCH_SIZE + 1}: "
            f"{len(batch)} card(s) embedded [{updated}/{len(rows)}]"
        )

        if not use_synthetic and batch_start + BATCH_SIZE < len(rows):
            time.sleep(RATE_LIMIT_SLEEP)

    await engine.dispose()

    # ── Verification ─────────────────────────────────────────────────────────
    verify_engine = create_async_engine(settings.async_database_url, echo=False)
    verify_factory = async_sessionmaker(
        verify_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with verify_factory() as session:
        total = (
            await session.execute(text("SELECT count(*) FROM cards"))
        ).scalar_one()
        with_emb = (
            await session.execute(
                text("SELECT count(*) FROM cards WHERE embedding IS NOT NULL")
            )
        ).scalar_one()
        null_emb = total - with_emb
    await verify_engine.dispose()

    print()
    print("── generate_embeddings.py complete ───────────────────────")
    print(f"  Updated : {updated}")
    print(f"  Errors  : {errors}")
    print(f"  Total cards            : {total}")
    print(f"  Cards with embedding   : {with_emb}")
    print(f"  Cards WITHOUT embedding: {null_emb}")
    backend = "synthetic (dev)" if use_synthetic else f"Gemini {EMBEDDING_MODEL}"
    print(f"  Embedding backend      : {backend}")
    print("──────────────────────────────────────────────────────────")

    if null_emb > 0:
        print(f"\nWARNING: {null_emb} card(s) still have NULL embeddings.")
        sys.exit(1)


def main() -> None:
    asyncio.run(generate_embeddings())


if __name__ == "__main__":
    main()
