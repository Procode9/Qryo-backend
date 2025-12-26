# app/rate_limit.py
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request, status

# -----------------------------------
# CONFIG (Phase-1 defaults)
# -----------------------------------
WINDOW_SECONDS = 60

LIMITS = {
    "auth": 10,     # /auth/login, /auth/register
    "jobs": 30,     # /jobs submit
    "global": 120,  # everything else
}

# -----------------------------------
# In-memory store
# key = (ip, bucket)
# -----------------------------------
_store: Dict[str, Deque[float]] = defaultdict(deque)


def _now() -> float:
    return time.time()


def _prune(q: Deque[float], now: float):
    while q and q[0] <= now - WINDOW_SECONDS:
        q.popleft()


def rate_limit(request: Request, bucket: str):
    ip = request.client.host if request.client else "unknown"
    key = f"{ip}:{bucket}"
    now = _now()

    q = _store[key]
    _prune(q, now)

    limit = LIMITS.get(bucket, LIMITS["global"])
    if len(q) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({bucket})",
        )

    q.append(now)