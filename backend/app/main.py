# backend/app/main.py
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn
from datetime import datetime
import json
from typing import List, Optional, Dict, Any
import structlog
from prometheus_client import Counter, Histogram, generate_latest
import time

# Import our services (removed auth and user services)
from backend.services.vertex_ai_service import VertexAIService
from backend.services.firestore_service import FirestoreService
from backend.services.opportunity_engine import OpportunityEngine
from backend.services.fi_mcp_service import FiMCPService
from backend.models.schemas import *
from backend.models.configs import get_settings
from backend.utils.logging_config import setup_logging
from backend.utils.middleware import MetricsMiddleware, RateLimitMiddleware

# Setup logging
setup_logging()
logger = structlog.get_logger()

# Metrics - Check if they already exist to avoid duplication
try:
    REQUEST_COUNT = Counter('avestoai_requests_total', 'Total requests', ['method', 'endpoint'])
    REQUEST_DURATION = Histogram('avestoai_request_duration_seconds', 'Request duration')
except ValueError as e:
    if "Duplicated timeseries" in str(e):
        # Metrics already exist, get them from the registry
        from prometheus_client import REGISTRY
        for collector in list(REGISTRY._collector_to_names.keys()):
            if hasattr(collector, '_name'):
                if collector._name == 'avestoai_requests_total':
                    REQUEST_COUNT = collector
                elif collector._name == 'avestoai_request_duration_seconds':
                    REQUEST_DURATION = collector
    else:
        raise e

# Load configuration
settings = get_settings()

