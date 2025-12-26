# app/config.py
from __future__ import annotations

from pydantic import BaseModel
import os

class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Start QuAntUm")
    env: str = os.getenv("APP_ENV", "development")  # development | production

    # CORS
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")

    # Auth / Security
    token_ttl_days: int = int(os.getenv("TOKEN_TTL_DAYS", "7"))
    max_tokens_per_user: int = int(os.getenv("MAX_TOKENS_PER_USER", "5"))

    # Rate limit (per user)
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

settings = Settings()

def assert_runtime_config() -> None:
    """
    Prod ortamında tehlikeli defaultlarla ayağa kalkmayı engeller.
    """
    if settings.env == "production":
        if settings.cors_origins.strip() in {"*", ""}:
            raise RuntimeError("PROD: CORS_ORIGINS '*' olamaz. Domainlerini ver.")
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # DB
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data.db")

    # Security
    token_ttl_days: int = int(os.getenv("TOKEN_TTL_DAYS", "30"))

    # CORS
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")

    # App
    app_name: str = os.getenv("APP_NAME", "Quantum Discovery API")
    environment: str = os.getenv("ENVIRONMENT", "production")


settings = Settings()