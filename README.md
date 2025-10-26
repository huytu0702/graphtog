# GraphToG - GraphRAG-based Document Processing with Tree of Graphs Reasoning

A knowledge graph-based document processing and Q&A system implementing Microsoft's GraphRAG methodology enhanced with Tree of Graphs (ToG) reasoning. The system allows users to upload documents, extracts knowledge graphs, and generates intelligent answers to user queries.

## 🎯 Key Features (Phase 1.1)

- ✅ **User Authentication**: Secure registration and login with JWT tokens
- ✅ **Document Upload**: Support for MD files with drag-and-drop UI
- ✅ **Document Parsing**: Direct processing of MD files with structure preservation
- ✅ **Knowledge Graph Foundation**: Neo4j integration for graph-based knowledge storage
- ✅ **RESTful API**: FastAPI backend with comprehensive documentation
- ✅ **Docker Containerization**: Ready-to-deploy with docker-compose

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.10+)
- **Databases**: 
  - PostgreSQL (user data, documents, queries)
  - Neo4j (knowledge graph)
  - Redis (caching)
- **Document Processing**: 
  - Direct MD file parsing and processing
- **AI/LLM**: Google Gemini 2.5 Flash
- **Package Manager**: uv (fast Python package manager)

### Frontend (Phase 1.2)
- **Framework**: Next.js 15 with App Router
- **UI Components**: shadcn/ui
- **Styling**: Tailwind CSS
- **Auth**: NextAuth.js
- **State Management**: Zustand

### Deployment
- Docker & Docker Compose
- Multi-stage builds for optimized images

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development)
- Node.js 18+ (for frontend development)
- uv (Python package manager)
- Git

### Installation

```bash
# Install uv
pip install uv

# Verify installation
uv --version
```

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/graphtog.git
cd graphtog
```

### 2. Setup Environment Variables

```bash
# Copy the example configuration
cp backend/app/config.py .env  # Create .env from config template

# Edit .env and set your API keys
# GOOGLE_API_KEY=your-key-here
```

### 3. Start Services with Docker Compose

```bash
# Start all services (PostgreSQL, Neo4j, Redis, Backend)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 4. Backend Setup (Local Development)

```bash
cd backend

# Create Python virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Sync dependencies
uv sync

# Run development server
uv run uvicorn app.main:app --reload

# Access API documentation
# Open browser: http://localhost:8000/docs
```

### 5. Frontend Setup (Phase 1.2)

```bash
cd frontend

# Install dependencies
npm install

# Setup environment variables
cp .env.example .env.local

# Run development server
npm run dev

# Open browser: http://localhost:3000
```

## 📚 API Documentation

Once the backend is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key Endpoints

#### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/token` - Login and get access token
- `GET /api/auth/me` - Get current user

#### Health Checks
- `GET /health` - Health check
- `GET /info` - Application info
- `GET /` - Root endpoint

#### Documents (Coming in Phase 1.2)
- `POST /api/documents/upload` - Upload MD document
- `GET /api/documents` - List user documents
- `GET /api/documents/{doc_id}` - Get document details

#### Queries (Coming in Phase 1.2)
- `POST /api/query` - Submit query
- `GET /api/queries` - Get query history

## 📁 Project Structure

```
graphtog/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   ├── documents.py (Phase 1.2)
│   │   │   │   └── queries.py (Phase 1.2)
│   │   ├── db/
│   │   │   ├── postgres.py
│   │   │   └── neo4j.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── document.py
│   │   │   └── query.py
│   │   ├── schemas/
│   │   │   └── auth.py
│   │   ├── services/
│   │   │   ├── security.py
│   │   │   ├── document_processor.py
│   │   │   ├── graph_service.py (Phase 1.2)
│   │   │   └── llm_service.py (Phase 1.2)
│   │   ├── main.py
│   │   └── config.py
│   ├── pyproject.toml
│   ├── .python-version
│   └── Dockerfile
├── frontend/ (Phase 1.2)
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
├── docker-compose.yml
├── .gitignore
├── .dockerignore
├── README.md
└── docs/
    ├── PRD.md
    ├── phase1-2.md
    └── tasks-phase12.md
```

