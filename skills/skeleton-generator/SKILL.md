---
name: skeleton-generator
description: "Agent P5 — Generate the complete structural scaffold of a codebase before any feature code is written. Use this skill whenever starting a new project from scratch, bootstrapping a codebase from an architecture blueprint, setting up project structure, or when the user asks 'set up the project', 'create the boilerplate', 'initialize the codebase', or wants a runnable empty app with zero features. The skeleton must start without errors."
version: 1.0.0
layer: 0
agent-id: P5
blocking-gate: false
triggers-next: []
---

# Skeleton Generator (Agent P5)

You are a Software Scaffolding Engineer. Your only job is structure — not features, not business logic. You produce a project that starts, responds to a health check, and has zero features.

This matters because a well-structured skeleton means every developer (and every agent) knows exactly where to put their code. A bad skeleton causes inconsistency, import confusion, and merge conflicts. It's cheaper to get the structure right with zero code than to restructure a codebase with thousands of lines.

---

## What a Good Skeleton Provides

### 1. Complete Directory Structure

Every directory must have a purpose. No placeholder folders. No "utils" dumping grounds.

**Example — Next.js + Supabase project:**
```
taskflow/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── layout.tsx          # Root layout with providers
│   │   ├── page.tsx            # Landing page (empty)
│   │   ├── api/
│   │   │   └── health/
│   │   │       └── route.ts    # GET /api/health endpoint
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx  # Login page (stub)
│   │   │   └── register/page.tsx
│   │   └── (dashboard)/
│   │       └── page.tsx        # Dashboard (stub)
│   ├── components/
│   │   ├── ui/                 # Reusable UI primitives
│   │   │   └── Button.tsx      # Empty component with types
│   │   └── layout/
│   │       └── Header.tsx      # Empty component with types
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts       # Browser Supabase client
│   │   │   └── server.ts       # Server Supabase client
│   │   └── utils.ts            # Shared utilities
│   ├── hooks/                  # Custom React hooks
│   │   └── useAuth.ts          # Auth hook (stub)
│   ├── types/
│   │   ├── database.ts         # Database types (empty interfaces)
│   │   └── api.ts              # API types (empty interfaces)
│   └── styles/
│       └── globals.css         # Base styles
├── public/                     # Static assets
│   └── favicon.ico
├── tests/
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── .env.example                # All env vars documented
├── .eslintrc.json
├── .prettierrc
├── .gitignore
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── package.json
├── README.md
└── docker-compose.yml          # Local dev services
```

**Example — Python FastAPI project:**
```
taskflow-api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Settings from env vars
│   ├── database.py             # Database connection
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py           # API router aggregation
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── health.py       # GET /health endpoint
│   ├── models/                 # SQLAlchemy models (empty)
│   │   └── __init__.py
│   ├── schemas/                # Pydantic schemas (empty)
│   │   └── __init__.py
│   ├── services/               # Business logic (empty)
│   │   └── __init__.py
│   └── repositories/           # Data access (empty)
│       └── __init__.py
├── tests/
│   ├── conftest.py
│   └── test_health.py
├── alembic/                    # Database migrations
│   ├── env.py
│   └── versions/
├── .env.example
├── .gitignore
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### 2. Configuration Files (fully populated)

Every configuration file must be complete and working, not a skeleton that needs editing.

**tsconfig.json example:**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

**.env.example (complete, documented):**
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/taskflow

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# Authentication
JWT_SECRET=your-jwt-secret-here-min-32-chars

# External Services (optional)
STRIPE_SECRET_KEY=sk_test_...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### 3. Entry Point Files

The app must start. Zero features, but it starts and serves a health check.

**Next.js entry (src/app/api/health/route.ts):**
```typescript
import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    version: process.env.npm_package_version || '0.1.0',
  });
}
```

**FastAPI entry (app/main.py):**
```python
from fastapi import FastAPI
from app.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
)

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
    }
```

### 4. Empty Module Files with Correct Signatures

Every module must have the right imports, type definitions, and function signatures — just no business logic.

**Example stub component (src/components/ui/Button.tsx):**
```typescript
import { ButtonHTMLAttributes, forwardRef } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
}

/**
 * Reusable button component with variants.
 * @todo Implement styling and loading state
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading = false, children, ...props }, ref) => {
    return (
      <button ref={ref} disabled={loading} {...props}>
        {loading ? 'Loading...' : children}
      </button>
    );
  }
);

Button.displayName = 'Button';
```

### 5. Docker Compose for Local Development

```yaml
version: '3.8'
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: taskflow
    ports:
      - '5432:5432'
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - '6379:6379'

volumes:
  pgdata:
```

---

## Success Criteria

When the skeleton is complete, this sequence must work:

```bash
# 1. Install dependencies
npm install  # (or pip install -r requirements.txt)

# 2. Start the app
npm run dev  # (or uvicorn app.main:app)

# 3. Health check passes
curl http://localhost:3000/api/health
# → {"status":"ok","timestamp":"2024-01-15T10:30:00Z","version":"0.1.0"}

# 4. Zero features are implemented
# → All pages show stubs or "Coming Soon"
# → No business logic exists
# → All tests pass (trivial tests only)
```

---

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Do This Instead |
|-------------|-------------|----------------|
| "utils" folder as a dumping ground | Becomes 50 unrelated functions | Create domain-specific modules |
| Config files with TODOs | App won't start until someone fills them in | Every config file must be complete |
| Missing .gitignore | node_modules or .env committed to git | Include comprehensive .gitignore from day 1 |
| No health check endpoint | Can't verify the app is running | Always include GET /health |
| Placeholder with `any` types | Defeats the purpose of TypeScript | Use proper stub types from the architecture |

---

## Orchestration

```
[Agent 1: Architecture] + [P4: Dependencies] → ★ P5: Skeleton Generator ★ → Layer 2 Agents
```

- **Input**: Architecture blueprint from Agent 1 + validated dependency manifest from P4
- **Output**: Complete project skeleton — all files, all configuration, runnable with zero features
- **Triggers Next**: Layer 2 implementation agents receive the skeleton as their starting point
