# 🚀 AvestoAI Backend - GCP Deployment Checklist

## ✅ Pre-Deployment Checklist

### 1. Code Quality & Structure
- [x] Fixed all import paths (removed `backend.` prefix)
- [x] All Python files compile successfully
- [x] Requirements files cleaned and properly formatted
- [x] Docker configuration optimized for GCP Cloud Run
- [x] Environment configuration template created
- [x] Logging configured for GCP compatibility

### 2. GCP Prerequisites
- [ ] GCP Project created and billing enabled
- [ ] Required APIs enabled:
  - [ ] Cloud Build API
  - [ ] Cloud Run API
  - [ ] Container Registry API
  - [ ] Vertex AI API
  - [ ] Firestore API
  - [ ] Secret Manager API
  - [ ] Cloud Monitoring API
- [ ] Service account created with proper roles
- [ ] gcloud CLI installed and authenticated

### 3. Environment Configuration
- [ ] Copy `.env.template` to `.env`
- [ ] Set `GOOGLE_CLOUD_PROJECT` to your project ID
- [ ] Configure other environment variables as needed
- [ ] Store sensitive data in GCP Secret Manager (optional)

### 4. Local Testing (Optional)
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run locally: `python app/main.py`
- [ ] Test endpoints: `curl http://localhost:8080/health`

## 🚀 Deployment Options

### Option 1: Automated Deployment (Recommended)
```bash
# Set your project ID
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Run deployment script
./deploy.sh
```

### Option 2: Cloud Build
```bash
gcloud builds submit --config cloudbuild.yaml
```

### Option 3: Manual Docker Deployment
```bash
# Build and push
docker build -t gcr.io/your-project-id/avestoai-backend .
docker push gcr.io/your-project-id/avestoai-backend

# Deploy to Cloud Run
gcloud run deploy avestoai-backend \
  --image gcr.io/your-project-id/avestoai-backend \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2
```

## 🔧 Post-Deployment Verification

### 1. Health Checks
- [ ] Service URL accessible
- [ ] Health endpoint returns 200: `GET /health`
- [ ] Root endpoint returns service info: `GET /`
- [ ] Metrics endpoint accessible: `GET /metrics`

### 2. API Testing
- [ ] Fi MCP authentication flow works
- [ ] Core AI endpoints respond correctly
- [ ] Error handling works properly
- [ ] Rate limiting is functional

### 3. Monitoring Setup
- [ ] Logs appearing in Cloud Logging
- [ ] Metrics being collected
- [ ] Alerts configured (optional)
- [ ] Uptime monitoring setup (optional)

## 🐛 Common Issues & Solutions

### Import Errors
**Issue**: `ModuleNotFoundError: No module named 'backend'`
**Solution**: All import paths have been fixed to be relative to project root

### Authentication Errors
**Issue**: GCP authentication failures
**Solution**: 
```bash
gcloud auth application-default login
# OR set service account key
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

### Memory Issues
**Issue**: Cloud Run out of memory
**Solution**: Increase memory allocation in deployment configuration

### Firestore Permissions
**Issue**: Firestore access denied
**Solution**: Ensure service account has `roles/datastore.user` role

## 📊 Performance Optimization

### Cloud Run Configuration
- **Memory**: 2Gi (can be adjusted based on usage)
- **CPU**: 2 (can be scaled up for high load)
- **Concurrency**: 100 requests per instance
- **Max Instances**: 10 (adjust based on expected load)
- **Timeout**: 300 seconds

### Cost Optimization
- Use minimum required resources
- Enable request-based scaling
- Monitor usage patterns
- Implement caching where appropriate

## 🔐 Security Considerations

### Service Account Permissions
- Use principle of least privilege
- Only grant necessary roles
- Regularly audit permissions

### Environment Variables
- Store sensitive data in Secret Manager
- Use environment-specific configurations
- Never commit secrets to version control

### Network Security
- Configure CORS properly
- Implement rate limiting
- Use HTTPS only
- Consider VPC if needed

## 📈 Monitoring & Alerting

### Key Metrics to Monitor
- Request latency and error rates
- Memory and CPU usage
- Fi MCP service availability
- Vertex AI API usage and costs
- Firestore read/write operations

### Recommended Alerts
- High error rate (>5%)
- High latency (>2 seconds)
- Service unavailability
- Resource exhaustion
- Cost thresholds

## 🔄 CI/CD Setup (Optional)

### GitHub Actions
```yaml
name: Deploy to Cloud Run
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: google-github-actions/setup-gcloud@v0
        with:
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          project_id: ${{ secrets.GCP_PROJECT_ID }}
      - run: gcloud builds submit --config cloudbuild.yaml
```

## 📞 Support & Resources

### Documentation
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Firestore Documentation](https://cloud.google.com/firestore/docs)

### Troubleshooting
- Check Cloud Logging for detailed error messages
- Use `gcloud run services describe` for service status
- Monitor resource usage in Cloud Console
- Test individual components separately

---

**Ready for deployment! 🚀**

Follow this checklist step by step to ensure a successful deployment to Google Cloud Platform.
