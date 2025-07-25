# backend/services/user_service.py
from datetime import datetime
from typing import Dict, Optional, Any
import structlog
from backend.services.firestore_service import FirestoreService
from backend.services.auth_service import AuthService

logger = structlog.get_logger()


class UserService:
    """Service for user management operations"""

    def __init__(self, firestore_service: FirestoreService, auth_service: AuthService):
        self.firestore = firestore_service
        self.auth = auth_service

        logger.info("✅ User service initialized")

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user with hashed password"""
        try:
            # Hash password
            password_hash = self.auth.hash_password(user_data["password"])

            # Prepare user data for storage
            user_create_data = {
                **user_data,
                "password_hash": password_hash
            }
            del user_create_data["password"]  # Remove plain password

            # Create user in Firestore
            user_doc = await self.firestore.create_user(user_create_data)

            # Remove password hash from response
            user_response = user_doc.copy()
            del user_response["password_hash"]

            return user_response

        except Exception as e:
            logger.error("❌ Failed to create user", error=str(e))
            raise

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password"""
        try:
            # Get user by email
            user = await self.firestore.get_user_by_email(email)

            if not user:
                return None

            # Verify password
            if not self.auth.verify_password(password, user["password_hash"]):
                return None

            # Update last login
            await self.firestore.update_user(user["user_id"], {
                "last_login": datetime.now()
            })

            # Remove password hash from response
            user_response = user.copy()
            del user_response["password_hash"]

            return user_response

        except Exception as e:
            logger.error("❌ Authentication failed", email=email, error=str(e))
            return None

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            user = await self.firestore.get_user_by_id(user_id)

            if user:
                # Remove password hash
                user_response = user.copy()
                if "password_hash" in user_response:
                    del user_response["password_hash"]
                return user_response

            return None

        except Exception as e:
            logger.error("❌ Failed to get user", user_id=user_id, error=str(e))
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            user = await self.firestore.get_user_by_email(email)

            if user:
                # Remove password hash
                user_response = user.copy()
                if "password_hash" in user_response:
                    del user_response["password_hash"]
                return user_response

            return None

        except Exception as e:
            logger.error("❌ Failed to get user by email", email=email, error=str(e))
            return None

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile with preferences and goals"""
        try:
            user = await self.get_user(user_id)

            if not user:
                return {}

            return {
                "user_id": user["user_id"],
                "name": user["name"],
                "age": user.get("age"),
                "city": user.get("city"),
                "annual_income": user.get("annual_income"),
                "risk_tolerance": user.get("risk_tolerance", "moderate"),
                "preferences": user.get("preferences", {}),
                "goals": user.get("goals", {})
            }

        except Exception as e:
            logger.error("❌ Failed to get user profile", user_id=user_id, error=str(e))
            return {}

    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context for decision analysis"""
        try:
            user = await self.get_user(user_id)

            if not user:
                return {}

            return {
                "annual_income": user.get("annual_income", 0),
                "risk_tolerance": user.get("risk_tolerance", "moderate"),
                "age": user.get("age", 30),
                "city": user.get("city", ""),
                "financial_goals": user.get("goals", {}),
                "preferences": user.get("preferences", {})
            }

        except Exception as e:
            logger.error("❌ Failed to get user context", user_id=user_id, error=str(e))
            return {}

    async def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """Update user profile"""
        try:
            # Filter allowed fields
            allowed_fields = [
                "name", "age", "phone", "city", "annual_income",
                "risk_tolerance", "preferences", "goals"
            ]

            update_data = {
                key: value for key, value in profile_data.items()
                if key in allowed_fields
            }

            return await self.firestore.update_user(user_id, update_data)

        except Exception as e:
            logger.error("❌ Failed to update user profile", user_id=user_id, error=str(e))
            return False

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 User service cleaned up")
