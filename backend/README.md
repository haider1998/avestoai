# 🔮 AvestoAI Backend

Revolutionary Financial Intelligence Platform with Fi MCP Integration - Ready for Google Cloud Platform deployment.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker
- Google Cloud SDK (`gcloud`)
- Google Cloud Project with billing enabled

### Local Development

1. **Clone and Setup**
   ```bash
   git clone <your-repo>
   cd avestoai/backend
   cp .env.template .env
   # Edit .env with your configuration
   ```

2. **Install Dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run Locally**
   ```bash
   python app/main.py
   ```

   The API will be available at `http://localhost:8080`

### GCP Deployment

#### Option 1: Automated Deployment (Recommended)

```bash
# Set your GCP project ID
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Run the deployment script
./deploy.sh
```

#### Option 2: Manual Deployment

1. **Setup GCP Project**
   ```bash
   gcloud config set project your-project-id
   gcloud services enable cloudbuild.googleapis.com run.googleapis.com
   ```

2. **Build and Deploy**
   ```bash
   gcloud builds submit --config cloudbuild.yaml
   ```

#### Option 3: Docker Build and Push

```bash
# Build locally
docker build -t gcr.io/your-project-id/avestoai-backend .

# Push to Container Registry
docker push gcr.io/your-project-id/avestoai-backend

# Deploy to Cloud Run
gcloud run deploy avestoai-backend \
  --image gcr.io/your-project-id/avestoai-backend \
  --region us-central1 \
  --allow-unauthenticated
```

## 🏗️ Architecture

### Core Components

- **FastAPI Application**: High-performance async web framework
- **Vertex AI Integration**: Google's AI/ML platform for financial analysis
- **Firestore**: NoSQL database for storing user data and analysis results
- **Fi MCP Service**: Integration with Fi Money's MCP protocol
- **Prometheus Metrics**: Monitoring and observability
- **Structured Logging**: GCP-compatible JSON logging

### Directory Structure

```
backend/
├── app/
│   └── main.py              # FastAPI application entry point
├── models/
│   ├── configs.py           # Configuration management
│   ├── schemas.py           # Pydantic models
│   └── fi_mcp_simulator.py  # Test data simulator
├── services/
│   ├── vertex_ai_service.py # AI/ML service integration
│   ├── firestore_service.py # Database operations
│   ├── fi_mcp_service.py    # Fi MCP integration
│   ├── opportunity_engine.py # Business logic
│   └── on_device_ai.py      # Local AI processing
├── utils/
│   ├── logging_config.py    # Structured logging setup
│   ├── middleware.py        # HTTP middleware
│   ├── metrics.py           # Prometheus metrics
│   └── env_validator.py     # Environment validation
├── migrations/
│   └── init_db.py           # Database initialization
├── Dockerfile               # Container configuration
├── cloudbuild.yaml          # GCP Cloud Build config
├── deploy.sh                # Deployment automation
├── requirements.txt         # Python dependencies
└── .env.template            # Environment variables template
```

## 🔧 Configuration

### Environment Variables

Copy `.env.template` to `.env` and configure:

#### Required Variables
```bash
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
VERTEX_AI_LOCATION=us-central1
FI_MCP_BASE_URL=https://fi-mcp-dev-172306289913.asia-south1.run.app
```

#### Optional Variables
```bash
ENVIRONMENT=development
LOG_LEVEL=INFO
PORT=8080
RATE_LIMIT_CALLS=100
```

### GCP Service Account

The application requires a service account with these roles:
- `roles/aiplatform.user` - For Vertex AI access
- `roles/datastore.user` - For Firestore access
- `roles/secretmanager.secretAccessor` - For secrets access
- `roles/monitoring.metricWriter` - For metrics

## 📊 API Endpoints

### Health & Monitoring
- `GET /` - Service status
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

### Fi MCP Authentication
- `POST /api/v1/fi-auth/initiate` - Start authentication
- `POST /api/v1/fi-auth/verify` - Verify OTP
- `GET /api/v1/fi-auth/status/{mobile}` - Check auth status

### Core AI Services
- `POST /api/v1/analyze-opportunities` - Generate financial opportunities
- `POST /api/v1/predict-decision` - Analyze financial decisions
- `POST /api/v1/chat` - AI chat interface
- `GET /api/v1/financial-dashboard/{mobile}` - User dashboard
- `GET /api/v1/financial-health-stream/{mobile}` - Real-time health monitoring

### Fi MCP Management
- `POST /api/v1/switch-scenario` - Switch test scenarios

## 🔍 Monitoring & Observability

### Metrics
- Request counts and durations
- Business metrics (opportunities, decisions, chats)
- Service health and errors
- Fi MCP and Vertex AI usage

### Logging
- Structured JSON logging
- GCP Cloud Logging integration
- Request tracing
- Error tracking

### Health Checks
- Service dependencies status
- Database connectivity
- External API availability

## 🧪 Testing

### Test Scenarios
The application includes Fi MCP test scenarios:
- `no_assets` - User with minimal assets
- `balanced` - Typical user profile
- `high_spender` - High spending patterns
- `starter` - New to financial planning

### Load Testing
```bash
# Install artillery
npm install -g artillery

# Run load test
artillery quick --count 10 --num 100 http://localhost:8080/health
```

## 🚨 Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure `PYTHONPATH=/app` is set
   - Check all import paths are relative to project root

2. **GCP Authentication**
   ```bash
   gcloud auth application-default login
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   ```

3. **Firestore Permissions**
   ```bash
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
     --role="roles/datastore.user"
   ```

4. **Memory Issues on Cloud Run**
   - Increase memory allocation in `cloudbuild.yaml`
   - Optimize dependency loading

### Debugging

1. **Enable Debug Logging**
   ```bash
   export LOG_LEVEL=DEBUG
   ```

2. **Check Service Health**
   ```bash
   curl https://your-service-url/health
   ```

3. **View Logs**
   ```bash
   gcloud logs read "resource.type=cloud_run_revision" --limit 50
   ```

## 🔐 Security

### Best Practices
- Service account with minimal required permissions
- Environment variables for sensitive data
- Rate limiting enabled
- CORS properly configured
- Non-root container user

### Secrets Management
```bash
# Store secrets in Secret Manager
gcloud secrets create fi-mcp-api-key --data-file=api-key.txt

# Access in application
export FI_MCP_API_KEY=$(gcloud secrets versions access latest --secret="fi-mcp-api-key")
```

## 📈 Performance

### Optimization
- Multi-stage Docker build
- Dependency caching
- Async/await throughout
- Connection pooling
- Response compression

### Scaling
- Cloud Run auto-scaling
- Concurrent request handling
- Stateless design
- Caching strategies

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review GCP Cloud Run documentation

---

**Built with ❤️ for the future of financial intelligence**
