# backend/migrations/init_db.py
import asyncio
from google.cloud import firestore
from datetime import datetime
import structlog

logger = structlog.get_logger()


class DatabaseInitializer:
    """Initialize Firestore database with required collections and indexes"""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.db = firestore.Client(project=project_id)

    async def initialize(self):
        """Initialize database"""
        logger.info("🗄️ Initializing Firestore database...")

        try:
            await self._create_collections()
            await self._create_indexes()
            await self._seed_data()

            logger.info("✅ Database initialization completed")

        except Exception as e:
            logger.error("❌ Database initialization failed", error=str(e))
            raise

    async def _create_collections(self):
        """Create required collections"""
        collections = [
            "users",
            "conversations",
            "opportunities",
            "analyses",
            "financial_goals",
            "health_check"
        ]

        for collection_name in collections:
            # Create a dummy document to ensure collection exists
            doc_ref = self.db.collection(collection_name).document("_init")
            await asyncio.to_thread(
                doc_ref.set,
                {
                    "created_at": datetime.now(),
                    "purpose": "Collection initialization",
                    "delete_me": True
                }
            )

            logger.info(f"✓ Collection created: {collection_name}")

    async def _create_indexes(self):
        """Create database indexes for better performance"""
        # Note: Firestore indexes are typically created through the console
        # or gcloud commands. This is a placeholder for documentation.

        indexes_needed = [
            {
                "collection": "users",
                "fields": ["email", "created_at"]
            },
            {
                "collection": "conversations",
                "fields": ["user_id", "last_updated"]
            },
            {
                "collection": "analyses",
                "fields": ["user_id", "created_at"]
            }
        ]

        logger.info("📝 Indexes needed (create manually in Firestore console):")
        for index in indexes_needed:
            logger.info(f"  • {index['collection']}: {index['fields']}")

    async def _seed_data(self):
        """Seed database with initial data"""
        # Create health check document
        health_doc = {
            "service": "avestoai",
            "initialized_at": datetime.now(),
            "version": "1.0.0"
        }

        await asyncio.to_thread(
            self.db.collection("health_check").document("status").set,
            health_doc
        )

        logger.info("✓ Seed data created")


async def main():
    """Run database initialization"""
    import os
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    if not project_id:
        logger.error("GOOGLE_CLOUD_PROJECT environment variable not set")
        return

    initializer = DatabaseInitializer(project_id)
    await initializer.initialize()


if __name__ == "__main__":
    asyncio.run(main())
