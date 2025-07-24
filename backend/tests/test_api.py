# backend/tests/test_api.py
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "🔮 AvestoAI API"
    assert data["status"] == "operational"


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code in [200, 503]  # Might be unhealthy in test environment


@patch('main.vertex_client')
@patch('main.firestore_client')
@patch('main.opportunity_engine')
def test_analyze_opportunities(mock_opportunity_engine, mock_firestore, mock_vertex, client, auth_headers,
                               sample_user_data):
    """Test opportunity analysis endpoint"""

    # Mock the services
    mock_firestore.get_user_data = AsyncMock(return_value=sample_user_data)
    mock_opportunity_engine.generate_opportunities = AsyncMock(return_value={
        "opportunities": [
            {
                "id": "test_opp_1",
                "type": "savings_optimization",
                "title": "Test Opportunity",
                "potential_annual_value": 10000
            }
        ],
        "total_annual_value": 10000,
        "processing_time": 1.5,
        "confidence_score": 0.8
    })

    # Test request
    request_data = {
        "user_id": "test_user_123",
        "analysis_type": "comprehensive"
    }

    response = client.post(
        "/api/v1/analyze-opportunities",
        json=request_data,
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "opportunities" in data
    assert data["total_annual_value"] == 10000


def test_predict_decision(client, auth_headers):
    """Test decision prediction endpoint"""

    request_data = {
        "user_id": "test_user_123",
        "amount": 50000,
        "category": "electronics",
        "description": "Laptop purchase",
        "user_context": {"income": 1200000, "savings": 180000}
    }

    with patch('main.on_device_ai') as mock_ai, \
            patch('main.vertex_client') as mock_vertex:
        mock_ai.quick_decision_score = AsyncMock(return_value={"score": 65})
        mock_vertex.deep_decision_analysis = AsyncMock(return_value={
            "score": 67,
            "explanation": "Test explanation",
            "alternatives": [],
            "projections": {}
        })

        response = client.post(
            "/api/v1/predict-decision",
            json=request_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert data["score"] >= 0 and data["score"] <= 100


def test_chat_endpoint(client, auth_headers):
    """Test chat endpoint"""

    request_data = {
        "user_id": "test_user_123",
        "message": "What's my net worth?",
        "conversation_history": []
    }

    with patch('main.firestore_client') as mock_firestore, \
            patch('main.on_device_ai') as mock_ai, \
            patch('main.vertex_client') as mock_vertex:
        mock_firestore.get_user_data = AsyncMock(return_value=sample_user_data)
        mock_ai.should_process_locally = AsyncMock(return_value=True)
        mock_ai.generate_local_response = AsyncMock(return_value={
            "response": "Your net worth is ₹6,05,000",
            "suggestions": ["How can I improve it?"],
            "confidence": 0.9
        })

        response = client.post(
            "/api/v1/chat",
            json=request_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "net worth" in data["response"].lower()


def test_invalid_decision_amount(client, auth_headers):
    """Test validation for invalid decision amounts"""

    request_data = {
        "user_id": "test_user_123",
        "amount": -1000,  # Invalid negative amount
        "category": "electronics",
        "description": "Invalid purchase",
        "user_context": {}
    }

    response = client.post(
        "/api/v1/predict-decision",
        json=request_data,
        headers=auth_headers
    )

    assert response.status_code == 422  # Validation error


def test_unauthorized_access(client):
    """Test unauthorized access"""

    request_data = {
        "user_id": "test_user_123",
        "analysis_type": "comprehensive"
    }

    response = client.post(
        "/api/v1/analyze-opportunities",
        json=request_data
        # No auth headers
    )

    assert response.status_code == 403  # Forbidden
