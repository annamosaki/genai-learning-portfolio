#!/bin/bash

# LLM Lab Web Application Start Script

echo "🚀 Starting LLM Foundation Ladder Demo"
echo "=====================================\n"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Start the development server
echo "🌐 Starting development server..."
echo "   → Local:   http://localhost:3000"
echo "   → Network: Check terminal output for network URL"
echo ""
echo "💡 The app will automatically proxy API calls to:"
echo "   → ${LAB_API_URL:-http://localhost:8100}"
echo ""

npm run dev