# app/main.py
from __future__ import annotations

import asyncio
import datetime as dt
import json
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal, engine
from .deps import get_current_user, get_db
from .models import Base, Job, User, UserToken, now_utc
from .schemas import (
    AuthResponse,
    JobResponse,
    JobSubmitRequest,
    JobListResponse,
    LoginRequest,
    MeResponse,
    RegisterRequest,
)
from .security import expires_at, hash_password, new_token, verify_password

app = FastAPI(title=settings.app_name)


# -------------------------
# CORS
# -------------------------
origins = [o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# STARTUP
# -------------------------
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": dt.datetime.now(dt.timezone.utc).isoformat()}


@app.get("/")
def root():
    return {"name": settings.app_name, "docs": "/docs"}


# =========================
# AUTH
# =========================
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

    tok = new_token()
    db.add(
        UserToken(
            token=tok,
            user_id=user.id,
            expires_at=expires_at(settings.token_ttl_days),
        )
    )
    db.commit()

    return AuthResponse(token=tok)


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    tok = new_token()
    db.add(
        UserToken(
            token=tok,
            user_id=user.id,
            expires_at=expires_at(settings.token_ttl_days),
        )
    )
    db.commit()

    return AuthResponse(token=tok)


@app.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(id=user.id, email=user.email)


# =========================
# JOB CORE (PHASE-1)
# =========================
def _job_to_response(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        provider=job.provider,
        status=job.status,
        payload=json.loads(job.payload_json or "{}"),
        result=json.loads(job.result_json or "{}"),
        error_message=job.error_message,
    )


async def _simulate_job(job_id: str):
    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = "running"
        job.updated_at = now_utc()
        db.commit()

        await asyncio.sleep(2)

        job.status = "succeeded"
        job.result_json = json.dumps(
            {
                "message": "simulated quantum execution completed",
                "provider": job.provider,
            }
        )
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


@app.post("/jobs", response_model=JobResponse)
def submit_job(
    req: JobSubmitRequest,
    bg: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    provider = (req.provider or "sim").lower()
    if provider != "sim":
        raise HTTPException(status_code=400, detail="Only 'sim' supported in phase-1")

    job = Job(
        user_id=user.id,
        provider=provider,
        status="queued",
        payload_json=json.dumps(req.payload or {}),
        result_json="{}",
        created_at=now_utc(),
        updated_at=now_utc(),
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    bg.add_task(_simulate_job, job.id)
    return _job_to_response(job)


# =========================
# PHASE-1.2
# JOB LIST (PAGINATION + FILTER)
# =========================
@app.get("/jobs", response_model=JobListResponse)
def list_jobs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
):
    q = db.query(Job).filter(Job.user_id == user.id)

    if status:
        q = q.filter(Job.status == status)
    if provider:
        q = q.filter(Job.provider == provider)

    if cursor:
        q = q.filter(Job.id < cursor)

    q = q.order_by(Job.id.desc()).limit(limit + 1)

    rows = q.all()
    has_next = len(rows) > limit
    items = rows[:limit]

    next_cursor = items[-1].id if has_next else None

    return JobListResponse(
        items=[_job_to_response(j) for j in items],
        next_cursor=next_cursor,
    )


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)