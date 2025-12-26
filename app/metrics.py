# app/metrics.py

from sqlalchemy.orm import Session
from .models import Job


def count_user_jobs(db: Session, user_id: int) -> int:
    return db.query(Job).filter(Job.user_id == user_id).count()