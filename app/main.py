from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from .models import Waitlist

# DB init
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Qryo API")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Schema
class WaitlistRequest(BaseModel):
    email: EmailStr

class WaitlistResponse(BaseModel):
    message: str

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/waitlist", response_model=WaitlistResponse)
def join_waitlist(
    payload: WaitlistRequest,
    db: Session = Depends(get_db)
):
    existing = db.query(Waitlist).filter(
        Waitlist.email == payload.email
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    entry = Waitlist(email=payload.email)
    db.add(entry)
    db.commit()

    return {"message": "Added to waitlist"}