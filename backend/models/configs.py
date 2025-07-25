# backend/models/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from functools import lru_cache
from pydantic import field_validator


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Google Cloud
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    VERTEX_AI_LOCATION: str = "us-central1"
    FIRESTORE_DATABASE: str = "(default)"

    # Authentication
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Fi Money MCP Configuration
    FI_MCP_BASE_URL: Optional[str] = None
    FI_MCP_API_KEY: Optional[str] = None
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

    @field_validator('FI_MCP_BASE_URL')
    @classmethod
    def validate_fi_mcp_base_url(cls, v):
        if v and v.startswith('https://your-fi-mcp-server.com'):
            return None  # Treat placeholder as None
        return v

    @field_validator('FI_MCP_API_KEY')
    @classmethod
    def validate_fi_mcp_api_key(cls, v):
        if v and v == 'your-fi-mcp-api-key-here':
            return None  # Treat placeholder as None
        return v

    @field_validator('GOOGLE_CLOUD_PROJECT')
    @classmethod
    def validate_google_cloud_project(cls, v):
        if not v and os.getenv('ENVIRONMENT') == 'production':
            raise ValueError('GOOGLE_CLOUD_PROJECT is required in production')
        return v

    @field_validator('JWT_SECRET_KEY')
    @classmethod
    def validate_jwt_secret_key(cls, v):
        if not v and os.getenv('ENVIRONMENT') == 'production':
            raise ValueError('JWT_SECRET_KEY is required in production')
        return v

    def is_fi_mcp_configured(self) -> bool:
        """Check if Fi Money MCP is properly configured"""
        return bool(self.FI_MCP_BASE_URL and self.FI_MCP_API_KEY)

    def is_google_cloud_configured(self) -> bool:
        """Check if Google Cloud is properly configured"""
        return bool(self.GOOGLE_CLOUD_PROJECT)

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    try:
        return Settings()
    except Exception as e:
        print(f"Warning: Failed to load some configuration values: {e}")
        print("The application will continue with available configuration.")
        # Create a minimal settings instance for development
        return Settings(
            GOOGLE_CLOUD_PROJECT="development-placeholder",
            JWT_SECRET_KEY="development-secret-key-not-for-production",
            FI_MCP_BASE_URL=None,
            FI_MCP_API_KEY=None
        )
