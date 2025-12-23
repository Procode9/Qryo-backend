import uuid
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Text
from .db import Base

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    status: Mapped[str] = mapped_column(String, default="pending")  # pending|running|completed|failed
    provider: Mapped[str] = mapped_column(String, default="simulated")

    payload: Mapped[str | None] = mapped_column(Text)   # JSON string
    result: Mapped[str | None] = mapped_column(Text)    # JSON string
    error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
