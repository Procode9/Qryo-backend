from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import List
import csv
import io
import os
from fastapi.responses import StreamingResponse

from .database import Base, engine, SessionLocal
from .models import Waitlist

# DB init
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Qryo API")

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def admin_auth(x_admin_token: str = Header(...)):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

# Schemas
class WaitlistRequest(BaseModel):
    email: EmailStr

class WaitlistResponse(BaseModel):
    message: str

class WaitlistItem(BaseModel):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True

@app.get("/")
def root():
    return {"status": "ok"}

# ---- PUBLIC ----

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

# ---- ADMIN ----

@app.get("/admin/count")
def admin_count(
    db: Session = Depends(get_db),
    _: None = Depends(admin_auth)
):
    count = db.query(Waitlist).count()
    return {"count": count}

@app.get("/admin/list", response_model=List[WaitlistItem])
def admin_list(
    db: Session = Depends(get_db),
    _: None = Depends(admin_auth)
):
    return db.query(Waitlist).order_by(Waitlist.id.desc()).all()

@app.get("/admin/export")
def admin_export(
    db: Session = Depends(get_db),
    _: None = Depends(admin_auth)
):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "email", "created_at"])

    for row in db.query(Waitlist).all():
        writer.writerow([row.id, row.email, row.created_at])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=waitlist.csv"
        }
    )