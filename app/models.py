# app/models.py
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    tokens = relationship(
        "UserToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserToken(Base):
    __tablename__ = "user_tokens"

    token = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=now_utc)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="tokens")