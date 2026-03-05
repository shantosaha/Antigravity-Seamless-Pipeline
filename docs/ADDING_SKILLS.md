# Adding Skills

How to create new skills for the TF-IDF semantic router.

---

## What is a Skill?

A skill is a folder in `skills/` containing a `SKILL.md` file. The pipeline's Layer 7 (Skill Router) reads all skill descriptions and uses **TF-IDF cosine similarity** to find the best match for any given user instruction.

```
skills/
├── auth-implementation-patterns/
│   └── SKILL.md
├── postgresql-table-design/
│   └── SKILL.md
├── react-performance-optimization/
│   └── SKILL.md
└── your-new-skill/          ← Add your skill here
    └── SKILL.md
```

---

## SKILL.md Format

Every skill file has **YAML frontmatter** and a **markdown body**:

```markdown
---
name: my-new-skill
description: Build secure GraphQL APIs with Apollo Server, authentication middleware, and database integration
version: 1.0.0
---

# My New Skill

## Capabilities
- Design GraphQL schemas with type safety
- Implement authentication middleware
- Set up database resolvers

## Instructions
1. Use Apollo Server 4+ with Express
2. Always validate inputs with Zod
3. Use DataLoader for N+1 query prevention

## Style
- TypeScript strict mode
- ESM imports only
- Error handling with custom GraphQL errors
```

---

## How the Skill Router Picks Skills

When a user says "Build me a GraphQL API with auth":

1. **[NEW] Experience API Check**: The router first checks the 32-Agent Experience API to see if a learned pattern exists for this exact task type and complexity. If a match is found with >80% confidence, it overrides the standard router.
2. **Vectorize**: The instruction is converted to a TF-IDF character n-gram vector.
3. **Compare**: Each skill's `description` (from frontmatter) is also vectorized.
4. **Rank**: Cosine similarity is computed between instruction vector and every skill vector.
5. **Select**: Highest similarity wins (with confidence %).

### Tips for High Discoverability

The router matches on the `description` field primarily. To get good matches:

| ✅ Good Description | ❌ Bad Description |
|---------------------|-------------------|
| "Build secure REST APIs with JWT authentication, bcrypt hashing, and Express middleware" | "API stuff" |
| "Design PostgreSQL schemas with indexing, constraints, and migration strategies" | "Database skill" |
| "Implement React Native mobile apps with navigation, state management, and offline support" | "Mobile development" |

**Be specific and use the keywords your users will type.** The TF-IDF vectorizer works on character n-grams, so even partial matches ("auth", "authen", "authentication") will score well.

---

## Example: Creating a "Docker Compose Patterns" Skill

### 1. Create the folder:
```bash
mkdir -p skills/docker-compose-patterns
```

### 2. Write the SKILL.md:
```markdown
---
name: docker-compose-patterns
description: Create Docker Compose configurations for multi-container applications with networking, volumes, health checks, and production deployment
version: 1.0.0
---

# Docker Compose Patterns

## Capabilities
- Multi-stage Docker builds
- Docker Compose service definitions
- Network isolation and service discovery
- Health checks and restart policies
- Volume management for persistence

## Instructions
- Always use named volumes (never bind mounts in production)
- Include health checks for every service
- Use `.env` files for configuration
- Pin image versions (never use :latest in production)

## Templates

### Basic web app:
- Frontend (Nginx)
- Backend (Node.js / Python)
- Database (PostgreSQL)
- Cache (Redis)
```

### 3. Test it:

```bash
source ~/.antigravity/venv/bin/activate
python3 run_pipeline.py --mode pre --input "Create a Docker Compose setup for a microservices app"
```

Look at Layer 7 output — your skill should appear with a high confidence score.

---

## Secondary Skills

Layer 7 also returns a **secondary skill** — the second-best match. This allows the AI to draw from multiple skill sets when the task spans domains (e.g., "Build a React app with PostgreSQL" → primary: `react`, secondary: `postgresql`).

---

## Included Skills (87)

The pipeline ships with 87 pre-built skills, including the massive 32-Agent Autonomous Ecosystem:

| Category | Skills |
|----------|--------|
| **Auth & Security** | auth-implementation-patterns, gdpr-data-handling, sast-configuration |
| **Backend** | fastapi-templates, nodejs-backend-patterns, microservices-patterns |
| **Frontend** | react-performance-optimization, responsive-design, tailwind-design-system, vue3, nextjs-app-router-patterns, framer-motion-animator, threejs-fundamentals |
| **Mobile** | react-native-architecture, react-native-design |
| **Database** | postgresql-table-design, database-migration, supabase-postgres-best-practices |
| **DevOps** | github-actions-templates, k8s-manifest-generator, workflow-orchestration-patterns |
| **AI/ML** | langchain-architecture, rag-implementation, prompt-engineering-patterns, google-cloud-agent-sdk-master |
| **Languages** | go-concurrency-patterns, rust-async-patterns, modern-javascript-patterns, python-performance-optimization |
| **Testing** | e2e-testing-patterns, javascript-testing-patterns |
| **Documents** | docx, pdf, pptx, xlsx |
| **Design** | canvas-design, implement-design, theme-factory, algorithmic-art, web-artifacts-builder |
| **Business** | competitive-landscape, data-storytelling, startup-metrics-framework, stripe-integration, sendgrid-automation |
| **Meta** | skill-creator, skills-downloader, mcp-builder, mcp-integration-expert, task-coordination-strategies |
| **Other** | accessibility-compliance, architecture-patterns |
