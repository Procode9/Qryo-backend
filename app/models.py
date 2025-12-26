# app/models.py
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


# -------------------------
# Time helpers
# -------------------------
def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# -------------------------
# USER
# -------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)

    tokens = relationship("UserToken", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")


# -------------------------
# USER TOKEN (AUTH CORE)
# -------------------------
class UserToken(Base):
    __tablename__ = "user_tokens"

    # random opaque token (Bearer)
    token = Column(String(128), primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # ✅ CRITICAL: revoke support
    revoked_at = Column(DateTime(timezone=True), nullable=True, index=True)

    user = relationship("User", back_populates="tokens")


# Helpful indexes (performans + güvenlik)
Index("ix_user_tokens_user_active", UserToken.user_id, UserToken.revoked_at)
Index("ix_user_tokens_expiry", UserToken.expires_at)


# -------------------------
# JOB (PHASE-1 CORE)
# -------------------------
class Job(Base):
    __tablename__ = "jobs"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    provider = Column(String(32), nullable=False)  # sim (phase-1)
    status = Column(String(32), nullable=False)    # queued | running | succeeded | failed

    payload_json = Column(Text, nullable=False)
    result_json = Column(Text, nullable=True)

    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now_utc)

    user = relationship("User", back_populates="jobs")


Index("ix_jobs_user_created", Job.user_id, Job.created_at.desc())