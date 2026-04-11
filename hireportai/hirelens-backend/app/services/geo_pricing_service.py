"""Geo-based pricing — show USD by default, INR for India.

Uses the free ip-api.com service for geolocation (45 req/min, no key).
Results are cached in Redis for 24 hours to avoid hitting the rate limit
and to keep pricing stable within a session.
"""
import json
import logging
from typing import Any, Dict

import httpx
import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_GEO_CACHE_TTL = 86_400  # 24 hours

# Pricing definitions
_PRICING: Dict[str, Dict[str, Any]] = {
    "inr": {
        "currency": "inr",
        "price": 999,
        "price_display": "\u20b9999/mo",
    },
    "usd": {
        "currency": "usd",
        "price": 49,
        "price_display": "$49/mo",
    },
}


def _get_redis() -> redis.Redis | None:
    """Return a Redis client, or None if unavailable."""
    settings = get_settings()
    if not settings.redis_url:
        return None
    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        logger.debug("Redis unavailable — geo pricing cache disabled")
        return None


def _lookup_country(ip: str) -> str | None:
    """Call ip-api.com to resolve an IP to a country code."""
    try:
        resp = httpx.get(
            f"http://ip-api.com/json/{ip}?fields=status,countryCode",
            timeout=3.0,
        )
        data = resp.json()
        if data.get("status") == "success":
            return data.get("countryCode")
    except Exception:
        logger.warning("ip-api.com lookup failed for %s", ip)
    return None


def get_pricing(ip_address: str) -> Dict[str, Any]:
    """Return geo-aware pricing for the given client IP.

    Returns a dict with: currency, price, price_display, stripe_price_id.
    Defaults to USD if geolocation fails or Redis is unavailable.
    """
    settings = get_settings()
    cache_key = f"geo_pricing:{ip_address}"

    # Try cache first
    r = _get_redis()
    if r is not None:
        try:
            cached = r.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    # Resolve country
    country = _lookup_country(ip_address)
    if country == "IN":
        result = {
            **_PRICING["inr"],
            "stripe_price_id": settings.stripe_pro_price_id_inr,
        }
    else:
        result = {
            **_PRICING["usd"],
            "stripe_price_id": settings.stripe_pro_price_id,
        }

    # Cache result
    if r is not None:
        try:
            r.setex(cache_key, _GEO_CACHE_TTL, json.dumps(result))
        except Exception:
            pass

    return result
