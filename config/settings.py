# config/settings.py
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

class Settings(BaseSettings):
    """Application settings with environment variable loading and validation"""
    # LLM Settings
    llm_model: str = Field(
        default="llama3.1:8b-instruct-q8_0",
        description="LLM model identifier"
    )
    llm_base_url: Optional[str] = Field(
        default="http://localhost:11434/v1",
        description="Base URL for LLM API"
    )
    llm_api_key: Optional[str] = Field(
        default="ollama",
        description="API key for LLM service"
    )
    
    # API Settings
    max_tokens: int = Field(default=4096, gt=0)
    max_retries: int = Field(default=3, ge=0)
    timeout: int = Field(default=30, gt=0)
    
    # Application Settings
    environment: str = Field(
        default="development",
        pattern="^(development|staging|production)$"
    )
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"
    )
    PYTHONPATH: Optional[str] = None
    
    # Rate Limiting
    max_requests_per_minute: int = Field(default=60, gt=0)
    cooldown_period: int = Field(default=1, gt=0)
    
    class Config:
        env_file = ".env"
        env_prefix = "APP_"
        case_sensitive = True

    @property
    def base_dir(self) -> Path:
        """Get base directory for the application"""
        return Path(__file__).parent.parent

    @property
    def config_dir(self) -> Path:
        """Get configuration directory"""
        return self.base_dir / "config"

    def get_config_path(self, filename: str) -> Path:
        """Get path to a configuration file"""
        return self.config_dir / filename

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()