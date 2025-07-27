# utils/metrics.py - Prometheus metrics for GCP monitoring
from prometheus_client import Counter, Histogram, Gauge, Info
import time
import structlog
from typing import Dict, Any
import os

logger = structlog.get_logger()

# Application metrics
REQUEST_COUNT = Counter(
    'avestoai_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'avestoai_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'avestoai_active_connections',
    'Number of active connections'
)

# Business metrics
OPPORTUNITIES_GENERATED = Counter(
    'avestoai_opportunities_generated_total',
    'Total opportunities generated',
    ['mobile_number', 'analysis_type']
)

DECISIONS_ANALYZED = Counter(
    'avestoai_decisions_analyzed_total',
    'Total decisions analyzed',
    ['mobile_number', 'category']
)

CHAT_MESSAGES = Counter(
    'avestoai_chat_messages_total',
    'Total chat messages processed',
    ['mobile_number']
)

FI_MCP_REQUESTS = Counter(
    'avestoai_fi_mcp_requests_total',
    'Total Fi MCP requests',
    ['endpoint', 'status']
)

VERTEX_AI_REQUESTS = Counter(
    'avestoai_vertex_ai_requests_total',
    'Total Vertex AI requests',
    ['model', 'status']
)

# System metrics
HEALTH_SCORE_CALCULATIONS = Counter(
    'avestoai_health_score_calculations_total',
    'Total health score calculations'
)

ERROR_COUNT = Counter(
    'avestoai_errors_total',
    'Total errors',
    ['error_type', 'service']
)

# Service info
SERVICE_INFO = Info(
    'avestoai_service_info',
    'Service information'
)

# Initialize service info
SERVICE_INFO.info({
    'version': '1.0.0',
    'environment': os.getenv('ENVIRONMENT', 'development'),
    'service': 'avestoai-backend',
    'project_id': os.getenv('GOOGLE_CLOUD_PROJECT', 'unknown')
})


class MetricsCollector:
    """Centralized metrics collection"""
    
    def __init__(self):
        self.start_time = time.time()
        logger.info("Metrics collector initialized")
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_opportunity_generation(self, mobile_number: str, analysis_type: str):
        """Record opportunity generation"""
        OPPORTUNITIES_GENERATED.labels(
            mobile_number=mobile_number,
            analysis_type=analysis_type
        ).inc()
    
    def record_decision_analysis(self, mobile_number: str, category: str):
        """Record decision analysis"""
        DECISIONS_ANALYZED.labels(
            mobile_number=mobile_number,
            category=category
        ).inc()
    
    def record_chat_message(self, mobile_number: str):
        """Record chat message processing"""
        CHAT_MESSAGES.labels(mobile_number=mobile_number).inc()
    
    def record_fi_mcp_request(self, endpoint: str, status: str):
        """Record Fi MCP request"""
        FI_MCP_REQUESTS.labels(
            endpoint=endpoint,
            status=status
        ).inc()
    
    def record_vertex_ai_request(self, model: str, status: str):
        """Record Vertex AI request"""
        VERTEX_AI_REQUESTS.labels(
            model=model,
            status=status
        ).inc()
    
    def record_health_score_calculation(self):
        """Record health score calculation"""
        HEALTH_SCORE_CALCULATIONS.inc()
    
    def record_error(self, error_type: str, service: str):
        """Record error occurrence"""
        ERROR_COUNT.labels(
            error_type=error_type,
            service=service
        ).inc()
    
    def set_active_connections(self, count: int):
        """Set active connections count"""
        ACTIVE_CONNECTIONS.set(count)
    
    def get_uptime(self) -> float:
        """Get service uptime in seconds"""
        return time.time() - self.start_time


# Global metrics collector instance
metrics_collector = MetricsCollector()
