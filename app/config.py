# app/config.py
from __future__ import annotations

import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    # -------------------------------------------------
    # App
    # -------------------------------------------------
    app_name: str = Field(
        default_factory=lambda: os.getenv("APP_NAME", "Start QuAntUm")
    )
    env: str = Field(
        default_factory=lambda: os.getenv("APP_ENV", "development")
    )
    # development | production

    # -------------------------------------------------
    # Database
    # -------------------------------------------------
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./data.db")
    )

    # -------------------------------------------------
    # CORS
    # -------------------------------------------------
    cors_origins: str = Field(
        default_factory=lambda: os.getenv("CORS_ORIGINS", "*")
    )

    # -------------------------------------------------
    # Auth / Security
    # -------------------------------------------------
    token_ttl_days: int = Field(
        default_factory=lambda: int(os.getenv("TOKEN_TTL_DAYS", "7"))
    )
    max_tokens_per_user: int = Field(
        default_factory=lambda: int(os.getenv("MAX_TOKENS_PER_USER", "5"))
    )

    # -------------------------------------------------
    # Rate limit (Risk-4)
    # -------------------------------------------------
    rate_limit_enabled: bool = Field(
        default_factory=lambda: os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
    )
    rate_limit_per_minute: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    )

    # -------------------------------------------------
    # Metrics / Ops (Risk-5)
    # -------------------------------------------------
    metrics_enabled: bool = Field(
        default_factory=lambda: os.getenv("METRICS_ENABLED", "false").lower() == "true"
    )
    metrics_admin_token: str = Field(
        default_factory=lambda: os.getenv("METRICS_ADMIN_TOKEN", "")
    )
    metrics_rate_limit_per_min: int = Field(
        default_factory=lambda: int(os.getenv("METRICS_RATE_LIMIT_PER_MIN", "30"))
    )

    # -------------------------------------------------
    # Admin / Ops
    # -------------------------------------------------
    admin_emails: str = Field(
        default_factory=lambda: os.getenv("ADMIN_EMAILS", "")
    )


settings = Settings()


def assert_runtime_config() -> None:
    """
    Production ortamında tehlikeli ayarlarla ayağa kalkmayı engeller.
    Startup'ta çağrılmalı.
    """
    if settings.env == "production":
        # CORS guard
        if settings.cors_origins.strip() in {"*", ""}:
            raise RuntimeError(
                "PROD CONFIG ERROR: CORS_ORIGINS '*' olamaz. Domainlerini belirt."
            )

        # Metrics guard (Risk-5)
        if settings.metrics_enabled and not settings.metrics_admin_token:
            raise RuntimeError(
                "PROD CONFIG ERROR: METRICS_ENABLED=true ama METRICS_ADMIN_TOKEN yok."
    )
