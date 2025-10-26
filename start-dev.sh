#!/bin/bash

# GraphToG Development Startup Script
# This script starts all services for local development

set -e

echo "🚀 GraphToG Development Environment Startup"
echo "==========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
echo "📦 Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"

# Start Docker Compose services
echo ""
echo "🐳 Starting Docker Compose services (PostgreSQL, Neo4j, Redis)..."
docker-compose up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if services are running
echo ""
echo "🔍 Checking service health..."

# PostgreSQL
if docker-compose exec -T postgres pg_isready -U graphtog_user > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL is ready (port 5432)${NC}"
else
    echo -e "${YELLOW}⚠️  PostgreSQL is starting...${NC}"
fi

# Neo4j
if docker-compose exec -T neo4j wget --quiet --tries=1 --spider http://localhost:7474 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Neo4j is ready (port 7474)${NC}"
else
    echo -e "${YELLOW}⚠️  Neo4j is starting...${NC}"
fi

# Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is ready (port 6379)${NC}"
else
    echo -e "${YELLOW}⚠️  Redis is starting...${NC}"
fi

echo ""
echo "📚 Service Information:"
echo "  - PostgreSQL: localhost:5432 (user: graphtog_user, db: graphtog_db)"
echo "  - Neo4j: http://localhost:7474 (user: neo4j)"
echo "  - Redis: localhost:6379"
echo ""

# Setup and start backend
echo "🔧 Setting up backend..."
cd backend

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📝 Creating Python virtual environment..."
    uv venv
fi

# Activate venv and sync dependencies
echo "📦 Installing/syncing Python dependencies with uv..."
source .venv/bin/activate
uv sync

echo ""
echo -e "${GREEN}✅ Backend setup complete!${NC}"
echo ""
echo "🎯 To start the backend API server, run:"
echo "   cd backend"
echo "   source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate"
echo "   uv run uvicorn app.main:app --reload"
echo ""
echo "📚 API Documentation will be available at:"
echo "   - Swagger UI: http://localhost:8000/docs"
echo "   - ReDoc: http://localhost:8000/redoc"
echo ""
echo "🛑 To stop all services, run:"
echo "   docker-compose down"
echo ""
