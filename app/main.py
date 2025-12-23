from fastapi import FastAPI, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4

from .db import get_db
from .models import User, Job
from .quota import check_and_update_daily_quota
from .schemas import JobSubmitRequest
from .cost import estimate_cost

app = FastAPI(
    title="QRYO API",
    version="0.5.0"
)


# ------------------------
# Helpers
# ------------------------

def get_current_user(
    db: Session,
    x_api_key: str = Header(..., alias="X-API-Key")
) -> User:
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user


# ------------------------
# Health
# ------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# ------------------------
# Register
# ------------------------

@app.post("/register")
def register(db: Session = Depends(get_db)):
    api_key = str(uuid4())

    user = User(
        api_key=api_key,
        credits=20
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "api_key": api_key,
        "credits": user.credits
    }


# ------------------------
# Me
# ------------------------

@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "api_key": user.api_key,
        "credits": user.credits,
        "jobs_today": user.jobs_today,
        "cost_today": user.cost_today,
        "daily_job_limit": user.daily_job_limit,
        "daily_cost_limit": user.daily_cost_limit
    }


# ------------------------
# Estimate Job
# ------------------------

@app.post("/estimate-job")
def estimate_job(payload: JobSubmitRequest):
    return estimate_cost(payload)


# ------------------------
# Submit Job
# ------------------------

@app.post("/submit-job")
def submit_job(
    payload: JobSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 1. Estimate cost
    estimate = estimate_cost(payload)

    if not estimate["allowed"]:
        raise HTTPException(
            status_code=400,
            detail="Job not allowed"
        )

    estimated_cost = estimate["estimated_cost"]

    # 2. Daily quota protection (STEP 6)
    check_and_update_daily_quota(
        db=db,
        user=user,
        estimated_cost=estimated_cost
    )

    # 3. Credit check
    if user.credits < estimated_cost:
        raise HTTPException(
            status_code=402,
            detail="Not enough credits"
        )

    # 4. Deduct credits
    user.credits -= estimated_cost

    # 5. Create job
    job = Job(
        user_api_key=user.api_key,
        provider=payload.provider,
        problem_type=payload.problem_type,
        status="queued",
        estimated_cost=estimated_cost
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "job_id": job.id,
        "status": job.status,
        "estimated_cost": estimated_cost
    }


# ------------------------
# Jobs
# ------------------------

@app.get("/jobs")
def list_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    jobs = db.query(Job).filter(
        Job.user_api_key == user.api_key
    ).all()

    return jobs


@app.get("/jobs/{job_id}")
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_api_key == user.api_key
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job
