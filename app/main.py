from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Job
from .schemas import JobCreate, JobResponse

# DB tablolarını oluştur
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Qryo Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "qryo-backend"}


@app.post("/submit-job", response_model=JobResponse)
def submit_job(payload: JobCreate, db: Session = Depends(get_db)):
    job = Job(status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    return JobResponse(
        job_id=job.id,
        status=job.status,
        estimated_cost=None,
    )
