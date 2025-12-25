from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
from collections import defaultdict, deque

app = FastAPI(
    title="QRYO Backend",
    description="Vendor-agnostic quantum job aggregator",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok", "service": "qryo-backend"}

# ---- Soft rate limit (IP-based, in-memory) ----
WINDOW_SECONDS = 60
MAX_EVENTS = 30
ip_events = defaultdict(deque)

def is_rate_limited(ip: str) -> bool:
    now = time.time()
    q = ip_events[ip]
    while q and now - q[0] > WINDOW_SECONDS:
        q.popleft()
    if len(q) >= MAX_EVENTS:
        return True
    q.append(now)
    return False

# ---- Analytics / Feedback Loop (Light + Bot-safe) ----
@app.post("/track")
async def track_event(payload: dict, request: Request):
    client_ip = request.client.host if request.client else "unknown"

    # Honeypot kontrolü (doluysa bot)
    if payload.get("hp"):
        # Sessizce geç → botu teşvik etme
        return {"status": "ok"}

    # Soft rate limit
    if is_rate_limited(client_ip):
        # Yine sessizce geç
        return {"status": "ok"}

    print({
        "event": payload.get("event"),
        "path": payload.get("path"),
        "referrer": payload.get("referrer"),
        "ip": client_ip,
    })

    return {"status": "ok"}