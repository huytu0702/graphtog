# So Sánh Quy Trình Index Document: GraphToG vs Microsoft GraphRAG

**Ngày phân tích:** 2025-11-07
**Mục đích:** So sánh chi tiết quy trình xử lý và index document giữa hệ thống GraphToG (codebase hiện tại) và Microsoft GraphRAG

---

## Tổng Quan Kiến Trúc

### Microsoft GraphRAG
- **Mô hình:** Pipeline tuần tự với 7 phases chính
- **LLM:** Sử dụng LLM làm trung tâm cho extraction và summarization
- **Graph Database:** Không bắt buộc (có thể lưu dạng file)
- **Focus:** Hierarchical community-based reasoning cho global queries

### GraphToG
- **Mô hình:** Pipeline tích hợp với Neo4j + PostgreSQL
- **LLM:** Google Gemini 2.5 Flash
- **Graph Database:** Neo4j (bắt buộc) + PostgreSQL + Redis
- **Focus:** Tree of Graphs (ToG) multi-hop reasoning cho complex queries

---

## So Sánh Chi Tiết Từng Bước

### 1. Document Parsing & Loading

| Tiêu chí | Microsoft GraphRAG | GraphToG |
|---------|-------------------|----------|
| **Input format** | CSV, .txt files | Markdown (.md) files only |
| **Implementation** | Built-in document loaders | Custom `DocumentProcessor.parse_md()` |
| **File validation** | Multiple formats supported | Only `.md` extension validated |
| **Content hash** | ❌ Không có | ✅ SHA256 hash tracking (`compute_content_hash()`) |
| **Change detection** | ❌ Không có | ✅ Incremental update support (`detect_document_changes()`) |
| **Metadata storage** | File-based hoặc database | PostgreSQL (Document table) + Neo4j (Document node) |

**Đánh giá:**
- ✅ **GraphToG tốt hơn:** Có change detection và incremental update
- ✅ **GraphRAG linh hoạt hơn:** Hỗ trợ nhiều định dạng file
- ⚠️ **GraphToG hạn chế:** Chỉ hỗ trợ Markdown

---

### 2. Text Chunking (Text Segmentation)

| Tiêu chí | Microsoft GraphRAG | GraphToG |
|---------|-------------------|----------|
| **Chunk size** | 300 tokens (default, configurable) | 1000 tokens (default, configurable) |
| **Overlap** | ❌ Không có overlap | ✅ 500 tokens overlap (default) |
| **Tokenizer** | LLM-specific tokenizer | tiktoken (GPT-3.5-turbo encoding) |
| **Splitting strategy** | Token-based | Semantic-aware: paragraphs → sentences → tokens |
| **Min chunk size** | Không rõ | 100 tokens (configurable) |
| **Implementation** | `compose_text_units` verb | `ChunkingService.create_chunks()` |
| **Metadata tracking** | TextUnit với document links | TextUnit với start_char, end_char, document_id |

**Code snippet GraphToG:**
```python
# chunking_service.py
def create_chunks(self, text: str) -> List[Tuple[str, int, int]]:
    """Create chunks with overlap and semantic awareness"""
    # 1. Split by paragraphs first
    paragraphs = self.split_by_paragraphs(text)

    # 2. Accumulate until chunk_size reached
    # 3. Create overlap for context continuity
    # 4. If paragraph too large, split by sentences
```

**Đánh giá:**
- ✅ **GraphToG tốt hơn:**
  - Overlap giúp maintain context giữa các chunks
  - Semantic-aware splitting (paragraph-level)
  - Character position tracking cho retrieval
- ✅ **GraphRAG đơn giản hơn:** Chunk nhỏ hơn (300 tokens) có thể giảm cost LLM extraction
- ⚠️ **Trade-off:** GraphToG chunks lớn hơn → nhiều thông tin hơn nhưng LLM cost cao hơn

---

### 3. Entity Extraction

