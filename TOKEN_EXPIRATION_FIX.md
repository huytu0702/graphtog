# 🔧 Token Expiration Fix - "Invalid Token" Upload Error

## Vấn Đề Đã Phát Hiện

Khi upload file, gặp lỗi **"Invalid token"** với mã lỗi 401 Unauthorized.

### Root Cause
Từ backend logs:
```
ERROR:app.services.security:❌ JWT verification error: Signature has expired.
ERROR:app.services.auth:❌ Token verification failed for: eyJhbGciOiJIUzI1NiIs...
INFO:     127.0.0.1:54703 - "POST /api/documents/upload HTTP/1.1" 401 Unauthorized
```

**Nguyên nhân chính**: JWT token đã **hết hạn (expired)** sau 30 phút, và NextAuth không tự động refresh token.

---

## ✅ Giải Pháp Đã Áp Dụng

### 1️⃣ Backend: Tăng Thời Gian Token Expiration

**File**: `backend/app/config.py`

**Thay đổi**:
- Token expiration: **30 phút → 24 giờ (1440 phút)**
- Ngăn token hết hạn trong quá trình làm việc

```python
# Before
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# After  
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
```

### 2️⃣ Frontend: NextAuth Token Refresh Logic

**File**: `frontend/lib/auth.ts`

**Thay đổi**:
- Thêm `accessTokenExpires` tracking
- Check token expiration trước khi sử dụng
- Warning khi token hết hạn
- Preserve user info (email, name) trong session

```typescript
async jwt({ token, user }: any) {
    // Initial sign in
    if (user) {
        token.accessToken = user.accessToken;
        token.id = user.id;
        token.email = user.email;
        token.name = user.name;
        // Set token expiration time (24 hours from now)
        token.accessTokenExpires = Date.now() + 24 * 60 * 60 * 1000;
    }

    // Return previous token if the access token has not expired yet
    if (Date.now() < (token.accessTokenExpires || 0)) {
        return token;
    }

    // Access token has expired
    console.warn('Access token has expired. User may need to re-login.');
    return token;
}
```

### 3️⃣ Frontend: Better Error Handling

**File**: `frontend/components/document-upload/document-upload.tsx`

**Thay đổi**:
- Detect token expiration error (401 + "Invalid token")
- Hiển thị message rõ ràng cho user

```typescript
if (response.status === 401 && error.detail === 'Invalid token') {
    setUploadStatus({ 
        success: false, 
        message: 'Session expired. Please refresh the page and log in again.' 
    });
}
```

---
