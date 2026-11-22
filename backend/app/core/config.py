from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"  # repo root
DEV_SECRET = "dev-only-insecure-secret-change-me"


class Settings(BaseSettings):
    app_name: str = "SentinelIQ API"
    version: str = "0.1.0"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://sentinel:change_me@localhost:5433/sentineliq"

    secret_key: str = DEV_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(env_file=ROOT_ENV, extra="ignore")

    @model_validator(mode="after")
    def _reject_dev_secret_in_production(self) -> "Settings":
        if self.environment == "production" and self.secret_key == DEV_SECRET:
            raise ValueError("SECRET_KEY must be set in production")
        return self


settings = Settings()