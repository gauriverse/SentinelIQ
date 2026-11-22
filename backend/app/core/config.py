from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"  # repo root


class Settings(BaseSettings):
    app_name: str = "SentinelIQ API"
    version: str = "0.1.0"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://sentinel:change_me@localhost:5432/sentineliq"

    model_config = SettingsConfigDict(env_file=ROOT_ENV, extra="ignore")


settings = Settings()