# Phase 1.2 & Phase 2 Implementation Checklist

**Status**: 🟡 Ready for Approval  
**Start Date**: Pending User Approval  
**Expected Completion**: ~9-11 weeks after start

---

## Phase 1.2: Knowledge Graph & Basic Q&A

### Week 1: Entity & Relationship Extraction Service

#### LLM Service Enhancement
- [ ] Create extraction prompt templates in `llm_service.py`
- [ ] Implement `extract_entities()` function
  - [ ] Support entity types: PERSON, ORGANIZATION, LOCATION, CONCEPT, EVENT
  - [ ] Return structured JSON format
  - [ ] Add confidence scoring
- [ ] Implement `extract_relationships()` function
  - [ ] Support relationship types: RELATED_TO, MENTIONS, CAUSES, PRECEDES, OPPOSES, SUPPORTS
  - [ ] Link source/target entities
  - [ ] Extract descriptions
- [ ] Implement `batch_extract()` function
  - [ ] Process multiple chunks concurrently (max 5)
  - [ ] Rate limiting (60 req/min)
  - [ ] Progress tracking
- [ ] Add error handling and retry logic
  - [ ] Exponential backoff for failed chunks
  - [ ] Max retry attempts (3)
  - [ ] Failure logging
- [ ] Add token counting utilities
  - [ ] Estimate tokens before API call
  - [ ] Split large texts appropriately

#### Text Chunking Strategy
- [ ] Implement semantic chunking
  - [ ] Chunk size: 1000-1500 tokens
  - [ ] 50% overlap between chunks
  - [ ] Preserve paragraph boundaries
- [ ] Add chunk ID tracking
  - [ ] Link chunks to source document
  - [ ] Track chunk index
- [ ] Create chunking validation
  - [ ] Verify chunk size limits
  - [ ] Check overlap implementation

#### Batch Processing Queue
- [ ] Create task queue structure
- [ ] Implement chunk processing queue
- [ ] Add queue monitoring
- [ ] Create queue persistence (database)

**Testing**:
- [ ] Unit tests for extraction functions
- [ ] Integration test: document → chunks → extraction
- [ ] Test with sample markdown documents

**Time Estimate**: 18-20 hours

---

### Week 2: Neo4j Graph Service Implementation

#### Graph Schema Setup
- [ ] Create constraints in `graph_service.py`
  - [ ] `CREATE CONSTRAINT entity_id FOR (e:Entity)`
  - [ ] `CREATE CONSTRAINT document_id FOR (d:Document)`
- [ ] Create indexes
  - [ ] `CREATE INDEX entity_name FOR (e:Entity) ON (e.name)`
  - [ ] `CREATE INDEX entity_type FOR (e:Entity) ON (e.type)`
  - [ ] `CREATE INDEX text_unit_document FOR (t:TextUnit) ON (t.document_id)`
- [ ] Define node properties
  - [ ] Document: id, name, file_path, size, processed_at
  - [ ] TextUnit: id, text, document_id, chunk_index
  - [ ] Entity: id, name, type, description, aliases
- [ ] Define relationship properties
  - [ ] CONTAINS: timestamp
  - [ ] MENTIONS: strength
  - [ ] RELATED_TO: weight, description

#### Graph Population Functions
- [ ] Implement `create_document_node()`
- [ ] Implement `create_text_unit_nodes()`
- [ ] Implement `create_entity_nodes()`
- [ ] Implement `create_relationships()`
- [ ] Implement `upsert_entities()`
  - [ ] Similarity matching for duplicates
  - [ ] Entity merging
  - [ ] Relationship consolidation

#### Entity Deduplication
- [ ] Implement similarity matching algorithm
- [ ] Create `find_duplicate_entities()` function
- [ ] Create `merge_entities()` function
- [ ] Track merge history

#### Transaction Management
- [ ] Implement transaction handling
- [ ] Add rollback logic
- [ ] Error recovery

**Testing**:
- [ ] Unit tests for graph operations
- [ ] Integration test: create nodes → create relationships
- [ ] Verify schema constraints

**Time Estimate**: 16-18 hours

---

### Week 2-3: Document Processing Integration

#### Enhanced Pipeline
- [ ] Update `document_processor.py`
  - [ ] Add chunking step
  - [ ] Add extraction step
  - [ ] Add graph building step
- [ ] Implement processing flow
  - [ ] Parse → Chunk → Extract → Build Graph → Store
- [ ] Add progress tracking
  - [ ] Track current step
  - [ ] Track progress percentage
