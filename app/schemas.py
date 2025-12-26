# app/schemas.py
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


# Auth
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class AuthResponse(BaseModel):
    token: str


class MeResponse(BaseModel):
    id: str
    email: EmailStr


# Jobs
JobStatus = Literal["queued", "running", "succeeded", "failed"]


class JobSubmitRequest(BaseModel):
    provider: str = Field(default="sim", max_length=32)
    payload: dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    id: str
    provider: str
    status: JobStatus
    payload: dict[str, Any]
    result: dict[str, Any]
    error_message: Optional[str] = None