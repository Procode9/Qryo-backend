import json
from datetime import datetime
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import Job
from .routing import route_job

def execute_job(job_id: str) -> None:
    """
    Runs in background. Updates job status and stores result/error.
    """
    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = "running"
        job.updated_at = datetime.utcnow()
        db.commit()

        payload = {}
        if job.payload:
            try:
                payload = json.loads(job.payload)
            except Exception:
                payload = {}

        provider, result = route_job(payload)

        job.provider = provider
        job.result = json.dumps(result)
        job.error = None
        job.status = "completed"
        job.updated_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        # Mark as failed
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error = str(e)
            job.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
