# backend/services/fi_mcp_service.py
import httpx
import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from models.configs import Settings
import urllib.parse

logger = structlog.get_logger()


class FiMCPService:
    """Service to interact with Fi Money MCP server without authentication"""

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
        """Initiate Fi MCP session for a mobile number without authentication"""
        try:
            logger.info("🔐 Initiating Fi MCP session", mobile_number=mobile_number, scenario=scenario)

            # Generate session ID
            session_id = f"mcp-session-{uuid.uuid4()}"

            # Map scenario to test phone number
            test_phone = self.test_scenarios.get(scenario, "1313131313")

            # Store session data without authentication requirements
            session_data = {
                "session_id": session_id,
                "mobile_number": mobile_number,
                "test_phone": test_phone,
                "scenario": scenario,
                "created_at": datetime.now(),
                "last_activity": datetime.now()
            }

            # Store session
            self.active_sessions[mobile_number] = session_data

            return {
                "session_id": session_id,
                "scenario": scenario,
                "requires_authentication": False,  # Since we're using test data
                "login_url": None  # No authentication required for test scenarios
            }

        except Exception as e:
            logger.error("❌ Failed to initiate Fi MCP session", error=str(e))
            raise

    async def switch_scenario(self, mobile_number: str, new_scenario: str) -> Dict[str, Any]:
        """Switch Fi MCP scenario for a user"""
        try:
            session_data = self.active_sessions.get(mobile_number)
            if not session_data:
                # Create new session if none exists
                return await self.initiate_session(mobile_number, new_scenario)

            # Update scenario and test phone
            old_scenario = session_data.get("scenario", "balanced")
            session_data["scenario"] = new_scenario
            session_data["test_phone"] = self.test_scenarios.get(new_scenario, "1313131313")
            session_data["last_activity"] = datetime.now()

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

            # Get or create session without authentication
            session_data = self.active_sessions.get(mobile_number)
            if not session_data:
                # Create a simple session without authentication
                session_id = f"mcp-session-{uuid.uuid4()}"
                session_data = {
                    "session_id": session_id,
                    "mobile_number": mobile_number,
                    "test_phone": self.test_scenarios.get(scenario or "balanced", "1313131313"),
                    "scenario": scenario or "balanced",
                    "created_at": datetime.now(),
                    "last_activity": datetime.now()
                }
                self.active_sessions[mobile_number] = session_data
            
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

    async def _fetch_credit_report(self, session_id: str) -> Dict[str, Any]:
        """Fetch credit report data from Fi MCP"""
        try:
            response = await self._make_mcp_call(session_id, "fetch_credit_report", {})
            
            if response.get("result"):
                credit_response = response["result"].get("creditReportResponse", {})
                
                # Parse credit score
                credit_score = 0
                if "creditScore" in credit_response:
                    credit_score = credit_response["creditScore"].get("score", 0)
                
                # Parse credit accounts
                accounts = []
                for account in credit_response.get("creditAccounts", []):
                    account_data = {
                        "account_type": account.get("accountType", ""),
                        "balance": self._parse_currency_value(account.get("currentBalance", {})),
                        "credit_limit": self._parse_currency_value(account.get("creditLimit", {})),
                        "payment_status": account.get("paymentStatus", ""),
                        "last_payment": account.get("lastPaymentDate", "")
                    }
                    accounts.append(account_data)
                
                return {
                    "credit_score": credit_score,
                    "accounts": accounts,
                    "total_credit_limit": sum(acc["credit_limit"] for acc in accounts),
                    "total_outstanding": sum(acc["balance"] for acc in accounts),
                    "raw_response": credit_response
                }
            
            return {}
            
        except Exception as e:
            logger.error("❌ Failed to fetch credit report", error=str(e))
            return {}

    async def _fetch_epf_details(self, session_id: str) -> Dict[str, Any]:
        """Fetch EPF details from Fi MCP"""
        try:
            response = await self._make_mcp_call(session_id, "fetch_epf_details", {})
            
            if response.get("result"):
                epf_response = response["result"].get("epfDetailsResponse", {})
                
                # Parse EPF balance
                total_balance = self._parse_currency_value(epf_response.get("totalBalance", {}))
                employee_contribution = self._parse_currency_value(epf_response.get("employeeContribution", {}))
                employer_contribution = self._parse_currency_value(epf_response.get("employerContribution", {}))
                
                # Parse recent transactions
                transactions = []
                for txn in epf_response.get("recentTransactions", []):
                    transaction_data = {
                        "date": txn.get("date", ""),
                        "type": txn.get("transactionType", ""),
                        "amount": self._parse_currency_value(txn.get("amount", {})),
                        "description": txn.get("description", "")
                    }
                    transactions.append(transaction_data)
                
                return {
                    "total_balance": total_balance,
                    "employee_contribution": employee_contribution,
                    "employer_contribution": employer_contribution,
                    "transactions": transactions,
                    "raw_response": epf_response
                }
            
            return {}
            
        except Exception as e:
            logger.error("❌ Failed to fetch EPF details", error=str(e))
            return {}

    async def _fetch_mf_transactions(self, session_id: str) -> Dict[str, Any]:
        """Fetch mutual fund transactions from Fi MCP"""
        try:
            response = await self._make_mcp_call(session_id, "fetch_mf_transactions", {})
            
            if response.get("result"):
                mf_response = response["result"].get("mfTransactionsResponse", {})
                
                # Parse transactions
                transactions = []
                total_invested = 0
                total_current_value = 0
                
                for txn in mf_response.get("transactions", []):
                    amount = self._parse_currency_value(txn.get("amount", {}))
                    current_value = self._parse_currency_value(txn.get("currentValue", {}))
                    
                    transaction_data = {
                        "fund_name": txn.get("fundName", ""),
                        "transaction_type": txn.get("transactionType", ""),
                        "amount": amount,
                        "units": float(txn.get("units", "0")),
                        "nav": float(txn.get("nav", "0")),
                        "current_value": current_value,
                        "date": txn.get("transactionDate", ""),
                        "folio_number": txn.get("folioNumber", "")
                    }
                    transactions.append(transaction_data)
                    
                    if txn.get("transactionType") == "PURCHASE":
                        total_invested += amount
                    total_current_value += current_value
                
                return {
                    "transactions": transactions,
                    "total_invested": total_invested,
                    "total_current_value": total_current_value,
                    "total_returns": total_current_value - total_invested,
                    "return_percentage": ((total_current_value - total_invested) / total_invested * 100) if total_invested > 0 else 0,
                    "raw_response": mf_response
                }
            
            return {}
            
        except Exception as e:
            logger.error("❌ Failed to fetch MF transactions", error=str(e))
            return {}

    async def _fetch_bank_transactions(self, session_id: str) -> Dict[str, Any]:
        """Fetch bank transactions from Fi MCP"""
        try:
            response = await self._make_mcp_call(session_id, "fetch_bank_transactions", {})
            
            if response.get("result"):
                bank_response = response["result"].get("bankTransactionsResponse", {})
                
                # Parse transactions
                transactions = []
                total_credits = 0
                total_debits = 0
                
                for txn in bank_response.get("transactions", []):
                    amount = self._parse_currency_value(txn.get("amount", {}))
                    
                    transaction_data = {
                        "date": txn.get("transactionDate", ""),
                        "description": txn.get("description", ""),
                        "amount": amount,
                        "type": txn.get("transactionType", ""),
                        "balance": self._parse_currency_value(txn.get("balance", {})),
                        "account_number": txn.get("accountNumber", ""),
                        "category": txn.get("category", "")
                    }
                    transactions.append(transaction_data)
                    
                    if txn.get("transactionType") == "CREDIT":
                        total_credits += amount
                    else:
                        total_debits += amount
                
                # Calculate monthly summary
                monthly_summary = self._calculate_monthly_summary(transactions)
                
                return {
                    "transactions": transactions,
                    "total_credits": total_credits,
                    "total_debits": total_debits,
                    "net_flow": total_credits - total_debits,
                    "monthly_summary": monthly_summary,
                    "raw_response": bank_response
                }
            
            return {}
            
        except Exception as e:
            logger.error("❌ Failed to fetch bank transactions", error=str(e))
            return {}

    async def _fetch_stock_transactions(self, session_id: str) -> Dict[str, Any]:
        """Fetch stock transactions from Fi MCP"""
        try:
            response = await self._make_mcp_call(session_id, "fetch_stock_transactions", {})
            
            if response.get("result"):
                stock_response = response["result"].get("stockTransactionsResponse", {})
                
                # Parse transactions
                transactions = []
                total_invested = 0
                total_current_value = 0
                
                for txn in stock_response.get("transactions", []):
                    amount = self._parse_currency_value(txn.get("amount", {}))
                    current_value = self._parse_currency_value(txn.get("currentValue", {}))
                    
                    transaction_data = {
                        "symbol": txn.get("symbol", ""),
                        "company_name": txn.get("companyName", ""),
                        "transaction_type": txn.get("transactionType", ""),
                        "quantity": int(txn.get("quantity", "0")),
                        "price": float(txn.get("price", "0")),
                        "amount": amount,
                        "current_price": float(txn.get("currentPrice", "0")),
                        "current_value": current_value,
                        "date": txn.get("transactionDate", ""),
                        "exchange": txn.get("exchange", "")
                    }
                    transactions.append(transaction_data)
                    
                    if txn.get("transactionType") == "BUY":
                        total_invested += amount
                    total_current_value += current_value
                
                return {
                    "transactions": transactions,
                    "total_invested": total_invested,
                    "total_current_value": total_current_value,
                    "total_returns": total_current_value - total_invested,
                    "return_percentage": ((total_current_value - total_invested) / total_invested * 100) if total_invested > 0 else 0,
                    "raw_response": stock_response
                }
            
            return {}
            
        except Exception as e:
            logger.error("❌ Failed to fetch stock transactions", error=str(e))
            return {}

    def _parse_currency_value(self, value_data: Dict[str, Any]) -> float:
        """Parse Fi MCP currency value format"""
        if not value_data:
            return 0.0

        units = float(value_data.get("units", "0"))
        nanos = value_data.get("nanos", 0)

        return units + (nanos / 1_000_000_000)

    def _parse_accounts_data(self, net_worth_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse accounts data from net worth response"""
        accounts = []
        assets = net_worth_data.get("assets", {})
        
        # Savings accounts
        if assets.get("ASSET_TYPE_SAVINGS_ACCOUNTS", 0) > 0:
            accounts.append({
                "type": "savings",
                "name": "Savings Account",
                "balance": assets["ASSET_TYPE_SAVINGS_ACCOUNTS"],
                "account_number": "****1234",
                "bank": "Primary Bank"
            })
        
        # Current accounts
        if assets.get("ASSET_TYPE_CURRENT_ACCOUNTS", 0) > 0:
            accounts.append({
                "type": "current",
                "name": "Current Account",
                "balance": assets["ASSET_TYPE_CURRENT_ACCOUNTS"],
                "account_number": "****5678",
                "bank": "Business Bank"
            })
        
        return accounts

    def _parse_investments_data(self, net_worth_data: Dict[str, Any], mf_data: Dict[str, Any], stock_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse investments data from various sources"""
        investments = []
        assets = net_worth_data.get("assets", {})
        
        # Mutual funds
        if assets.get("ASSET_TYPE_MUTUAL_FUND", 0) > 0:
            investments.append({
                "type": "mutual_fund",
                "name": "Mutual Funds Portfolio",
                "current_value": assets["ASSET_TYPE_MUTUAL_FUND"],
                "invested_amount": mf_data.get("total_invested", assets["ASSET_TYPE_MUTUAL_FUND"] * 0.9),
                "returns": mf_data.get("total_returns", assets["ASSET_TYPE_MUTUAL_FUND"] * 0.1),
                "return_percentage": mf_data.get("return_percentage", 10.0)
            })
        
        # Stocks
        if assets.get("ASSET_TYPE_INDIAN_SECURITIES", 0) > 0:
            investments.append({
                "type": "stocks",
                "name": "Stock Portfolio",
                "current_value": assets["ASSET_TYPE_INDIAN_SECURITIES"],
                "invested_amount": stock_data.get("total_invested", assets["ASSET_TYPE_INDIAN_SECURITIES"] * 0.85),
                "returns": stock_data.get("total_returns", assets["ASSET_TYPE_INDIAN_SECURITIES"] * 0.15),
                "return_percentage": stock_data.get("return_percentage", 15.0)
            })
        
        # EPF
        if assets.get("ASSET_TYPE_EPF", 0) > 0:
            investments.append({
                "type": "epf",
                "name": "Employee Provident Fund",
                "current_value": assets["ASSET_TYPE_EPF"],
                "invested_amount": assets["ASSET_TYPE_EPF"] * 0.95,
                "returns": assets["ASSET_TYPE_EPF"] * 0.05,
                "return_percentage": 8.5
            })
        
        return investments

    def _parse_debt_data(self, net_worth_data: Dict[str, Any], credit_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse debt data from various sources"""
        debt = []
        liabilities = net_worth_data.get("liabilities", {})
        
        # Credit cards
        if liabilities.get("LIABILITY_TYPE_CREDIT_CARD", 0) > 0:
            debt.append({
                "type": "credit_card",
                "name": "Credit Card Debt",
                "balance": liabilities["LIABILITY_TYPE_CREDIT_CARD"],
                "interest_rate": 18.0,
                "minimum_payment": liabilities["LIABILITY_TYPE_CREDIT_CARD"] * 0.05,
                "credit_limit": credit_data.get("total_credit_limit", liabilities["LIABILITY_TYPE_CREDIT_CARD"] * 2)
            })
        
        # Personal loans
        if liabilities.get("LIABILITY_TYPE_PERSONAL_LOAN", 0) > 0:
            debt.append({
                "type": "personal_loan",
                "name": "Personal Loan",
                "balance": liabilities["LIABILITY_TYPE_PERSONAL_LOAN"],
                "interest_rate": 12.0,
                "emi": liabilities["LIABILITY_TYPE_PERSONAL_LOAN"] * 0.08,
                "tenure_remaining": 24
            })
        
        # Home loan
        if liabilities.get("LIABILITY_TYPE_HOME_LOAN", 0) > 0:
            debt.append({
                "type": "home_loan",
                "name": "Home Loan",
                "balance": liabilities["LIABILITY_TYPE_HOME_LOAN"],
                "interest_rate": 8.5,
                "emi": liabilities["LIABILITY_TYPE_HOME_LOAN"] * 0.012,
                "tenure_remaining": 180
            })
        
        return debt

    def _parse_all_transactions(self, bank_data: Dict[str, Any], mf_data: Dict[str, Any], stock_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Combine and parse all transactions"""
        all_transactions = []
        
        # Bank transactions
        for txn in bank_data.get("transactions", [])[:10]:  # Last 10
            all_transactions.append({
                "date": txn.get("date", ""),
                "description": txn.get("description", ""),
                "amount": txn.get("amount", 0),
                "type": txn.get("type", ""),
                "category": "banking",
                "source": "bank"
            })
        
        # MF transactions
        for txn in mf_data.get("transactions", [])[:5]:  # Last 5
            all_transactions.append({
                "date": txn.get("date", ""),
                "description": f"MF: {txn.get('fund_name', '')}",
                "amount": txn.get("amount", 0),
                "type": txn.get("transaction_type", ""),
                "category": "investment",
                "source": "mutual_fund"
            })
        
        # Stock transactions
        for txn in stock_data.get("transactions", [])[:5]:  # Last 5
            all_transactions.append({
                "date": txn.get("date", ""),
                "description": f"Stock: {txn.get('symbol', '')}",
                "amount": txn.get("amount", 0),
                "type": txn.get("transaction_type", ""),
                "category": "investment",
                "source": "stocks"
            })
        
        # Sort by date (most recent first)
        all_transactions.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        return all_transactions[:20]  # Return top 20

    def _calculate_income_data(self, bank_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate income data from bank transactions"""
        monthly_summary = bank_data.get("monthly_summary", {})
        
        return {
            "monthly": monthly_summary.get("income", 0),
            "annual": monthly_summary.get("income", 0) * 12,
            "sources": monthly_summary.get("income_sources", []),
            "growth_rate": 5.0  # Assumed growth rate
        }

    def _calculate_expenses_data(self, bank_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate expenses data from bank transactions"""
        monthly_summary = bank_data.get("monthly_summary", {})
        
        return {
            "monthly": monthly_summary.get("expenses", 0),
            "annual": monthly_summary.get("expenses", 0) * 12,
            "categories": monthly_summary.get("expense_categories", {}),
            "trends": monthly_summary.get("expense_trends", {})
        }

    def _calculate_monthly_summary(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate monthly summary from transactions"""
        current_month = datetime.now().strftime("%Y-%m")
        
        monthly_income = 0
        monthly_expenses = 0
        income_sources = []
        expense_categories = {}
        
        for txn in transactions:
            txn_date = txn.get("date", "")
            if txn_date.startswith(current_month):
                amount = txn.get("amount", 0)
                
                if txn.get("type") == "CREDIT":
                    monthly_income += amount
                    description = txn.get("description", "").lower()
                    if "salary" in description:
                        income_sources.append("salary")
                    elif "interest" in description:
                        income_sources.append("interest")
                else:
                    monthly_expenses += amount
                    category = txn.get("category", "others")
                    expense_categories[category] = expense_categories.get(category, 0) + amount
        
        return {
            "income": monthly_income,
            "expenses": monthly_expenses,
            "net_flow": monthly_income - monthly_expenses,
            "income_sources": list(set(income_sources)),
            "expense_categories": expense_categories,
            "expense_trends": {"month_over_month": 0}  # Can be enhanced
        }

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

    async def verify_authentication(self, session_id: str, mobile_number: str, otp: str) -> Dict[str, Any]:
        """Verify OTP authentication (simplified for test scenarios)"""
        try:
            logger.info("🔐 Verifying Fi MCP authentication", 
                       mobile_number=mobile_number, session_id=session_id)
            
            # Get session data
            session_data = self.active_sessions.get(mobile_number)
            if not session_data or session_data.get("session_id") != session_id:
                return {
                    "success": False,
                    "message": "Invalid session"
                }
            
            # For test scenarios, accept any 6-digit OTP
            if len(otp) == 6 and otp.isdigit():
                # Update session as authenticated
                session_data["is_authenticated"] = True
                session_data["last_activity"] = datetime.now()
                
                return {
                    "success": True,
                    "scenario": session_data.get("scenario", "balanced"),
                    "message": "Authentication successful"
                }
            else:
                return {
                    "success": False,
                    "message": "Invalid OTP format"
                }
                
        except Exception as e:
            logger.error("❌ Failed to verify authentication", error=str(e))
            return {
                "success": False,
                "message": f"Authentication error: {str(e)}"
            }

    async def get_authentication_status(self, mobile_number: str) -> Dict[str, Any]:
        """Get authentication status for a mobile number"""
        try:
            session_data = self.active_sessions.get(mobile_number)
            
            if not session_data:
                return {
                    "is_authenticated": False,
                    "session_id": None,
                    "scenario": None,
                    "last_activity": None
                }
            
            # Check if session is still valid (24 hours)
            last_activity = session_data.get("last_activity", datetime.now())
            if datetime.now() - last_activity > timedelta(hours=24):
                # Session expired
                del self.active_sessions[mobile_number]
                return {
                    "is_authenticated": False,
                    "session_id": None,
                    "scenario": None,
                    "last_activity": None
                }
            
            return {
                "is_authenticated": session_data.get("is_authenticated", False),
                "session_id": session_data.get("session_id"),
                "scenario": session_data.get("scenario"),
                "last_activity": last_activity.isoformat()
            }
            
        except Exception as e:
            logger.error("❌ Failed to get authentication status", error=str(e))
            return {
                "is_authenticated": False,
                "session_id": None,
                "scenario": None,
                "last_activity": None
            }

    async def cleanup(self):
        """Cleanup resources"""
        await self.client.aclose()
        self.active_sessions.clear()
        logger.info("🧹 Fi MCP service cleaned up")
