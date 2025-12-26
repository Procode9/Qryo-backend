# app/security.py
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import os
import secrets

PBKDF2_ITERS = 210_000
SALT_BYTES = 16
DKLEN = 32


def hash_password(password: str) -> str:
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    salt = os.urandom(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERS, dklen=DKLEN)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERS,
        base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="),
        base64.urlsafe_b64encode(dk).decode("ascii").rstrip("="),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_b64, hash_b64 = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        iters = int(iters_s)

        def _pad(s: str) -> str:
            return s + "=" * (-len(s) % 4)

        salt = base64.urlsafe_b64decode(_pad(salt_b64))
        expected = base64.urlsafe_b64decode(_pad(hash_b64))

        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters, dklen=len(expected))
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def expires_at(days: int) -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=days)