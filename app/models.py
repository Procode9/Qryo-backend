import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Text, Integer
from .db import Base

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # pending|running|completed|failed
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    provider: Mapped[str] = mapped_column(String, default="simulated", nullable=False)
    user_api_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    user_api_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    payload: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class User(Base):
    __tablename__ = "users"

    # We'll use api_key as the primary key for MVP
    api_key: Mapped[str] = mapped_column(String, primary_key=True)

    credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