- [ ] Implement error handling
  - [ ] Partial completion
  - [ ] Rollback on failure
  - [ ] Retry logic

#### Status Management
- [ ] Add document status column to PostgreSQL
  - [ ] pending → processing → completed/failed
- [ ] Implement status update mechanism
- [ ] Add progress polling endpoint

#### Background Tasks
- [ ] Setup FastAPI BackgroundTasks
- [ ] Create async task wrapper
- [ ] Implement task monitoring
- [ ] Add task logging

#### Validation
- [ ] Validate extracted entities
  - [ ] Non-empty names
  - [ ] Valid types
  - [ ] Description present
- [ ] Validate relationships
  - [ ] Source/target exist
  - [ ] Valid relationship type
- [ ] Add validation error logging

**Testing**:
- [ ] End-to-end: upload → parse → extract → graph
- [ ] Error cases: invalid file, extraction failure
- [ ] Status tracking verification

**Time Estimate**: 14-16 hours

---

### Week 3: Basic Q&A System

#### Query Service
- [ ] Create `query_service.py`
- [ ] Implement `extract_query_entities()`
  - [ ] Use Gemini to identify entities in query
  - [ ] Return entity names and types
- [ ] Implement `retrieve_context()`
  - [ ] Find entities in Neo4j
  - [ ] Get 1-2 hop relationships
  - [ ] Retrieve related text chunks
- [ ] Implement `generate_answer()`
  - [ ] Build context prompt
  - [ ] Call Gemini with context
  - [ ] Return structured answer

#### Graph Traversal
- [ ] Write Cypher queries
  - [ ] Find entity by name
  - [ ] Get related entities (1-hop)
  - [ ] Get related entities (2-hop)
  - [ ] Get text chunks mentioning entity
- [ ] Implement query execution
- [ ] Add result ranking/sorting

#### Answer Generation
- [ ] Create answer prompt template
- [ ] Implement context formatting
- [ ] Add citation extraction
- [ ] Implement confidence scoring

#### Citation Tracking
- [ ] Link answers to source documents
- [ ] Track contributing entities/relationships
- [ ] Create citation formatting
- [ ] Frontend citation display integration

#### Query Endpoints
- [ ] Create `POST /api/queries` endpoint
  - [ ] Accept query text
  - [ ] Accept optional document_id filter
  - [ ] Return query_id for async retrieval
- [ ] Create `GET /api/queries/{id}` endpoint
  - [ ] Return query result
  - [ ] Include context data
  - [ ] Include citations
- [ ] Create `GET /api/queries?document_id=...` endpoint
  - [ ] Filter by document
  - [ ] Pagination support

**Testing**:
- [ ] Test entity extraction
- [ ] Test context retrieval
- [ ] Test answer generation
- [ ] Test citation accuracy
- [ ] End-to-end Q&A flow

**Time Estimate**: 18-20 hours

---

### Week 4: Testing Dashboard & Refinement

#### Backend Endpoints
- [ ] Create `/api/admin/stats` endpoint
  - [ ] Return total documents
  - [ ] Return total entities
  - [ ] Return total relationships
  - [ ] Return processing statistics
- [ ] Create `/api/admin/graph/sample` endpoint
  - [ ] Return sample entities
  - [ ] Return sample relationships
- [ ] Create `/api/admin/documents/{id}/processing` endpoint
  - [ ] Return processing status
  - [ ] Return extraction metrics

#### Frontend Testing Page
- [ ] Create `frontend/app/(dashboard)/test/page.tsx`
- [ ] Display graph statistics
- [ ] Display document list with status
- [ ] Implement sample query interface
- [ ] Show sample entity relationships

#### Testing & Refinement
- [ ] Functional testing
  - [ ] Test extraction quality (100+ documents)
  - [ ] Test graph building (1000+ entities)
  - [ ] Test Q&A accuracy (80%+ target)
- [ ] Performance testing
  - [ ] Processing time per document
  - [ ] Q&A response time
  - [ ] Memory usage
- [ ] Bug fixes and optimization
- [ ] Documentation updates

**Time Estimate**: 10-12 hours

---

### Phase 1.2 Summary
- **Total Duration**: 4-5 weeks
- **Total Hours**: 100 hours
- **Deliverables**:
  - ✓ Entity & relationship extraction service
  - ✓ Neo4j graph service
  - ✓ Document processing pipeline
  - ✓ Basic Q&A system
  - ✓ Testing dashboard

---

## Phase 2: Advanced GraphRAG Features

