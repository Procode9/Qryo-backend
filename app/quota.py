from datetime import date
from fastapi import HTTPException
from sqlalchemy.orm import Session
from .models import User


def check_and_update_daily_quota(
    db: Session,
    user: User,
    estimated_cost: float,
):
    today = date.today()

    # Reset if new day
    if user.last_reset_date != today:
        user.jobs_today = 0
        user.cost_today = 0.0
        user.last_reset_date = today

    # Check job count
    if user.jobs_today >= user.daily_job_limit:
        raise HTTPException(
            status_code=403,
            detail="Daily job limit exceeded"
        )

    # Check cost
    if (user.cost_today + estimated_cost) > user.daily_cost_limit:
        raise HTTPException(
            status_code=403,
            detail="Daily cost limit exceeded"
        )

    # Update counters (reserve quota)
    user.jobs_today += 1
    user.cost_today += estimated_cost

    db.commit()
