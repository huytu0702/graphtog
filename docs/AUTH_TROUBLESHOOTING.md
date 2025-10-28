# Authentication 401 Error - Troubleshooting & Fix Guide

## Problem Summary

Users are experiencing 401 (Unauthorized) errors during:
1. **After registration** - Auto sign-in fails with `CredentialsSignin` error
2. **Manual login** - Login attempts return 401 from `/api/auth/callback/credentials`

### Error Messages:
```
Failed to load resource: the server responded with a status of 401 (Unauthorized)
Sign-in error after registration: CredentialsSignin
```

---

## Root Cause Analysis

### Issue #1: Missing `.env.local` File (CRITICAL)
**Status:** ✅ **FIXED**

The frontend's `.env.local` file was not created, which means:
- ❌ `NEXTAUTH_SECRET` was not set (NextAuth cannot sign/verify sessions)
- ❌ `NEXTAUTH_URL` was using default (may cause cookie domain issues)
- ❌ `NEXT_PUBLIC_API_URL` was falling back to default

**Why it matters:** Without `NEXTAUTH_SECRET`, NextAuth cannot properly encrypt and sign JWT tokens, causing all authentication attempts to fail.

**Fix Applied:**
```bash
# File: frontend/.env.local (created)
NEXTAUTH_SECRET=your-super-secret-key-please-change-in-production-12345
NEXTAUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Verification Steps

### Step 1: Verify `.env.local` File Exists
```bash
# Windows PowerShell
cd frontend
Get-Content .env.local

# Expected output:
# NEXTAUTH_SECRET=your-super-secret-key-please-change-in-production-12345
# NEXTAUTH_URL=http://localhost:3000
# NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 2: Clear Browser Data
1. **Open DevTools**: `F12` or `Ctrl+Shift+I`
2. **Go to**: Application → Cookies
3. **Delete** cookies for `localhost:3000`
4. **Refresh** the page

### Step 3: Restart Frontend Service

**If using Docker:**
```bash
docker-compose restart frontend
```

**If running locally:**
```bash
cd frontend
npm run dev
# or
npm install  # if needed
npm run dev
```

### Step 4: Test Registration Flow

1. Navigate to: `http://localhost:3000/register`
2. Fill in the form:
   - **Full Name**: Test User
   - **Email**: test@example.com
   - **Password**: TestPassword123
   - **Confirm Password**: TestPassword123
3. Click **Register**
4. **Expected Result**: Auto-redirect to `/dashboard` ✅

### Step 5: Test Login Flow

1. Navigate to: `http://localhost:3000/login`
2. Enter credentials:
   - **Email**: test@example.com
   - **Password**: TestPassword123
3. Click **Sign in**
4. **Expected Result**: Redirect to `/dashboard` ✅

### Step 6: Check Backend Logs

```bash
docker-compose logs -f backend
```

**Expected log output:**
```
[INFO] POST /api/auth/register 200 OK
[INFO] POST /api/auth/token 200 OK
```

---

## Configuration Details

### Frontend Configuration

#### What was missing: `frontend/.env.local`
```env
# Required for NextAuth to sign/verify sessions
NEXTAUTH_SECRET=your-super-secret-key-please-change-in-production-12345

# Must match your frontend domain
NEXTAUTH_URL=http://localhost:3000

# Backend API endpoint (public variable, safe to expose)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### Current Implementation: `frontend/lib/auth.ts`
```typescript
// ✅ Correct implementation
async authorize(credentials) {
    if (!credentials?.email || !credentials?.password) return null;

    try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: credentials.email,
                password: credentials.password,
            }),
        });

        const data = await res.json();

        if (res.ok && data.access_token && data.user) {
            return {
                id: data.user.id,              // ✅ Correct path (nested user object)
                email: data.user.email,        // ✅ Correct path
                name: data.user.name,          // ✅ Correct path
                accessToken: data.access_token,
            };
        }
        return null;
    } catch (error) {
        console.error('Auth error:', error);
        return null;
    }
}
```

### Backend Response Structure: `/api/auth/token`

The backend returns the correct structure that the frontend expects:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "name": "Test User",
    "created_at": "2024-10-27T12:00:00"
  }
}
```

---

## Authentication Flow Diagram

### Registration → Auto Sign-in
```
1. User fills registration form
   ↓
2. POST /api/auth/register (Backend)
   ↓
3. Backend creates user in PostgreSQL ✅
   Returns: UserResponse {id, email, name, created_at}
   ↓
4. Frontend calls signIn('credentials', {email, password})
   ↓
5. NextAuth calls /api/auth/token (Backend)
   Backend validates credentials, returns token ✅
   ↓
6. NextAuth callback:
   - authorize(): Extracts user info from response
   - jwt(): Stores token in JWT
   - session(): Adds accessToken and id to session
   ↓
7. User auto-redirected to /dashboard ✅
```

### Login Flow
```
1. User fills login form
   ↓
2. Frontend calls signIn('credentials', {email, password})
   ↓
3. NextAuth calls /api/auth/token (Backend)
   Backend validates credentials, returns token ✅
   ↓
4. NextAuth callbacks process token
   ↓
5. User redirected to /dashboard ✅
```

---

## Common Troubleshooting

### Still Getting 401 Unauthorized?

