"""CLI entry — daily Pro digest cron.

Spec: docs/specs/phase-6/14-daily-digest-cron.md §6.6 + §12 D-2.

Invocation: ``python -m app.scripts.send_pro_digest``

Boots a fresh ``async_sessionmaker`` (mirrors
``app/scripts/seed_phase6.py`` pattern); does NOT share the FastAPI
request-scoped session. Prints ``SendSummary`` JSON to stdout for
ops dashboards (§12 D-12). Exit code 0 on success / non-zero on
fatal failure.
"""
from __future__ import annotations

import asyncio
import logging
import sys

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.services.pro_digest_service import send_pro_digest

logger = logging.getLogger("pro_digest")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def _run() -> int:
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as session:
            summary = await send_pro_digest(session)
            # Service flushes per-user `email_log` rows but does not
            # commit (test isolation contract); the CLI commits here so
            # rows persist past the tick.
            await session.commit()
            print(summary.model_dump_json())
        return 0
    finally:
        await engine.dispose()


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception:  # noqa: BLE001 — fatal wrapper for cron exit-code
        logger.exception("pro_digest cron tick failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
