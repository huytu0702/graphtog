# Phase 1.2 & Phase 2 Implementation Plan - Advanced GraphRAG & ToG Integration

**Document Date**: October 26, 2025  
**Status**: Ready for Approval  
**Architecture**: GraphRAG-based with Tree of Graphs (ToG) Reasoning

---

## 📋 Executive Summary

This comprehensive plan outlines the implementation of Phase 1.2 (Knowledge Graph & Basic Q&A) and Phase 2 (Advanced GraphRAG Features) using Microsoft's GraphRAG methodology. The implementation will:

1. **Phase 1.2**: Build core GraphRAG functionality including entity/relationship extraction, knowledge graph construction, and basic Q&A
2. **Phase 2**: Add advanced features including community detection (Leiden algorithm), hierarchical retrieval, and graph visualization

---

## Phase 1.2: Knowledge Graph & Basic Q&A

### Overview
Build the fundamental GraphRAG pipeline that transforms documents into a queryable knowledge graph using Gemini 2.5 Flash for entity extraction.

### Phase 1.2.1: Entity & Relationship Extraction Service

#### Objective
Implement LLM-powered entity and relationship extraction using Gemini 2.5 Flash following Microsoft GraphRAG extraction patterns.

#### Implementation Steps

1. **Enhance LLM Service** (`backend/app/services/llm_service.py`)
   - Create extraction prompts based on GraphRAG templates
   - Implement entity extraction with types: PERSON, ORGANIZATION, LOCATION, CONCEPT, EVENT
   - Extract relationships with types: RELATED_TO, MENTIONS, CAUSES, PRECEDES, OPPOSES, SUPPORTS
   - Add batch processing with rate limiting
   - Implement retry logic for API failures
   - Add token counting to handle long documents

2. **Extraction Prompt Template**
   ```
   Extract entities and relationships from the following text chunk.
   
   Return JSON with this structure:
   {
     "entities": [
       {
         "name": "string",
         "type": "PERSON|ORGANIZATION|LOCATION|CONCEPT|EVENT",
         "description": "brief description",
         "aliases": ["alternative names"]
       }
     ],
     "relationships": [
       {
         "source": "entity name",
         "target": "entity name",
         "type": "RELATED_TO|MENTIONS|CAUSES|PRECEDES|OPPOSES|SUPPORTS",
         "description": "brief description of relationship"
       }
     ]
   }
   
   Text: {chunk}
   ```

3. **Text Chunking Strategy**
   - Semantic chunking with overlap (50% overlap for context)
   - Chunk size: 1000-1500 tokens
   - Preserve paragraph boundaries
   - Track chunk IDs for traceability

4. **Batch Processing**
   - Process document chunks in parallel (max 5 concurrent)
   - Rate limit: 60 requests per minute for Gemini API
   - Queue failed chunks for retry with exponential backoff
   - Log extraction metrics (chunks processed, entities found, relationships)

#### Deliverables
- [ ] Enhanced `llm_service.py` with extraction functions
- [ ] Extraction prompt templates
- [ ] Batch processing queue
- [ ] Error handling and retry logic

---

### Phase 1.2.2: Neo4j Graph Service Implementation

#### Objective
Create service layer for graph operations following GraphRAG schema patterns.

#### Implementation Steps

1. **Graph Schema Setup** (`backend/app/services/graph_service.py`)
   - Create constraints and indexes:
     ```cypher
     CREATE CONSTRAINT entity_id IF NOT EXISTS 
     FOR (e:Entity) REQUIRE e.id IS UNIQUE;
     
     CREATE CONSTRAINT document_id IF NOT EXISTS 
     FOR (d:Document) REQUIRE d.id IS UNIQUE;
     
     CREATE INDEX entity_name IF NOT EXISTS 
     FOR (e:Entity) ON (e.name);
     
     CREATE INDEX entity_type IF NOT EXISTS 
     FOR (e:Entity) ON (e.type);
     ```

2. **Node Types (Following Microsoft GraphRAG)**
   - **Document**: Source document metadata
     - Properties: id, name, file_path, size, processed_at, user_id
   - **TextUnit** (Chunk): Text chunks with preservation of structure
     - Properties: id, text, document_id, chunk_index
   - **Entity**: Extracted entities
     - Properties: id, name, type, description, aliases
   - **Community** (Phase 2): Hierarchical communities
     - Properties: id, level, title

3. **Relationship Types**
   - `(Document)-[:CONTAINS]->(TextUnit)`: Document contains chunks
   - `(TextUnit)-[:MENTIONS]->(Entity)`: Chunk mentions entity
   - `(Entity)-[:RELATED_TO]->(Entity)`: Entity-entity relationships
   - `(Entity)-[:IN_COMMUNITY]->(Community)`: Entity membership (Phase 2)

