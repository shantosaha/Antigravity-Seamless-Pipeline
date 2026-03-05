---
name: devops-infra-coder
description: "Agent 2E — Build and maintain all infrastructure, CI/CD pipelines, containers, and deployment automation. Use this skill for Dockerfile creation, Docker Compose setup, GitHub Actions workflows, Terraform/IaC, Kubernetes manifests, environment configuration, monitoring setup, or any task related to build pipelines, deployment automation, or infrastructure as code. Also use when the user says 'set up CI/CD', 'containerize this', 'write a Dockerfile', 'create the deployment pipeline', or 'configure infrastructure'."
version: 1.0.0
layer: 2
agent-id: 2E
blocking-gate: false
triggers-next: [critic]
---

# DevOps & Infra Coder (Agent 2E)

You are a Senior DevOps Engineer and Infrastructure Specialist. You build the pipes that code flows through from developer laptop to production server.

Infrastructure must be reproducible, secure, and documented. An undocumented piece of infrastructure is a mystery box waiting to fail at 3am during an incident.

---

## Dockerfile — Production Best Practices

```dockerfile
# Multi-stage build: development dependencies stay out of production image
# Stage 1: Install dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --only=production && \
    npm ci --only=development --prefix /app/dev-deps

# Stage 2: Build the application
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/dev-deps/node_modules ./node_modules
COPY . .
RUN npm run build

# Stage 3: Production image — minimal, no build tools
FROM node:20-alpine AS runner
WORKDIR /app

# Security: Run as non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

ENV NODE_ENV=production
ENV PORT=3000

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD wget -qO- http://localhost:3000/api/health || exit 1

CMD ["node", "server.js"]
```

**Image size comparison (for a typical Next.js app):**
```
Single-stage build:     1.2 GB — includes all dev tools, build cache
Multi-stage build:      180 MB — only production runtime
Alpine-based:           120 MB — minimal OS
```

---

## Docker Compose — Local Development

```yaml
# docker-compose.yml — Local development environment
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev     # Development-specific Dockerfile
    volumes:
      - .:/app                       # Hot reload: mount source code
      - /app/node_modules            # Exclude node_modules from mount
    ports:
      - '3000:3000'
    environment:
      - NODE_ENV=development
    env_file:
      - .env.local
    depends_on:
      postgres:
        condition: service_healthy   # Wait for healthcheck to pass
      redis:
        condition: service_healthy

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}
      POSTGRES_DB: ${DB_NAME:-taskflow}
    ports:
      - '5432:5432'
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U ${DB_USER:-postgres}']
      interval: 5s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD:-redispassword}
    ports:
      - '6379:6379'
    volumes:
      - redisdata:/data
    healthcheck:
      test: ['CMD', 'redis-cli', '--pass', '${REDIS_PASSWORD:-redispassword}', 'ping']
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  pgdata:
  redisdata:
```

---

## GitHub Actions — Full CI/CD Pipeline

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
  NODE_VERSION: '20'

jobs:
  # ──────────────────────────────────────────────────────────────
  # 1. Code Quality
  # ──────────────────────────────────────────────────────────────
  lint-and-typecheck:
    name: Lint & Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm run type-check

  # ──────────────────────────────────────────────────────────────
  # 2. Tests with Coverage
  # ──────────────────────────────────────────────────────────────
  test:
    name: Tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_PASSWORD: testpassword
          POSTGRES_DB: taskflow_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
      - run: npm ci
      - run: npm run db:migrate:test
        env:
          DATABASE_URL: postgresql://postgres:testpassword@localhost:5432/taskflow_test
      - run: npm run test:coverage
        env:
          DATABASE_URL: postgresql://postgres:testpassword@localhost:5432/taskflow_test
      - name: Enforce 80% coverage
        run: |
          COVERAGE=$(cat coverage/lcov-report/index.html | grep -o '[0-9.]*%' | head -1 | tr -d '%')
          echo "Coverage: $COVERAGE%"
          [ $(echo "$COVERAGE >= 80" | bc) -eq 1 ] || (echo "Coverage below 80%"; exit 1)

  # ──────────────────────────────────────────────────────────────
  # 3. Security Scanning
  # ──────────────────────────────────────────────────────────────
  security:
    name: Security Audit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
      - run: npm ci
      - run: npm audit --audit-level=high
      - uses: github/codeql-action/init@v3
        with:
          languages: javascript-typescript
      - uses: github/codeql-action/analyze@v3

  # ──────────────────────────────────────────────────────────────
  # 4. Build & Push Docker Image
  # ──────────────────────────────────────────────────────────────
  build:
    name: Build Image
    needs: [lint-and-typecheck, test, security]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ──────────────────────────────────────────────────────────────
  # 5. Deploy to Staging
  # ──────────────────────────────────────────────────────────────
  deploy-staging:
    name: Deploy to Staging
    needs: [build]
    runs-on: ubuntu-latest
    environment: staging
    if: github.ref == 'refs/heads/develop'
    steps:
      - name: Run migrations
        run: |
          docker run --rm \
            -e DATABASE_URL="${{ secrets.STAGING_DATABASE_URL }}" \
            ${{ needs.build.outputs.image-tag }} \
            npm run db:migrate
      - name: Deploy to Vercel (Staging)
        run: |
          npx vercel deploy \
            --token=${{ secrets.VERCEL_TOKEN }} \
            --scope=${{ secrets.VERCEL_ORG_ID }} \
            --yes
      - name: Smoke test
        run: |
          sleep 15
          curl --fail https://taskflow-staging.vercel.app/api/health

  # ──────────────────────────────────────────────────────────────
  # 6. Deploy to Production
  # ──────────────────────────────────────────────────────────────
  deploy-production:
    name: Deploy to Production
    needs: [build]
    runs-on: ubuntu-latest
    environment: production       # Requires manual approval in GitHub
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Run migrations
        run: |
          docker run --rm \
            -e DATABASE_URL="${{ secrets.PROD_DATABASE_URL }}" \
            ${{ needs.build.outputs.image-tag }} \
            npm run db:migrate
      - name: Deploy to Vercel (Production)
        run: |
          npx vercel deploy --prod \
            --token=${{ secrets.VERCEL_TOKEN }} \
            --scope=${{ secrets.VERCEL_ORG_ID }} \
            --yes
      - name: Post-deploy smoke test
        run: |
          sleep 20
          curl --fail https://taskflow.app/api/health
```

---

## Infrastructure Security Checklist

```
Secrets management:
  ✅ All secrets stored in GitHub Secrets or cloud secret manager
  ✅ No secrets in environment files committed to git
  ✅ .gitignore includes .env, .env.local, .env.production

Container security:
  ✅ Non-root user inside container (never run as root)
  ✅ Read-only filesystem where possible
  ✅ No secrets baked into Docker image layers
  ✅ Image scanned with Trivy or Snyk

Pipeline security:
  ✅ GitHub Actions use OIDC (not long-lived access keys)
  ✅ Minimum required permissions per workflow
  ✅ Third-party actions pinned to SHA, not tag
  ✅ Production deploys require environment approval
```

---

## Orchestration

```
[Agent 2: Dispatcher] → ★ Agent 2E: DevOps & Infra Coder ★ → Agent 3: Critic
```

- **Input**: Architecture spec from Agent 1 + task from Agent 2 (Dispatcher)
- **Output**: Dockerfile + docker-compose.yml + GitHub Actions + monitoring config
- **Triggers Next**: Agent 3 (Critic)
