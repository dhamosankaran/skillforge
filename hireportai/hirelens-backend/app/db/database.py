"""Async SQLite database setup for the job application tracker."""
import os

import aiosqlite

DB_PATH = "data/hirelens.db"


async def init_db() -> None:
    """Initialize the SQLite database and create tables if they don't exist."""
    os.makedirs("data", exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tracker_applications (
                id TEXT PRIMARY KEY,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                date_applied TEXT NOT NULL,
                ats_score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Applied',
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()
