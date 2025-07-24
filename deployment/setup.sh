#!/bin/bash
# deployment/setup.sh

set -e  # Exit on any error

echo "🚀 Setting up AvestoAI development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if required tools are installed
check_dependencies() {
    echo "📋 Checking dependencies..."

    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}❌ Google Cloud CLI not found. Please install it first.${NC}"
        exit 1
    fi

    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 not found. Please install it first.${NC}"
        exit 1
    fi

    if ! command -v node &> /dev/null; then
        echo -e "${RED}❌ Node.js not found. Please install it first.${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ All dependencies found${NC}"
}

# Set up Google Cloud project
setup_gcp() {
    echo "☁️ Setting up Google Cloud project..."

    # Check if user is logged in
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        echo "🔐 Please log in to Google Cloud..."
        gcloud auth login
        gcloud auth application-default login
    fi

    # Set project
    if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
        echo "Please enter your Google Cloud Project ID:"
        read -r PROJECT_ID
        export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
    else
        PROJECT_ID=$GOOGLE_CLOUD_PROJECT
    fi

    gcloud config set project $PROJECT_ID
    echo -e "${GREEN}✅ Project set to: $PROJECT_ID${NC}"

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
        artifactregistry.googleapis.com \
        monitoring.googleapis.com \
        logging.googleapis.com

    echo -e "${GREEN}✅ APIs enabled${NC}"
}

# Create service accounts
setup_service_accounts() {
    echo "👤 Setting up service accounts..."

    # Create backend service account
    if ! gcloud iam service-accounts describe avestoai-backend@$PROJECT_ID.iam.gserviceaccount.com &> /dev/null; then
        gcloud iam service-accounts create avestoai-backend \
            --display-name="AvestoAI Backend Service Account" \
            --description="Service account for AvestoAI backend API"

        echo -e "${GREEN}✅ Backend service account created${NC}"
    else
        echo -e "${YELLOW}ℹ️ Backend service account already exists${NC}"
    fi

    # Grant permissions
    echo "🔐 Granting permissions..."
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:avestoai-backend@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/aiplatform.user" --quiet

    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:avestoai-backend@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/datastore.user" --quiet

    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:avestoai-backend@$PROJECT_ID.iam.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor" --quiet

    # Create service account key
    if [ ! -f "./service-account-key.json" ]; then
        gcloud iam service-accounts keys create ./service-account-key.json \
            --iam-account=avestoai-backend@$PROJECT_ID.iam.gserviceaccount.com
        echo -e "${GREEN}✅ Service account key created${NC}"
    else
        echo -e "${YELLOW}ℹ️ Service account key already exists${NC}"
    fi
}

# Set up Firestore
setup_firestore() {
    echo "🗄️ Setting up Firestore..."

    if ! gcloud firestore databases describe --format="value(name)" 2>/dev/null | grep -q "projects/$PROJECT_ID"; then
        gcloud firestore databases create --region=us-central1
        echo -e "${GREEN}✅ Firestore database created${NC}"
    else
        echo -e "${YELLOW}ℹ️ Firestore database already exists${NC}"
    fi
}

# Set up Artifact Registry
setup_artifact_registry() {
    echo "📦 Setting up Artifact Registry..."

    if ! gcloud artifacts repositories describe avestoai-repo --location=us-central1 &> /dev/null; then
        gcloud artifacts repositories create avestoai-repo \
            --repository-format=docker \
            --location=us-central1 \
            --description="AvestoAI container images"

        echo -e "${GREEN}✅ Artifact Registry repository created${NC}"
    else
        echo -e "${YELLOW}ℹ️ Artifact Registry repository already exists${NC}"
    fi

    # Configure Docker authentication
    gcloud auth configure-docker us-central1-docker.pkg.dev
}

