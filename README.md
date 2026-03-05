# 🚀 Antigravity Seamless Pipeline v4

> A **self-learning, 11-layer AI development pipeline** with a 32-agent autonomous ecosystem. One command activates it in any project — new or existing.

---

## ✨ What Is This?

Antigravity Seamless Pipeline is an autonomous AI coding infrastructure that wraps around your IDE's AI assistant (e.g., Antigravity / Gemini). Every task your AI performs is guided through a structured pipeline that:

- **Gathers intelligence** before writing a single line of code (Layers 1–9)
- **Executes** using specialist agents, each with their own skill protocol
- **Evaluates** quality and safety via AST analysis after the work is done (Layer 10)
- **Learns permanently** by storing outcomes in Qdrant vector memory (Layer 11)

---

## 📦 Requirements

| Dependency | Version | Purpose |
| :--- | :--- | :--- |
| Python | 3.10+ | Pipeline engine |
| Docker Desktop | Latest | Qdrant + Redis + PostgreSQL containers |
| Node.js / npm | 18+ | For JS/TS projects (optional) |

---

## ⚡ Quick Start

### 1. Install the Pipeline (One-Time Global Setup)

```bash
# Clone or download the pipeline to ~/.antigravity
git clone https://github.com/YOUR_USERNAME/antigravity-pipeline.git ~/.antigravity

# Create Python virtual environment
python3 -m venv ~/.antigravity/venv
source ~/.antigravity/venv/bin/activate
pip install qdrant-client redis pyyaml scikit-learn numpy

# Start the required Docker services (Qdrant, Redis, PostgreSQL)
cd ~/.antigravity && docker-compose up -d
```

### 2. Activate in Any Project (Per-Project Setup)

```bash
# cd into your project (new or existing)
cd ~/projects/my-awesome-app

# Run the activator — creates all required files automatically
bash ~/.antigravity/activate.sh
```

That's it. Open the project in your IDE. The pipeline runs on every task.

---

## 🔄 How It Works — The Full Pipeline

```
User Instruction
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  PRE-PIPELINE (Layers 1–9) — "Intelligence Gathering"       │
│                                                             │
│  L1: Intent & Language Detection                            │
│  L2: Context File Ranking (token-budget aware)              │
│  L3: Semantic Memory Retrieval (Qdrant vector search)       │
│  L4: Strategy & Complexity Scoring (LangGraph)              │
│  L5: Policy & Rules Enforcement                             │
│  L6: Workflow YAML Condition Evaluation                     │
│  L7: Skill Matching (TF-IDF semantic)                       │
│  L8: Tool Cache Check (Redis)                               │
│  L9: MCP Server Health Probes                               │
│                                                             │
│  Output: pipeline_guidance.json                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  WORK — 32-Agent Autonomous Fleet                           │
│                                                             │
│  Agent 15: Orchestrator (routes all agents)                 │
│  Agent 1:  Architect                                        │
│  Agent 2A: Frontend UI Engineer                             │
│  Agent 2B: Backend API Engineer                             │
│  Agent 3:  Critic (code review + self-correction)           │
│  Agent 4:  Debugger                                         │
│  Agent 5:  Tester                                           │
│  Agent 6:  Security Auditor                                 │
│  ... (32 total specialist agents)                           │
│                                                             │
│  Every agent reads its own SKILL.md for its protocol.       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  POST-PIPELINE (Layers 10–11) — "Validation & Learning"     │
│                                                             │
│  L10: AST Analysis + Safety Check + Alignment Score        │
│  L11: State v{N} → Qdrant memory + Redis telemetry         │
│                                                             │
│  Output: Learned patterns stored permanently                │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 What `activate.sh` Creates in Your Project

```
your-project/
├── .antigravity.vrc            ← Workflow mode toggle (antigravity | base)
├── .agent/
│   ├── antigravity_pipeline.md ← Auto-run enforcement rule (alwaysApply: true)
│   └── rules.md                ← Editable project-specific rules
└── .agents/
    └── workflows/
        └── generate_code.md    ← /generate_code slash command
