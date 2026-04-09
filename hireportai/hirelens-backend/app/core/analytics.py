"""PostHog analytics client.

Provides a single `track()` entry point so service code can fire product
events without knowing how PostHog is configured. When `POSTHOG_API_KEY`
is unset (local dev, CI, tests) the module becomes a silent no-op.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_client: Any | None = None
_initialized: bool = False


def _get_client() -> Any | None:
    """Lazily build a PostHog client from env vars.

    Cached on the module so we only construct it once. Returns None when
    analytics are disabled so callers can short-circuit.
    """
    global _client, _initialized
    if _initialized:
        return _client

    _initialized = True
    api_key = os.getenv("POSTHOG_API_KEY", "").strip()
    if not api_key:
        logger.info("PostHog disabled: POSTHOG_API_KEY not set")
        _client = None
        return None

    try:
        from posthog import Posthog
    except ImportError:
        logger.warning("posthog package not installed; analytics disabled")
        _client = None
        return None

    host = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com").strip()
    try:
        _client = Posthog(project_api_key=api_key, host=host)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to initialize PostHog client: %s", exc)
        _client = None
    return _client


def track(
    user_id: str | int | None,
    event: str,
    properties: dict[str, Any] | None = None,
) -> None:
    """Fire a PostHog event. Safe to call from anywhere; never raises.

    `user_id` may be None for anonymous events; we fall back to "anonymous".
    """
    client = _get_client()
    if client is None:
        return
    try:
        distinct_id = str(user_id) if user_id is not None else "anonymous"
        client.capture(
            distinct_id=distinct_id,
            event=event,
            properties=properties or {},
        )
    except Exception as exc:  # noqa: BLE001
        # Analytics must never break a request path.
        logger.warning("PostHog capture failed for event %s: %s", event, exc)