# Install Ollama for on-device AI
setup_ollama() {
    echo "🧠 Setting up Ollama for on-device AI..."

    if ! command -v ollama &> /dev/null; then
        echo "📥 Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
        echo -e "${GREEN}✅ Ollama installed${NC}"
    else
        echo -e "${YELLOW}ℹ️ Ollama already installed${NC}"
    fi

    # Start Ollama service
    echo "🚀 Starting Ollama service..."
    ollama serve &
    sleep 5

    # Pull Gemma model
    echo "📥 Pulling Gemma 2B model..."
    ollama pull gemma:2b

    echo -e "${GREEN}✅ Ollama setup complete${NC}"
}

# Create environment file
create_env_file() {
    echo "📝 Creating environment file..."

    if [ ! -f ".env" ]; then
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

# On-Device AI
LOCAL_MODEL_NAME=gemma:2b
OLLAMA_ENDPOINT=http://localhost:11434

# Security
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:8001","http://localhost:8002"]

# Performance
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT_SECONDS=30
EOF

        echo -e "${GREEN}✅ Environment file created${NC}"
    else
        echo -e "${YELLOW}ℹ️ Environment file already exists${NC}"
    fi
}

# Install Python dependencies
setup_python_env() {
    echo "🐍 Setting up Python environment..."

    cd backend

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo -e "${GREEN}✅ Virtual environment created${NC}"
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    pip install --upgrade pip
    pip install -r requirements.txt

    echo -e "${GREEN}✅ Python dependencies installed${NC}"

    cd ..
}

# Install frontend dependencies
setup_frontend() {
    echo "🎨 Setting up frontend dependencies..."

    # Chainlit
    cd frontend-chainlit
    pip install -r requirements.txt
    cd ..

    # Flutter (if available)
    if command -v flutter &> /dev/null; then
        cd frontend-flutter
        flutter pub get
        cd ..
        echo -e "${GREEN}✅ Flutter dependencies installed${NC}"
    else
        echo -e "${YELLOW}ℹ️ Flutter not found, skipping Flutter setup${NC}"
    fi

    echo -e "${GREEN}✅ Frontend setup complete${NC}"
}

# Test the setup
test_setup() {
    echo "🧪 Testing setup..."

    cd backend
    source venv/bin/activate

    # Test Python imports
    python -c "
import sys
try:
    from fastapi import FastAPI
    from google.cloud import aiplatform
    print('✅ Python dependencies OK')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"

    # Test Ollama
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        echo -e "${GREEN}✅ Ollama service OK${NC}"
    else
        echo -e "${YELLOW}⚠️ Ollama service not responding${NC}"
    fi

    cd ..
}

# Main setup function
main() {
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    🔮 AvestoAI Setup                         ║"
    echo "║              Revolutionary Financial Intelligence             ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_dependencies
    setup_gcp
    setup_service_accounts
    setup_firestore
    setup_artifact_registry
    setup_ollama
    create_env_file
    setup_python_env
    setup_frontend
    test_setup

    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    🎉 Setup Complete!                        ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    echo "🚀 To start the development environment:"
    echo ""
    echo "1. Backend API:"
    echo "   cd backend && source venv/bin/activate && python main.py"
    echo "   🌐 http://localhost:8080"
    echo ""
    echo "2. Chainlit AI Chat:"
    echo "   cd frontend-chainlit && chainlit run app.py --port 8001"
    echo "   💬 http://localhost:8001"
    echo ""
    echo "3. Flutter Web App (if available):"
    echo "   cd frontend-flutter && flutter run -d chrome --web-port 8002"
    echo "   📱 http://localhost:8002"
    echo ""
    echo "📚 API Documentation: http://localhost:8080/docs"
    echo "🏥 Health Check: http://localhost:8080/health"
    echo ""
    echo -e "${YELLOW}💡 Don't forget to set GOOGLE_APPLICATION_CREDENTIALS:${NC}"
    echo "   export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/service-account-key.json"
}

# Run main function
main "$@"
