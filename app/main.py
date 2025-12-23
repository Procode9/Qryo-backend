from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .models import User, Job

app = FastAPI(title="Qryo Backend", version="0.1.0")


# ------------------------
# HEALTH CHECK
# ------------------------
@app.get("/")
def health():
    return {"status": "ok"}


# ------------------------
# DUMMY AUTH (API KEY YERİNE GEÇİCİ)
# ------------------------
def get_current_user(db: Session = Depends(get_db)) -> User:
    user = db.query(User).first()
    if not user:
        user = User(
            email="demo@qryo.ai",
            api_key="demo-key",
            jobs_today=0
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ------------------------
# SUBMIT JOB (SADE – STABİL)
# ------------------------
@app.post("/submit-job")
def submit_job(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    job = Job(
        user_id=user.id,
        status="queued",
        estimated_cost=1  # SABİT, GEÇİCİ
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "job_id": job.id,
        "status": job.status
    }