| Tiêu chí | Microsoft GraphRAG | GraphToG |
|---------|-------------------|----------|
| **Method** | LLM-based extraction | LLM-based (Gemini) + batch processing |
| **Entity attributes** | title, type, description | name, type, description, confidence |
| **Entity types** | User-configurable | PERSON, ORGANIZATION, LOCATION, CONCEPT, EVENT, PRODUCT, OTHER |
| **Batch processing** | ✅ (entity_extract verb) | ✅ `batch_extract_entities()` |
| **Coreference resolution** | ❌ Không có | ✅ `resolve_coreferences()` (advanced_extraction) |
| **Few-shot learning** | ✅ (prompt tuning) | ✅ `extract_with_few_shot()` |
| **Deduplication** | Merged in summarization phase | ✅ Immediate via `create_or_merge_entity()` |
| **Mention count tracking** | ❌ | ✅ Auto-increment on merge |

**Code snippet GraphToG:**
```python
# document_processor.py - Step 7
entity_results = await llm_service.batch_extract_entities(chunk_data)

for result in entity_results:
    if result["status"] == "success":
        for entity in result["entities"]:
            entity_id = graph_service.create_or_merge_entity(
                name=entity.get("name", ""),
                entity_type=entity.get("type", "OTHER"),
                description=entity.get("description", ""),
                confidence=entity.get("confidence", 0.8),
            )
```

**Đánh giá:**
- ✅ **GraphToG tốt hơn:**
  - Immediate deduplication via MERGE
  - Mention count tracking (hữu ích cho ToG ranking)
  - Confidence scoring
  - Coreference resolution support
- ✅ **GraphRAG:** Tách biệt extraction và summarization → có thể optimize riêng
- 🟰 **Tương đương:** Cả hai đều dùng LLM extraction với few-shot learning

---

### 4. Entity Resolution & Disambiguation

| Tiêu chí | Microsoft GraphRAG | GraphToG |
|---------|-------------------|----------|
| **Phase** | Phase 2b (Graph Extraction) | Step 7.5 (Optional, after extraction) |
| **Method** | LLM summarization of duplicate instances | Fuzzy matching + LLM resolution |
| **Fuzzy matching** | ❌ | ✅ SequenceMatcher (difflib) |
| **Similarity threshold** | N/A | 0.85 (default, configurable) |
| **LLM verification** | ✅ (summarization) | ✅ `resolve_with_llm()` (optional) |
| **Auto-merge threshold** | N/A | 0.95+ (high confidence) |
| **Merge strategy** | Consolidate descriptions | Transfer relationships + mention counts + aliases |
| **Alias tracking** | ❌ | ✅ Entity aliases stored |
| **Incremental** | ❌ | ✅ Can skip if disabled |

**Code snippet GraphToG:**
```python
# entity_resolution_service.py
def find_duplicate_entity_pairs(self, entity_type=None, threshold=0.85):
    """Find duplicate pairs using fuzzy matching"""
    similarity = self.calculate_similarity(entity1["name"], entity2["name"])
    if similarity >= threshold:
        duplicate_pairs.append((entity1, entity2, similarity))

async def resolve_with_llm(self, entity1, entity2):
    """Use LLM to verify if entities are the same"""
    # Prompt: "Are these names referring to the same entity?"
    # Returns: {are_same, confidence, reasoning, suggested_canonical_name}
```

**Đánh giá:**
- ✅ **GraphToG vượt trội:**
  - 3-stage resolution: fuzzy → LLM verification → merge
  - Configurable thresholds (similarity, auto-merge, LLM)
  - Alias tracking cho better retrieval
  - Optional (có thể disable để giảm cost)
  - Incremental (chỉ xử lý affected entities khi update)
- ⚠️ **GraphRAG đơn giản hơn:** Chỉ summarization, không có sophisticated merging
- 💡 **GraphToG approach phức tạp hơn nhưng accurate hơn** cho entity disambiguation

---

### 5. Relationship Extraction

| Tiêu chí | Microsoft GraphRAG | GraphToG |
|---------|-------------------|----------|
| **Method** | LLM extraction cùng với entities | LLM extraction (separate step) |
| **Relationship attributes** | source, target, description | source, target, type, description, confidence |
| **Relationship types** | Generic "RELATED_TO" | Typed relationships (WORKS_AT, LOCATED_IN, etc.) |
| **Batch processing** | ✅ | ✅ `batch_extract_relationships()` |
| **Confidence scoring** | ❌ | ✅ Confidence 0.0-1.0 |
| **Deduplication** | Merged in summarization | ✅ ON MATCH update highest confidence |
| **Graph storage** | Generic edge | Neo4j typed relationship |

