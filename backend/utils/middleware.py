# backend/utils/middleware.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import structlog
from prometheus_client import Counter, Histogram

logger = structlog.get_logger()

# Metrics
REQUEST_COUNT = Counter('avestoai_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('avestoai_request_duration_seconds', 'Request duration')


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting metrics"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Record metrics
        duration = time.time() - start_time
        REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
        REQUEST_DURATION.observe(duration)

        # Log request
        logger.info("Request processed",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration=f"{duration:.3f}s")

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware"""

    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()

        # Clean old entries
        self.clients = {
            ip: times for ip, times in self.clients.items()
            if any(t > current_time - self.period for t in times)
        }

        # Check rate limit
        if client_ip in self.clients:
            recent_calls = [t for t in self.clients[client_ip] if t > current_time - self.period]
            if len(recent_calls) >= self.calls:
                return Response("Rate limit exceeded", status_code=429)
            self.clients[client_ip] = recent_calls + [current_time]
        else:
            self.clients[client_ip] = [current_time]

        return await call_next(request)
