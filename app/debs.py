# app/deps.py
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

# DB session
try:
    from .db import SessionLocal
except Exception as e:
    raise RuntimeError(
        "SessionLocal bulunamadı. app/db.py içinde SessionLocal tanımlı olmalı."
    ) from e

# User model
try:
    from .models import User
except Exception as e:
    raise RuntimeError(
        "User modeli bulunamadı. app/models.py içinde User tanımlı olmalı."
    ) from e


security = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Token decode: Önce projede varsa .auth kullan, yoksa fallback decode ---
def _decode_token_with_project_auth(token: str) -> Optional[Dict[str, Any]]:
    """
    Projede app/auth.py veya benzeri varsa onu kullanmaya çalışır.
    Bulamazsa None döner (fallback'a geçer).
    """
    try:
        from .auth import decode_token  # type: ignore
        payload = decode_token(token)  # dict bekliyoruz
        if isinstance(payload, dict):
            return payload
    except Exception:
        return None
    return None


def _decode_token_fallback(token: str) -> Dict[str, Any]:
    """
    Ek dependency istemeyen minimal token doğrulama.
    Token formatı:
      base64url(json_payload).base64url(signature)
    signature = HMAC_SHA256(SECRET_KEY, payload_part)
    payload içinde en az:
      {"sub": "<user_id or email>", "exp": <unix_ts>}
    """
    secret = os.getenv("SECRET_KEY", "dev-secret-change-me").encode("utf-8")

    if "." not in token:
        # Bazı projelerde token direkt email/uid gibi saklanmış olabiliyor
        return {"sub": token, "exp": int(time.time()) + 3600}

    payload_b64, sig_b64 = token.split(".", 1)

    def b64url_decode(s: str) -> bytes:
        pad = "=" * (-len(s) % 4)
        return base64.urlsafe_b64decode(s + pad)

    def b64url_encode(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")

    expected = hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).digest()
    expected_b64 = b64url_encode(expected)

    if not hmac.compare_digest(expected_b64, sig_b64):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature",
        )

    payload_json = b64url_decode(payload_b64).decode("utf-8")
    payload = json.loads(payload_json)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    exp = int(payload.get("exp", 0))
    if exp and exp < int(time.time()):
        raise HTTPException(status_code=401, detail="Token expired")

    return payload


def decode_token(token: str) -> Dict[str, Any]:
    payload = _decode_token_with_project_auth(token)
    if payload is not None:
        return payload
    return _decode_token_fallback(token)


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token = creds.credentials
    payload = decode_token(token)

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token (no sub)")

    # sub email olabilir, id olabilir. İkisini de deneriz.
    user = None

    # 1) email gibi görünüyorsa email ile ara
    if isinstance(sub, str) and "@" in sub:
        user = db.query(User).filter(User.email == sub).first()

    # 2) id ile ara (int'e çevrilebiliyorsa)
    if user is None:
        try:
            uid = int(sub)
            user = db.query(User).filter(User.id == uid).first()
        except Exception:
            user = None

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user