# GraphRAG Implementation - Tasks & Improvements

Danh sách các tasks để áp dụng hoàn chỉnh GraphRAG methodology theo chuẩn Microsoft.

**Trạng thái hiện tại: 9.0/10** - Core implementation hoàn chỉnh, cần thêm advanced features và optimization.

---

## 🔴 Priority 1: Critical (High Impact)

### 1.1 Prompt Tuning cho Domain-Specific Data
**Tầm quan trọng:** ⭐⭐⭐⭐⭐ (Microsoft khuyến nghị mạnh mẽ)

- [ ] Chạy prompt tuning trên sample documents để generate domain-specific prompts
- [ ] Tạo custom entity types phù hợp với domain của project
  - Ví dụ: TECHNOLOGY, CONCEPT, ALGORITHM, DATASET, MODEL, LIBRARY, API
- [ ] Custom relationship types cho domain
  - Ví dụ: IMPLEMENTS, USES, DEPENDS_ON, EXTENDS
- [ ] Tạo prompt variants trong `backend/app/services/prompt.py`
- [ ] A/B test giữa default prompts và custom prompts
- [ ] Đo lường improvement: entity precision, relationship accuracy
- [ ] Document best practices trong `docs/prompt-tuning.md`

**Files cần modify:**
- `backend/app/services/prompt.py` - Thêm custom prompt variants
- `backend/app/config.py` - Add config cho prompt selection
- `backend/app/services/llm_service.py` - Support multiple prompt templates

**References:**
- https://microsoft.github.io/graphrag/posts/prompt_tuning/
- https://microsoft.github.io/graphrag/posts/config/init/

---

### 1.2 Monitoring & Observability
**Tầm quan trọng:** ⭐⭐⭐⭐⭐

- [ ] Add logging cho tất cả LLM calls (latency, tokens, cost)
- [ ] Track extraction quality metrics:
  - Entity extraction success rate
  - Relationship extraction success rate
  - Community detection quality (modularity score)
- [ ] Query performance monitoring:
  - Query latency by type (local/global/hybrid)
  - Cache hit rate
  - Context retrieval quality
- [ ] Dashboard với Grafana/Prometheus hoặc tích hợp vào admin panel
- [ ] Alert khi extraction quality giảm

**Files cần tạo:**
- `backend/app/services/monitoring.py` - Metrics collection
- `backend/app/services/metrics.py` - Quality metrics calculation
- `backend/app/middleware/logging.py` - Request/response logging

---

### 1.3 Error Handling & Resilience
**Tầm quan trọng:** ⭐⭐⭐⭐

- [ ] Graceful degradation khi LLM API fails
  - Fallback to cached results
  - Partial results instead of complete failure
- [ ] Better error messages cho users
- [ ] Retry logic với exponential backoff cho transient failures (đã có, cần improve)
- [ ] Circuit breaker pattern cho LLM service
- [ ] Dead letter queue cho failed extraction jobs
- [ ] Recovery mechanism cho incomplete document processing

**Files cần modify:**
- `backend/app/services/llm_service.py` - Circuit breaker, better retry
- `backend/app/services/document_processor.py` - Recovery logic
- `backend/app/api/endpoints/*.py` - Better error responses

---

## 🟠 Priority 2: Important (Medium Impact)

### 2.1 Map-Reduce Global Search
**Tầm quan trọng:** ⭐⭐⭐⭐

- [x] Implement Map-Reduce pattern cho global query processing
  - Map phase: Chia communities thành batches, summarize từng batch
  - Reduce phase: Combine intermediate summaries thành final answer
- [x] Configurable batch size (default: 10 communities/batch)
- [x] Parallel processing cho Map phase
- [x] Compare performance vs current concatenation approach
- [x] Add config option để switch giữa Map-Reduce và simple concatenation

