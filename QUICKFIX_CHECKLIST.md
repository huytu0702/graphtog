# 🔧 QUICK FIX CHECKLIST - Query Errors

## Vấn Đề
Khi thực hiện query API, gặp 2 lỗi chính:
1. ❌ `ERROR: 'query_type' is an invalid keyword argument for Query`
2. ❌ `ERROR: No API_KEY or ADC found`

---

## ✅ SOLUTION

### 1️⃣ Fix Database Schema Mismatch (DONE)

**Vấn Đề**: Endpoint đang cố lưu các field không tồn tại trong Query model

**Sửa**:
- ✅ Updated `backend/app/api/endpoints/queries.py` to use correct fields:
  - `query_type` → `query_mode`
  - `status` → (removed, use query_mode)
  - `entities_found` → (removed)
  - `answer` → `response`
  - `citations` → (removed, stored in reasoning_chain)
  - Added required `user_id` and `document_id` fields

**File Changed**: `backend/app/api/endpoints/queries.py` (lines 29-82)

---

### 2️⃣ Configure GOOGLE_API_KEY (⚠️ REQUIRED)

**Steps:**

#### Option A: Create .env file in backend directory

```bash
cd backend
# Create .env file with content:
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
```

#### Option B: Set environment variable

Windows PowerShell:
```powershell
$env:GOOGLE_API_KEY="your_google_api_key_here"
```

Linux/Mac:
```bash
export GOOGLE_API_KEY="your_google_api_key_here"
```

#### Option C: Docker Compose
Update `docker-compose.yml`:
```yaml
services:
  backend:
    environment:
      - GOOGLE_API_KEY=your_google_api_key_here
```

**Get Your API Key:**
1. Go to: https://ai.google.dev/
2. Click "Get API Key"
3. Create a new API key
4. Copy and use it

---

### 3️⃣ Better Error Handling (DONE)

**Improvements Made**:
- ✅ `llm_service.py`: Check if API key exists before configuring
- ✅ `llm_service.py`: Better error detection for missing API key
- ✅ `config.py`: Added validation method that warns about missing GOOGLE_API_KEY
- ✅ `query_service.py`: Added better error messages and logging
- ✅ `queries.py`: Added user_id validation in endpoint

---

## 🧪 Testing

### Test Query Endpoint

```bash
# Make sure you have:
# 1. Backend running: python -m uvicorn app.main:app --reload
# 2. Databases running: docker-compose up -d
# 3. GOOGLE_API_KEY set

# Test API:
curl -X POST http://localhost:8000/api/queries \
  -H "Content-Type: application/json" \
  -d '{
    "query": "what is the problem?",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "document_id": "550e8400-e29b-41d4-a716-446655440001",
    "hop_limit": 1
  }'
```

**Expected Response** (if API key is set):
```json
{
  "query": "what is the problem?",
  "status": "success or no_entities_found",
  "query_type": "EXPLORATORY",
  "entities_found": [...],
  "answer": "...",
  "citations": [...],
  "error": null,
  "id": "uuid-of-saved-query"
}
```

---

## 📋 Database Schema - Query Model

Current Query model fields:
```python
id: UUID                    # Primary key
user_id: UUID              # Foreign key to users
document_id: UUID (nullable) # Foreign key to documents
query_text: Text           # The user's question
response: Text (nullable)  # The answer from LLM
reasoning_chain: Text (nullable) # JSON with reasoning steps
query_mode: String (nullable)  # graphrag, tog, hybrid
confidence_score: String (nullable) # e.g., "0.95"
created_at: DateTime
updated_at: DateTime
```

---

## 🚀 Next Steps

1. **Get Google API Key** from https://ai.google.dev/
2. **Set GOOGLE_API_KEY** in .env or environment
3. **Restart Backend**: 
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```
4. **Test Query Endpoint** with curl or Postman
5. **Check Logs** for any remaining errors

---

## 📚 Relevant Documentation

- Google Gemini API: https://ai.google.dev/
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Neo4j: https://neo4j.com/docs/

---

## ⚡ Quick Status Check

Run this to see what's missing:
```bash
# Check .env file
ls -la backend/.env

# Check environment variables
echo $GOOGLE_API_KEY  # or $env:GOOGLE_API_KEY on Windows

# Check if services running
docker ps | grep postgres
docker ps | grep neo4j
docker ps | grep redis
```

---

**Last Updated**: 2025-10-28
**Status**: ✅ Schema Fixed, ⚠️ API Key Configuration Required

