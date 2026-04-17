#!/usr/bin/env python3
"""
Extract study cards from archive/prototype/src/data/cards.js into PostgreSQL.

SOURCE
  archive/prototype/src/data/cards.js
  The file header notes it contains representative prototype cards.
  Actual count: 15 cards across 14 categories.

RUN
  cd hireportai/hirelens-backend
  source venv/bin/activate
  python scripts/extract_cards.py

IDEMPOTENCY
  Category IDs and Card IDs are deterministic (uuid5) so re-running
  produces the same primary keys → ON CONFLICT (id) DO NOTHING is safe.
"""

import asyncio
import json
import subprocess
import sys
import uuid
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_DIR.parents[1]          # …/SkillForge/
CARDS_JS = REPO_ROOT / "archive" / "prototype" / "src" / "data" / "cards.js"

# ── Add backend to sys.path so app.* imports work ──────────────────────────
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

# ── Deterministic ID helpers ────────────────────────────────────────────────
_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # uuid.NAMESPACE_URL


def cat_uuid(name: str) -> str:
    return str(uuid.uuid5(_NS, f"category:{name}"))


def card_uuid(cat_name: str, question: str) -> str:
    return str(uuid.uuid5(_NS, f"card:{cat_name}:{question[:200]}"))


# ── Parse cards.js via Node.js ─────────────────────────────────────────────

def load_categories() -> dict:
    """Use Node 18+ dynamic import to parse the ESM cards.js and return CATEGORIES."""
    if not CARDS_JS.exists():
        sys.exit(f"ERROR: cards.js not found at {CARDS_JS}\n"
                 f"  Expected: {CARDS_JS}")

    # Dynamic import works with file:// URIs in Node 18+
    file_uri = CARDS_JS.as_uri()
    inline = (
        f'import("{file_uri}")'
        ".then(m => process.stdout.write(JSON.stringify(m.CATEGORIES)))"
        ".catch(e => { process.stderr.write(String(e)); process.exit(1); });"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "--eval", inline],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        sys.exit(f"Node.js failed to parse cards.js:\n{result.stderr}")

    return json.loads(result.stdout)


# ── Database seeding ────────────────────────────────────────────────────────

async def seed(categories_data: dict) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    cat_inserted = 0
    cat_skipped = 0
    card_inserted = 0
    card_skipped = 0

    async with session_factory() as session:
        # ── 1. Seed categories ──────────────────────────────────────────────
        for display_order, (cat_name, cat_info) in enumerate(categories_data.items()):
            cat_id = cat_uuid(cat_name)
            result = await session.execute(
                text("""
                    INSERT INTO categories
                        (id, name, icon, color, display_order, source, tags)
                    VALUES
                        (:id, :name, :icon, :color, :display_order, :source,
                         CAST(:tags AS jsonb))
                    ON CONFLICT (id) DO NOTHING
                    RETURNING id
                """),
                {
                    "id": cat_id,
                    "name": cat_name,
                    "icon": cat_info.get("icon", "📚"),
                    "color": cat_info.get("color", "#6366F1"),
                    "display_order": display_order,
                    "source": "foundation",
                    "tags": json.dumps([]),
                },
            )
            if result.fetchone():
                cat_inserted += 1
            else:
                cat_skipped += 1

        # ── 2. Seed cards ───────────────────────────────────────────────────
        for cat_name, cat_info in categories_data.items():
            cat_id = cat_uuid(cat_name)
            for card in cat_info.get("cards", []):
                question = card.get("q", "")
                answer = card.get("a", "")
                difficulty = card.get("difficulty", "Medium")
                tags = card.get("tags", [])

                card_id = card_uuid(cat_name, question)

                result = await session.execute(
                    text("""
                        INSERT INTO cards
                            (id, category_id, question, answer, difficulty, tags)
                        VALUES
                            (:id, :category_id, :question, :answer, :difficulty,
                             CAST(:tags AS json))
                        ON CONFLICT (id) DO NOTHING
                        RETURNING id
                    """),
                    {
                        "id": card_id,
                        "category_id": cat_id,
                        "question": question,
                        "answer": answer,
                        "difficulty": difficulty,
                        "tags": json.dumps(tags),
                    },
                )
                if result.fetchone():
                    card_inserted += 1
                else:
                    card_skipped += 1

        await session.commit()

    await engine.dispose()

    # ── Summary ─────────────────────────────────────────────────────────────
    print()
    print("── extract_cards.py complete ─────────────────────────────")
    print(f"  Categories : {cat_inserted} inserted, {cat_skipped} skipped"
          f"  (total {cat_inserted + cat_skipped})")
    print(f"  Cards      : {card_inserted} inserted, {card_skipped} skipped"
          f"  (total {card_inserted + card_skipped})")
    print()

    # Verification queries
    verify_engine = create_async_engine(settings.async_database_url, echo=False)
    verify_factory = async_sessionmaker(
        verify_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with verify_factory() as session:
        total_cards = (
            await session.execute(text("SELECT count(*) FROM cards"))
        ).scalar_one()
        null_embeddings = (
            await session.execute(
                text("SELECT count(*) FROM cards WHERE embedding IS NULL")
            )
        ).scalar_one()
        breakdown = (
            await session.execute(
                text("""
                    SELECT cat.name, count(c.id) AS card_count
                    FROM categories cat
                    JOIN cards c ON c.category_id = cat.id
                    GROUP BY cat.name, cat.display_order
                    ORDER BY cat.display_order
                """)
            )
        ).fetchall()
    await verify_engine.dispose()

    print(f"  DB total cards     : {total_cards}")
    print(f"  Cards with no embed: {null_embeddings}")
    print()
    print("  Category breakdown:")
    for row in breakdown:
        print(f"    {row[0]:<35} {row[1]} card(s)")
    print()

    if null_embeddings > 0:
        print("  NOTE: Run the embeddings pass next to populate embedding column.")
    print("──────────────────────────────────────────────────────────")


# ── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    print(f"Loading cards from: {CARDS_JS}")
    categories_data = load_categories()
    total_cards = sum(len(v.get("cards", [])) for v in categories_data.values())
    print(f"Parsed {len(categories_data)} categories, {total_cards} cards.")
    asyncio.run(seed(categories_data))


if __name__ == "__main__":
    main()
