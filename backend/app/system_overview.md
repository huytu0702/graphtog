# GraphToG System Overview

## Mission
GraphToG converts collections of Markdown documents into an explorable knowledge graph and answers complex user questions through Tree of Graphs (ToG) reasoning. The platform fuses structured graph traversal, LLM-guided pruning, and evidence-backed answer generation.

## End-to-End Workflow
1. **Document ingestion** – Markdown documents are uploaded through the frontend, stored as metadata in PostgreSQL, and persisted as raw files.
2. **Text processing** – The backend chunks documents, extracts entities and relationships with Google Gemini 2.5 Flash, and loads them into Neo4j.
3. **Reasoning** – Users issue questions that trigger ToG multi-hop exploration, guided by configurable pruning strategies and sufficiency checks.
4. **Answer delivery** – The system synthesizes reasoning paths, supporting evidence, and confidence scores for the frontend to display.

## Platform Composition
- **Frontend**: Next.js 15 with shadcn/ui, Tailwind CSS, Zustand, and NextAuth.js. The primary UI is `tog-query-interface.tsx`, which surfaces configuration controls, reasoning visualization, and responses.
- **Backend**: FastAPI application under `app/` with layered modules: API routers, service layer, data access, and schemas. uv handles Python dependency management.
- **Graph Store**: Neo4j Enterprise (with APOC & GDS) stores knowledge graph nodes (`Document`, `TextUnit`, `Entity`, `Community`) and relationships (`CONTAINS`, `MENTIONS`, `RELATED_TO`, `BELONGS_TO`, `PART_OF`). Optimized indexes aid ToG traversal.
- **Relational Store**: PostgreSQL (with pgvector) stores accounts, document metadata, query history, and embeddings.
- **Caching**: Redis accelerates repeated ToG queries and embedding lookups.
- **LLM Integration**: `LLMService` centralizes Gemini requests, enforces rate limiting, retries, and prompt usage (`prompt.py`).

## Backend Structure
- **API Layer (`app/api/endpoints/`)**: FastAPI routers for auth, document handling, ToG operations, community analytics, visualization, cache, and administrative actions.
- **Services (`app/services/`)**:
  - `document_processor.py` – Markdown parsing, chunking, and enrichment
  - `graph_service.py` – Neo4j session management, schema initialization, Cypher helpers
  - `tog_service.py` – Orchestrates ToG exploration, sufficiency checks, and answer synthesis
  - `llm_service.py` – Gemini API interactions, structured response parsing, prompt templating
  - `pruning_methods.py` – Factory for LLM, BM25, and SentenceBERT pruning strategies
  - Additional helpers for visualization, analytics, caching, security, embeddings, and prompts
- **Database Layer (`app/db/`)**: Connection factories for PostgreSQL (`postgres.py`) and Neo4j (`neo4j.py`).
- **ORM Models (`app/models/`)**: SQLAlchemy models for users, documents, queries, embeddings.
- **Schemas (`app/schemas/`)**: Pydantic definitions for payload validation and response typing.
- **Configuration (`app/config.py`)**: Loads environment settings (database URIs, API keys, JWT secrets, limits) with validation on startup.

## Tree of Graphs Reasoning
1. **Topic entity extraction** – Gemini identifies seed entities from the query and fuzzy-matches them against Neo4j.
2. **Iterative exploration** – The system traverses up to `search_depth` levels, each time scoring relations (`search_width`) and entities (`num_retain_entity`) via the configured pruning method.
3. **Sufficiency assessment** – Optional checks determine if enough evidence exists to halt exploration early.
4. **Answer generation** – Gemini composes an answer referencing the reasoning path and retrieved triplets, returning a confidence score and sufficiency status.

Configuration knobs (defaults in parentheses):
- `search_width` (3), `search_depth` (3)
- `num_retain_entity` (5)
- `pruning_method` (`llm`, with `bm25` and `sentence_bert` alternatives)
- `enable_sufficiency_check` (true)
- `exploration_temp` (0.4), `reasoning_temp` (0.0)

## Operations & Tooling
- **Service management**: `docker-compose up -d` starts PostgreSQL, Neo4j, and Redis locally.
- **Backend development**:
  - `uv venv` / `uv sync` for environment setup
  - `uv run uvicorn app.main:app --reload` for local server
- **Frontend development**:
  - `npm install`, `npm run dev` for live reload
- **Testing**: `uv run pytest` (with markers `integration`, `unit`, `benchmark`, `slow`, `auth`, `crud`); `uv run pytest --cov=app --cov-report=html` for coverage; parallel runs with `-n auto`.
- **Quality gates**: `uv run black`, `uv run ruff check`, and `uv run mypy`.

## Data & Authentication Flow
- Users register/login via FastAPI endpoints or NextAuth; passwords hashed with bcrypt.
- JWT access tokens (24 h default) protect authenticated routes using `get_current_user`.
- Uploaded Markdown is validated (max 50 MB), chunked, and linked to graph entities for ToG consumption.

## Testing Practices
- Pytest fixtures in `conftest.py` provide FastAPI client instances, database sessions, and auth tokens.
- ToG integration tests mock LLM responses for deterministic reasoning paths.
- Database transactions roll back per test to keep environments clean.

## Deployment Considerations
- Docker Compose orchestrates local services; production deployments reuse the same stack.
- Ensure `GOOGLE_API_KEY`, database URLs, and `NEO4J_ACCEPT_LICENSE_AGREEMENT=eval` are set.
- Monitor for port conflicts (8000, 3000, 5432, 7687, 6379) and adjust compose or server configs as needed.

## Troubleshooting Notes
- **Database connectivity**: Verify Docker services with `docker-compose ps` and inspect logs.
- **LLM failures**: Check Gemini API key and rate limits; retries are handled automatically but escalate persistent failures.
- **ToG gaps**: If queries return no entities, confirm documents exist in Neo4j (`MATCH (e:Entity) RETURN count(e)`).
- **Performance tuning**: Prefer BM25 or SentenceBERT pruning when latency is critical; disable sufficiency checks for exhaustive exploration.

