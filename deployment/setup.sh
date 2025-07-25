#!/bin/bash
# scripts/setup.sh

set -e  # Exit on any error

echo "🔮 AvestoAI Complete Setup Script"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check dependencies
check_dependencies() {
    echo -e "${BLUE}📋 Checking dependencies...${NC}"

    MISSING_DEPS=()

    if ! command -v gcloud &> /dev/null; then
        MISSING_DEPS+=("Google Cloud CLI")
    fi

    if ! command -v python3 &> /dev/null; then
        MISSING_DEPS+=("Python 3.9+")
    fi

    if ! command -v node &> /dev/null; then
        MISSING_DEPS+=("Node.js")
    fi

    if ! command -v docker &> /dev/null; then
        MISSING_DEPS+=("Docker")
    fi

    if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
        echo -e "${RED}❌ Missing dependencies:${NC}"
        for dep in "${MISSING_DEPS[@]}"; do
            echo "  - $dep"
        done
        echo ""
        echo "Please install missing dependencies and run setup again."
        exit 1
    fi

    echo -e "${GREEN}✅ All dependencies found${NC}"
}

# Get project configuration
get_project_config() {
    echo -e "${BLUE}⚙️ Project Configuration${NC}"

    if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
        echo "Enter your Google Cloud Project ID:"
        read -r PROJECT_ID
        export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
    else
        PROJECT_ID=$GOOGLE_CLOUD_PROJECT
    fi

    echo "Enter Fi Money MCP Base URL (e.g., https://fi-mcp.example.com):"
    read -r FI_MCP_BASE_URL

    echo "Enter Fi Money MCP API Key:"
    read -r FI_MCP_API_KEY

    echo -e "${GREEN}✅ Configuration collected${NC}"
}

# Setup GCP
setup_gcp() {
    echo -e "${BLUE}☁️ Setting up Google Cloud...${NC}"

    # Login check
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        echo "🔐 Please log in to Google Cloud..."
        gcloud auth login
        gcloud auth application-default login
    fi

    gcloud config set project $PROJECT_ID

    # Enable APIs
    echo "🔧 Enabling required APIs..."
    gcloud services enable \
        run.googleapis.com \
        aiplatform.googleapis.com \
        firestore.googleapis.com \
        cloudbuild.googleapis.com \
        storage.googleapis.com \
        secretmanager.googleapis.com \
        cloudresourcemanager.googleapis.com \
        iam.googleapis.com \
        compute.googleapis.com \
        container.googleapis.com \
        artifactregistry.googleapis.com \
        monitoring.googleapis.com \
        logging.googleapis.com \
        cloudfunctions.googleapis.com \
        endpoints.googleapis.com \
        servicecontrol.googleapis.com \
        servicemanagement.googleapis.com

    echo -e "${GREEN}✅ GCP setup complete${NC}"
}

# Create service accounts
setup_service_accounts() {
    echo -e "${BLUE}👤 Setting up service accounts...${NC}"

    # Create backend service account
    if ! gcloud iam service-accounts describe avestoai-backend@$PROJECT_ID.iam.gserviceaccount.com &> /dev/null; then
        gcloud iam service-accounts create avestoai-backend \
            --display-name="AvestoAI Backend Service Account" \
            --description="Main service account for AvestoAI backend operations"
    fi

    # Grant permissions
    declare -a roles=(
        "roles/aiplatform.user"
        "roles/datastore.user"
        "roles/datastore.owner"
        "roles/secretmanager.secretAccessor"
        "roles/storage.objectViewer"
        "roles/monitoring.metricWriter"
        "roles/logging.logWriter"
        "roles/cloudsql.client"
        "roles/pubsub.publisher"
        "roles/pubsub.subscriber"
        "roles/serviceusage.serviceUsageConsumer"
    )

    for role in "${roles[@]}"; do
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:avestoai-backend@$PROJECT_ID.iam.gserviceaccount.com" \
            --role="$role" --quiet
    done

    # Create service account key
    mkdir -p credentials
    if [ ! -f "./credentials/service-account-key.json" ]; then
        gcloud iam service-accounts keys create ./credentials/service-account-key.json \
            --iam-account=avestoai-backend@$PROJECT_ID.iam.gserviceaccount.com
    fi

    echo -e "${GREEN}✅ Service accounts configured${NC}"
}

# Setup Firestore
setup_firestore() {
    echo -e "${BLUE}🗄️ Setting up Firestore...${NC}"

    if ! gcloud firestore databases describe --format="value(name)" 2>/dev/null | grep -q "projects/$PROJECT_ID"; then
        gcloud firestore databases create --region=us-central1
        echo -e "${GREEN}✅ Firestore database created${NC}"
    else
        echo -e "${YELLOW}ℹ️ Firestore database already exists${NC}"
    fi
}

# Setup Artifact Registry
setup_artifact_registry() {
    echo -e "${BLUE}📦 Setting up Artifact Registry...${NC}"

    if ! gcloud artifacts repositories describe avestoai-repo --location=us-central1 &> /dev/null; then
        gcloud artifacts repositories create avestoai-repo \
            --repository-format=docker \
            --location=us-central1 \
            --description="AvestoAI container images"
    fi

    gcloud auth configure-docker us-central1-docker.pkg.dev
    echo -e "${GREEN}✅ Artifact Registry configured${NC}"
}

