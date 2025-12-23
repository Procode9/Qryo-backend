from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "QRYO"
    environment: str = "dev"

    # DB bump to avoid schema mismatch when we add cost fields
    database_url: str = "sqlite:///./qryo_v4.db"

    # Provider routing
    default_provider: str = "sim"          # sim | dwave
    allow_user_provider_override: bool = True

    # Safety
    enable_real_quantum: bool = False      # KILL SWITCH (default off)
    max_shots: int = 1024

    # Cost estimation (abstract USD-like)
    cost_per_1000_shots_sim: float = 0.10
    cost_per_1000_shots_dwave: float = 1.50
    max_estimated_cost_per_job: float = 5.0

    # D-Wave
    dwave_api_token: str | None = None


settings = Settings()
