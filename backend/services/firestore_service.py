# backend/services/firestore_service.py - Remove user-related operations
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timedelta
import json
import asyncio
from typing import Dict, List, Optional, Any
import structlog
import uuid
from backend.models.configs import Settings

logger = structlog.get_logger()


class FirestoreService:
    """Service for Firestore database operations (Fi MCP mode)"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)

        # Collection references (mobile number based)
        self.conversations_collection = "conversations"
        self.opportunities_collection = "opportunities"
        self.analyses_collection = "analyses"

        logger.info("✅ Firestore service initialized (Fi MCP mode)")

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

    async def store_analysis(self, mobile_number: str, analysis_data: Dict[str, Any]) -> str:
        """Store analysis results for mobile number"""
        try:
            analysis_id = str(uuid.uuid4())

            doc_data = {
                "analysis_id": analysis_id,
                "mobile_number": mobile_number,
                "analysis_type": analysis_data.get("type", "opportunity"),
                "data": analysis_data,
                "created_at": datetime.now(),
                "ttl": datetime.now() + timedelta(days=90)
            }

            await asyncio.to_thread(
                self.db.collection(self.analyses_collection).document(analysis_id).set,
                doc_data
            )

            return analysis_id

        except Exception as e:
            logger.error("❌ Failed to store analysis", mobile_number=mobile_number, error=str(e))
            return ""

    async def get_recent_analysis(self, mobile_number: str, limit: int = 5) -> Dict[str, Any]:
        """Get recent analysis results for mobile number"""
        try:
            query = (self.db.collection(self.analyses_collection)
                     .where("mobile_number", "==", mobile_number)
                     .order_by("created_at", direction=firestore.Query.DESCENDING)
                     .limit(limit))

            docs = await asyncio.to_thread(query.stream)

            analyses = []
            for doc in docs:
                data = doc.to_dict()
                analyses.append(data["data"])

            return {"opportunities": analyses}

        except Exception as e:
            logger.error("❌ Failed to get recent analysis", mobile_number=mobile_number, error=str(e))
            return {"opportunities": []}

    async def store_conversation_turn(self, mobile_number: str, user_message: str, ai_response: str) -> str:
        """Store conversation turn for mobile number"""
        try:
            conversation_id = f"{mobile_number}_{datetime.now().strftime('%Y%m%d')}"

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
                    "mobile_number": mobile_number
                }
            )

            return conversation_id

        except Exception as e:
            # If document doesn't exist, create it
            try:
                conversation_doc = {
                    "conversation_id": conversation_id,
                    "mobile_number": mobile_number,
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
                             mobile_number=mobile_number, error=str(create_error))
                return ""

    async def get_conversation_history(self, mobile_number: str, limit: int = 10) -> List[Dict[str, str]]:
        """Get conversation history for mobile number"""
        try:
            conversation_id = f"{mobile_number}_{datetime.now().strftime('%Y%m%d')}"

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
                         mobile_number=mobile_number, error=str(e))
            return []

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Firestore service cleaned up")
