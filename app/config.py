from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "QRYO"
    environment: str = "dev"
    database_url: str = "sqlite:///./qryo_v3.db"

    # Provider routing
    default_provider: str = "sim"          # sim | dwave
    allow_user_provider_override: bool = True

    # Safety
    enable_real_quantum: bool = False
    max_shots: int = 1024

    # Cost estimation (USD-like, abstract units)
    cost_per_1000_shots_sim: float = 0.10
    cost_per_1000_shots_dwave: float = 1.50

    # HARD LIMIT
    max_estimated_cost_per_job: float = 5.0


settings = Settings()
