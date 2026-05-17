from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./registration_service.db"
    raw_image_dir: Path = Path("data/raw-images")
    duplicate_hash_ttl_seconds: int = 3600
    raw_image_min_retention_hours: int = 24
    app_port: int = 8080


settings = Settings()
