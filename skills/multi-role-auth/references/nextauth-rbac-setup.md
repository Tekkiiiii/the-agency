# NextAuth v5 RBAC Setup Reference

## Auth.js (NextAuth v5) Role Flow

1. Credentials provider: email + bcrypt-hashed password
2. Authorize → verify → return user with role
3. JWT callback: embed role in token
4. Session callback: expose role in session
5. Middleware: protect /admin, /guest routes
6. Client: `useSession()` → `(session.user as any).role`

## Middleware Route Protection

```typescript
// middleware.ts
export default auth((req) => {
  const token = req.auth;
  const path = req.nextUrl.pathname;

  if (path.startsWith('/admin') && token?.role !== 'ADMIN' && token?.role !== 'OWNER') {
    return Response.redirect(new URL('/unauthorized', req.url));
  }

  return NextAuth();
});
```

## Environment Variables

```
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=openssl rand -base64 32
```
