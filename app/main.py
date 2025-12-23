import json
import secrets
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from sqlalchemy.orm import Session

from .db import engine, SessionLocal
from .models import Base, Job, User
from .jobs import execute_job

from .auth import require_api_key
from .credits import charge_credits, get_or_create_user, JOB_COST_CREDITS
from .estimation import estimate_cost
from .quota import check_and_update_daily_quota

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="QRYO API", version="0.5.0")


# --------------------
# Health
# --------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# --------------------
# Register
# --------------------
@app.post("/register")
def register():
    """
    Create a new user and return a random API key with initial credits.
    """
    db: Session = SessionLocal()
    try:
        api_key = secrets.token_urlsafe(24)

        user = User(api_key=api_key, credits=5)
        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "api_key": user.api_key,
            "credits": user.credits
        }
    finally:
        db.close()


# --------------------
# Me
# --------------------
@app.get("/me")
def me(api_key: str = Depends(require_api_key)):
    db: Session = SessionLocal()
    try:
        user = get_or_create_user(db, api_key)
        return {
            "api_key": user.api_key,
            "credits": user.credits
        }
    finally:
        db.close()


# --------------------
# Cost Estimate (SAFE)
# --------------------
@app.post("/estimate-job")
def estimate_job(
    payload: dict = {},
    api_key: str = Depends(require_api_key),
):
    """
    Estimate job cost WITHOUT executing it.
    No credits charged. No job created.
    """
    estimate = estimate_cost(payload)
    user = get_or_create_user(db, api_key)

check_and_update_daily_quota(
    db=db,
    user=user,
    estimated_cost=estimate["estimated_cost"],
)

    if not estimate["allowed"]:
        return {
            **estimate,
            "warning": "Estimated cost exceeds hard limit. Job would be blocked."
        }

    return estimate


# --------------------
# Submit Job (EXECUTION)
# --------------------
@app.post("/submit-job")
def submit_job(
    background_tasks: BackgroundTasks,
    payload: dict = {},
    api_key: str = Depends(require_api_key),
):
    db: Session = SessionLocal()
    try:
        # 1) Estimate & HARD LIMIT check
        estimate = estimate_cost(payload)
        if not estimate["allowed"]:
            raise HTTPException(
                status_code=403,
                detail="Estimated cost exceeds allowed limit"
            )

        # 2) Charge credits BEFORE execution
        remaining = charge_credits(db, api_key, JOB_COST_CREDITS)

        # 3) Create job (with cost estimate attached)
        job = Job(
            status="pending",
            provider=estimate["provider"],
            user_api_key=api_key,
            payload=json.dumps(payload),
            result=None,
            error=None,
            currency=estimate["currency"],
            cost_estimate=estimate["estimated_cost"],
            cost_actual=None,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # 4) Run asynchronously
        background_tasks.add_task(execute_job, job.id)

        return {
            "job_id": job.id,
            "status": job.status,
            "charged": JOB_COST_CREDITS,
            "credits_left": remaining,
            "estimated_cost": estimate["estimated_cost"],
            "currency": estimate["currency"],
        }

    finally:
        db.close()


# --------------------
# List Jobs (scoped)
# --------------------
@app.get("/jobs")
def list_jobs(api_key: str = Depends(require_api_key)):
    db: Session = SessionLocal()
    try:
        jobs = (
            db.query(Job)
            .filter(Job.user_api_key == api_key)
            .order_by(Job.created_at.desc())
            .all()
        )
        return [
            {
                "id": j.id,
                "provider": j.provider,
                "status": j.status,
                "cost_estimate": j.cost_estimate,
                "cost_actual": j.cost_actual,
                "created_at": j.created_at,
                "updated_at": j.updated_at,
            }
            for j in jobs
        ]
    finally:
        db.close()


# --------------------
# Get Job Detail (scoped)
# --------------------
@app.get("/jobs/{job_id}")
def get_job(job_id: str, api_key: str = Depends(require_api_key)):
    db: Session = SessionLocal()
    try:
        job = (
            db.query(Job)
            .filter(Job.id == job_id)
            .filter(Job.user_api_key == api_key)
            .first()
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        payload_obj = {}
        if job.payload:
            try:
                payload_obj = json.loads(job.payload)
            except Exception:
                payload_obj = {}

        result_obj = None
        if job.result:
            try:
                result_obj = json.loads(job.result)
            except Exception:
                result_obj = job.result

        return {
            "id": job.id,
            "provider": job.provider,
            "status": job.status,
            "payload": payload_obj,
            "result": result_obj,
            "error": job.error,
            "currency": job.currency,
            "cost_estimate": job.cost_estimate,
            "cost_actual": job.cost_actual,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }
    finally:
        db.close()
