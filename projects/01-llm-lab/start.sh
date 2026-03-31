#!/bin/bash

# LLM Lab Start Script
# Starts both API and web services

echo "🚀 Starting LLM Lab..."

# Check if we're in the right directory
if [ ! -f "start.sh" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Start API server
echo "📡 Starting API server on port 8100..."
cd api
python -m llm_lab.app &
API_PID=$!
cd ..

echo "🌐 API started (PID: $API_PID)"

# Check if web directory exists and start web server
if [ -d "web" ]; then
    echo "🖥️  Starting web server on port 3100..."
    cd web
    if [ -f "package.json" ]; then
        npm start &
        WEB_PID=$!
        echo "🌐 Web started (PID: $WEB_PID)"
    else
        echo "⚠️  No package.json found in web directory"
    fi
    cd ..
else
    echo "ℹ️  No web directory found - API only mode"
fi

echo ""
echo "✅ LLM Lab is running!"
echo "📡 API: http://localhost:8100"
echo "📊 Health: http://localhost:8100/health"
echo "📚 Docs: http://localhost:8100/docs"

if [ ! -z "$WEB_PID" ]; then
    echo "🖥️  Web: http://localhost:3100"
fi

echo ""
echo "Press Ctrl+C to stop all services"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null
        echo "📡 API stopped"
    fi
    
    if [ ! -z "$WEB_PID" ]; then
        kill $WEB_PID 2>/dev/null
        echo "🖥️  Web stopped"
    fi
    
    echo "✅ All services stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for services
wait