# app/models.py
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


# -------------------------------------------------
# User
# -------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=new_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    tokens = relationship(
        "UserToken",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# -------------------------------------------------
# UserToken  (Risk-6 FINAL)
# -------------------------------------------------
class UserToken(Base):
    __tablename__ = "user_tokens"

    # token value itself
    token = Column(String, primary_key=True)

    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # 🔒 Risk-6 fields
    revoked = Column(Boolean, default=False, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="tokens")

    # -------------------------
    # helpers
    # -------------------------
    @staticmethod
    def new_token() -> str:
        # cryptographically safe, URL-friendly
        return uuid.uuid4().hex


# -------------------------------------------------
# Indexes (performance + security)
# -------------------------------------------------
Index(
    "ix_user_tokens_active",
    UserToken.user_id,
    UserToken.revoked,
    UserToken.expires_at,
)
