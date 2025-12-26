# app/config.py
from __future__ import annotations

import os
from pydantic import BaseModel, Field


def _env(name: str, default: str) -> str:
    return (os.getenv(name, default) or default).strip()


class Settings(BaseModel):
    # -----------------------------
    # App
    # -----------------------------
    app_name: str = Field(default_factory=lambda: _env("APP_NAME", "Start QuAntUm"))
    env: str = Field(default_factory=lambda: _env("APP_ENV", "development").lower())
    # development | production

    # -----------------------------
    # Database
    # -----------------------------
    database_url: str = Field(default_factory=lambda: _env("DATABASE_URL", "sqlite:///./data.db"))

    # -----------------------------
    # CORS
    # -----------------------------
    cors_origins: str = Field(default_factory=lambda: _env("CORS_ORIGINS", "*"))

    # -----------------------------
    # Auth / Security
    # -----------------------------
    token_ttl_days: int = Field(default_factory=lambda: int(_env("TOKEN_TTL_DAYS", "7")))
    max_tokens_per_user: int = Field(default_factory=lambda: int(_env("MAX_TOKENS_PER_USER", "5")))

    # -----------------------------
    # Rate limit (Risk-4)
    # -----------------------------
    rate_limit_enabled: bool = Field(default_factory=lambda: _env("RATE_LIMIT_ENABLED", "0") == "1")
    rate_limit_per_minute: int = Field(default_factory=lambda: int(_env("RATE_LIMIT_PER_MINUTE", "60")))

    # -----------------------------
    # Metrics / Ops (Risk-5)
    # -----------------------------
    metrics_token: str = Field(default_factory=lambda: _env("METRICS_TOKEN", ""))  # empty => dev açık
    metrics_rate_limit_per_min: int = Field(default_factory=lambda: int(_env("METRICS_RATE_LIMIT_PER_MIN", "30")))

    # -----------------------------
    # Admin / Ops
    # -----------------------------
    admin_emails: str = Field(default_factory=lambda: _env("ADMIN_EMAILS", ""))  # "a@x.com,b@y.com"


settings = Settings()


def assert_runtime_config() -> None:
    """
    Production ortamında tehlikeli ayarlarla ayağa kalkmayı engeller.
    Startup'ta çağır.
    """
    if settings.env == "production":
        if settings.cors_origins.strip() in {"*", ""}:
            raise RuntimeError("PROD CONFIG ERROR: CORS_ORIGINS '*' olamaz. Domainlerini belirt.")
        if settings.metrics_token.strip() == "":
            raise RuntimeError("PROD CONFIG ERROR: METRICS_TOKEN boş olamaz (metrics endpointini koru).")