**Code snippet GraphToG:**
```python
# document_processor.py - Step 8
rel_results = await llm_service.batch_extract_relationships(chunk_with_entities)

for result in rel_results:
    if result["status"] == "success":
        for relationship in result["relationships"]:
            graph_service.create_relationship(
                source_entity_id=source_entity["id"],
                target_entity_id=target_entity["id"],
                relationship_type=rel_type,  # WORKS_AT, LOCATED_IN, etc.
                description=relationship.get("description", ""),
                confidence=relationship.get("confidence", 0.8),
            )
```

**Đánh giá:**
- ✅ **GraphToG tốt hơn:**
  - Typed relationships → richer semantics
  - Confidence scoring → pruning cho ToG
  - Confidence-based deduplication
- ⚠️ **GraphRAG generic hơn:** RELATED_TO relationship with descriptions
- 💡 **Trade-off:**
  - GraphRAG: Đơn giản, LLM tự do generate descriptions
  - GraphToG: Structured types, tốt cho graph traversal và pruning

---

### 6. Claim Extraction (Covariate Extraction)

| Tiêu chí | Microsoft GraphRAG | GraphToG |
|---------|-------------------|----------|
| **Support** | ✅ Phase 2c (optional) | ✅ Step 8.5 (always run) |
| **Claim attributes** | subject, object, type, status, time-bounds | subject, object, claim_type, status, description, start_date, end_date, source_text |
| **Status values** | TRUE, FALSE, SUSPECTED | TRUE, FALSE, SUSPECTED |
| **Temporal support** | ✅ Time-bounds | ✅ start_date, end_date (ISO-8601) |
| **Source tracking** | ❌ | ✅ Linked to TextUnit (SOURCED_FROM) |
| **Entity linking** | ✅ | ✅ MAKES_CLAIM, ABOUT relationships |
| **Deduplication** | ❌ | ✅ MERGE by claim_id (md5 hash) |
| **Occurrence tracking** | ❌ | ✅ occurrence_count |

**Code snippet GraphToG:**
```python
# document_processor.py - Step 8.5
claims_results = await llm_service.batch_extract_claims(chunk_with_entities)

for claim in claims:
    claim_id = graph_service.create_claim_node(
        subject_entity_name=claim.get("subject", ""),
        object_entity_name=claim.get("object", ""),
        claim_type=claim.get("claim_type", "UNKNOWN"),
        status=claim.get("status", "SUSPECTED"),
        description=claim.get("description", ""),
        start_date=claim.get("start_date"),
        end_date=claim.get("end_date"),
        source_text=claim.get("source_text", ""),
    )

    # Link claim to entities and text unit
    graph_service.link_claim_to_entities(claim_id, subject, object)
    graph_service.link_claim_to_textunit(claim_id, chunk_id)
```

**Đánh giá:**
- ✅ **GraphToG tốt hơn:**
  - Always-on (không optional)
  - Source tracking via SOURCED_FROM → TextUnit
  - Deduplication với occurrence tracking
  - Richer attributes (source_text, descriptions)
  - Fuzzy entity matching cho linking
- 🟰 **GraphRAG:** Temporal support tương tự
- 💡 **GraphToG coi claims là first-class citizens** trong knowledge graph

---

### 7. Community Detection

| Tiêu chí | Microsoft GraphRAG | GraphToG |
|---------|-------------------|----------|
| **Algorithm** | Hierarchical Leiden | Leiden (via Neo4j GDS) |
| **Hierarchy** | ✅ Recursive until threshold | ✅ includeIntermediateCommunities |
| **Graph projection** | Internal graph structure | Neo4j GDS graph projection |
| **Relationship types** | RELATED_TO | RELATED_TO + MENTIONED_IN (undirected) |
| **Parameters** | seed, tolerance, maxLevels | seed, tolerance, maxLevels, concurrency |
| **Community metadata** | Community ID, level | id, level, createdAt, summary (empty initially) |
| **Incremental support** | ❌ | ✅ `detect_communities_incrementally()` |
| **Orphan cleanup** | ❌ | ✅ Auto-remove orphaned communities |

