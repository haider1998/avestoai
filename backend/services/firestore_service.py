# backend/services/firestore_service.py
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timedelta
import json
import asyncio
from typing import Dict, List, Optional, Any
import structlog
import hashlib
import uuid
from backend.models.configs import Settings

logger = structlog.get_logger()


class FirestoreService:
    """Service for Firestore database operations"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)

        # Collection references
        self.users_collection = "users"
        self.conversations_collection = "conversations"
        self.opportunities_collection = "opportunities"
        self.analyses_collection = "analyses"
        self.goals_collection = "financial_goals"

        logger.info("✅ Firestore service initialized")

    async def health_check(self) -> Dict[str, Any]:
        """Check Firestore service health"""
        try:
            start_time = datetime.now()

            # Test connection with a simple read
            test_doc = self.db.collection("health_check").document("test")
            await asyncio.to_thread(test_doc.get)

            response_time = (datetime.now() - start_time).total_seconds() * 1000

            return {
                "status": "healthy",
                "response_time": response_time,
                "last_check": datetime.now()
            }

        except Exception as e:
            logger.error("❌ Firestore health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "last_check": datetime.now(),
                "error": str(e)
            }

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
        try:
            user_id = str(uuid.uuid4())

            user_doc = {
                "user_id": user_id,
                "email": user_data["email"],
                "name": user_data["name"],
                "age": user_data.get("age"),
                "phone": user_data.get("phone"),
                "city": user_data.get("city"),
                "annual_income": user_data.get("annual_income"),
                "risk_tolerance": user_data.get("risk_tolerance", "moderate"),
                "password_hash": user_data["password_hash"],
                "role": "user",
                "is_active": True,
                "created_at": datetime.now(),
                "last_login": None,
                "preferences": {},
                "goals": {},
                "metadata": {
                    "registration_source": "api",
                    "email_verified": False
                }
            }

            # Store in Firestore
            await asyncio.to_thread(
                self.db.collection(self.users_collection).document(user_id).set,
                user_doc
            )

            logger.info("✅ User created successfully", user_id=user_id)
            return user_doc

        except Exception as e:
            logger.error("❌ Failed to create user", error=str(e))
            raise

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            doc_ref = self.db.collection(self.users_collection).document(user_id)
            doc = await asyncio.to_thread(doc_ref.get)

            if doc.exists:
                return doc.to_dict()
            return None

        except Exception as e:
            logger.error("❌ Failed to get user", user_id=user_id, error=str(e))
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            query = self.db.collection(self.users_collection).where("email", "==", email)
            docs = await asyncio.to_thread(query.stream)

            for doc in docs:
                return doc.to_dict()
            return None

        except Exception as e:
            logger.error("❌ Failed to get user by email", email=email, error=str(e))
            return None

    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user data"""
        try:
            update_data["updated_at"] = datetime.now()

            await asyncio.to_thread(
                self.db.collection(self.users_collection).document(user_id).update,
                update_data
            )

            logger.info("✅ User updated successfully", user_id=user_id)
            return True

        except Exception as e:
            logger.error("❌ Failed to update user", user_id=user_id, error=str(e))
            return False

    async def store_analysis(self, user_id: str, analysis_data: Dict[str, Any]) -> str:
        """Store analysis results"""
        try:
            analysis_id = str(uuid.uuid4())

            doc_data = {
                "analysis_id": analysis_id,
                "user_id": user_id,
                "analysis_type": analysis_data.get("type", "opportunity"),
                "data": analysis_data,
                "created_at": datetime.now(),
                "ttl": datetime.now() + timedelta(days=90)  # Auto-delete after 90 days
            }

            await asyncio.to_thread(
                self.db.collection(self.analyses_collection).document(analysis_id).set,
                doc_data
            )

            return analysis_id

        except Exception as e:
            logger.error("❌ Failed to store analysis", user_id=user_id, error=str(e))
            return ""

    async def get_recent_analysis(self, user_id: str, limit: int = 5) -> Dict[str, Any]:
        """Get recent analysis results"""
        try:
            query = (self.db.collection(self.analyses_collection)
                     .where("user_id", "==", user_id)
                     .order_by("created_at", direction=firestore.Query.DESCENDING)
                     .limit(limit))

            docs = await asyncio.to_thread(query.stream)

            analyses = []
            for doc in docs:
                data = doc.to_dict()
                analyses.append(data["data"])

            return {"opportunities": analyses}

        except Exception as e:
            logger.error("❌ Failed to get recent analysis", user_id=user_id, error=str(e))
            return {"opportunities": []}

    async def store_conversation_turn(self, user_id: str, user_message: str, ai_response: str) -> str:
        """Store conversation turn"""
        try:
            conversation_id = f"{user_id}_{datetime.now().strftime('%Y%m%d')}"

            turn_data = {
                "timestamp": datetime.now(),
                "user_message": user_message,
                "ai_response": ai_response,
                "message_id": str(uuid.uuid4())
            }

            # Update or create conversation document
            doc_ref = self.db.collection(self.conversations_collection).document(conversation_id)

            await asyncio.to_thread(
                doc_ref.update,
                {
                    "turns": firestore.ArrayUnion([turn_data]),
                    "last_updated": datetime.now(),
                    "user_id": user_id
                }
            )

            return conversation_id

        except Exception as e:
            # If document doesn't exist, create it
            try:
                conversation_doc = {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "created_at": datetime.now(),
                    "last_updated": datetime.now(),
                    "turns": [turn_data],
                    "ttl": datetime.now() + timedelta(days=30)
                }

                await asyncio.to_thread(
                    doc_ref.set,
                    conversation_doc
                )

                return conversation_id

            except Exception as create_error:
                logger.error("❌ Failed to store conversation",
                             user_id=user_id, error=str(create_error))
                return ""

    async def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Get conversation history"""
        try:
            conversation_id = f"{user_id}_{datetime.now().strftime('%Y%m%d')}"

            doc_ref = self.db.collection(self.conversations_collection).document(conversation_id)
            doc = await asyncio.to_thread(doc_ref.get)

            if doc.exists:
                data = doc.to_dict()
                turns = data.get("turns", [])

                # Return last N turns
                recent_turns = turns[-limit:] if len(turns) > limit else turns

                return [
                    {
                        "user": turn["user_message"],
                        "ai": turn["ai_response"],
                        "timestamp": turn["timestamp"]
                    }
                    for turn in recent_turns
                ]

            return []

        except Exception as e:
            logger.error("❌ Failed to get conversation history",
                         user_id=user_id, error=str(e))
            return []

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Firestore service cleaned up")
