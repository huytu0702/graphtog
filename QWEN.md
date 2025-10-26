# GraphRAG and Tree of Graphs (ToG) Implementation - Project Documentation

## Project Overview

This is a knowledge graph-based document processing and Q&A system that implements Microsoft's GraphRAG methodology enhanced with Tree of Graphs (ToG) reasoning. The system allows users to upload documents, processes them through advanced AI techniques, and generates intelligent answers to user queries. It features a LangGraph agent that intelligently selects optimal retrieval strategies and provides transparent reasoning chains with LangSmith tracing.

### Key Technologies:
- **Frontend**: Next.js 15 (App Router) + shadcn/ui + Tailwind CSS + NextAuth
- **Backend**: FastAPI + Python 3.10+
- **Databases**: PostgreSQL (user data) + Neo4j (knowledge graph)
- **AI**: Google Gemini 2.5 Flash via Google AI SDK
- **Document Processing**: Unstructured library with PaddleOCR for enhanced document parsing
- **Architecture**: Containerized with Docker Compose

### Core Features:
- Document upload and processing (PDF, DOCX, TXT, PPTX, XLSX)
- Knowledge graph construction with entity and relationship extraction
- Advanced Q&A with GraphRAG and Tree of Graphs (ToG) reasoning
- Multi-level retrieval with community detection (Leiden algorithm)
- LangGraph agent for intelligent query routing
- LangSmith integration for comprehensive tracing
- Reasoning chain visualization and transparency

## Current Implementation Phase

The project is currently focused on implementing Phase 1 and Phase 2 features as outlined in the development plan:

### Phase 1 - MVP Development with GraphRAG Foundation:
- Basic user authentication system
- Document upload functionality with drag-and-drop UI
- Document parsing using Unstructured library with PaddleOCR
- Knowledge graph construction in Neo4j
- Basic Q&A functionality with simple graph retrieval
- Entity and relationship extraction using Gemini

### Phase 2 - Advanced GraphRAG Features:
- Community detection using Leiden algorithm via Neo4j GDS
- Community summaries generation with Gemini
- Enhanced multi-level retrieval with hierarchical search
- Advanced entity and relationship extraction
- Graph-based Q&A with community summaries
- Graph visualization tools
- Performance optimization with Redis caching

## Building and Running

### Prerequisites:
- Docker and Docker Compose
- Python 3.10+
- Node.js 18+
- uv (Python package manager)

### Development Setup:

1. **Initialize the project structure** (as outlined in docs):
   ```
   backend/
   ├── app/
   │   ├── main.py
   │   ├── config.py
   │   ├── api/
   │   │   ├── endpoints/
   │   │   │   ├── auth.py
   │   │   │   ├── documents.py
   │   │   │   └── queries.py
   │   ├── models/
   │   │   ├── user.py
   │   │   └── document.py
   │   ├── services/
   │   │   ├── document_processor.py
   │   │   ├── graph_service.py
   │   │   └── llm_service.py
   │   ├── db/
   │   │   ├── postgres.py
   │   │   └── neo4j.py
   │   └── schemas/
   ├── pyproject.toml
   ├── uv.lock
   ├── .python-version
   ├── Dockerfile
   └── docker-compose.yml

   frontend/
   ├── app/
   │   ├── (auth)/
   │   │   ├── login/page.tsx
   │   │   └── register/page.tsx
   │   ├── (dashboard)/
   │   │   ├── layout.tsx
   │   │   ├── documents/page.tsx
   │   │   └── query/page.tsx
   │   └── api/auth/[...nextauth]/route.ts
   ├── components/
   │   ├── ui/
   │   ├── document-upload.tsx
   │   └── query-interface.tsx
   └── lib/
       ├── api.ts
       └── store.ts
   ```

2. **Backend setup with uv**:
   ```bash
   cd backend
   uv init  # Initialize project
   uv add fastapi uvicorn[standard] sqlalchemy psycopg2-binary neo4j unstructured[pdf,docx,pptx] paddlepaddle paddleocr google-generativeai python-multipart python-jose[cryptography] passlib[bcrypt] Pillow python-dotenv
   uv sync  # Install dependencies
   uv run uvicorn app.main:app --reload  # Run development server
   ```

3. **Frontend setup**:
   ```bash
   cd frontend
   npm install next@latest react@latest react-dom@latest
   npm install shadcn/ui tailwindcss next-auth axios zustand
   npm run dev  # Run development server
   ```

4. **Start databases with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

### Environment Configuration:
Create a `.env` file with:
- Google Gemini API key
- Database connection strings
- OCR configuration: `OCR_AGENT=unstructured.partition.utils.ocr_models.paddle_ocr.OCRAgentPaddle`

## Development Conventions

### Coding Standards:
- Python: Follow PEP 8 guidelines with type hints
- TypeScript/React: Use functional components with hooks
- FastAPI: Follow the recommended project structure with separate modules for endpoints, models, services, and schemas
- Cypher: Use parameterized queries to prevent injection

### Testing Strategy:
- Unit tests for document parsing and entity extraction
- Integration tests for graph creation and retrieval
- End-to-end tests: document upload → processing → Q&A
- Performance benchmarks for ToG reasoning and response times

### Architecture Patterns:
- Service layer pattern for business logic separation
- Repository pattern for database operations
- DTOs for API requests/responses
- Dependency injection for service management
- Asynchronous processing for document uploads and processing

## Project Status

The project is currently in the early development phase with a focus on implementing the foundational GraphRAG features. The documentation in the `/docs` directory outlines the complete implementation plan across multiple phases, with Phase 1 and 2 being the immediate focus areas.

Key files in the repository:
- `docs/PRD.md` - Product requirements document detailing the complete vision
- `docs/phase1-2.md` - Implementation plan for phases 1 and 2
- `docs/tasks-phase12.md` - Task checklist for the current development phases
- `.cursor/plans/` - Implementation plan files

## Special Notes

### PaddleOCR Integration:
The project uses PaddleOCR for Vietnamese and English text and complex document layouts. The OCR agent is configured through the `OCR_AGENT` environment variable.

### LangGraph Agent:
The system will feature a LangGraph agent that automatically classifies question types and selects the most appropriate processing strategy:
- **GraphRAG Mode**: For comprehensive, holistic questions
- **ToG Mode**: For deep sequential reasoning questions 
- **Hybrid Mode**: For complex multi-tiered questions

### LangSmith Integration:
Full tracing capabilities are planned to provide transparency in the agent's decision-making process and enable debugging of the reasoning chains.

### Context7 MCP:
Use context7 MCP to get latest documents of any packages