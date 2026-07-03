# src/utils/config.py

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "Otonom Data Cleanroom & Tahminleme Ajanı"
    app_env: Literal["local", "dev", "test", "prod"] = "local"
    debug: bool = True
    log_level: str = "INFO"

    # LLM / API Keys
    google_api_key: str | None = Field(default=None, repr=False)

    # Database
    database_url: str = "postgresql+psycopg2://postgres:3456@localhost:5434/pizza_runner"

    # AWS - optional for MVP
    aws_access_key_id: str | None = Field(default=None, repr=False)
    aws_secret_access_key: str | None = Field(default=None, repr=False)
    aws_s3_bucket: str | None = None
    aws_region: str = "eu-central-1"
    aws_s3_prefix: str = ""
    aws_endpoint_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_aws_configured(self) -> bool:
        return bool(
            self.aws_access_key_id
            and self.aws_secret_access_key
            and self.aws_s3_bucket
        )
    
    def safe_dict(self) -> dict:
        """Log veya debug için secret değerleri maskeleyerek döndürür."""
        data = self.model_dump()
        secret_keys = {
            "google_api_key",
            "aws_access_key_id",
            "aws_secret_access_key",
        }

        for key in secret_keys:
            if data.get(key):
                data[key] = "***masked***"

        return data


@lru_cache
def get_settings() -> Settings:
    return Settings()