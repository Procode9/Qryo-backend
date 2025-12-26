# app/main.py
from __future__ import annotations

import asyncio
import datetime as dt
import json

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal, engine
from app.deps import get_current_user, get_db
from app.models import Base, Job, User, UserToken, now_utc
from app.schemas import (
    AuthResponse,
    JobResponse,
    JobSubmitRequest,
    LoginRequest,
    MeResponse,
    RegisterRequest,
)
from app.security import expires_at, hash_password, new_token, verify_password
from app.providers.registry import get_provider
from app.ratelimit import rate_limit

app = FastAPI(title=settings.app_name)


# -------------------------
# CORS
# -------------------------
origins = [o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# Startup
# -------------------------
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

    # cleanup expired tokens
    db = SessionLocal()
    try:
        db.query(UserToken).filter(UserToken.expires_at < now_utc()).delete()
        db.commit()
    finally:
        db.close()


# -------------------------
# Health
# -------------------------
@app.get("/")
def root():
    return {"name": settings.app_name, "docs": "/docs"}


@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": dt.datetime.now(dt.timezone.utc).isoformat()}


# -------------------------
# AUTH
# -------------------------
@app.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email already registered")

    pw_hash = hash_password(payload.password)
    user = User(email=email, password_hash=pw_hash)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = new_token()
    db.add(UserToken(token=token, user_id=user.id, expires_at=expires_at(settings.token_ttl_days)))
    db.commit()

    return AuthResponse(token=token)


@app.post("/auth/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    rate_limit(request.client.host)

    email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    token = new_token()
    db.add(UserToken(token=token, user_id=user.id, expires_at=expires_at(settings.token_ttl_days)))
    db.commit()

    return AuthResponse(token=token)


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
        status=job.status,
        payload=json.loads(job.payload_json or "{}"),
        result=json.loads(job.result_json or "{}"),
        error_message=job.error_message,
    )


async def _run_job(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = "running"
        db.commit()

        provider = get_provider(job.provider)
        payload = json.loads(job.payload_json or "{}")
        result = provider.run(payload)

        job.status = "succeeded"
        job.result_json = json.dumps(result, ensure_ascii=False)
        job.updated_at = now_utc()
        db.commit()
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
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
    provider_name = (req.provider or "sim").lower()
    get_provider(provider_name)  # validate early

    job = Job(
        user_id=user.id,
        provider=provider_name,
        status="queued",
        payload_json=json.dumps(req.payload or {}, ensure_ascii=False),
        result_json="{}",
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    bg.add_task(_run_job, job.id)
    return _job_to_response(job)


@app.get("/jobs", response_model=list[JobResponse])
def list_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.user_id == user.id).order_by(Job.created_at.desc()).all()
    return [_job_to_response(j) for j in jobs]