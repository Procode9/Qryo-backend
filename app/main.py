
import asyncio
import json
import datetime as dt
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.db import engine, SessionLocal
from app.models import Base, User, Job, UserToken, now_utc
from app.schemas import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    MeResponse,
    JobSubmitRequest,
    JobResponse,
)
from app.security import hash_password, verify_password, new_token, expires_at
from app.deps import get_db, get_current_user

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"name": settings.app_name, "docs": "/docs"}


@app.get("/healthz")
def health():
    return {"ok": True, "ts": dt.datetime.now(dt.timezone.utc)}


# ---------- AUTH ----------
@app.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(409, "Email already registered")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

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
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    token = new_token()
    db.add(UserToken(
        token=token,
        user_id=user.id,
        expires_at=expires_at(settings.token_ttl_days),
    ))
    db.commit()

    return AuthResponse(token=token)


@app.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(id=user.id, email=user.email)