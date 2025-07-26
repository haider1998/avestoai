# frontend-chainlit/Dockerfile
FROM python:3.11-slim

# Build argument for environment
ARG ENVIRONMENT=development

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash chainlit && \
    chown -R chainlit:chainlit /app
USER chainlit

# Expose port
EXPOSE 8001

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV CHAINLIT_HOST=0.0.0.0
ENV CHAINLIT_PORT=8001
ENV ENVIRONMENT=${ENVIRONMENT}

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Start application
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8001"]
