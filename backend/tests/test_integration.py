# tests/test_integration.py
import pytest
import httpx
import asyncio


@pytest.mark.asyncio
async def test_complete_user_journey():
    """Test complete user journey from registration to analysis"""

    async with httpx.AsyncClient() as client:
        # 1. Register user
        register_response = await client.post(
            "http://localhost:8080/api/v1/auth/register",
            json={
                "email": "integration@test.com",
                "password": "testpass123",
                "name": "Integration Test User",
                "annual_income": 1200000
            }
        )

        assert register_response.status_code == 200
        auth_data = register_response.json()
        token = auth_data["access_token"]

        # 2. Test dashboard
        dashboard_response = await client.get(
            f"http://localhost:8080/api/v1/financial-dashboard/{auth_data['user']['user_id']}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert dashboard_response.status_code == 200

        # 3. Test opportunity analysis
        opportunities_response = await client.post(
            "http://localhost:8080/api/v1/analyze-opportunities",
            headers={"Authorization": f"Bearer {token}"},
            json={"analysis_type": "comprehensive"}
        )

        assert opportunities_response.status_code == 200
        opportunities = opportunities_response.json()
        assert "opportunities" in opportunities

        # 4. Test decision scoring
        decision_response = await client.post(
            "http://localhost:8080/api/v1/predict-decision",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": 50000,
                "category": "electronics",
                "description": "Laptop purchase"
            }
        )

        assert decision_response.status_code == 200
        decision = decision_response.json()
        assert "score" in decision
        assert 0 <= decision["score"] <= 100
