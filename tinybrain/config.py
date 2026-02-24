"""Configuration management using pydantic-settings."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """TinyBrain configuration."""

    model_config = SettingsConfigDict(
        env_prefix="TINYBRAIN_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    db_path: Path = Field(
        default_factory=lambda: Path.home() / ".tinybrain" / "memory.db",
        description="Path to SQLite database",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_file: Optional[Path] = Field(
        default_factory=lambda: Path.home() / ".tinybrain" / "logs" / "tinybrain.log",
        description="Log file path",
    )
    log_rotation: str = Field(default="100 MB", description="Log rotation size")
    log_retention: str = Field(default="10 days", description="Log retention period")

    # Server
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # Security data
    security_data_dir: Path = Field(
        default_factory=lambda: Path.home() / ".tinybrain" / "security_data",
        description="Security data directory",
    )


settings = Settings()
