
# app/schemas.py
from __future__ import annotations

from typing import Any, Optional, List
from pydantic import BaseModel, EmailStr, Field


# -------------------------
# AUTH
# -------------------------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str


class MeResponse(BaseModel):
    id: int
    email: EmailStr


# -------------------------
# JOBS
# -------------------------
class JobSubmitRequest(BaseModel):
    provider: Optional[str] = "sim"
    payload: Optional[dict[str, Any]] = None


class JobResponse(BaseModel):
    id: str
    provider: str
    status: str
    payload: dict[str, Any]
    result: dict[str, Any]
    error_message: Optional[str] = None


# 🔹 Phase-1.2
class JobListResponse(BaseModel):
    items: List[JobResponse]
    next_cursor: Optional[str] = None