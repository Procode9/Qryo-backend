import json
from datetime import datetime
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import Job
from .routing import route_job


def execute_job(job_id: str) -> None:
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

        # optional: real cost could be filled later if provider returns it
        if isinstance(result, dict) and "cost_actual" in result:
            try:
                job.cost_actual = float(result["cost_actual"])
            except Exception:
                pass

        db.commit()

    except Exception as e:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error = str(e)
            job.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
