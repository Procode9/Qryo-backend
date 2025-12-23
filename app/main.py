from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .schemas import JobCreate, JobResponse

app = FastAPI(title="Qryo Backend", version="0.1.0")

# ------------------------
# CORS (şimdilik açık)
# ------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# ROOT (health check)
# ------------------------
@app.get("/")
def root():
    return {"status": "ok", "service": "qryo-backend"}

# ------------------------
# SUBMIT JOB
# ------------------------
@app.post("/submit-job", response_model=JobResponse)
def submit_job(payload: JobCreate):
    """
    Şu an:
    - DB yok
    - Cost yok
    - Quantum yok

    Sadece sistemin düzgün çalıştığını kanıtlayan iskelet.
    """

    fake_job_id = 1

    return JobResponse(
        job_id=fake_job_id,
        status="queued",
        estimated_cost=None,
    )