4. **Graph Population Functions**
   ```python
   async def create_document_node(document_id, filename, file_path)
   async def create_text_unit_nodes(document_id, chunks)
   async def create_entity_nodes(entities)
   async def create_relationships(relationships)
   async def upsert_entities(entities)  # Merge duplicates
   ```

5. **Entity Deduplication**
   - Implement similarity matching for duplicate detection
   - Use entity name + type for matching
   - Merge related entities with weighted connections

#### Deliverables
- [ ] `graph_service.py` with graph operations
- [ ] Neo4j schema constraints and indexes
- [ ] Entity upsert logic with deduplication
- [ ] Transaction management for reliability

---

### Phase 1.2.3: Document Processing Pipeline

#### Objective
Integrate document parsing, chunking, and graph construction into cohesive workflow.

#### Implementation Steps

1. **Document Processing Flow**
   ```
   Document Upload
         ↓
   Parse Markdown (.md)
         ↓
   Chunk Text (semantic)
         ↓
   Extract Entities & Relationships (Gemini)
         ↓
   Create Text Unit Nodes
         ↓
   Upsert Entities & Relationships
         ↓
   Build Graph Structure
         ↓
   Generate Summary
         ↓
   Mark Document as Processed
   ```

2. **Processing Service** (`backend/app/services/document_processor.py`)
   - Enhanced `process_document()` function
   - State management (pending → processing → completed/failed)
   - Progress tracking for long-running operations
   - Error recovery and partial completion handling

3. **Background Task Management**
   - Use FastAPI BackgroundTasks for async processing
   - Implement document status updates
   - Add webhooks/polling for frontend status
   - Store processing logs in PostgreSQL

4. **Validation**
   - Validate extracted entities (non-empty names, valid types)
   - Check relationship validity (source/target exist)
   - Ensure graph consistency before commit
   - Log validation errors for debugging

#### Deliverables
- [ ] Enhanced document processing pipeline
- [ ] Status tracking in database
- [ ] Progress indicators for uploads
- [ ] Error logging and recovery

---

### Phase 1.2.4: Basic Q&A Implementation

#### Objective
Implement simple question-answering using graph retrieval and Gemini.

#### Implementation Steps

1. **Query Processing Flow**
   ```
   User Query
         ↓
   Extract Query Entities (Gemini)
         ↓
   Find Matching Entities in Graph
         ↓
   Get Related Context (1-hop relationships)
         ↓
   Retrieve Source Text Chunks
         ↓
   Generate Answer with Context (Gemini)
         ↓
   Return Answer + Citations
   ```

2. **Query Endpoint** (`backend/app/api/endpoints/queries.py`)
   - `POST /api/queries` - Submit query
   - `GET /api/queries/{id}` - Get query result
   - `GET /api/queries?document_id=...` - Filter by document

3. **Query Entity Extraction**
   ```python
   async def extract_query_entities(query: str) -> List[Entity]:
       # Use Gemini to identify key entities in query
       # Return: [Entity(name, type)]
   ```

4. **Graph Traversal & Context Retrieval**
   ```cypher
   # Find relevant entities and their context
   MATCH (q:Entity {name: $entity_name})
   MATCH (q)-[rel]-(connected:Entity)
   MATCH (chunk:TextUnit)-[:MENTIONS]->(q)
   RETURN q, connected, rel, chunk
   LIMIT 20
   ```

5. **Answer Generation**
   ```
   Prompt:
   Based on the following context from a knowledge graph,
   answer this question: {query}
   
   Context:
   - Main entities: {entities}
   - Related connections: {relationships}
   - Source text: {chunks}
   
   Provide a comprehensive answer with proper citations.
   ```

6. **Citation Tracking**
   - Include source document and chunk ID in response
   - Show which entities/relationships contributed to answer
   - Enable source highlighting in UI

#### Deliverables
- [ ] Query extraction and processing service
- [ ] Graph traversal queries
- [ ] Answer generation with Gemini
- [ ] Citation tracking and formatting
- [ ] Query endpoints and responses

---

### Phase 1.2.5: Testing Dashboard

#### Objective
Create admin interface to verify Phase 1.2 functionality.

#### Implementation Steps

1. **Testing Endpoints**
   - `GET /api/admin/stats` - Graph statistics (documents, entities, relationships)
   - `GET /api/admin/graph/sample` - Sample entity relationships
   - `GET /api/admin/documents/{id}/processing` - Document processing details

