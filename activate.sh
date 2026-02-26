#!/bin/bash
# ============================================================
# Antigravity Pipeline v4 — Activate in ANY project
# 
# Usage:
#   cd /path/to/your/project
#   bash ~/.antigravity/activate.sh
#
# This copies the .agents/workflows/ folder into your project
# so the Antigravity IDE picks up the pipeline workflow.
# ============================================================

set -e

GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Antigravity Pipeline v4 — Activate        ║${NC}"
echo -e "${BLUE}║   (P0-P3 optimized: TF-IDF + AST + YAML)   ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""

# Check we're in a project directory
if [ "$(pwd)" = "$HOME" ]; then
    echo -e "${YELLOW}⚠  Don't run this from ~/ — cd into your project first.${NC}"
    exit 1
fi

PROJECT_DIR="$(pwd)"
echo -e "  Project: ${GREEN}${PROJECT_DIR}${NC}"

# Step 1: Create .agents/workflows and .agent/rules directories
mkdir -p "${PROJECT_DIR}/.agents/workflows"
mkdir -p "${PROJECT_DIR}/.agent/rules"
echo -e "${GREEN}✓${NC} Created .agents/workflows/ and .agent/rules/"

# Step 2: Copy the global workflow file (for /generate_code command)
cp "$HOME/.antigravity/generate_code.md" "${PROJECT_DIR}/.agents/workflows/generate_code.md"
echo -e "${GREEN}✓${NC} Linked pipeline workflow (/generate_code)"

# Step 3: Create auto-run rule (pipeline runs on EVERY task automatically)
cat > "${PROJECT_DIR}/.agent/rules/antigravity_pipeline.md" << 'RULE_EOF'
---
description: Antigravity 11-layer pipeline — runs automatically before and after every task
alwaysApply: true
---

**MANDATORY: Before doing ANY work, run the pre-pipeline. After finishing, run the post-pipeline.**

## Step 1 — Pre-Pipeline (BEFORE any work)

Run this command first, replacing `<task>` with the user's actual instruction:

```bash
source ~/.antigravity/venv/bin/activate && python3 ~/.antigravity/run_pipeline.py --mode pre --input "<task>"
```

Then read the output and follow:
- **Layer 4 strategy** → linear / parallel / conditional — structure your work accordingly
- **Layer 5 rules** → hard violations MUST be fixed, soft suggestions should be applied
- **Layer 6 skipped nodes** → skip those steps in your work too
- **Layer 7 skill** → use the matched skill's instructions and capabilities
- **Layer 3 memories** → reference past similar tasks retrieved from Qdrant

## Step 2 — Do the Work

Follow the strategy and skill guidance from the pipeline output above.

## Step 3 — Post-Pipeline (AFTER work is complete)

Run this command, replacing `<task>` and `<file>` with the instruction and the main file you created/edited:

```bash
source ~/.antigravity/venv/bin/activate && python3 ~/.antigravity/run_pipeline.py --mode post --input "<task>" --code-file "<file>"
```

Include in your final response:
- Evaluation score from Layer 10
- State version and backup count from Layer 11
RULE_EOF
echo -e "${GREEN}✓${NC} Auto-run rule installed (pipeline runs on every task)"

# Step 4: Verify Python environment
echo ""
echo -e "  Checking environment..."
VENV="$HOME/.antigravity/venv/bin/activate"
if [ -f "$VENV" ]; then
    source "$VENV" 2>/dev/null
    # Check critical packages
    MISSING=""
    python3 -c "import sklearn" 2>/dev/null || MISSING="$MISSING scikit-learn"
    python3 -c "import qdrant_client" 2>/dev/null || MISSING="$MISSING qdrant-client"
    python3 -c "import redis" 2>/dev/null || MISSING="$MISSING redis"
    python3 -c "import yaml" 2>/dev/null || MISSING="$MISSING pyyaml"
    python3 -c "import numpy" 2>/dev/null || MISSING="$MISSING numpy"
    
    if [ -z "$MISSING" ]; then
        echo -e "${GREEN}✓${NC} Python venv OK (sklearn, qdrant, redis, numpy)"
    else
        echo -e "${YELLOW}⚠${NC}  Missing packages:${MISSING}"
        echo -e "    ${BLUE}source ~/.antigravity/venv/bin/activate && pip install${MISSING}${NC}"
    fi
else
    echo -e "${RED}✗${NC} Python venv not found at ~/.antigravity/venv/"
    echo -e "    ${BLUE}python3 -m venv ~/.antigravity/venv${NC}"
    echo -e "    ${BLUE}source ~/.antigravity/venv/bin/activate${NC}"
    echo -e "    ${BLUE}pip install qdrant-client redis pyyaml scikit-learn numpy${NC}"
fi

# Step 5: Verify Docker services
DOCKER_OK=true
docker ps --format "{{.Names}}" 2>/dev/null | grep -q "antigravity" || DOCKER_OK=false

if [ "$DOCKER_OK" = true ]; then
    QDRANT=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -c "qdrant" || true)
    REDIS=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -c "redis" || true)
    echo -e "${GREEN}✓${NC} Docker services running (Qdrant: $QDRANT, Redis: $REDIS)"
else
    echo -e "${YELLOW}⚠${NC}  Docker services not detected. Start them:"
    echo -e "    ${BLUE}cd ~/.antigravity && docker-compose up -d${NC}"
    echo -e "    (or start Docker Desktop first)"
fi

# Step 6: Quick pipeline test
echo ""
echo -e "  Running pipeline health check..."
cd "$HOME/.antigravity"
RESULT=$(python run_pipeline.py --mode pre --input "health check" --json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); s=d['summary']; print(f'{s[\"layers_passed\"]}/{s[\"total_layers\"]} layers | {s[\"total_duration_ms\"]}ms')" 2>/dev/null)
cd "${PROJECT_DIR}"

if [ -n "$RESULT" ]; then
    echo -e "  Pipeline: ${GREEN}${RESULT}${NC}"
else
    echo -e "  Pipeline: ${YELLOW}Could not verify (may need Docker)${NC}"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✓ Pipeline v4 Active!                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Open this project in your IDE."
echo -e "  The pipeline will run AUTOMATICALLY on every task."
echo -e "  You can also use /generate_code for manual control."
echo ""
echo -e "  ${BLUE}Manual run:${NC}"
echo -e "    source ~/.antigravity/venv/bin/activate"
echo -e "    cd ~/.antigravity"
echo -e "    python run_pipeline.py --mode pre --input \"your task here\""
echo ""
