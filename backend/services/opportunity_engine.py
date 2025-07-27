# backend/services/opportunity_engine.py
from datetime import datetime, timedelta
import json
import numpy as np
from typing import List, Dict, Optional, Any
import structlog
from backend.services.vertex_ai_service import VertexAIService
from backend.services.firestore_service import FirestoreService
from backend.services.fi_mcp_service import FiMCPService

logger = structlog.get_logger()


class OpportunityEngine:
    """Core business logic for financial opportunity detection"""

    def __init__(self, vertex_ai: VertexAIService, firestore: FirestoreService, fi_mcp: FiMCPService):
        self.vertex_ai = vertex_ai
        self.firestore = firestore
        self.fi_mcp = fi_mcp

        logger.info("✅ Opportunity engine initialized")

    async def generate_opportunities(
            self,
            user_data: Dict[str, Any],
            analysis_type: str = "comprehensive",
            mobile_number: Optional[str] = None  # ADDED: Accept mobile_number parameter
    ) -> Dict[str, Any]:
        """Main opportunity generation logic"""

        logger.info("🔍 Generating financial opportunities",
                    analysis_type=analysis_type,
                    mobile_number=mobile_number)

        try:
            opportunities = []

            # 1. Analyze different opportunity categories
            savings_ops = await self._analyze_savings_optimization(user_data, mobile_number)
            opportunities.extend(savings_ops)

            investment_ops = await self._analyze_investment_opportunities(user_data, mobile_number)
            opportunities.extend(investment_ops)

            spending_ops = await self._analyze_spending_optimization(user_data, mobile_number)
            opportunities.extend(spending_ops)

            debt_ops = await self._analyze_debt_optimization(user_data, mobile_number)
            opportunities.extend(debt_ops)

            tax_ops = await self._analyze_tax_opportunities(user_data, mobile_number)
            opportunities.extend(tax_ops)

            income_ops = await self._analyze_income_enhancement(user_data, mobile_number)
            opportunities.extend(income_ops)

            # 2. Use AI for advanced analysis if enabled
            if analysis_type == "comprehensive":
                ai_opportunities = await self._get_ai_enhanced_opportunities(user_data, opportunities, mobile_number)
                opportunities.extend(ai_opportunities)

            # 3. Score and rank opportunities
            scored_opportunities = await self._score_and_rank_opportunities(opportunities, user_data)

            # 4. Generate recommendations
            recommendations = self._generate_recommendations(scored_opportunities)

            total_annual_value = sum(opp.get("potential_annual_value", 0) for opp in scored_opportunities)

            result = {
                "opportunities": scored_opportunities[:10],  # Top 10
                "total_annual_value": total_annual_value,
                "confidence_score": np.mean([opp.get("confidence_score", 0.5) for opp in
                                             scored_opportunities]) if scored_opportunities else 0.5,
                "recommendations": recommendations,
                "analysis_timestamp": datetime.now().isoformat(),
                "market_context": await self._get_market_context(),
                "mobile_number": mobile_number  # ADDED: Include mobile_number in response
            }

            logger.info("✅ Opportunities generated",
                        count=len(scored_opportunities),
                        total_value=total_annual_value,
                        mobile_number=mobile_number)

            return result

        except Exception as e:
            logger.error("❌ Failed to generate opportunities",
                         error=str(e),
                         mobile_number=mobile_number)
            raise

    async def _analyze_investment_opportunities(self, user_data: Dict[str, Any], mobile_number: Optional[str] = None) -> \
    List[Dict[str, Any]]:
        """Analyze potential investment opportunities"""
        opportunities = []

        try:
            user_profile = user_data.get("user_profile", {})
            investments = user_data.get("investments", [])
            accounts = user_data.get("accounts", [])

            age = user_profile.get("age", 30)
            annual_income = user_profile.get("annual_income", 0)

            # Calculate total liquid assets
            total_liquid = sum(
                acc.get("balance", 0) for acc in accounts
                if acc.get("type") in ["savings", "checking"]
            )

            # Calculate current investments
            total_investments = sum(inv.get("current_value", 0) for inv in investments)

            # Check for investment readiness (emergency fund)
            monthly_expenses = self._calculate_monthly_expenses(user_data)
            has_emergency_fund = total_liquid >= (monthly_expenses * 3)

            # Diversification check
            investment_types = set(inv.get("type", "other") for inv in investments)
            needs_diversification = len(investment_types) < 3 and total_investments > 100000

            # Retirement planning
            retirement_investments = sum(
                inv.get("current_value", 0) for inv in investments
                if inv.get("category") == "retirement"
            )

            # SIP opportunity if income is good and investments are low
            if annual_income > 600000 and total_investments < annual_income * 0.5 and has_emergency_fund:
                monthly_sip = min(annual_income * 0.15 / 12, 25000)  # 15% of income up to ₹25,000/month
                five_year_returns = self._calculate_sip_returns(monthly_sip, 5, 0.12)  # 12% annual returns

                opportunities.append({
                    "id": f"sip_investment_{datetime.now().timestamp()}",
                    "type": "investment_opportunity",
                    "priority": "high",
                    "title": "Start Monthly SIP Investment",
                    "description": f"Invest ₹{monthly_sip:,.0f}/month in diversified mutual funds",
                    "potential_annual_value": monthly_sip * 12 * 0.12,  # 12% annual returns
                    "effort_level": "low",
                    "time_to_implement": "1 week",
                    "confidence_score": 0.85,
                    "risk_level": "medium",
                    "category": "wealth_building",
                    "mobile_number": mobile_number,
                    "action_steps": [
                        "Research top-performing mutual funds",
                        "Set up SIP with trusted platform",
                        "Automate monthly transfers",
                        "Review performance quarterly"
                    ],
                    "financial_impact": {
                        "monthly_investment": monthly_sip,
                        "5_year_value": five_year_returns,
                        "implementation_cost": 0
                    }
                })

            # Retirement planning opportunity
            if age > 25 and retirement_investments < annual_income * age * 0.1:
                required_retirement_corpus = annual_income * 25  # 25x annual income
                current_gap = required_retirement_corpus - retirement_investments

                if current_gap > 0:
                    opportunities.append({
                        "id": f"retirement_planning_{datetime.now().timestamp()}",
                        "type": "retirement_planning",
                        "priority": "medium",
                        "title": "Retirement Planning Gap",
                        "description": f"Increase retirement investments to build adequate corpus",
                        "potential_annual_value": current_gap * 0.08 / (60 - age),  # Value of closing the gap
                        "effort_level": "medium",
                        "time_to_implement": "1 month",
                        "confidence_score": 0.8,
                        "risk_level": "low",
                        "category": "long_term_planning",
                        "mobile_number": mobile_number,
                        "action_steps": [
                            "Consult with financial advisor",
                            "Increase NPS/EPF contributions",
                            "Set up retirement-focused mutual funds",
                            "Review allocation annually"
                        ]
                    })

            # Diversification opportunity
            if needs_diversification and total_investments > 0:
                opportunities.append({
                    "id": f"diversification_{datetime.now().timestamp()}",
                    "type": "portfolio_optimization",
                    "priority": "medium",
                    "title": "Investment Portfolio Diversification",
                    "description": "Diversify investments across asset classes to reduce risk",
                    "potential_annual_value": total_investments * 0.02,  # 2% improved risk-adjusted returns
                    "effort_level": "medium",
                    "time_to_implement": "1-2 months",
                    "confidence_score": 0.75,
                    "risk_level": "low",
                    "category": "risk_management",
                    "mobile_number": mobile_number,
                    "action_steps": [
                        "Analyze current portfolio allocation",
                        "Rebalance across equity, debt, and hybrid funds",
                        "Consider gold and international exposure",
                        "Set up automatic rebalancing"
                    ]
                })

            return opportunities

        except Exception as e:
            logger.error("❌ Investment opportunity analysis failed",
                         error=str(e),
                         mobile_number=mobile_number)
            return []

    async def _analyze_savings_optimization(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze savings account optimization opportunities"""
        opportunities = []

        try:
            accounts = user_data.get("accounts", [])

            total_savings = sum(
                acc.get("balance", 0) for acc in accounts
                if acc.get("type") in ["savings", "checking"]
            )

            if total_savings > 50000:
                # High-yield savings opportunity
                current_rate = 0.035  # 3.5% typical savings
                high_yield_rate = 0.075  # 7.5% high-yield
                annual_gain = total_savings * (high_yield_rate - current_rate)

                if annual_gain > 5000:  # Only if meaningful impact
                    opportunities.append({
                        "id": f"savings_opt_{datetime.now().timestamp()}",
                        "type": "savings_optimization",
                        "priority": "high" if annual_gain > 15000 else "medium",
                        "title": f"High-Yield Savings Optimization",
                        "description": f"Move ₹{total_savings:,.0f} to high-yield savings account earning 7.5% instead of 3.5%",
                        "potential_annual_value": annual_gain,
                        "effort_level": "low",
                        "time_to_implement": "1-2 days",
                        "confidence_score": 0.95,
                        "risk_level": "very_low",
                        "category": "immediate_gain",
                        "action_steps": [
                            "Research FDIC-insured high-yield savings accounts",
                            "Compare rates from digital banks (Marcus, Ally, etc.)",
                            "Open new account online",
                            "Transfer funds and update auto-payments"
                        ],
                        "financial_impact": {
                            "monthly_gain": annual_gain / 12,
                            "5_year_value": annual_gain * 5.5,  # With compounding
                            "implementation_cost": 0
                        },
                        "prerequisites": [],
                        "timeline_milestones": [
                            {"milestone": "Research and compare", "timeline": "Day 1"},
                            {"milestone": "Open account", "timeline": "Day 2"},
                            {"milestone": "Transfer funds", "timeline": "Day 3"}
                        ]
                    })

            # Emergency fund analysis
            monthly_expenses = self._calculate_monthly_expenses(user_data)
            emergency_target = monthly_expenses * 6
            current_emergency = total_savings

            if current_emergency < emergency_target and current_emergency > 0:
                shortage = emergency_target - current_emergency
                opportunities.append({
                    "id": f"emergency_fund_{datetime.now().timestamp()}",
                    "type": "risk_mitigation",
                    "priority": "medium" if shortage < 100000 else "high",
                    "title": f"Emergency Fund Gap: ₹{shortage:,.0f}",
                    "description": f"Build emergency fund to 6 months of expenses (₹{emergency_target:,.0f})",
                    "potential_annual_value": shortage * 0.1,  # Peace of mind value
                    "effort_level": "medium",
                    "time_to_implement": "6-12 months",
                    "confidence_score": 0.9,
                    "risk_level": "low",
                    "category": "financial_security"
                })

            return opportunities

        except Exception as e:
            logger.error("❌ Savings optimization analysis failed", error=str(e))
            return []

    async def _analyze_savings_optimization(self, user_data: Dict[str, Any], mobile_number: Optional[str] = None) -> \
    List[Dict[str, Any]]:
        """Analyze savings account optimization opportunities"""
        opportunities = []

        try:
            accounts = user_data.get("accounts", [])
            total_savings = sum(
                acc.get("balance", 0) for acc in accounts
                if acc.get("type") in ["savings", "checking"]
            )

            if total_savings > 50000:
                # High-yield savings opportunity
                current_rate = 0.035  # 3.5% typical savings
                high_yield_rate = 0.075  # 7.5% high-yield
                annual_gain = total_savings * (high_yield_rate - current_rate)

                if annual_gain > 5000:  # Only if meaningful impact
                    opportunities.append({
                        "id": f"savings_opt_{datetime.now().timestamp()}",
                        "type": "savings_optimization",
                        "priority": "high" if annual_gain > 15000 else "medium",
                        "title": f"High-Yield Savings Optimization",
                        "description": f"Move ₹{total_savings:,.0f} to high-yield savings account earning 7.5% instead of 3.5%",
                        "potential_annual_value": annual_gain,
                        "effort_level": "low",
                        "time_to_implement": "1-2 days",
                        "confidence_score": 0.95,
                        "risk_level": "very_low",
                        "category": "immediate_gain",
                        "mobile_number": mobile_number,  # ADDED
                        "action_steps": [
                            "Research FDIC-insured high-yield savings accounts",
                            "Compare rates from digital banks (Marcus, Ally, etc.)",
                            "Open new account online",
                            "Transfer funds and update auto-payments"
                        ],
                        "financial_impact": {
                            "monthly_gain": annual_gain / 12,
                            "5_year_value": annual_gain * 5.5,  # With compounding
                            "implementation_cost": 0
                        },
                        "prerequisites": [],
                        "timeline_milestones": [
                            {"milestone": "Research and compare", "timeline": "Day 1"},
                            {"milestone": "Open account", "timeline": "Day 2"},
                            {"milestone": "Transfer funds", "timeline": "Day 3"}
                        ]
                    })

            return opportunities

        except Exception as e:
            logger.error("❌ Savings optimization analysis failed",
                         error=str(e),
                         mobile_number=mobile_number)
            return []

    async def _analyze_spending_optimization(self, user_data: Dict[str, Any], mobile_number: Optional[str] = None) -> List[Dict[str, Any]]:
        """Analyze spending optimization opportunities"""
        opportunities = []

        try:
            transactions = user_data.get("transactions", [])

            # Categorize spending
            spending_by_category = {}
            recent_transactions = [
                t for t in transactions
                if (datetime.now() - datetime.fromisoformat(t.get("date", "2024-01-01"))).days <= 30
            ]

            for transaction in recent_transactions:
                if transaction.get("amount", 0) < 0:  # Expenses
                    category = transaction.get("category", "other")
                    amount = abs(transaction.get("amount", 0))
                    spending_by_category[category] = spending_by_category.get(category, 0) + amount

            # Analyze high-impact categories
            for category, monthly_amount in spending_by_category.items():
                if monthly_amount > 10000:  # Categories with significant spending
                    optimization_potential = self._get_category_optimization_potential(category, monthly_amount)


                    if optimization_potential["savings"] > 2000:  # Meaningful savings
                        annual_savings = optimization_potential["savings"] * 12

                        opportunities.append({
                            "id": f"spending_{category}_{datetime.now().timestamp()}",
                            "type": "expense_reduction",
                            "priority": "medium",
                            "title": f"Optimize {category.title()} Spending",
                            "description": f"Reduce {category} expenses by {optimization_potential['percentage']}% through {optimization_potential['method']}",
                            "potential_annual_value": annual_savings,
                            "effort_level": optimization_potential["effort"],
                            "time_to_implement": optimization_potential["timeline"],
                            "confidence_score": optimization_potential["confidence"],
                            "risk_level": "low",
                            "category": "lifestyle_optimization",
                            "action_steps": optimization_potential["action_steps"]
                        })

            return opportunities

        except Exception as e:
            logger.error("❌ Spending analysis failed", error=str(e))
            return []

    async def _analyze_debt_optimization(self, user_data: Dict[str, Any], mobile_number: Optional[str] = None) -> List[Dict[str, Any]]:
        """Analyze debt optimization opportunities"""
        opportunities = []

        try:
            debt_accounts = user_data.get("debt", [])

            for debt in debt_accounts:
                balance = debt.get("balance", 0)
                interest_rate = debt.get("interest_rate", 24.0)
                debt_type = debt.get("type", "unknown")

                if balance > 10000:  # Significant debt
                    annual_interest = balance * (interest_rate / 100)

                    if debt_type == "credit_card" and interest_rate > 20:
                        opportunities.append({
                            "id": f"debt_optimization_{debt.get('id', 'unknown')}",
                            "type": "debt_reduction",
                            "priority": "high",
                            "title": f"Pay Down High-Interest {debt_type.title()}",
                            "description": f"Reduce ₹{balance:,.0f} debt at {interest_rate}% interest",
                            "potential_annual_value": annual_interest,
                            "effort_level": "high",
                            "time_to_implement": "3-12 months",
                            "confidence_score": 0.95,
                            "risk_level": "low",
                            "category": "debt_management",
                            "action_steps": [
                                "List all debts by interest rate",
                                "Pay minimum on all, extra on highest rate",
                                "Consider debt consolidation options",
                                "Set up automatic payments"
                            ]
                        })

            return opportunities

        except Exception as e:
            logger.error("❌ Debt analysis failed", error=str(e))
            return []

    async def _analyze_tax_opportunities(self, user_data: Dict[str, Any], mobile_number: Optional[str] = None) -> List[Dict[str, Any]]:
        """Analyze tax optimization opportunities"""
        opportunities = []

        try:
            user_profile = user_data.get("user_profile", {})
            investments = user_data.get("investments", [])

            annual_income = user_profile.get("annual_income", 0)

            if annual_income > 500000:  # Above ₹5 LPA
                # 80C optimization
                current_80c = sum(
                    inv.get("current_value", 0) for inv in investments
                    if inv.get("category") in ["ppf", "elss", "tax_saver"]
                )

                max_80c = 150000
                if current_80c < max_80c:
                    additional_investment = max_80c - current_80c
                    tax_bracket = 0.30 if annual_income > 1000000 else 0.20 if annual_income > 500000 else 0.05
                    tax_savings = additional_investment * tax_bracket

                    opportunities.append({
                        "id": f"tax_80c_{datetime.now().timestamp()}",
                        "type": "tax_optimization",
                        "priority": "medium",
                        "title": f"80C Tax Optimization - Save ₹{tax_savings:,.0f}",
                        "description": f"Invest ₹{additional_investment:,.0f} more in ELSS/PPF to maximize 80C deduction",
                        "potential_annual_value": tax_savings,
                        "effort_level": "low",
                        "time_to_implement": "1 week",
                        "confidence_score": 0.9,
                        "risk_level": "low",
                        "category": "tax_optimization"
                    })

            return opportunities

        except Exception as e:
            logger.error("❌ Tax analysis failed", error=str(e))
            return []

    async def _analyze_income_enhancement(self, user_data: Dict[str, Any], mobile_number: Optional[str] = None) -> List[Dict[str, Any]]:
        """Analyze income enhancement opportunities"""
        opportunities = []

        try:
            user_profile = user_data.get("user_profile", {})

            # Skill-based income opportunities
            age = user_profile.get("age", 30)
            current_income = user_profile.get("annual_income", 0)

            if age < 40 and current_income > 0:
                # Upskilling opportunities
                potential_income_increase = current_income * 0.15  # 15% potential increase

                opportunities.append({
                    "id": f"income_enhancement_{datetime.now().timestamp()}",
                    "type": "income_enhancement",
                    "priority": "medium",
                    "title": f"Skill Development for ₹{potential_income_increase:,.0f} Income Boost",
                    "description": "Invest in upskilling for career growth and salary increment",
                    "potential_annual_value": potential_income_increase,
                    "effort_level": "high",
                    "time_to_implement": "6-12 months",
                    "confidence_score": 0.65,
                    "risk_level": "medium",
                    "category": "career_growth"
                })

            return opportunities

        except Exception as e:
            logger.error("❌ Income analysis failed", error=str(e))
            return []

    async def _get_ai_enhanced_opportunities(self, user_data: Dict[str, Any],
                                             existing_opportunities: List[Dict[str, Any]], mobile_number: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get AI-enhanced opportunities using Vertex AI"""
        try:
            # Use Vertex AI to find additional opportunities
            ai_analysis = await self.vertex_ai.analyze_market_opportunities(user_data)

            ai_opportunities = []
            for opp in ai_analysis.get("market_opportunities", []):
                ai_opportunities.append({
                    "id": f"ai_enhanced_{datetime.now().timestamp()}",
                    "type": opp.get("type", "investment"),
                    "priority": "medium",
                    "title": opp.get("title", "AI-Detected Opportunity"),
                    "description": opp.get("description", ""),
                    "potential_annual_value": opp.get("potential_annual_value", 0),
                    "effort_level": "medium",
                    "time_to_implement": opp.get("time_horizon", "3-6 months"),
                    "confidence_score": opp.get("confidence", 0.7),
                    "risk_level": opp.get("risk_level", "medium"),
                    "category": "ai_recommended",
                    "action_steps": opp.get("action_steps", [])
                })

            return ai_opportunities

        except Exception as e:
            logger.error("❌ AI enhancement failed", error=str(e))
            return []

    async def _score_and_rank_opportunities(self, opportunities: List[Dict[str, Any]], user_data: Dict[str, Any]) -> \
    List[Dict[str, Any]]:
        """Score and rank opportunities by impact and feasibility"""

        scored_opportunities = []

        for opp in opportunities:
            # Calculate composite score
            impact_score = min(opp.get("potential_annual_value", 0) / 10000, 10)  # Normalize to 10
            confidence_score = opp.get("confidence_score", 0.5) * 10

            effort_multiplier = {
                "low": 1.0,
                "medium": 0.8,
                "high": 0.6
            }.get(opp.get("effort_level", "medium"), 0.8)

            priority_multiplier = {
                "urgent": 1.2,
                "high": 1.0,
                "medium": 0.8,
                "low": 0.6
            }.get(opp.get("priority", "medium"), 0.8)

            composite_score = (impact_score + confidence_score) * effort_multiplier * priority_multiplier

            opp["composite_score"] = composite_score
            scored_opportunities.append(opp)

        # Sort by composite score
        scored_opportunities.sort(key=lambda x: x["composite_score"], reverse=True)

        return scored_opportunities

    def _generate_recommendations(self, opportunities: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        if not opportunities:
            return ["Your finances are well-optimized! Keep monitoring for new opportunities."]

        # Top priority recommendations
        high_impact_ops = [opp for opp in opportunities[:3] if opp.get("potential_annual_value", 0) > 10000]

        if high_impact_ops:
            recommendations.append(
                f"Priority: {high_impact_ops[0]['title']} could save ₹{high_impact_ops[0]['potential_annual_value']:,.0f} annually")

        # Quick wins
        quick_wins = [opp for opp in opportunities if opp.get("effort_level") == "low"]
        if quick_wins:
            recommendations.append(f"Quick win: {quick_wins[0]['title']} - minimal effort, good returns")

        # Risk mitigation
        risk_ops = [opp for opp in opportunities if opp.get("type") == "risk_mitigation"]
        if risk_ops:
            recommendations.append(f"Security: {risk_ops[0]['title']} - strengthen your financial foundation")

        return recommendations[:5]  # Top 5 recommendations

    async def _get_market_context(self) -> Dict[str, Any]:
        """Get current market context"""
        return {
            "interest_rates": {"repo_rate": 6.5, "fd_rates": "6.5-7.5%"},
            "inflation": 4.2,
            "market_trend": "volatile",
            "recommendation": "Focus on diversification and emergency fund"
        }

    # Helper methods
    def _calculate_monthly_expenses(self, user_data: Dict[str, Any]) -> float:
        """Calculate average monthly expenses"""
        transactions = user_data.get("transactions", [])

        if not transactions:
            # Estimate based on income
            income = user_data.get("user_profile", {}).get("annual_income", 600000)
            return income * 0.6 / 12  # Assume 60% of income as expenses

        # Calculate from actual transactions
        monthly_expenses = []
        current_month_expenses = 0
        current_month = None

        for transaction in sorted(transactions, key=lambda x: x.get("date", "")):
            try:
                transaction_date = datetime.fromisoformat(transaction.get("date", "2024-01-01"))
                month_key = (transaction_date.year, transaction_date.month)

                if current_month != month_key:
                    if current_month is not None:
                        monthly_expenses.append(current_month_expenses)
                    current_month = month_key
                    current_month_expenses = 0

                if transaction.get("amount", 0) < 0:  # Expense
                    current_month_expenses += abs(transaction.get("amount", 0))
            except:
                continue

        if current_month_expenses > 0:
            monthly_expenses.append(current_month_expenses)

        return np.mean(monthly_expenses) if monthly_expenses else 50000

    def _calculate_sip_returns(self, monthly_sip: float, years: int, annual_return: float) -> float:
        """Calculate SIP returns with compounding"""
        monthly_return = annual_return / 12
        months = years * 12

        future_value = monthly_sip * (((1 + monthly_return) ** months - 1) / monthly_return) * (1 + monthly_return)
        return future_value

    def _get_category_optimization_potential(self, category: str, monthly_amount: float) -> Dict[str, Any]:
        """Get optimization potential for spending category"""

        optimization_strategies = {
            "food": {
                "percentage": 25,
                "method": "meal planning and cooking at home",
                "effort": "medium",
                "timeline": "1 month",
                "confidence": 0.75,
                "action_steps": [
                    "Plan weekly meals and create shopping lists",
                    "Cook at home 4-5 days per week",
                    "Use food delivery apps mindfully",
                    "Buy groceries in bulk for non-perishables"
                ]
            },
            "transport": {
                "percentage": 20,
                "method": "public transport and ride optimization",
                "effort": "low",
                "timeline": "2 weeks",
                "confidence": 0.8,
                "action_steps": [
                    "Use public transport for daily commute",
                    "Combine errands into single trips",
                    "Consider carpooling options",
                    "Walk or cycle for short distances"
                ]
            },
            "entertainment": {
                "percentage": 30,
                "method": "budget allocation and free alternatives",
                "effort": "low",
                "timeline": "1 month",
                "confidence": 0.85,
                "action_steps": [
                    "Set monthly entertainment budget",
                    "Explore free events and activities",
                    "Use discount apps and offers",
                    "Limit expensive outings to special occasions"
                ]
            },
            "shopping": {
                "percentage": 35,
                "method": "planned purchases and comparison shopping",
                "effort": "medium",
                "timeline": "2 months",
                "confidence": 0.7,
                "action_steps": [
                    "Create shopping lists and stick to them",
                    "Compare prices across platforms",
                    "Wait 24 hours before impulse purchases",
                    "Use cashback and reward programs"
                ]
            }
        }

        strategy = optimization_strategies.get(category, {
            "percentage": 15,
            "method": "mindful spending and budgeting",
            "effort": "medium",
            "timeline": "1-2 months",
            "confidence": 0.6,
            "action_steps": ["Track expenses", "Set category budget", "Review monthly"]
        })

        strategy["savings"] = monthly_amount * (strategy["percentage"] / 100)
        return strategy

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Opportunity engine cleaned up")
