from __future__ import annotations

from typing import Generator, Optional, Set

from fastapi import Depends, Header, HTTPException, status, Request
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import User, UserToken, now_utc
from .config import settings


# =====================================================
# DB dependency
# =====================================================
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =====================================================
# Auth dependency
# =====================================================
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
# HELPER FUNCTIONS (Phase-1 FINAL)
# =====================================================

# -----------------------------------------------------
# 1. Token limit enforcement (Risk-6) ✅
# -----------------------------------------------------
def enforce_user_token_limit(db: Session, user: User) -> None:
    """
    Kullanıcının aktif (revoked=false & expire olmamış) token sayısını sınırlar.
    Limit aşılırsa EN ESKİ tokenlar otomatik revoke edilir.
    """

    max_tokens = settings.max_tokens_per_user
    if max_tokens <= 0:
        return

    active_tokens = (
        db.query(UserToken)
        .filter(
            UserToken.user_id == user.id,
            UserToken.revoked.is_(False),
            UserToken.expires_at > now_utc(),
        )
        .order_by(UserToken.created_at.asc())
        .all()
    )

    excess = len(active_tokens) - max_tokens
    if excess <= 0:
        return

    for tok in active_tokens[:excess]:
        tok.revoked = True

    db.commit()


# -----------------------------------------------------
# 2. Rate-limit bypass logic (Risk-4) ✅
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
    - Internal healthcheck
    """

    if not settings.rate_limit_enabled:
        return True

    path = request.url.path

    if path.startswith("/metrics"):
        return True

    if path in {"/healthz", "/"}:
        return True

    if user and settings.admin_emails:
        admins: Set[str] = {
            e.strip().lower()
            for e in settings.admin_emails.split(",")
            if e.strip()
        }
        if user.email.lower() in admins:
            return True

    return False


# -----------------------------------------------------
# 3. Metrics endpoint token guard (Risk-5) ✅
# -----------------------------------------------------
def require_metrics_token(
    authorization: Optional[str] = Header(default=None),
) -> None:
    """
    /metrics endpointi için token koruması.
    PROD ortamında zorunlu.
    """

    if settings.env != "production":
        return

    if not settings.metrics_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Metrics token not configured",
        )

    expected = f"Bearer {settings.metrics_token}"
    if not authorization or authorization.strip() != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing metrics token",
        )
