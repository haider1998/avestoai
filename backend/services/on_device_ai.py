# backend/services/on_device_ai.py
import asyncio
import json
import numpy as np
from typing import Dict, List, Optional
import ollama
import subprocess
import os


class OnDeviceAI:
    def __init__(self):
        self.model_name = "gemma:2b"  # Lightweight model for on-device
        self.model_loaded = False
        self.cache = {}

    async def initialize_model(self):
        """Initialize Gemma model locally using Ollama"""
        try:
            # Check if Ollama is installed
            subprocess.run(["ollama", "--version"], check=True, capture_output=True)

            # Pull Gemma model if not already available
            await asyncio.to_thread(
                subprocess.run,
                ["ollama", "pull", self.model_name],
                check=True
            )

            # Test model
            test_response = await self._generate_local(
                "Test prompt: Respond with 'Model loaded successfully'"
            )

            if "successfully" in test_response.lower():
                self.model_loaded = True
                print(f"✅ {self.model_name} loaded successfully on-device")
            else:
                raise Exception("Model test failed")

        except Exception as e:
            print(f"⚠️ On-device AI initialization failed: {e}")
            print("Falling back to cloud-only mode")
            self.model_loaded = False

    async def analyze_sensitive_data(self, user_data: dict) -> dict:
        """Analyze sensitive financial data locally for privacy"""

        if not self.model_loaded:
            return self._fallback_local_analysis(user_data)

        # Create anonymized profile locally
        prompt = f"""
        Analyze this financial data privately and create an anonymized profile.
        Keep all personal details local, only output aggregate patterns.

        Financial Data: {json.dumps(user_data, indent=2)}

        Create anonymized profile with:
        - Spending patterns (categories and trends)
        - Income stability score
        - Risk profile
        - Financial discipline score

        Output only anonymized aggregates, no personal details.
        Format as JSON.
        """

        try:
            response = await self._generate_local(prompt)
            return self._parse_local_response(response)
        except:
            return self._fallback_local_analysis(user_data)

    async def quick_decision_score(self, amount: int, category: str, user_context: dict) -> dict:
        """Fast local scoring for immediate feedback"""

        if not self.model_loaded:
            return self._fallback_quick_score(amount, category)

        prompt = f"""
        Quick financial decision scoring (respond in <2 seconds):

        Purchase: ₹{amount:,} for {category}
        Context: {json.dumps(user_context)}

        Provide immediate score (0-100) with brief reasoning.
        Format: {{"score": 75, "reasoning": "Brief explanation"}}
        """

        try:
            response = await self._generate_local(prompt, max_tokens=100)
            return self._parse_local_response(response)
        except:
            return self._fallback_quick_score(amount, category)

    async def calculate_health_score(self, current_data: dict) -> dict:
        """Real-time financial health calculation"""

        # Use local calculation for privacy-sensitive health metrics
        health_metrics = self._calculate_basic_health_metrics(current_data)

        if not self.model_loaded:
            return health_metrics

        # Enhance with AI insights
        prompt = f"""
        Calculate financial health score based on these metrics:
        {json.dumps(health_metrics)}

        Provide:
        - Overall health score (0-100)
        - Key strengths
        - Risk areas
        - Trend analysis

        Keep response under 200 tokens for speed.
        """

        try:
            ai_analysis = await self._generate_local(prompt, max_tokens=200)
            enhanced_metrics = self._parse_local_response(ai_analysis)
            return {**health_metrics, **enhanced_metrics}
        except:
            return health_metrics

    async def detect_spending_anomalies(self, current_data: dict) -> List[dict]:
        """Detect unusual spending patterns locally"""

        # Basic rule-based detection
        anomalies = []
        transactions = current_data.get('transactions', [])

        if not transactions:
            return anomalies

        # Calculate spending baseline
        daily_amounts = []
        for transaction in transactions[-30:]:  # Last 30 transactions
            if transaction.get('amount', 0) < 0:  # Expenses
                daily_amounts.append(abs(transaction['amount']))

        if len(daily_amounts) < 5:
            return anomalies

        avg_spending = np.mean(daily_amounts)
        std_spending = np.std(daily_amounts)

        # Check recent transactions for anomalies
        recent_transactions = transactions[-5:]  # Last 5 transactions

        for transaction in recent_transactions:
            amount = abs(transaction.get('amount', 0))
            if amount > avg_spending + (2 * std_spending):  # 2 standard deviations
                anomalies.append({
                    "type": "high_spending",
                    "amount": amount,
                    "description": f"Unusual expense: ₹{amount:,}",
                    "severity": "medium" if amount < avg_spending + (3 * std_spending) else "high",
                    "timestamp": transaction.get('date'),
                    "suggestion": "Review this expense and consider if it aligns with your financial goals"
                })

        return anomalies

    async def _generate_local(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate response using local Ollama"""
        try:
            response = await asyncio.to_thread(
                ollama.generate,
                model=self.model_name,
                prompt=prompt,
                options={"num_predict": max_tokens, "temperature": 0.3}
            )
            return response['response']
        except Exception as e:
            raise Exception(f"Local generation failed: {e}")

    def _parse_local_response(self, response: str) -> dict:
        """Parse JSON response from local model"""
        try:
            # Find JSON in response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                # If no JSON found, create structured response
                return {"response": response, "parsed": False}
        except:
            return {"response": response, "parsed": False}

    def _calculate_basic_health_metrics(self, data: dict) -> dict:
        """Basic financial health calculation without AI"""
        accounts = data.get('accounts', {})
        transactions = data.get('transactions', [])

        # Calculate basic metrics
        total_assets = sum(accounts.get('savings', 0), accounts.get('checking', 0))
        total_debt = accounts.get('credit_used', 0)
        net_worth = total_assets - total_debt

        # Spending analysis
        monthly_expenses = sum(abs(t.get('amount', 0)) for t in transactions
                               if t.get('amount', 0) < 0)

        # Simple health score calculation
        debt_ratio = total_debt / (total_assets + 1) if total_assets > 0 else 1
        savings_score = min(total_assets / 100000, 1.0) * 40  # Up to 40 points for savings
        debt_score = max(0, (1 - debt_ratio) * 30)  # Up to 30 points for low debt
        spending_score = 30  # Base spending score

        health_score = int(savings_score + debt_score + spending_score)

        return {
            "health_score": health_score,
            "net_worth": net_worth,
            "debt_ratio": debt_ratio,
            "monthly_expenses": monthly_expenses,
            "calculation_method": "local"
        }

    def _fallback_local_analysis(self, user_data: dict) -> dict:
        """Fallback when local AI is not available"""
        return {
            "anonymized_profile": {
                "income_stability": 0.8,
                "spending_pattern": "consistent",
                "risk_tolerance": "moderate",
                "financial_discipline": 0.7
            },
            "processing_mode": "fallback"
        }

    def _fallback_quick_score(self, amount: int, category: str) -> dict:
        """Fallback quick scoring"""
        # Simple rule-based scoring
        score = 50  # Base score

        if category in ["investment", "education", "health"]:
            score += 20
        elif category in ["entertainment", "luxury"]:
            score -= 15

        if amount > 50000:
            score -= 10
        elif amount < 5000:
            score += 10

        return {
            "score": max(0, min(100, score)),
            "reasoning": f"Quick assessment for ₹{amount:,} {category} purchase",
            "processing_mode": "fallback"
        }
