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

    # CogDB
    cog_home: str = Field(default="tinybrain", description="CogDB home directory name")
    cog_path_prefix: Path = Field(
        default_factory=lambda: Path.home() / ".tinybrain",
        description="CogDB path prefix (parent directory for cog_home)",
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
