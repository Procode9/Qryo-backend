from fastapi import FastAPI
from sqlalchemy.orm import Session
from .db import engine, SessionLocal
from .models import Job, Base
from .routing import route_job
import json

Base.metadata.create_all(bind=engine)

app = FastAPI(title="QRYO API")

@app.post("/submit-job")
def submit_job(payload: dict = {}):
    db: Session = SessionLocal()

    provider, result = route_job(payload)

    job = Job(
        provider=provider,
        status="completed",
        result=json.dumps(result)
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "job_id": job.id,
        "provider": provider,
        "result": result
    }

@app.get("/jobs")
def list_jobs():
    db: Session = SessionLocal()
    jobs = db.query(Job).all()

    return [
        {
            "id": j.id,
            "provider": j.provider,
            "status": j.status,
            "created_at": j.created_at
        }
        for j in jobs
    ]
