# backend/main.py
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from datetime import datetime
import json
from typing import List, Optional, Dict, Any
import structlog

# Import our services
from services.vertex_ai_client import VertexAIClient
from services.firestore_client import FirestoreClient
from services.opportunity_engine import OpportunityEngine
from services.on_device_ai import OnDeviceAI
from services.auth_service import AuthService
from models.schemas import *
from models.config import Settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Load configuration
settings = Settings()

# Global service instances
vertex_client: Optional[VertexAIClient] = None
firestore_client: Optional[FirestoreClient] = None
opportunity_engine: Optional[OpportunityEngine] = None
on_device_ai: Optional[OnDeviceAI] = None
auth_service: Optional[AuthService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting AvestoAI backend services...")

    global vertex_client, firestore_client, opportunity_engine, on_device_ai, auth_service

    try:
        # Initialize services
        vertex_client = VertexAIClient(settings)
        firestore_client = FirestoreClient(settings)
        auth_service = AuthService(settings)

        # Initialize on-device AI
        on_device_ai = OnDeviceAI(settings)
        await on_device_ai.initialize_model()

        # Initialize opportunity engine
        opportunity_engine = OpportunityEngine(vertex_client, firestore_client, on_device_ai)

        # Test connections
        await vertex_client.health_check()
        await firestore_client.health_check()

        logger.info("✅ All services initialized successfully")

        yield

    except Exception as e:
        logger.error("❌ Failed to initialize services", error=str(e))
        raise

    # Shutdown
    logger.info("🛑 Shutting down AvestoAI backend services...")
    if on_device_ai:
        await on_device_ai.cleanup()


# Create FastAPI app
app = FastAPI(
    title="🔮 AvestoAI API",
    description="Revolutionary Financial Intelligence Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate JWT token and get current user"""
    try:
        payload = auth_service.verify_token(credentials.credentials)
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication")


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with service status"""
    return {
        "service": "🔮 AvestoAI API",
        "status": "operational",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "environment": settings.ENVIRONMENT,
        "services": {
            "vertex_ai": "connected" if vertex_client else "disconnected",
            "firestore": "connected" if firestore_client else "disconnected",
            "on_device_ai": "loaded" if on_device_ai and on_device_ai.model_loaded else "not_loaded"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }

    try:
        # Check Vertex AI
        if vertex_client:
            vertex_status = await vertex_client.health_check()
            health_status["services"]["vertex_ai"] = vertex_status

        # Check Firestore
        if firestore_client:
            firestore_status = await firestore_client.health_check()
            health_status["services"]["firestore"] = firestore_status

        # Check On-Device AI
        if on_device_ai:
            health_status["services"]["on_device_ai"] = {
                "status": "healthy" if on_device_ai.model_loaded else "unhealthy",
                "model_loaded": on_device_ai.model_loaded
            }

        return health_status

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.post("/api/v1/analyze-opportunities", response_model=OpportunityResponse, tags=["Intelligence"])
async def analyze_opportunities(
        request: OpportunityRequest,
        current_user: dict = Depends(get_current_user),
        background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Main endpoint for financial opportunity analysis"""
    try:
        logger.info("🔍 Starting opportunity analysis", user_id=request.user_id)

        # Get user financial data
        user_data = await firestore_client.get_user_data(request.user_id)

        if not user_data:
            raise HTTPException(status_code=404, detail="User data not found")

        # Use hybrid AI approach
        # 1. On-device analysis for privacy-sensitive data
        private_insights = await on_device_ai.analyze_sensitive_data(user_data)

        # 2. Cloud analysis for complex market insights
        market_insights = await vertex_client.analyze_market_opportunities(
            user_profile=private_insights.anonymized_profile
        )

        # 3. Combine insights to generate opportunities
        opportunities = await opportunity_engine.generate_opportunities(
            private_insights, market_insights, user_data
        )

        # Store results asynchronously
        background_tasks.add_task(
            firestore_client.store_analysis,
            request.user_id,
            opportunities
        )

        logger.info("✅ Opportunity analysis completed",
                    user_id=request.user_id,
                    opportunities_found=len(opportunities.opportunities))

        return opportunities

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Opportunity analysis failed",
                     user_id=request.user_id,
                     error=str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/v1/predict-decision", response_model=DecisionResponse, tags=["Intelligence"])
async def predict_decision(
        request: DecisionRequest,
        current_user: dict = Depends(get_current_user)
):
    """Score financial decisions with AI prediction"""
    try:
        logger.info("🎯 Starting decision analysis",
                    amount=request.amount,
                    category=request.category)

        # Fast on-device scoring for immediate feedback
        quick_score = await on_device_ai.quick_decision_score(
            amount=request.amount,
            category=request.category,
            user_context=request.user_context
        )

        # Detailed cloud analysis for comprehensive insights
        detailed_analysis = await vertex_client.deep_decision_analysis(request)

        response = DecisionResponse(
            score=detailed_analysis.get("score", quick_score.get("score", 50)),
            quick_score=quick_score.get("score"),
            explanation=detailed_analysis.get("explanation", "Analysis completed"),
            alternatives=detailed_analysis.get("alternatives", []),
            long_term_impact=detailed_analysis.get("projections", {}),
            processing_mode="hybrid",
            confidence=detailed_analysis.get("confidence", 0.8)
        )

        logger.info("✅ Decision analysis completed",
                    score=response.score,
                    processing_time=f"{response.processing_time}ms")

        return response

    except Exception as e:
        logger.error("❌ Decision analysis failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.get("/api/v1/financial-health-stream/{user_id}", tags=["Intelligence"])
async def stream_financial_health(
        user_id: str,
        current_user: dict = Depends(get_current_user)
):
    """Real-time financial health monitoring using Server-Sent Events"""

    async def generate_health_updates():
        """Generate real-time health updates"""
        try:
            while True:
                # Get real-time data
                current_data = await firestore_client.get_real_time_data(user_id)

                # Analyze with on-device AI (privacy-first)
                health_score = await on_device_ai.calculate_health_score(current_data)

                # Detect anomalies
                alerts = await on_device_ai.detect_spending_anomalies(current_data)

                # Create update
                update = {
                    "health_score": health_score,
                    "alerts": alerts,
                    "timestamp": datetime.now().isoformat(),
                    "net_worth": current_data.get("net_worth", 0),
                    "cash_flow": current_data.get("cash_flow", {})
                }

                yield f"data: {json.dumps(update)}\n\n"

                # Wait 5 seconds before next update
                await asyncio.sleep(5)

        except Exception as e:
            error_data = {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_health_updates(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )


@app.post("/api/v1/chat", response_model=ChatResponse, tags=["Intelligence"])
async def chat_with_ai(
        request: ChatRequest,
        current_user: dict = Depends(get_current_user)
):
    """Conversational AI interface for financial questions"""
    try:
        logger.info("💬 Processing chat message",
                    user_id=request.user_id,
                    message_length=len(request.message))

        # Get user context
        user_data = await firestore_client.get_user_data(request.user_id)

        # Route query based on complexity
        if await on_device_ai.should_process_locally(request.message):
            # Simple query - process locally
            response = await on_device_ai.generate_local_response(
                request.message,
                user_data
            )
            processing_location = "local"
        else:
            # Complex query - use cloud AI
            response = await vertex_client.generate_chat_response(
                request.message,
                user_data,
                request.conversation_history
            )
            processing_location = "cloud"

        chat_response = ChatResponse(
            response=response.get("response", "I'm here to help with your financial questions."),
            processing_location=processing_location,
            suggestions=response.get("suggestions", []),
            charts=response.get("charts", []),
            confidence=response.get("confidence", 0.8)
        )

        logger.info("✅ Chat response generated",
                    processing_location=processing_location,
                    response_length=len(chat_response.response))

        return chat_response

    except Exception as e:
        logger.error("❌ Chat processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/api/v1/users", response_model=UserResponse, tags=["Users"])
async def create_user(request: CreateUserRequest):
    """Create new user account"""
    try:
        # Create user in Firestore
        user_data = await firestore_client.create_user(request.dict())

        # Generate JWT token
        token = auth_service.create_access_token({"user_id": user_data["user_id"]})

        return UserResponse(
            user_id=user_data["user_id"],
            token=token,
            created_at=user_data["created_at"]
        )

    except Exception as e:
        logger.error("❌ User creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"User creation failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )
