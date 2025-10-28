# Authentication and File Upload Fix

## Issues Fixed

### 1. Registration Auto-Login Error (403 Forbidden)
**Problem**: After successful registration, the automatic sign-in failed with a connection error:
```
Auth error: TypeError: fetch failed
cause: Error: connect ECONNREFUSED ::1:8000
```

**Root Cause**: NextAuth's `authorize` function runs server-side (inside the frontend Docker container), but was trying to use `NEXT_PUBLIC_API_URL` which is meant for client-side (browser) requests. When set to `http://backend:8000`, browsers couldn't access it. When not set, it defaulted to `http://localhost:8000`, causing IPv6 connection errors.

**Solution**: 
- Added separate `API_URL` environment variable for server-side requests
- Updated `docker-compose.yml`:
  ```yaml
  environment:
    - NEXT_PUBLIC_API_URL=http://localhost:8000  # Browser requests
    - API_URL=http://backend:8000                 # Server-side requests
  ```
- Updated `frontend/lib/auth.ts` to prioritize `API_URL` for server-side auth

### 2. File Upload Authentication Error (403 Forbidden)
**Problem**: After successful login, uploading documents failed with:
```
INFO: 172.18.0.1:60318 - "POST /api/documents/upload HTTP/1.1" 403 Forbidden
frontend log: Not authenticated
```

**Root Cause**: The frontend components were not sending the JWT access token in the `Authorization` header when making API requests to the backend.

**Solution**: Updated all API-calling components to include the Bearer token:

#### Files Modified:
1. **`frontend/components/document-upload/document-upload.tsx`**
   - Added `accessToken` prop
   - Included `Authorization: Bearer ${accessToken}` header in upload request

2. **`frontend/app/(dashboard)/documents/page.client.tsx`**
   - Extracted `accessToken` from session
   - Passed token to `DocumentUpload` component
   - Added authorization header to `fetchDocuments` request

3. **`frontend/components/query-interface.tsx`**
   - Added `accessToken` prop
   - Included authorization header in query requests

4. **`frontend/app/(dashboard)/query/page.tsx`**
   - Converted to client component
   - Added session management
   - Extracted and passed `accessToken` to `QueryInterface`

## How It Works Now

### Authentication Flow:
1. **Registration/Login** → Backend returns JWT access token
2. **NextAuth Session** → Stores token in session via JWT callback
3. **API Requests** → Frontend includes token in Authorization header
4. **Backend Validation** → Verifies token and authorizes request

### Environment Variables:
- **`NEXT_PUBLIC_API_URL`**: Used by browser for client-side API calls
- **`API_URL`**: Used by Next.js server for server-side API calls (NextAuth)
- **`NEXTAUTH_SECRET`**: Secret for signing NextAuth tokens
- **`GOOGLE_API_KEY`**: Google Gemini API key for LLM operations

## Testing

### To Test the Fix:
1. **Rebuild and restart containers**:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

2. **Register a new user**:
   - Go to http://localhost:3000/register
   - Fill in the form and submit
   - Should automatically log in and redirect to dashboard ✅

3. **Upload a document**:
   - Go to Documents page
   - Drag and drop a .md file
   - Should upload successfully ✅

4. **Query documents**:
   - Go to Query page
   - Ask a question
   - Should receive an answer ✅

## Environment Setup

Create a `.env` file in the project root (see `.env.example`):
```bash
GOOGLE_API_KEY=your_google_api_key_here
NEXTAUTH_SECRET=your_secret_key_here
```

## Technical Details

### JWT Token Flow:
```
1. User logs in → POST /api/auth/token
2. Backend validates credentials → Returns JWT + user data
3. NextAuth stores in session:
   {
     user: {
       id, email, name,
       accessToken: "JWT_TOKEN_HERE"
     }
   }
4. Frontend extracts token:
   const accessToken = (session?.user as any)?.accessToken;
5. Frontend includes in requests:
   headers: { Authorization: `Bearer ${accessToken}` }
6. Backend validates:
   HTTPBearer → verify_token() → get_current_user()
```

### Docker Networking:
- **Browser → Backend**: Uses `localhost:8000` (port mapping)
- **Frontend Container → Backend**: Uses `backend:8000` (internal network)
- **NextAuth (server-side)**: Uses `API_URL` for internal network communication

## Files Changed
- `docker-compose.yml` - Added `API_URL` environment variable
- `frontend/lib/auth.ts` - Use server-side API URL
- `frontend/components/document-upload/document-upload.tsx` - Pass auth token
- `frontend/app/(dashboard)/documents/page.client.tsx` - Extract and pass token
- `frontend/components/query-interface.tsx` - Include auth header
- `frontend/app/(dashboard)/query/page.tsx` - Session management
- `.env.example` - Documentation for required environment variables

## Next Steps
- Test all authenticated endpoints
- Ensure proper error handling for expired tokens
- Consider implementing token refresh mechanism
- Add loading states for authentication checks

