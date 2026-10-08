#!/bin/bash
# RutinitasKu Deployment Script

set -e

echo "🚀 Starting RutinitasKu deployment..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env with your configuration before running again."
    exit 1
fi

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "🐳 Docker detected. Using Docker deployment..."

    # Build and run with Docker Compose
    if command -v docker-compose &> /dev/null; then
        echo "Building and starting containers..."
        docker-compose up -d --build
        echo "✅ RutinitasKu is running at http://localhost:${PORT:-7860}"
    else
        echo "Building Docker image..."
        docker build -t rutinitasku .
        echo "Starting container..."
        docker run -d \
            --name rutinitasku \
            -p ${PORT:-7860}:7860 \
            -v $(pwd)/data:/app/data \
            -v $(pwd)/.env:/app/.env:ro \
            --restart unless-stopped \
            rutinitasku
        echo "✅ RutinitasKu is running at http://localhost:${PORT:-7860}"
    fi

else
    echo "📦 Docker not found. Using local Python deployment..."

    # Check Python version
    python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo "Python version: $python_version"

    # Create virtual environment if not exists
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    echo "Installing dependencies..."
    pip install -r requirements.txt

    # Create data directories
    mkdir -p data/uploads data/workspace

    # Run the application
    echo "Starting RutinitasKu..."
    python3 app.py
fi