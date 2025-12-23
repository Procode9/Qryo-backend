from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import time

from .db import Base, engine, get_db
from .models import Job
from .schemas import JobCreate, JobResponse
from .cost import estimate_cost

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Qryo Backend", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "worker": "simulated"}


# ------------------------
# BACKGROUND WORKER
# ------------------------
def run_job(job_id: int):
    from .db import SessionLocal

    db = SessionLocal()
    job = db.query(Job).get(job_id)

    if not job:
        db.close()
        return

    job.status = "running"
    db.commit()

    time.sleep(3)  # simulate work

    job.status = "done"
    db.commit()
    db.close()


# ------------------------
# CREATE JOB
# ------------------------
@app.post("/submit-job", response_model=JobResponse)
def submit_job(
    _: JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = Job(status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_job, job.id)

    return JobResponse(
        job_id=job.id,
        status=job.status,
        estimated_cost=estimate_cost(),
    )


# ------------------------
# LIST JOBS
# ------------------------
@app.get("/jobs", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.id.desc()).all()

    return [
        JobResponse(
            job_id=j.id,
            status=j.status,
            estimated_cost=estimate_cost(),
        )
        for j in jobs
    ]