2. **Frontend Testing Page** (`frontend/app/(dashboard)/test/page.tsx`)
   - Graph statistics display
   - Document processing status
   - Sample query execution
   - Sample entity relationships visualization

#### Deliverables
- [ ] Admin statistics endpoints
- [ ] Basic testing UI
- [ ] Processing verification

---

## Phase 2: Advanced GraphRAG Features

### Overview
Enhance system with hierarchical community detection, multi-level retrieval, advanced extraction, and visualization tools.

### Phase 2.1: Community Detection (Leiden Algorithm)

#### Objective
Implement hierarchical community detection using Neo4j GDS Leiden algorithm following Microsoft GraphRAG approach.

#### Implementation Steps

1. **Neo4j GDS Setup**
   - Install Neo4j Graph Data Science library
   - Enable GDS plugins in Neo4j
   - Create graph projection for entity relationships

2. **Leiden Algorithm Implementation**
   ```cypher
   // Create graph projection
   CALL gds.graph.project(
     'entity-graph',
     'Entity',
     'RELATED_TO'
   )
   
   // Run Leiden algorithm with multiple resolution parameters
   CALL gds.leiden.write('entity-graph', {
     writeProperty: 'community',
     includeIntermediateCommunities: true,
     relationshipWeightProperty: 'weight'
   })
   YIELD communityCount, modularity
   ```

3. **Hierarchical Community Structure**
   - Run Leiden at multiple resolution levels
   - Level 0: Fine-grained communities (many small groups)
   - Level 1: Intermediate communities
   - Level 2: Broad thematic clusters
   - Store community hierarchy in database

4. **Community Indexing**
   ```sql
   CREATE TABLE communities (
     id UUID PRIMARY KEY,
     graph_id UUID REFERENCES documents(id),
     community_id INT,
     level INT,
     parent_community_id INT,
     entity_count INT,
     relationship_count INT,
     created_at TIMESTAMP
   );
   ```

#### Deliverables
- [ ] Neo4j GDS integration
- [ ] Leiden algorithm implementation
- [ ] Hierarchical community structure
- [ ] Community indexing

---

### Phase 2.2: Community Summarization

#### Objective
Generate semantic summaries for each community using Gemini.

#### Implementation Steps

1. **Community Summary Generation**
   - For each community, collect:
     - All entities in community
     - All relationships within community
     - Connection strength metrics
     - Representative text chunks

2. **Summary Prompt Template**
   ```
   Summarize the following group of related entities and connections:
   
   Entities:
   {entity_list}
   
   Key Relationships:
   {relationship_list}
   
   Representative Text:
   {text_chunks}
   
   Provide:
   1. Brief summary of community theme
   2. Key entities and their roles
   3. Important relationships
   4. Main insights about this cluster
   ```

3. **Summary Storage**
   ```sql
   CREATE TABLE community_summaries (
     id UUID PRIMARY KEY,
     community_id UUID REFERENCES communities(id),
     summary TEXT,
     key_themes TEXT[],
     entity_count INT,
     generated_at TIMESTAMP
   );
   ```

4. **Multi-level Summaries**
   - Generate summaries at each community level
   - Use lower-level summaries as context for higher levels
   - Build hierarchical understanding

#### Deliverables
- [ ] Community summary service
- [ ] Summary generation with Gemini
- [ ] Hierarchical summary storage
- [ ] Summary caching

---

### Phase 2.3: Multi-level Retrieval Strategy

#### Objective
Implement three-tier retrieval combining local, community, and global searches.

#### Implementation Steps

1. **Retrieval Architecture**
   ```
   Query
     ↓
   ├─→ Local Retrieval (Entity-specific)
   │   - Find exact matching entities
   │   - Get 1-2 hop relationships
   │   - Retrieve nearby text chunks
   │
   ├─→ Community Retrieval (Theme-specific)
   │   - Identify relevant communities
   │   - Get community summaries
   │   - Retrieve community members
   │
   └─→ Global Retrieval (Context-wide)
       - Get broad thematic overview
       - Find cross-community patterns
       - Identify global connections
   ```

2. **Local Retrieval Service**
   ```python
   async def local_search(query: str, entity_name: str) -> Dict:
       # Find entity
       # Get immediate neighbors (1-2 hops)
       # Get related text chunks
       # Return contextualized results
   ```

3. **Community Retrieval Service**
   ```python
   async def community_search(query: str) -> Dict:
       # Extract query type and keywords
       # Find relevant communities using similarity
       # Get community summaries
       # Retrieve top entities from communities
       # Return hierarchical context
   ```

4. **Adaptive Selection**
   - Simple queries → Local retrieval
   - Analytical queries → Community retrieval  
   - Exploratory queries → Multi-level retrieval
   - Classify query type with Gemini