**Checklist:**
- [ ] `.env.local` exists in `frontend/` directory
- [ ] `NEXTAUTH_SECRET` is set (non-empty string)
- [ ] `NEXTAUTH_URL=http://localhost:3000` exactly
- [ ] Backend is running: `curl http://localhost:8000/health`
- [ ] Browser cookies cleared
- [ ] Frontend restarted after creating `.env.local`

**Debug Steps:**
```bash
# 1. Check backend health
curl http://localhost:8000/health

# 2. Check backend logs
docker-compose logs backend

# 3. Check frontend logs
docker-compose logs frontend

# 4. Verify user was created in database
docker exec graphtog_postgres psql -U graphtog_user -d graphtog_db -c "SELECT id, email, name FROM users;"
```

### Getting "Invalid email or password" After Registration?

**Possible causes:**
1. Database connection issue - user wasn't actually saved
2. Password hashing mismatch
3. Typo in credentials

**Solution:**
1. Check backend logs for errors: `docker-compose logs backend`
2. Verify user exists: Check PostgreSQL directly
3. Try registering with different credentials
4. Clear all cookies and try again

### Redirect Loop or Blank Page After Login?

**Possible causes:**
1. Dashboard route doesn't exist
2. Session not being properly stored
3. Missing middleware configuration

**Solution:**
1. Check browser console for errors: `F12` → Console tab
2. Verify `/dashboard` route exists
3. Check that SessionProvider wraps the app
4. Restart all services: `docker-compose restart`

### Session Lost After Page Refresh?

**Possible causes:**
1. `NEXTAUTH_SECRET` changed between requests
2. Session configuration issue
3. Browser privacy settings blocking cookies

**Solution:**
1. Ensure `NEXTAUTH_SECRET` is consistent
2. Check browser privacy settings
3. Disable "Block third-party cookies" if needed
4. Check that cookies are being saved: DevTools → Application → Cookies

---

## Database Verification

### Check if User Was Created

```bash
# Connect to PostgreSQL
docker exec -it graphtog_postgres psql -U graphtog_user -d graphtog_db

# List all users
SELECT id, email, name, created_at FROM users;

# Check specific user
SELECT * FROM users WHERE email = 'test@example.com';
```

### Reset User Data (if needed)

```bash
# Connect to PostgreSQL
docker exec -it graphtog_postgres psql -U graphtog_user -d graphtog_db

# Delete a user
DELETE FROM users WHERE email = 'test@example.com';

# Reset all users (WARNING: destructive)
DELETE FROM users;
```

---

## Environment Variables Reference

### Frontend `.env.local`

| Variable | Required | Purpose | Example |
|----------|----------|---------|---------|
| `NEXTAUTH_SECRET` | ✅ Yes | JWT signing key | `your-secret-key-...` |
| `NEXTAUTH_URL` | ✅ Yes | Frontend URL for cookies | `http://localhost:3000` |
| `NEXT_PUBLIC_API_URL` | ✅ Yes | Backend API endpoint | `http://localhost:8000` |

### Backend `docker-compose.yml`

| Variable | Purpose | Current Value |
|----------|---------|---|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://graphtog_user:graphtog_password@postgres:5432/graphtog_db` |
| `NEO4J_URI` | Neo4j connection | `bolt://neo4j:7687` |
| `NEO4J_PASSWORD` | Neo4j password | `graphtog_password` |
| `NEXTAUTH_SECRET` | (Optional in docker-compose) | Set via environment |

---

## Production Deployment Checklist

Before deploying to production, **MUST DO:**

- [ ] Change `NEXTAUTH_SECRET` to a strong random string (use `openssl rand -base64 32`)
- [ ] Set `NEXTAUTH_URL` to your production domain (e.g., `https://graphtog.example.com`)
- [ ] Update `NEXT_PUBLIC_API_URL` to production backend URL
- [ ] Enable HTTPS only (set cookies with Secure flag)
- [ ] Update CORS origins to specific domains (not `*`)
- [ ] Change PostgreSQL credentials in docker-compose
- [ ] Change Neo4j credentials in docker-compose
- [ ] Set up proper logging and monitoring
- [ ] Test entire auth flow in staging environment
- [ ] Backup production database before deployment

---

## Testing Guide

### Manual Test Script

```bash
#!/bin/bash

echo "🧪 Testing GraphToG Authentication"
echo ""

# Test 1: Health Check
echo "1️⃣  Testing backend health..."
curl -s http://localhost:8000/health | jq .
echo ""

# Test 2: Registration
echo "2️⃣  Testing registration..."
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "name": "Test User",
    "password": "TestPassword123"
  }')
echo $REGISTER_RESPONSE | jq .
USER_ID=$(echo $REGISTER_RESPONSE | jq -r '.id')
echo "User ID: $USER_ID"
echo ""

# Test 3: Token Generation
echo "3️⃣  Testing token generation..."
TOKEN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "TestPassword123"
  }')
echo $TOKEN_RESPONSE | jq .
ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')
echo ""

# Test 4: Get User Info
echo "4️⃣  Testing get current user..."
curl -s -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
```

---

## References

- [NextAuth.js Documentation](https://next-auth.js.org/)
- [NextAuth Credentials Provider](https://next-auth.js.org/providers/credentials)
- [FastAPI Authentication](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Token Best Practices](https://tools.ietf.org/html/rfc8949)