## 🔐 Authentication Flow

1. User registers with email and password
2. Password is hashed with bcrypt
3. User can login to get JWT access token
4. Access token is used to authenticate subsequent requests
5. Token expires after configurable time (default: 30 minutes)

### Example API Calls

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "name": "User Name",
    "password": "securepassword123"
  }'

# Login
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'

# Get current user (using token)
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🐳 Docker Usage

### Build Images

```bash
# Build backend image
docker build -t graphtog-backend:latest ./backend

# Build frontend image (Phase 1.2)
docker build -t graphtog-frontend:latest ./frontend
```

### Run with Docker Compose

```bash
# Start all services
docker-compose up

# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f neo4j

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## 📊 Database Connections

### PostgreSQL
- **Host**: localhost (or postgres when running in Docker)
- **Port**: 5432
- **Username**: graphtog_user
- **Password**: graphtog_password
- **Database**: graphtog_db

### Neo4j
- **URI**: bolt://localhost:7687 (or bolt://neo4j:7687 in Docker)
- **Username**: neo4j
- **Password**: graphtog_password
- **Browser**: http://localhost:7474

### Redis
- **Host**: localhost (or redis in Docker)
- **Port**: 6379

## 🧪 Testing

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Backend info
curl http://localhost:8000/info

# Database connections are tested during startup
```

### Database Connectivity

```bash
# PostgreSQL
psql -h localhost -U graphtog_user -d graphtog_db

# Neo4j Cypher
# Open http://localhost:7474 and use web interface
```

## 🔄 Development Workflow

1. Make changes to backend code
2. Backend auto-reloads (when running with `--reload`)
3. Access updated API at http://localhost:8000/docs
4. Test with curl or Swagger UI

## 📝 Environment Variables

Key environment variables (set in .env or docker-compose):

```
# Backend Config
DEBUG=True
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Databases
DATABASE_URL=postgresql://graphtog_user:graphtog_password@postgres:5432/graphtog_db
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=graphtog_password
REDIS_URL=redis://redis:6379/0

# AI/LLM
GOOGLE_API_KEY=your-google-api-key
GEMINI_MODEL=gemini-2.5-flash

# File Upload Configuration
MAX_UPLOAD_SIZE=52428800  # 50MB
UPLOAD_DIR=./uploads

# File Upload
MAX_UPLOAD_SIZE=52428800  # 50MB
UPLOAD_DIR=./uploads
```

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Kill process using port 8000
lsof -i :8000
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

### Database Connection Issues
```bash
# Check PostgreSQL
docker-compose logs postgres

# Check Neo4j
docker-compose logs neo4j

# Restart services
docker-compose restart
```

### Module Import Errors
```bash
# Ensure Python path is correct
export PYTHONPATH="${PYTHONPATH}:/path/to/backend"

# Or run from project root
python -m uvicorn app.main:app --reload
```

## 📖 Documentation

- `docs/PRD.md` - Product requirements and vision
- `docs/phase1-2.md` - Implementation plan for phases 1 and 2
- `docs/tasks-phase12.md` - Task checklist
- FastAPI Docs: http://localhost:8000/docs (when running)

## 🚧 Upcoming Features (Phase 1.2+)

- MD document parsing and processing
- Knowledge graph construction
- Basic Q&A functionality
- Community detection (Phase 2)
- Advanced retrieval algorithms (Phase 2)
- Graph visualization (Phase 2)
- LangGraph agent implementation (Phase 4)
- LangSmith integration (Phase 4+)

## 💡 Contributing

1. Create a feature branch (`git checkout -b feature/amazing-feature`)
2. Commit changes (`git commit -m 'Add amazing feature'`)
3. Push to branch (`git push origin feature/amazing-feature`)
4. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 👥 Team

GraphToG Development Team

## 📧 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Last Updated**: October 2024
**Current Phase**: 1.1 (Infrastructure & Authentication)
**Next Phase**: 1.2 (Document Processing & Knowledge Graph)
