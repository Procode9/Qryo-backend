from fastapi import FastAPI, Depends
from pydantic import BaseModel, EmailStr
from app.auth import (
    USERS,
    hash_password,
    verify_password,
    create_token,
    get_current_user
)

app = FastAPI(title="Quantum Aggregator API")

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/auth/register", status_code=201)
def register(data: RegisterRequest):
    if data.email in USERS:
        return {"error": "user_exists"}

    USERS[data.email] = {
        "password": hash_password(data.password),
        "created_at": "now"
    }
    return {"status": "created"}


@app.post("/auth/login")
def login(data: LoginRequest):
    user = USERS.get(data.email)
    if not user or not verify_password(data.password, user["password"]):
        return {"error": "invalid_credentials"}

    token = create_token(data.email)
    return {"token": token}


@app.get("/dashboard")
def dashboard(user_email: str = Depends(get_current_user)):
    return {
        "user": user_email,
        "jobs": [],
        "providers": ["simulator"],
        "status": "ready"
    }