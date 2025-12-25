from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

app = FastAPI(title="Qryo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- In-memory waitlist (Phase 0) ----
WAITLIST = []

class WaitlistRequest(BaseModel):
    email: EmailStr

@app.get("/")
def root():
    return {"status": "ok", "service": "qryo-backend"}

@app.post("/v1/waitlist")
def join_waitlist(data: WaitlistRequest):
    if data.email in WAITLIST:
        raise HTTPException(status_code=400, detail="Email already registered")

    WAITLIST.append(data.email)

    # Log for now (Render logs = audit trail)
    print(f"[WAITLIST] New signup: {data.email}")

    return {
        "success": True,
        "message": "You are on the waitlist",
        "count": len(WAITLIST)
    }