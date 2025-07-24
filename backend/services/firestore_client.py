# backend/services/firestore_client.py
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timedelta
import json
import asyncio
from typing import Dict, List, Optional


class FirestoreClient:
    def __init__(self):
        self.db = firestore.Client()
        self.users_collection = "users"
        self.transactions_collection = "transactions"
        self.opportunities_collection = "opportunities"
        self.alerts_collection = "alerts"

    async def get_user_data(self, user_id: str) -> dict:
        """Get comprehensive user financial data"""
        try:
            # Get user profile
            user_ref = self.db.collection(self.users_collection).document(user_id)
            user_doc = await asyncio.to_thread(user_ref.get)

            if not user_doc.exists:
                # Create demo user data
                demo_data = self._create_demo_user_data(user_id)
                await asyncio.to_thread(user_ref.set, demo_data)
                return demo_data

            user_data = user_doc.to_dict()

            # Get recent transactions
            transactions = await self._get_user_transactions(user_id, days=90)
            user_data['transactions'] = transactions

            return user_data

        except Exception as e:
            print(f"Error getting user data: {e}")
            return self._create_demo_user_data(user_id)

    async def _get_user_transactions(self, user_id: str, days: int = 30) -> List[dict]:
        """Get user transactions from last N days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            transactions_ref = (self.db.collection(self.transactions_collection)
                                .where("user_id", "==", user_id)
                                .where("date", ">=", cutoff_date)
                                .order_by("date", direction=firestore.Query.DESCENDING)
                                .limit(100))

            docs = await asyncio.to_thread(transactions_ref.stream)
            transactions = []

            async for doc in docs:
                transaction_data = doc.to_dict()
                transaction_data['id'] = doc.id
                transactions.append(transaction_data)

            return transactions

        except Exception as e:
            print(f"Error getting transactions: {e}")
            return self._generate_demo_transactions(user_id, days)

    async def store_analysis(self, user_id: str, analysis_data: dict) -> str:
        """Store analysis results in Firestore"""
        try:
            doc_data = {
                "user_id": user_id,
                "analysis": analysis_data,
                "timestamp": datetime.now(),
                "ttl": datetime.now() + timedelta(days=30)  # Auto-delete after 30 days
            }

            doc_ref = self.db.collection(self.opportunities_collection).document()
            await asyncio.to_thread(doc_ref.set, doc_data)

            return doc_ref.id

        except Exception as e:
            print(f"Error storing analysis: {e}")
            return "error"

    async def get_real_time_data(self, user_id: str) -> dict:
        """Get real-time financial data for streaming"""
        try:
            # Get latest account balances
            user_data = await self.get_user_data(user_id)

            # Get very recent transactions (last 24 hours)
            recent_transactions = await self._get_user_transactions(user_id, days=1)

            return {
                "accounts": user_data.get("accounts", {}),
                "transactions": recent_transactions,
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"Error getting real-time data: {e}")
            return {"error": str(e)}

    async def store_alert(self, user_id: str, alert_data: dict) -> str:
        """Store financial alert"""
        try:
            doc_data = {
                "user_id": user_id,
                "alert": alert_data,
                "created_at": datetime.now(),
                "status": "active",
                "ttl": datetime.now() + timedelta(days=7)
            }

            doc_ref = self.db.collection(self.alerts_collection).document()
            await asyncio.to_thread(doc_ref.set, doc_data)

            return doc_ref.id

        except Exception as e:
            print(f"Error storing alert: {e}")
            return "error"

    def _create_demo_user_data(self, user_id: str) -> dict:
        """Create realistic demo user data for hackathon"""
        return {
            "user_id": user_id,
            "profile": {
                "age": 28,
                "income": 1200000,  # ₹12 LPA
                "city": "Bangalore",
                "risk_tolerance": "moderate"
            },
            "accounts": {
                "savings": 180000,
                "checking": 25000,
                "credit_used": 45000,
                "credit_limit": 200000
            },
            "investments": {
                "mutual_funds": 350000,
                "stocks": 120000,
                "ppf": 150000,
                "fd": 250000
            },
            "goals": {
                "emergency_fund": {"target": 600000, "current": 180000},
                "house_down_payment": {"target": 2000000, "current": 470000},
                "retirement": {"target": 50000000, "current": 870000}
            },
            "created_at": datetime.now(),
            "last_updated": datetime.now()
        }

    def _generate_demo_transactions(self, user_id: str, days: int) -> List[dict]:
        """Generate realistic demo transactions"""
        import random

        transactions = []
        base_date = datetime.now() - timedelta(days=days)

        for i in range(days):
            date = base_date + timedelta(days=i)

            # Salary on 1st of month
            if date.day == 1:
                transactions.append({
                    "user_id": user_id,
                    "date": date,
                    "amount": 100000,  # Monthly salary
                    "category": "salary",
                    "description": "Monthly Salary Credit",
                    "account": "checking"
                })

            # Random daily expenses
            if date.weekday() < 5:  # Weekdays
                transactions.append({
                    "user_id": user_id,
                    "date": date,
                    "amount": -random.randint(200, 800),
                    "category": "food",
                    "description": f"Lunch/Coffee",
                    "account": "checking"
                })

            # Random other expenses
            if random.random() < 0.3:  # 30% chance of other expense
                amount = -random.randint(1000, 15000)
                category = random.choice(["shopping", "entertainment", "transport", "utilities"])
                transactions.append({
                    "user_id": user_id,
                    "date": date,
                    "amount": amount,
                    "category": category,
                    "description": f"{category.title()} expense",
                    "account": "checking"
                })

        return transactions
