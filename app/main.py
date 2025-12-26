# app/main.py
from __future__ import annotations

import datetime as dt
import json

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal, engine
from .deps import get_current_user, get_db
from .job_engine import execute_job
from .models import Base, Job, User, UserToken, now_utc
from .schemas import (
    AuthResponse,
    JobResponse,
    JobSubmitRequest,
    LoginRequest,
    MeResponse,
    RegisterRequest,
)
from .security import expires_at, hash_password, new_token, verify_password

# -------------------------------------------------
# APP
# -------------------------------------------------
app = FastAPI(title=settings.app_name)

# -------------------------------------------------
# CORS
# -------------------------------------------------
origins = (
    [o.strip() for o in settings.cors_origins.split(",")]
    if settings.cors_origins
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# STARTUP
# -------------------------------------------------
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# -------------------------------------------------
# HEALTH
# -------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": dt.datetime.now(dt.timezone.utc).isoformat()}


@app.get("/")
def root():
    return {"name": settings.app_name, "docs": "/docs"}

# =================================================
# AUTH
# =================================================
@app.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    pw_hash = hash_password(payload.password)

    user = User(email=email, password_hash=pw_hash)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = new_token()
    db.add(
        UserToken(
            token=token,
            user_id=user.id,
            expires_at=expires_at(settings.token_ttl_days),
        )
    )
    db.commit()

    return AuthResponse(token=token)


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = new_token()
    db.add(
        UserToken(
            token=token,
            user_id=user.id,
            expires_at=expires_at(settings.token_ttl_days),
        )
    )
    db.commit()

    return AuthResponse(token=token)


@app.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(id=user.id, email=user.email)

# =================================================
# JOBS (Phase-1 Core)
# =================================================
def _job_to_response(job: Job) -> JobResponse:
    try:
        payload = json.loads(job.payload_json or "{}")
    except Exception:
        payload = {}

    try:
        result = json.loads(job.result_json or "{}")
    except Exception:
        result = {}

    return JobResponse(
        id=job.id,
        provider=job.provider,
        status=job.status,  # type: ignore
        payload=payload,
        result=result,
        error_message=job.error_message,
    )


@app.post("/jobs", response_model=JobResponse)
def submit_job(
    req: JobSubmitRequest,
    bg: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    provider = (req.provider or "sim").strip().lower()

    # Phase-1 only
    if provider not in {"sim"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported provider in phase-1 (use 'sim')",
        )

    job = Job(
        user_id=user.id,
        provider=provider,
        status="queued",
        payload_json=json.dumps(req.payload or {}, ensure_ascii=False),
        result_json="{}",
        created_at=now_utc(),
        updated_at=now_utc(),
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # 🔥 NEW: provider-agnostic job engine
    bg.add_task(execute_job, job.id)

    return _job_to_response(job)


@app.get("/jobs", response_model=list[JobResponse])
def list_jobs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    jobs = (
        db.query(Job)
        .filter(Job.user_id == user.id)
        .order_by(Job.created_at.desc())
        .limit(100)
        .all()
    )
    return [_job_to_response(j) for j in jobs]


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = (
        db.query(Job)
        .filter(Job.id == job_id, Job.user_id == user.id)
        .first()
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return _job_to_response(job)