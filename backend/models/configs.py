# backend/models/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


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

    # External APIs
    FI_MCP_ENDPOINT: Optional[str] = None
    FI_MCP_API_KEY: Optional[str] = None

    # On-Device AI
    LOCAL_MODEL_NAME: str = "gemma:2b"
    OLLAMA_ENDPOINT: str = "http://localhost:11434"

    # Security
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8001", "http://localhost:8002"]

    # Performance
    MAX_CONCURRENT_REQUESTS: int = 100
    REQUEST_TIMEOUT_SECONDS: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


# Singleton instance
settings = Settings()
