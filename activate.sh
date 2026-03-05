#!/bin/bash
# ================================================================
# Antigravity Seamless Pipeline v4 — Project Activator
#
# Usage:
#   cd /path/to/your/project
#   bash ~/.antigravity/activate.sh
#
# Works on NEW projects and EXISTING projects.
# Creates ALL required files and enforces the pipeline by default.
# ================================================================

set -e

GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

# ────────────────────────────────────────────────────────────────
# HEADER
# ────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🚀  Antigravity Seamless Pipeline v4                  ║${NC}"
echo -e "${BLUE}║       Project Activator — New & Existing Projects        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ────────────────────────────────────────────────────────────────
# GUARD: Must be run from a project directory, not ~
# ────────────────────────────────────────────────────────────────
if [ "$(pwd)" = "$HOME" ]; then
    echo -e "${RED}✗${NC} Don't run this from ~/ — cd into your project first."
    echo -e "  Example: ${CYAN}cd ~/projects/my-app && bash ~/.antigravity/activate.sh${NC}"
    exit 1
fi

PROJECT_DIR="$(pwd)"
PROJECT_NAME="$(basename "$PROJECT_DIR")"
ANTIGRAVITY_DIR="$HOME/.antigravity"

echo -e "  ${BOLD}Project:${NC} ${GREEN}${PROJECT_NAME}${NC}"
echo -e "  ${BOLD}Path:${NC}    ${PROJECT_DIR}"
echo ""

# ────────────────────────────────────────────────────────────────
# STEP 1: Create directory structure
# ────────────────────────────────────────────────────────────────
echo -e "${CYAN}── Step 1: Setting up project structure${NC}"

mkdir -p "${PROJECT_DIR}/.agents/workflows"
mkdir -p "${PROJECT_DIR}/.agent"

echo -e "  ${GREEN}✓${NC} .agents/workflows/ — Pipeline workflow commands"
echo -e "  ${GREEN}✓${NC} .agent/            — Project rules and config"

# ────────────────────────────────────────────────────────────────
# STEP 2: Install the /generate_code workflow command
# ────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Step 2: Installing pipeline workflow (/generate_code)${NC}"

if [ -f "${ANTIGRAVITY_DIR}/generate_code.md" ]; then
    cp "${ANTIGRAVITY_DIR}/generate_code.md" "${PROJECT_DIR}/.agents/workflows/generate_code.md"
    echo -e "  ${GREEN}✓${NC} /generate_code command installed"
else
    echo -e "  ${YELLOW}⚠${NC}  generate_code.md not found — skipping"
fi

# ────────────────────────────────────────────────────────────────
# STEP 3: Create the project-level workflow config (.antigravity.vrc)
# ────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Step 3: Creating workflow configuration (.antigravity.vrc)${NC}"

VRC_FILE="${PROJECT_DIR}/.antigravity.vrc"
if [ -f "$VRC_FILE" ]; then
    echo -e "  ${YELLOW}↻${NC}  .antigravity.vrc already exists — skipping (preserving your settings)"
else
    cat > "$VRC_FILE" << 'VRC_EOF'
{
  "workflow_mode": "antigravity",
  "version": "4.0.0",
  "auto_pipeline": true,
  "description": "Antigravity Seamless Pipeline config. Set 'workflow_mode' to 'base' to bypass the 11-layer pipeline for a specific session."
}
VRC_EOF
    echo -e "  ${GREEN}✓${NC} .antigravity.vrc created (mode: antigravity)"
fi

# ────────────────────────────────────────────────────────────────
# STEP 4: Install the mandatory auto-run pipeline rule
# ────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Step 4: Installing pipeline enforcement rule${NC}"

cat > "${PROJECT_DIR}/.agent/antigravity_pipeline.md" << 'RULE_EOF'
---
description: "Antigravity Seamless Pipeline v4 — Mandatory PRE/WORK/POST cycle for every task"
alwaysApply: true
---

**MANDATORY: Run the PRE-pipeline BEFORE any work. Run the POST-pipeline AFTER.**

## Workflow Mode Check

Before running, check `.antigravity.vrc` in the project root:
- `"workflow_mode": "antigravity"` → Run the full 11-layer pipeline (DEFAULT)
- `"workflow_mode": "base"` → Skip the pipeline (only for minor doc edits)

## Step 1 — Pre-Pipeline (BEFORE any work)

```bash
source ~/.antigravity/venv/bin/activate && python3 ~/.antigravity/run_pipeline.py --mode pre --input "<TASK>"
```

Then read `~/.antigravity/state/pipeline_guidance.json` and follow:
- **Layer 4 strategy** → linear / parallel / conditional
- **Layer 5 rules** → hard violations MUST be fixed
- **Layer 7 skill** → use matched skill's instructions OR the 32-Agent Experience API learned pattern
- **Layer 3 memories** → reference past similar tasks from Qdrant

