# app/deps.py
from __future__ import annotations

import time
from collections import deque
from typing import Deque, Dict, Generator, Optional, Tuple

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .models import User, UserToken, now_utc


# ---------------------------
# DB dependency
# ---------------------------
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------
# In-memory rate limiter (Phase-1)
# NOTE: Tek instance için yeterli. Multi-instance olursa Redis'e taşırsın (Phase-2).
# ---------------------------
# key: (user_id, "minute") -> timestamps
_RL_BUCKETS: Dict[int, Deque[float]] = {}
_RL_WINDOW_SECONDS = 60.0


def rate_limit_user(user_id: int) -> None:
    now = time.time()
    q = _RL_BUCKETS.get(user_id)
    if q is None:
        q = deque()
        _RL_BUCKETS[user_id] = q

    # eski timestamp'leri çıkar
    while q and (now - q[0]) > _RL_WINDOW_SECONDS:
        q.popleft()

    if len(q) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

    q.append(now)


# ---------------------------
# Auth dependency (DB-backed token)
# ---------------------------
def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization must be: Bearer <token>",
        )
    token = parts[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty token",
        )
    return token


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
) -> User:
    token = _extract_bearer(authorization)

    tok = (
        db.query(UserToken)
        .filter(UserToken.token == token)
        .first()
    )
    if not tok:
        raise HTTPException(status_code=401, detail="Invalid token")

    if tok.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Token revoked")

    if tok.expires_at <= now_utc():
        raise HTTPException(status_code=401, detail="Token expired")

    user = db.query(User).filter(User.id == tok.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # ✅ user bazlı rate limit (auth endpointler hariç)
    # /auth/* hariç her yerde uygula
    if not request.url.path.startswith("/auth/"):
        rate_limit_user(user.id)

    return user