### Week 1: Community Detection (Leiden Algorithm)

#### Neo4j GDS Setup
- [ ] Install Neo4j Graph Data Science library
- [ ] Enable GDS in Neo4j configuration
- [ ] Verify GDS permissions
- [ ] Create GDS usage documentation

#### Leiden Implementation
- [ ] Create graph projection
  - [ ] Project entity nodes
  - [ ] Project RELATED_TO relationships
  - [ ] Include relationship weights
- [ ] Implement Leiden algorithm
  - [ ] Set resolution level for fine-grained communities
  - [ ] Set resolution level for intermediate communities
  - [ ] Set resolution level for broad communities
  - [ ] Calculate modularity metrics
- [ ] Store community assignments
  - [ ] Update entity community property
  - [ ] Create community hierarchy

#### Hierarchical Structure
- [ ] Design community hierarchy schema
  - [ ] Community ID
  - [ ] Level (0, 1, 2)
  - [ ] Parent community ID
  - [ ] Entity count
  - [ ] Relationship count
- [ ] Create community hierarchy table in PostgreSQL
- [ ] Implement community tree structure
- [ ] Add community traversal functions

#### Community Indexing
- [ ] Create PostgreSQL communities table
- [ ] Create Neo4j community nodes
- [ ] Link entities to communities
- [ ] Add performance indexes

**Testing**:
- [ ] Verify Leiden algorithm results
- [ ] Check modularity scores (target > 0.5)
- [ ] Validate community hierarchy
- [ ] Test community traversal

**Time Estimate**: 14-16 hours

---

### Week 2: Community Summarization

#### Community Data Collection
- [ ] Implement `collect_community_data()` function
  - [ ] Get all entities in community
  - [ ] Get all relationships in community
  - [ ] Calculate connection metrics
  - [ ] Retrieve representative text chunks

#### Summary Generation
- [ ] Create summary prompt template
- [ ] Implement `generate_community_summary()` function
  - [ ] Format community data for Gemini
  - [ ] Generate summary with Gemini
  - [ ] Extract key themes
  - [ ] Return structured summary
- [ ] Add summary quality scoring

#### Summary Storage
- [ ] Create community_summaries table in PostgreSQL
  - [ ] community_id
  - [ ] summary text
  - [ ] key_themes (array)
  - [ ] entity_count
  - [ ] generated_at
- [ ] Implement summary retrieval
- [ ] Add summary update logic

#### Hierarchical Summaries
- [ ] Generate summaries for Level 0 communities
- [ ] Generate summaries for Level 1 communities
  - [ ] Use Level 0 summaries as context
- [ ] Generate summaries for Level 2 communities
  - [ ] Use Level 1 summaries as context
- [ ] Implement hierarchical summary traversal

#### Caching
- [ ] Setup Redis caching for summaries
- [ ] Set TTL (7 days)
- [ ] Implement cache invalidation
- [ ] Monitor cache hit rates

**Testing**:
- [ ] Generate summaries for test communities
- [ ] Verify summary quality
- [ ] Check hierarchy building
- [ ] Test cache performance

**Time Estimate**: 12-14 hours

---

### Week 2-3: Multi-level Retrieval Strategy

#### Query Classification
- [ ] Create query classifier
  - [ ] Factual queries: "What is X?"
  - [ ] Analytical queries: "Why does X happen?"
  - [ ] Exploratory queries: "How are X and Y related?"
- [ ] Implement `classify_query()` function

#### Local Retrieval Service
- [ ] Implement `local_search()` function
  - [ ] Find exact entity matches
  - [ ] Get 1-hop relationships
  - [ ] Get 2-hop relationships
  - [ ] Retrieve related text chunks
- [ ] Add ranking/scoring logic
- [ ] Optimize for performance

#### Community Retrieval Service
- [ ] Implement `community_search()` function
  - [ ] Identify relevant communities
  - [ ] Get community summaries
  - [ ] Get top entities from communities
  - [ ] Calculate community relevance
- [ ] Add multi-level community traversal
- [ ] Implement community ranking

#### Global Retrieval Service
- [ ] Implement `global_search()` function
  - [ ] Get broad thematic overview
  - [ ] Find cross-community patterns
  - [ ] Identify global connections
  - [ ] Aggregate insights

#### Adaptive Selection
- [ ] Implement query type → retrieval strategy mapping
  - [ ] Simple → Local
  - [ ] Analytical → Community
  - [ ] Exploratory → Multi-level
- [ ] Create hybrid retrieval for complex queries
- [ ] Add parameter tuning

