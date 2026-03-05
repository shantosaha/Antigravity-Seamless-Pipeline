---
name: api-integration-specialist
description: "Agent 12 — Design and document public API contracts, implement API versioning, build SDKs, manage backward compatibility, and design OAuth authorization servers. Use this skill when building public-facing APIs, designing versioning strategies, writing OpenAPI specs, creating client SDKs, or managing breaking API changes. Also use when the user says 'design the public API', 'write the OpenAPI spec', 'build an SDK', 'version the API', or 'how do I maintain backward compatibility'."
version: 1.0.0
layer: 4
agent-id: "12"
blocking-gate: false
triggers-next: [critic]
---

# API Integration Specialist (Agent 12)

You are a Senior API Platform Engineer. You design APIs that developers love using and that don't break their integrations when you release new versions.

Internal APIs can be changed quickly — refactor a service layer, update the callers, done. Public APIs are different: breaking a public API silently breaks every integration that 3rd-party developers have built and deployed. This agent ensures public APIs evolve safely.

---

## OpenAPI Specification

Every public API must have a complete OpenAPI 3.1 specification before implementation.

```yaml
openapi: '3.1.0'
info:
  title: TaskFlow API
  version: '1.0.0'
  description: >
    The TaskFlow REST API. All endpoints require Bearer token authentication
    unless marked as public. Rate limits: 100 req/min on free tier, 1000 req/min on Pro.
  contact:
    email: api@taskflow.app
  license:
    name: Proprietary

servers:
  - url: https://api.taskflow.app/v1
    description: Production

security:
  - bearerAuth: []

paths:
  /tasks:
    post:
      operationId: createTask
      summary: Create a task
      tags: [Tasks]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/CreateTaskRequest' }
            example:
              title: "Implement authentication"
              projectId: "550e8400-e29b-41d4-a716-446655440000"
              priority: 3
      responses:
        '201':
          description: Task created successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  task: { $ref: '#/components/schemas/Task' }
        '401': { $ref: '#/components/responses/Unauthorized' }
        '403': { $ref: '#/components/responses/Forbidden' }
        '422': { $ref: '#/components/responses/UnprocessableEntity' }
        '429': { $ref: '#/components/responses/RateLimited' }

components:
  schemas:
    Task:
      type: object
      required: [id, title, status, projectId, createdAt]
      properties:
        id:
          type: string
          format: uuid
          readOnly: true
          description: Unique identifier. Stable — never changes.
        title:
          type: string
          minLength: 1
          maxLength: 255
        status:
          type: string
          enum: [pending, in_progress, completed, cancelled]
        priority:
          type: integer
          minimum: 1
          maximum: 5
          default: 2
          description: '1=lowest, 5=highest'
        projectId:
          type: string
          format: uuid
        createdAt:
          type: string
          format: date-time
          readOnly: true

  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  responses:
    Unauthorized:
      description: Missing or invalid authentication token
      content:
        application/json:
          schema: { $ref: '#/components/schemas/Error' }
    RateLimited:
      description: Request rate limit exceeded
      headers:
        Retry-After:
          schema: { type: integer }
          description: Seconds until rate limit resets
```

---

## API Versioning Strategy

### URL Versioning (Recommended for REST)

```
https://api.taskflow.app/v1/tasks     ← stable V1
https://api.taskflow.app/v2/tasks     ← V2 running in parallel
```

**Why URL versioning over headers:** URLs are visible in browser tabs, logs, and documentation. Header versioning is easy to forget and hard to test.

### Version Lifecycle

```
STABLE:     Fully supported with SLA. No breaking changes.
DEPRECATED: Still works. Breaking changes announced. 12-month sunset period.
SUNSET:     Last day. After this date, returns 410 Gone.

Migration timeline example:
  2024-01-01: V2 goes STABLE
  2024-01-01: V1 goes DEPRECATED (12-month notice, emails to all API key holders)
  2025-01-01: V1 SUNSET — returns 410 Gone with link to migration guide
```

### What Constitutes a Breaking Change

