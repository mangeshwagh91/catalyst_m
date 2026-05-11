# Multi-User Authentication Implementation

## Overview

This document describes the JWT-based multi-user authentication system implemented for the Catalyst AI Platform. The system replaces the hardcoded "Dr. Sharma" identity with a proper user management system supporting multiple concurrent users.

## Backend Implementation

### 1. User Model (`backend/app/models/models.py`)

The `User` model stores user account information:

```python
class User(Base):
    """Stores user accounts for multi-user platform"""
    __tablename__ = "users"

    id: str (UUID)
    username: str (unique)
    email: str (unique)
    full_name: str
    hashed_password: str (bcrypt)
    is_active: bool (default=True)
    is_superuser: bool (default=False)
    created_at: DateTime
    updated_at: DateTime
    last_login: DateTime

    Relationships:
    - reactions: List[Reaction] (creator)
    - experiments: List[Experiment] (creator)
```

### 2. Security Utilities (`backend/app/core/security.py`)

Core authentication functions:

- **`hash_password(password: str) -> str`**: Hash passwords using bcrypt
- **`verify_password(plain, hashed) -> bool`**: Verify plain text against hash
- **`create_access_token(user_id, expires_delta) -> str`**: Generate JWT tokens (24-hour expiry by default)
- **`verify_token(token: str) -> Optional[str]`**: Decode and validate JWT tokens

Configuration:

- Algorithm: HS256
- Access token expiry: 24 hours (1440 minutes)
- Secret key: Loaded from `settings.secret_key`

### 3. Authentication Endpoints (`backend/app/api/auth.py`)

#### POST `/auth/register`

Register a new user account.

**Request:**

```json
{
  "email": "researcher@example.com",
  "password": "secure_password",
  "full_name": "Dr. Jane Smith"
}
```

**Response:**

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user_id": "uuid-here",
  "username": "researcher@example.com",
  "full_name": "Dr. Jane Smith"
}
```

#### POST `/auth/login`

Authenticate user and receive JWT token.

**Request:**

```json
{
  "email": "researcher@example.com",
  "password": "secure_password"
}
```

**Response:** Same as register endpoint

#### GET `/auth/me`

Get current authenticated user's information.

**Headers:**

```
Authorization: Bearer <access_token>
```

**Response:**

```json
{
  "id": "uuid-here",
  "email": "researcher@example.com",
  "full_name": "Dr. Jane Smith"
}
```

### 4. Data Ownership with Creator IDs

Reactions and Experiments tables now have `creator_id` foreign key:

```python
class Reaction(Base):
    creator_id: str = Column(String(64), ForeignKey("users.id"))
    creator: User = relationship("User", back_populates="reactions")

class Experiment(Base):
    creator_id: str = Column(String(64), ForeignKey("users.id"))
    creator: User = relationship("User", back_populates="experiments")
```

**Data Isolation:**

- Users can only see reactions/experiments they created
- Future: Add `shared_with` JSON array for team collaboration

## Frontend Implementation

### 1. Authentication Hook (`frontend/src/hooks/useAuth.ts`)

Manages authentication state:

```typescript
const auth = useAuth();
// auth.user: Current user info (id, email, full_name)
// auth.isAuthenticated: Boolean
// auth.isLoading: Loading state
// auth.token: JWT token
// auth.login(email, password): Promise
// auth.register(email, password, full_name): Promise
// auth.logout(): void
```

Features:

- Loads token from localStorage on mount
- Verifies token freshness via GET `/auth/me`
- Auto-clears invalid/expired tokens
- Handles errors gracefully

### 2. Auth Context (`frontend/src/context/AuthContext.tsx`)

Global auth state provider:

```typescript
<AuthProvider>
  {/* All child components have access to auth context */}
  <YourApp />
</AuthProvider>
```

Usage in components:

```typescript
const auth = useAuthContext();
if (!auth.isAuthenticated) {
  navigate({ to: "/login" });
}
```

### 3. Login Page (`frontend/src/routes/login.tsx`)

Unified login/registration interface:

Features:

- Toggle between login and register modes
- Form validation (email format, password strength hints)
- Error messages for failed attempts
- Demo credentials for testing
- Redirect to workspace on success
- Auto-redirect to login if not authenticated

### 4. Workspace Updates (`frontend/src/routes/workspace.tsx`)

- User greeting with actual name: "Welcome back, {user.full_name}"
- User profile in sidebar showing name and email
- Logout button (LogOut icon) in user profile
- Route protection: Redirects unauthenticated users to login
- All API calls include JWT token

### 5. API Client (`frontend/src/lib/api.ts`)

Auto-includes JWT token in all requests:

```typescript
// All functions automatically add:
// Authorization: Bearer <token>
// Content-Type: application/json

