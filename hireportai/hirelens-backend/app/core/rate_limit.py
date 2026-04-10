"""Rate limiting via slowapi (Spec #25).

Provides a shared ``limiter`` instance used by route decorators and the
SlowAPIMiddleware attached in ``app.main``.

Default: 100 requests/minute per IP.
Overrides are applied per-route via ``@limiter.limit()``.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
)
