# app/rate_limit.py
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request, status

from .config import settings

# key -> timestamps
_BUCKETS: Dict[str, Deque[float]] = defaultdict(deque)

WINDOW_SECONDS = 60


def _now() -> float:
    return time.time()


def _cleanup(bucket: Deque[float]) -> None:
    cutoff = _now() - WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.popleft()


def rate_limit_check(request: Request, user_id: int | None) -> None:
    """
    Raises HTTP 429 if rate limit exceeded.
    """

    if not settings.rate_limit_enabled:
        return

    # user-based > ip-based
    if user_id is not None:
        key = f"user:{user_id}"
    else:
        ip = request.client.host if request.client else "unknown"
        key = f"ip:{ip}"

    bucket = _BUCKETS[key]
    _cleanup(bucket)

    if len(bucket) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down.",
        )

    bucket.append(_now())
