from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime

class JobSubmitRequest(BaseModel):
    task: str
    params: Dict[str, Any] = {}

class JobResponse(BaseModel):
    job_id: str
    status: str
    created_at: datetime