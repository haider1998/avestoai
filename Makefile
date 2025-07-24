# Makefile
.PHONY: help setup dev-backend dev-chainlit dev-flutter test lint clean deploy

# Default target
help:
	@echo "🔮 AvestoAI Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup          Initial project setup"
	@echo "  make install        Install all dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev-backend    Start backend API server"
	@echo "  make dev-chainlit   Start Chainlit chat interface"
	@echo "  make dev-flutter    Start Flutter web app"
	@echo "  make dev-all        Start all services"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run all tests"
	@echo "  make test-backend   Run backend tests only"
	@echo "  make lint           Run code quality checks"
	@echo ""
	@echo "Deployment:"
	@echo "  make build          Build for production"
	@echo "  make deploy-staging Deploy to staging"
	@echo "  make deploy-prod    Deploy to production"
	@echo ""
	@echo "Utilities:"
	@echo "  make logs           View application logs"
	@echo "  make clean          Clean temporary files"

# Setup and installation
setup:
	@echo "🚀 Running initial setup..."
	./deployment/setup.sh

install: setup
	@echo "📦 Installing dependencies..."
	cd backend && source venv/bin/activate && pip install -r requirements.txt
	cd frontend-chainlit && pip install -r requirements.txt
	cd frontend-flutter && flutter pub get

# Development servers
dev-backend:
	@echo "🚀 Starting backend API server..."
	cd backend && source venv/bin/activate && \
	export GOOGLE_APPLICATION_CREDENTIALS=$(PWD)/service-account-key.json && \
	python main.py

dev-chainlit:
	@echo "💬 Starting Chainlit chat interface..."
	cd frontend-chainlit && chainlit run app.py --port 8001

dev-flutter:
	@echo "📱 Starting Flutter web app..."
	cd frontend-flutter && flutter run -d chrome --web-port 8002

dev-all:
	@echo "🌟 Starting all services..."
	make -j3 dev-backend dev-chainlit dev-flutter

# Testing
test:
	@echo "🧪 Running all tests..."
	cd backend && source venv/bin/activate && python -m pytest tests/ -v

test-backend:
	@echo "🧪 Running backend tests..."
	cd backend && source venv/bin/activate && python -m pytest tests/ -v

lint:
	@echo "🔍 Running code quality checks..."
	cd backend && source venv/bin/activate && \
	python -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics && \
	python -m flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Building and deployment
build:
	@echo "🏗️ Building for production..."
	cd backend && docker build -t avestoai-backend .
	cd frontend-flutter && flutter build web

deploy-staging:
	@echo "🚀 Deploying to staging..."
	gcloud builds submit --config=deployment/cloudbuild.yaml . --substitutions=_ENV=staging

deploy-prod:
	@echo "🚀 Deploying to production..."
	gcloud builds submit --config=deployment/cloudbuild.yaml . --substitutions=_ENV=production

# Utilities
logs:
	@echo "📋 Viewing application logs..."
	gcloud logs tail projects/${GOOGLE_CLOUD_PROJECT}/logs/avestoai-backend --format="value(timestamp,severity,textPayload)"

clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	cd frontend-flutter && flutter clean

# Database operations
db-migrate:
	@echo "🗄️ Running database migrations..."
	cd backend && source venv/bin/activate && python -c "
from services.firestore_client import FirestoreClient
from models.config import settings
import asyncio
client = FirestoreClient(settings)
asyncio.run(client.setup_database())
"

# Monitoring
monitor:
	@echo "📊 Opening monitoring dashboard..."
	gcloud app browse --service=default

# Security checks
security-scan:
	@echo "🔒 Running security scan..."
	cd backend && source venv/bin/activate && safety check

# Local development with hot reload
dev-hot:
	@echo "🔥 Starting development with hot reload..."
	cd backend && source venv/bin/activate && \
	export GOOGLE_APPLICATION_CREDENTIALS=$(PWD)/service-account-key.json && \
	uvicorn main:app --reload --host 0.0.0.0 --port 8080
