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

settings = Settings()