**Implementation outline:**
```python
# backend/app/services/query_service.py
async def process_global_query_with_mapreduce(
    query: str,
    batch_size: int = 10
):
    # 1. Retrieve all communities
    communities = await retrieval_service.retrieve_global_context()

    # 2. Map: Batch processing
    batches = chunk_list(communities, batch_size)
    intermediate_summaries = []

    for batch in batches:
        batch_summary = await llm_service.summarize_community_batch(
            query, batch
        )
        intermediate_summaries.append(batch_summary)

    # 3. Reduce: Final synthesis
    final_answer = await llm_service.synthesize_final_answer(
        query, intermediate_summaries
    )

    return final_answer
```

**Files cần modify:**
- `backend/app/services/query_service.py` - Add Map-Reduce method
- `backend/app/services/llm_service.py` - Add batch summarization
- `backend/app/services/prompt.py` - Add Map-Reduce prompts
- `backend/app/config.py` - Add config options

**References:**
- https://microsoft.github.io/graphrag/posts/query/global_search/

---

### 2.2 Claims Extraction & Storage
**Tầm quan trọng:** ⭐⭐⭐

- [x] Integrate claims extraction vào document processing pipeline
- [x] Extend Neo4j schema với Claim nodes
  - Properties: subject, object, claim_type, status, description, date_range
- [x] Store claims với relationships:
  - `Entity -[:MAKES_CLAIM]-> Claim`
  - `Claim -[:ABOUT]-> Entity`
  - `Claim -[:SOURCED_FROM]-> TextUnit`
- [x] Query service support cho claim-based queries
- [x] UI để display claims trong document analysis
- [x] Claim verification workflow (optional)

**Neo4j Schema Extension:**
```cypher
CREATE CONSTRAINT claim_id IF NOT EXISTS
FOR (c:Claim) REQUIRE c.id IS UNIQUE;

CREATE INDEX claim_type IF NOT EXISTS
FOR (c:Claim) ON (c.claim_type);

CREATE INDEX claim_status IF NOT EXISTS
FOR (c:Claim) ON (c.status);
```

**Files cần modify:**
- `backend/app/services/document_processor.py` - Add claims extraction step
- `backend/app/services/llm_service.py` - Add `extract_claims()` method
- `backend/app/services/graph_service.py` - Add claims storage methods
- `backend/app/models/claim.py` - NEW: Claim model
- `backend/app/schemas/claim.py` - NEW: Claim schemas

**References:**
- Prompt template đã có: `backend/app/services/prompt.py:158-209`

---

### 2.3 DRIFT Search Implementation
**Tầm quan trọng:** ⭐⭐⭐

- [ ] Implement DRIFT (Dynamic Reasoning with Inference over Text) search
- [ ] DRIFT = Local search + Community context enrichment
- [ ] Add to query routing logic
- [ ] Performance comparison với pure local search

**Implementation outline:**
```python
# backend/app/services/retrieval_service.py
async def retrieve_drift_context(
    query_entity: str,
    hop_limit: int = 2,
    include_community_summaries: bool = True
) -> Dict:
    # 1. Local context retrieval
    local_results = await retrieve_local_context(
        query_entity, hop_limit, include_text=True
    )

    # 2. Community context enrichment
    if include_community_summaries:
        community_context = await retrieve_community_context(
            query_entity, include_summaries=True
        )

        # Merge contexts
        enriched_context = merge_local_and_community(
            local_results, community_context
        )
        return enriched_context

    return local_results
```

**Files cần modify:**
- `backend/app/services/retrieval_service.py` - Add DRIFT methods
- `backend/app/services/query_service.py` - Add DRIFT query processing
- `backend/app/api/endpoints/queries.py` - Add DRIFT endpoint

**References:**
- https://microsoft.github.io/graphrag/posts/query/drift_search/

---

### 2.4 Entity Resolution & Disambiguation
**Tầm quan trọng:** ⭐⭐⭐⭐

- [ ] Improve entity deduplication beyond MD5 hash
- [ ] Fuzzy matching cho entity names (Levenshtein distance)
- [ ] LLM-based entity resolution cho ambiguous cases
- [ ] Merge duplicate entities sau khi detection
- [ ] Entity alias tracking (e.g., "Microsoft" = "MS" = "MSFT")

