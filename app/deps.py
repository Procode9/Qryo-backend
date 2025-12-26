from __future__ import annotations

from typing import Generator, Optional

from fastapi import Depends, Header, HTTPException, status, Request
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import User, UserToken, now_utc
from .config import settings


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
# Auth dependency
# ---------------------------
def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
) -> User:
    """
    Authorization: Bearer <token>
    Token DB'de UserToken olarak saklanır.
    revoked = false
    expires_at > now
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

    token_value = parts[1].strip()
    if not token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty token",
        )

    tok = (
        db.query(UserToken)
        .filter(UserToken.token == token_value)
        .first()
    )

    if not tok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    if tok.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked",
        )

    if tok.expires_at and now_utc() >= tok.expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    user = db.query(User).filter(User.id == tok.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


# =====================================================
# HELPER FUNCTIONS (Phase-1 completion)
# =====================================================

# -----------------------------------------------------
# 1. Token limit enforcement (Risk-6)
# -----------------------------------------------------
def enforce_user_token_limit(db: Session, user: User) -> None:
    """
    Kullanıcının aktif (revoked=false, expire olmamış) token sayısını kontrol eder.
    Limit aşılmışsa yeni token oluşturulmasına izin vermez.
    """

    active_tokens_count = (
        db.query(UserToken)
        .filter(
            UserToken.user_id == user.id,
            UserToken.revoked.is_(False),
            UserToken.expires_at > now_utc(),
        )
        .count()
    )

    if active_tokens_count >= settings.max_tokens_per_user:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum active token limit reached",
        )


# -----------------------------------------------------
# 2. Rate-limit bypass logic (Risk-4 hardening)
# -----------------------------------------------------
def should_bypass_rate_limit(
    request: Request,
    user: Optional[User] = None,
) -> bool:
    """
    Aşağıdaki durumlarda rate-limit bypass edilir:
    - Rate limit kapalıysa
    - Metrics endpoint
    - Admin email listesinde olan kullanıcı
    - Internal Render healthcheck
    """

    if not settings.rate_limit_enabled:
        return True

    path = request.url.path

    # Metrics endpoint her zaman bypass
    if path.startswith("/metrics"):
        return True

    # Healthcheck / internal probe
    if path in {"/health", "/"}:
        return True

    # Admin kullanıcılar
    if user and settings.admin_emails:
        admins = {e.strip().lower() for e in settings.admin_emails.split(",")}
        if user.email.lower() in admins:
            return True

    return False


# -----------------------------------------------------
# 3. Metrics endpoint token guard (Risk-5)
# -----------------------------------------------------
def require_metrics_token(
    x_metrics_token: Optional[str] = Header(default=None),
) -> None:
    """
    /metrics endpointi için özel token koruması.
    PROD ortamında zorunlu.
    """

    # Dev ortamında serbest
    if settings.env != "production":
        return

    if not settings.metrics_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Metrics token not configured",
        )

    if not x_metrics_token or x_metrics_token != settings.metrics_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing metrics token",
    )