```

---

## 🔀 Workflow Toggle

You can switch between **two modes** by editing `.antigravity.vrc` in your project root:

### Antigravity Mode (Default — Recommended)
```json
{
  "workflow_mode": "antigravity"
}
```
Full 11-layer pipeline. All learning, safety, and memory features active.

### Base Mode (Bypass — Use Sparingly)
```json
{
  "workflow_mode": "base"
}
```
Skips the 11-layer pipeline entirely. Standard AI behavior.
> ⚠️ **Warning**: Layer 10 Safety Scoring and Layer 11 Memory Persistence are disabled in Base Mode. Use only for minor documentation edits.

---

## 🧠 Self-Learning System

| Storage | Location | Scope | Permanence |
| :--- | :--- | :--- | :--- |
| **Qdrant (Vector DB)** | `~/.antigravity/` | ALL projects on this machine | Permanent |
| **Redis (Cache)** | Docker container | Real-time telemetry | Persistent |
| **PostgreSQL** | Docker container | Long-term structured data | Permanent |
| **State JSON** | `~/.antigravity/state/` | Per-session history | Permanent |

When the pipeline stores a successful outcome in Qdrant, the next time you ask for something similar (even in a **different project**), Layer 3 retrieves that pattern and the agent proactively applies the proven solution.

---

## 🛠️ Manual Pipeline Control

```bash
# Activate the Python environment
source ~/.antigravity/venv/bin/activate

# PRE-mode: Before doing work
python3 ~/.antigravity/run_pipeline.py --mode pre --input "Build a login page"

# POST-mode: After completing work
python3 ~/.antigravity/run_pipeline.py --mode post --input "Build a login page" --code-file "./src/app/login/page.tsx"

# Full pipeline: PRE + POST in one command
python3 ~/.antigravity/run_pipeline.py --mode full --input "Add Stripe payments" --code-file "./src/payments.ts"
```

---

## 🐳 Docker Services

```bash
# Start all services
cd ~/.antigravity && docker-compose up -d

# Status check
docker ps | grep antigravity

# Stop all services
cd ~/.antigravity && docker-compose down
```

| Service | Port | Purpose |
| :--- | :--- | :--- |
| **Qdrant** | 6333 | Vector memory (Layer 3 & 11) |
| **Redis** | 6379 | Tool cache & telemetry (Layer 8) |
| **PostgreSQL** | 5432 | Long-term state storage |

---

## 🤖 The 32-Agent Ecosystem

Each agent has a `SKILL.md` in `~/.antigravity/skills/<skill-name>/SKILL.md` that defines its autonomous decision-making protocol. Agents are activated by the **Orchestrator (Agent 15)** based on the task type detected in Layer 1.

**Key agents:**

| Agent | Role | Skill |
| :--- | :--- | :--- |
| **Agent 15** | Orchestrator — routes everything | `orchestrator` |
| **Agent 1** | System Architect | `architect` |
| **Agent 2A** | Frontend UI Engineer | `frontend-ui-engineer` |
| **Agent 2B** | Backend API Engineer | `backend-api-engineer` |
| **Agent 3** | Critic & Code Reviewer | `critic` |
| **Agent 4** | Debugger | `debugger` |
| **Agent 5** | Learning Specialist | `context-memory-manager` |
| **Agent 6** | Security Auditor | `security-auditor` |

---

## 📝 Directory Structure (`~/.antigravity`)

```
~/.antigravity/
├── activate.sh            ← Project activator (run this first)
├── run_pipeline.py        ← Main pipeline CLI
├── generate_code.md       ← /generate_code workflow template
├── docker-compose.yml     ← Qdrant + Redis + PostgreSQL
├── global.yaml            ← Global rules engine config
├── INTEGRATION_GUIDE.md   ← Agent-pipeline data flow guide
├── engine/                ← Pipeline layer engine
├── skills/                ← 88+ specialist agent skills
│   ├── orchestrator/
│   ├── frontend-ui-engineer/
│   ├── backend-api-engineer/
│   └── ... (88 total)
├── workflows/             ← YAML workflow definitions
│   ├── code_generation.yaml
│   └── agent_orchestration.yaml
├── state/                 ← Pipeline state & guidance files
│   ├── pipeline_guidance.json
│   └── pipeline_report.json
└── venv/                  ← Python virtual environment
```

---

## 🔒 Security

- **No eval(), exec(), subprocess.call** — hard-blocked by Layer 5
- **No dangerouslySetInnerHTML** — hard-blocked for all web projects
- **No hardcoded secrets** — Layer 5 detects `.env` files and enforces externalization
- All security patterns are enforced via `global.yaml` and updated dynamically per project

---

## 🤝 Contributing

1. Fork this repo
2. Create a feature branch: `git checkout -b feature/my-skill`
3. Add or update a skill: `~/.antigravity/skills/my-skill/SKILL.md`
4. Test with: `bash ~/.antigravity/activate.sh` in a test project
5. Submit a Pull Request

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

**Built with ❤️ by the Antigravity community.**
*One command. Full autonomy. Permanent learning.*
