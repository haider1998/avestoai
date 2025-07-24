# backend/services/opportunity_engine.py
from datetime import datetime, timedelta
import json
import numpy as np
from typing import List, Dict, Optional


class OpportunityEngine:
    def __init__(self, vertex_client, firestore_client):
        self.vertex_client = vertex_client
        self.firestore_client = firestore_client

    async def generate_opportunities(self, private_insights: dict, market_insights: dict, user_data: dict) -> List[
        dict]:
        """Main opportunity generation logic"""

        opportunities = []

        # High-yield savings opportunities
        savings_ops = self._analyze_savings_optimization(user_data)
        opportunities.extend(savings_ops)

        # Investment opportunities
        investment_ops = self._analyze_investment_opportunities(user_data, market_insights)
        opportunities.extend(investment_ops)

        # Spending optimization
        spending_ops = self._analyze_spending_optimization(user_data, private_insights)
        opportunities.extend(spending_ops)

        # Debt optimization
        debt_ops = self._analyze_debt_optimization(user_data)
        opportunities.extend(debt_ops)

        # Tax optimization
        tax_ops = self._analyze_tax_opportunities(user_data)
        opportunities.extend(tax_ops)

        # Sort by potential impact
        opportunities.sort(key=lambda x: x.get('potential_annual_value', 0), reverse=True)

        return opportunities[:5]  # Top 5 opportunities

    def _analyze_savings_optimization(self, user_data: dict) -> List[dict]:
        """Analyze savings account optimization opportunities"""
        opportunities = []
        accounts = user_data.get('accounts', {})

        savings_balance = accounts.get('savings', 0)
        checking_balance = accounts.get('checking', 0)
        total_liquid = savings_balance + checking_balance

        # High-yield savings opportunity
        if total_liquid > 50000:
            current_rate = 0.035  # 3.5% typical savings
            high_yield_rate = 0.075  # 7.5% high-yield
            annual_gain = total_liquid * (high_yield_rate - current_rate)

            opportunities.append({
                "id": "high_yield_savings",
                "type": "savings_optimization",
                "priority": "high",
                "title": f"Earn ₹{annual_gain:,.0f} More Annually",
                "description": f"Move ₹{total_liquid:,} to high-yield savings account earning 7.5% instead of 3.5%",
                "potential_annual_value": annual_gain,
                "effort_level": "low",
                "time_to_implement": "1 day",
                "confidence_score": 0.95,
                "risk_level": "very_low",
                "category": "immediate_gain",
                "action_steps": [
                    "Research FDIC-insured high-yield savings accounts",
                    "Compare rates from top digital banks",
                    "Open account and transfer funds",
                    "Set up automatic transfers"
                ],
                "financial_impact": {
                    "monthly_gain": annual_gain / 12,
                    "5_year_value": annual_gain * 5,
                    "compound_effect": annual_gain * 5.5  # Assuming compound growth
                }
            })

        # Emergency fund analysis
        monthly_expenses = self._calculate_monthly_expenses(user_data)
        emergency_target = monthly_expenses * 6
        current_emergency = savings_balance

        if current_emergency < emergency_target:
            shortage = emergency_target - current_emergency
            opportunities.append({
                "id": "emergency_fund_gap",
                "type": "risk_mitigation",
                "priority": "medium",
                "title": f"Build Emergency Fund (₹{shortage:,.0f} Short)",
                "description": f"Your emergency fund should be ₹{emergency_target:,} (6 months expenses) but is currently ₹{current_emergency:,}",
                "potential_annual_value": shortage * 0.1,  # Value of financial security
                "effort_level": "medium",
                "time_to_implement": "6-12 months",
                "confidence_score": 0.9,
                "risk_level": "low",
                "category": "financial_security"
            })

        return opportunities

    def _analyze_investment_opportunities(self, user_data: dict, market_insights: dict) -> List[dict]:
        """Analyze investment optimization opportunities"""
        opportunities = []

        accounts = user_data.get('accounts', {})
        investments = user_data.get('investments', {})
        profile = user_data.get('profile', {})

        total_liquid = accounts.get('savings', 0) + accounts.get('checking', 0)
        total_investments = sum(investments.values())
        monthly_income = profile.get('income', 0) / 12

        # SIP opportunity analysis
        recommended_sip = min(monthly_income * 0.2, 25000)  # 20% of income or max ₹25k
        current_sip = investments.get('mutual_funds', 0) / 12  # Rough estimate

        if recommended_sip > current_sip + 5000:  # If gap is significant
            additional_sip = recommended_sip - current_sip
            projected_returns = additional_sip * 12 * 0.12 * 10  # 12% returns over 10 years

            opportunities.append({
                "id": "sip_optimization",
                "type": "investment_growth",
                "priority": "high",
                "title": f"Increase SIP by ₹{additional_sip:,.0f}/month",
                "description": f"Based on your income, you can invest ₹{additional_sip:,.0f} more monthly. Projected 10-year value: ₹{projected_returns:,.0f}",
                "potential_annual_value": additional_sip * 12 * 0.12,
                "effort_level": "low",
                "time_to_implement": "1 week",
                "confidence_score": 0.8,
                "risk_level": "medium",
                "category": "wealth_building",
                "financial_impact": {
                    "10_year_corpus": projected_returns,
                    "monthly_investment": additional_sip,
                    "expected_annual_return": 0.12
                }
            })

        # Asset allocation opportunity
        if total_liquid > total_investments * 0.5:  # Too much in liquid assets
            excess_liquid = total_liquid - (total_investments * 0.3)
            if excess_liquid > 25000:
                opportunities.append({
                    "id": "asset_rebalancing",
                    "type": "investment_allocation",
                    "priority": "medium",
                    "title": f"Rebalance ₹{excess_liquid:,.0f} from Savings to Investments",
                    "description": "You have too much money in low-yield savings. Consider moving some to diversified investments.",
                    "potential_annual_value": excess_liquid * 0.08,  # 8% additional returns
                    "effort_level": "medium",
                    "time_to_implement": "2 weeks",
                    "confidence_score": 0.75,
                    "risk_level": "medium",
                    "category": "portfolio_optimization"
                })

        return opportunities

    def _analyze_spending_optimization(self, user_data: dict, private_insights: dict) -> List[dict]:
        """Analyze spending optimization opportunities"""
        opportunities = []
        transactions = user_data.get('transactions', [])

        # Categorize spending
        spending_by_category = {}
        for transaction in transactions:
            if transaction.get('amount', 0) < 0:  # Expenses
                category = transaction.get('category', 'other')
                amount = abs(transaction.get('amount', 0))
                spending_by_category[category] = spending_by_category.get(category, 0) + amount

        # Analyze food/dining expenses
        food_spending = spending_by_category.get('food', 0)
        if food_spending > 15000:  # If spending more than ₹15k/month on food
            potential_savings = food_spending * 0.25  # 25% reduction potential
            annual_savings = potential_savings * 12

            opportunities.append({
                "id": "food_spending_optimization",
                "type": "expense_reduction",
                "priority": "medium",
                "title": f"Optimize Food Spending (Save ₹{annual_savings:,.0f}/year)",
                "description": f"You spent ₹{food_spending:,} on food last month. Small changes could save 25%.",
                "potential_annual_value": annual_savings,
                "effort_level": "medium",
                "time_to_implement": "1 month",
                "confidence_score": 0.7,
                "risk_level": "low",
                "category": "lifestyle_optimization",
                "action_steps": [
                    "Track dining out vs cooking at home",
                    "Plan weekly meals and grocery shopping",
                    "Use food delivery apps mindfully",
                    "Set monthly food budget"
                ]
            })

        return opportunities

    def _analyze_debt_optimization(self, user_data: dict) -> List[dict]:
        """Analyze debt optimization opportunities"""
        opportunities = []
        accounts = user_data.get('accounts', {})

        credit_used = accounts.get('credit_used', 0)
        credit_limit = accounts.get('credit_limit', 0)

        if credit_used > 0:
            # High credit utilization
            utilization_ratio = credit_used / credit_limit if credit_limit > 0 else 0

            if utilization_ratio > 0.3:  # More than 30% utilization
                annual_interest = credit_used * 0.24  # Assuming 24% APR

                opportunities.append({
                    "id": "credit_card_debt",
                    "type": "debt_reduction",
                    "priority": "high",
                    "title": f"Pay Down Credit Card (Save ₹{annual_interest:,.0f}/year)",
                    "description": f"High credit utilization ({utilization_ratio:.1%}). Paying down ₹{credit_used:,} will save significant interest.",
                    "potential_annual_value": annual_interest,
                    "effort_level": "high",
                    "time_to_implement": "3-6 months",
                    "confidence_score": 0.95,
                    "risk_level": "low",
                    "category": "debt_management"
                })

        return opportunities

    def _analyze_tax_opportunities(self, user_data: dict) -> List[dict]:
        """Analyze tax optimization opportunities"""
        opportunities = []
        profile = user_data.get('profile', {})
        investments = user_data.get('investments', {})

        annual_income = profile.get('income', 0)
        if annual_income > 500000:  # If income is above ₹5 LPA

            # 80C optimization
            current_80c = investments.get('ppf', 0) + investments.get('elss', 0)
            max_80c = 150000

            if current_80c < max_80c:
                additional_investment = max_80c - current_80c
                tax_savings = additional_investment * 0.3  # Assuming 30% tax bracket

                opportunities.append({
                    "id": "tax_optimization_80c",
                    "type": "tax_savings",
                    "priority": "medium",
                    "title": f"Save ₹{tax_savings:,.0f} in Taxes (80C)",
                    "description": f"Invest additional ₹{additional_investment:,} in ELSS/PPF to maximize 80C deduction",
                    "potential_annual_value": tax_savings,
                    "effort_level": "low",
                    "time_to_implement": "1 week",
                    "confidence_score": 0.9,
                    "risk_level": "low",
                    "category": "tax_optimization"
                })

        return opportunities

    def _calculate_monthly_expenses(self, user_data: dict) -> float:
        """Calculate average monthly expenses"""
        transactions = user_data.get('transactions', [])

        monthly_expenses = []
        current_month_expenses = 0
        current_month = None

        for transaction in sorted(transactions, key=lambda x: x.get('date', datetime.now())):
            transaction_date = transaction.get('date')
            if isinstance(transaction_date, str):
                transaction_date = datetime.fromisoformat(transaction_date)

            month_key = (transaction_date.year, transaction_date.month)

            if current_month != month_key:
                if current_month is not None:
                    monthly_expenses.append(current_month_expenses)
                current_month = month_key
                current_month_expenses = 0

            if transaction.get('amount', 0) < 0:  # Expense
                current_month_expenses += abs(transaction.get('amount', 0))

        if current_month_expenses > 0:
            monthly_expenses.append(current_month_expenses)

        return np.mean(monthly_expenses) if monthly_expenses else 50000  # Default ₹50k
