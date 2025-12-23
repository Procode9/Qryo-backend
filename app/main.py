import json
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from sqlalchemy.orm import Session

from .db import engine, SessionLocal
from .models import Base, Job
from .jobs import execute_job

# Credit/Auth helpers (bu dosyalar repoda olmalı)
from .auth import require_api_key
from .credits import charge_credits, get_or_create_user, JOB_COST_CREDITS

# Create tables at startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="QRYO API", version="0.2.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/me")
def me(api_key: str = Depends(require_api_key)):
    db: Session = SessionLocal()
    try:
        u = get_or_create_user(db, api_key)
        return {"api_key": u.api_key, "credits": u.credits}
    finally:
        db.close()


@app.post("/submit-job")
def submit_job(
    background_tasks: BackgroundTasks,
    payload: dict = {},
    api_key: str = Depends(require_api_key),
):
    db: Session = SessionLocal()
    try:
        # 1) Charge credits BEFORE running the job (no free runs)
        remaining = charge_credits(db, api_key, JOB_COST_CREDITS)

        # 2) Create job as pending
        job = Job(
            status="pending",
            provider="simulated",
            payload=json.dumps(payload),
            result=None,
            error=None,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # 3) Run in background
        background_tasks.add_task(execute_job, job.id)

        return {
            "job_id": job.id,
            "status": job.status,
            "charged": JOB_COST_CREDITS,
            "credits_left": remaining,
        }
    finally:
        db.close()


@app.get("/jobs")
def list_jobs():
    db: Session = SessionLocal()
    try:
        jobs = db.query(Job).order_by(Job.created_at.desc()).all()
        return [
            {
                "id": j.id,
                "provider": j.provider,
                "status": j.status,
                "created_at": j.created_at,
                "updated_at": j.updated_at,
            }
            for j in jobs
        ]
    finally:
        db.close()


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
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
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }
    finally:
        db.close()
