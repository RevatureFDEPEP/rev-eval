#!/bin/bash

# Quick Start Script for Rev Eval AI
# This script starts all services using Docker Compose

set -e  # Exit on error

echo "🚀 Rev Eval AI - Quick Start"
echo "=============================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "   Please start Docker Desktop and try again"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env file"
        echo "   Please edit .env and add your WorkOS credentials, then run this script again"
        exit 0
    else
        echo "❌ Error: .env.example not found"
        exit 1
    fi
fi

# Check if WorkOS credentials are set
if grep -q "your_client_id_here" .env 2>/dev/null; then
    echo "⚠️  Warning: WorkOS credentials not configured in .env"
    echo "   Please edit .env and add your credentials from https://dashboard.workos.com"
    echo ""
    echo "   Required variables:"
    echo "   - WORKOS_CLIENT_ID"
    echo "   - WORKOS_API_KEY"
    echo "   - WORKOS_DEFAULT_ORG"
    echo "   - WORKOS_COOKIE_PASSWORD"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

echo "📦 Building and starting services with Docker Compose..."
echo ""

# Check if --no-build flag is passed
if [[ "$1" == "--no-build" ]]; then
    echo "⚡ Skipping build step (using existing images)..."
    docker compose up -d
else
    echo "🔨 Building images (this may take a few minutes)..."
    docker compose up -d --build
fi

echo ""
echo "⏳ Waiting for services to be healthy..."
echo ""

# Wait for services to initialize
sleep 10

# Check service health
echo "🔍 Checking service health..."
echo ""

# Function to check if a service is healthy
#fall back after retries?? if the script is terminated for any reason, what will happen???
check_service() {
    local name=$1
    local url=$2
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo "✅ $name is healthy"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done

    echo "⚠️  $name is not responding (this might be okay, check logs)"
    return 1
}

# Check each service
# but why are we missing data layer checks(postgres, minio,mongo)
#is it too early for db health checks or some other reason 
#some health checks are not required for now 
check_service "Consul" "http://localhost:8500/v1/status/leader"
check_service "User Service" "http://localhost:8002/health"
check_service "Notification Service" "http://localhost:8004/health"
check_service "Test Management Service" "http://localhost:8001/health"
check_service "Question Management Service" "http://localhost:8003/health"
check_service "AI Quiz Service" "http://localhost:8005/health"
check_service "AI Interview Service" "http://localhost:8009/health"
check_service "Quiz Evaluation Lambda" "http://localhost:9000/health"
check_service "API Gateway" "http://localhost:8000/health"
check_service "Frontend" "http://localhost:3000"

echo ""
echo "🌱 Notes:"
echo "   - Check logs: docker compose logs -f test-management-service"

echo ""
echo "=============================="
echo "✨ Rev Eval AI is ready!"
echo ""
echo "📱 Access the application:"
echo "   Frontend:             http://localhost:3000"
echo "   API Gateway:          http://localhost:8000"
echo "   Consul UI:            http://localhost:8500"
echo ""
echo "📚 API Documentation:"
echo "   User Service:         http://localhost:8002/docs"
echo "   Test Management:      http://localhost:8001/docs"
echo "   Question Management:  http://localhost:8003/docs"
echo "   Notification Service: http://localhost:8004/docs"
echo "   AI Quiz Service:      http://localhost:8005/docs"
echo "   AI Interview Service: http://localhost:8009/docs"
echo ""
echo "🔧 Quiz Evaluation Lambda:"
echo "   Health Check:         http://localhost:9000/health"
echo "   Trigger Endpoint:     http://localhost:9000/invoke"
echo "   See:                  lambda/quiz-evaluation-handler/LOCAL_TESTING.md"
echo ""
echo "🔑 Test Credentials:"
echo "   Trainer:      rev-eval.test001@yopmail.com"
echo "   Participant:  rev-eval.test002@yopmail.com"
echo ""
echo "📊 View logs:"
echo "   All services:       docker compose logs -f"
echo "   Specific service:   docker compose logs -f <service-name>"
echo "   Example:            docker compose logs -f api-gateway"
echo "   Lambda logs:        docker compose logs -f quiz-evaluation-lambda"
echo ""
echo "🛑 Stop services:"
echo "   docker compose down"
echo ""
echo "🔄 Quick restart (no rebuild):"
echo "   ./start.sh --no-build"
echo ""
echo "🗑️  Clean restart (rebuilds images):"
echo "   docker compose down && ./start.sh"
echo ""
