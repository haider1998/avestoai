#!/bin/bash

# AvestoAI Docker Setup and Testing Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

check_docker() {
    log_info "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    log_success "Docker is installed and running"
}

check_docker_compose() {
    log_info "Checking Docker Compose..."
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
        log_success "Docker Compose is available"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
        log_success "Docker Compose (plugin) is available"
    else
        log_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
}

verify_files() {
    log_info "Verifying required files..."
    
    required_files=(
        "Dockerfile"
        "docker-compose.yml"
        "requirements-optimized.txt"
        "app/main.py"
        ".env"
        "credentials/avestoai-466417-1e5f06659c0e.json"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Required file missing: $file"
            exit 1
        fi
    done
    
    log_success "All required files are present"
}

build_image() {
    log_info "Building Docker image..."
    
    # Clean up any existing containers
    $COMPOSE_CMD down --remove-orphans 2>/dev/null || true
    
    # Build the image
    if $COMPOSE_CMD build --no-cache; then
        log_success "Docker image built successfully"
    else
        log_error "Failed to build Docker image"
        exit 1
    fi
}

start_container() {
    log_info "Starting AvestoAI container..."
    
    if $COMPOSE_CMD up -d; then
        log_success "Container started successfully"
    else
        log_error "Failed to start container"
        exit 1
    fi
    
    # Wait for container to be ready
    log_info "Waiting for container to be ready..."
    sleep 10
    
    # Check if container is running
    if $COMPOSE_CMD ps | grep -q "Up"; then
        log_success "Container is running"
    else
        log_error "Container failed to start properly"
        $COMPOSE_CMD logs
        exit 1
    fi
}

check_health() {
    log_info "Checking container health..."
    
    # Wait for health check to pass
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8080/health &> /dev/null; then
            log_success "Health check passed"
            return 0
        fi
        
        log_info "Health check attempt $attempt/$max_attempts..."
        sleep 5
        ((attempt++))
    done
    
    log_error "Health check failed after $max_attempts attempts"
    log_info "Container logs:"
    $COMPOSE_CMD logs --tail=50
    return 1
}

show_status() {
    log_info "Container Status:"
    $COMPOSE_CMD ps
    
    log_info "Container Logs (last 20 lines):"
    $COMPOSE_CMD logs --tail=20
    
    log_info "Available Endpoints:"
    echo "  - Health Check: http://localhost:8080/health"
    echo "  - API Docs: http://localhost:8080/docs"
    echo "  - Root: http://localhost:8080/"
    echo "  - Metrics: http://localhost:8080/metrics"
}

main() {
    log_info "AvestoAI Docker Setup and Testing"
    echo "======================================"
    
    case "${1:-setup}" in
        "setup")
            check_docker
            check_docker_compose
            verify_files
            build_image
            start_container
            check_health
            show_status
            log_success "AvestoAI backend is running successfully!"
            log_info "Run './docker_setup.sh test' to run endpoint tests"
            ;;
        "test")
            check_docker
            check_docker_compose
            if ! curl -f http://localhost:8080/health &> /dev/null; then
                log_error "Container is not running. Run './docker_setup.sh setup' first"
                exit 1
            fi
            log_info "Running endpoint tests..."
            python3 test_endpoints.py
            ;;
        "status")
            check_docker_compose
            show_status
            ;;
        "logs")
            check_docker_compose
            $COMPOSE_CMD logs -f
            ;;
        "stop")
            check_docker_compose
            log_info "Stopping container..."
            $COMPOSE_CMD stop
            log_success "Container stopped"
            ;;
        "cleanup")
            check_docker_compose
            log_info "Cleaning up..."
            $COMPOSE_CMD down --remove-orphans
            log_success "Cleanup completed"
            ;;
        *)
            echo "Usage: $0 {setup|test|status|logs|stop|cleanup}"
            echo ""
            echo "Commands:"
            echo "  setup    - Build and start the container"
            echo "  test     - Run endpoint tests"
            echo "  status   - Show container status"
            echo "  logs     - Show container logs"
            echo "  stop     - Stop the container"
            echo "  cleanup  - Stop and remove containers"
            exit 1
            ;;
    esac
}

main "$@"