**Code snippet GraphToG:**
```python
# community_detection_service.py
def detect_communities(self, seed=42, include_intermediate_communities=True):
    """Run Leiden algorithm via Neo4j GDS"""

    # 1. Create GDS graph projection
    gds.graph.project('entity_graph', 'Entity',
                      {'RELATED_TO': {orientation: 'UNDIRECTED'}})

    # 2. Run Leiden
    leiden_results = gds.leiden.stream('entity_graph', {
        randomSeed: seed,
        includeIntermediateCommunities: include_intermediate_communities,
        tolerance: 0.0001,
        maxLevels: 10
    })

    # 3. Store community assignments with hierarchy levels
    self._store_community_assignments(session, results)
```

**Incremental community detection (GraphToG only):**
```python
def detect_communities_incrementally(self, affected_entity_ids, seed=42):
    """Efficient incremental detection for document updates"""

    # 1. Get old communities to mark as stale
    # 2. Remove old community assignments
    # 3. Expand to 1-hop neighbors
    # 4. Create subgraph projection for affected entities
    # 5. Run Leiden on subgraph
    # 6. Update community assignments
    # 7. Clean up orphaned communities
```

**Đánh giá:**
- ✅ **GraphToG tốt hơn:**
  - Incremental community detection → efficient updates
  - Neo4j GDS integration → native graph algorithms
  - Concurrency support (parallel processing)
  - Orphan cleanup
  - 1-hop neighbor expansion trong incremental mode
- 🟰 **Tương đương:** Cả hai đều dùng Hierarchical Leiden
- ⚠️ **GraphRAG:** Generic implementation, không có incremental support

---

### 8. Community Summarization

| Tiêu chí | Microsoft GraphRAG | GraphToG |
|---------|-------------------|----------|
| **Phase** | Phase 4 (separate phase) | Step 10 (integrated) |
| **LLM calls** | 2 passes (generate + summarize) | 1 pass (generate) |
| **Input** | Community members + relationships | Community entities + relationships + claims |
| **Output** | Executive summary + key entities/rels | Natural language summary |
| **Hierarchy handling** | Bottom-up summarization | Level-by-level summarization |
| **Storage** | Community Reports Table | Community.summary property |
| **Incremental** | ❌ | ✅ `summarize_affected_communities()` (implied) |

**Code snippet GraphToG:**
```python
# community_summarization_service.py
def summarize_all_communities(self):
    """Generate summaries for all detected communities"""

    # 1. Get all communities
    communities = self._get_all_communities()

    for community in communities:
        # 2. Get community context (entities, relationships, claims)
        context = self._get_community_context(community["id"])

        # 3. Generate summary via LLM
        summary = await llm_service.summarize_community(
            community_id=community["id"],
            entities=context["entities"],
            relationships=context["relationships"],
            claims=context.get("claims", [])
        )

        # 4. Store summary in Community node
        self._update_community_summary(community["id"], summary)
```

**Đánh giá:**
- ✅ **GraphRAG tốt hơn:**
  - 2-pass summarization → executive summaries
  - Bottom-up hierarchy → multi-level abstractions
- ✅ **GraphToG tốt hơn:**
  - Includes claims in summarization context
  - Integrated với Neo4j (không cần separate table)
  - Potentially incremental (có thể summarize only affected)
- 💡 **Different use cases:**
  - GraphRAG: Global search với hierarchical summaries
  - GraphToG: ToG traversal context với community-level understanding

---

### 9. Text Embeddings

| Tiêu chí | Microsoft GraphRAG | GraphToG |
|---------|-------------------|----------|
| **Phase** | Phase 7 (final phase) | Step 6 (integrated in pipeline) |
| **Embedded content** | TextUnits, Entity descriptions, Community reports | TextUnits (chunks) |
| **Embedding model** | User-configurable | Google Gemini text-embedding-004 |
| **Storage** | Vector store (user-defined) | PostgreSQL pgvector |
| **Deduplication** | ❌ | ✅ Skip if embedding exists |
| **Batch processing** | ✅ | ✅ Batch generation |
| **Cache support** | ❌ | ✅ Redis caching |
| **Dimension** | Model-dependent | 768 dimensions (Gemini) |

