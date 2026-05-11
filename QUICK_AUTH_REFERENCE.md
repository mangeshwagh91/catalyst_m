# Quick Reference: Multi-User Authentication

## For Backend Developers

### Adding Authentication to New Endpoints

**Before:** All API routes are public

```python
@router.post("/api/my-endpoint")
async def my_endpoint(data: MyRequest, db: Session = Depends(get_db)):
    return {...}
```

**After:** Protected with JWT

```python
from app.api.auth import get_current_user_from_token

@router.post("/api/my-endpoint")
async def my_endpoint(
    data: MyRequest,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    # Filter data by creator_id
    items = db.query(MyModel).filter(MyModel.creator_id == current_user.id).all()
    return {...}
```

### Environment Variables (Backend)

```bash
# .env file
SECRET_KEY=change-me-in-production-12345
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ALGORITHM=HS256
```

### Testing Authenticated Routes

```bash
# 1. Login to get token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"pass"}' \
  | jq -r '.access_token')

# 2. Use token in requests
curl -X GET http://localhost:8000/api/my-endpoint \
  -H "Authorization: Bearer $TOKEN"
```

## For Frontend Developers

### Using Auth in Components

```typescript
import { useAuthContext } from '../context/AuthContext';

export function MyComponent() {
  const auth = useAuthContext();

  // Check authentication
  if (auth.isLoading) return <div>Loading...</div>;
  if (!auth.isAuthenticated) return <div>Please log in</div>;

  // Use user info
  return (
    <div>
      <h1>Hello, {auth.user?.full_name}</h1>
      <p>Email: {auth.user?.email}</p>
      <button onClick={() => {
        auth.logout();
        navigate({ to: '/login' });
      }}>
        Logout
      </button>
    </div>
  );
}
```

### Making Authenticated API Calls

All API functions in `lib/api.ts` automatically include the token:

```typescript
import { listReactions, createReaction } from "../lib/api";

// Token is automatically included in headers
const reactions = await listReactions();
const newReaction = await createReaction({
  name: "CO2 → Methanol",
  reactants: ["CO2", "H2"],
  products: ["CH3OH"],
});
```

### Protecting Routes

```typescript
import { useAuthContext } from '../context/AuthContext';
import { useNavigate } from '@tanstack/react-router';

export function ProtectedComponent() {
  const auth = useAuthContext();
  const navigate = useNavigate();

  // Auto-redirect if not authenticated
  if (!auth.isLoading && !auth.isAuthenticated) {
    navigate({ to: '/login' });
  }

  return <div>Protected content</div>;
}
```

### Login/Register

```typescript
const auth = useAuthContext();

// Register new user
await auth.register("user@example.com", "password", "Full Name");

// Login existing user
await auth.login("user@example.com", "password");

// Logout
auth.logout();
```

### Environment Variables (Frontend)

```bash
# .env.local
VITE_API_URL=http://localhost:8000/api
```

## Common Tasks

### Task: Create a Private Reaction

**Before:** No owner tracking

```typescript
await createReaction({name: "CO2 → Methanol", ...});
// Anyone can see this
```

**After:** Automatically owned by current user

```typescript
const auth = useAuthContext();
await createReaction({name: "CO2 → Methanol", ...});
// Only {auth.user.id} can see this
// Backend: reaction.creator_id = current_user_id
```

### Task: Load User's Own Experiments

```typescript
// lib/api.ts
export async function getUserExperiments(): Promise<any[]> {
  const response = await fetch(`${API_BASE_URL}/experiments/mine`, {
    headers: getHeaders(),
  });
  return handleResponse(response);
}

// In component
const { data: myExperiments } = useQuery({
  queryKey: ["userExperiments"],
  queryFn: getUserExperiments,
});
```

### Task: Share a Reaction with Team

**Coming Soon:** Add `shared_with` field

```typescript
// Future API
await shareReaction(reactionId, ["user2@example.com", "user3@example.com"]);
// Adds user IDs to shared_with array
// Now those users can see and use the reaction
```

### Task: Add Logout Button

```typescript
import { LogOut } from 'lucide-react';
import { useAuthContext } from '../context/AuthContext';
import { useNavigate } from '@tanstack/react-router';

export function LogoutButton() {
  const auth = useAuthContext();
  const navigate = useNavigate();

  return (
    <button
      onClick={() => {
        auth.logout();
        navigate({ to: '/login' });
      }}
      className="flex items-center gap-2"
    >
      <LogOut className="h-4 w-4" />
      Logout
    </button>
  );
}
```

## Database Queries

### Find user and their reactions

```python
from sqlalchemy import select
from app.models.models import User, Reaction

user = db.execute(select(User).filter(User.email == "user@example.com")).scalar_one()
reactions = db.execute(
    select(Reaction).filter(Reaction.creator_id == user.id)
).scalars().all()
```

### Create reaction for current user

```python
from app.models.models import Reaction
import uuid

reaction = Reaction(
    id=str(uuid.uuid4()),
    creator_id=current_user.id,  # Link to authenticated user
    name="CO2 → Methanol",
    reactants=["CO2", "H2"],
    products=["CH3OH"],
)
db.add(reaction)
db.commit()
```

### Check user owns experiment

```python
experiment = db.execute(
    select(Experiment).filter(
        Experiment.id == exp_id,
        Experiment.creator_id == current_user.id  # Verify ownership
    )
).scalar_one_or_none()

if not experiment:
    raise HTTPException(status_code=403, detail="Not authorized")
```

## Security Checklist

- [ ] All endpoints that modify data require authentication
- [ ] User can only see data they created (creator_id == current_user.id)
- [ ] Passwords are hashed with bcrypt
- [ ] Tokens expire after 24 hours
- [ ] CORS is configured for your domain
- [ ] SECRET_KEY is set in production (not hardcoded)
- [ ] HTTPS is used in production
- [ ] Invalid tokens are rejected
- [ ] User can logout and token is cleared

## Debugging

### Check if user is authenticated

```typescript
console.log("Auth:", {
  isAuthenticated: auth.isAuthenticated,
  user: auth.user,
  token: localStorage.getItem("auth_token")?.substring(0, 20) + "...",
});
```

### Verify token is valid

```bash
# Decode JWT (online tool: jwt.io)
JWT=<your_token>
# Or use jwt CLI tool
```

### Check API calls include token

```typescript
// Browser DevTools → Network → any API call
// Headers tab → Authorization: Bearer eyJ0eXAi...
```

### Login failed? Check:

1. ✓ Email exists in database
2. ✓ Password is correct
3. ✓ User.is_active = True
4. ✓ Backend is running and accessible
5. ✓ VITE_API_URL is set correctly

## Performance Notes

- Token is validated on every authenticated request (fast, cached in memory)
- User data is loaded once on app mount and cached
- Consider adding token refresh endpoint for long-lived sessions
- Add caching headers to reduce /auth/me calls

## Rollback Plan (If needed)

1. Revert migrations: `alembic downgrade -1`
2. Remove auth routes from main.py
3. Remove AuthProvider from \_\_root.tsx
4. Restore hardcoded user in workspace.tsx
5. Remove auth.py, security.py files
6. Remove User model from models.py
7. Remove creator_id columns from Reaction/Experiment
