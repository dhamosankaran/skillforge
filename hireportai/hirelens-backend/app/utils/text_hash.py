"""Stable text-hash helpers for content-addressed caching keys.

Currently consumed by interview-question storage (spec #49). The scan-tracker
Locked Decision also specs this normalization for `(user_id, jd_hash)` dedup
on the tracker_applications_v2 path; tracker can adopt this module later.
"""
import hashlib


def _normalize_jd(text: str) -> str:
    # Collapse any whitespace run (incl. \n, \t, multi-space) to a single space,
    # strip, casefold. Stable across copy/paste whitespace drift and case noise.
    return " ".join(text.split()).strip().casefold()


def hash_jd(text: str) -> str:
    """Return the SHA256 hex digest of the normalized job description.

    Same JD with different whitespace or case produces the same hash.
    """
    return hashlib.sha256(_normalize_jd(text).encode("utf-8")).hexdigest()
