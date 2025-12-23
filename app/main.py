import os
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from .db import get_db
from .models import User, Job

app = FastAPI(title="Qryo Backend", version="0.2.0")


# ------------------------
# ROOT / HEALTH (GET + HEAD)
# ------------------------
@app.api_route("/", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}


# ------------------------
# SEED DEFAULT USER (DB boşsa)
# ------------------------
def seed_default_user_if_needed(db: Session) -> None:
    existing = db.query(User).first()
    if existing:
        return

    default_api_key = os.getenv("DEFAULT_API_KEY", "demo-key")
    default_email = os.getenv("DEFAULT_EMAIL", "demo@qryo.ai")

    user = User(
        email=default_email,
        api_key=default_api_key,
        jobs_today=0,
    )
    db.add(user)
    db.commit()


# ------------------------
# API KEY AUTH
# Header: X-API-Key: <key>
# ------------------------
def get_current_user(
    db: Session = Depends(get_db),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> User:
    # İlk kurulum kolaylığı: DB boşsa seed et
    seed_default_user_if_needed(db)

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header",
        )

    user = db.query(User).filter(User.api_key == x_api_key).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    return user


# ------------------------
# WHO AM I
# ------------------------
@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}


# ------------------------
# SUBMIT JOB (stabil çekirdek)
# ------------------------
@app.post("/submit-job")
def submit_job(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = Job(
        user_id=user.id,
        status="queued",
        estimated_cost=1,  # şimdilik sabit
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return {"job_id": job.id, "status": job.status}
