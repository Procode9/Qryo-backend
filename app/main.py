import json
from fastapi import FastAPI, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from .db import engine, SessionLocal
from .models import Job, Base
from .jobs import execute_job

Base.metadata.create_all(bind=engine)

app = FastAPI(title="QRYO API")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/submit-job")
def submit_job(background_tasks: BackgroundTasks, payload: dict = {}):
    db: Session = SessionLocal()
    try:
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

        # Run in background
        background_tasks.add_task(execute_job, job.id)

        return {
            "job_id": job.id,
            "status": job.status,
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
            "payload": json.loads(job.payload) if job.payload else {},
            "result": result_obj,
            "error": job.error,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }
    finally:
        db.close()