# Global service instances
services: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management with proper service initialization"""
    logger.info("🚀 Starting AvestoAI backend services...")

    try:
        # Initialize core services (removed auth and user services)
        services['firestore'] = FirestoreService(settings)
        services['vertex_ai'] = VertexAIService(settings)
        services['fi_mcp'] = FiMCPService(settings)

        # Initialize opportunity engine
        services['opportunity_engine'] = OpportunityEngine(
            services['vertex_ai'],
            services['firestore'],
            services['fi_mcp']
        )

        # Test connections
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
    description="Revolutionary Financial Intelligence Platform with Fi MCP Integration",
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
app.add_middleware(RateLimitMiddleware, calls=100, period=60)


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
        "authentication": "Fi MCP Mobile + OTP",
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
    from fastapi.responses import Response
    return Response(generate_latest(), media_type="text/plain")


# Fi MCP Authentication endpoints
@app.post("/api/v1/fi-auth/initiate", response_model=FiAuthInitiateResponse, tags=["Fi MCP Auth"])
async def initiate_fi_auth(request: FiAuthInitiateRequest):
    """Initiate Fi MCP authentication process"""
    try:
        logger.info("🔐 Initiating Fi MCP authentication", mobile_number=request.mobile_number)

        # Initialize or get existing session for this mobile number
        session_result = await services['fi_mcp'].initiate_session(request.mobile_number, request.scenario)

        return FiAuthInitiateResponse(
            session_id=session_result["session_id"],
            login_url=session_result.get("login_url"),
            mobile_number=request.mobile_number,
            scenario=request.scenario,
            requires_authentication=session_result["requires_authentication"],
            message="Please complete authentication if login_url is provided"
        )

    except Exception as e:
        logger.error("❌ Fi MCP authentication initiation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Authentication initiation failed: {str(e)}")


@app.post("/api/v1/fi-auth/verify", response_model=FiAuthVerifyResponse, tags=["Fi MCP Auth"])
async def verify_fi_auth(request: FiAuthVerifyRequest):
    """Verify Fi MCP authentication with OTP"""
    try:
        logger.info("🔐 Verifying Fi MCP authentication",
                    mobile_number=request.mobile_number,
                    session_id=request.session_id)

        # Verify authentication with Fi MCP
        verification_result = await services['fi_mcp'].verify_authentication(
            request.session_id,
            request.mobile_number,
            request.otp
        )

        if verification_result["success"]:
            # Get initial financial data
            financial_data = await services['fi_mcp'].get_user_financial_data(
                request.mobile_number,
                scenario=verification_result.get("scenario", "balanced")
            )

            return FiAuthVerifyResponse(
                success=True,
                session_id=request.session_id,
                mobile_number=request.mobile_number,
                scenario=verification_result.get("scenario", "balanced"),
                net_worth=financial_data.get("net_worth", {}).get("total_value", 0),
                accounts_count=len(financial_data.get("accounts", [])),
                message="Authentication successful"
            )
        else:
            return FiAuthVerifyResponse(
                success=False,
                session_id=request.session_id,
                mobile_number=request.mobile_number,
                message=verification_result.get("message", "Authentication failed")
            )

    except Exception as e:
        logger.error("❌ Fi MCP authentication verification failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Authentication verification failed: {str(e)}")


@app.get("/api/v1/fi-auth/status/{mobile_number}", response_model=FiAuthStatusResponse, tags=["Fi MCP Auth"])
async def get_fi_auth_status(mobile_number: str):
    """Get Fi MCP authentication status"""
    try:
        status = await services['fi_mcp'].get_authentication_status(mobile_number)

        return FiAuthStatusResponse(
            mobile_number=mobile_number,
            is_authenticated=status["is_authenticated"],
            session_id=status.get("session_id"),
            scenario=status.get("scenario"),
            last_activity=status.get("last_activity")
        )

    except Exception as e:
        logger.error("❌ Failed to get Fi auth status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get authentication status")


# Core AI endpoints (updated to use mobile number)
@app.post("/api/v1/analyze-opportunities", response_model=OpportunityResponse, tags=["Intelligence"])
async def analyze_opportunities(
        request: OpportunityRequest,
        background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Analyze financial opportunities using Fi MCP data"""
    start_time = time.time()

    try:
        logger.info("🔍 Starting opportunity analysis", mobile_number=request.mobile_number)

        # Check Fi MCP authentication
        auth_status = await services['fi_mcp'].get_authentication_status(request.mobile_number)
        if not auth_status["is_authenticated"]:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Fi MCP authentication required",
                    "mobile_number": request.mobile_number,
                    "action": "Please authenticate with Fi MCP first"
                }
            )

        # Get comprehensive financial data from Fi MCP
        fi_data = await services['fi_mcp'].get_user_financial_data(
            request.mobile_number,
            scenario=auth_status.get("scenario", "balanced")
        )

        # Generate opportunities using AI
        opportunities = await services['opportunity_engine'].generate_opportunities(
            user_data=fi_data,
            analysis_type=request.analysis_type,
            mobile_number=request.mobile_number
        )

        # Store analysis results
        background_tasks.add_task(
            services['firestore'].store_analysis,
            request.mobile_number,
            opportunities
        )

        processing_time = (time.time() - start_time) * 1000

        logger.info("✅ Opportunity analysis completed",
                    mobile_number=request.mobile_number,
                    opportunities_found=len(opportunities.get("opportunities", [])),
                    processing_time=f"{processing_time:.1f}ms")

        return OpportunityResponse(
            **opportunities,
            processing_time=processing_time,
            data_sources=["fi_mcp", "vertex_ai", "firestore"],
            mobile_number=request.mobile_number
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Opportunity analysis failed",
                     mobile_number=request.mobile_number,
                     error=str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/v1/predict-decision", response_model=DecisionResponse, tags=["Intelligence"])
async def predict_decision(request: DecisionRequest):
    """Score financial decisions with AI prediction"""
    start_time = time.time()

    try:
        logger.info("🎯 Starting decision analysis",
                    mobile_number=request.mobile_number,
                    amount=request.amount,
                    category=request.category)

        # Check Fi MCP authentication
        auth_status = await services['fi_mcp'].get_authentication_status(request.mobile_number)
        if not auth_status["is_authenticated"]:
            raise HTTPException(
                status_code=401,
                detail="Fi MCP authentication required"
            )

        # Get current financial state from Fi MCP
        financial_state = await services['fi_mcp'].get_current_financial_state(request.mobile_number)

        # Enhanced decision request with real data
        enhanced_request = DecisionRequest(
            **request.dict(),
            user_context={
                **request.user_context,
                **financial_state
            }
        )

        # Analyze decision using Vertex AI
        decision_analysis = await services['vertex_ai'].analyze_financial_decision(enhanced_request)

        processing_time = (time.time() - start_time) * 1000

        response = DecisionResponse(
            **decision_analysis,
            processing_time=processing_time,
            data_sources=["fi_mcp", "vertex_ai"],
            mobile_number=request.mobile_number
        )

        logger.info("✅ Decision analysis completed",
                    mobile_number=request.mobile_number,
                    score=response.score,
                    processing_time=f"{processing_time:.1f}ms")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Decision analysis failed",
                     mobile_number=request.mobile_number,
                     error=str(e))
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.get("/api/v1/financial-dashboard/{mobile_number}", response_model=DashboardResponse, tags=["Dashboard"])
async def get_financial_dashboard(mobile_number: str):
    """Get comprehensive financial dashboard"""
    try:
        logger.info("📊 Generating financial dashboard", mobile_number=mobile_number)

        # Check Fi MCP authentication
        auth_status = await services['fi_mcp'].get_authentication_status(mobile_number)
        if not auth_status["is_authenticated"]:
            raise HTTPException(status_code=401, detail="Fi MCP authentication required")

        # Get comprehensive data from Fi MCP
        financial_data = await services['fi_mcp'].get_comprehensive_financial_data(mobile_number)

        # Get recent opportunities and predictions
        recent_analysis = await services['firestore'].get_recent_analysis(mobile_number, limit=5)

        # Calculate financial health score
        health_score = await services['vertex_ai'].calculate_financial_health_score(financial_data)

        # Generate insights
        insights = await services['vertex_ai'].generate_dashboard_insights(financial_data)

        dashboard = DashboardResponse(
            mobile_number=mobile_number,
            financial_summary=financial_data.get("summary", {}),
            health_score=health_score,
            recent_opportunities=recent_analysis.get("opportunities", []),
            insights=insights,
            charts_data=financial_data.get("charts", []),
            last_updated=datetime.now(),
            data_sources=["fi_mcp", "vertex_ai", "firestore"],
            scenario=auth_status.get("scenario", "balanced")
        )

        logger.info("✅ Dashboard generated successfully", mobile_number=mobile_number)
        return dashboard

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Dashboard generation failed", mobile_number=mobile_number, error=str(e))
        raise HTTPException(status_code=500, detail="Dashboard generation failed")


