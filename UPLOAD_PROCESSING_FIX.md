# 🔧 Upload Processing Fix - Neo4j UUID & API Key Errors

## 🐛 Lỗi Phát Hiện

Sau khi upload file thành công, backend gặp 2 lỗi khi xử lý document:

### Lỗi 1: Neo4j UUID Type Error
```
ERROR:app.services.graph_service:Document creation error: Values of type <class 'uuid.UUID'> are not supported
ERROR:app.services.graph_service:TextUnit creation error: Values of type <class 'uuid.UUID'> are not supported
```

**Nguyên nhân**: Neo4j driver không hỗ trợ Python UUID object trực tiếp, cần convert sang string.

### Lỗi 2: Missing GOOGLE_API_KEY
```
ERROR:app.services.llm_service:API key not configured. Please set GOOGLE_API_KEY environment variable.
ERROR:app.services.document_processor:❌ Error processing document: No API_KEY or ADC found.
```

**Nguyên nhân**: GOOGLE_API_KEY chưa được set trong environment.

---

## ✅ Giải Pháp Đã Triển Khai

### 1️⃣ Fix Neo4j UUID Conversion

**File**: `backend/app/services/graph_service.py`

**Thay đổi line 112** (create_document_node):
```python
result = session.run(
    query,
    document_id=str(document_id),  # Convert UUID to string for Neo4j
    document_name=document_name,
    file_path=file_path,
)
```

**Thay đổi line 167** (create_textunit_node):
```python
result = session.run(
    query,
    textunit_id=textunit_id,
    document_id=str(document_id),  # Convert UUID to string for Neo4j
    text=text,
    start_char=start_char,
    end_char=end_char,
)
```

### 2️⃣ Create .env File with GOOGLE_API_KEY

**File**: `backend/.env` (đã được tạo)

**Nội dung**:
```bash
# Google Gemini API - REQUIRED for entity extraction
# Get your API key from: https://ai.google.dev/
GOOGLE_API_KEY=AIzaSyCpz9Q5YLfxXNYKXl_example_replace_this
GEMINI_MODEL=gemini-2.0-flash-exp
```

---

## 🚀 Hướng Dẫn Hoàn Tất Setup

### Bước 1: Lấy Google API Key

1. Truy cập: **https://ai.google.dev/**
2. Click **"Get API Key"** hoặc **"Get started"**
3. Đăng nhập với Google account
4. Tạo API key mới (hoặc sử dụng existing key)
5. Copy API key (dạng: `AIzaSy...`)

### Bước 2: Cập Nhật .env File

**Mở file**: `backend/.env`

**Thay thế dòng**:
```bash
# Before
GOOGLE_API_KEY=AIzaSyCpz9Q5YLfxXNYKXl_example_replace_this

# After (paste your real API key)
GOOGLE_API_KEY=AIzaSyC_YOUR_REAL_API_KEY_HERE
```

**Hoặc dùng command**:
```powershell
# PowerShell
cd backend
(Get-Content .env) -replace 'AIzaSyCpz9Q5YLfxXNYKXl_example_replace_this', 'YOUR_REAL_API_KEY' | Set-Content .env
```

### Bước 3: Restart Backend

**Option A: Development mode (uvicorn)**
```bash
cd backend
# Ctrl+C để stop backend hiện tại
python -m uvicorn app.main:app --reload
```

**Option B: Docker mode**
```bash
# Trong root directory
docker-compose restart backend
```

**Option C: Đang chạy Python trực tiếp**
```bash
# Ctrl+C để stop
cd backend
uv run uvicorn app.main:app --reload
```

### Bước 4: Test Upload Lại

1. Vào dashboard: `http://localhost:3000/dashboard`
2. Click **"Tải nguồn lên"**
3. Upload file `.md` (ví dụ: `test.md` hoặc `README.md`)
4. Chờ processing complete

---

## 🧪 Kiểm Tra Logs (Expected)

**Backend logs sau khi fix** (successful processing):
```
INFO:app.services.document_processor:Step 1: Parsing document...
INFO:app.services.document_processor:✅ Successfully parsed Markdown: XXXX characters
INFO:app.services.document_processor:Step 2: Initializing graph schema...
INFO:app.services.graph_service:✅ Graph schema initialized
INFO:app.services.document_processor:Step 3: Creating document node...
INFO:app.services.graph_service:Created document node: filename.md
INFO:app.services.document_processor:Step 4: Chunking document...
INFO:app.services.chunking:Created X chunks from text (XXX tokens)
INFO:app.services.document_processor:Step 5: Processing chunks for entity extraction...
INFO:app.services.llm_service:✅ Gemini configured successfully
INFO:app.services.document_processor:Step 6: Extracting entities from chunks...
INFO:app.services.llm_service:Extracted X entities from chunk
INFO:app.services.document_processor:✅ Document processing completed
```

**Không còn lỗi**:
- ❌ `Values of type <class 'uuid.UUID'> are not supported`
- ❌ `No API_KEY or ADC found`

---

## 📋 Checklist

- ✅ Neo4j UUID conversion fixed in `graph_service.py`
- ✅ `.env` file created in `backend/`
- ⚠️ **TODO**: Replace placeholder API key with real key
- ⚠️ **TODO**: Restart backend to load new environment variables
- ⚠️ **TODO**: Test upload and verify processing completes

---

## 🔍 Troubleshooting

### Vấn đề: Vẫn thấy "No API_KEY" error

**Giải pháp**:
1. Check .env file có API key chưa:
   ```bash
   cat backend/.env | grep GOOGLE_API_KEY
   ```
2. Verify backend đã restart:
   ```bash
   # Check process timestamp
   ps aux | grep uvicorn
   ```
3. Check config.py có load API key:
   ```bash
   cd backend
   python -c "from app.config import get_settings; print(get_settings().GOOGLE_API_KEY)"
   ```

### Vấn đề: API key invalid

**Giải pháp**:
1. Verify key format: Should start with `AIzaSy`
2. Check key hasn't expired at https://ai.google.dev/
3. Ensure no extra spaces or quotes in .env file
4. Try regenerating a new key

### Vấn đề: UUID error vẫn còn

**Giải pháp**:
1. Verify file `backend/app/services/graph_service.py` đã được update
2. Check line 112 và 167 có `str(document_id)`
3. Restart backend để reload code changes

---

## 📚 Files Changed

1. ✅ `backend/app/services/graph_service.py` - UUID to string conversion (lines 112, 167)
2. ✅ `backend/.env` - Created with GOOGLE_API_KEY placeholder

---

## 🎯 Next Steps

1. **Replace API key** in `backend/.env`
2. **Restart backend** server
3. **Upload a test file** to verify end-to-end processing
4. **Check Neo4j** to see document and entity nodes created:
   ```cypher
   // Open Neo4j Browser: http://localhost:7474
   MATCH (d:Document) RETURN d LIMIT 5
   MATCH (e:Entity) RETURN e LIMIT 10
   MATCH (t:TextUnit) RETURN t LIMIT 5
   ```

---

**Last Updated**: 2025-10-28
**Status**: ✅ Code Fixed, ⚠️ Waiting for API Key Configuration
**Impact**: Enables full document processing pipeline (upload → parse → chunk → extract → graph)

