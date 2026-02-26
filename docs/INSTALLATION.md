# Installation Guide

Complete step-by-step setup for the Antigravity Pipeline.

---

## Prerequisites

| Requirement | Version | Required? | Purpose |
|-------------|---------|-----------|---------|
| **Python** | 3.11+ | ✅ Yes | Engine runtime |
| **Docker Desktop** | Latest | ✅ Yes | Qdrant, Redis, Postgres |
| **pip** | Latest | ✅ Yes | Package management |
| **Node.js** | 18+ | ❌ Optional | MCP servers |
| **Git** | Any | ❌ Optional | Version control |

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/shantosaha/Antigravity-Seamless-Pipeline.git
cd Antigravity-Seamless-Pipeline
```

---

## Step 2: Create Python Virtual Environment

```bash
# Create the venv at the global location
python3 -m venv ~/.antigravity/venv

# Activate it
source ~/.antigravity/venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

### Key packages installed:

| Package | Purpose |
|---------|---------|
| `scikit-learn` | TF-IDF semantic vectors (Layers 3, 7, 10) |
| `qdrant-client` | Vector memory storage (Layers 3, 11) |
| `redis` | Caching + telemetry (Layers 2, 8, 11) |
| `pyyaml` | Configuration parsing |
| `numpy` | Numerical operations |
| `langgraph` | Dynamic task graph (Layer 4) |

> **Note:** Without `scikit-learn`, the pipeline falls back to SHA-512 hash vectors which have no semantic understanding. The pipeline still runs but with reduced intelligence.

---

## Step 3: Start Docker Services

```bash
docker-compose up -d
```

This starts three containers:

| Container | Port | Purpose |
|-----------|------|---------|
| `antigravity-qdrant` | 6333 | Vector database for semantic memory |
| `antigravity-redis` | 6379 | Cache for guidance + telemetry |
| `antigravity-postgres` | 5432 | Optional relational storage |

### Verify services are running:

```bash
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"
```

Expected output:
```
NAMES                  PORTS                    STATUS
antigravity-qdrant     0.0.0.0:6333->6333/tcp   Up 2 minutes
antigravity-redis      0.0.0.0:6379->6379/tcp   Up 2 minutes
antigravity-postgres   0.0.0.0:5432->5432/tcp   Up 2 minutes
```

---

## Step 4: Install Globally

Copy the pipeline to the global `~/.antigravity/` directory, which is shared across all your projects:

```bash
# Create the global directory
mkdir -p ~/.antigravity

# Copy everything except .git, venv, and docs
rsync -av --exclude='.git' --exclude='venv' --exclude='docs' \
    --exclude='__pycache__' --exclude='.DS_Store' \
    . ~/.antigravity/
```

### Verify the installation:

```bash
source ~/.antigravity/venv/bin/activate
python3 ~/.antigravity/run_pipeline.py --mode pre --input "health check"
```

You should see all 9 layers pass:
```
PRE RESULT: ✅ ALL PASSED
Layers: 9/9 | Time: ~800ms
```

---

## Step 5: Activate in Your Project

```bash
cd /path/to/your/project
bash ~/.antigravity/activate.sh
```

This creates:
```
your-project/
├── .agent/rules/
│   └── antigravity_pipeline.md    ← Auto-runs pipeline on every task
└── .agents/workflows/
    └── generate_code.md           ← Manual /generate_code command
```

**That's it.** The pipeline now runs automatically before and after every task in your IDE.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `python3: command not found` | Install Python 3.11+ from python.org or `brew install python3` |
| `docker: command not found` | Install Docker Desktop from docker.com |
| `Qdrant: offline` in pipeline | Run `docker-compose up -d` |
| `Redis: offline` in pipeline | Same as above |
| `ModuleNotFoundError: sklearn` | Run `pip install scikit-learn` in the antigravity venv |
| `Vectorizer: sha512_hash` | Install scikit-learn for TF-IDF vectors |
| Pipeline not auto-running | Ensure `.agent/rules/antigravity_pipeline.md` exists with `alwaysApply: true` |
| Permission denied on `activate.sh` | Run `chmod +x ~/.antigravity/activate.sh` |

---

## Without Docker (Degraded Mode)

The pipeline can run **without Docker** — Layers 3 (Qdrant), 8 (Redis), and 11 (memory/telemetry) will report "offline" but all other layers function normally. You lose semantic memory and caching, but the core intelligence (intent parsing, planning, policy enforcement, skill routing) still works.
