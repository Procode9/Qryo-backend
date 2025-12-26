# app/deps.py
from __future__ import annotations

from typing import Generator, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import User, UserToken, now_utc


# ---------------------------
# DB session dependency
# ---------------------------
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------
# Auth dependency (DB token)
# ---------------------------
def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """
    Authorization: Bearer <token>

    Token DB'de aranır:
    - var mı
    - expire olmuş mu
    - kullanıcı var mı
    """

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization must be: Bearer <token>",
        )

    token_row = (
        db.query(UserToken)
        .filter(UserToken.token == token)
        .first()
    )

    if not token_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    if token_row.expires_at and token_row.expires_at < now_utc():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    user = db.query(User).filter(User.id == token_row.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user