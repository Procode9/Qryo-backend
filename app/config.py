# app/config.py
from __future__ import annotations

import os
from pydantic import BaseModel, Field


def _env(name: str, default: str) -> str:
    return (os.getenv(name, default) or default).strip()


class Settings(BaseModel):
    # -----------------------------
    # App / Environment
    # -----------------------------
    env: str = Field(default_factory=lambda: _env("ENV", "development"))
    app_name: str = Field(default_factory=lambda: _env("APP_NAME", "qryo-backend"))

    # -----------------------------
    # Database
    # -----------------------------
    database_url: str = Field(
        default_factory=lambda: _env("DATABASE_URL", "sqlite:///./data.db")
    )

    # -----------------------------
    # CORS
    # -----------------------------
    cors_origins: str = Field(
        default_factory=lambda: _env("CORS_ORIGINS", "*")
    )

    # -----------------------------
    # Auth / Tokens
    # -----------------------------
    token_ttl_days: int = Field(
        default_factory=lambda: int(_env("TOKEN_TTL_DAYS", "7"))
    )
    max_tokens_per_user: int = Field(
        default_factory=lambda: int(_env("MAX_TOKENS_PER_USER", "5"))
    )

    # -----------------------------
    # Rate limit (Risk-4)
    # -----------------------------
    rate_limit_enabled: bool = Field(
        default_factory=lambda: _env("RATE_LIMIT_ENABLED", "0") == "1"
    )
    rate_limit_per_minute: int = Field(
        default_factory=lambda: int(_env("RATE_LIMIT_PER_MINUTE", "60"))
    )

    # -----------------------------
    # Jobs limits (Phase-1)
    # -----------------------------
    jobs_max_payload_bytes: int = Field(
        default_factory=lambda: int(_env("JOBS_MAX_PAYLOAD_BYTES", "65536"))  # 64 KB
    )
    jobs_max_active_per_user: int = Field(
        default_factory=lambda: int(_env("JOBS_MAX_ACTIVE_PER_USER", "3"))
    )

    # -----------------------------
    # Metrics / Ops (Risk-5)
    # -----------------------------
    metrics_token: str = Field(
        default_factory=lambda: _env("METRICS_TOKEN", "")
    )
    metrics_rate_limit_per_min: int = Field(
        default_factory=lambda: int(_env("METRICS_RATE_LIMIT_PER_MIN", "30"))
    )

    # -----------------------------
    # Admin / Ops
    # -----------------------------
    admin_emails: str = Field(
        default_factory=lambda: _env("ADMIN_EMAILS", "")
    )


settings = Settings()


def assert_runtime_config() -> None:
    """
    Production ortamında tehlikeli ayarlarla ayağa kalkmayı engeller.
    Startup'ta çağır.
    """
    if settings.env == "production":
        if settings.cors_origins.strip() in {"*", ""}:
            raise RuntimeError(
                "PROD CONFIG ERROR: CORS_ORIGINS '*' olamaz. Domainlerini belirt."
            )
        if settings.metrics_token.strip() == "":
            raise RuntimeError(
                "PROD CONFIG ERROR: METRICS_TOKEN boş olamaz."
            )