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
from .deps import get_current_user, get_db
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

    try:
        response: Response = await call_next(request)
    except Exception:
        dt_ms = (time.perf_counter() - t0) * 1000.0
        METRICS["requests_total"] += 1
        METRICS["by_path"][request.url.path] += 1
        METRICS["by_status"]["500"] += 1
        METRICS["latency_ms_sum"] += dt_ms
        METRICS["latency_ms_count"] += 1
        raise

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
# CORS (global use)
# -------------------------
raw = (settings.cors_origins or "*").strip()
if raw in {"*", ""}:
    origins = ["*"]
else:
    origins = [o.strip() for o in raw.split(",") if o.strip()]

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
    # Risk-5: metrics token varsa koru
    if settings.metrics_token:
        if not authorization or authorization.strip() != f"Bearer {settings.metrics_token}":
            raise HTTPException(status_code=401, detail="Unauthorized")

    avg = (METRICS["latency_ms_sum"] / METRICS["latency_ms_count"]) if METRICS["latency_ms_count"] else 0.0
    return {
        "started_at": METRICS["started_at"],
        "requests_total": METRICS["requests_total"],
        "by_path": dict(METRICS["by_path"]),
        "by_status": dict(METRICS["by_status"]),
        "latency_ms_avg": round(avg, 2),
    }

@app.get("/")
def root():
    return {"name": settings.app_name, "docs": "/docs", "health": "/healthz", "metrics": "/metrics"}

# -------------------------
# AUTH
# -------------------------
@app.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    try:
        pw_hash = hash_password(payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user = User(email=email, password_hash=pw_hash)
    db.add(user)
    db.commit()
    db.refresh(user)

    tok = new_token()
    db.add(UserToken(token=tok, user_id=user.id, expires_at=expires_at(settings.token_ttl_days)))
    db.commit()

    return AuthResponse(token=tok)

@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    tok = new_token()
    db.add(UserToken(token=tok, user_id=user.id, expires_at=expires_at(settings.token_ttl_days)))
    db.commit()

    return AuthResponse(token=tok)

@app.post("/auth/logout")
def logout(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    if not authorization or " " not in authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization")
    token_value = authorization.split(" ", 1)[1].strip()

    token = db.query(UserToken).filter(UserToken.token == token_value).first()
    if token:
        token.revoked = True
        db.commit()

    return {"ok": True}

@app.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(id=user.id, email=user.email)

# -------------------------
# JOBS (phase-1 core)
# -------------------------
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

def _enforce_job_limits(user: User, req: JobSubmitRequest, db: Session) -> None:
    # 1) payload size limit
    raw = json.dumps(req.payload or {}, ensure_ascii=False)
    if len(raw.encode("utf-8")) > settings.jobs_max_payload_bytes:
        raise HTTPException(status_code=413, detail="Payload too large")

    # 2) per-user per-minute limiter (in-memory)
    allowed, retry_after = JOBS_LIMITER.allow(f"user:{user.id}")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Too many job submissions. Retry after {retry_after}s",
            headers={"Retry-After": str(retry_after)},
        )

    # 3) active jobs cap (DB-backed)
    active = (
        db.query(Job)
        .filter(Job.user_id == user.id, Job.status.in_(["queued", "running"]))
        .count()
    )
    if active >= settings.jobs_max_active_per_user:
        raise HTTPException(
            status_code=429,
            detail=f"Too many active jobs (max {settings.jobs_max_active_per_user}).",
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

        await asyncio.sleep(2.0)

        try:
            payload = json.loads(job.payload_json or "{}")
        except Exception:
            payload = {}

        job.status = "succeeded"
        job.result_json = json.dumps(
            {
                "provider": job.provider,
                "echo": payload,
                "message": "simulated quantum execution completed",
            },
            ensure_ascii=False,
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
    _enforce_job_limits(user, req, db)

    provider = (req.provider or "sim").strip().lower()
    if provider not in {"sim"}:
        raise HTTPException(status_code=400, detail="Unsupported provider in phase-1 (use 'sim')")

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

@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)
