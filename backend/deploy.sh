#!/bin/bash

# AvestoAI Backend Deployment Script for GCP Cloud Run
# This script automates the deployment process to Google Cloud Platform

set -e  # Exit on any error

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"avestoai-466417"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="avestoai-backend"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check if authenticated with gcloud
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with gcloud. Please run 'gcloud auth login'"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Set up GCP project
setup_project() {
    log_info "Setting up GCP project: ${PROJECT_ID}"
    
    # Set the project
    gcloud config set project ${PROJECT_ID}
    
    # Enable required APIs
    log_info "Enabling required GCP APIs..."
    gcloud services enable \
        cloudbuild.googleapis.com \
        run.googleapis.com \
        containerregistry.googleapis.com \
        aiplatform.googleapis.com \
        firestore.googleapis.com \
        secretmanager.googleapis.com \
        monitoring.googleapis.com
    
    log_success "GCP project setup completed"
}

# Create service account
create_service_account() {
    log_info "Creating service account for Cloud Run..."
    
    SERVICE_ACCOUNT_EMAIL="${SERVICE_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Create service account if it doesn't exist
    if ! gcloud iam service-accounts describe ${SERVICE_ACCOUNT_EMAIL} &> /dev/null; then
        gcloud iam service-accounts create ${SERVICE_NAME} \
            --display-name="AvestoAI Backend Service Account" \
            --description="Service account for AvestoAI backend application"
        
        # Grant necessary roles
        gcloud projects add-iam-policy-binding ${PROJECT_ID} \
            --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
            --role="roles/aiplatform.user"
        
        gcloud projects add-iam-policy-binding ${PROJECT_ID} \
            --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
            --role="roles/datastore.user"
        
        gcloud projects add-iam-policy-binding ${PROJECT_ID} \
            --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
            --role="roles/secretmanager.secretAccessor"
        
        gcloud projects add-iam-policy-binding ${PROJECT_ID} \
            --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
            --role="roles/monitoring.metricWriter"
        
        log_success "Service account created and configured"
    else
        log_info "Service account already exists"
    fi
}

# Build and push Docker image
build_and_push() {
    log_info "Building Docker image..."
    
    # Build the image
    docker build -t ${IMAGE_NAME}:latest .
    
    # Configure Docker to use gcloud as a credential helper
    gcloud auth configure-docker --quiet
    
    # Push the image
    log_info "Pushing image to Container Registry..."
    docker push ${IMAGE_NAME}:latest
    
    log_success "Docker image built and pushed successfully"
}

# Deploy to Cloud Run
deploy_to_cloud_run() {
    log_info "Deploying to Cloud Run..."
    
    gcloud run deploy ${SERVICE_NAME} \
        --image=${IMAGE_NAME}:latest \
        --region=${REGION} \
        --platform=managed \
        --allow-unauthenticated \
        --memory=2Gi \
        --cpu=2 \
        --concurrency=100 \
        --max-instances=10 \
        --timeout=300 \
        --port=8080 \
        --set-env-vars="ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
        --service-account="${SERVICE_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Get the service URL
    SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
        --region=${REGION} \
        --format="value(status.url)")
    
    log_success "Deployment completed successfully!"
    log_info "Service URL: ${SERVICE_URL}"
    log_info "Health check: ${SERVICE_URL}/health"
    log_info "API docs: ${SERVICE_URL}/docs"
}

# Test deployment
test_deployment() {
    log_info "Testing deployment..."
    
    SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
        --region=${REGION} \
        --format="value(status.url)")
    
    # Test health endpoint
    if curl -f "${SERVICE_URL}/health" > /dev/null 2>&1; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        return 1
    fi
    
    # Test root endpoint
    if curl -f "${SERVICE_URL}/" > /dev/null 2>&1; then
        log_success "Root endpoint test passed"
    else
        log_error "Root endpoint test failed"
        return 1
    fi
    
    log_success "All tests passed!"
}

# Main deployment function
main() {
    log_info "Starting AvestoAI Backend deployment to GCP Cloud Run"
    log_info "Project: ${PROJECT_ID}"
    log_info "Region: ${REGION}"
    log_info "Service: ${SERVICE_NAME}"
    
    check_prerequisites
    setup_project
    create_service_account
    build_and_push
    deploy_to_cloud_run
    test_deployment
    
    log_success "🎉 Deployment completed successfully!"
    log_info "Your AvestoAI backend is now running on Google Cloud Run"
}

# Handle script arguments
case "${1:-}" in
    "build")
        build_and_push
        ;;
    "deploy")
        deploy_to_cloud_run
        ;;
    "test")
        test_deployment
        ;;
    "setup")
        setup_project
        create_service_account
        ;;
    *)
        main
        ;;
esac
