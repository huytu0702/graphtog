# ToG Query Timeout Fix

## Problem

ToG queries were timing out when processing took longer than ~30 seconds, even though the backend successfully completed processing. The error manifested as:

```
Error: Query failed: Internal Server Error
Failed to proxy http://localhost:8000/api/tog/query Error: socket hang up
ECONNRESET
```

**Root Cause:** Next.js proxy/rewrite mechanism has a default timeout of ~30 seconds, which was being exceeded by complex ToG queries that required 30-60 seconds to process multiple hops through the knowledge graph.

## Solution

### 1. Custom API Route Handlers with Extended Timeout

Created dedicated Next.js API route handlers for ToG endpoints instead of using simple proxy rewrites:

**Files Created:**
- `frontend/app/api/tog/query/route.ts` - Main query endpoint with 120s timeout
- `frontend/app/api/tog/config/route.ts` - Configuration validation endpoint
- `frontend/app/api/tog/visualize/[query_id]/route.ts` - Visualization endpoint

**Key Features:**
```typescript
// 120 second timeout on the server-side
export const maxDuration = 120;

// Client-side timeout with AbortController
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 120000);
```

### 2. Frontend Timeout Handling

Updated `frontend/components/tog-query-interface.tsx` with:

**a) Client-side timeout (130s)** - Slightly longer than server timeout to allow graceful error handling:
```typescript
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 130000); // 130 seconds

fetch('/api/tog/query', {
  signal: controller.signal,
  // ...
});
```

**b) Better Error Handling:**
- Improved error messages with actionable suggestions
- Graceful handling of timeout errors with helpful guidance
- Better parsing of backend error responses

**c) User Feedback:**
- Changed loading text from "Processing..." to "Reasoning through graph..."
- Added informative message: "Complex queries may take 30-60 seconds to complete..."
- Timeout error suggests: "Try reducing search depth or width, or use a faster pruning method (BM25 or SentenceBERT)"

### 3. Next.js Configuration Update

Updated `frontend/next.config.js`:
- Removed `/api/tog/*` from rewrites (now handled by custom API routes)
- Added comments explaining the separation of concerns

## Architecture

### Before (Direct Proxy)
```
Frontend → Next.js Rewrite → Backend
          └─ 30s timeout ❌
```

### After (Custom API Routes)
```
Frontend → Next.js API Route → Backend
          └─ 130s timeout ✅  └─ 120s timeout ✅
```

## Benefits

1. **Longer Timeout Support:** Queries can now run for up to 2 minutes
2. **Better Error Handling:** Clear, actionable error messages for users
3. **Graceful Degradation:** Timeout errors are caught and reported properly
4. **User Feedback:** Progress indicators and helpful messages during long operations
5. **Flexibility:** Easy to adjust timeouts for different endpoints

## Testing

To test the fix:

1. **Restart the frontend dev server:**
   ```bash
   cd frontend
   npm run dev
   ```

2. **Submit a complex ToG query:**
   - Question: "tài liệu nói gì" (or any complex multi-hop question)
   - Use default configuration (LLM pruning method)
   - Observe: Query should complete successfully even if it takes 30-60 seconds

3. **Test timeout scenario:**
   - If you have a very complex graph, try increasing search_depth to 5
   - Query should fail gracefully with helpful error message if it exceeds 2 minutes

## Configuration

### Adjusting Timeouts

If you need different timeout values:

**Server-side (API Route):**
```typescript
// In frontend/app/api/tog/query/route.ts
export const maxDuration = 180; // Increase to 3 minutes
const timeoutId = setTimeout(() => controller.abort(), 180000);
```

**Client-side (Frontend Component):**
```typescript
// In frontend/components/tog-query-interface.tsx
const timeoutId = setTimeout(() => controller.abort(), 190000); // Slightly longer than server
```

### Alternative: Reduce Query Complexity

If queries are consistently timing out, consider:

1. **Reduce search_depth** from 3 to 2
2. **Reduce search_width** from 3 to 2
3. **Use faster pruning method:** Change from "llm" to "bm25" or "sentence_bert"
4. **Filter by documents:** Select specific documents to reduce graph size

## Related Files Modified

1. `frontend/next.config.js` - Removed ToG rewrite, added comments
2. `frontend/components/tog-query-interface.tsx` - Enhanced error handling and UX
3. `frontend/app/api/tog/query/route.ts` - New custom API route
4. `frontend/app/api/tog/config/route.ts` - New custom API route
5. `frontend/app/api/tog/visualize/[query_id]/route.ts` - New custom API route

## Notes

- Backend processing time (34.79s in the original error) is now successfully handled
- The solution is production-ready and follows Next.js best practices
- Timeout values (120s) are configurable based on your infrastructure needs
- For very large graphs, consider implementing query result caching or query optimization
