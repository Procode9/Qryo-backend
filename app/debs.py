# app/deps.py
from __future__ import annotations

import datetime as dt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import User, UserToken


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return auth.removeprefix("Bearer ").strip()


def get_current_user(
    token: str = Depends(get_bearer_token),
    db: Session = Depends(get_db),
) -> User:
    tok = db.query(UserToken).filter(UserToken.token == token).first()
    if not tok:
        raise HTTPException(status_code=401, detail="Invalid token")
    if tok.expires_at <= dt.datetime.now(dt.timezone.utc):
        raise HTTPException(status_code=401, detail="Token expired")

    user = db.query(User).filter(User.id == tok.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user