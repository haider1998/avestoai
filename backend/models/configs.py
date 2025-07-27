# backend/models/configs.py
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any
import os
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Google Cloud
    GOOGLE_CLOUD_PROJECT: str = "avestoai-466417"  # Default value as fallback
    VERTEX_AI_LOCATION: str = "us-central1"
    FIRESTORE_DATABASE: str = "(default)"

    # Fi Money MCP Configuration
    FI_MCP_BASE_URL: str = "https://fi-mcp-dev-172306289913.asia-south1.run.app"
    FI_MCP_TIMEOUT: int = 30
    FI_MCP_MAX_RETRIES: int = 3
    FI_MCP_DEFAULT_SCENARIO: str = "balanced"

    # Fi MCP Test Scenarios
    FI_MCP_SCENARIOS: Dict[str, str] = {
        "no_assets": "1111111111",
        "all_assets_large": "2222222222",
        "all_assets_small": "3333333333",
        "multiple_accounts": "4444444444",
        "no_credit": "5555555555",
        "no_bank": "6666666666",
        "debt_heavy": "7777777777",
        "sip_investor": "8888888888",
        "fixed_income": "9999999999",
        "gold_investor": "1010101010",
        "epf_dormant": "1212121212",
        "salary_sink": "1414141414",
        "balanced": "1313131313",
        "starter": "2020202020",
        "dual_income": "2121212121",
        "high_spender": "2525252525"
    }

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
    RATE_LIMIT_PERIOD: int = 60

    # Caching
    CACHE_TTL: int = 300
    REDIS_URL: Optional[str] = None

    # Monitoring
    ENABLE_METRICS: bool = True
    LOG_LEVEL: str = "INFO"

    # ElevenLabs Configuration
    ELEVENLABS_API_KEY: str = "sk_696265e68daa7c9e67c4fc09c476d236376e72bb46246219"
    ELEVENLABS_DEFAULT_VOICE: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
    OPENAI_API_KEY: str = "sk-dummy-openai-api-key-for-whisper-stt"  # For Whisper STT

    # Feature Flags
    ENABLE_PREDICTIVE_ANALYSIS: bool = True
    ENABLE_REAL_TIME_STREAMING: bool = True
    ENABLE_ADVANCED_CHARTS: bool = True
    ENABLE_FI_MCP_INTEGRATION: bool = True
    ENABLE_VOICE_CONVERSATIONS: bool = True

    class Config:
        # Look for .env file in the project root (one level up from this file)
        env_file = Path(__file__).parent.parent / ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