## Step 2 — Do the Work

Execute using the agent fleet defined by the Orchestrator (Agent 15). Follow each specialist skill's
internal protocol exactly as written in `~/.antigravity/skills/<skill>/SKILL.md`. Or, use the learned 
pattern provided by the Experience API.

## Step 3 — Post-Pipeline (AFTER work is complete)

```bash
source ~/.antigravity/venv/bin/activate && python3 ~/.antigravity/run_pipeline.py --mode post --input "<TASK>" --code-file "<PATH_TO_OUTPUT_FILE>"
```

Report in your final response:
- Layer 10 evaluation score
- State version from Layer 11
RULE_EOF

echo -e "  ${GREEN}✓${NC} .agent/antigravity_pipeline.md installed"

# ────────────────────────────────────────────────────────────────
# STEP 5: Create project rules.md (only if it doesn't exist)
# ────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Step 5: Initializing project rules (.agent/rules.md)${NC}"

RULES_FILE="${PROJECT_DIR}/.agent/rules.md"
if [ -f "$RULES_FILE" ]; then
    echo -e "  ${YELLOW}↻${NC}  .agent/rules.md already exists — skipping (preserving your rules)"
    # Ensure Workflow section is present in existing file
    if ! grep -q "Antigravity Pipeline" "$RULES_FILE"; then
        echo "" >> "$RULES_FILE"
        cat >> "$RULES_FILE" << 'RULES_APPEND_EOF'

## Workflow & Pipeline

1.  **Antigravity Pipeline (v4)**: This project operates exclusively under the 11-layer Antigravity Pipeline.
    *   **Mandatory Cycle**: Every task MUST follow the `PRE` → `WORK` → `POST` cycle using `run_pipeline.py`.
    *   **Enforcement**: Use `run_pipeline.py --mode pre` before starting work and `run_pipeline.py --mode post` after finishing.
2.  **Base Workflow Toggle**: Set `"workflow_mode": "base"` in `.antigravity.vrc` to bypass for minor docs-only tasks.
    *   **Warning**: Bypassing disables Layer 10 Safety Scoring and Layer 11 Memory Persistence.
RULES_APPEND_EOF
        echo -e "  ${GREEN}✓${NC} Workflow section appended to existing rules.md"
    else
        echo -e "  ${GREEN}✓${NC} Workflow section already present in rules.md"
    fi
else
    cat > "$RULES_FILE" << 'RULES_EOF'
# Project Rules & Universal Instructions

## Tech Stack & Standards
- **Frameworks**: Define in this section based on your project (e.g., Next.js, FastAPI, etc.)
- **Styling**: Define preferred styling approach (e.g., Tailwind CSS, Vanilla CSS, etc.)
- **State Management**: Define approach (e.g., React Hooks, Zustand, Redux, etc.)
- **API Communication**: Define service layer patterns for this project.

## Communication & Style
- **Problem Solving**: Do not apologize for errors; simply fix them and explain the change.
- **UI/UX**: Prioritize visual aesthetics. Use modern, premium designs with smooth transitions.
- **Logic**: Prefer clarity and reliability over brevity.

## Workflow & Pipeline

1.  **Antigravity Pipeline (v4)**: This project operates exclusively under the 11-layer Antigravity Pipeline.
    *   **Mandatory Cycle**: Every task MUST follow the `PRE` → `WORK` → `POST` cycle using `run_pipeline.py`.
    *   **Enforcement**: Use `run_pipeline.py --mode pre` before starting work and `run_pipeline.py --mode post` after finishing.
2.  **Base Workflow Toggle**: Set `"workflow_mode": "base"` in `.antigravity.vrc` to bypass for minor docs-only tasks.
    *   **Warning**: Bypassing disables Layer 10 Safety Scoring and Layer 11 Memory Persistence.
RULES_EOF
    echo -e "  ${GREEN}✓${NC} .agent/rules.md created with pipeline enforcement"
fi

# ────────────────────────────────────────────────────────────────
# STEP 6: Verify Python environment
# ────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Step 6: Verifying Python environment${NC}"

VENV="${ANTIGRAVITY_DIR}/venv/bin/activate"
if [ -f "$VENV" ]; then
    source "$VENV" 2>/dev/null

    MISSING=""
    python3 -c "import sklearn"      2>/dev/null || MISSING="$MISSING scikit-learn"
    python3 -c "import qdrant_client" 2>/dev/null || MISSING="$MISSING qdrant-client"
    python3 -c "import redis"         2>/dev/null || MISSING="$MISSING redis"
    python3 -c "import yaml"          2>/dev/null || MISSING="$MISSING pyyaml"
    python3 -c "import numpy"         2>/dev/null || MISSING="$MISSING numpy"

    if [ -z "$MISSING" ]; then
        echo -e "  ${GREEN}✓${NC} Python venv OK (all packages present)"
    else
        echo -e "  ${YELLOW}⚠${NC}  Missing packages:${MISSING}"
        echo -e "      Fix: ${CYAN}source ~/.antigravity/venv/bin/activate && pip install${MISSING}${NC}"
    fi