**Implementation:**
```python
# backend/app/services/entity_resolution.py - NEW FILE
class EntityResolutionService:
    def find_similar_entities(
        self,
        entity_name: str,
        entity_type: str,
        threshold: float = 0.85
    ):
        # Fuzzy matching logic
        pass

    def merge_duplicate_entities(
        self,
        entity_ids: List[str]
    ):
        # Merge logic with mention_count aggregation
        pass

    async def resolve_with_llm(
        self,
        entity1: Dict,
        entity2: Dict
    ) -> bool:
        # LLM-based resolution for edge cases
        pass
```

**Files cần tạo:**
- `backend/app/services/entity_resolution.py` - NEW
- `backend/app/api/endpoints/admin.py` - Add entity merge endpoints

---

### 2.5 Incremental Indexing ✅ COMPLETED
**Tầm quan trọng:** ⭐⭐⭐⭐

- [x] Support incremental document updates (không phải reindex toàn bộ)
- [x] Track document versions trong PostgreSQL
- [x] Update existing entities thay vì recreate
- [x] Incremental community detection (chỉ recompute affected communities)
- [x] Efficient graph updates

**Implementation Details:**
- Added version tracking fields to Document model (version, content_hash, last_processed_at)
- Implemented SHA256-based change detection to skip unchanged documents
- Created `process_document_incrementally()` for efficient updates
- Added `get_affected_communities_for_document()` and `delete_document_graph_data()` to graph service
- Implemented `detect_communities_incrementally()` for subgraph-only community detection
- Added API endpoints: PUT /documents/{id}/update, POST /documents/{id}/reprocess
- Comprehensive test suite with 20+ tests including integration and performance benchmarks

**Files modified:**
- ✅ `backend/app/models/document.py` - Added version, content_hash, last_processed_at fields
- ✅ `backend/app/schemas/document.py` - Updated DocumentResponse schema
- ✅ `backend/app/services/document_processor.py` - Incremental processing logic
- ✅ `backend/app/services/graph_service.py` - Update operations and cleanup methods
- ✅ `backend/app/services/community_detection.py` - Incremental detection
- ✅ `backend/app/api/endpoints/documents.py` - Update and reprocess endpoints
- ✅ `backend/tests/test_incremental_indexing.py` - Comprehensive test suite

**Documentation:** See `INCREMENTAL_INDEXING.md` for usage guide

**Completed:** 2025-10-30

---

### 3.3 Query Optimization & Caching
**Tầm quan trọng:** ⭐⭐⭐⭐

- [ ] Semantic query caching (similar queries → cached results)
- [ ] Embedding-based query similarity
- [ ] Cache warming cho popular queries
- [ ] Query result ranking improvement
- [ ] Relevance feedback loop

**Files cần modify:**
- `backend/app/services/cache_service.py` - Semantic caching
- `backend/app/services/embedding_service.py` - Query embeddings
- `backend/app/services/query_service.py` - Cache integration

---

### 3.4 Batch Document Processing
**Tầm quan trọng:** ⭐⭐⭐

- [ ] Bulk upload interface (multiple files)
- [ ] Background job queue (Celery/RQ)
- [ ] Progress tracking cho long-running jobs
- [ ] Parallel document processing
- [ ] Batch status dashboard

**Files cần tạo:**
- `backend/app/workers/` - Background workers
- `backend/app/services/job_queue.py` - Queue management
- `frontend/components/batch-upload/` - Bulk upload UI

---

### 3.5 Graph Analytics & Insights
**Tầm quan trọng:** ⭐⭐

- [ ] Centrality metrics (PageRank, Betweenness, Closeness)
- [ ] Entity importance scoring
- [ ] Knowledge gap detection (sparse areas in graph)
- [ ] Relationship pattern mining
- [ ] Temporal analysis (entity evolution over time)

**Implementation:**
```python
# backend/app/services/graph_analytics.py - NEW FILE
class GraphAnalyticsService:
    def calculate_centrality(self):
        # Use Neo4j GDS algorithms
        pass

    def detect_knowledge_gaps(self):
        # Find under-connected entities
        pass

    def mine_relationship_patterns(self):
        # Frequent pattern mining
        pass
```

