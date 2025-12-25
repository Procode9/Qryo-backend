import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# -------------------------
# Config
# -------------------------
APP_NAME = os.getenv("APP_NAME", "Qryo Backend")
ENV = os.getenv("ENV", "production")

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Render Postgres vs local sqlite:
# - If DATABASE_URL is empty -> sqlite file
# - If postgres URL exists and starts with "postgres://" -> SQLAlchemy expects "postgresql://"
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    DATABASE_URL = "sqlite:///./app.db"

CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=CONNECT_ARGS, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


# -------------------------
# DB Model
# -------------------------
class WaitlistEntry(Base):
    __tablename__ = "waitlist"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), unique=True, index=True, nullable=False)
    name = Column(String(120), nullable=True)
    source = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


# -------------------------
# API Schemas
# -------------------------
class WaitlistRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(default=None, max_length=120)
    source: Optional[str] = Field(default=None, max_length=120)


class WaitlistResponse(BaseModel):
    ok: bool
    message: str
    id: Optional[int] = None


# -------------------------
# App
# -------------------------
app = FastAPI(title=APP_NAME)

# CORS: landing domainini sonra whitelist yaparız; Phase 1 hızlı stabil için açık.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def root():
    return {"ok": True, "name": APP_NAME, "env": ENV}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/waitlist", response_model=WaitlistResponse)
def waitlist(payload: WaitlistRequest):
    email = payload.email.strip().lower()

    db = SessionLocal()
    try:
        existing = db.query(WaitlistEntry).filter(WaitlistEntry.email == email).first()
        if existing:
            return WaitlistResponse(ok=True, message="Already on waitlist", id=existing.id)

        entry = WaitlistEntry(
            email=email,
            name=(payload.name.strip() if payload.name else None),
            source=(payload.source.strip() if payload.source else None),
            created_at=datetime.now(timezone.utc),
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)

        return WaitlistResponse(ok=True, message="Added to waitlist", id=entry.id)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    finally:
        db.close()