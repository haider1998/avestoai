# backend/services/fi_mcp_service.py
import httpx
import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.models.configs import Settings

logger = structlog.get_logger()


class FiMCPService:
    """Service to interact with Fi Money MCP server for financial data"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.FI_MCP_BASE_URL
        self.api_key = settings.FI_MCP_API_KEY
        self.timeout = settings.FI_MCP_TIMEOUT
        self.max_retries = settings.FI_MCP_MAX_RETRIES

        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "AvestoAI/1.0"
            }
        )

        logger.info("✅ Fi MCP service initialized", base_url=self.base_url)

    async def health_check(self) -> Dict[str, Any]:
        """Check Fi MCP service health"""
        try:
            start_time = datetime.now()
            response = await self.client.get(f"{self.base_url}/health")
            response_time = (datetime.now() - start_time).total_seconds() * 1000

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "response_time": response_time,
                    "last_check": datetime.now()
                }
            else:
                return {
                    "status": "unhealthy",
                    "response_time": response_time,
                    "last_check": datetime.now(),
                    "error": f"HTTP {response.status_code}"
                }

        except Exception as e:
            logger.error("❌ Fi MCP health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "last_check": datetime.now(),
                "error": str(e)
            }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_user_financial_data(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive financial data for a user"""
        try:
            logger.info("📊 Fetching user financial data from Fi MCP", user_id=user_id)

            # Make request to Fi MCP server
            response = await self.client.post(
                f"{self.base_url}/api/v1/users/{user_id}/financial-data",
                json={
                    "include_accounts": True,
                    "include_transactions": True,
                    "include_investments": True,
                    "include_goals": True,
                    "include_insights": True,
                    "date_range": {
                        "start": (datetime.now() - timedelta(days=90)).isoformat(),
                        "end": datetime.now().isoformat()
                    }
                }
            )

            response.raise_for_status()
            data = response.json()

            logger.info("✅ Financial data fetched successfully",
                        user_id=user_id,
                        accounts_count=len(data.get("accounts", [])),
                        transactions_count=len(data.get("transactions", [])))

            return data

        except httpx.HTTPStatusError as e:
            logger.error("❌ Fi MCP API error",
                         user_id=user_id,
                         status_code=e.response.status_code,
                         error=str(e))
            # Return demo data for development
            return self._get_demo_financial_data(user_id)

        except Exception as e:
            logger.error("❌ Failed to fetch financial data",
                         user_id=user_id,
                         error=str(e))
            # Return demo data for development
            return self._get_demo_financial_data(user_id)

    async def get_current_financial_state(self, user_id: str) -> Dict[str, Any]:
        """Get current financial state for decision analysis"""
        try:
            logger.info("💰 Fetching current financial state", user_id=user_id)

            response = await self.client.get(
                f"{self.base_url}/api/v1/users/{user_id}/current-state"
            )

            response.raise_for_status()
            data = response.json()

            # Calculate derived metrics
            current_state = {
                **data,
                "net_worth": self._calculate_net_worth(data),
                "debt_to_income_ratio": self._calculate_debt_ratio(data),
                "emergency_fund_months": self._calculate_emergency_fund_coverage(data),
                "investment_allocation": self._calculate_investment_allocation(data)
            }

            logger.info("✅ Current financial state calculated", user_id=user_id)
            return current_state

        except Exception as e:
            logger.error("❌ Failed to get current financial state",
                         user_id=user_id,
                         error=str(e))
            return self._get_demo_current_state(user_id)

    async def get_comprehensive_financial_data(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive financial data for dashboard"""
        try:
            logger.info("📈 Fetching comprehensive financial data", user_id=user_id)

            # Fetch multiple data sources in parallel
            tasks = [
                self.get_user_financial_data(user_id),
                self._get_market_data(),
                self._get_user_preferences(user_id),
                self._get_financial_goals(user_id)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Combine results
            financial_data = results[0] if not isinstance(results[0], Exception) else {}
            market_data = results[1] if not isinstance(results[1], Exception) else {}
            preferences = results[2] if not isinstance(results[2], Exception) else {}
            goals = results[3] if not isinstance(results[3], Exception) else {}

            comprehensive_data = {
                **financial_data,
                "market_context": market_data,
                "user_preferences": preferences,
                "financial_goals": goals,
                "summary": self._generate_financial_summary(financial_data),
                "charts": self._generate_chart_data(financial_data)
            }

            logger.info("✅ Comprehensive data compiled", user_id=user_id)
            return comprehensive_data

        except Exception as e:
            logger.error("❌ Failed to get comprehensive data",
                         user_id=user_id,
                         error=str(e))
            return self._get_demo_comprehensive_data(user_id)

    async def get_real_time_data(self, user_id: str) -> Dict[str, Any]:
        """Get real-time financial data for streaming"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/users/{user_id}/real-time"
            )

            response.raise_for_status()
            data = response.json()

            # Add real-time calculations
            real_time_data = {
                **data,
                "timestamp": datetime.now().isoformat(),
                "net_worth": self._calculate_net_worth(data),
                "cash_flow": self._calculate_cash_flow(data),
                "spending_velocity": self._calculate_spending_velocity(data)
            }

            return real_time_data

        except Exception as e:
            logger.error("❌ Failed to get real-time data",
                         user_id=user_id,
                         error=str(e))
            return self._get_demo_real_time_data(user_id)

    async def get_user_context_for_chat(self, user_id: str) -> Dict[str, Any]:
        """Get user context optimized for chat interactions"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/users/{user_id}/context"
            )

            response.raise_for_status()
            data = response.json()

            # Create chat-optimized context
            chat_context = {
                "current_balance": data.get("accounts", {}).get("total_balance", 0),
                "monthly_income": data.get("income", {}).get("monthly", 0),
                "monthly_expenses": data.get("expenses", {}).get("monthly", 0),
                "investment_value": data.get("investments", {}).get("total_value", 0),
                "debt_amount": data.get("debt", {}).get("total", 0),
                "financial_goals": data.get("goals", {}),
                "risk_profile": data.get("profile", {}).get("risk_tolerance", "moderate"),
                "recent_transactions": data.get("recent_transactions", [])[:5]
            }

            return chat_context

        except Exception as e:
            logger.error("❌ Failed to get chat context",
                         user_id=user_id,
                         error=str(e))
            return self._get_demo_chat_context(user_id)

    # Private helper methods
    def _calculate_net_worth(self, data: Dict[str, Any]) -> float:
        """Calculate net worth from financial data"""
        assets = sum(account.get("balance", 0) for account in data.get("accounts", []))
        investments = sum(inv.get("current_value", 0) for inv in data.get("investments", []))
        debt = sum(debt_item.get("balance", 0) for debt_item in data.get("debt", []))

        return assets + investments - debt

    def _calculate_debt_ratio(self, data: Dict[str, Any]) -> float:
        """Calculate debt-to-income ratio"""
        total_debt = sum(debt_item.get("balance", 0) for debt_item in data.get("debt", []))
        monthly_income = data.get("income", {}).get("monthly", 1)

        return (total_debt / (monthly_income * 12)) if monthly_income > 0 else 0

    def _calculate_emergency_fund_coverage(self, data: Dict[str, Any]) -> float:
        """Calculate emergency fund coverage in months"""
        emergency_fund = data.get("accounts", {}).get("savings", 0)
        monthly_expenses = data.get("expenses", {}).get("monthly", 1)

        return emergency_fund / monthly_expenses if monthly_expenses > 0 else 0

    def _calculate_investment_allocation(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate investment allocation percentages"""
        investments = data.get("investments", [])
        total_value = sum(inv.get("current_value", 0) for inv in investments)

        if total_value == 0:
            return {}

        allocation = {}
        for investment in investments:
            category = investment.get("category", "other")
            value = investment.get("current_value", 0)
            allocation[category] = allocation.get(category, 0) + (value / total_value * 100)

        return allocation

    def _calculate_cash_flow(self, data: Dict[str, Any]) -> float:
        """Calculate monthly cash flow"""
        income = data.get("income", {}).get("monthly", 0)
        expenses = data.get("expenses", {}).get("monthly", 0)
        return income - expenses

    def _calculate_spending_velocity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate spending velocity and trends"""
        transactions = data.get("recent_transactions", [])

        if not transactions:
            return {"velocity": 0, "trend": "stable"}

        # Calculate spending in last 7 days vs previous 7 days
        now = datetime.now()
        last_7_days = [t for t in transactions if (now - datetime.fromisoformat(t.get("date", ""))).days <= 7]
        prev_7_days = [t for t in transactions if 7 < (now - datetime.fromisoformat(t.get("date", ""))).days <= 14]

        last_week_spending = sum(abs(t.get("amount", 0)) for t in last_7_days if t.get("amount", 0) < 0)
        prev_week_spending = sum(abs(t.get("amount", 0)) for t in prev_7_days if t.get("amount", 0) < 0)

        if prev_week_spending == 0:
            velocity = 0
            trend = "stable"
        else:
            velocity = ((last_week_spending - prev_week_spending) / prev_week_spending) * 100
            trend = "increasing" if velocity > 10 else "decreasing" if velocity < -10 else "stable"

        return {
            "velocity": velocity,
            "trend": trend,
            "last_week_spending": last_week_spending,
            "prev_week_spending": prev_week_spending
        }

    async def _get_market_data(self) -> Dict[str, Any]:
        """Get current market data"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/market/current")
            response.raise_for_status()
            return response.json()
        except:
            return {
                "indices": {"nifty50": 19500, "sensex": 65000},
                "interest_rates": {"fd": 6.5, "savings": 3.5},
                "inflation": 4.2
            }

    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/users/{user_id}/preferences")
            response.raise_for_status()
            return response.json()
        except:
            return {"risk_tolerance": "moderate", "investment_horizon": "long_term"}

    async def _get_financial_goals(self, user_id: str) -> Dict[str, Any]:
        """Get user financial goals"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/users/{user_id}/goals")
            response.raise_for_status()
            return response.json()
        except:
            return {
                "emergency_fund": {"target": 600000, "current": 180000},
                "house_purchase": {"target": 2000000, "current": 450000},
                "retirement": {"target": 50000000, "current": 1200000}
            }

    def _generate_financial_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate financial summary from raw data"""
        return {
            "net_worth": self._calculate_net_worth(data),
            "liquid_assets": sum(acc.get("balance", 0) for acc in data.get("accounts", [])),
            "investments": sum(inv.get("current_value", 0) for inv in data.get("investments", [])),
            "debt": sum(debt.get("balance", 0) for debt in data.get("debt", [])),
            "monthly_income": data.get("income", {}).get("monthly", 0),
            "monthly_expenses": data.get("expenses", {}).get("monthly", 0),
            "emergency_fund_months": self._calculate_emergency_fund_coverage(data)
        }

    def _generate_chart_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate chart data for dashboard"""
        charts = []

        # Net worth trend chart
        charts.append({
            "type": "line",
            "title": "Net Worth Trend",
            "data": data.get("net_worth_history", []),
            "config": {"timeframe": "6_months"}
        })

        # Expense breakdown chart
        expense_categories = {}
        for transaction in data.get("transactions", []):
            if transaction.get("amount", 0) < 0:
                category = transaction.get("category", "other")
                expense_categories[category] = expense_categories.get(category, 0) + abs(transaction.get("amount", 0))

        charts.append({
            "type": "pie",
            "title": "Expense Breakdown",
            "data": [{"label": k, "value": v} for k, v in expense_categories.items()],
            "config": {"currency": "INR"}
        })

        return charts

    # Demo data methods for development
    def _get_demo_financial_data(self, user_id: str) -> Dict[str, Any]:
        """Generate demo financial data for development"""
        return {
            "user_id": user_id,
            "accounts": [
                {"id": "acc1", "type": "savings", "balance": 250000, "bank": "Fi Money"},
                {"id": "acc2", "type": "checking", "balance": 45000, "bank": "HDFC"}
            ],
            "investments": [
                {"id": "inv1", "type": "mutual_fund", "current_value": 450000, "category": "equity"},
                {"id": "inv2", "type": "stocks", "current_value": 180000, "category": "equity"}
            ],
            "debt": [
                {"id": "debt1", "type": "credit_card", "balance": 35000, "interest_rate": 24.0}
            ],
            "transactions": self._generate_demo_transactions(user_id),
            "income": {"monthly": 120000, "annual": 1440000},
            "expenses": {"monthly": 75000, "annual": 900000}
        }

    def _generate_demo_transactions(self, user_id: str) -> List[Dict[str, Any]]:
        """Generate demo transactions"""
        import random
        transactions = []

        for i in range(50):
            date = datetime.now() - timedelta(days=random.randint(1, 90))

            # Income transactions
            if random.random() < 0.1:  # 10% chance of income
                transactions.append({
                    "id": f"txn_{i}",
                    "date": date.isoformat(),
                    "amount": random.randint(100000, 150000),
                    "category": "salary",
                    "description": "Monthly Salary",
                    "account_id": "acc1"
                })
            else:  # Expense transactions
                categories = ["food", "transport", "entertainment", "shopping", "utilities", "healthcare"]
                category = random.choice(categories)
                amount = -random.randint(500, 15000)

                transactions.append({
                    "id": f"txn_{i}",
                    "date": date.isoformat(),
                    "amount": amount,
                    "category": category,
                    "description": f"{category.title()} expense",
                    "account_id": "acc2"
                })

        return sorted(transactions, key=lambda x: x["date"], reverse=True)

    def _get_demo_current_state(self, user_id: str) -> Dict[str, Any]:
        """Demo current state data"""
        return {
            "net_worth": 840000,
            "liquid_assets": 295000,
            "debt_to_income_ratio": 0.35,
            "emergency_fund_months": 3.3,
            "investment_allocation": {"equity": 70, "debt": 20, "gold": 10}
        }

    def _get_demo_comprehensive_data(self, user_id: str) -> Dict[str, Any]:
        """Demo comprehensive data"""
        financial_data = self._get_demo_financial_data(user_id)
        return {
            **financial_data,
            "summary": self._generate_financial_summary(financial_data),
            "charts": self._generate_chart_data(financial_data),
            "market_context": {"nifty50": 19500, "interest_rates": {"fd": 6.5}},
            "user_preferences": {"risk_tolerance": "moderate"},
            "financial_goals": {
                "emergency_fund": {"target": 600000, "current": 295000},
                "house_purchase": {"target": 2000000, "current": 840000}
            }
        }

    def _get_demo_real_time_data(self, user_id: str) -> Dict[str, Any]:
        """Demo real-time data"""
        return {
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "net_worth": 840000,
            "cash_flow": 45000,
            "spending_velocity": {"velocity": 15.2, "trend": "increasing"},
            "recent_transactions": self._generate_demo_transactions(user_id)[:5]
        }

    def _get_demo_chat_context(self, user_id: str) -> Dict[str, Any]:
        """Demo chat context"""
        return {
            "current_balance": 295000,
            "monthly_income": 120000,
            "monthly_expenses": 75000,
            "investment_value": 630000,
            "debt_amount": 35000,
            "financial_goals": {
                "emergency_fund": {"target": 600000, "current": 295000}
            },
            "risk_profile": "moderate"
        }

    async def cleanup(self):
        """Cleanup resources"""
        await self.client.aclose()
        logger.info("🧹 Fi MCP service cleaned up")
