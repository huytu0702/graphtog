# Phase 1.2 Testing Guide - GraphRAG Foundation

**Last Updated**: October 26, 2025  
**Status**: Ready for Testing

---

## 🚀 Quick Start Testing

### 1. Verify Deployment

```bash
# Check backend is running
curl http://localhost:8000/health

# Check graph stats
curl http://localhost:8000/api/admin/graph/stats

# Check admin health
curl http://localhost:8000/api/admin/health
```

### 2. Test Entity Extraction

```bash
curl -X POST http://localhost:8000/api/admin/test-entity-extraction \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Apple Inc. was founded by Steve Jobs in Cupertino, California. The company revolutionized personal computing."
  }'
```

**Expected Response**:
```json
{
  "status": "success",
  "test_result": {
    "chunk_id": "test_chunk",
    "entities": [
      {"name": "Apple Inc.", "type": "ORGANIZATION", "description": "...", "confidence": 0.95},
      {"name": "Steve Jobs", "type": "PERSON", "description": "...", "confidence": 0.92},
      {"name": "Cupertino", "type": "LOCATION", "description": "...", "confidence": 0.88}
    ],
    "status": "success"
  }
}
```

### 3. Test Query Classification

```bash
curl -X POST http://localhost:8000/api/admin/test-query-classification \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the relationship between Apple and Microsoft?"
  }'
```

**Expected Response**:
```json
{
  "status": "success",
  "classification": {
    "type": "ANALYTICAL",
    "reasoning": "Asks for relationship between two entities",
    "key_entities": ["Apple", "Microsoft"],
    "suggested_depth": 2
  }
}
```

---

## 📋 Full Testing Workflow

### Phase 1: Document Upload & Processing

#### Step 1: Create Test Document

```bash
# Create a test markdown file (backend/uploads/test_doc.md)
cat > backend/uploads/test_doc.md << 'EOF'
# AI Technology Companies

## Apple
Apple Inc. is a technology company headquartered in Cupertino, California. Founded in 1976 by Steve Jobs, Steve Wozniak, and Ronald Wayne, Apple develops and sells computer hardware, software, and online services.

## Microsoft
Microsoft is a technology corporation headquartered in Redmond, Washington. Bill Gates and Paul Allen founded the company in 1975. Microsoft develops software, cloud services, and gaming products.

## Relationship
Apple and Microsoft have historically competed in the personal computer market. Both companies have collaborated on various projects including Office for Mac.

EOF
```

#### Step 2: Upload Document

```bash
# First login to get auth token
TOKEN=$(curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}' \
  | jq -r '.access_token')

# Upload document
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@backend/uploads/test_doc.md"
```

**Expected Response**:
```json
{
  "id": 1,
  "filename": "test_doc.md",
  "status": "processing",
  "created_at": "2025-10-26T10:00:00",
  "processing_progress": 0
}
```

#### Step 3: Check Processing Status

```bash
curl http://localhost:8000/api/documents/1

# Expected: status changes from "processing" to "completed"
```

### Phase 2: Entity Extraction Validation

#### Check Extracted Entities

```bash
# Get graph statistics
curl http://localhost:8000/api/admin/graph/stats
```

**Expected Output**:
```json
{
  "status": "success",
  "statistics": {
    "documents": 1,
    "text_units": 3,
    "entities": 8,
    "relationships": 5
  }
}
```

**What to validate**:
- ✓ Documents count = 1
- ✓ Text units > 0 (should be 3 from test doc)
- ✓ Entities > 0 (should extract: Apple, Microsoft, Steve Jobs, Bill Gates, Paul Allen, Cupertino, Redmond, Washington)
- ✓ Relationships > 0 (should extract: Apple-Microsoft competition, co-collaboration, etc.)

### Phase 3: Query Testing

#### Test 1: Simple Entity Query

```bash
curl -X POST http://localhost:8000/api/queries \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Who founded Apple?",
    "hop_limit": 1
  }'
```

**Expected Output**:
```json
{
  "query": "Who founded Apple?",
  "status": "success",
  "entities_found": ["Steve Jobs", "Apple"],
  "context": "**Apple** (ORGANIZATION) - ...\n**Steve Jobs** (PERSON) - ...",
  "answer": "Steve Jobs founded Apple in 1976 along with Steve Wozniak and Ronald Wayne.",
  "citations": ["Steve Jobs (PERSON)", "Apple (ORGANIZATION)"]
}
```

#### Test 2: Relationship Query

```bash
curl -X POST http://localhost:8000/api/queries \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the relationship between Apple and Microsoft?",
    "hop_limit": 2
  }'
```

**Expected Output**:
```json
{
  "query": "What is the relationship between Apple and Microsoft?",
  "status": "success",
  "entities_found": ["Apple", "Microsoft"],
  "context": "**Apple** (ORGANIZATION) - ...\n  Related to: Microsoft, Steve Jobs, ...\n**Microsoft** (ORGANIZATION) - ...",
  "answer": "Apple and Microsoft are competing technology companies that have historically competed in the personal computer market. They have also collaborated on projects like Office for Mac.",
  "citations": ["Apple (ORGANIZATION)", "Microsoft (ORGANIZATION)"]
}
```

#### Test 3: Batch Queries

```bash
curl -X POST http://localhost:8000/api/batch-queries \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [
      "Who founded Microsoft?",
      "Where is Apple headquartered?",
      "When was Microsoft founded?"
    ]
  }'
```

