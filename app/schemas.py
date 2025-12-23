from pydantic import BaseModel
from typing import Optional


class JobCreate(BaseModel):
    pass


class JobResponse(BaseModel):
    job_id: int
    status: str
    estimated_cost: Optional[float] = None

    class Config:
        from_attributes = True