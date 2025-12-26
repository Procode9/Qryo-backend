# app/job_engine.py
from __future__ import annotations

import asyncio
import json
import time

from sqlalchemy.orm import Session

from .constants import JobStatus
from .db import SessionLocal
from .models import Job, now_utc

MAX_RETRIES = 2
TIMEOUT_SECONDS = 5


async def execute_job(job_id: str):
    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = JobStatus.RUNNING
        job.updated_at = now_utc()
        db.commit()

        retries = 0
        start = time.time()

        while retries <= MAX_RETRIES:
            try:
                await asyncio.sleep(2)

                if time.time() - start > TIMEOUT_SECONDS:
                    raise TimeoutError("Job execution timeout")

                payload = json.loads(job.payload_json or "{}")

                job.status = JobStatus.SUCCEEDED
                job.result_json = json.dumps(
                    {
                        "provider": job.provider,
                        "echo": payload,
                        "message": "execution completed",
                        "retries": retries,
                    },
                    ensure_ascii=False,
                )
                job.updated_at = now_utc()
                db.commit()
                return

            except Exception as e:
                retries += 1
                if retries > MAX_RETRIES:
                    job.status = JobStatus.FAILED
                    job.error_message = str(e)
                    job.updated_at = now_utc()
                    db.commit()
                    return

    finally:
        db.close()