#### Ranking & Scoring
- [ ] Implement relevance scoring
- [ ] Implement confidence scoring
- [ ] Implement source diversity scoring
- [ ] Create score aggregation

**Testing**:
- [ ] Test local retrieval accuracy
- [ ] Test community retrieval quality
- [ ] Test global retrieval coverage
- [ ] Test adaptive selection
- [ ] Performance benchmarks

**Time Estimate**: 18-20 hours

---

### Week 3-4: Advanced Extraction Improvements

#### Enhanced Prompts
- [ ] Add few-shot examples to extraction prompts
- [ ] Create domain-specific entity type templates
- [ ] Add confidence scoring to extraction
- [ ] Implement temporal relationship extraction

#### Co-reference Resolution
- [ ] Implement entity mention detection
- [ ] Implement pronoun resolution
- [ ] Handle abbreviations and aliases
- [ ] Create entity name variation mapping

#### Relationship Refinement
- [ ] Extract temporal aspects (before/after)
- [ ] Capture relationship strength
- [ ] Add relationship confidence scoring
- [ ] Extract supporting evidence for relationships

#### Extraction Quality Metrics
- [ ] Implement entity coverage metric
- [ ] Implement relationship completeness metric
- [ ] Add extraction consistency checks
- [ ] Create quality scoring function
- [ ] Flag uncertain extractions for review

#### Extraction Refinement Loop
- [ ] Implement validation step
  - [ ] Check entity existence in graph
  - [ ] Verify relationship validity
- [ ] Implement merge/consolidation logic
- [ ] Create duplicate detection across documents
- [ ] Implement iterative refinement

**Testing**:
- [ ] Test improved extraction quality
- [ ] Test co-reference resolution
- [ ] Verify quality metrics
- [ ] Test refinement loop effectiveness

**Time Estimate**: 14-16 hours

---

### Week 4: Enhanced Q&A System

#### Query Classification Service
- [ ] Create advanced query classifier
- [ ] Implement topic extraction
- [ ] Implement intent detection
- [ ] Add query complexity scoring

#### Multi-perspective Answer Generation
- [ ] For each relevant community:
  - [ ] Generate community-specific answer
  - [ ] Include community summary
  - [ ] Highlight key entities
  - [ ] Note relationships to query
- [ ] Implement perspective combination
  - [ ] Identify consensus points
  - [ ] Flag conflicting information
  - [ ] Provide balanced view
  - [ ] Suggest additional exploration

#### Answer Quality Metrics
- [ ] Implement confidence scoring (0-1)
- [ ] Implement evidence coverage metric
- [ ] Implement source count metric
- [ ] Implement conflict resolution scoring
- [ ] Create explanation generation

#### Enhanced Citation System
- [ ] Track contributing communities
- [ ] Show retrieval path in answer
- [ ] Include source entity chains
- [ ] Link to specific text evidence
- [ ] Create citation visualization data

#### Query Endpoints Enhancement
- [ ] Update `POST /api/queries` with confidence/explanation
- [ ] Update `GET /api/queries/{id}` with multi-perspective data
- [ ] Add `/api/queries/{id}/context` endpoint
- [ ] Add `/api/queries/{id}/visualization` endpoint

**Testing**:
- [ ] Test query classification
- [ ] Test multi-perspective generation
- [ ] Verify answer quality scores
- [ ] Test citation accuracy
- [ ] End-to-end system test

**Time Estimate**: 16-18 hours

---

### Week 4-5: Graph Visualization Tools

#### Backend Visualization Endpoints
- [ ] Create `/api/graph/entity/{name}` endpoint
  - [ ] Return entity data
  - [ ] Return connected entities
  - [ ] Return relationships
- [ ] Create `/api/graph/community/{id}` endpoint
  - [ ] Return community data
  - [ ] Return member entities
  - [ ] Return community relationships
- [ ] Create `/api/graph/query/{id}` endpoint
  - [ ] Return query path
  - [ ] Return retrieved entities
  - [ ] Return retrieval scoring
- [ ] Create `/api/graph/export` endpoint
  - [ ] Export full graph data
  - [ ] Support multiple formats (JSON, Cypher)

#### Frontend Visualization Component
- [ ] Choose visualization library (Cytoscape.js or D3.js)
- [ ] Create graph node rendering
- [ ] Create relationship/edge rendering
- [ ] Implement node coloring by type/community
- [ ] Implement zoom and pan interactions
- [ ] Implement node/edge filtering
- [ ] Create interactive node expansion

