from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from .db import Base, engine, get_db
from .models import Job
from .schemas import JobCreate, JobResponse
from .cost import estimate_cost

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Qryo Backend", version="0.3.0")

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


@app.post("/submit-job", response_model=JobResponse)
def submit_job(_: JobCreate, db: Session = Depends(get_db)):
    job = Job(status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    return JobResponse(
        job_id=job.id,
        status=job.status,
        estimated_cost=estimate_cost()
    )


@app.get("/jobs", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.id.desc()).all()
    return [
        JobResponse(
            job_id=j.id,
            status=j.status,
            estimated_cost=estimate_cost()
        )
        for j in jobs
    ]