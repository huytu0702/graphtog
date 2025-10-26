# Phase 1 & 2 Implementation Plan: GraphRAG-based Document Processing System

## Architecture Overview

**Frontend**: Next.js 15 (App Router) + shadcn/ui + Tailwind CSS + NextAuth

**Backend**: FastAPI + Python 3.10+

**Databases**: PostgreSQL (user data) + Neo4j (knowledge graph)

**AI**: Google Gemini 2.5 Flash via Google AI SDK

**Document Processing**: Direct .md file loading

**Vector Search**: Neo4j Vector Index (Neo4j 5.11+)

## Phase 1: MVP Development with GraphRAG Foundation

### 1. Project Setup & Infrastructure

**Backend Setup**:

- Initialize FastAPI project with `uv` for fast Python package management:
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
  ├── pyproject.toml (uv project file)
  ├── uv.lock (uv lock file)
  ├── .python-version
  ├── Dockerfile
  └── docker-compose.yml
  ```

- Use `uv` for package management:
  - Initialize project: `uv init`
  - Add dependencies: `uv add <package>`
  - Sync environment: `uv sync`
  - Run scripts: `uv run <command>`

- Key Python dependencies (via uv): `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `psycopg2-binary`, `neo4j`, `google-generativeai`, `python-multipart`, `python-jose[cryptography]`, `passlib[bcrypt]`, `python-dotenv`

- System dependencies (install via Dockerfile):
  - No special system dependencies needed for .md file processing

- Dockerfile will use multi-stage build:
  - Stage 1: Install system dependencies and uv
  - Stage 2: Copy app and use `uv sync --frozen` for reproducible builds
  - Use `uv` to manage Python environment inside container

**Frontend Setup**:

- Initialize Next.js 15 project with App Router
- Install dependencies: `shadcn/ui`, `tailwindcss`, `next-auth`, `axios`, `zustand`
- Setup NextAuth with credentials provider
- Project structure:
  ```
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
  │   ├── ui/ (shadcn components)
  │   ├── document-upload.tsx
  │   └── query-interface.tsx
  └── lib/
      ├── api.ts
      └── store.ts
  ```


**Database Setup**:

- Create `docker-compose.yml` for PostgreSQL and Neo4j:
  - PostgreSQL: port 5432
  - Neo4j: port 7474 (HTTP), 7687 (Bolt)
- PostgreSQL schema:
  ```sql
  CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR UNIQUE NOT NULL,
    name VARCHAR,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
  );
  
  CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    filename VARCHAR NOT NULL,
    file_path VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'pending',
    file_size BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
  );
  
  CREATE TABLE queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    query_text TEXT NOT NULL,
    response TEXT,
    created_at TIMESTAMP DEFAULT NOW()
  );
  ```


### 2. Authentication System

**Backend**:

- Implement JWT token generation and validation
- Create API endpoints:
  - `POST /api/auth/register` - User registration
  - `POST /api/auth/token` - Token generation for NextAuth
  - `GET /api/auth/me` - Get current user

**Frontend**:

- Configure NextAuth with custom credentials provider
- Create login/register pages with shadcn forms
- Implement protected routes middleware
- Setup auth state management

### 3. Document Upload & Storage

**Backend**:

- Create document upload endpoint: `POST /api/documents/upload`
- Implement file validation (type, size limits: 50MB)
- Store files in local `uploads/` directory (structure: `uploads/{user_id}/{doc_id}/`)
- Support formats: MD files
- Save document metadata to PostgreSQL
- Background task queue for processing (use `BackgroundTasks` from FastAPI)

**Frontend**:

- Create drag-and-drop upload component using shadcn
- Show upload progress with progress bar
- Display document list with status indicators
- Real-time status updates using polling or WebSocket

### 4. Document Parsing & Entity Extraction

**Document Processor Service** (`document_processor.py`):

- Parse .md files directly to extract text content
- Extract text, preserve structure (headings, paragraphs, lists)
- Chunk text into semantic units (paragraphs/sections)

**Entity Extraction using Gemini**:

- Create `llm_service.py` with Gemini integration
- Implement prompt template for entity extraction:
  ```
  Extract entities from the following text. Return JSON format:
  {
    "entities": [
      {"name": "...", "type": "PERSON|ORGANIZATION|LOCATION|CONCEPT", "description": "..."}
    ],
    "relationships": [
      {"source": "entity1", "target": "entity2", "type": "RELATED_TO|MENTIONS|...", "description": "..."}
    ]
  }
  Text: {chunk}
  ```

- Process document in chunks to handle token limits
- Batch API calls with rate limiting

### 5. Knowledge Graph Construction

**Graph Service** (`graph_service.py`):

- Connect to Neo4j using `neo4j` Python driver
- Create graph schema with constraints and indexes:
  ```cypher
  CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE;
  CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE;
  CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name);
  CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type);
  ```


**Graph Population**:

- Create Document node with metadata
- Create Entity nodes from extracted entities
- Create Sentence/Paragraph nodes for text chunks
- Establish relationships:
  - `(Document)-[:CONTAINS]->(Entity)`
  - `(Document)-[:CONTAINS]->(Sentence)`
  - `(Sentence)-[:MENTIONS]->(Entity)`
  - `(Entity)-[:RELATED_TO]->(Entity)`
- Store embeddings for entities (optional for Phase 1, required for Phase 2)

**Indexing**:

- Create vector index for similarity search (Phase 2)
- Full-text search index on entity names and descriptions

### 6. Basic Q&A Interface

**Backend**:

