# app/security.py
from __future__ import annotations

import datetime as dt
import hashlib
import secrets

from .models import now_utc


def hash_password(password: str) -> str:
    pwd = password.strip()
    if len(pwd) < 8:
        raise ValueError("Password must be at least 8 characters")

    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"), salt, 200_000)
    return f"pbkdf2_sha256$200000${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_hex, dk_hex = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(dk_hex)
        got = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
        return secrets.compare_digest(got, expected)
    except Exception:
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def expires_at(ttl_days: int) -> dt.datetime:
    return now_utc() + dt.timedelta(days=int(ttl_days))
