# app/config.py
from __future__ import annotations

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
    app_name: str = os.getenv("APP_NAME", "Quantum Job API")
    environment: str = os.getenv("ENVIRONMENT", "production")


settings = Settings()