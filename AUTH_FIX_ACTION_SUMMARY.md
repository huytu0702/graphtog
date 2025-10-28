# Authentication 401 Error - Quick Fix Summary

## 🚨 Problem
Users getting `401 Unauthorized` errors during registration and login with `CredentialsSignin` failure.

## ✅ Root Cause
**Missing `frontend/.env.local` file** - NextAuth cannot sign/verify sessions without `NEXTAUTH_SECRET`.

---

# 🔧 QUERY ENDPOINT FIXES (Completed 2025-10-28)

## Problem Detected ❌

When executing queries via `/api/queries` endpoint:
```
ERROR 1: 'query_type' is an invalid keyword argument for Query
ERROR 2: No API_KEY or ADC found. GOOGLE_API_KEY environment variable not set
```

## Root Causes 🔍

### Issue 1: Database Schema Mismatch
Endpoint (`backend/app/api/endpoints/queries.py` lines 60-67) tried to save fields that **don't exist** in Query model:

| Fields Endpoint Tried to Save | Query Model Fields |
|-----|-----|
| `query_type` | ❌ No |
| `status` | ❌ No |
| `entities_found` | ❌ No |
| `answer` | ❌ No |
| `citations` | ❌ No |
| **Query Model Has** | **Endpoints Should Use** |
| `query_mode` | ✅ Maps from query_type |
| `response` | ✅ Maps from answer |
| `reasoning_chain` | ✅ Maps from context |
| `confidence_score` | ✅ New field |
| `user_id` (required) | ⚠️ Was missing |

### Issue 2: Missing API Key Configuration
File: `backend/app/services/llm_service.py` line 22
- Called `genai.configure(api_key=settings.GOOGLE_API_KEY)` without checking if key exists
- When `GOOGLE_API_KEY` is None, Google SDK throws error
- No fallback or graceful handling

---

## Solutions Applied ✅

### Fix 1: Update Query Endpoint to Use Correct Schema

**File**: `backend/app/api/endpoints/queries.py`

**Changes**:
- Line 45-46: Added `user_id` and `document_id` extraction from request
- Line 49-50: Added validation for required `user_id`
- Line 62: Changed `Query()` initialization to use correct fields
- Lines 62-69: Map result fields to Query model fields:
  - `query_type` → `query_mode`
  - `answer` → `response`  
  - `context` → `reasoning_chain`
  - Added `user_id` and `document_id`
- Line 101-121: Updated all GET endpoints to return `query_mode` and `response`
- Line 143-150: Fixed query results endpoint

**Before**:
```python
db_query = Query(
    query_text=query_text,
    query_type=result.get("query_type", "unknown"),      # ❌ Doesn't exist
    status=result["status"],                              # ❌ Doesn't exist
    entities_found=result.get("entities_found", []),      # ❌ Doesn't exist
    answer=result.get("answer", ""),                      # ❌ Doesn't exist
    citations=result.get("citations", []),                # ❌ Doesn't exist
)
```

**After**:
```python
db_query = Query(
    user_id=user_id,                                      # ✅ Required
    document_id=document_id,                              # ✅ Optional
    query_text=query_text,                                # ✅ Correct
    response=result.get("answer", ""),                    # ✅ Maps answer→response
    reasoning_chain=str(result.get("context", "")),       # ✅ Maps context→reasoning_chain
    query_mode=result.get("query_type", "unknown"),       # ✅ Maps query_type→query_mode
    confidence_score=result.get("confidence_score", "0.0"),  # ✅ New field
)
```

### Fix 2: Graceful API Key Configuration

**File**: `backend/app/services/llm_service.py` lines 22-26

**Changes**:
- Check if `GOOGLE_API_KEY` exists before calling `genai.configure()`
- Log warning if API key not provided
- Prevent hard crash on startup

**Before**:
```python
genai.configure(api_key=settings.GOOGLE_API_KEY)  # ❌ Fails if None
```

**After**:
```python
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)
else:
    logger.warning("GOOGLE_API_KEY not configured...")
```

### Fix 3: Enhanced Error Handling

**File**: `backend/app/services/llm_service.py` lines 43-54

- Added detection for API key errors in retry logic
- Provide helpful error message with link to get API key
- Raise immediately instead of retrying on API key errors

**File**: `backend/app/config.py` lines 56-65

- Added `_validate_critical_settings()` method
- Called during initialization to warn about missing GOOGLE_API_KEY
- Shows how to get API key and where to set it

**File**: `backend/app/services/query_service.py` lines 115-189

- Added `query_type` to initial result dict
- Added `confidence_score` to result
- Better error messages when classification fails
- Log full exception with `exc_info=True`

---

## Configuration Required ⚠️

To make query endpoint work, set `GOOGLE_API_KEY`:

### Option 1: Create `.env` file in backend/
```
cd backend
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

### Option 2: Set Environment Variable
**Windows PowerShell**:
```powershell
$env:GOOGLE_API_KEY="your_api_key_here"
```

**Linux/Mac**:
```bash
export GOOGLE_API_KEY="your_api_key_here"
```

### Option 3: Docker Compose
Edit `docker-compose.yml`:
```yaml
services:
  backend:
    environment:
      - GOOGLE_API_KEY=your_api_key_here
```

### Get Your API Key:
1. Visit: https://ai.google.dev/
2. Click "Get API Key"
3. Create new API key in Google Cloud Console
4. Copy and use it

---

## Testing ✅

### Test with curl:
```bash
curl -X POST http://localhost:8000/api/queries \
  -H "Content-Type: application/json" \
  -d '{
    "query": "what is the problem?",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "document_id": "550e8400-e29b-41d4-a716-446655440001"
  }'
```

### Expected Response (Success):
```json
{
  "query": "what is the problem?",
  "status": "success",
  "query_type": "EXPLORATORY",
  "entities_found": ["problem"],
  "context": "...",
  "answer": "Based on the knowledge graph...",
  "citations": ["problem (CONCEPT)"],
  "confidence_score": "0.85",
  "error": null,
  "id": "550e8400-e29b-41d4-a716-446655440002"
}
```

---

## Files Modified 📝

1. `backend/app/api/endpoints/queries.py` - Fixed schema mapping
2. `backend/app/services/llm_service.py` - Added API key validation
3. `backend/app/services/query_service.py` - Better error handling
4. `backend/app/config.py` - Added settings validation
5. `QUICKFIX_CHECKLIST.md` - Updated with fix guide

---

## Verification Checklist

- [x] Query model schema mismatch fixed
- [x] All endpoints use correct fields
- [x] API key configuration is graceful
- [x] Better error messages added
- [x] No linter errors
- [ ] GOOGLE_API_KEY environment variable set (USER ACTION REQUIRED)
- [ ] Backend restarted with new config
- [ ] Query endpoint tested successfully
