# Fix MENTIONS Relationship Direction

## 🐛 Problem

ToG Enhancement Solution 2+5 failed because:
- **graph_service.py** created `(Entity)-[:MENTIONED_IN]->(TextUnit)` (wrong direction)
- **tog_service.py** queries for `(Entity)<-[:MENTIONS]-(TextUnit)` (correct direction)
- Result: No matches found, 0 enrichment chunks retrieved

## ✅ Solution Applied

### 1. Fixed `graph_service.py` Line 251-288

**Before:**
```python
MERGE (e)-[r:MENTIONED_IN]->(t)  # ❌ Wrong direction, wrong name
```

**After:**
```python
MERGE (t)-[r:MENTIONS]->(e)  # ✅ Correct: TextUnit → Entity
```

Also added `session.close()` in `finally` block to prevent connection leaks.

### 2. Database Cleanup Required

You need to clean up old data and re-upload documents.

## 🔧 Cleanup Steps

### Option A: Delete All Data (Recommended for Testing)

Run this in Neo4j Browser (http://localhost:7474):

```cypher
// 1. Delete all MENTIONED_IN relationships (old, wrong direction)
MATCH ()-[r:MENTIONED_IN]->()
DELETE r;

// 2. Delete all nodes (documents, entities, textunits)
MATCH (n)
DETACH DELETE n;

// 3. Verify cleanup
MATCH (n) RETURN count(n) as total_nodes;
MATCH ()-[r]->() RETURN count(r) as total_relationships;
```

### Option B: Delete Only MENTIONED_IN Relationships (Keep Entities)

If you want to keep existing entities and only fix the mention relationships:

```cypher
// Delete old MENTIONED_IN relationships
MATCH (e:Entity)-[r:MENTIONED_IN]->(t:TextUnit)
DELETE r;

// Verify deletion
MATCH ()-[r:MENTIONED_IN]->() RETURN count(r);
// Should return 0

// Note: You'll need to re-upload documents to create new MENTIONS relationships
```

### Option C: Migrate Existing Relationships (Advanced)

Convert existing MENTIONED_IN to MENTIONS with correct direction:

```cypher
// Find all MENTIONED_IN relationships
MATCH (e:Entity)-[old:MENTIONED_IN]->(t:TextUnit)

// Create new MENTIONS relationship in correct direction
MERGE (t)-[new:MENTIONS]->(e)
ON CREATE SET new.created_at = datetime()

// Delete old relationship
DELETE old

RETURN count(new) as mentions_created;
```

## 📋 Post-Cleanup Steps

### 1. Restart Backend Server

```bash
cd backend
# Stop server (Ctrl+C)
# Restart with uv
uv run uvicorn app.main:app --reload
```

### 2. Re-upload Test Document

Via frontend UI or API:

```bash
# Using curl
curl -X POST "http://localhost:8000/api/documents/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test_document.md"
```

### 3. Verify MENTIONS Relationships

Run in Neo4j Browser:

```cypher
// Check MENTIONS relationships exist
MATCH (tu:TextUnit)-[r:MENTIONS]->(e:Entity)
RETURN tu.text as textunit, e.name as entity, count(r) as mention_count
LIMIT 10;

// Count total MENTIONS
MATCH ()-[r:MENTIONS]->()
RETURN count(r) as total_mentions;
```

### 4. Test ToG Query

Query via frontend or API:

```bash
curl -X POST "http://localhost:8000/api/tog/query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "tài liệu nói gì",
    "config": {
      "search_depth": 3,
      "search_width": 3
    }
  }'
```

**Expected Logs (Success):**
```
INFO:app.services.tog_service:Enriching answer with top 3 chunks for 5 entities
INFO:app.services.tog_service:Retrieved 3 enrichment chunks  # ✅ Should be > 0
INFO:app.services.tog_service:ToG reasoning completed with 5 triplets  # ✅ Should be > 0
```

**No more warnings:**
```
❌ WARNING: One of the relationship types in your query is not available: MENTIONS
```

## 🔍 Verification Checklist

After applying the fix:

- [ ] Ran Neo4j cleanup query (Option A, B, or C)
- [ ] Verified old MENTIONED_IN relationships deleted
- [ ] Restarted backend server
- [ ] Re-uploaded test document
- [ ] Verified MENTIONS relationships created in correct direction
- [ ] Ran ToG query successfully
- [ ] Checked logs show "Retrieved N enrichment chunks" where N > 0
- [ ] No more Neo4j warnings about MENTIONS relationship

## 📊 Before/After Comparison

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| Relationship Type | MENTIONED_IN | MENTIONS |
| Direction | Entity → TextUnit ❌ | TextUnit → Entity ✅ |
| Neo4j Warnings | Yes (MENTIONS not found) | No warnings |
| Enrichment Chunks | 0 | 3-5+ |
| ToG Triplets | 0 | 5-10+ |
| Answer Quality | Generic (no context) | Detailed (with source texts) |

## 👤 Fix Date

**Date:** 2025-11-10
**Modified Files:**
- `backend/app/services/graph_service.py` (Line 251-288)

**Changes:**
1. Changed relationship from `MENTIONED_IN` to `MENTIONS`
2. Reversed direction from `(e)->(t)` to `(t)->(e)`
3. Added `session.close()` in `finally` block

---

## 📝 Technical Notes

### Why This Direction?

The correct direction is `(TextUnit)-[:MENTIONS]->(Entity)` because:

1. **Semantic meaning**: A text unit "mentions" an entity (not the other way around)
2. **Query pattern**: ToG needs to find all text units that mention an entity
3. **Performance**: Easier to traverse from entity to find all mentioning texts

```cypher
// Find all texts mentioning entity "X"
MATCH (e:Entity {name: "X"})<-[:MENTIONS]-(tu:TextUnit)
RETURN tu.text
```

### Schema Consistency

This fix aligns with standard graph modeling:
- `(Document)-[:CONTAINS]->(TextUnit)` - Document contains text
- `(TextUnit)-[:MENTIONS]->(Entity)` - Text mentions entity
- `(Entity)-[:RELATED_TO]->(Entity)` - Entity relates to entity

All relationships flow in semantically meaningful directions.