**Code snippet GraphToG:**
```python
# embedding_service.py
async def generate_and_store_embeddings(self, db, document_id, chunks):
    """Generate embeddings for chunks and store in pgvector"""

    # 1. Filter out chunks that already have embeddings
    new_chunks = self._filter_existing_embeddings(db, chunks)

    # 2. Batch generate embeddings
    embeddings = await self._batch_generate_embeddings([c["text"] for c in new_chunks])

    # 3. Store in PostgreSQL with pgvector
    for chunk, embedding in zip(new_chunks, embeddings):
        db_embedding = Embedding(
            document_id=document_id,
            chunk_id=chunk["chunk_id"],
            embedding=embedding,  # pgvector column
            text=chunk["text"]
        )
        db.add(db_embedding)

    db.commit()
```

**Đánh giá:**
- ✅ **GraphRAG comprehensive hơn:**
  - Embed TextUnits + Entity descriptions + Community reports
  - Multi-level embeddings cho different retrieval strategies
- ✅ **GraphToG tốt hơn:**
  - pgvector native support (SQL queries)
  - Deduplication (skip existing)
  - Redis caching
- ⚠️ **GraphToG thiếu:** Không embed entity descriptions và community summaries

---

### 10. Graph Schema & Storage

| Tiêu chí | Microsoft GraphRAG | GraphToG |
|---------|-------------------|----------|
| **Storage format** | Parquet files / Optional graph DB | Neo4j (required) + PostgreSQL |
| **Node types** | Entities, TextUnits, Documents, Communities, Claims | Entity, TextUnit, Document, Community, Claim |
| **Relationship types** | Generic RELATED_TO | Typed: RELATED_TO, MENTIONED_IN, PART_OF, IN_COMMUNITY, MAKES_CLAIM, ABOUT, SOURCED_FROM |
| **Constraints** | N/A (file-based) | Entity (name+type) UNIQUE, Document name UNIQUE, TextUnit id UNIQUE, Community id UNIQUE, Claim id UNIQUE |
| **Indexes** | N/A | 15+ indexes cho performance (entity name, type, document_id, mention_count, etc.) |
| **ToG optimization** | ❌ | ✅ Indexes cho entity name lookup, relation type, confidence, mention_count |

**GraphToG Schema (graph_service.py):**
```cypher
// Constraints
CREATE CONSTRAINT entity_name_type IF NOT EXISTS
FOR (e:Entity) REQUIRE (e.name, e.type) IS UNIQUE

CREATE CONSTRAINT document_name IF NOT EXISTS
FOR (d:Document) REQUIRE d.name IS UNIQUE

// ToG-specific indexes
CREATE INDEX entity_name_lookup IF NOT EXISTS
FOR (e:Entity) ON (e.name)

CREATE INDEX entity_mention_count IF NOT EXISTS
FOR (e:Entity) ON (e.mention_count)

CREATE INDEX relation_type IF NOT EXISTS
FOR ()-[r:RELATES_TO]-() ON (r.type)
```

**Đánh giá:**
- ✅ **GraphToG vượt trội:**
  - Native graph database (Neo4j) → efficient traversal
  - Constraints đảm bảo data integrity
  - Extensive indexing cho ToG performance
  - Typed relationships → semantic richness
- ⚠️ **GraphRAG flexible hơn:**
  - File-based → không cần graph DB infrastructure
  - Có thể integrate với bất kỳ graph DB nào
- 💡 **Trade-off:** GraphRAG portability vs GraphToG performance

---

## Tổng Kết So Sánh

### Điểm Mạnh Của Microsoft GraphRAG

1. **Simplicity & Portability**
   - File-based storage (Parquet) → không cần infrastructure phức tạp
   - Có thể chạy trên bất kỳ môi trường nào
   - Easy to deploy và scale horizontally

2. **Hierarchical Community Summarization**
   - 2-pass summarization (generate + summarize)
   - Bottom-up hierarchy → multi-level abstractions
   - Tối ưu cho global search queries

3. **Comprehensive Embeddings**
   - Embed TextUnits + Entities + Community reports
   - Multi-level retrieval strategies

