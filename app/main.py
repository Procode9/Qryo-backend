from __future__ import annotations

import asyncio
import datetime as dt
import json
import time
from collections import defaultdict

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
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
    LoginRequest,
    MeResponse,
    RegisterRequest,
)
from .security import expires_at, hash_password, new_token, verify_password

# -------------------------------------------------------------------
# APP
# -------------------------------------------------------------------
app = FastAPI(title=settings.app_name)

# -------------------------------------------------------------------
# CORS
# -------------------------------------------------------------------
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

# -------------------------------------------------------------------
# USAGE METRICS (GLOBAL - PHASE 1)
# -------------------------------------------------------------------
METRICS = {
    "requests_total": 0,
    "requests_by_path": defaultdict(int),
    "requests_by_status": defaultdict(int),
    "latency_ms": [],
    "jobs_created": 0,
    "jobs_by_user": defaultdict(int),
}


@app.middleware("http")
async def usage_metrics_middleware(request: Request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    duration_ms = (time.perf_counter() - start) * 1000

    METRICS["requests_total"] += 1
    METRICS["requests_by_path"][request.url.path] += 1
    METRICS["requests_by_status"][response.status_code] += 1
    METRICS["latency_ms"].append(round(duration_ms, 2))

    return response


# -------------------------------------------------------------------
# STARTUP
# -------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


# -------------------------------------------------------------------
# SYSTEM
# -------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": dt.datetime.now(dt.timezone.utc).isoformat()}


@app.get("/")
def root():
    return {"name": settings.app_name, "docs": "/docs"}


@app.get("/metrics")
def metrics():
    """Phase-1 internal metrics (no auth by design)"""
    return {
        "requests_total": METRICS["requests_total"],
        "requests_by_path": dict(METRICS["requests_by_path"]),
        "requests_by_status": dict(METRICS["requests_by_status"]),
        "avg_latency_ms": (
            round(sum(METRICS["latency_ms"]) / len(METRICS["latency_ms"]), 2)
            if METRICS["latency_ms"]
            else 0
        ),
        "jobs_created": METRICS["jobs_created"],
        "jobs_by_user": dict(METRICS["jobs_by_user"]),
    }


# -------------------------------------------------------------------
# AUTH
# -------------------------------------------------------------------
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
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
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


# -------------------------------------------------------------------
# JOB ENGINE (PHASE 1)
# -------------------------------------------------------------------
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
                "provider": job.provider,
                "message": "simulated quantum execution completed",
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
    if (req.provider or "sim") != "sim":
        raise HTTPException(status_code=400, detail="Only 'sim' provider supported")

    job = Job(
        user_id=user.id,
        provider="sim",
        status="queued",
        payload_json=json.dumps(req.payload or {}),
        result_json="{}",
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    METRICS["jobs_created"] += 1
    METRICS["jobs_by_user"][str(user.id)] += 1

    bg.add_task(_simulate_job, job.id)
    return _job_to_response(job)


@app.get("/jobs", response_model=list[JobResponse])
def list_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = (
        db.query(Job)
        .filter(Job.user_id == user.id)
        .order_by(Job.created_at.desc())
        .limit(100)
        .all()
    )
    return [_job_to_response(j) for j in jobs]