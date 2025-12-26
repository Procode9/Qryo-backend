# app/ratelimit.py
import time
from fastapi import HTTPException

_HITS: dict[str, list[int]] = {}


def rate_limit(key: str, limit: int = 10, window: int = 60) -> None:
    """
    Simple in-memory rate limit.
    """
    now = int(time.time())
    hits = _HITS.get(key, [])
    hits = [t for t in hits if now - t < window]

    if len(hits) >= limit:
        raise HTTPException(status_code=429, detail="Too many requests")

    hits.append(now)
    _HITS[key] = hits