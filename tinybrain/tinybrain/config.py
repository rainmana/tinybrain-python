"""Configuration management for TinyBrain."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    cog_home: str = "tinybrain"
    cog_path_prefix: str = str(Path.home() / ".tinybrain")
    log_level: str = "INFO"

    class Config:
        env_prefix = "TINYBRAIN_"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
