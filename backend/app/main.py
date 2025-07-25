# backend/app/main.py
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.models import Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from datetime import datetime
import json
from typing import List, Optional, Dict, Any
import structlog
from prometheus_client import Counter, Histogram, generate_latest
import time

# Import our services
from backend.services.vertex_ai_service import VertexAIService
from backend.services.firestore_service import FirestoreService
from backend.services.opportunity_engine import OpportunityEngine
from backend.services.auth_service import AuthService
from backend.services.fi_mcp_service import FiMCPService
from backend.services.user_service import UserService
from backend.models.schemas import *
from backend.models.configs import get_settings
from backend.utils.logging_config import setup_logging
from backend.utils.middleware import MetricsMiddleware, RateLimitMiddleware

# Setup logging
setup_logging()
logger = structlog.get_logger()

# Metrics
REQUEST_COUNT = Counter('avestoai_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('avestoai_request_duration_seconds', 'Request duration')

# Load configuration
settings = get_settings()

# Global service instances
services: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management with proper service initialization"""
    logger.info("🚀 Starting AvestoAI backend services...")

    try:
        # Initialize core services
        services['firestore'] = FirestoreService(settings)
        services['vertex_ai'] = VertexAIService(settings)
        services['auth'] = AuthService(settings)
        services['fi_mcp'] = FiMCPService(settings)
        services['user'] = UserService(services['firestore'], services['auth'])

        # Initialize opportunity engine
        services['opportunity_engine'] = OpportunityEngine(
            services['vertex_ai'],
            services['firestore'],
            services['fi_mcp']
        )

        # Test all connections
        await services['firestore'].health_check()
        await services['vertex_ai'].health_check()
        await services['fi_mcp'].health_check()

        logger.info("✅ All services initialized successfully")
        yield

    except Exception as e:
        logger.error("❌ Failed to initialize services", error=str(e))
        raise
    finally:
        # Cleanup
        logger.info("🛑 Shutting down AvestoAI backend services...")
        for service_name, service in services.items():
            if hasattr(service, 'cleanup'):
                await service.cleanup()


# Create FastAPI app
app = FastAPI(
    title="🔮 AvestoAI API",
    description="Revolutionary Financial Intelligence Platform - Google Agentic AI Hackathon 2025",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RateLimitMiddleware, calls=100, period=60)  # 100 calls per minute

# Security
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate JWT token and get current user"""
    try:
        payload = services['auth'].verify_token(credentials.credentials)
        user_id = payload.get("user_id")
        user = await services['user'].get_user(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except Exception as e:
        logger.error("Authentication failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid authentication")


# Health and monitoring endpoints
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
            "vertex_ai": "connected" if services.get('vertex_ai') else "disconnected",
            "firestore": "connected" if services.get('firestore') else "disconnected",
            "fi_mcp": "connected" if services.get('fi_mcp') else "disconnected"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {},
        "version": "1.0.0"
    }

    try:
        # Check all services
        for service_name, service in services.items():
            if hasattr(service, 'health_check'):
                health_status["services"][service_name] = await service.health_check()

        # Determine overall status
        unhealthy_services = [
            name for name, status in health_status["services"].items()
            if status.get("status") != "healthy"
        ]

        if unhealthy_services:
            health_status["status"] = "degraded"
            health_status["unhealthy_services"] = unhealthy_services

        return health_status

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")


# Authentication endpoints
@app.post("/api/v1/auth/register", response_model=AuthResponse, tags=["Authentication"])
async def register_user(request: RegisterRequest):
    """Register a new user"""
    try:
        logger.info("👤 Registering new user", email=request.email)

        # Check if user already exists
        existing_user = await services['user'].get_user_by_email(request.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")

        # Create user
        user = await services['user'].create_user(request.dict())

        # Generate tokens
        access_token = services['auth'].create_access_token({"user_id": user["user_id"]})
        refresh_token = services['auth'].create_refresh_token({"user_id": user["user_id"]})

        logger.info("✅ User registered successfully", user_id=user["user_id"])

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserProfile(**user),
            token_type="bearer"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ User registration failed", error=str(e))
        raise HTTPException(status_code=500, detail="Registration failed")


@app.post("/api/v1/auth/login", response_model=AuthResponse, tags=["Authentication"])
async def login_user(request: LoginRequest):
    """Login user"""
    try:
        logger.info("🔐 User login attempt", email=request.email)

        # Authenticate user
        user = await services['user'].authenticate_user(request.email, request.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Generate tokens
        access_token = services['auth'].create_access_token({"user_id": user["user_id"]})
        refresh_token = services['auth'].create_refresh_token({"user_id": user["user_id"]})

        logger.info("✅ User logged in successfully", user_id=user["user_id"])

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserProfile(**user),
            token_type="bearer"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ User login failed", error=str(e))
        raise HTTPException(status_code=500, detail="Login failed")


# Core AI endpoints
@app.post("/api/v1/analyze-opportunities", response_model=OpportunityResponse, tags=["Intelligence"])
async def analyze_opportunities(
        request: OpportunityRequest,
        current_user: dict = Depends(get_current_user),
        background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Analyze financial opportunities using hybrid AI and Fi MCP data"""
    start_time = time.time()

    try:
        logger.info("🔍 Starting opportunity analysis", user_id=current_user["user_id"])

        # Get comprehensive financial data from Fi MCP
        fi_data = await services['fi_mcp'].get_user_financial_data(current_user["user_id"])

        # Get user profile and preferences
        user_profile = await services['user'].get_user_profile(current_user["user_id"])

        # Combine Fi data with user profile
        comprehensive_data = {
            **fi_data,
            "user_profile": user_profile,
            "preferences": user_profile.get("preferences", {}),
            "goals": user_profile.get("goals", {})
        }

        # Generate opportunities using AI
        opportunities = await services['opportunity_engine'].generate_opportunities(
            user_data=comprehensive_data,
            analysis_type=request.analysis_type
        )

        # Store analysis results
        background_tasks.add_task(
            services['firestore'].store_analysis,
            current_user["user_id"],
            opportunities
        )

        processing_time = (time.time() - start_time) * 1000

        logger.info("✅ Opportunity analysis completed",
                    user_id=current_user["user_id"],
                    opportunities_found=len(opportunities.opportunities),
                    processing_time=f"{processing_time:.1f}ms")

        return OpportunityResponse(
            **opportunities,
            processing_time=processing_time,
            data_sources=["fi_mcp", "vertex_ai", "firestore"]
        )

    except Exception as e:
        logger.error("❌ Opportunity analysis failed",
                     user_id=current_user["user_id"],
                     error=str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/v1/predict-decision", response_model=DecisionResponse, tags=["Intelligence"])
async def predict_decision(
        request: DecisionRequest,
        current_user: dict = Depends(get_current_user)
):
    """Score financial decisions with AI prediction"""
    start_time = time.time()

    try:
        logger.info("🎯 Starting decision analysis",
                    user_id=current_user["user_id"],
                    amount=request.amount,
                    category=request.category)

        # Get current financial state from Fi MCP
        financial_state = await services['fi_mcp'].get_current_financial_state(current_user["user_id"])

        # Get user context
        user_context = await services['user'].get_user_context(current_user["user_id"])

        # Enhanced decision request with real data
        enhanced_request = DecisionRequest(
            **request.dict(),
            user_context={
                **request.user_context,
                **financial_state,
                **user_context
            }
        )

        # Analyze decision using Vertex AI
        decision_analysis = await services['vertex_ai'].analyze_financial_decision(enhanced_request)

        processing_time = (time.time() - start_time) * 1000

        response = DecisionResponse(
            **decision_analysis,
            processing_time=processing_time,
            data_sources=["fi_mcp", "vertex_ai"]
        )

        logger.info("✅ Decision analysis completed",
                    user_id=current_user["user_id"],
                    score=response.score,
                    processing_time=f"{processing_time:.1f}ms")

        return response

    except Exception as e:
        logger.error("❌ Decision analysis failed",
                     user_id=current_user["user_id"],
                     error=str(e))
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.get("/api/v1/financial-dashboard/{user_id}", response_model=DashboardResponse, tags=["Dashboard"])
async def get_financial_dashboard(
        user_id: str,
        current_user: dict = Depends(get_current_user)
):
    """Get comprehensive financial dashboard"""
    try:
        # Verify user access
        if current_user["user_id"] != user_id and current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Access denied")

        logger.info("📊 Generating financial dashboard", user_id=user_id)

        # Get comprehensive data from Fi MCP
        financial_data = await services['fi_mcp'].get_comprehensive_financial_data(user_id)

        # Get recent opportunities and predictions
        recent_analysis = await services['firestore'].get_recent_analysis(user_id, limit=5)

        # Calculate financial health score
        health_score = await services['vertex_ai'].calculate_financial_health_score(financial_data)

        # Generate insights
        insights = await services['vertex_ai'].generate_dashboard_insights(financial_data)

        dashboard = DashboardResponse(
            user_id=user_id,
            financial_summary=financial_data.get("summary", {}),
            health_score=health_score,
            recent_opportunities=recent_analysis.get("opportunities", []),
            insights=insights,
            charts_data=financial_data.get("charts", []),
            last_updated=datetime.now(),
            data_sources=["fi_mcp", "vertex_ai", "firestore"]
        )

        logger.info("✅ Dashboard generated successfully", user_id=user_id)
        return dashboard

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Dashboard generation failed", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Dashboard generation failed")


@app.get("/api/v1/financial-health-stream/{user_id}", tags=["Streaming"])
async def stream_financial_health(
        user_id: str,
        current_user: dict = Depends(get_current_user)
):
    """Real-time financial health monitoring"""

    # Verify access
    if current_user["user_id"] != user_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    async def generate_health_updates():
        """Generate real-time health updates"""
        try:
            while True:
                # Get real-time data from Fi MCP
                current_data = await services['fi_mcp'].get_real_time_data(user_id)

                # Calculate health metrics
                health_metrics = await services['vertex_ai'].calculate_real_time_health(current_data)

                # Detect anomalies
                anomalies = await services['vertex_ai'].detect_financial_anomalies(current_data)

                # Create update
                update = {
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                    "health_score": health_metrics.get("score", 0),
                    "metrics": health_metrics.get("metrics", {}),
                    "anomalies": anomalies,
                    "alerts": health_metrics.get("alerts", []),
                    "trends": health_metrics.get("trends", {})
                }

                yield f"data: {json.dumps(update)}\n\n"

                # Wait 10 seconds before next update
                await asyncio.sleep(10)

        except Exception as e:
            error_data = {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id
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


@app.post("/api/v1/chat", response_model=ChatResponse, tags=["AI Chat"])
async def chat_with_ai(
        request: ChatRequest,
        current_user: dict = Depends(get_current_user)
):
    """Conversational AI interface for financial questions"""
    start_time = time.time()

    try:
        logger.info("💬 Processing chat message",
                    user_id=current_user["user_id"],
                    message_length=len(request.message))

        # Get user's financial context from Fi MCP
        financial_context = await services['fi_mcp'].get_user_context_for_chat(current_user["user_id"])

        # Get conversation history
        conversation_history = await services['firestore'].get_conversation_history(
            current_user["user_id"],
            limit=10
        )

        # Generate AI response
        ai_response = await services['vertex_ai'].generate_chat_response(
            message=request.message,
            financial_context=financial_context,
            conversation_history=conversation_history,
            user_preferences=current_user.get("preferences", {})
        )

        # Store conversation
        await services['firestore'].store_conversation_turn(
            current_user["user_id"],
            request.message,
            ai_response.get("response", "")
        )

        processing_time = (time.time() - start_time) * 1000

        chat_response = ChatResponse(
            **ai_response,
            processing_time=processing_time,
            data_sources=["fi_mcp", "vertex_ai", "firestore"]
        )

        logger.info("✅ Chat response generated",
                    user_id=current_user["user_id"],
                    processing_time=f"{processing_time:.1f}ms")

        return chat_response

    except Exception as e:
        logger.error("❌ Chat processing failed",
                     user_id=current_user["user_id"],
                     error=str(e))
        raise HTTPException(status_code=500, detail="Chat processing failed")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )
