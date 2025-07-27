# backend/Dockerfile - Optimized for faster builds
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy optimized requirements first for better caching
COPY requirements-optimized.txt ./requirements.txt

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --timeout=1000 --retries=5 --index-url https://pypi.org/simple/ \
    --extra-index-url https://pypi.python.org/simple/ \
    -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory - changed to /app/backend to match import structure
WORKDIR /app

# Copy application code with proper structure
COPY . ./backend/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port
EXPOSE 8080

# Environment variables - fixed PYTHONPATH to include both /app and /app/backend
ENV PYTHONPATH=/app:/app/backend
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Health check with longer timeout for startup
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start application with uvicorn - updated path to match new structure
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--timeout-keep-alive", "120"]