---

### 3.6 Export & Integration
**Tầm quan trọng:** ⭐⭐

- [ ] Export knowledge graph (GraphML, GEXF, JSON)
- [ ] Export community reports (PDF, DOCX)
- [ ] REST API cho external integrations
- [ ] Webhook support cho events (document processed, etc.)
- [ ] Integration với tools khác (Obsidian, Notion, etc.)

**Files cần tạo:**
- `backend/app/services/export_service.py` - Export logic
- `backend/app/api/endpoints/export.py` - Export endpoints

---

### 3.7 Testing & Quality Assurance
**Tầm quan trọng:** ⭐⭐⭐⭐⭐

- [ ] Expand test coverage to 80%+
- [ ] Integration tests cho full pipeline
- [ ] Performance benchmarks
- [ ] Load testing (concurrent users, large documents)
- [ ] Extraction quality regression tests
- [ ] End-to-end tests cho query flows

**Files cần tạo:**
- `backend/tests/integration/test_full_pipeline.py`
- `backend/tests/performance/test_benchmarks.py`
- `backend/tests/quality/test_extraction_quality.py`

---

### 3.8 Documentation Improvements
**Tầm quan trọng:** ⭐⭐⭐

- [ ] API documentation với examples
- [ ] Architecture diagrams
- [ ] Deployment guide
- [ ] Troubleshooting guide
- [ ] Performance tuning guide
- [ ] Video tutorials

**Files cần tạo:**
- `docs/api/README.md`
- `docs/architecture/diagrams/`
- `docs/deployment/production.md`
- `docs/guides/troubleshooting.md`

---

## 📊 Implementation Roadmap

### Phase 1: Stability & Observability (2-3 weeks)
- Priority 1.2: Monitoring & Observability
- Priority 1.3: Error Handling & Resilience
- Priority 3.7: Testing expansion

### Phase 2: Core Enhancements (3-4 weeks)
- Priority 1.1: Prompt Tuning
- Priority 2.1: Map-Reduce Global Search
- Priority 2.4: Entity Resolution
- Priority 2.5: Incremental Indexing

### Phase 3: Advanced Features (4-6 weeks)
- Priority 2.2: Claims Extraction
- Priority 2.3: DRIFT Search
- Priority 3.2: Advanced Visualization
- Priority 3.3: Query Optimization

### Phase 4: Optimization & Scale (2-3 weeks)
- Priority 3.4: Batch Processing
- Priority 3.5: Graph Analytics
- Priority 3.6: Export & Integration

---

## 🎯 Success Metrics

### Extraction Quality
- Entity precision/recall > 85%
- Relationship accuracy > 80%
- Community modularity > 0.4

### Performance
- Document processing: < 2 min per 10K tokens
- Local query: < 3s response time
- Global query: < 10s response time
- Cache hit rate: > 60%

### User Experience
- Query satisfaction score: > 4/5
- System uptime: > 99.5%
- Error rate: < 1%

---

## 📚 References

### Microsoft GraphRAG Documentation
- Main docs: https://microsoft.github.io/graphrag/
- Prompt tuning: https://microsoft.github.io/graphrag/posts/prompt_tuning/
- Query methods: https://microsoft.github.io/graphrag/posts/query/overview/
- Configuration: https://microsoft.github.io/graphrag/posts/config/overview/

### Neo4j Resources
- GDS Library: https://neo4j.com/docs/graph-data-science/current/
- Leiden Algorithm: https://neo4j.com/docs/graph-data-science/current/algorithms/leiden/
- Performance tuning: https://neo4j.com/docs/operations-manual/current/performance/

### Research Papers
- Graph Retrieval-Augmented Generation: https://arxiv.org/abs/2404.16130
- Leiden Algorithm: https://www.nature.com/articles/s41598-019-41695-z

---

## 💡 Notes

- Tất cả tasks nên có unit tests và documentation
- Performance impact phải được đo lường trước và sau optimization
- Breaking changes cần migration scripts
- User-facing features cần user testing trước khi deploy

**Last updated:** 2025-10-30
