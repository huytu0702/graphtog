# Incremental Indexing Implementation

## Overview

Incremental indexing allows efficient document updates without reprocessing the entire knowledge graph. The system detects content changes via SHA256 hashing and only reprocesses affected portions of the graph.

## Features Implemented

### 1. Version Tracking (Document Model)
- **version**: Integer field tracking document version (starts at 1, increments on update)
- **content_hash**: SHA256 hash of document content for change detection
- **last_processed_at**: Timestamp of last successful processing

### 2. Change Detection
- Computes SHA256 hash of document content
- Compares with stored hash to detect changes
- Skips reprocessing if content unchanged (saves LLM API calls and processing time)

### 3. Incremental Processing Pipeline
When a document is updated:
1. **Parse new content** and compute hash
2. **Detect changes** - compare with stored hash
3. **Skip if unchanged** - return success immediately
4. **Identify affected communities** - track which communities contain entities from this document
5. **Clean up old data**:
   - Delete claims sourced from document
   - Remove orphaned entities (only mentioned in this document)
   - Decrement mention_count for shared entities
   - Delete text units
6. **Reprocess document** with full pipeline (chunking, entity extraction, relationships, claims)
7. **Incremental community detection** - only recompute affected communities + 1-hop neighbors
8. **Update metadata** - increment version, update hash and timestamp

### 4. Graph Service Updates
New methods in `graph_service.py`:

#### `get_affected_communities_for_document(document_id)`
Returns communities and entities affected by document update.

```python
{
    "community_ids": [123, 456],
    "affected_entities": ["entity_1", "entity_2"],
    "num_communities": 2,
    "num_entities": 5
}
```

#### `delete_document_graph_data(document_id)`
Removes all graph data for a document:
- Text units
- Claims
- Orphaned entities
- Updates mention counts for shared entities

```python
{
    "status": "success",
    "textunits_deleted": 50,
    "entities_deleted": 10,
    "entities_affected": 25,
    "claims_deleted": 8
}
```

#### `update_entity(entity_id, **kwargs)`
Updates existing entity instead of recreating:
- name, entity_type, description, confidence

#### `update_document_node_status(document_id, status)`
Updates document status in Neo4j graph.

### 5. Incremental Community Detection
New method in `community_detection_service.py`:

#### `detect_communities_incrementally(affected_entity_ids, seed=42)`
Efficiently recomputes communities for affected entities:
1. Remove old community assignments
2. Expand to include 1-hop neighbors (ensures proper boundary detection)
3. Create temporary subgraph projection
4. Run Leiden algorithm on subgraph only
5. Update community assignments
6. Clean up orphaned communities

**Performance**: O(n) where n = affected entities + neighbors, instead of O(N) for all entities

### 6. API Endpoints

#### PUT `/documents/{document_id}/update`
Update document with incremental processing.

**Request**:
```bash
curl -X PUT "http://localhost:8000/api/documents/{doc_id}/update" \
  -H "Authorization: Bearer {token}" \
  -F "file=@updated_document.md"
```

**Response**:
```json
{
  "id": "doc-uuid",
  "filename": "updated_document.md",
  "status": "processing",
  "version": 2,
  "message": "Document update initiated with incremental processing"
}
```

#### POST `/documents/{document_id}/reprocess`
Reprocess existing document (incremental by default, force_full optional).

**Request**:
```bash
# Incremental reprocessing
curl -X POST "http://localhost:8000/api/documents/{doc_id}/reprocess" \
  -H "Authorization: Bearer {token}"

# Force full reprocessing
curl -X POST "http://localhost:8000/api/documents/{doc_id}/reprocess?force_full=true" \
  -H "Authorization: Bearer {token}"
```

**Response**:
```json
{
  "id": "doc-uuid",
  "filename": "document.md",
  "status": "processing",
  "version": 2,
  "force_full": false,
  "message": "Incremental document reprocessing initiated"
}
```

#### GET `/documents/{document_id}/version-info`
Get version tracking information.

**Response**:
```json
{
  "id": "doc-uuid",
  "filename": "document.md",
  "version": 3,
  "content_hash": "a3d5f2...",
  "last_processed_at": "2025-10-30T10:30:00",
  "created_at": "2025-10-25T08:00:00",
  "updated_at": "2025-10-30T10:30:00",
  "status": "completed"
}
```

### 7. Testing
Comprehensive test suite in `tests/test_incremental_indexing.py`:

- **Content Hashing**: SHA256 computation, empty content, hash consistency
- **Change Detection**: First upload, content changed, content unchanged
- **Graph Cleanup**: Orphaned entities, affected communities, data deletion
- **Entity Updates**: Update operations, confidence scoring
- **Incremental Community Detection**: Empty lists, invalid entities, subgraph processing
- **Document Versioning**: Initial version, version increment, metadata updates
- **Integration Tests**: Full incremental workflow with real files
- **Performance Benchmarks**: Change detection speed, hash computation speed

