# 🚀 Quick Start - GraphRAG Testing Guide

## Bước 1: Đảm bảo services đang chạy

```bash
# Start tất cả services
docker-compose up -d

# Kiểm tra status
docker-compose ps
```

Expected output:
```
NAME                COMMAND                  STATUS
graphtog-backend    "uvicorn app.main:..."   Up
graphtog-postgres   "docker-entrypoint..."   Up
graphtog-neo4j      "tini -g -- /docker..."  Up
graphtog-frontend   "docker-entrypoint..."   Up
```

---

## Bước 2: Kiểm tra biến môi trường

```bash
# Kiểm tra file .env trong backend/
cat backend/.env
```

Cần có:
```
GOOGLE_API_KEY=your_gemini_api_key_here
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
DATABASE_URL=postgresql://...
```

---

## Bước 3: Upload một document để test

### Option A: Qua Web UI
1. Mở http://localhost:3000
2. Login
3. Upload một file `.md`
4. Đợi processing hoàn tất (100%)

### Option B: Qua API (Postman/curl)
```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@sample.md"
```

---

## Bước 4: Chạy validation tests

```bash
# Di chuyển vào thư mục backend
cd backend

# Chạy test script
uv run python test_graphrag_fixes.py
```

---

## Expected Test Results

### ✅ Nếu thành công (4/4 tests passed):

```
======================================================================
  🚀 GraphRAG Critical Fixes - Validation Tests
  Microsoft GraphRAG Methodology Implementation
======================================================================

======================================================================
  📊 Graph Statistics
======================================================================
✅ Graph Statistics:
   • Documents: 1
   • Entities: 45
   • Communities: 3
   • Relationships: 28

======================================================================
  🧪 Test 1: Hierarchical Community Storage
======================================================================
✅ Found 3 communities with hierarchy info:
   • Level 0: 2 communities
   • Level 1: 1 communities
   ✅ Relationships have community_level property (45 found)

======================================================================
  🧪 Test 2: Community Summary Generation
======================================================================
📊 Existing summaries: 0
🔄 Generating community summaries...
✅ Generated 2 summaries
⚠️  Failed: 0

✅ Stored 2 community summaries (showing first 3):

   Community 42:
   • Summary: This community represents key entities related to...
   • Themes: technology, innovation, development
   • Significance: high

======================================================================
  🧪 Test 3: Global Search with Summaries
======================================================================
✅ Global search successful:
   • Communities: 2
   • Total entities: 45
   • Summaries available: True

   First 3 communities:

   Community 42:
   • Size: 25 entities
   • Level: 0
   • Summary: This community represents key entities related to...
   • Themes: technology, innovation, development

======================================================================
  📋 Test Summary
======================================================================

Results: 4/4 tests passed

  ✅ PASSED - Statistics
  ✅ PASSED - Hierarchical Communities
  ✅ PASSED - Community Summaries
  ✅ PASSED - Global Search

======================================================================
🎉 All tests passed! GraphRAG implementation is correct.
======================================================================
```

---

## ⚠️ Nếu có lỗi

### Error 1: "No entities found"
**Nguyên nhân**: Chưa upload và process document  
**Giải pháp**: Upload một file `.md` qua web UI hoặc API

### Error 2: "No communities found"
**Nguyên nhân**: Community detection chưa chạy  
**Giải pháp**: 
```python
# Chạy manually
from app.services.community_detection import community_detection_service
community_detection_service.detect_communities()
```

### Error 3: "GOOGLE_API_KEY not set"
**Nguyên nhân**: Thiếu API key  
**Giải pháp**: 
```bash
# Thêm vào backend/.env
echo "GOOGLE_API_KEY=your_key_here" >> backend/.env

# Restart backend
docker-compose restart backend
```

### Error 4: "Neo4j connection failed"
**Nguyên nhân**: Neo4j chưa start hoặc credentials sai  
**Giải pháp**:
```bash
# Kiểm tra Neo4j
docker-compose logs neo4j

# Restart Neo4j
docker-compose restart neo4j
```

---

## Bước 5: Test Global Query qua API

### Test với curl:

```bash
# Get token first (login)
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your_username","password":"your_password"}' \
  | jq -r '.access_token')

# Test global query
curl -X POST http://localhost:8000/api/queries/global \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"What are the main themes in this dataset?"}' \
  | jq
```

Expected response:
```json
{
  "status": "success",
  "query": "What are the main themes in this dataset?",
  "query_type": "global",
  "num_communities": 3,
  "answer": "Based on the community analysis...",
  "confidence_score": "0.85",
  "context": "📊 Dataset Overview: 45 entities across 3 communities..."
}
```

---

## Bước 6: Verify qua Neo4j Browser

1. Mở http://localhost:7474
2. Login với credentials từ `.env`
3. Chạy queries:

### Check communities với summaries:
```cypher
MATCH (c:Community)
WHERE c.summary IS NOT NULL
RETURN 
  c.id AS community_id,
  c.level AS level,
  c.summary AS summary,
  c.key_themes AS themes
LIMIT 5
```

### Check hierarchical structure:
```cypher
MATCH (e:Entity)-[r:IN_COMMUNITY]->(c:Community)
WHERE r.community_level IS NOT NULL
RETURN 
  e.name AS entity,
  c.id AS community_id,
  c.level AS community_level,
  r.community_level AS relationship_level
LIMIT 10
```

### Visualize community structure:
```cypher
MATCH path = (e:Entity)-[:IN_COMMUNITY]->(c:Community)
WHERE c.level = 0
RETURN path
LIMIT 50
```

---

## 📊 Performance Benchmarks

Với document ~10 pages:
- **Entity Extraction**: ~30 seconds
- **Relationship Extraction**: ~20 seconds
- **Community Detection**: ~5 seconds
- **Community Summarization**: ~15 seconds (3 communities)
- **Total Processing**: ~70 seconds

---

## 🎯 Next Actions

1. ✅ Upload test document
2. ✅ Run validation tests
3. ✅ Verify via Neo4j Browser
4. ✅ Test global query via API
5. ✅ Check logs for any warnings

---

## 📞 Support

Nếu gặp vấn đề:

1. Check logs:
   ```bash
   docker-compose logs backend | tail -100
   ```

2. Check Neo4j logs:
   ```bash
   docker-compose logs neo4j | tail -100
   ```

3. Verify environment variables:
   ```bash
   docker-compose exec backend env | grep -E "(GOOGLE_API_KEY|NEO4J)"
   ```

4. Restart services:
   ```bash
   docker-compose restart
   ```

---

## ✅ Success Criteria

GraphRAG implementation đúng khi:

- [x] Test script pass 4/4 tests
- [x] Communities có `summary` field populated
- [x] Communities có hierarchical `level` structure
- [x] Global search returns summaries
- [x] LLM generates answers using community summaries
- [x] No errors in backend logs

**Ready to use!** 🚀

