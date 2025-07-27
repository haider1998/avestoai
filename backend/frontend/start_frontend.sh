#!/bin/bash

# AvestoAI Frontend Startup Script

echo "🔮 AvestoAI Frontend Server"
echo "=========================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "Please install Python 3 and try again."
    exit 1
fi

# Check if backend is running
echo "🔍 Checking backend status..."
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ Backend is running on http://localhost:8080"
else
    echo "⚠️  Backend is not running on http://localhost:8080"
    echo "Please start the backend server first:"
    echo "   cd ../backend && python app/main.py"
    echo ""
    echo "Continuing anyway... (frontend will show connection errors)"
fi

# Set default port if not specified
if [ -z "$FRONTEND_PORT" ]; then
    export FRONTEND_PORT=3000
fi

echo ""
echo "🚀 Starting frontend server on port $FRONTEND_PORT..."
echo "📱 Open http://localhost:$FRONTEND_PORT in your browser"
echo ""

# Start the server
python3 server.py
