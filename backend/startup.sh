#!/bin/bash
# startup.sh - Optimized startup script for Cloud Run

set -e

echo "🚀 Starting AvestoAI Backend..."

# Set Python path to ensure imports work
export PYTHONPATH="/app:/app/backend:$PYTHONPATH"

# Verify Python path
echo "Python path: $PYTHONPATH"

# Test imports before starting server
python -c "
import sys
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/backend')
try:
    from backend.app.main import app
    print('✅ Import test successful')
except ImportError as e:
    print(f'❌ Import test failed: {e}')
    sys.exit(1)
"

# Start uvicorn with optimized settings for Cloud Run
exec uvicorn backend.app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8080} \
    --workers 1 \
    --timeout-keep-alive 120 \
    --timeout-graceful-shutdown 30 \
    --log-level info \
    --access-log \
    --use-colors
