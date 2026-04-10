"""Thin wrapper around the Resend API for transactional email.

Provides a single ``send_email`` entry point with retry logic for
transient errors (429 / 5xx).  When ``RESEND_API_KEY`` is unset the
function logs a warning and returns ``None`` so dev / CI environments
never hit the network.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 1  # seconds


class EmailSendError(Exception):
    """Raised on permanent Resend failures (4xx other than 429)."""


async def send_email(
    to: str,
    subject: str,
    html_body: str,
) -> str | None:
    """Send a single transactional email via Resend.

    Returns the Resend message ID on success, or ``None`` when the API
    key is missing (dev/CI).  Retries up to 3 times on 429/5xx with
    exponential backoff.
    """
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        logger.warning("RESEND_API_KEY not set — skipping email to %s", to)
        return None

    from_address = os.getenv("RESEND_FROM_ADDRESS", "reminders@skillforge.app")

    import resend

    resend.api_key = api_key

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            email: Any = resend.Emails.send(
                {
                    "from": from_address,
                    "to": [to],
                    "subject": subject,
                    "html": html_body,
                }
            )
            return email.get("id") if isinstance(email, dict) else getattr(email, "id", None)
        except Exception as exc:
            last_error = exc
            err_str = str(exc).lower()
            is_transient = "429" in err_str or "5" in err_str[:1]
            if not is_transient:
                raise EmailSendError(str(exc)) from exc
            wait = _BACKOFF_BASE * (2 ** attempt)
            logger.warning(
                "Resend transient error (attempt %d/%d), retrying in %ds: %s",
                attempt + 1,
                _MAX_RETRIES,
                wait,
                exc,
            )
            await asyncio.sleep(wait)

    raise EmailSendError(f"All {_MAX_RETRIES} retries exhausted: {last_error}")
