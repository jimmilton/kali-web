"""Application configuration settings.

Copyright 2025 milbert.ai
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "kwebbie"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Data directory (for SQLite, files, etc.)
    data_dir: str = "/data"

    # Database - SQLite by default
    database_url: str = "sqlite:///data/kwebbie.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT Authentication
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: List[str] = ["*"]

    # Tool Execution
    tool_timeout_default: int = 3600  # 1 hour
    tools_dir: str = "/usr/bin"  # Where tools are installed

    # Encryption
    encryption_key: Optional[str] = None

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    # Integrations (optional)
    jira_url: Optional[str] = None
    jira_user: Optional[str] = None
    jira_api_token: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    discord_webhook_url: Optional[str] = None

    @property
    def async_database_url(self) -> str:
        """Get async database URL for SQLAlchemy."""
        if self.database_url.startswith("sqlite"):
            # SQLite async uses aiosqlite
            return self.database_url.replace("sqlite://", "sqlite+aiosqlite://")
        elif self.database_url.startswith("postgresql"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        return self.database_url

    @property
    def data_path(self) -> Path:
        """Get data directory path."""
        path = Path(self.data_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def uploads_path(self) -> Path:
        """Get uploads directory path."""
        path = self.data_path / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def reports_path(self) -> Path:
        """Get reports directory path."""
        path = self.data_path / "reports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def outputs_path(self) -> Path:
        """Get tool outputs directory path."""
        path = self.data_path / "outputs"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