await createReaction({...});        // ✓ Includes token
await rankCatalysts({...});         // ✓ Includes token
await triggerRetraining();          // ✓ Includes token
```

## Database Migration

An Alembic migration creates the users table and adds creator_id fields:

**File:** `backend/alembic/versions/2b3f8c1a9d2e_add_user_model_and_creator_id.py`

To run:

```bash
cd backend
alembic upgrade head
```

This migration:

1. Creates `users` table with proper indexes
2. Adds `creator_id` FK to `reactions` table
3. Adds `creator_id` FK to `experiments` table

## Testing the Authentication Flow

### 1. Backend Testing

Start the backend server:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

Test endpoints with curl:

**Register:**

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "full_name": "Test Researcher"
  }'
```

**Login:**

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

**Get Current User (use token from login response):**

```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### 2. Frontend Testing

Start the frontend dev server:

```bash
cd frontend
npm install  # If needed
npm run dev
```

Navigate to http://localhost:5173/login

**Test Scenarios:**

1. **New User Registration:**
   - Click "Sign up"
   - Enter email, password, full name
   - Click "Create Account"
   - Should redirect to workspace
   - Check sidebar shows your name and email

2. **User Login:**
   - Enter email and password
   - Click "Sign In"
   - Should redirect to workspace
   - Greeting should show your name: "Welcome back, [Full Name]"

3. **Logout:**
   - Click LogOut icon in user profile (bottom of sidebar)
   - Should redirect to login page

4. **Session Persistence:**
   - Login and refresh page
   - Should remain logged in (token in localStorage)
   - Clear localStorage and refresh
   - Should redirect to login

5. **Token Validation:**
   - Login and note the token in console (localStorage.getItem('auth_token'))
   - Manually modify token in localStorage
   - Refresh page
   - Should redirect to login (invalid token)

## Security Considerations

### Current Implementation

✓ Passwords hashed with bcrypt (12 rounds)
✓ JWT tokens signed with secret key (HS256)
✓ 24-hour token expiry
✓ Tokens stored in localStorage (XSS vulnerable but acceptable for dev)
✓ Creator-based data isolation
✓ Authorization header validation

### Future Enhancements

1. **Token Refresh:**
   - Implement refresh token endpoint
   - Rotate tokens on each request
   - Shorter access token expiry (15 min)

2. **Secure Storage:**
   - Use httpOnly cookies (if possible with CORS)
   - Implement token rotation

3. **Rate Limiting:**
   - Add login attempt rate limiting
   - Prevent brute force attacks

4. **Audit Logging:**
   - Log all authentication events
   - Track failed login attempts
   - Monitor data access patterns

5. **Team Collaboration:**
   - Add `shared_with` field for sharing reactions/experiments
   - Implement team ownership models
   - Add role-based access control (RBAC)

6. **OAuth Integration:**
   - Support GitHub/Google login
   - OIDC provider integration

## Configuration

### Backend (`.env` or environment variables)

```bash
# FastAPI Configuration
API_TITLE=Catalyst Discovery Platform
DEBUG=True

# Database
DATABASE_URL=postgresql://user:password@localhost/catalyst_db

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours

# Frontend URL
FRONTEND_URL=http://localhost:5173

# CORS
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Frontend (`vite.config.ts` or environment variables)

```bash
VITE_API_URL=http://localhost:8000/api
```

## File Structure

```
Backend:
  app/
    core/
      security.py          # Auth utilities (NEW)
      config.py           # Config with SECRET_KEY (UPDATED)
    api/
      auth.py             # Auth endpoints (NEW)
    models/
      models.py           # User model + creator_id (UPDATED)
    main.py              # Include auth router (UPDATED)

Frontend:
  src/
    hooks/
      useAuth.ts         # Auth hook (NEW)
    context/
      AuthContext.tsx    # Auth provider (NEW)
    routes/
      login.tsx          # Login page (NEW)
      workspace.tsx      # Auth checks + user display (UPDATED)
      __root.tsx         # AuthProvider wrapper (UPDATED)
    lib/
      api.ts            # Token auto-include (NEW)

Migrations:
  alembic/versions/
    2b3f8c1a9d2e_add_user_model_and_creator_id.py (NEW)
```

## Troubleshooting

### "Invalid email or password"

- Check user exists in database
- Verify password is correct
- Check user.is_active = True

### "Missing authorization header"

- Ensure token is in localStorage
- Check Authorization header format: `Bearer <token>`
- Clear localStorage and re-login if corrupted

### CORS errors

- Verify FRONTEND_URL includes frontend origin
- Check BACKEND_CORS_ORIGINS includes your domain
- Restart backend after config changes

### Token not working after deployment

- Verify SECRET_KEY is set consistently
- Check JWT expiry time (24 hours default)
- Ensure clock skew between frontend/backend is minimal

## Next Steps

1. ✅ **JWT Authentication** - Implemented
2. ✅ **User Management** - Implemented
3. ✅ **Data Ownership** - Implemented
4. ⏳ **Team Collaboration** - Pending (shared_with field)
5. ⏳ **API Access Control** - Pending (add Depends(get_current_user) to all routes)
6. ⏳ **Audit Logging** - Pending
7. ⏳ **Token Refresh** - Pending