#### Query Path Visualization
- [ ] Show query → entities retrieved → answer flow
- [ ] Highlight retrieval path
- [ ] Show communities involved
- [ ] Display scoring/ranking
- [ ] Show confidence levels
- [ ] Create step-by-step visualization

#### Debugging Dashboard
- [ ] Create entity detail panel
- [ ] Create relationship browser
- [ ] Create community composition view
- [ ] Display extraction statistics
- [ ] Display query performance metrics
- [ ] Create performance timeline

**Testing**:
- [ ] Test visualization endpoints
- [ ] Test component rendering
- [ ] Test interaction responsiveness
- [ ] Performance testing (large graphs)
- [ ] Verify visualization accuracy

**Time Estimate**: 16-18 hours

---

### Week 5-6: Performance Optimization

#### Redis Caching Layer
- [ ] Setup Redis connection
- [ ] Implement entity cache
  - [ ] TTL: 24 hours
  - [ ] Key: `entity:{entity_id}`
- [ ] Implement community summary cache
  - [ ] TTL: 7 days
  - [ ] Key: `summary:{community_id}:{level}`
- [ ] Implement query result cache
  - [ ] TTL: 1 hour
  - [ ] Key: `query:{query_hash}:{user_id}`
- [ ] Implement cache invalidation
  - [ ] On document update
  - [ ] On entity update
  - [ ] On community update
- [ ] Monitor cache hit rates

#### Neo4j Optimization
- [ ] Create performance indexes
  - [ ] Entity name index
  - [ ] Entity type index
  - [ ] Document reference index
- [ ] Optimize Cypher queries
  - [ ] Review slow queries
  - [ ] Add query hints
  - [ ] Profile queries
- [ ] Implement connection pooling
- [ ] Monitor query performance
- [ ] Setup query logging

#### PostgreSQL Optimization
- [ ] Create composite indexes
  - [ ] (user_id, created_at)
  - [ ] (document_id, status)
  - [ ] (community_id, level)
- [ ] Implement query pagination
- [ ] Archive old queries
  - [ ] Move queries > 90 days to archive
  - [ ] Setup archive cleanup
- [ ] Monitor slow queries

#### API Optimization
- [ ] Ensure all I/O operations are async
- [ ] Implement request batching
- [ ] Add streaming responses for large datasets
- [ ] Implement rate limiting (100 req/min per user)
- [ ] Add response compression (gzip)

#### Monitoring & Metrics
- [ ] Setup API response time tracking
- [ ] Setup database query performance tracking
- [ ] Track cache hit rates
- [ ] Track processing pipeline metrics
- [ ] Track error rates by component
- [ ] Create performance dashboard

**Testing**:
- [ ] Load testing (100+ concurrent queries)
- [ ] Performance benchmarking
- [ ] Cache hit rate verification
- [ ] Memory usage profiling
- [ ] Database query optimization verification

**Time Estimate**: 18-20 hours

---

### Phase 2 Summary
- **Total Duration**: 5-6 weeks
- **Total Hours**: 122 hours
- **Deliverables**:
  - ✓ Community detection (Leiden algorithm)
  - ✓ Community summarization
  - ✓ Multi-level retrieval
  - ✓ Advanced extraction
  - ✓ Enhanced Q&A
  - ✓ Graph visualization
  - ✓ Performance optimization

---

## Overall Summary

### Timeline
| Phase | Duration | Hours |
|-------|----------|-------|
| 1.2 | 4-5 weeks | 100h |
| 2 | 5-6 weeks | 122h |
| **Total** | **9-11 weeks** | **222h** |

### Success Criteria Checklist

#### Phase 1.2
- [ ] Extract entities from 100+ documents
- [ ] Build graphs with 1000+ entities/relationships
- [ ] Answer 80%+ of test queries accurately
- [ ] Processing time < 2 min per 10K tokens
- [ ] Q&A response time < 3 seconds

#### Phase 2
- [ ] Community modularity > 0.5
- [ ] Multi-level retrieval 90%+ accurate
- [ ] Handle 100+ concurrent queries
- [ ] Visualization load < 2 seconds
- [ ] Cache hit rate 95%+

---

## Next Steps

Upon approval:
1. [ ] Create feature branch
2. [ ] Set up Redis and Neo4j GDS
3. [ ] Install dependencies
4. [ ] Begin Phase 1.2 Week 1
5. [ ] Weekly progress updates

**Document Status**: Ready for Implementation  
**Last Updated**: October 26, 2025
