from pydantic import BaseModel, Field
from typing import Optional


# ------------------------
# JOB CREATE (Request)
# ------------------------
class JobCreate(BaseModel):
    problem_type: str = Field(
        ...,
        description="Type of problem (e.g. optimization, sampling)",
        examples=["optimization"],
    )
    size: int = Field(
        ...,
        ge=1,
        le=1000,
        description="Problem size or complexity indicator",
        examples=[10],
    )


# ------------------------
# JOB RESPONSE (Response)
# ------------------------
class JobResponse(BaseModel):
    job_id: int
    status: str
    estimated_cost: Optional[float] = None

    class Config:
        from_attributes = True