- Create query endpoint: `POST /api/query`
- Implement simple graph retrieval:

  1. Extract key entities from query using Gemini
  2. Find matching entities in Neo4j
  3. Retrieve context (related entities, sentences, documents)
  4. Generate answer using Gemini with retrieved context
  5. Return answer with source citations

**Frontend**:

- Create chat-like Q&A interface with shadcn components
- Input field for queries
- Display answers with source document references
- Show loading states during processing

### 7. Basic Testing UI

**Testing Dashboard**:

- Simple admin page to view graph statistics
- Display: total documents, entities, relationships
- Basic graph visualization using Neo4j Browser iframe
- API health checks


---

## Phase 2: Advanced GraphRAG Features

### 1. Community Detection (Leiden Algorithm)

**Graph Analysis**:

- Implement **Leiden algorithm** for community detection (Microsoft GraphRAG standard)
- Use Neo4j Graph Data Science library:
  ```cypher
  // Install GDS plugin in Neo4j
  // Create graph projection
  CALL gds.graph.project(
    'entity-graph',
    'Entity',
    'RELATED_TO'
  )
  
  // Run Leiden algorithm
  CALL gds.leiden.write('entity-graph', {
    writeProperty: 'community',
    includeIntermediateCommunities: true
  })
  YIELD communityCount, modularity
  ```

- Identify hierarchical thematic clusters in knowledge graph
- Assign community IDs to entities with parent/child relationships
- Store community hierarchy (parent_community, level, children)

### 2. Community Summaries

**Summary Generation**:

- For each community, collect all entities and relationships
- Generate community summary using Gemini:
  ```
  Summarize the following group of related entities and their relationships:
  Entities: [list]
  Relationships: [list]
  
  Provide a concise summary describing the main theme and key information.
  ```

- Store summaries in Neo4j:
  ```cypher
  CREATE (c:Community {
    community_id: ...,
    summary: ...,
    entity_count: ...,
    created_at: datetime()
  })
  ```


### 3. Enhanced Retrieval Algorithms

**Multi-level Retrieval**:

- Implement hierarchical retrieval strategy:

  1. **Local retrieval**: Find entities directly related to query
  2. **Community retrieval**: Find relevant communities and their summaries
  3. **Global retrieval**: Search across all communities for broad context

**Graph Traversal**:

- Implement BFS/DFS for relationship exploration
- Create Cypher queries for multi-hop relationships:
  ```cypher
  MATCH path = (e1:Entity {name: $entity})-[*1..3]-(e2:Entity)
  WHERE e2.name CONTAINS $keyword
  RETURN path
  LIMIT 100
  ```


### 4. Advanced Entity & Relationship Extraction

**Improved Prompting**:

- Use few-shot examples for better extraction
- Extract more relationship types: CAUSES, PRECEDES, OPPOSES, SUPPORTS
- Co-reference resolution for entity mentions
- Temporal relationship extraction (before/after)

**Refinement Loop**:

- Validate extracted entities against existing graph
- Merge duplicate entities using similarity scoring
- Disambiguate entity references using context

### 5. Graph-based Q&A with Community Summaries

**Enhanced Query Processing**:

- Classify query type (factual, analytical, exploratory)
- Multi-stage retrieval:

  1. Identify relevant communities using query embedding
  2. Retrieve community summaries for context
  3. Drill down into specific entities within communities
  4. Gather supporting evidence from document sentences

- Generate comprehensive answer using:
  - Community summaries (broad context)
  - Entity relationships (specific connections)
  - Original text chunks (evidence)

**Answer Quality Improvements**:

- Confidence scoring based on evidence strength
- Multi-perspective answers from different communities
- Conflict detection and resolution
- Source attribution with specific document sections

### 6. Graph Visualization

**Debugging Tools**:

- Create API endpoint: `GET /api/graph/visualize?entity={name}`
- Return graph data in D3.js or Cytoscape.js format
- Frontend visualization component:
  - Show entity nodes and relationships
  - Highlight communities with colors
  - Interactive exploration (click to expand)
  - Filter by entity type or relationship type

**Query Path Visualization**:

- Show retrieval path for each query
- Highlight which entities and relationships were used
- Display relevance scores for each node

### 7. Performance Optimization

**Caching Layer**:

- Setup Redis for caching:
  - Frequently accessed entities
  - Community summaries
  - Recent query results
- Implement cache invalidation on document updates

**Database Optimization**:

- Neo4j indexes on frequently queried properties
- PostgreSQL indexes on user_id, created_at
- Connection pooling for both databases
- Query optimization for common patterns

**API Optimization**:

- Async processing for document uploads
- Batch processing for multiple documents
- Streaming responses for long-running queries
- Rate limiting per user

---

## Testing Strategy

**Phase 1 Testing**:

- Unit tests for document parsing
- Integration tests for graph creation
- End-to-end test: upload document → query → get answer
- Test with sample .md documents

**Phase 2 Testing**:

- Community detection accuracy
- Retrieval quality metrics (precision, recall)
- Answer quality evaluation
- Performance benchmarks (response time, throughput)

## Deployment

**Development Environment**:

- Docker Compose for local development
- Environment variables in `.env` file
- Hot reload for both frontend and backend

**Phase 1 Deliverables**:

- Working authentication system
- Document upload and processing of .md files
- Basic knowledge graph creation
- Simple Q&A functionality
- Minimal UI for testing

**Phase 2 Deliverables**:

- Community detection and summaries
- Advanced retrieval with multi-level search
- Enhanced Q&A with better context
- Graph visualization tools
- Performance optimizations