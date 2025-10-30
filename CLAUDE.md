# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GraphToG is a GraphRAG-based document processing system with Tree of Graphs (ToG) reasoning. It combines Microsoft's GraphRAG methodology with a knowledge graph approach to process markdown documents and provide intelligent Q&A capabilities. The system uses Neo4j for graph storage, PostgreSQL for relational data, and Google Gemini 2.5 Flash for LLM processing.

## Technology Stack

**Backend:** FastAPI (Python 3.10+), SQLAlchemy, Neo4j, PostgreSQL, Redis
**Frontend:** Next.js 15, shadcn/ui, Tailwind CSS, NextAuth.js, Zustand
**Package Management:** uv (Python), npm (Node.js)
**Deployment:** Docker Compose

## Development Commands

### Starting Services

```bash
# Start databases (PostgreSQL, Neo4j, Redis)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Backend Development

```bash
cd backend

# Setup virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Run development server (auto-reload enabled)
uv run uvicorn app.main:app --reload

# Run on specific port
uv run uvicorn app.main:app --reload --port 8001

# Access API documentation
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

### Testing

```bash
cd backend

# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_endpoints_integration.py

# Run tests with markers
uv run pytest -m integration  # Integration tests only
uv run pytest -m unit         # Unit tests only
uv run pytest -m benchmark    # Benchmark tests only

# Run tests with coverage
uv run pytest --cov=app --cov-report=html

# Run tests in parallel
uv run pytest -n auto
```

Available test markers: `integration`, `unit`, `benchmark`, `slow`, `auth`, `crud`

### Code Quality

```bash
cd backend

# Format code with black
uv run black app/ tests/

# Lint with ruff
uv run ruff check app/ tests/

# Type checking with mypy
uv run mypy app/
```

## Architecture Overview

### Backend Architecture

The backend follows a layered architecture pattern:

**API Layer** (`app/api/endpoints/`): FastAPI routers handling HTTP requests
- `auth.py` - Authentication and user management
- `documents.py` - Document upload and management
- `queries.py` - Query processing and Q&A
- `communities.py` - Community detection and summarization
- `retrieval.py` - Advanced retrieval strategies
- `visualization.py` - Graph visualization endpoints
- `admin.py` - Administrative operations
- `analyze.py` - Document analysis endpoints
- `advanced_features.py` - Advanced extraction features
- `cache.py` - Cache management

**Service Layer** (`app/services/`): Business logic and processing
- `llm_service.py` - LLM integration with Google Gemini
- `graph_service.py` - Neo4j graph operations and knowledge graph management
- `document_processor.py` - MD file parsing and processing
- `query_service.py` - Query processing and answering
- `community_detection.py` - Graph community detection using Leiden algorithm
- `community_summarization.py` - Community-level summarization
- `retrieval_service.py` - Retrieval strategies (local, global, hybrid)
- `embedding_service.py` - Text embedding generation
- `chunking.py` - Document chunking strategies
- `cache_service.py` - Redis caching
- `security.py` - Password hashing and JWT token management
- `prompt.py` - LLM prompt templates

**Database Layer** (`app/db/`):
- `postgres.py` - PostgreSQL connection and SQLAlchemy ORM setup
- `neo4j.py` - Neo4j driver initialization and session management

**Models** (`app/models/`): SQLAlchemy ORM models for PostgreSQL
- `user.py` - User accounts
- `document.py` - Document metadata
- `query.py` - Query history
- `embedding.py` - Document embeddings

**Schemas** (`app/schemas/`): Pydantic models for request/response validation

### GraphRAG Implementation

The system implements Microsoft's GraphRAG methodology:

1. **Document Processing**: MD files are parsed and chunked into text units
2. **Entity Extraction**: LLM extracts entities and relationships from text chunks
3. **Graph Construction**: Entities and relationships stored in Neo4j as knowledge graph
4. **Community Detection**: Leiden algorithm identifies hierarchical communities in the graph
5. **Community Summarization**: Each community gets an LLM-generated summary
6. **Query Processing**:
   - **Local Query**: Searches specific entities and their neighborhoods
   - **Global Query**: Uses community summaries for broad questions
   - **Hybrid Query**: Combines local and global approaches

### Graph Schema (Neo4j)

**Nodes:**
- `Document` - Uploaded documents with metadata
- `TextUnit` - Chunked text segments from documents
- `Entity` - Extracted entities (people, places, concepts, etc.)
- `Community` - Detected communities with hierarchical levels

**Relationships:**
- `CONTAINS` - Document contains TextUnits
- `MENTIONS` - TextUnit mentions Entity
- `RELATES_TO` - Entity relates to Entity (with type and confidence)
- `BELONGS_TO` - Entity belongs to Community
- `PART_OF` - Community hierarchical structure

**Constraints and Indexes:** Defined in `graph_service.init_schema()`

### Frontend Architecture

Next.js 15 app using the App Router pattern:

**Routes** (`frontend/app/`):
- `(auth)/` - Authentication pages (login, register)
- `(dashboard)/` - Main application pages (upload, query, documents)
- `api/auth/` - NextAuth.js API routes

