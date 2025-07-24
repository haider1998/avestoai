# backend/tests/conftest.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.main import app
from backend.models.configs import Settings

# Override settings for testing
test_settings = Settings(
    ENVIRONMENT="testing",
    GOOGLE_CLOUD_PROJECT="test-project",
    JWT_SECRET_KEY="test-secret-key",
    DEBUG=True
)

@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)

@pytest.fixture
def mock_vertex_client():
    """Mock Vertex AI client"""
    mock = AsyncMock()
    mock.health_check.return_value = {"status": "healthy"}
    mock.analyze_market_opportunities.return_value = {
        "market_opportunities": [],
        "ai_confidence": 0.8
    }
    return mock

@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client"""
    mock = AsyncMock()
    mock.health_check.return_value = {"status": "healthy"}
    mock.get_user_data.return_value = {
        "user_id": "test_user",
        "accounts": {"savings": 100000},
        "investments": {"mutual_funds": 50000}
    }
    return mock

@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "user_id": "test_user_123",
        "profile": {
            "age": 28,
            "income": 1200000,
            "city": "Bangalore",
            "risk_tolerance": "moderate"
        },
        "accounts": {
            "savings": 180000,
            "checking": 25000,
            "credit_used": 45000,
            "credit_limit": 200000
        },
        "investments": {
            "mutual_funds": 350000,
            "stocks": 120000,
            "ppf": 150000
        }
    }

@pytest.fixture
def auth_headers():
    """Authentication headers for testing"""
    # In real implementation, generate valid JWT
    return {"Authorization": "Bearer test-token"}
