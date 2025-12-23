from datetime import datetime, date

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from .db import Base


# ------------------------
# User
# ------------------------

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    api_key = Column(String, primary_key=True, index=True)

    credits = Column(Integer, default=0, nullable=False)

    # Daily quota / abuse protection
    daily_job_limit = Column(Integer, default=20, nullable=False)
    daily_cost_limit = Column(Float, default=10.0, nullable=False)

    jobs_today = Column(Integer, default=0, nullable=False)
    cost_today = Column(Float, default=0.0, nullable=False)
    last_reset_date = Column(Date, default=date.today, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    jobs = relationship("Job", back_populates="user")


# ------------------------
# Job
# ------------------------

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)

    user_api_key = Column(
        String,
        ForeignKey("users.api_key"),
        nullable=False,
        index=True
    )

    provider = Column(String, nullable=False)
    problem_type = Column(String, nullable=False)

    status = Column(String, default="queued", nullable=False)

    estimated_cost = Column(Float, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="jobs")