# Create environment file
create_env_file() {
    echo -e "${BLUE}📝 Creating environment configuration...${NC}"

    JWT_SECRET=$(openssl rand -base64 32)

    cat > .env << EOF
# AvestoAI Environment Configuration
ENVIRONMENT=development
DEBUG=true

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
VERTEX_AI_LOCATION=us-central1
FIRESTORE_DATABASE=(default)

# Authentication
JWT_SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=30

# Fi Money MCP Configuration
FI_MCP_BASE_URL=$FI_MCP_BASE_URL
FI_MCP_API_KEY=$FI_MCP_API_KEY
FI_MCP_TIMEOUT=30
FI_MCP_MAX_RETRIES=3

# Security
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:8001","http://localhost:8002","https://avestoai.com"]
ALLOWED_HOSTS=["*"]

# Performance & Features
MAX_CONCURRENT_REQUESTS=100
RATE_LIMIT_CALLS=100
RATE_LIMIT_PERIOD=60
CACHE_TTL=300
ENABLE_METRICS=true
LOG_LEVEL=INFO

# Feature Flags
ENABLE_PREDICTIVE_ANALYSIS=true
ENABLE_REAL_TIME_STREAMING=true
ENABLE_ADVANCED_CHARTS=true
EOF

    echo -e "${GREEN}✅ Environment file created${NC}"
}

# Setup Python environment
setup_python_env() {
    echo -e "${BLUE}🐍 Setting up Python environment...${NC}"

    cd backend

    # Create virtual environment
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi

    # Activate and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

    echo -e "${GREEN}✅ Python environment ready${NC}"
    cd ..
}

# Setup frontend
setup_frontend() {
    echo -e "${BLUE}🎨 Setting up frontend...${NC}"

    # Chainlit
    cd frontend-chainlit
    pip install -r requirements.txt
    cd ..

    echo -e "${GREEN}✅ Frontend setup complete${NC}"
}

# Create secrets in Secret Manager
create_secrets() {
    echo -e "${BLUE}🔐 Creating secrets...${NC}"

    # JWT Secret
    echo -n "$JWT_SECRET" | gcloud secrets create jwt-secret-key --data-file=- --replication-policy=automatic || true

    # Fi MCP API Key
    echo -n "$FI_MCP_API_KEY" | gcloud secrets create fi-mcp-api-key --data-file=- --replication-policy=automatic || true

    echo -e "${GREEN}✅ Secrets created${NC}"
}

# Test setup
test_setup() {
    echo -e "${BLUE}🧪 Testing setup...${NC}"

    cd backend
    source venv/bin/activate

    # Test Python imports
    python -c "
import sys
try:
    from fastapi import FastAPI
    from google.cloud import aiplatform, firestore
    import vertexai
    print('✅ Python dependencies OK')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"

    cd ..
    echo -e "${GREEN}✅ Setup test passed${NC}"
}

# Create startup script
create_startup_script() {
    echo -e "${BLUE}📝 Creating startup script...${NC}"

    cat > start-dev.sh << 'EOF'
#!/bin/bash

echo "🚀 Starting AvestoAI Development Environment"

# Set environment variables
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/credentials/service-account-key.json"

# Function to start backend
start_backend() {
    echo "🔧 Starting backend API..."
    cd backend
    source venv/bin/activate
    python app/main.py &
    BACKEND_PID=$!
    echo "Backend PID: $BACKEND_PID"
    cd ..
}

# Function to start frontend
start_frontend() {
    echo "💬 Starting Chainlit frontend..."
    cd frontend-chainlit
    chainlit run app.py --port 8001 &
    FRONTEND_PID=$!
    echo "Frontend PID: $FRONTEND_PID"
    cd ..
}

# Start services
start_backend
sleep 5
start_frontend

echo ""
echo "🎉 AvestoAI is running!"
echo ""
echo "📊 Backend API: http://localhost:8080"
echo "💬 AI Chat:     http://localhost:8001"
echo "📚 API Docs:    http://localhost:8080/docs"
echo "🏥 Health:      http://localhost:8080/health"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap 'echo "🛑 Stopping services..."; kill $BACKEND_PID $FRONTEND_PID; exit' INT
wait
EOF

    chmod +x start-dev.sh
    echo -e "${GREEN}✅ Startup script created${NC}"
}

# Main setup function
main() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║               🔮 AvestoAI Complete Setup                     ║"
    echo "║          Revolutionary Financial Intelligence Platform        ║"
    echo "║              Google Agentic AI Hackathon 2025               ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_dependencies
    get_project_config
    setup_gcp
    setup_service_accounts
    setup_firestore
    setup_artifact_registry
    create_env_file
    create_secrets
    setup_python_env
    setup_frontend
    test_setup
    create_startup_script

    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    🎉 Setup Complete!                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    echo ""
    echo -e "${YELLOW}🚀 To start the development environment:${NC}"
    echo "   ./start-dev.sh"
    echo ""
    echo -e "${YELLOW}📊 Services will be available at:${NC}"
    echo "   Backend API:  http://localhost:8080"
    echo "   AI Chat:      http://localhost:8001"
    echo "   API Docs:     http://localhost:8080/docs"
    echo "   Health Check: http://localhost:8080/health"
    echo ""
    echo -e "${YELLOW}📚 Next steps:${NC}"
    echo "   1. Run ./start-dev.sh to start services"
    echo "   2. Test the API at http://localhost:8080/docs"
    echo "   3. Chat with AI at http://localhost:8001"
    echo "   4. Register users via /api/v1/auth/register"
    echo "   5. Explore opportunities via /api/v1/analyze-opportunities"
    echo ""
    echo -e "${BLUE}💡 Pro tip: Check logs with 'make logs' for troubleshooting${NC}"
}

# Run main function
main "$@"