#### Deliverables
- [ ] Multi-level retrieval services
- [ ] Query classification
- [ ] Adaptive retrieval selection
- [ ] Result ranking and scoring

---

### Phase 2.4: Advanced Entity & Relationship Extraction

#### Objective
Enhance extraction with better prompts, co-reference resolution, and refinement loops.

#### Implementation Steps

1. **Improved Extraction Prompts**
   - Add few-shot examples to prompts
   - Include domain-specific entity types
   - Add confidence scoring
   - Extract temporal relationships

2. **Co-reference Resolution**
   - Identify entity mentions and references
   - Link pronouns to entities
   - Handle abbreviations and aliases
   - Build entity name variations

3. **Relationship Refinement**
   - Extract temporal aspects (before/after)
   - Capture relationship strength (weak/strong)
   - Identify relationship confidence
   - Extract supporting evidence

4. **Extraction Quality Metrics**
   - Entity coverage: % of concepts mentioned
   - Relationship completeness: relationships per entity
   - Accuracy validation through consistency checks
   - Manual review flagging for uncertain extractions

#### Deliverables
- [ ] Enhanced extraction prompts
- [ ] Co-reference resolution
- [ ] Relationship refinement
- [ ] Quality metrics

---

### Phase 2.5: Enhanced Q&A with Community-based Retrieval

#### Objective
Upgrade Q&A system to leverage community context and multi-perspective answers.

#### Implementation Steps

1. **Enhanced Query Processing**
   ```
   Query
     ↓
   Classify Query Type (Gemini)
   - Factual: "What is X?"
   - Analytical: "Why does X happen?"
   - Exploratory: "How are X and Y related?"
     ↓
   Select Retrieval Strategy
     ↓
   Retrieve Multi-level Context
   - Local: specific entities
   - Community: thematic context
   - Global: broad perspective
     ↓
   Generate Answer with Multiple Perspectives
     ↓
   Rank and Combine Perspectives
     ↓
   Return Comprehensive Answer + Confidence Score
   ```

2. **Multi-perspective Answer Generation**
   ```
   For each relevant community:
   - Generate answer from community perspective
   - Include community summary
   - Highlight key entities
   - Note community relationships to query topic
   
   Combine perspectives:
   - Identify consensus points
   - Flag conflicting information
   - Provide balanced view
   - Suggest additional exploration
   ```

3. **Answer Quality Metrics**
   - Confidence score (0-1)
   - Evidence coverage
   - Source count
   - Conflict resolution
   - Explanation of reasoning

4. **Citation Enhancement**
   - Track which communities contributed
   - Show retrieval path visualization
   - Include source entity chains
   - Link to specific text evidence

#### Deliverables
- [ ] Query classification service
- [ ] Multi-perspective answer generation
- [ ] Answer quality scoring
- [ ] Enhanced citation tracking

---

### Phase 2.6: Graph Visualization

#### Objective
Create tools for debugging and understanding graph structure and retrieval.

#### Implementation Steps

1. **Graph Visualization Endpoints**
   - `GET /api/graph/entity/{name}` - Entity and connections
   - `GET /api/graph/community/{id}` - Community structure
   - `GET /api/graph/query/{id}` - Query retrieval path
   - `GET /api/graph/export` - Full graph export

2. **Frontend Visualization Component**
   - Use Cytoscape.js or D3.js
   - Display nodes (entities, communities)
   - Show relationships with labels
   - Color by entity type or community
   - Interactive exploration (zoom, filter)
   - Click to expand related nodes

3. **Query Path Visualization**
   - Show which entities were retrieved
   - Display retrieval path from query to answer
   - Highlight communities involved
   - Show ranking/scoring
   - Indicate confidence levels

4. **Debugging Views**
   - Entity detail panel
   - Relationship browser
   - Community composition
   - Extraction statistics
   - Query performance metrics

#### Deliverables
- [ ] Graph visualization endpoints
- [ ] Cytoscape/D3 frontend component
- [ ] Query path visualization
- [ ] Debugging dashboard

---

### Phase 2.7: Performance Optimization

#### Objective
Optimize database queries, caching, and system throughput.

#### Implementation Steps

1. **Redis Caching Layer**
   - Cache entity lookups (TTL: 24 hours)
   - Cache community summaries (TTL: 7 days)
   - Cache query results (TTL: 1 hour)
   - Cache entity embeddings (TTL: 30 days)
   - Implement cache invalidation on updates

2. **Neo4j Optimization**
   - Create indexes on frequently queried properties
   - Optimize Cypher query plans
   - Use query parameters (prevent injection)
   - Implement connection pooling
   - Monitor slow queries

