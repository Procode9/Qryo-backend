# app/deps.py
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from typing import Generator, Optional

from fastapi import Depends, Header

 HTTPException, status
from sqlalchemy.orm import Session

from fastapi import Request
from .rate_limit import rate_limit_check

from .db import SessionLocal
from .models import User, UserToken, now_utc

# =========================================================
# DATABASE DEPENDENCY
# =========================================================
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================================================
# TOKEN CORE (stdlib only – Phase-1)
# =========================================================
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me").encode("utf-8")
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", "86400"))  # 24h


def _sign(payload: str) -> str:
    return hmac.new(
        SECRET_KEY,
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_access_token(user_id: str, ttl_seconds: int = TOKEN_TTL_SECONDS) -> str:
    exp = int(time.time()) + ttl_seconds
    payload = f"{user_id}:{exp}"
    sig = _sign(payload)
    raw = f"{payload}:{sig}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def _decode_token(token: str) -> tuple[str, int]:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        user_id, exp_str, sig = raw.split(":", 2)
        payload = f"{user_id}:{exp_str}"
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )

    expected = _sign(payload)
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature",
        )

    try:
        exp = int(exp_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return user_id, exp


# =========================================================
# AUTH DEPENDENCY (GLOBAL, SAFE)
# =========================================================
def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
) -> User:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
 def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
):
    ...
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # 🔒 RATE LIMIT (user-based)
    rate_limit_check(request, user.id)

    return user          
        )

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization must be: Bearer <token>",
        )

    token_value = parts[1].strip()

    # --- decode token ---
    user_id, exp = _decode_token(token_value)

    # --- DB lookup ---
    token = (
        db.query(UserToken)
        .filter(UserToken.token == token_value)
        .first()
    )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not found",
        )

    # --- LAZY CLEANUP ---
    if token.revoked or token.expires_at < now_utc():
        db.delete(token)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired or revoked",
        )

    user = db.query(User).filter(User.id == token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
