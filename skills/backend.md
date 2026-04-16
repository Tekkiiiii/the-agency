---
name: backend
description: >
  Backend architecture and implementation — establishes patterns for REST API
  design, authentication, database access, error handling, and deployment
  configuration. Trigger when: building backend services from scratch,
  reviewing existing backend architecture, or setting up backend infrastructure.
  Key capability: architecture patterns consistent with gstack conventions,
  including auth patterns, middleware, and database connection management.
  Also for: backend code review, performance analysis, and scaling decisions.
---

# /backend — Backend Architecture

Backend service patterns using REST conventions, auth, and database access.

## When to Activate

Trigger `/backend` when:
- Building backend services from scratch
- Reviewing existing backend architecture
- Setting up backend infrastructure
- Backend code review
- Performance analysis

## API Design Conventions

### REST Resource Naming

```
RESOURCE NAMING — {project}
════════════════════════════════

Rules:
  - Use nouns, not verbs: /users not /getUsers
  - Plural resources: /users not /user
  - Nested resources for relationships: /users/{id}/orders
  - Use query params for filtering: /users?role=admin
  - Version prefix: /api/v1/users

Endpoints:
  GET    /users          List users
  POST   /users          Create user
  GET    /users/{id}     Get user
  PATCH  /users/{id}     Update user
  DELETE /users/{id}     Delete user

  GET    /users/{id}/orders       Get user's orders
  POST   /users/{id}/orders       Create order for user
```

### Request/Response Shapes

```typescript
// Standard success response
interface SuccessResponse<T> {
  data: T;
  meta?: {
    page: number;
    perPage: number;
    total: number;
  };
}

// Standard error response
interface ErrorResponse {
  error: {
    code: string;      // e.g. "USER_NOT_FOUND"
    message: string;  // Human-readable
    details?: any;    // Optional additional context
  };
}

// Pagination
interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    perPage: number;
    total: number;
    totalPages: number;
  };
}
```

### HTTP Status Codes

```
STATUS CODES — {project}
════════════════════════════════

Success:
  200 OK          — Standard success
  201 Created     — Resource created
  204 No Content  — Success with no body (DELETE)

Client errors:
  400 Bad Request     — Invalid input
  401 Unauthorized    — Not authenticated
  403 Forbidden       — Authenticated but not authorized
  404 Not Found       — Resource doesn't exist
  409 Conflict        — State conflict (duplicate, etc.)
  422 Unprocessable   — Validation failed

Server errors:
  500 Internal Server Error — Unexpected error
  503 Service Unavailable   — Degraded or unavailable
```

## Authentication

### Auth Pattern (JWT)

```typescript
// Token structure
interface JWTPayload {
  sub: string;         // User ID
  email: string;
  role: string;
  iat: number;
  exp: number;          // Expiry (15m for access, 7d for refresh)
}

// Auth middleware
async function authMiddleware(req: Request, res: Response, next: NextFunction) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) {
    return res.status(401).json({
      error: { code: 'UNAUTHORIZED', message: 'No token provided' }
    });
  }

  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET!);
    req.user = payload;
    next();
  } catch (err) {
    return res.status(401).json({
      error: { code: 'INVALID_TOKEN', message: 'Token invalid or expired' }
    });
  }
}

// Role-based access
function requireRole(...roles: string[]) {
  return (req: Request, res: Response, next: NextFunction) => {
    if (!roles.includes(req.user.role)) {
      return res.status(403).json({
        error: { code: 'FORBIDDEN', message: 'Insufficient permissions' }
      });
    }
    next();
  };
}
```

### Session Management

```
SESSION PATTERNS — {project}
════════════════════════════════

Short-lived sessions (sensitive ops):
  - Access token: 15 minutes
  - Refresh token: 7 days
  - Rotate on use

Long-lived sessions (remember me):
  - Access token: 24 hours
  - Refresh token: 30 days
  - Strict refresh token rotation

Session storage:
  - Redis for production
  - In-memory for development
```

## Database Access

### Connection Management

```typescript
// Connection pool (Node.js / pg)
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,             // Max connections
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Query helper
async function query<T = any>(
  text: string,
  params?: any[]
): Promise<{ rows: T[]; rowCount: number }> {
  const start = Date.now();
  const result = await pool.query(text, params);
  const duration = Date.now() - start;

  // Log slow queries
  if (duration > 100) {
    console.warn(`Slow query (${duration}ms):`, text);
  }

  return result;
}
```

### Query Patterns

```typescript
// Parameterized queries (always)
const result = await query<User>(
  'SELECT * FROM users WHERE id = $1 AND active = $2',
  [userId, true]
);

// Transaction pattern
async function createOrderWithUser(userId: string, items: Item[]) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    const order = await client.query(
      'INSERT INTO orders (user_id, status) VALUES ($1, $2) RETURNING *',
      [userId, 'pending']
    );

    for (const item of items) {
      await client.query(
        'INSERT INTO order_items (order_id, product_id, quantity) VALUES ($1, $2, $3)',
        [order.rows[0].id, item.productId, item.quantity]
      );
    }

    await client.query('COMMIT');
    return order.rows[0];
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}
```

## Error Handling

### Error Hierarchy

```typescript
// Base application error
class AppError extends Error {
  constructor(
    public code: string,
    message: string,
    public statusCode: number = 500,
    public details?: any
  ) {
    super(message);
    this.name = 'AppError';
  }
}

// Specific errors
class NotFoundError extends AppError {
  constructor(resource: string, id: string) {
    super('NOT_FOUND', `${resource} ${id} not found`, 404);
  }
}

class ValidationError extends AppError {
  constructor(message: string, details?: any) {
    super('VALIDATION_ERROR', message, 422, details);
  }
}

class UnauthorizedError extends AppError {
  constructor(message = 'Unauthorized') {
    super('UNAUTHORIZED', message, 401);
  }
}

// Error handler middleware
function errorHandler(err: Error, req: Request, res: Response, next: NextFunction) {
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      error: {
        code: err.code,
        message: err.message,
        details: err.details,
      },
    });
  }

  // Unknown error — don't leak details
  console.error('Unhandled error:', err);
  return res.status(500).json({
    error: {
      code: 'INTERNAL_ERROR',
      message: 'An unexpected error occurred',
    },
  });
}
```

## Important Rules

- **Parameterized queries only.** Never concatenate user input into SQL.
- **Auth middleware on every protected route.** No exceptions.
- **Error responses are consistent.** Always `{ error: { code, message } }`.
- **Connection pooling in production.** No connection-per-request.
- **Log slow queries.** A query that takes 5s will take 5s for every user.
