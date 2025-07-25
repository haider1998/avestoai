# Makefile
.PHONY: help setup install dev test clean deploy

# Default target
help:
	@echo "🔮 AvestoAI Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup          Initial project setup"
	@echo "  make install        Install dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev           Start all services with Docker Compose"
	@echo "  make dev-local     Start services locally"
	@echo "  make dev-backend   Start backend only"
	@echo "  make dev-frontend  Start frontend only"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run all tests"
	@echo "  make test-unit     Run unit tests"
	@echo "  make test-integration  Run integration tests"
	@echo "  make test-load     Run load tests"
	@echo ""
	@echo "Quality:"
	@echo "  make lint          Run linting"
	@echo "  make format        Format code"
	@echo "  make security      Security scan"
	@echo ""
	@echo "Deployment:"
	@echo "  make build         Build Docker images"
	@echo "  make deploy-staging Deploy to staging"
	@echo "  make deploy-prod   Deploy to production"
	@echo ""
	@echo "Utilities:"
	@echo "  make logs          View logs"
	@echo "  make clean         Clean up"

# Setup and installation
setup:
	@echo "🚀 Running initial setup..."
	chmod +x scripts/setup.sh
	./scripts/setup.sh

install: setup
	@echo "📦 Installing dependencies..."
	cd backend && pip install -r requirements.txt
	cd frontend-chainlit && pip install -r requirements.txt

# Development
dev:
	@echo "🚀 Starting all services with Docker Compose..."
	docker-compose up --build

dev-local:
	@echo "🚀 Starting services locally..."
	./start-dev.sh

dev-backend:
	@echo "🔧 Starting backend only..."
	cd backend && \
	export GOOGLE_APPLICATION_CREDENTIALS="$(PWD)/credentials/service-account-key.json" && \
	python app/main.py

dev-frontend:
	@echo "💬 Starting frontend only..."
	cd frontend-chainlit && chainlit run app.py --port 8001

# Testing
test:
	@echo "🧪 Running all tests..."
	make test-unit
	make test-integration

test-unit:
	@echo "🧪 Running unit tests..."
	cd backend && python -m pytest tests/unit/ -v

test-integration:
	@echo "🧪 Running integration tests..."
	cd backend && python -m pytest tests/integration/ -v

test-load:
	@echo "🧪 Running load tests..."
	cd backend && locust -f tests/load_test.py --host=http://localhost:8080 --headless -u 10 -r 2 -t 30s

# Code quality
lint:
	@echo "🔍 Running linting..."
	cd backend && \
	python -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics && \
	python -m flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

format:
	@echo "✨ Formatting code..."
	cd backend && python -m black . && python -m isort .

security:
	@echo "🔒 Running security scan..."
	cd backend && python -m safety check
	cd backend && python -m bandit -r .

# Building and deployment
build:
	@echo "🏗️ Building Docker images..."
	docker-compose build

deploy-staging:
	@echo "🚀 Deploying to staging..."
	gcloud builds submit --config=deployment/cloudbuild.yaml . --substitutions=_ENV=staging

deploy-prod:
	@echo "🚀 Deploying to production..."
	gcloud builds submit --config=deployment/cloudbuild.yaml . --substitutions=_ENV=production

# Utilities
logs:
	@echo "📋 Viewing application logs..."
	docker-compose logs -f

clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	docker system prune -f
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