3. **PostgreSQL Optimization**
   - Index on (user_id, created_at) for queries
   - Index on (document_id, status) for filtering
   - Implement query pagination
   - Archive old queries
   - Monitor slow queries

4. **API Optimization**
   - Async processing for all I/O operations
   - Request batching for multiple queries
   - Streaming responses for large datasets
   - Rate limiting per user (100 req/min)
   - Response compression

5. **Monitoring & Metrics**
   - Track API response times
   - Monitor database query performance
   - Cache hit rates
   - Processing pipeline metrics
   - Error rates by component

#### Deliverables
- [ ] Redis caching implementation
- [ ] Database query optimization
- [ ] Performance monitoring
- [ ] Rate limiting

---

## Implementation Timeline & Task Breakdown

### Phase 1.2 Timeline: 4-5 weeks

| Week | Tasks | Estimated Hours |
|------|-------|-----------------|
| 1 | LLM Service enhancement + entity extraction | 20 |
| 2 | Graph service + schema setup | 18 |
| 2-3 | Document processing integration | 16 |
| 3 | Q&A implementation + retrieval | 20 |
| 4 | Testing dashboard + refinement | 12 |
| 4-5 | Testing & bug fixes | 14 |
| **Total** | | **100 hours** |

### Phase 2 Timeline: 5-6 weeks

| Week | Tasks | Estimated Hours |
|------|-------|-----------------|
| 1 | Community detection setup | 16 |
| 2 | Community summarization | 14 |
| 2-3 | Multi-level retrieval | 20 |
| 3-4 | Advanced extraction improvements | 16 |
| 4 | Enhanced Q&A system | 18 |
| 4-5 | Graph visualization | 18 |
| 5-6 | Performance optimization + testing | 20 |
| **Total** | | **122 hours** |

---

## Technology Stack & Dependencies

### Python Packages (Backend)
```toml
# Core dependencies (already installed)
fastapi = "^0.104"
uvicorn = "^0.24"
sqlalchemy = "^2.0"
neo4j = "^5.14"
google-generativeai = "^0.3.0"

# New dependencies for Phase 1.2 & 2
pandas = "^2.0"          # Data processing
numpy = "^1.24"          # Numerical operations
networkx = "^3.2"        # Graph analysis
lancedb = "^0.3"         # Vector store (GraphRAG style)
redis = "^5.0"           # Caching
pydantic-settings = "^2.0"  # Config management
```

### Frontend Packages
```json
{
  "cytoscape": "^3.28",
  "cytoscape-fcose": "^2.2",
  "cytoscape-cose-bilkent": "^4.1",
  "d3": "^7.8",
  "react-d3-library": "^1.0"
}
```

---

## Microsoft GraphRAG Best Practices Applied

✅ **Indexing Pipeline**: Multi-stage processing (chunking → extraction → graph building)
✅ **Hierarchical Communities**: Leiden algorithm with multiple resolution levels
✅ **Multi-level Retrieval**: Local, community, and global search strategies
✅ **Entity Deduplication**: Similarity matching and merging
✅ **Vector Embeddings**: Preparation for Phase 3 (vector search)
✅ **Community Summarization**: LLM-generated semantic summaries
✅ **Structured Extraction**: JSON-based entity and relationship extraction
✅ **Query Classification**: Adaptive retrieval based on query type
✅ **Citation Tracking**: Source attribution and evidence linking

---

## Success Criteria

### Phase 1.2 Completion
- [ ] Successfully extract entities and relationships from 100+ test documents
- [ ] Build knowledge graphs with 1000+ entities and relationships
- [ ] Answer 80%+ of test queries accurately with proper sources
- [ ] Document processing completes in < 2 min per 10K tokens
- [ ] Q&A response times < 3 seconds

### Phase 2 Completion
- [ ] Detect communities with modularity > 0.5
- [ ] Generate meaningful community summaries
- [ ] Multi-level retrieval returns relevant context 90%+ of time
- [ ] Handle 100+ concurrent queries
- [ ] Graph visualization loads in < 2 seconds
- [ ] 95%+ cache hit rate on popular queries

---

## Next Steps for Approval

1. **Review** this implementation plan
2. **Approve** resource allocation (100 + 122 = 222 developer hours)
3. **Confirm** Gemini API quotas and costs
4. **Start Phase 1.2** implementation
5. **Set up** Redis instance and Neo4j GDS
6. **Create** development branch for Phase work

---

**Document Prepared By**: AI Assistant  
**Ready For**: User Approval & Implementation Start  
**Last Updated**: October 26, 2025