4. **Mature Ecosystem**
   - Well-documented
   - Active community
   - Integration với nhiều tools (LlamaIndex, LangChain, etc.)

### Điểm Mạnh Của GraphToG

1. **Incremental Update Support** ⭐⭐⭐
   - Content hash tracking
   - Change detection
   - Incremental entity resolution
   - Incremental community detection
   - **→ Production-ready cho systems cần update thường xuyên**

2. **Advanced Entity Resolution** ⭐⭐⭐
   - 3-stage pipeline: Fuzzy matching → LLM verification → Merge
   - Configurable thresholds
   - Alias tracking
   - Mention count tracking
   - **→ Higher quality entity disambiguation**

3. **Rich Graph Semantics** ⭐⭐
   - Typed relationships (not just RELATED_TO)
   - Confidence scoring
   - Claims as first-class nodes
   - Source tracking (claims → text units)
   - **→ Richer knowledge representation**

4. **Neo4j Native Integration** ⭐⭐⭐
   - Native graph algorithms (Leiden via GDS)
   - Constraints & indexes
   - Efficient graph traversal
   - ToG-optimized indexes
   - **→ Best performance cho multi-hop reasoning**

5. **Claims Integration** ⭐⭐
   - Always-on claim extraction
   - Occurrence tracking
   - Temporal support
   - Fuzzy entity linking
   - **→ Better factual reasoning**

6. **Caching & Optimization** ⭐
   - Redis caching
   - pgvector deduplication
   - Batch processing
   - Concurrency support

### Điểm Yếu Của GraphToG

1. **Infrastructure Complexity**
   - Requires Neo4j + PostgreSQL + Redis
   - Harder to deploy và maintain
   - Higher operational cost

2. **Limited File Format Support**
   - Chỉ hỗ trợ Markdown (.md)
   - GraphRAG hỗ trợ CSV, .txt, và extensible

3. **Single-pass Community Summarization**
   - Không có hierarchical summarization như GraphRAG
   - Có thể kém hiệu quả cho global search

4. **Missing Multi-level Embeddings**
   - Chỉ embed text chunks
   - Không embed entity descriptions và community summaries

---

## Alignment với Microsoft GraphRAG

### ✅ Đã Giống (High Alignment)

| Feature | Implementation |
|---------|----------------|
| **Text Chunking** | Token-based với tiktoken, configurable size |
| **Entity Extraction** | LLM-based với batch processing |
| **Relationship Extraction** | LLM-based extraction |
| **Claim Extraction** | Subject, object, type, status, temporal bounds |
| **Community Detection** | Hierarchical Leiden algorithm |
| **Community Summarization** | LLM-generated summaries |
| **Text Embeddings** | Vector embeddings for chunks |

### ⚠️ Khác Biệt (Partial Alignment)

| Feature | GraphRAG | GraphToG | Impact |
|---------|----------|----------|--------|
| **Overlap trong chunking** | ❌ | ✅ 500 tokens | Tốt cho context continuity |
| **Entity resolution** | Basic summarization | Advanced 3-stage | Tốt hơn cho disambiguation |
| **Relationship types** | Generic RELATED_TO | Typed relationships | Semantic richness vs simplicity |
| **Graph storage** | File-based | Neo4j required | Portability vs performance |
| **Incremental updates** | ❌ | ✅ Full support | Production-readiness |

### ❌ Thiếu So Với GraphRAG

1. **Multi-level embeddings**
   - GraphRAG: TextUnits + Entities + Communities
   - GraphToG: Chỉ TextUnits
   - **Impact:** GraphToG có thể kém hiệu quả cho entity-based retrieval

2. **2-pass community summarization**
   - GraphRAG: Generate → Summarize → Executive summaries
   - GraphToG: Single-pass generation
   - **Impact:** GraphToG summaries có thể verbose hơn

3. **File format flexibility**
   - GraphRAG: CSV, .txt, extensible
   - GraphToG: Markdown only
   - **Impact:** Limited use cases

### ⭐ Vượt Trội Hơn GraphRAG

1. **Incremental processing** → Production-ready
2. **Advanced entity resolution** → Higher quality
3. **Neo4j native integration** → Best performance cho graph queries
4. **Claims as first-class nodes** → Better reasoning
5. **Source tracking** → Traceability

