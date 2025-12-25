from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="QRYO Backend",
    description="Vendor-agnostic quantum job aggregator",
    version="0.1.0",
)

# CORS (landing + future dashboard için güvenli)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "qryo-backend"
    }

# ---- Analytics / Feedback Loop (Phase-1, DB yok) ----
@app.post("/track")
async def track_event(payload: dict, request: Request):
    client_ip = request.client.host if request.client else "unknown"

    print({
        "event": payload.get("event"),
        "path": payload.get("path"),
        "referrer": payload.get("referrer"),
        "ip": client_ip,
    })

    return {"status": "ok"}