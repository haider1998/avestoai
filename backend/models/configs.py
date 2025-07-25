# backend/models/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from functools import lru_cache


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Google Cloud
    GOOGLE_CLOUD_PROJECT: str
    VERTEX_AI_LOCATION: str = "us-central1"
    FIRESTORE_DATABASE: str = "(default)"

    # Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Fi Money MCP Configuration
    FI_MCP_BASE_URL: str
    FI_MCP_API_KEY: str
    FI_MCP_TIMEOUT: int = 30
    FI_MCP_MAX_RETRIES: int = 3

    # External APIs
    EXTERNAL_API_TIMEOUT: int = 30
    MAX_CONCURRENT_REQUESTS: int = 100

    # Security
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8001",
        "http://localhost:8002",
        "https://avestoai.com"
    ]
    ALLOWED_HOSTS: List[str] = ["*"]

    # Rate Limiting
    RATE_LIMIT_CALLS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds

    # Caching
    CACHE_TTL: int = 300  # 5 minutes
    REDIS_URL: Optional[str] = None

    # Database
    DATABASE_URL: Optional[str] = None
    DATABASE_POOL_SIZE: int = 20

    # Monitoring
    ENABLE_METRICS: bool = True
    LOG_LEVEL: str = "INFO"

    # Feature Flags
    ENABLE_PREDICTIVE_ANALYSIS: bool = True
    ENABLE_REAL_TIME_STREAMING: bool = True
    ENABLE_ADVANCED_CHARTS: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
