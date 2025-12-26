# app/main.py
from __future__ import annotations

import asyncio
import datetime as dt
import json
import time
import uuid
from collections import defaultdict

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .config import settings, assert_runtime_config
from .db import SessionLocal, engine
from .deps import get_current_user, get_db, enforce_user_token_limit
from .limits import SlidingWindowLimiter
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

app = FastAPI(title=settings.app_name)

# -------------------------
# In-memory metrics (Phase-1)
# -------------------------
METRICS = {
    "started_at": now_utc().isoformat(),
    "requests_total": 0,
    "by_path": defaultdict(int),
    "by_status": defaultdict(int),
    "latency_ms_sum": 0.0,
    "latency_ms_count": 0,
}

# -------------------------
# Risk-7: per-user job submit limiter
# -------------------------
JOBS_LIMITER = SlidingWindowLimiter(
    per_minute=settings.rate_limit_per_minute
)

# -------------------------
# Middleware: request id + metrics + timing
# -------------------------
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    t0 = time.perf_counter()
    req_id = request.headers.get("x-request-id") or str(uuid.uuid4())

    response: Response = await call_next(request)

    dt_ms = (time.perf_counter() - t0) * 1000.0
    METRICS["requests_total"] += 1
    METRICS["by_path"][request.url.path] += 1
    METRICS["by_status"][str(response.status_code)] += 1
    METRICS["latency_ms_sum"] += dt_ms
    METRICS["latency_ms_count"] += 1

    response.headers["X-Request-Id"] = req_id
    response.headers["X-Response-Time-Ms"] = f"{dt_ms:.2f}"
    return response

# -------------------------
# CORS
# -------------------------
raw = (settings.cors_origins or "*").strip()
origins = ["*"] if raw in {"*", ""} else [o.strip() for o in raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False if origins == ["*"] else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    assert_runtime_config()
    Base.metadata.create_all(bind=engine)

@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": dt.datetime.now(dt.timezone.utc).isoformat()}

@app.get("/metrics")
def metrics(authorization: str | None = Header(default=None)):
    if settings.metrics_token:
        if not authorization or authorization.strip() != f"Bearer {settings.metrics_token}":
            raise HTTPException(status_code=401, detail="Unauthorized")

    avg = METRICS["latency_ms_sum"] / METRICS["latency_ms_count"] if METRICS["latency_ms_count"] else 0.0
    return {
        "started_at": METRICS["started_at"],
        "requests_total": METRICS["requests_total"],
        "by_path": dict(METRICS["by_path"]),
        "by_status": dict(METRICS["by_status"]),
        "latency_ms_avg": round(avg, 2),
    }

@app.get("/")
def root():
    return {"name": settings.app_name}

# -------------------------
# AUTH
# -------------------------
@app.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    # ✅ ÇÖZÜLEN NOKTA
    enforce_user_token_limit(
        db=db,
        user_id=user.id,
        max_tokens=settings.max_tokens_per_user,
    )

    token = new_token()
    db.add(UserToken(
        token=token,
        user_id=user.id,
        expires_at=expires_at(settings.token_ttl_days),
    ))
    db.commit()

    return AuthResponse(token=token)

@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # ✅ ÇÖZÜLEN NOKTA
    enforce_user_token_limit(
        db=db,
        user_id=user.id,
        max_tokens=settings.max_tokens_per_user,
    )

    token = new_token()
    db.add(UserToken(
        token=token,
        user_id=user.id,
        expires_at=expires_at(settings.token_ttl_days),
    ))
    db.commit()

    return AuthResponse(token=token)

@app.post("/auth/logout")
def logout(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    token_value = authorization.split(" ", 1)[1]
    token = db.query(UserToken).filter(UserToken.token == token_value).first()
    if token:
        token.revoked = True
        db.commit()
    return {"ok": True}

@app.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(id=user.id, email=user.email)

# -------------------------
# JOBS
# -------------------------
def _job_to_response(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        provider=job.provider,
        status=job.status,  # type: ignore
        payload=json.loads(job.payload_json or "{}"),
        result=json.loads(job.result_json or "{}"),
        error_message=job.error_message,
    )

def _enforce_job_limits(user: User, req: JobSubmitRequest, db: Session):
    raw = json.dumps(req.payload or {}, ensure_ascii=False)
    if len(raw.encode()) > settings.jobs_max_payload_bytes:
        raise HTTPException(413, "Payload too large")

    allowed, retry = JOBS_LIMITER.allow(f"user:{user.id}")
    if not allowed:
        raise HTTPException(429, "Too many jobs", headers={"Retry-After": str(retry)})

    active = db.query(Job).filter(
        Job.user_id == user.id,
        Job.status.in_(["queued", "running"]),
    ).count()

    if active >= settings.jobs_max_active_per_user:
        raise HTTPException(429, "Too many active jobs")

async def _simulate_job(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        job.status = "running"
        db.commit()
        await asyncio.sleep(2)
        job.status = "succeeded"
        job.result_json = json.dumps({"ok": True})
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
    _enforce_job_limits(user, req, db)

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

    bg.add_task(_simulate_job, job.id)
    return _job_to_response(job)

@app.get("/jobs", response_model=list[JobResponse])
def list_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [
        _job_to_response(j)
        for j in db.query(Job)
        .filter(Job.user_id == user.id)
        .order_by(Job.created_at.desc())
        .limit(100)
        .all()
    ]

@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return _job_to_response(job)
