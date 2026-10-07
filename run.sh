#!/bin/bash

# NaraTask AI - Run Script

echo "🤖 Starting NaraTask AI..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt -q

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "Please edit .env and add your API keys:"
    echo "  - ANTHROPIC_API_KEY"
    echo "  - NARAROUTER_API_KEY"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Create data directories
mkdir -p data/uploads data/workspace

# Run the application
echo ""
echo "🚀 Launching NaraTask AI..."
echo "📍 Open http://localhost:7860 in your browser"
echo ""
python app.py