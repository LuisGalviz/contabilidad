from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "ContaFlow"
    app_env: str = "development"
    app_debug: bool = False
    app_secret_key: str
    app_allowed_origins: str = "http://localhost:3000"

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.app_allowed_origins.split(",")]

    # Database
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Storage
    storage_backend: str = "local"
    storage_local_path: str = "./uploads"
    storage_s3_bucket: str = "contaflow-reports"
    storage_s3_region: str = "us-east-1"
    storage_s3_access_key: str = ""
    storage_s3_secret_key: str = ""
    storage_s3_endpoint_url: str = ""

    # Rate limiting
    rate_limit_per_minute: int = 60

    # Observability
    log_level: str = "INFO"
    sentry_dsn: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
