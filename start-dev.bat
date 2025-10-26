@echo off
REM GraphToG Development Startup Script for Windows
REM This script starts all services for local development

echo.
echo 🚀 GraphToG Development Environment Startup
echo ===========================================
echo.

REM Check if Docker is running
echo 📦 Checking Docker...
docker ps > nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop.
    pause
    exit /b 1
)
echo ✅ Docker is running
echo.

REM Start Docker Compose services
echo 🐳 Starting Docker Compose services (PostgreSQL, Neo4j, Redis)...
docker-compose up -d
echo.

REM Wait for services to be ready
echo ⏳ Waiting for services to be ready...
timeout /t 5 /nobreak
echo.

echo 🔍 Checking service health...
echo.

echo 📚 Service Information:
echo   - PostgreSQL: localhost:5432 (user: graphtog_user, db: graphtog_db)
echo   - Neo4j: http://localhost:7474 (user: neo4j)
echo   - Redis: localhost:6379
echo.

REM Setup and start backend
echo 🔧 Setting up backend...
cd backend

REM Check if virtual environment exists
if not exist ".venv" (
    echo 📝 Creating Python virtual environment...
    uv venv
)

REM Activate venv and sync dependencies
echo 📦 Installing/syncing Python dependencies with uv...
call .venv\Scripts\activate.bat
uv sync

echo.
echo ✅ Backend setup complete!
echo.
echo 🎯 To start the backend API server, run:
echo    cd backend
echo    .venv\Scripts\activate.bat
echo    uv run uvicorn app.main:app --reload
echo.
echo 📚 API Documentation will be available at:
echo    - Swagger UI: http://localhost:8000/docs
echo    - ReDoc: http://localhost:8000/redoc
echo.
echo 🛑 To stop all services, run:
echo    docker-compose down
echo.
pause
