from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "QRYO"
    environment: str = "dev"
    database_url: str = "sqlite:///./qryo.db"
    default_provider: str = "sim"

settings = Settings()