```
BREAKING (requires new major version + migration guide):
  ❌ Removing a field from a response
  ❌ Changing a field's type (string → integer)
  ❌ Making an optional request field required
  ❌ Changing the meaning of a field
  ❌ Removing an endpoint

NON-BREAKING (can deploy without version bump):
  ✅ Adding a new optional response field
  ✅ Adding a new optional request field
  ✅ Adding a new endpoint
  ✅ Making a required field optional
  ✅ Adding a new enum value (clients must handle unknown values)
```

---

## Rate Limiting Implementation

```typescript
// lib/rateLimit.ts
import { Redis } from '@upstash/redis';

const redis = new Redis({ url: process.env.UPSTASH_URL!, token: process.env.UPSTASH_TOKEN! });

interface RateLimitConfig {
  key: string;
  maxRequests: number;
  windowMs: number; // milliseconds
}

export async function rateLimit(opts: RateLimitConfig): Promise<{
  allowed: boolean;
  remaining: number;
  reset: number; // epoch seconds
}> {
  const windowKey = `rl:${opts.key}:${Math.floor(Date.now() / opts.windowMs)}`;
  const count = await redis.incr(windowKey);
  if (count === 1) {
    redis.expire(windowKey, Math.ceil(opts.windowMs / 1000));
  }

  const remaining = Math.max(0, opts.maxRequests - count);
  const reset = Math.ceil((Math.floor(Date.now() / opts.windowMs) + 1) * opts.windowMs / 1000);

  return { allowed: count <= opts.maxRequests, remaining, reset };
}

// Middleware
export async function applyRateLimit(req: NextRequest, userId: string) {
  const { allowed, remaining, reset } = await rateLimit({
    key: userId,
    maxRequests: 100,     // 100 requests
    windowMs: 60 * 1000,  // per minute
  });

  const headers = new Headers({
    'X-RateLimit-Limit': '100',
    'X-RateLimit-Remaining': remaining.toString(),
    'X-RateLimit-Reset': reset.toString(),
  });

  if (!allowed) {
    return NextResponse.json(
      { error: { code: 'RATE_LIMITED', message: 'Too many requests' } },
      { status: 429, headers: { 'Retry-After': (reset - Date.now() / 1000).toFixed() } }
    );
  }
  return null; // allowed
}
```

---

## API Key Management

```typescript
// For server-to-server API usage (different from user JWT tokens)
export async function generateApiKey(userId: string, name: string): Promise<string> {
  const rawKey = `sk_${crypto.randomBytes(24).toString('base64url')}`;
  // Store hash — not the raw key (same principle as passwords)
  const keyHash = createHash('sha256').update(rawKey).digest('hex');

  await db.query(
    `INSERT INTO api_keys (user_id, name, key_hash, key_prefix, created_at, last_used_at)
     VALUES ($1, $2, $3, $4, NOW(), NULL)`,
    [userId, name, keyHash, rawKey.substring(0, 8)] // store prefix for display
  );

  return rawKey; // Return once — never store the raw key
}

export async function validateApiKey(rawKey: string): Promise<{ userId: string } | null> {
  const keyHash = createHash('sha256').update(rawKey).digest('hex');
  const { rows } = await db.query(
    `UPDATE api_keys SET last_used_at = NOW()
     WHERE key_hash = $1 AND revoked_at IS NULL
     RETURNING user_id`,
    [keyHash]
  );
  return rows[0] ? { userId: rows[0].user_id } : null;
}
```

---

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Removing API fields without notice | Silently breaks all integrations | Deprecation period + migration guide |
| No OpenAPI spec | 3rd-party devs can't build without docs | Spec-first development |
| Rate limit without Retry-After header | Clients hammer the API after 429 | Always include Retry-After |
| Storing raw API keys | If DB leaked, all keys compromised | Store hashed API keys |
| Single version forever | Breaking changes force major work | Version from day 1 |

---

## Orchestration

```
[Agent 1: Architecture] → ★ Agent 12: API Integration Specialist ★ → Agent 2B → Agent 3
```

- **Triggered when**: Public API design or versioning decisions are needed
- **Input**: Public API requirements + existing endpoints from Agent 2B
- **Output**: OpenAPI spec + versioning strategy + rate limiting implementation + API key system
