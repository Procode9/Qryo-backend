# app/job_engine.py
from __future__ import annotations

import json
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import Job, now_utc
from .providers import PROVIDERS


async def execute_job(job_id: str):
    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        provider = PROVIDERS.get(job.provider)
        if not provider:
            raise RuntimeError(f"Provider not found: {job.provider}")

        job.status = "running"
        job.updated_at = now_utc()
        db.commit()

        payload = json.loads(job.payload_json or "{}")
        result = await provider.run(payload)

        job.status = "succeeded"
        job.result_json = json.dumps(result, ensure_ascii=False)
        job.updated_at = now_utc()
        db.commit()

    except Exception as e:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.updated_at = now_utc()
            db.commit()
    finally:
        db.close()