@app.get("/api/v1/financial-health-stream/{mobile_number}", tags=["Streaming"])
async def stream_financial_health(mobile_number: str):
    """Real-time financial health monitoring"""

    # Check Fi MCP authentication
    auth_status = await services['fi_mcp'].get_authentication_status(mobile_number)
    if not auth_status["is_authenticated"]:
        raise HTTPException(status_code=401, detail="Fi MCP authentication required")

    async def generate_health_updates():
        """Generate real-time health updates"""
        try:
            while True:
                # Get real-time data from Fi MCP
                current_data = await services['fi_mcp'].get_real_time_data(mobile_number)

                # Calculate health metrics
                health_metrics = await services['vertex_ai'].calculate_real_time_health(current_data)

                # Detect anomalies
                anomalies = await services['vertex_ai'].detect_financial_anomalies(current_data)

                # Create update
                update = {
                    "mobile_number": mobile_number,
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
                "mobile_number": mobile_number
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
async def chat_with_ai(request: ChatRequest):
    """Conversational AI interface for financial questions"""
    start_time = time.time()

    try:
        logger.info("💬 Processing chat message",
                    mobile_number=request.mobile_number,
                    message_length=len(request.message))

        # Check Fi MCP authentication
        auth_status = await services['fi_mcp'].get_authentication_status(request.mobile_number)
        if not auth_status["is_authenticated"]:
            raise HTTPException(status_code=401, detail="Fi MCP authentication required")

        # Get user's financial context from Fi MCP
        financial_context = await services['fi_mcp'].get_user_context_for_chat(request.mobile_number)

        # Get conversation history
        conversation_history = await services['firestore'].get_conversation_history(
            request.mobile_number,
            limit=10
        )

        # Generate AI response
        ai_response = await services['vertex_ai'].generate_chat_response(
            message=request.message,
            financial_context=financial_context,
            conversation_history=conversation_history,
            user_preferences={}
        )

        # Store conversation
        await services['firestore'].store_conversation_turn(
            request.mobile_number,
            request.message,
            ai_response.get("response", "")
        )

        processing_time = (time.time() - start_time) * 1000

        chat_response = ChatResponse(
            **ai_response,
            processing_time=processing_time,
            data_sources=["fi_mcp", "vertex_ai", "firestore"],
            mobile_number=request.mobile_number
        )

        logger.info("✅ Chat response generated",
                    mobile_number=request.mobile_number,
                    processing_time=f"{processing_time:.1f}ms")

        return chat_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Chat processing failed",
                     mobile_number=request.mobile_number,
                     error=str(e))
        raise HTTPException(status_code=500, detail="Chat processing failed")


# Fi MCP specific endpoints
@app.post("/api/v1/switch-scenario", tags=["Fi MCP"])
async def switch_fi_scenario(request: SwitchScenarioRequest):
    """Switch Fi MCP test scenario"""
    try:
        logger.info("🔄 Switching Fi MCP scenario",
                    mobile_number=request.mobile_number,
                    new_scenario=request.scenario)

        # Check authentication
        auth_status = await services['fi_mcp'].get_authentication_status(request.mobile_number)
        if not auth_status["is_authenticated"]:
            raise HTTPException(status_code=401, detail="Fi MCP authentication required")

        # Switch scenario
        switch_result = await services['fi_mcp'].switch_scenario(
            request.mobile_number,
            request.scenario
        )

        if switch_result["success"]:
            # Get fresh data with new scenario
            fresh_data = await services['fi_mcp'].get_user_financial_data(
                request.mobile_number,
                scenario=request.scenario
            )

            return {
                "success": True,
                "mobile_number": request.mobile_number,
                "new_scenario": request.scenario,
                "net_worth": fresh_data.get("net_worth", {}).get("total_value", 0),
                "accounts_count": len(fresh_data.get("accounts", [])),
                "investments_count": len(fresh_data.get("investments", [])),
                "message": f"Switched to {request.scenario} scenario successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to switch scenario")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to switch scenario",
                     mobile_number=request.mobile_number,
                     error=str(e))
        raise HTTPException(status_code=500, detail="Scenario switch failed")


# Server startup
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(
        "🚀 Starting AvestoAI API server",
        host=host,
        port=port,
        environment=settings.ENVIRONMENT
    )

    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        loop="asyncio"
    )