---

## Kết Luận

### GraphToG có giống với GraphRAG không?

**Trả lời: Giống 70-80%, nhưng có những cải tiến quan trọng**

### Chi Tiết:

#### Core Pipeline: ✅ Giống (90%)
- Text chunking → Entity extraction → Relationship extraction → Community detection → Summarization
- Cả hai đều dùng LLM-based extraction với Leiden algorithm

#### Implementation Details: ⚠️ Khác Biệt (60%)
- **Storage:** File-based vs Neo4j (fundamental difference)
- **Incremental updates:** GraphToG có, GraphRAG không
- **Entity resolution:** GraphToG sophisticated hơn
- **Schema:** GraphToG typed relationships, GraphRAG generic

#### Production Readiness: ⭐ GraphToG Tốt Hơn
- Incremental updates → không cần reindex toàn bộ
- Change detection → efficient resource usage
- Neo4j optimization → fast multi-hop queries
- Claims integration → better factual reasoning

### Recommendations

#### Nếu Muốn Alignment 100% Với GraphRAG:

1. **Add multi-level embeddings:**
   ```python
   # Embed entity descriptions
   await embedding_service.generate_entity_embeddings(entities)

   # Embed community summaries
   await embedding_service.generate_community_embeddings(communities)
   ```

2. **Add 2-pass community summarization:**
   ```python
   # Pass 1: Generate detailed reports
   detailed_reports = await summarize_communities(communities)

   # Pass 2: Summarize to executive summaries
   exec_summaries = await summarize_reports(detailed_reports)
   ```

3. **Support more file formats:**
   ```python
   # Add CSV, TXT parsers
   if file_ext == "csv":
       return DocumentProcessor.parse_csv(file_path)
   elif file_ext == "txt":
       return DocumentProcessor.parse_txt(file_path)
   ```

#### Nếu Giữ Nguyên GraphToG Philosophy:

**Keep incremental updates và advanced entity resolution** → Đây là competitive advantages

**Maintain Neo4j native integration** → Best cho ToG multi-hop reasoning

**Consider adding:**
- Multi-level embeddings (entity + community)
- File format flexibility (CSV, TXT)
- Optional file-based export (for portability)

---

## Appendix: Code Comparison

### GraphRAG Dataflow (Conceptual)
```
Documents → compose_text_units → TextUnits
  ↓
TextUnits → entity_extract → Entities + Relationships
  ↓
Entities → entity_summarize → Merged Entities
  ↓
Relationships → relationship_summarize → Merged Relationships
  ↓
TextUnits → claim_extract → Claims [optional]
  ↓
Graph → leiden_community_detection → Communities
  ↓
Communities → community_summarize → Community Reports
  ↓
Community Reports → summarize_reports → Executive Summaries
  ↓
All → text_embed → Vector Store
```

### GraphToG Pipeline (Actual Implementation)
```
Document (MD) → compute_content_hash → Change Detection
  ↓
[If changed or new]
  ↓
parse_md → Full Text
  ↓
create_chunks (with overlap) → TextUnits
  ↓
batch_extract_entities → Entities
  ↓
[Optional] find_duplicate_entity_pairs → Entity Resolution
  ↓           ↓ [fuzzy match]
  ↓           ↓ [LLM verification]
  ↓           ↓ merge_entities
  ↓
batch_extract_relationships → Typed Relationships
  ↓
batch_extract_claims → Claims (always)
  ↓
detect_communities (Leiden via Neo4j GDS) → Communities
  ↓
[Optional] detect_communities_incrementally [if update]
  ↓
summarize_all_communities → Community Summaries
  ↓
generate_and_store_embeddings → pgvector (TextUnits only)
  ↓
[Optional] Cache in Redis
```

### Key Architectural Difference:
- **GraphRAG:** Linear pipeline với clear phases, file-based
- **GraphToG:** Integrated pipeline với Neo4j, incremental-first design

---

**Tác giả:** Claude Code
**Codebase:** GraphToG (F:\khoaluan\graphtog)
**Reference:** Microsoft GraphRAG (https://github.com/microsoft/graphrag)
