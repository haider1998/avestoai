# backend/services/fi_mcp_service.py
import httpx
import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.models.configs import Settings
import urllib.parse

logger = structlog.get_logger()


class FiMCPService:
    """Service to interact with Fi Money MCP server with proper authentication"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.FI_MCP_BASE_URL
        self.timeout = settings.FI_MCP_TIMEOUT
        self.max_retries = settings.FI_MCP_MAX_RETRIES

        # Session management
        self.active_sessions = {}  # mobile_number -> session_data

        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AvestoAI/1.0"
            }
        )

        # Test phone numbers for different scenarios
        self.test_scenarios = {
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

        logger.info("✅ Fi MCP service initialized")

    async def health_check(self) -> Dict[str, Any]:
        """Check Fi MCP service health"""
        try:
            start_time = datetime.now()

            # Test basic connectivity
            response = await self.client.get(f"{self.base_url}/")
            response_time = (datetime.now() - start_time).total_seconds() * 1000

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "response_time": response_time,
                    "last_check": datetime.now(),
                    "active_sessions": len(self.active_sessions)
                }
            else:
                return {
                    "status": "degraded",
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

    async def initiate_session(self, mobile_number: str, scenario: str = "balanced") -> Dict[str, Any]:
        """Initiate Fi MCP session for a mobile number"""
        try:
            logger.info("🔐 Initiating Fi MCP session", mobile_number=mobile_number, scenario=scenario)

            # Generate session ID
            session_id = f"mcp-session-{uuid.uuid4()}"

            # Map scenario to test phone number
            test_phone = self.test_scenarios.get(scenario, "1313131313")

            # Store session data
            session_data = {
                "session_id": session_id,
                "mobile_number": mobile_number,
                "test_phone": test_phone,
                "scenario": scenario,
                "is_authenticated": False,
                "created_at": datetime.now(),
                "last_activity": datetime.now(),
                "login_url": None
            }

            # Try making a test call to get login URL if needed
            try:
                test_response = await self._make_mcp_call(session_id, "fetch_net_worth", {})

                if test_response.get("error") and "login_url" in str(test_response.get("error", {})):
                    # Extract login URL from error
                    error_data = test_response.get("error", {})
                    if isinstance(error_data, dict) and "data" in error_data:
                        login_url = error_data["data"].get("login_url")
                        session_data["login_url"] = login_url
                        session_data["requires_authentication"] = True
                    else:
                        session_data["requires_authentication"] = True
                else:
                    # Already authenticated or no auth required
                    session_data["is_authenticated"] = True
                    session_data["requires_authentication"] = False

            except Exception as e:
                # Assume authentication required
                session_data["requires_authentication"] = True
                logger.info("Test call failed, assuming auth required", error=str(e))

            # Store session
            self.active_sessions[mobile_number] = session_data

            return {
                "session_id": session_id,
                "login_url": session_data.get("login_url"),
                "requires_authentication": session_data["requires_authentication"]
            }

        except Exception as e:
            logger.error("❌ Failed to initiate Fi MCP session", error=str(e))
            raise

    async def verify_authentication(self, session_id: str, mobile_number: str, otp: str) -> Dict[str, Any]:
        """Verify Fi MCP authentication with OTP"""
        try:
            logger.info("🔐 Verifying Fi MCP authentication", mobile_number=mobile_number)

            session_data = self.active_sessions.get(mobile_number)
            if not session_data or session_data["session_id"] != session_id:
                return {"success": False, "message": "Invalid session"}

            login_url = session_data.get("login_url")
            if not login_url:
                return {"success": False, "message": "No login URL available"}

            # Simulate login process
            login_data = {
                "phone": session_data["test_phone"],
                "otp": otp  # Any OTP works in dev server
            }

            try:
                async with httpx.AsyncClient() as login_client:
                    login_response = await login_client.post(
                        login_url,
                        data=login_data,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        follow_redirects=True
                    )

                    if login_response.status_code == 200:
                        # Update session
                        session_data["is_authenticated"] = True
                        session_data["last_activity"] = datetime.now()

                        logger.info("✅ Fi MCP authentication successful", mobile_number=mobile_number)

                        return {
                            "success": True,
                            "message": "Authentication successful",
                            "scenario": session_data["scenario"]
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"Authentication failed: HTTP {login_response.status_code}"
                        }

            except Exception as login_error:
                logger.error("❌ Login request failed", error=str(login_error))
                return {"success": False, "message": f"Login failed: {str(login_error)}"}

        except Exception as e:
            logger.error("❌ Fi MCP authentication verification failed", error=str(e))
            return {"success": False, "message": str(e)}

    async def get_authentication_status(self, mobile_number: str) -> Dict[str, Any]:
        """Get authentication status for a mobile number"""
        session_data = self.active_sessions.get(mobile_number)

        if not session_data:
            return {
                "is_authenticated": False,
                "session_id": None,
                "scenario": None,
                "last_activity": None
            }

        # Check if session is expired (4 hours)
        if datetime.now() - session_data["last_activity"] > timedelta(hours=4):
            # Session expired
            del self.active_sessions[mobile_number]
            return {
                "is_authenticated": False,
                "session_id": None,
                "scenario": None,
                "last_activity": None
            }

        return {
            "is_authenticated": session_data["is_authenticated"],
            "session_id": session_data["session_id"],
            "scenario": session_data.get("scenario"),
            "last_activity": session_data["last_activity"]
        }

    async def switch_scenario(self, mobile_number: str, new_scenario: str) -> Dict[str, Any]:
        """Switch Fi MCP scenario for a user"""
        try:
            session_data = self.active_sessions.get(mobile_number)
            if not session_data:
                return {"success": False, "message": "No active session"}

            # Update scenario and test phone
            old_scenario = session_data.get("scenario", "balanced")
            session_data["scenario"] = new_scenario
            session_data["test_phone"] = self.test_scenarios.get(new_scenario, "1313131313")
            session_data["last_activity"] = datetime.now()

            # May need to re-authenticate with new phone number
            session_data["is_authenticated"] = False

            # Try to authenticate automatically
            await self.verify_authentication(
                session_data["session_id"],
                mobile_number,
                "123456"  # Default OTP
            )

            logger.info("✅ Scenario switched successfully",
                        mobile_number=mobile_number,
                        old_scenario=old_scenario,
                        new_scenario=new_scenario)

            return {"success": True, "scenario": new_scenario}

        except Exception as e:
            logger.error("❌ Failed to switch scenario", error=str(e))
            return {"success": False, "message": str(e)}

    async def get_user_financial_data(self, mobile_number: str, scenario: str = None) -> Dict[str, Any]:
        """Get comprehensive financial data for a user"""
        try:
            logger.info("📊 Fetching comprehensive financial data", mobile_number=mobile_number)

            # Check authentication
            auth_status = await self.get_authentication_status(mobile_number)
            if not auth_status["is_authenticated"]:
                raise Exception("Authentication required")

            session_data = self.active_sessions[mobile_number]
            session_id = session_data["session_id"]

            # Update last activity
            session_data["last_activity"] = datetime.now()

            # Fetch all financial data in parallel
            tasks = [
                self._fetch_net_worth(session_id),
                self._fetch_credit_report(session_id),
                self._fetch_epf_details(session_id),
                self._fetch_mf_transactions(session_id),
                self._fetch_bank_transactions(session_id),
                self._fetch_stock_transactions(session_id)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            net_worth_data = results[0] if not isinstance(results[0], Exception) else {}
            credit_data = results[1] if not isinstance(results[1], Exception) else {}
            epf_data = results[2] if not isinstance(results[2], Exception) else {}
            mf_data = results[3] if not isinstance(results[3], Exception) else {}
            bank_data = results[4] if not isinstance(results[4], Exception) else {}
            stock_data = results[5] if not isinstance(results[5], Exception) else {}

            # Combine and structure the data
            comprehensive_data = {
                "mobile_number": mobile_number,
                "scenario": session_data.get("scenario", "balanced"),
                "net_worth": net_worth_data,
                "credit_report": credit_data,
                "epf_details": epf_data,
                "mutual_funds": mf_data,
                "bank_transactions": bank_data,
                "stock_transactions": stock_data,
                "accounts": self._parse_accounts_data(net_worth_data),
                "investments": self._parse_investments_data(net_worth_data, mf_data, stock_data),
                "debt": self._parse_debt_data(net_worth_data, credit_data),
                "transactions": self._parse_all_transactions(bank_data, mf_data, stock_data),
                "income": self._calculate_income_data(bank_data),
                "expenses": self._calculate_expenses_data(bank_data),
                "summary": self._generate_financial_summary(net_worth_data, bank_data),
                "last_updated": datetime.now().isoformat()
            }

            logger.info("✅ Comprehensive financial data fetched successfully",
                        mobile_number=mobile_number,
                        net_worth=comprehensive_data.get("net_worth", {}).get("total_value", 0))

            return comprehensive_data

        except Exception as e:
            logger.error("❌ Failed to fetch comprehensive financial data",
                         mobile_number=mobile_number, error=str(e))
            # Return demo data as fallback
            return self._get_demo_comprehensive_data(mobile_number)

    async def _make_mcp_call(self, session_id: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make MCP protocol call to Fi server"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": method,
                    "arguments": params
                }
            }

            headers = {
                "Content-Type": "application/json",
                "Mcp-Session-Id": session_id
            }

            response = await self.client.post(
                f"{self.base_url}/mcp/stream",
                json=payload,
                headers=headers
            )

            response.raise_for_status()
            result = response.json()

            return result

        except Exception as e:
            logger.error(f"❌ MCP call failed: {method}", error=str(e))
            raise

    async def _fetch_net_worth(self, session_id: str) -> Dict[str, Any]:
        """Fetch net worth data from Fi MCP"""
        try:
            response = await self._make_mcp_call(session_id, "fetch_net_worth", {})

            if response.get("result"):
                net_worth_response = response["result"].get("netWorthResponse", {})

                # Parse asset values
                assets = {}
                total_assets = 0
                for asset in net_worth_response.get("assetValues", []):
                    asset_type = asset.get("netWorthAttribute", "")
                    value_data = asset.get("value", {})
                    amount = self._parse_currency_value(value_data)
                    assets[asset_type] = amount
                    total_assets += amount

                # Parse liability values
                liabilities = {}
                total_liabilities = 0
                for liability in net_worth_response.get("liabilityValues", []):
                    liability_type = liability.get("netWorthAttribute", "")
                    value_data = liability.get("value", {})
                    amount = self._parse_currency_value(value_data)
                    liabilities[liability_type] = amount
                    total_liabilities += amount

                # Total net worth
                total_net_worth_data = net_worth_response.get("totalNetWorthValue", {})
                total_net_worth = self._parse_currency_value(total_net_worth_data)

                return {
                    "assets": assets,
                    "liabilities": liabilities,
                    "total_assets": total_assets,
                    "total_liabilities": total_liabilities,
                    "total_value": total_net_worth,
                    "raw_response": net_worth_response
                }

            return {}

        except Exception as e:
            logger.error("❌ Failed to fetch net worth", error=str(e))
            return {}

    # Include all the other _fetch methods from previous implementation
    # (keeping them the same as they work correctly)

    def _parse_currency_value(self, value_data: Dict[str, Any]) -> float:
        """Parse Fi MCP currency value format"""
        if not value_data:
            return 0.0

        units = float(value_data.get("units", "0"))
        nanos = value_data.get("nanos", 0)

        return units + (nanos / 1_000_000_000)

    # Keep all other helper methods from previous implementation
    # ... (all the parsing and calculation methods remain the same)

    async def get_current_financial_state(self, mobile_number: str) -> Dict[str, Any]:
        """Get current financial state for decision analysis"""
        try:
            # Get full financial data
            financial_data = await self.get_user_financial_data(mobile_number)

            net_worth_data = financial_data.get("net_worth", {})

            return {
                "net_worth": net_worth_data.get("total_value", 0),
                "liquid_assets": sum(acc.get("balance", 0) for acc in financial_data.get("accounts", [])),
                "total_investments": sum(inv.get("current_value", 0) for inv in financial_data.get("investments", [])),
                "total_debt": sum(debt.get("balance", 0) for debt in financial_data.get("debt", [])),
                "monthly_income": financial_data.get("income", {}).get("monthly", 0),
                "monthly_expenses": financial_data.get("expenses", {}).get("monthly", 0),
                "emergency_fund_months": self._calculate_emergency_fund_months(financial_data)
            }

        except Exception as e:
            logger.error("❌ Failed to get current financial state", mobile_number=mobile_number, error=str(e))
            return {"net_worth": 0, "monthly_income": 0}

    def _calculate_emergency_fund_months(self, financial_data: Dict[str, Any]) -> float:
        """Calculate emergency fund coverage in months"""
        liquid_assets = sum(acc.get("balance", 0) for acc in financial_data.get("accounts", []))
        monthly_expenses = financial_data.get("expenses", {}).get("monthly", 1)

        return liquid_assets / monthly_expenses if monthly_expenses > 0 else 0

    def _generate_financial_summary(self, net_worth_data: Dict[str, Any], bank_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate financial summary"""
        assets = net_worth_data.get("assets", {})
        liabilities = net_worth_data.get("liabilities", {})

        return {
            "net_worth": net_worth_data.get("total_value", 0),
            "liquid_assets": assets.get("ASSET_TYPE_SAVINGS_ACCOUNTS", 0),
            "investments": sum([
                assets.get("ASSET_TYPE_MUTUAL_FUND", 0),
                assets.get("ASSET_TYPE_INDIAN_SECURITIES", 0),
                assets.get("ASSET_TYPE_US_SECURITIES", 0),
                assets.get("ASSET_TYPE_EPF", 0)
            ]),
            "debt": sum(liabilities.values()),
            "monthly_income": bank_data.get("monthly_summary", {}).get("income", 0),
            "monthly_expenses": bank_data.get("monthly_summary", {}).get("expenses", 0),
            "emergency_fund_months": 0  # Calculate based on data
        }

    # Keep other methods for compatibility
    async def get_comprehensive_financial_data(self, mobile_number: str) -> Dict[str, Any]:
        """Alias for get_user_financial_data"""
        return await self.get_user_financial_data(mobile_number)

    async def get_real_time_data(self, mobile_number: str) -> Dict[str, Any]:
        """Get real-time financial data"""
        try:
            financial_data = await self.get_user_financial_data(mobile_number)

            return {
                **financial_data,
                "timestamp": datetime.now().isoformat(),
                "is_real_time": True
            }

        except Exception as e:
            logger.error("❌ Failed to get real-time data", mobile_number=mobile_number, error=str(e))
            return {"timestamp": datetime.now().isoformat(), "error": str(e)}

    async def get_user_context_for_chat(self, mobile_number: str) -> Dict[str, Any]:
        """Get user context optimized for chat"""
        try:
            financial_data = await self.get_user_financial_data(mobile_number)

            return {
                "current_balance": sum(acc.get("balance", 0) for acc in financial_data.get("accounts", [])),
                "monthly_income": financial_data.get("income", {}).get("monthly", 0),
                "monthly_expenses": financial_data.get("expenses", {}).get("monthly", 0),
                "investment_value": sum(inv.get("current_value", 0) for inv in financial_data.get("investments", [])),
                "debt_amount": sum(debt.get("balance", 0) for debt in financial_data.get("debt", [])),
                "net_worth": financial_data.get("net_worth", {}).get("total_value", 0),
                "emergency_fund_months": self._calculate_emergency_fund_months(financial_data),
                "recent_transactions": financial_data.get("transactions", [])[:5]
            }

        except Exception as e:
            logger.error("❌ Failed to get chat context", mobile_number=mobile_number, error=str(e))
            return {"current_balance": 0, "monthly_income": 0}

    def _get_demo_comprehensive_data(self, mobile_number: str) -> Dict[str, Any]:
        """Demo comprehensive data for fallback"""
        return {
            "mobile_number": mobile_number,
            "scenario": "demo",
            "net_worth": {"total_value": 910000},
            "accounts": [{"type": "savings", "balance": 250000}],
            "investments": [{"type": "mutual_fund", "current_value": 450000}],
            "debt": [{"type": "credit_card", "balance": 35000}],
            "transactions": [],
            "income": {"monthly": 120000, "annual": 1440000},
            "expenses": {"monthly": 75000, "annual": 900000},
            "summary": {
                "net_worth": 910000,
                "liquid_assets": 250000,
                "investments": 450000,
                "debt": 35000,
                "monthly_income": 120000,
                "monthly_expenses": 75000
            }
        }

    async def cleanup(self):
        """Cleanup resources"""
        await self.client.aclose()
        self.active_sessions.clear()
        logger.info("🧹 Fi MCP service cleaned up")

    # Add these methods to the FiMCPService class

    async def _fetch_credit_report(self, session_id: str) -> Dict[str, Any]:
        """Fetch credit report data from Fi MCP"""
        try:
            response = await self._make_mcp_call(session_id, "fetch_credit_report", {})

            if response.get("result"):
                return response["result"]
            return {}

        except Exception as e:
            logger.error("❌ Failed to fetch credit report", error=str(e))
            return {}

    async def _fetch_epf_details(self, session_id: str) -> Dict[str, Any]:
        """Fetch EPF details from Fi MCP"""
        try:
            response = await self._make_mcp_call(session_id, "fetch_epf_details", {})

            if response.get("result"):
                return response["result"]
            return {}

        except Exception as e:
            logger.error("❌ Failed to fetch EPF details", error=str(e))
            return {}

    async def _fetch_mf_transactions(self, session_id: str) -> Dict[str, Any]:
        """Fetch mutual fund transactions from Fi MCP"""
        try:
            response = await self._make_mcp_call(session_id, "fetch_mf_transactions", {})

            if response.get("result"):
                return response["result"]
            return {}

        except Exception as e:
            logger.error("❌ Failed to fetch MF transactions", error=str(e))
            return {}

    async def _fetch_bank_transactions(self, session_id: str) -> Dict[str, Any]:
        """Fetch bank transactions from Fi MCP"""
        try:
            response = await self._make_mcp_call(session_id, "fetch_bank_transactions", {})

            if response.get("result"):
                return response["result"]
            return {}

        except Exception as e:
            logger.error("❌ Failed to fetch bank transactions", error=str(e))
            return {}

    async def _fetch_stock_transactions(self, session_id: str) -> Dict[str, Any]:
        """Fetch stock transactions from Fi MCP"""
        try:
            response = await self._make_mcp_call(session_id, "fetch_stock_transactions", {})

            if response.get("result"):
                return response["result"]
            return {}

        except Exception as e:
            logger.error("❌ Failed to fetch stock transactions", error=str(e))
            return {}

    def _parse_accounts_data(self, net_worth_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse accounts from net worth data"""
        accounts = []
        assets = net_worth_data.get("assets", {})

        # Savings accounts
        savings_amount = assets.get("ASSET_TYPE_SAVINGS_ACCOUNTS", 0)
        if savings_amount > 0:
            accounts.append({
                "id": "savings_001",
                "type": "savings",
                "name": "Primary Savings",
                "balance": savings_amount,
                "currency": "INR"
            })

        # Current accounts
        current_amount = assets.get("ASSET_TYPE_CURRENT_ACCOUNTS", 0)
        if current_amount > 0:
            accounts.append({
                "id": "current_001",
                "type": "current",
                "name": "Current Account",
                "balance": current_amount,
                "currency": "INR"
            })

        return accounts

    def _parse_investments_data(self, net_worth_data: Dict[str, Any],
                                mf_data: Dict[str, Any],
                                stock_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse investments from various data sources"""
        investments = []
        assets = net_worth_data.get("assets", {})

        # Mutual funds
        mf_amount = assets.get("ASSET_TYPE_MUTUAL_FUND", 0)
        if mf_amount > 0:
            investments.append({
                "id": "mf_portfolio",
                "type": "mutual_fund",
                "name": "Mutual Fund Portfolio",
                "current_value": mf_amount,
                "currency": "INR"
            })

        # Stocks
        stock_amount = assets.get("ASSET_TYPE_INDIAN_SECURITIES", 0)
        if stock_amount > 0:
            investments.append({
                "id": "stock_portfolio",
                "type": "stocks",
                "name": "Stock Portfolio",
                "current_value": stock_amount,
                "currency": "INR"
            })

        # EPF
        epf_amount = assets.get("ASSET_TYPE_EPF", 0)
        if epf_amount > 0:
            investments.append({
                "id": "epf_account",
                "type": "epf",
                "name": "EPF Account",
                "current_value": epf_amount,
                "currency": "INR"
            })

        return investments

    def _parse_debt_data(self, net_worth_data: Dict[str, Any],
                         credit_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse debt information"""
        debt = []
        liabilities = net_worth_data.get("liabilities", {})

        # Credit card debt
        cc_debt = liabilities.get("LIABILITY_TYPE_CREDIT_CARD", 0)
        if cc_debt > 0:
            debt.append({
                "id": "cc_debt_001",
                "type": "credit_card",
                "name": "Credit Card Debt",
                "balance": cc_debt,
                "interest_rate": 24.0,
                "currency": "INR"
            })

        # Personal loans
        loan_debt = liabilities.get("LIABILITY_TYPE_PERSONAL_LOAN", 0)
        if loan_debt > 0:
            debt.append({
                "id": "loan_001",
                "type": "personal_loan",
                "name": "Personal Loan",
                "balance": loan_debt,
                "interest_rate": 12.0,
                "currency": "INR"
            })

        return debt

    def _parse_all_transactions(self, bank_data: Dict[str, Any],
                                mf_data: Dict[str, Any],
                                stock_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse all transactions from various sources"""
        transactions = []

        # Bank transactions
        bank_transactions = bank_data.get("transactions", [])
        for txn in bank_transactions[:20]:  # Last 20 transactions
            transactions.append({
                "id": txn.get("id", f"bank_{len(transactions)}"),
                "date": txn.get("date", "2024-01-01"),
                "amount": txn.get("amount", 0),
                "description": txn.get("description", "Bank Transaction"),
                "category": txn.get("category", "other"),
                "source": "bank"
            })

        return transactions

    def _calculate_income_data(self, bank_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate income data from transactions"""
        transactions = bank_data.get("transactions", [])

        monthly_income = 0
        income_transactions = [t for t in transactions if t.get("amount", 0) > 0]

        if income_transactions:
            monthly_income = sum(t.get("amount", 0) for t in income_transactions[-30:])

        return {
            "monthly": monthly_income,
            "annual": monthly_income * 12,
            "sources": ["salary", "other"]
        }

    def _calculate_expenses_data(self, bank_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate expense data from transactions"""
        transactions = bank_data.get("transactions", [])

        monthly_expenses = 0
        expense_transactions = [t for t in transactions if t.get("amount", 0) < 0]

        if expense_transactions:
            monthly_expenses = sum(abs(t.get("amount", 0)) for t in expense_transactions[-30:])

        return {
            "monthly": monthly_expenses,
            "annual": monthly_expenses * 12,
            "categories": {"food": 15000, "transport": 8000, "utilities": 5000}
        }

