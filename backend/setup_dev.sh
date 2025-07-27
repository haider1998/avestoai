#!/bin/bash

# AvestoAI Backend Development Setup Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_info "🚀 Setting up AvestoAI Backend Development Environment"

# Check if we're in the right directory
if [ ! -f "app/main.py" ]; then
    log_error "Please run this script from the backend directory"
    exit 1
fi

# Create virtual environment
log_info "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    log_success "Virtual environment created"
else
    log_info "Virtual environment already exists"
fi

# Activate virtual environment
log_info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
log_info "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
log_info "Installing dependencies..."
if [ -f "requirements-optimized.txt" ]; then
    pip install -r requirements-optimized.txt
    log_success "Dependencies installed from requirements-optimized.txt"
else
    pip install -r requirements.txt
    log_success "Dependencies installed from requirements.txt"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    log_warning ".env file not found. Creating default .env file..."
    cat > .env << EOF
# AvestoAI Backend Environment Configuration

# Environment
ENVIRONMENT=development
DEBUG=true

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=avestoai-466417
VERTEX_AI_LOCATION=us-central1
FIRESTORE_DATABASE=(default)

# Fi Money MCP Configuration
FI_MCP_BASE_URL=https://fi-mcp-dev-172306289913.asia-south1.run.app
FI_MCP_TIMEOUT=30
FI_MCP_MAX_RETRIES=3
FI_MCP_DEFAULT_SCENARIO=balanced

# Security Configuration
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:8001","http://localhost:8002","https://avestoai.com"]
ALLOWED_HOSTS=["*"]

# Rate Limiting
RATE_LIMIT_CALLS=100
RATE_LIMIT_PERIOD=60

# External APIs
EXTERNAL_API_TIMEOUT=30
MAX_CONCURRENT_REQUESTS=100

# Caching
CACHE_TTL=300

# Monitoring
ENABLE_METRICS=true
LOG_LEVEL=INFO

# ElevenLabs Configuration (Voice Features)
ELEVENLABS_API_KEY=sk-dummy-elevenlabs-api-key-replace-with-real-key
ELEVENLABS_DEFAULT_VOICE=21m00Tcm4TlvDq8ikWAM
OPENAI_API_KEY=sk-dummy-openai-api-key-for-whisper-stt

# Feature Flags
ENABLE_PREDICTIVE_ANALYSIS=true
ENABLE_REAL_TIME_STREAMING=true
ENABLE_ADVANCED_CHARTS=true
ENABLE_FI_MCP_INTEGRATION=true
ENABLE_VOICE_CONVERSATIONS=true
EOF
    log_success ".env file created with default values"
else
    log_info ".env file already exists"
fi

