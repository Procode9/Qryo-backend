from typing import Generator, Optional
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
import datetime as dt

from app.db import SessionLocal
from app.models import User, UserToken


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    now = dt.datetime.now(dt.timezone.utc)
    token_row = (
        db.query(UserToken)
        .filter(UserToken.token == token, UserToken.expires_at > now)
        .first()
    )

    if not token_row:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return token_row.user