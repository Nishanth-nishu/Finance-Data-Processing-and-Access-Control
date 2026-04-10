"""
Application configuration using pydantic-settings.
All values are loaded from environment variables — zero hardcoding.

Security improvements:
- JWT_SECRET_KEY uses SecretStr to prevent accidental logging of the secret.
- DATABASE_URL uses SecretStr to prevent connection strings leaking to logs.
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Finance Dashboard API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database — SecretStr prevents the URL (with credentials) from leaking to logs
    DATABASE_URL: SecretStr = SecretStr(
        "sqlite+aiosqlite:///./finance_dashboard.db"
    )

    # PostgreSQL connection pool tuning (ignored for SQLite)
    DB_POOL_SIZE: int = 10          # Max persistent connections
    DB_MAX_OVERFLOW: int = 20       # Extra connections beyond pool_size under load
    DB_POOL_TIMEOUT: int = 30       # Seconds to wait for a free connection
    DB_POOL_RECYCLE: int = 1800     # Recycle connections after 30 min (avoids stale TCP)

    # JWT — SecretStr ensures the key is NEVER printed by logging or repr()
    JWT_SECRET_KEY: SecretStr = SecretStr(
        "change-me-in-production-use-openssl-rand-hex-32"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis (optional — for caching and Celery)
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 300        # Dashboard summary cache TTL (5 min)

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Pagination hard limits
    MAX_PAGE_SIZE: int = 100

    # Retry / resilience
    DB_CONNECT_RETRY_ATTEMPTS: int = 3
    DB_CONNECT_RETRY_DELAY_SECONDS: float = 1.0


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance (singleton pattern)."""
    return Settings()
