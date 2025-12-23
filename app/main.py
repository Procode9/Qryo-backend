from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from .db import Base, engine, get_db
from .models import Job
from .schemas import JobCreate, JobResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Qryo Backend", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok"}


# CREATE
@app.post("/submit-job", response_model=JobResponse)
def submit_job(_: JobCreate, db: Session = Depends(get_db)):
    job = Job(status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    return JobResponse(job_id=job.id, status=job.status)


# READ
@app.get("/jobs", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.id.desc()).all()
    return [JobResponse(job_id=j.id, status=j.status) for j in jobs]


# UPDATE → running
@app.post("/jobs/{job_id}/start")
def start_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job.status != "queued":
        raise HTTPException(400, "Job not in queued state")

    job.status = "running"
    db.commit()

    return {"job_id": job.id, "status": job.status}


# UPDATE → done
@app.post("/jobs/{job_id}/complete")
def complete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job.status != "running":
        raise HTTPException(400, "Job not running")

    job.status = "done"
    db.commit()

    return {"job_id": job.id, "status": job.status}


# UPDATE → failed
@app.post("/jobs/{job_id}/fail")
def fail_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    job.status = "failed"
    db.commit()

    return {"job_id": job.id, "status": job.status}