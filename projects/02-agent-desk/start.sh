#!/bin/bash

# Agent Desk Startup Script
# Starts the multi-agent investment desk API and web interface

set -e

echo "🚀 Starting Agent Desk..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "start.sh" ]; then
    echo "❌ Please run this script from the Agent Desk root directory"
    exit 1
fi

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port $1 is already in use"
        return 1
    fi
    return 0
}

# Function to start API server
start_api() {
    echo -e "${BLUE}📡 Starting Agent Desk API (port 8200)...${NC}"
    
    if ! check_port 8200; then
        echo "   API server may already be running"
        return 1
    fi
    
    cd api
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "   Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    echo "   Installing/updating Python dependencies..."
    pip install -q -r requirements.txt
    
    # Set PYTHONPATH
    export PYTHONPATH="${PWD}:${PYTHONPATH}"
    
    # Start API server
    echo "   Starting FastAPI server..."
    uvicorn desk.app:app --host 0.0.0.0 --port 8200 --reload &
    API_PID=$!
    
    cd ..
    echo -e "${GREEN}✅ API server started (PID: $API_PID)${NC}"
    return 0
}

# Function to start web server
start_web() {
    echo -e "${BLUE}🌐 Starting Agent Desk Web (port 3200)...${NC}"
    
    if ! check_port 3200; then
        echo "   Web server may already be running"
        return 1
    fi
    
    cd web
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo "   Installing Node.js dependencies..."
        npm install
    fi
    
    # Build if needed
    if [ ! -d ".next" ]; then
        echo "   Building Next.js application..."
        npm run build
    fi
    
    # Start web server
    echo "   Starting Next.js server..."
    npm run start &
    WEB_PID=$!
    
    cd ..
    echo -e "${GREEN}✅ Web server started (PID: $WEB_PID)${NC}"
    return 0
}

# Function to start A2A servers (optional)
start_a2a_servers() {
    if [ "$ENABLE_A2A_SERVERS" = "true" ]; then
        echo -e "${BLUE}🤖 Starting A2A servers...${NC}"
        
        cd api
        source venv/bin/activate
        export PYTHONPATH="${PWD}:${PYTHONPATH}"
        
        # Start A2A servers in background
        python -m desk.a2a_servers &
        A2A_PID=$!
        
        cd ..
        echo -e "${GREEN}✅ A2A servers started (PID: $A2A_PID)${NC}"
        echo -e "${YELLOW}   Agent cards available on ports 8201-8205${NC}"
    else
        echo -e "${YELLOW}ℹ️  A2A servers disabled (using in-process agents)${NC}"
    fi
}

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down Agent Desk...${NC}"
    
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
        echo "   Stopped API server"
    fi
    
    if [ ! -z "$WEB_PID" ]; then
        kill $WEB_PID 2>/dev/null || true
        echo "   Stopped web server"
    fi
    
    if [ ! -z "$A2A_PID" ]; then
        kill $A2A_PID 2>/dev/null || true
        echo "   Stopped A2A servers"
    fi
    
    # Kill any remaining processes on our ports
    pkill -f "uvicorn.*8200" 2>/dev/null || true
    pkill -f "next.*3200" 2>/dev/null || true
    
    echo -e "${GREEN}✅ Shutdown complete${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo -e "${BLUE}📄 Loading environment variables from .env${NC}"
    export $(cat .env | grep -v ^# | xargs) 2>/dev/null || true
fi

# Check Python dependencies
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check Node.js dependencies
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

# Start services
echo -e "${GREEN}🎯 Agent Desk - Multi-Agent Investment Analysis${NC}"
echo "   API: http://localhost:8200"
echo "   Web: http://localhost:3200"
echo ""

# Start API server
start_api
sleep 2

# Start web server  
start_web
sleep 2

# Start A2A servers if enabled
start_a2a_servers

echo ""
echo -e "${GREEN}🎉 Agent Desk is running!${NC}"
echo -e "${BLUE}   Open http://localhost:3200 to get started${NC}"
echo -e "${YELLOW}   Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for user interrupt
while true; do
    sleep 1
done