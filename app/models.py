# app/models.py
from __future__ import annotations

import datetime as dt
import uuid
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, String, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# -------------------------
# Job status enum (Risk-7 hardening)
# -------------------------
class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


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


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)

    provider = Column(String, nullable=False)

    # 🔒 Enum-safe ama DB String (Phase-1 migration-free)
    status = Column(String, nullable=False, default=JobStatus.queued.value)

    payload_json = Column(String, nullable=False)
    result_json = Column(String, nullable=False)
    error_message = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc)
