"""Configuration management for TinyBrain."""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    db_path: str = str(Path.home() / ".tinybrain" / "data.db")
    use_chromadb: bool = False
    chromadb_path: Optional[str] = None
    log_level: str = "INFO"
    
    class Config:
        env_prefix = "TINYBRAIN_"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()

