# models/fi_mcp_simulator.py - Fi MCP data simulation for testing
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import random
import uuid


class FiMCPSimulator:
    """Simulator for Fi MCP data when real service is unavailable"""
    
    def __init__(self):
        self.scenarios = {
            "no_assets": self._generate_no_assets_data,
            "all_assets_large": self._generate_large_assets_data,
            "all_assets_small": self._generate_small_assets_data,
            "multiple_accounts": self._generate_multiple_accounts_data,
            "balanced": self._generate_balanced_data,
            "starter": self._generate_starter_data,
            "high_spender": self._generate_high_spender_data,
        }
    
    def generate_data(self, mobile_number: str, scenario: str = "balanced") -> Dict[str, Any]:
        """Generate simulated Fi MCP data"""
        generator = self.scenarios.get(scenario, self._generate_balanced_data)
        return generator(mobile_number)
    
    def _generate_no_assets_data(self, mobile_number: str) -> Dict[str, Any]:
        """Generate data for user with no assets"""
        return {
            "mobile_number": mobile_number,
            "scenario": "no_assets",
            "net_worth": {
                "total_value": 5000.0,
                "assets": 5000.0,
                "liabilities": 0.0
            },
            "accounts": [
                {
                    "id": "acc_001",
                    "type": "savings",
                    "bank": "HDFC Bank",
                    "balance": 5000.0,
                    "account_number": "****1234"
                }
            ],
            "investments": [],
            "loans": [],
            "transactions": self._generate_basic_transactions(),
            "summary": {
                "monthly_income": 25000.0,
                "monthly_expenses": 20000.0,
                "savings_rate": 0.2,
                "emergency_fund_months": 0.25
            }
        }
    
    def _generate_large_assets_data(self, mobile_number: str) -> Dict[str, Any]:
        """Generate data for user with large assets"""
        return {
            "mobile_number": mobile_number,
            "scenario": "all_assets_large",
            "net_worth": {
                "total_value": 2500000.0,
                "assets": 2800000.0,
                "liabilities": 300000.0
            },
            "accounts": [
                {
                    "id": "acc_001",
                    "type": "savings",
                    "bank": "HDFC Bank",
                    "balance": 150000.0,
                    "account_number": "****1234"
                },
                {
                    "id": "acc_002",
                    "type": "current",
                    "bank": "ICICI Bank",
                    "balance": 75000.0,
                    "account_number": "****5678"
                }
            ],
            "investments": [
                {
                    "id": "inv_001",
                    "type": "mutual_fund",
                    "name": "HDFC Equity Fund",
                    "current_value": 800000.0,
                    "invested_amount": 600000.0,
                    "returns": 200000.0
                },
                {
                    "id": "inv_002",
                    "type": "stocks",
                    "name": "Direct Equity",
                    "current_value": 500000.0,
                    "invested_amount": 400000.0,
                    "returns": 100000.0
                },
                {
                    "id": "inv_003",
                    "type": "ppf",
                    "name": "Public Provident Fund",
                    "current_value": 350000.0,
                    "invested_amount": 300000.0,
                    "returns": 50000.0
                }
            ],
            "loans": [
                {
                    "id": "loan_001",
                    "type": "home_loan",
                    "bank": "SBI",
                    "outstanding": 300000.0,
                    "emi": 25000.0,
                    "interest_rate": 8.5
                }
            ],
            "transactions": self._generate_high_value_transactions(),
            "summary": {
                "monthly_income": 150000.0,
                "monthly_expenses": 80000.0,
                "savings_rate": 0.47,
                "emergency_fund_months": 2.8
            }
        }
    
    def _generate_small_assets_data(self, mobile_number: str) -> Dict[str, Any]:
        """Generate data for user with small assets"""
        return {
            "mobile_number": mobile_number,
            "scenario": "all_assets_small",
            "net_worth": {
                "total_value": 85000.0,
                "assets": 95000.0,
                "liabilities": 10000.0
            },
            "accounts": [
                {
                    "id": "acc_001",
                    "type": "savings",
                    "bank": "HDFC Bank",
                    "balance": 15000.0,
                    "account_number": "****1234"
                }
            ],
            "investments": [
                {
                    "id": "inv_001",
                    "type": "mutual_fund",
                    "name": "SIP Investment",
                    "current_value": 45000.0,
                    "invested_amount": 40000.0,
                    "returns": 5000.0
                },
                {
                    "id": "inv_002",
                    "type": "fd",
                    "name": "Fixed Deposit",
                    "current_value": 35000.0,
                    "invested_amount": 35000.0,
                    "returns": 0.0
                }
            ],
            "loans": [
                {
                    "id": "loan_001",
                    "type": "credit_card",
                    "bank": "HDFC Bank",
                    "outstanding": 10000.0,
                    "minimum_due": 1000.0,
                    "interest_rate": 36.0
                }
            ],
            "transactions": self._generate_moderate_transactions(),
            "summary": {
                "monthly_income": 45000.0,
                "monthly_expenses": 35000.0,
                "savings_rate": 0.22,
                "emergency_fund_months": 0.43
            }
        }
    
    def _generate_balanced_data(self, mobile_number: str) -> Dict[str, Any]:
        """Generate balanced financial data"""
        return {
            "mobile_number": mobile_number,
            "scenario": "balanced",
            "net_worth": {
                "total_value": 450000.0,
                "assets": 520000.0,
                "liabilities": 70000.0
            },
            "accounts": [
                {
                    "id": "acc_001",
                    "type": "savings",
                    "bank": "HDFC Bank",
                    "balance": 45000.0,
                    "account_number": "****1234"
                },
                {
                    "id": "acc_002",
                    "type": "current",
                    "bank": "ICICI Bank",
                    "balance": 25000.0,
                    "account_number": "****5678"
                }
            ],
            "investments": [
                {
                    "id": "inv_001",
                    "type": "mutual_fund",
                    "name": "Diversified Equity Fund",
                    "current_value": 180000.0,
                    "invested_amount": 150000.0,
                    "returns": 30000.0
                },
                {
                    "id": "inv_002",
                    "type": "ppf",
                    "name": "Public Provident Fund",
                    "current_value": 120000.0,
                    "invested_amount": 100000.0,
                    "returns": 20000.0
                },
                {
                    "id": "inv_003",
                    "type": "fd",
                    "name": "Fixed Deposits",
                    "current_value": 150000.0,
                    "invested_amount": 150000.0,
                    "returns": 0.0
                }
            ],
            "loans": [
                {
                    "id": "loan_001",
                    "type": "personal_loan",
                    "bank": "HDFC Bank",
                    "outstanding": 50000.0,
                    "emi": 5000.0,
                    "interest_rate": 12.0
                },
                {
                    "id": "loan_002",
                    "type": "credit_card",
                    "bank": "ICICI Bank",
                    "outstanding": 20000.0,
                    "minimum_due": 2000.0,
                    "interest_rate": 36.0
                }
            ],
            "transactions": self._generate_balanced_transactions(),
            "summary": {
                "monthly_income": 75000.0,
                "monthly_expenses": 55000.0,
                "savings_rate": 0.27,
                "emergency_fund_months": 1.27
            }
        }
    
    def _generate_starter_data(self, mobile_number: str) -> Dict[str, Any]:
        """Generate data for financial starter"""
        return {
            "mobile_number": mobile_number,
            "scenario": "starter",
            "net_worth": {
                "total_value": 25000.0,
                "assets": 25000.0,
                "liabilities": 0.0
            },
            "accounts": [
                {
                    "id": "acc_001",
                    "type": "savings",
                    "bank": "SBI",
                    "balance": 25000.0,
                    "account_number": "****9876"
                }
            ],
            "investments": [],
            "loans": [],
            "transactions": self._generate_starter_transactions(),
            "summary": {
                "monthly_income": 35000.0,
                "monthly_expenses": 30000.0,
                "savings_rate": 0.14,
                "emergency_fund_months": 0.83
            }
        }
    
    def _generate_high_spender_data(self, mobile_number: str) -> Dict[str, Any]:
        """Generate data for high spender"""
        return {
            "mobile_number": mobile_number,
            "scenario": "high_spender",
            "net_worth": {
                "total_value": 180000.0,
                "assets": 280000.0,
                "liabilities": 100000.0
            },
            "accounts": [
                {
                    "id": "acc_001",
                    "type": "savings",
                    "bank": "HDFC Bank",
                    "balance": 30000.0,
                    "account_number": "****1111"
                }
            ],
            "investments": [
                {
                    "id": "inv_001",
                    "type": "mutual_fund",
                    "name": "Growth Fund",
                    "current_value": 250000.0,
                    "invested_amount": 200000.0,
                    "returns": 50000.0
                }
            ],
            "loans": [
                {
                    "id": "loan_001",
                    "type": "credit_card",
                    "bank": "HDFC Bank",
                    "outstanding": 80000.0,
                    "minimum_due": 8000.0,
                    "interest_rate": 42.0
                },
                {
                    "id": "loan_002",
                    "type": "personal_loan",
                    "bank": "ICICI Bank",
                    "outstanding": 20000.0,
                    "emi": 2500.0,
                    "interest_rate": 15.0
                }
            ],
            "transactions": self._generate_high_spending_transactions(),
            "summary": {
                "monthly_income": 90000.0,
                "monthly_expenses": 85000.0,
                "savings_rate": 0.06,
                "emergency_fund_months": 0.35
            }
        }
    
    def _generate_basic_transactions(self) -> List[Dict[str, Any]]:
        """Generate basic transaction history"""
        transactions = []
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(20):
            date = base_date + timedelta(days=random.randint(0, 30))
            transactions.append({
                "id": f"txn_{uuid.uuid4().hex[:8]}",
                "date": date.isoformat(),
                "amount": -random.randint(500, 3000),
                "category": random.choice(["food", "transport", "utilities", "shopping"]),
                "description": f"Transaction {i+1}",
                "merchant": f"Merchant {i+1}"
            })
        
        return sorted(transactions, key=lambda x: x["date"], reverse=True)
    
    def _generate_moderate_transactions(self) -> List[Dict[str, Any]]:
        """Generate moderate transaction history"""
        transactions = []
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(35):
            date = base_date + timedelta(days=random.randint(0, 30))
            transactions.append({
                "id": f"txn_{uuid.uuid4().hex[:8]}",
                "date": date.isoformat(),
                "amount": -random.randint(800, 5000),
                "category": random.choice(["food", "transport", "utilities", "shopping", "entertainment"]),
                "description": f"Transaction {i+1}",
                "merchant": f"Merchant {i+1}"
            })
        
        return sorted(transactions, key=lambda x: x["date"], reverse=True)
    
    def _generate_high_value_transactions(self) -> List[Dict[str, Any]]:
        """Generate high value transaction history"""
        transactions = []
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(50):
            date = base_date + timedelta(days=random.randint(0, 30))
            transactions.append({
                "id": f"txn_{uuid.uuid4().hex[:8]}",
                "date": date.isoformat(),
                "amount": -random.randint(2000, 15000),
                "category": random.choice(["food", "transport", "utilities", "shopping", "entertainment", "travel"]),
                "description": f"Transaction {i+1}",
                "merchant": f"Merchant {i+1}"
            })
        
        return sorted(transactions, key=lambda x: x["date"], reverse=True)
    
    def _generate_balanced_transactions(self) -> List[Dict[str, Any]]:
        """Generate balanced transaction history"""
        transactions = []
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(40):
            date = base_date + timedelta(days=random.randint(0, 30))
            transactions.append({
                "id": f"txn_{uuid.uuid4().hex[:8]}",
                "date": date.isoformat(),
                "amount": -random.randint(1000, 8000),
                "category": random.choice(["food", "transport", "utilities", "shopping", "entertainment"]),
                "description": f"Transaction {i+1}",
                "merchant": f"Merchant {i+1}"
            })
        
        return sorted(transactions, key=lambda x: x["date"], reverse=True)
    
    def _generate_starter_transactions(self) -> List[Dict[str, Any]]:
        """Generate starter transaction history"""
        transactions = []
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(15):
            date = base_date + timedelta(days=random.randint(0, 30))
            transactions.append({
                "id": f"txn_{uuid.uuid4().hex[:8]}",
                "date": date.isoformat(),
                "amount": -random.randint(300, 2000),
                "category": random.choice(["food", "transport", "utilities"]),
                "description": f"Transaction {i+1}",
                "merchant": f"Merchant {i+1}"
            })
        
        return sorted(transactions, key=lambda x: x["date"], reverse=True)
    
    def _generate_high_spending_transactions(self) -> List[Dict[str, Any]]:
        """Generate high spending transaction history"""
        transactions = []
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(60):
            date = base_date + timedelta(days=random.randint(0, 30))
            transactions.append({
                "id": f"txn_{uuid.uuid4().hex[:8]}",
                "date": date.isoformat(),
                "amount": -random.randint(1500, 12000),
                "category": random.choice(["food", "transport", "utilities", "shopping", "entertainment", "travel", "luxury"]),
                "description": f"Transaction {i+1}",
                "merchant": f"Merchant {i+1}"
            })
        
        return sorted(transactions, key=lambda x: x["date"], reverse=True)


# Global simulator instance
fi_mcp_simulator = FiMCPSimulator()