**Expected Output**:
```json
{
  "status": "success",
  "query_count": 3,
  "results": [
    {"query": "Who founded Microsoft?", "status": "success", "answer": "..."},
    {"query": "Where is Apple headquartered?", "status": "success", "answer": "..."},
    {"query": "When was Microsoft founded?", "status": "success", "answer": "..."}
  ]
}
```

---

## 🔍 Manual Testing Scenarios

### Scenario 1: Small Document Processing

**Test**: Upload a 2-3 paragraph document

**Expected Results**:
- Processing completes in < 30 seconds
- 2-4 chunks created
- 5-10 entities extracted
- 3-8 relationships extracted

### Scenario 2: Medium Document Processing

**Test**: Upload a 10-15 paragraph document (~5KB)

**Expected Results**:
- Processing completes in < 2 minutes
- 5-10 chunks created
- 20-50 entities extracted
- 15-30 relationships extracted

### Scenario 3: Query Accuracy

**Test**: Ask 10 queries about the uploaded document

**Expected Results**:
- 80%+ queries return relevant entities
- 70%+ queries generate accurate answers
- All queries include proper citations

### Scenario 4: Error Handling

**Test Cases**:
1. Empty query → Error message: "Query cannot be empty"
2. Query too long (>1000 chars) → Error message: "Query too long"
3. No matching entities → Status: "no_entities_found"
4. Malformed JSON → HTTP 422 Unprocessable Entity

---

## 📊 Performance Benchmarks

### Target Metrics

| Metric | Target | Threshold |
|--------|--------|-----------|
| Document parsing | < 5s for 10KB | < 10s |
| Chunking | < 2s for 10KB | < 5s |
| Entity extraction | < 60s for 10 chunks | < 120s |
| Relationship extraction | < 60s for 10 chunks | < 120s |
| Total processing | < 2 min for 10KB | < 5 min |
| Query response | < 3s | < 5s |
| Batch query (10) | < 30s | < 60s |

### How to Measure

```bash
# Time a document upload
time curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@backend/uploads/test_doc.md"

# Time a query
time curl -X POST http://localhost:8000/api/queries \
  -H "Content-Type: application/json" \
  -d '{"query":"Who founded Apple?"}'
```

---

## 🐛 Debugging Helpers

### Admin Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/admin/health` | GET | Check component health |
| `/api/admin/graph/stats` | GET | Get graph statistics |
| `/api/admin/test-entity-extraction` | POST | Test entity extraction |
| `/api/admin/test-relationship-extraction` | POST | Test relationship extraction |
| `/api/admin/test-query-classification` | POST | Test query classification |
| `/api/admin/test-answer-generation` | POST | Test answer generation |

### Logs to Check

```bash
# Backend logs
docker logs graphtog_backend -f

# Neo4j logs
docker logs graphtog_neo4j -f

# PostgreSQL logs
docker logs graphtog_postgres -f
```

### Common Issues & Solutions

#### Issue 1: "No matching entities found"
- **Cause**: Entities not extracted or entities don't match query terms
- **Solution**: 
  1. Check `/api/admin/graph/stats` to verify entities were created
  2. Test entity extraction directly with `/api/admin/test-entity-extraction`
  3. Verify query classification with `/api/admin/test-query-classification`

#### Issue 2: "Connection refused" to Neo4j
- **Cause**: Neo4j container not running
- **Solution**: 
  ```bash
  docker-compose up -d neo4j
  docker logs graphtog_neo4j
  ```

#### Issue 3: Slow processing
- **Cause**: Large document, rate limiting, or Gemini API quota
- **Solution**:
  1. Check Gemini API quota in Google Cloud Console
  2. Increase rate limiting in `LLMService`
  3. Break large documents into smaller files

---

## ✅ Sign-Off Checklist

- [ ] Backend starts without errors
- [ ] `/api/health` responds
- [ ] `/api/admin/health` shows healthy
- [ ] Entity extraction test works
- [ ] Query classification test works
- [ ] Document upload completes successfully
- [ ] Graph statistics show created entities
- [ ] Simple query returns result
- [ ] Relationship query returns result
- [ ] Batch queries work
- [ ] All 4 query endpoints respond
- [ ] Admin endpoints accessible
- [ ] Performance within targets
- [ ] Error handling works correctly

---

## 📝 Testing Log Template

```markdown
# Testing Log - Phase 1.2

**Date**: [date]
**Tester**: [name]
**Backend Version**: [commit hash]

## Environment
- Docker: [version]
- Python: [version]
- Neo4j: [version]

## Test Results

### Document Processing
- [ ] Small doc (1KB)
  - Time: ___s
  - Chunks: ___
  - Entities: ___
- [ ] Medium doc (10KB)
  - Time: ___s
  - Chunks: ___
  - Entities: ___

### Query Testing
- [ ] Simple query: ___% accuracy
- [ ] Complex query: ___% accuracy
- [ ] Batch queries: ___/10 successful

### Performance
- [ ] Avg processing time: ___s
- [ ] Avg query time: ___ms
- [ ] Graph stats response: ___ms

### Issues Found
1. ___
2. ___
3. ___

### Recommendations
1. ___
2. ___
```

---

**Next Steps After Testing**:
1. ✅ Complete Phase 1.2 testing
2. ⏳ Begin Phase 2 (Community Detection)
3. ⏳ Optimize performance bottlenecks
4. ⏳ Add frontend testing dashboard