**Components** (`frontend/components/`):
- `ui/` - shadcn/ui components (button, card, dialog, etc.)
- `document-upload/` - Document upload interface
- `query-interface.tsx` - Query input and results display
- `providers.tsx` - Context providers for app state

**State Management:** Zustand stores for global state

### Authentication Flow

1. User registers with email/password via `/api/auth/register`
2. Password hashed with bcrypt before storage
3. User logs in via `/api/auth/token` (backend) or NextAuth (frontend)
4. JWT access token issued (default expiry: 24 hours)
5. Token included in `Authorization: Bearer <token>` header for authenticated requests
6. Backend validates token using `get_current_user` dependency

### LLM Service Integration

The `LLMService` class (`llm_service.py`) handles all LLM operations:
- **Rate limiting**: 60 requests/minute to respect API limits
- **Retry logic**: Exponential backoff for failed requests
- **Prompt templates**: Located in `prompt.py` for entity extraction, relationship extraction, query classification, and answer generation
- **Response parsing**: Handles JSON responses with markdown code block cleanup

Key methods:
- `extract_entities()` - Extract entities from text
- `extract_relationships()` - Extract relationships between entities
- `classify_query()` - Determine query type (local/global/hybrid)
- `generate_answer()` - Generate contextual answers from retrieved data
- `summarize_community()` - Generate community summaries

### Configuration

Environment variables are managed in `app/config.py` using `Settings` class:
- Database URLs for PostgreSQL, Neo4j, Redis
- Google API key for Gemini
- JWT configuration (secret, algorithm, expiry)
- File upload limits and allowed types
- Debug mode and logging level

Critical settings validation occurs on startup. Missing `GOOGLE_API_KEY` triggers a warning.

## Database Connections

**PostgreSQL:**
- Host: `localhost` (local) or `postgres` (Docker)
- Port: 5432
- Default credentials: `graphtog_user` / `graphtog_password`
- Database: `graphtog_db`
- Uses pgvector extension for embeddings

**Neo4j:**
- URI: `bolt://localhost:7687` (local) or `bolt://neo4j:7687` (Docker)
- Browser UI: http://localhost:7474
- Default credentials: `neo4j` / `graphtog_password`
- Enterprise edition with APOC and GDS plugins

**Redis:**
- Host: `localhost` (local) or `redis` (Docker)
- Port: 6379
- Used for caching query results and embeddings

## Common Development Patterns

### Adding a New API Endpoint

1. Create router function in appropriate file under `app/api/endpoints/`
2. Use dependency injection for database sessions: `db: Session = Depends(get_db)`
3. Use `get_current_user` dependency for authenticated endpoints
4. Define Pydantic schemas for request/response in `app/schemas/`
5. Include router in `app/main.py` with appropriate prefix

### Working with Neo4j Graph

1. Get session via `graph_service.get_session()`
2. Use parameterized Cypher queries to prevent injection
3. Wrap operations in try-except for error handling
4. Return boolean success flags from service methods
5. Log errors with descriptive messages

### LLM Operations

1. All LLM calls go through `LLMService` class methods
2. Use prompt templates from `prompt.py` - don't hardcode prompts
3. Handle rate limiting automatically via `_apply_rate_limit()`
4. Parse responses with `_parse_json_response()` for JSON output
5. Implement retry logic for transient failures

### Testing Best Practices

1. Use pytest fixtures from `conftest.py` (`client`, `db`, `auth_token`, `authenticated_client`)
2. Mark tests with appropriate markers (`@pytest.mark.integration`, etc.)
3. Tests require running Docker services (PostgreSQL, Neo4j, Redis)
4. Use `TestClient` for API testing without starting server
5. Database transactions roll back after each test

## Important Notes

- **uv Package Manager**: This project uses `uv` instead of `pip` for faster dependency management
- **API Key Required**: Set `GOOGLE_API_KEY` environment variable for LLM functionality
- **Docker First**: Always start Docker services before running backend locally
- **Path Handling**: Backend uses relative paths from `backend/` directory
- **Token Expiry**: Default token expiry is 24 hours (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **File Upload**: Only MD files supported, max 50MB (configurable via `MAX_UPLOAD_SIZE`)
- **Neo4j License**: Using Neo4j Enterprise with eval license (set `NEO4J_ACCEPT_LICENSE_AGREEMENT=eval`)

## Troubleshooting

**Port conflicts**: If port 8000, 3000, 5432, 7687, or 6379 is in use, modify `docker-compose.yml` or use different port in uvicorn command

**Database connection errors**: Verify Docker services are running (`docker-compose ps`) and check logs (`docker-compose logs postgres/neo4j/redis`)

**Module import errors**: Ensure Python path includes backend directory or run uvicorn as module: `python -m uvicorn app.main:app --reload`

**Google API errors**: Verify `GOOGLE_API_KEY` is set correctly and has Gemini API enabled

**Test database issues**: Tests use same database as development. Ensure PostgreSQL is accessible at configured URL.