Run tests:
```bash
# All tests
pytest tests/test_incremental_indexing.py

# Specific test class
pytest tests/test_incremental_indexing.py::TestChangeDetection

# Integration tests only
pytest tests/test_incremental_indexing.py -m integration

# Benchmarks only
pytest tests/test_incremental_indexing.py -m benchmark
```

## Performance Benefits

### Before (Full Reprocessing)
- Delete entire document graph
- Reprocess all chunks (~50-100 for typical document)
- Extract entities for all chunks (50-100 LLM calls)
- Extract relationships for all chunks (50-100 LLM calls)
- Full community detection on entire graph (expensive)
- **Total**: ~200 LLM calls + full graph algorithms

### After (Incremental Processing)
- Detect no change → **0 LLM calls**, instant return
- Detect change → Same extraction but **incremental community detection**
- Community detection on affected subgraph only (~10-20% of entities)
- **Savings**: Up to 100% for unchanged, 80-90% faster community detection for changes

## Usage Examples

### Scenario 1: Update Unchanged Document
```python
# User uploads same document again
# System computes hash, detects no change
# Returns immediately without reprocessing
# Result: ~1 second instead of ~5 minutes
```

### Scenario 2: Minor Document Update
```python
# User updates 1 section out of 10
# System detects change via hash
# Reprocesses entire document (extracts entities/relationships)
# Only recomputes communities for affected 15% of entities
# Result: ~3 minutes instead of ~5 minutes
```

### Scenario 3: Force Full Reprocessing
```python
# Admin wants to reprocess with updated prompts
POST /documents/{id}/reprocess?force_full=true
# Clears hash, forces complete reprocessing
# Useful for prompt tuning or algorithm updates
```

## Configuration

Add to `backend/app/config.py`:

```python
# Incremental indexing settings
ENABLE_INCREMENTAL_INDEXING = True  # Enable/disable feature
INCREMENTAL_HASH_ALGORITHM = "sha256"  # Hash algorithm for change detection
```

## Database Schema Changes

### PostgreSQL
```sql
-- Add to documents table
ALTER TABLE documents ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE documents ADD COLUMN content_hash VARCHAR(64);
ALTER TABLE documents ADD COLUMN last_processed_at TIMESTAMP;

-- Add index for performance
CREATE INDEX idx_documents_content_hash ON documents(content_hash);
```

### Neo4j
No schema changes required. Existing graph structure supports incremental updates.

## Migration Guide

For existing deployments:

2. **Rebuild containers** (schema changes require rebuild):
```bash
docker-compose down
docker-compose up --build -d
```

3. **Backfill existing documents** (optional):
```python
# Compute hashes for existing documents
from app.services.document_processor import compute_content_hash

for doc in db.query(Document).filter(Document.content_hash == None):
    if os.path.exists(doc.file_path):
        content = open(doc.file_path).read()
        doc.content_hash = compute_content_hash(content)
        doc.last_processed_at = doc.updated_at
        db.commit()
```

## Monitoring

Track incremental indexing performance:

```python
# Metrics to monitor
- Incremental update rate (% of updates that skip reprocessing)
- Average processing time: full vs incremental
- Community detection time: full vs incremental
- Entity reuse rate (entities not deleted because shared)
```

## Troubleshooting

### Issue: Documents always reprocessing
**Cause**: Hash mismatches due to encoding or line ending differences
**Solution**: Ensure consistent file encoding (UTF-8) and normalize line endings

### Issue: Orphaned communities after update
**Cause**: Community cleanup not running
**Solution**: Check `delete_document_graph_data` logs, verify Neo4j connectivity

### Issue: Version not incrementing
**Cause**: Database transaction not committing
**Solution**: Check `document.version += 1` and `db.commit()` in processing pipeline

## Future Enhancements

Potential improvements (not yet implemented):

1. **Partial document updates**: Only reprocess changed sections
2. **Delta extraction**: Extract only new entities/relationships
3. **Async community detection**: Background job queue for large graphs
4. **Hash-based deduplication**: Prevent duplicate document uploads
5. **Version history**: Store snapshots of previous document versions
6. **Rollback support**: Revert to previous document version

## References

- Microsoft GraphRAG: https://microsoft.github.io/graphrag/
- Neo4j GDS Leiden: https://neo4j.com/docs/graph-data-science/current/algorithms/leiden/
- Task specification: `tasks.md` section 2.5

---

**Implementation Date**: 2025-10-30
**Status**: ✅ Complete and tested
**Related Tasks**: Priority 2.5 from tasks.md
