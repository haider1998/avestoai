# AvestoAI Backend Dockerfile - Optimized for GCP Cloud Run
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
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements-optimized.txt ./requirements.txt

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --timeout=1000 --retries=5 \
    --index-url https://pypi.org/simple/ \
    --extra-index-url https://pypi.python.org/simple/ \
    -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies (including curl for health checks)
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 app && \
    chown -R app:app /app && \
    chmod -R 755 /app

# Switch to non-root user
USER app

# Environment variables for GCP Cloud Run
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080
ENV HOST=0.0.0.0

# Expose port (Cloud Run will set this automatically)
EXPOSE 8080

# Health check (compatible with Cloud Run)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start application with proper signal handling for Cloud Run
CMD exec python app/main.py