else
    echo -e "  ${RED}✗${NC} Python venv not found."
    echo -e "      Fix: ${CYAN}python3 -m venv ~/.antigravity/venv${NC}"
    echo -e "           ${CYAN}source ~/.antigravity/venv/bin/activate${NC}"
    echo -e "           ${CYAN}pip install qdrant-client redis pyyaml scikit-learn numpy${NC}"
fi

# ────────────────────────────────────────────────────────────────
# STEP 7: Verify Docker services (Qdrant, Redis, PostgreSQL)
# ────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Step 7: Verifying Docker services${NC}"

if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    QDRANT_UP=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -c "qdrant"  || echo "0")
    REDIS_UP=$(docker ps  --format "{{.Names}}" 2>/dev/null | grep -c "redis"   || echo "0")
    PG_UP=$(docker ps     --format "{{.Names}}" 2>/dev/null | grep -c "postgres" || echo "0")

    if [ "$QDRANT_UP" -gt 0 ] && [ "$REDIS_UP" -gt 0 ]; then
        echo -e "  ${GREEN}✓${NC} Qdrant: running   Redis: running   PostgreSQL: ${PG_UP:-0} running"
    else
        echo -e "  ${YELLOW}⚠${NC}  Docker services not fully running."
        echo -e "      Start them: ${CYAN}cd ~/.antigravity && docker-compose up -d${NC}"
        echo -e "      Qdrant: ${QDRANT_UP}  Redis: ${REDIS_UP}  PostgreSQL: ${PG_UP}"
    fi
else
    echo -e "  ${YELLOW}⚠${NC}  Docker not running or not installed."
    echo -e "      Layers 3 (Qdrant) and 8 (Redis) will run in offline/fallback mode."
    echo -e "      Start Docker Desktop, then: ${CYAN}cd ~/.antigravity && docker-compose up -d${NC}"
fi

# ────────────────────────────────────────────────────────────────
# STEP 8: Pipeline health check
# ────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Step 8: Pipeline health check${NC}"

# Run from project directory so the .antigravity.vrc is picked up
RESULT=$(source "${ANTIGRAVITY_DIR}/venv/bin/activate" 2>/dev/null && \
    python3 "${ANTIGRAVITY_DIR}/run_pipeline.py" --mode pre --input "health check" --json 2>/dev/null | \
    python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    s = d['summary']
    print(f'{s[\"layers_passed\"]}/{s[\"total_layers\"]} layers | {s[\"total_duration_ms\"]}ms')
except:
    print('unavailable')
" 2>/dev/null || echo "unavailable")

if [ "$RESULT" != "unavailable" ]; then
    echo -e "  ${GREEN}✓${NC} Pipeline: ${RESULT}"
else
    echo -e "  ${YELLOW}⚠${NC}  Could not verify pipeline. Check Docker services and Python venv."
fi

# ────────────────────────────────────────────────────────────────
# FOOTER
# ────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅  Antigravity Pipeline v4 — ACTIVE                  ║${NC}"
echo -e "${GREEN}║   Project: ${BOLD}${PROJECT_NAME}${NC}${GREEN}$(printf '%*s' $((42 - ${#PROJECT_NAME})) '')║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}What was set up:${NC}"
echo -e "  ${GREEN}•${NC} .agents/workflows/generate_code.md  → /generate_code command"
echo -e "  ${GREEN}•${NC} .agent/antigravity_pipeline.md      → Auto-run PRE/POST enforcement"
echo -e "  ${GREEN}•${NC} .agent/rules.md                     → Project rules (edit to customize)"
echo -e "  ${GREEN}•${NC} .antigravity.vrc                    → Workflow toggle config"
echo ""
echo -e "  ${BOLD}How to use:${NC}"
echo -e "  ${CYAN}1.${NC} Open this project in your IDE — the pipeline runs automatically."
echo -e "  ${CYAN}2.${NC} Use ${BOLD}/generate_code${NC} for manual pipeline control."
echo -e "  ${CYAN}3.${NC} To switch to Base Workflow (no pipeline):"
echo -e "     Edit ${BOLD}.antigravity.vrc${NC} → set ${CYAN}\"workflow_mode\": \"base\"${NC}"
echo ""
echo -e "  ${BOLD}Manual pipeline run:${NC}"
echo -e "  ${CYAN}source ~/.antigravity/venv/bin/activate${NC}"
echo -e "  ${CYAN}python3 ~/.antigravity/run_pipeline.py --mode pre --input \"your task\"${NC}"
echo ""
