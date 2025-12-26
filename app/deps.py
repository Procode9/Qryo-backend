# app/deps.py
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from typing import Generator, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session


# ---------------------------
# DB dependency
# ---------------------------
def get_db() -> Generator[Session, None, None]:
    """
    SQLAlchemy session dependency.
    Tries to import SessionLocal from app.db; if missing, raises a clear error.
    """
    try:
        from .db import SessionLocal  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "SessionLocal bulunamadı. app/db.py içinde SessionLocal tanımlı olmalı."
        ) from e

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------
# Minimal token system (stdlib only)
# ---------------------------
# Token format: base64("uid:exp:signaturehex")
# signature = HMAC_SHA256(SECRET_KEY, f"{uid}:{exp}")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me").encode("utf-8")
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", "86400"))  # 24h default


def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_access_token(user_id: int, ttl_seconds: int = TOKEN_TTL_SECONDS) -> str:
    exp = int(time.time()) + int(ttl_seconds)
    payload = f"{user_id}:{exp}"
    sig = _sign(payload)
    raw = f"{payload}:{sig}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def verify_access_token(token: str) -> int:
    """
    Returns user_id if valid, else raises HTTP 401.
    """
    try:
        raw = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        uid_str, exp_str, sig = raw.split(":", 2)
        payload = f"{uid_str}:{exp_str}"
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
        uid = int(uid_str)
        exp = int(exp_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    if time.time() > exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    return uid


# ---------------------------
# Auth dependency
# ---------------------------
def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
) -> object:
    """
    Reads: Authorization: Bearer <token>
    Token is verified with stdlib HMAC (no extra deps).
    Then loads User from DB (app.models.User).
    """
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
    user_id = verify_access_token(token)

    try:
        from .models import User  # type: ignore
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User model not found (app.models.User).",
        ) from e

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
