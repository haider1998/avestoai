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

logger = structlog.get_logger()


class FiMCPService:
    """Service to interact with Fi Money MCP server using proper MCP protocol"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.FI_MCP_BASE_URL
        self.timeout = settings.FI_MCP_TIMEOUT
        self.max_retries = settings.FI_MCP_MAX_RETRIES

        # MCP session management
        self.session_id = f"mcp-session-{uuid.uuid4()}"
        self.is_authenticated = False
        self.login_url = None

        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={
                "Content-Type": "application/json",
                "Mcp-Session-Id": self.session_id,
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

        logger.info("✅ Fi MCP service initialized", session_id=self.session_id)

    async def health_check(self) -> Dict[str, Any]:
        """Check Fi MCP service health"""
        try:
            start_time = datetime.now()

            # Test MCP connection with a simple call
            response = await self._make_mcp_call("tools/list", {})
            response_time = (datetime.now() - start_time).total_seconds() * 1000

            if response.get("result"):
                return {
                    "status": "healthy",
                    "response_time": response_time,
                    "last_check": datetime.now(),
                    "session_id": self.session_id,
                    "authenticated": self.is_authenticated
                }
            else:
                return {
                    "status": "degraded",
                    "response_time": response_time,
                    "last_check": datetime.now(),
                    "error": "Invalid MCP response"
                }

        except Exception as e:
            logger.error("❌ Fi MCP health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "last_check": datetime.now(),
                "error": str(e)
            }

    async def authenticate_user(self, user_scenario: str = "balanced") -> bool:
        """Authenticate with Fi MCP using test phone number"""
        try:
            # Use phone number based on user scenario
            phone_number = self.test_scenarios.get(user_scenario, "1313131313")

            logger.info("🔐 Authenticating with Fi MCP", scenario=user_scenario, phone=phone_number)

            # If we have a login URL, simulate the login process
            if self.login_url:
                login_data = {
                    "phone": phone_number,
                    "otp": "123456"  # Any OTP works in dev server
                }

                async with httpx.AsyncClient() as login_client:
                    login_response = await login_client.post(
                        self.login_url,
                        data=login_data,
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )

                    if login_response.status_code == 200:
                        self.is_authenticated = True
                        logger.info("✅ Fi MCP authentication successful")
                        return True

            # Try a test call to trigger authentication if needed
            await self._make_mcp_call("tools/list", {})
            return True

        except Exception as e:
            logger.error("❌ Fi MCP authentication failed", error=str(e))
            return False

    async def get_user_financial_data(self, user_id: str, scenario: str = "balanced") -> Dict[str, Any]:
        """Get comprehensive financial data for a user"""
        try:
            logger.info("📊 Fetching comprehensive financial data", user_id=user_id, scenario=scenario)

            # Ensure authentication
            await self.authenticate_user(scenario)

            # Fetch all financial data in parallel
            tasks = [
                self._fetch_net_worth(),
                self._fetch_credit_report(),
                self._fetch_epf_details(),
                self._fetch_mf_transactions(),
                self._fetch_bank_transactions(),
                self._fetch_stock_transactions()
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
                "user_id": user_id,
                "scenario": scenario,
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
                "last_updated": datetime.now().isoformat()
            }

            logger.info("✅ Comprehensive financial data fetched successfully",
                        user_id=user_id,
                        net_worth=comprehensive_data.get("net_worth", {}).get("total_value", 0))

            return comprehensive_data

        except Exception as e:
            logger.error("❌ Failed to fetch comprehensive financial data",
                         user_id=user_id, error=str(e))
            # Return demo data as fallback
            return self._get_demo_comprehensive_data(user_id)

    async def _fetch_net_worth(self) -> Dict[str, Any]:
        """Fetch net worth data from Fi MCP"""
        try:
            response = await self._make_mcp_call("fetch_net_worth", {})

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

    async def _fetch_credit_report(self) -> Dict[str, Any]:
        """Fetch credit report data from Fi MCP"""
        try:
            response = await self._make_mcp_call("fetch_credit_report", {})

            if response.get("result") and response["result"].get("creditReports"):
                credit_reports = response["result"]["creditReports"]

                if credit_reports and len(credit_reports) > 0:
                    credit_data = credit_reports[0].get("creditReportData", {})

                    # Extract credit score
                    score_data = credit_data.get("score", {})
                    credit_score = score_data.get("bureauScore", 0)

                    # Extract credit accounts
                    credit_accounts = []
                    credit_account_data = credit_data.get("creditAccount", {})
                    account_details = credit_account_data.get("creditAccountDetails", [])

                    for account in account_details:
                        credit_accounts.append({
                            "account_type": account.get("accountType", ""),
                            "account_status": account.get("accountStatus", ""),
                            "current_balance": account.get("currentBalance", 0),
                            "credit_limit": account.get("creditLimit", 0),
                            "payment_rating": account.get("paymentRating", ""),
                            "date_opened": account.get("dateOpened", ""),
                            "date_closed": account.get("dateClosed", "")
                        })

                    return {
                        "credit_score": credit_score,
                        "credit_accounts": credit_accounts,
                        "date_of_birth": credit_data.get("currentApplication", {}).get("currentApplicationDetails",
                                                                                       {}).get(
                            "currentApplicantDetails", {}).get("dateOfBirthApplicant", ""),
                        "raw_response": credit_data
                    }

            return {}

        except Exception as e:
            logger.error("❌ Failed to fetch credit report", error=str(e))
            return {}

    async def _fetch_epf_details(self) -> Dict[str, Any]:
        """Fetch EPF details from Fi MCP"""
        try:
            response = await self._make_mcp_call("fetch_epf_details", {})

            if response.get("result") and response["result"].get("uanAccounts"):
                uan_accounts = response["result"]["uanAccounts"]

                epf_accounts = []
                total_balance = 0

                for account in uan_accounts:
                    raw_details = account.get("rawDetails", {})
                    overall_balance = raw_details.get("overall_pf_balance", {})

                    current_balance = overall_balance.get("current_pf_balance", 0)
                    employee_share = overall_balance.get("employee_share_total", {}).get("balance", 0)
                    employer_share = overall_balance.get("employer_share_total", {}).get("balance", 0)

                    epf_accounts.append({
                        "uan": account.get("uan", ""),
                        "establishment_name": raw_details.get("establishment_name", ""),
                        "current_balance": current_balance,
                        "employee_share": employee_share,
                        "employer_share": employer_share,
                        "raw_details": raw_details
                    })

                    total_balance += current_balance

                return {
                    "accounts": epf_accounts,
                    "total_balance": total_balance,
                    "raw_response": uan_accounts
                }

            return {}

        except Exception as e:
            logger.error("❌ Failed to fetch EPF details", error=str(e))
            return {}

    async def _fetch_mf_transactions(self) -> Dict[str, Any]:
        """Fetch mutual fund transactions from Fi MCP"""
        try:
            response = await self._make_mcp_call("fetch_mf_transactions", {})

            if response.get("result") and response["result"].get("transactions"):
                transactions = response["result"]["transactions"]

                processed_transactions = []
                schemes = {}

                for tx in transactions:
                    isin = tx.get("isinNumber", "")
                    scheme_name = tx.get("schemeName", "")
                    transaction_date = tx.get("transactionDate", "")
                    transaction_amount = self._parse_currency_value(tx.get("transactionAmount", {}))
                    transaction_units = float(tx.get("transactionUnits", "0"))
                    purchase_price = float(tx.get("purchasePrice", "0"))
                    transaction_mode = tx.get("transactionMode", "")
                    order_type = tx.get("externalOrderType", "")

                    processed_tx = {
                        "isin": isin,
                        "scheme_name": scheme_name,
                        "date": transaction_date,
                        "amount": transaction_amount,
                        "units": transaction_units,
                        "nav": purchase_price,
                        "mode": transaction_mode,
                        "type": order_type,
                        "raw_transaction": tx
                    }

                    processed_transactions.append(processed_tx)

                    # Group by scheme
                    if isin not in schemes:
                        schemes[isin] = {
                            "scheme_name": scheme_name,
                            "transactions": [],
                            "total_invested": 0,
                            "total_units": 0
                        }

                    schemes[isin]["transactions"].append(processed_tx)

                    if order_type == "BUY":
                        schemes[isin]["total_invested"] += transaction_amount
                        schemes[isin]["total_units"] += transaction_units
                    elif order_type == "SELL":
                        schemes[isin]["total_invested"] -= transaction_amount
                        schemes[isin]["total_units"] -= transaction_units

                return {
                    "transactions": processed_transactions,
                    "schemes": schemes,
                    "total_schemes": len(schemes),
                    "total_transactions": len(processed_transactions),
                    "raw_response": transactions
                }

            return {}

        except Exception as e:
            logger.error("❌ Failed to fetch MF transactions", error=str(e))
            return {}

    async def _fetch_bank_transactions(self) -> Dict[str, Any]:
        """Fetch bank transactions from Fi MCP"""
        try:
            response = await self._make_mcp_call("fetch_bank_transactions", {})

            if response.get("result") and response["result"].get("transactions"):
                transactions = response["result"]["transactions"]

                processed_transactions = []
                monthly_summary = {}

                for tx in transactions:
                    amount = self._parse_currency_value(tx.get("transactionAmount", {}))
                    narration = tx.get("narration", "")
                    date = tx.get("transactionDate", "")
                    balance = self._parse_currency_value(tx.get("currentBalance", {}))

                    # Categorize transaction
                    category = self._categorize_transaction(narration, amount)

                    processed_tx = {
                        "date": date,
                        "amount": amount,
                        "narration": narration,
                        "balance": balance,
                        "category": category,
                        "raw_transaction": tx
                    }

                    processed_transactions.append(processed_tx)

                    # Monthly summary
                    try:
                        tx_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                        month_key = tx_date.strftime("%Y-%m")

                        if month_key not in monthly_summary:
                            monthly_summary[month_key] = {
                                "income": 0,
                                "expenses": 0,
                                "transactions": 0
                            }

                        monthly_summary[month_key]["transactions"] += 1

                        if amount > 0:
                            monthly_summary[month_key]["income"] += amount
                        else:
                            monthly_summary[month_key]["expenses"] += abs(amount)
                    except:
                        pass

                return {
                    "transactions": processed_transactions,
                    "monthly_summary": monthly_summary,
                    "total_transactions": len(processed_transactions),
                    "raw_response": transactions
                }

            return {}

        except Exception as e:
            logger.error("❌ Failed to fetch bank transactions", error=str(e))
            return {}

    async def _fetch_stock_transactions(self) -> Dict[str, Any]:
        """Fetch stock transactions from Fi MCP"""
        try:
            response = await self._make_mcp_call("fetch_stock_transactions", {})

            if response.get("result") and response["result"].get("transactions"):
                transactions = response["result"]["transactions"]

                processed_transactions = []
                holdings = {}

                for tx in transactions:
                    isin = tx.get("isin", "")
                    transaction_type = tx.get("transactionType", "")
                    transaction_date = tx.get("transactionDate", "")
                    nav_value = float(tx.get("navValue", "0"))
                    quantity = float(tx.get("quantity", "0"))

                    processed_tx = {
                        "isin": isin,
                        "type": transaction_type,
                        "date": transaction_date,
                        "nav": nav_value,
                        "quantity": quantity,
                        "value": nav_value * quantity,
                        "raw_transaction": tx
                    }

                    processed_transactions.append(processed_tx)

                    # Track holdings
                    if isin not in holdings:
                        holdings[isin] = {
                            "total_quantity": 0,
                            "total_invested": 0,
                            "transactions": []
                        }

                    holdings[isin]["transactions"].append(processed_tx)

                    if transaction_type == "Buy":
                        holdings[isin]["total_quantity"] += quantity
                        holdings[isin]["total_invested"] += (nav_value * quantity)
                    elif transaction_type == "Sell":
                        holdings[isin]["total_quantity"] -= quantity
                        holdings[isin]["total_invested"] -= (nav_value * quantity)

                return {
                    "transactions": processed_transactions,
                    "holdings": holdings,
                    "total_transactions": len(processed_transactions),
                    "raw_response": transactions
                }

            return {}

        except Exception as e:
            logger.error("❌ Failed to fetch stock transactions", error=str(e))
            return {}

    async def _make_mcp_call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make MCP protocol call to Fi server"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": f"tools/call",
                "params": {
                    "name": method,
                    "arguments": params
                }
            }

            response = await self.client.post(
                f"{self.base_url}/mcp/stream",
                json=payload
            )

            response.raise_for_status()
            result = response.json()

            # Handle authentication requirement
            if result.get("error") and "login_url" in str(result.get("error", {})):
                error_data = result.get("error", {})
                if isinstance(error_data, dict) and "data" in error_data:
                    self.login_url = error_data["data"].get("login_url")
                    logger.info("🔐 Login required", login_url=self.login_url)

                    # Try to authenticate automatically
                    if await self.authenticate_user():
                        # Retry the original call
                        response = await self.client.post(
                            f"{self.base_url}/mcp/stream",
                            json=payload
                        )
                        response.raise_for_status()
                        result = response.json()

            return result

        except Exception as e:
            logger.error(f"❌ MCP call failed: {method}", error=str(e))
            raise

    def _parse_currency_value(self, value_data: Dict[str, Any]) -> float:
        """Parse Fi MCP currency value format"""
        if not value_data:
            return 0.0

        units = float(value_data.get("units", "0"))
        nanos = value_data.get("nanos", 0)

        return units + (nanos / 1_000_000_000)

    def _categorize_transaction(self, narration: str, amount: float) -> str:
        """Categorize bank transaction based on narration"""
        narration_lower = narration.lower()

        if amount > 0:  # Credit transactions
            if any(word in narration_lower for word in ["salary", "sal", "payroll"]):
                return "salary"
            elif any(word in narration_lower for word in ["interest", "fd", "savings"]):
                return "interest"
            elif any(word in narration_lower for word in ["dividend", "mutual fund"]):
                return "investment_return"
            else:
                return "credit"
        else:  # Debit transactions
            if any(word in narration_lower for word in ["swiggy", "zomato", "food", "restaurant"]):
                return "food"
            elif any(word in narration_lower for word in ["uber", "ola", "metro", "bus", "petrol"]):
                return "transport"
            elif any(word in narration_lower for word in ["amazon", "flipkart", "shopping", "mall"]):
                return "shopping"
            elif any(word in narration_lower for word in ["electricity", "gas", "water", "mobile", "internet"]):
                return "utilities"
            elif any(word in narration_lower for word in ["hospital", "medical", "pharmacy", "doctor"]):
                return "healthcare"
            elif any(word in narration_lower for word in ["movie", "entertainment", "games"]):
                return "entertainment"
            elif any(word in narration_lower for word in ["loan", "emi", "credit card"]):
                return "loan_payment"
            else:
                return "expense"

    def _parse_accounts_data(self, net_worth_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse accounts data from net worth response"""
        accounts = []

        assets = net_worth_data.get("assets", {})

        # Savings accounts
        if "ASSET_TYPE_SAVINGS_ACCOUNTS" in assets:
            accounts.append({
                "id": "savings_account",
                "type": "savings",
                "balance": assets["ASSET_TYPE_SAVINGS_ACCOUNTS"],
                "bank": "Connected Bank"
            })

        return accounts

    def _parse_investments_data(self, net_worth_data: Dict[str, Any], mf_data: Dict[str, Any],
                                stock_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse investments data"""
        investments = []

        assets = net_worth_data.get("assets", {})

        # Mutual funds
        if "ASSET_TYPE_MUTUAL_FUND" in assets:
            investments.append({
                "id": "mutual_funds",
                "type": "mutual_fund",
                "current_value": assets["ASSET_TYPE_MUTUAL_FUND"],
                "category": "equity_debt",
                "schemes_count": mf_data.get("total_schemes", 0)
            })

        # Indian stocks
        if "ASSET_TYPE_INDIAN_SECURITIES" in assets:
            investments.append({
                "id": "indian_stocks",
                "type": "stocks",
                "current_value": assets["ASSET_TYPE_INDIAN_SECURITIES"],
                "category": "equity",
                "holdings_count": len(stock_data.get("holdings", {}))
            })

        # US stocks
        if "ASSET_TYPE_US_SECURITIES" in assets:
            investments.append({
                "id": "us_stocks",
                "type": "international_stocks",
                "current_value": assets["ASSET_TYPE_US_SECURITIES"],
                "category": "international_equity"
            })

        # EPF
        if "ASSET_TYPE_EPF" in assets:
            investments.append({
                "id": "epf",
                "type": "epf",
                "current_value": assets["ASSET_TYPE_EPF"],
                "category": "retirement"
            })

        return investments

    def _parse_debt_data(self, net_worth_data: Dict[str, Any], credit_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse debt data"""
        debt = []

        liabilities = net_worth_data.get("liabilities", {})

        # Credit cards from credit report
        credit_accounts = credit_data.get("credit_accounts", [])
        for account in credit_accounts:
            if account.get("account_type") == "10":  # Credit card
                debt.append({
                    "id": f"credit_card_{account.get('account_type', 'unknown')}",
                    "type": "credit_card",
                    "balance": account.get("current_balance", 0),
                    "credit_limit": account.get("credit_limit", 0),
                    "interest_rate": 24.0  # Default credit card rate
                })

        # Other liabilities from net worth
        for liability_type, amount in liabilities.items():
            if "VEHICLE_LOAN" in liability_type:
                debt.append({
                    "id": "vehicle_loan",
                    "type": "vehicle_loan",
                    "balance": amount,
                    "interest_rate": 12.0
                })
            elif "HOME_LOAN" in liability_type:
                debt.append({
                    "id": "home_loan",
                    "type": "home_loan",
                    "balance": amount,
                    "interest_rate": 8.5
                })

        return debt

    def _parse_all_transactions(self, bank_data: Dict[str, Any], mf_data: Dict[str, Any], stock_data: Dict[str, Any]) -> \
    List[Dict[str, Any]]:
        """Parse and combine all transactions"""
        all_transactions = []

        # Bank transactions
        bank_transactions = bank_data.get("transactions", [])
        for tx in bank_transactions:
            all_transactions.append({
                "id": f"bank_{len(all_transactions)}",
                "date": tx["date"],
                "amount": tx["amount"],
                "category": tx["category"],
                "description": tx["narration"],
                "account_id": "bank_account",
                "type": "bank"
            })

        # MF transactions
        mf_transactions = mf_data.get("transactions", [])
        for tx in mf_transactions:
            all_transactions.append({
                "id": f"mf_{len(all_transactions)}",
                "date": tx["date"],
                "amount": tx["amount"] if tx["type"] == "BUY" else -tx["amount"],
                "category": "investment",
                "description": f"{tx['type']} {tx['scheme_name']}",
                "account_id": "mutual_fund",
                "type": "mutual_fund"
            })

        # Stock transactions
        stock_transactions = stock_data.get("transactions", [])
        for tx in stock_transactions:
            all_transactions.append({
                "id": f"stock_{len(all_transactions)}",
                "date": tx["date"],
                "amount": tx["value"] if tx["type"] == "Buy" else -tx["value"],
                "category": "investment",
                "description": f"{tx['type']} Stock (ISIN: {tx['isin']})",
                "account_id": "stock_account",
                "type": "stock"
            })

        # Sort by date (newest first)
        all_transactions.sort(key=lambda x: x["date"], reverse=True)

        return all_transactions

    def _calculate_income_data(self, bank_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate income data from bank transactions"""
        monthly_summary = bank_data.get("monthly_summary", {})

        if monthly_summary:
            # Get latest month's income
            latest_month = max(monthly_summary.keys())
            monthly_income = monthly_summary[latest_month]["income"]

            # Calculate annual income (average of last 6 months)
            recent_months = sorted(monthly_summary.keys())[-6:]
            avg_monthly_income = sum(monthly_summary[month]["income"] for month in recent_months) / len(recent_months)

            return {
                "monthly": monthly_income,
                "annual": avg_monthly_income * 12,
                "trend": "stable"  # Could be calculated based on month-over-month changes
            }

        return {"monthly": 0, "annual": 0, "trend": "unknown"}

    def _calculate_expenses_data(self, bank_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate expenses data from bank transactions"""
        monthly_summary = bank_data.get("monthly_summary", {})

        if monthly_summary:
            # Get latest month's expenses
            latest_month = max(monthly_summary.keys())
            monthly_expenses = monthly_summary[latest_month]["expenses"]

            # Calculate annual expenses (average of last 6 months)
            recent_months = sorted(monthly_summary.keys())[-6:]
            avg_monthly_expenses = sum(monthly_summary[month]["expenses"] for month in recent_months) / len(
                recent_months)

            return {
                "monthly": monthly_expenses,
                "annual": avg_monthly_expenses * 12,
                "trend": "stable"
            }

        return {"monthly": 0, "annual": 0, "trend": "unknown"}

    # Keep existing demo data methods for fallback
    def _get_demo_comprehensive_data(self, user_id: str) -> Dict[str, Any]:
        """Demo comprehensive data for fallback"""
        return {
            "user_id": user_id,
            "scenario": "demo",
            "net_worth": {"total_value": 910000},
            "accounts": [{"type": "savings", "balance": 250000}],
            "investments": [{"type": "mutual_fund", "current_value": 450000}],
            "debt": [{"type": "credit_card", "balance": 35000}],
            "transactions": [],
            "income": {"monthly": 120000, "annual": 1440000},
            "expenses": {"monthly": 75000, "annual": 900000}
        }

    async def get_current_financial_state(self, user_id: str) -> Dict[str, Any]:
        """Get current financial state for decision analysis"""
        try:
            # Get full financial data
            financial_data = await self.get_user_financial_data(user_id)

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
            logger.error("❌ Failed to get current financial state", user_id=user_id, error=str(e))
            return {"net_worth": 0, "monthly_income": 0}

    def _calculate_emergency_fund_months(self, financial_data: Dict[str, Any]) -> float:
        """Calculate emergency fund coverage in months"""
        liquid_assets = sum(acc.get("balance", 0) for acc in financial_data.get("accounts", []))
        monthly_expenses = financial_data.get("expenses", {}).get("monthly", 1)

        return liquid_assets / monthly_expenses if monthly_expenses > 0 else 0

    async def get_comprehensive_financial_data(self, user_id: str) -> Dict[str, Any]:
        """Alias for get_user_financial_data for compatibility"""
        return await self.get_user_financial_data(user_id)

    async def get_real_time_data(self, user_id: str) -> Dict[str, Any]:
        """Get real-time financial data"""
        try:
            # For now, return recent data with timestamp
            financial_data = await self.get_user_financial_data(user_id)

            return {
                **financial_data,
                "timestamp": datetime.now().isoformat(),
                "is_real_time": True
            }

        except Exception as e:
            logger.error("❌ Failed to get real-time data", user_id=user_id, error=str(e))
            return {"timestamp": datetime.now().isoformat(), "error": str(e)}

    async def get_user_context_for_chat(self, user_id: str) -> Dict[str, Any]:
        """Get user context optimized for chat"""
        try:
            financial_data = await self.get_user_financial_data(user_id)

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
            logger.error("❌ Failed to get chat context", user_id=user_id, error=str(e))
            return {"current_balance": 0, "monthly_income": 0}

    async def cleanup(self):
        """Cleanup resources"""
        await self.client.aclose()
        logger.info("🧹 Fi MCP service cleaned up")
