from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "QRYO"
    environment: str = "dev"
    database_url: str = "sqlite:///./qryo_v3.db"

    # Provider routing
    default_provider: str = "sim"         # sim|dwave|ibm (later)
    allow_user_provider_override: bool = True

    # Safety + cost control
    enable_real_quantum: bool = False     # REAL providerlar kapalı default
    max_shots: int = 1024                 # limit

    # D-Wave (optional)
    dwave_api_token: str | None = None
    # Cost estimation (USD-like units, abstract)
    cost_per_1000_shots_sim: float = 0.10   # sim için sembolik
    cost_per_1000_shots_dwave: float = 1.50 # gerçekçi placeholder

     max_estimated_cost_per_job: float = 5.0 # HARD LIMIT

settings = Settings()
