# app/main.py
from __future__ import annotations

import asyncio
import datetime as dt
import json
import time
import uuid
from collections import defaultdict, deque

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
    Header,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi import Request
from .rate_limit import rate_limit_check

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

# --------------------------------------------------
# APP
# --------------------------------------------------
app = FastAPI(title=settings.app_name)

# --------------------------------------------------
# METRICS (Phase-1, in-memory)
# --------------------------------------------------
METRICS = {
    "started_at": now_utc().isoformat(),
    "requests_total": 0,
    "by_path": defaultdict(int),
    "by_status": defaultdict(int),
    "latency_ms_sum": 0.0,
    "latency_ms_count": 0,
}

# Risk-5: protect /metrics (ops token) + basic rate-limit (instance-local)
_METRICS_CALLS = deque()  # timestamps (monotonic)
_METRICS_RPM = int(getattr(settings, "metrics_rate_limit_per_min", 30) or 30)


def _require_ops_token(authorization: str | None) -> None:
    """
    Ops-only gate:
    Authorization: Bearer <METRICS_TOKEN>
    """
    token = (getattr(settings, "metrics_token", "") or "").strip()
    if not token:
        # Safer default: if not configured, DISABLE metrics endpoint.
        raise HTTPException(status_code=404, detail="Not found")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    incoming = authorization.split(" ", 1)[1].strip()
    if incoming != token:
        raise HTTPException(status_code=403, detail="Forbidden")


def _metrics_rate_limit() -> None:
    """
    Instance-local sliding window: last 60s <= _METRICS_RPM
    """
    now = time.monotonic()
    window_start = now - 60.0
    while _METRICS_CALLS and _METRICS_CALLS[0] < window_start:
        _METRICS_CALLS.popleft()

    if len(_METRICS_CALLS) >= _METRICS_RPM:
        raise HTTPException(status_code=429, detail="Too many requests")

    _METRICS_CALLS.append(now)


# --------------------------------------------------
# MIDDLEWARE: request-id + metrics
# --------------------------------------------------
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    req_id = request.headers.get("x-request-id") or str(uuid.uuid4())
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    # 🔒 RATE LIMIT (anon / public)
    try:
        rate_limit_check(request, user_id=None)
    except HTTPException:
        raise
        
    try:
        response: Response = await call_next(request)
        status_code = response.status_code
    except Exception:
        status_code = 500
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000.0
        METRICS["requests_total"] += 1
        METRICS["by_path"][request.url.path] += 1
        METRICS["by_status"][str(status_code)] += 1
        METRICS["latency_ms_sum"] += duration_ms
        METRICS["latency_ms_count"] += 1

    response.headers["X-Request-Id"] = req_id
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
    return response


# --------------------------------------------------
# CORS (global)
# --------------------------------------------------
raw = getattr(settings, "cors_origins", "*") or "*"
origins = ["*"] if raw in ("*", "") else [o.strip() for o in raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False if origins == ["*"] else True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# STARTUP
# --------------------------------------------------
from .config import assert_runtime_config

@app.on_event("startup")
def on_startup():
    assert_runtime_config()
    Base.metadata.create_all(bind=engine)


# --------------------------------------------------
# HEALTH & METRICS
# --------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": dt.datetime.now(dt.timezone.utc).isoformat()}


@app.get("/metrics")
def metrics(authorization: str | None = Header(default=None)):
    # Risk-5 fix: secure + rate-limit
    _require_ops_token(authorization)
    _metrics_rate_limit()

    avg = (
        METRICS["latency_ms_sum"] / METRICS["latency_ms_count"]
        if METRICS["latency_ms_count"]
        else 0.0
    )
    return {
        "started_at": METRICS["started_at"],
        "requests_total": METRICS["requests_total"],
        "by_path": dict(METRICS["by_path"]),
        "by_status": dict(METRICS["by_status"]),
        "latency_ms_avg": round(avg, 2),
    }


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": "/healthz",
        # intentionally NOT advertising /metrics publicly
    }


# --------------------------------------------------
# AUTH
# --------------------------------------------------
@app.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    try:
        pw_hash = hash_password(payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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


@app.post("/auth/logout")
def logout(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=400, detail="Invalid Authorization header")

    token_value = authorization.split(" ", 1)[1].strip()

    token = db.query(UserToken).filter(UserToken.token == token_value).first()
    if token:
        token.revoked = True
        db.commit()

    return {"ok": True}


@app.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(id=user.id, email=user.email)


# --------------------------------------------------
# JOBS (Phase-1 core)
# --------------------------------------------------
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
            {"provider": job.provider, "message": "simulated quantum execution completed"},
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
    provider = (req.provider or "sim").strip().lower()
    if provider != "sim":
        raise HTTPException(status_code=400, detail="Only 'sim' provider supported in phase-1")

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
