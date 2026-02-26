# Usage Guide

How to use the Antigravity Pipeline in your daily workflow.

---

## Automatic Mode (Recommended)

After running `activate.sh` in your project, the pipeline runs **automatically on every task**. You don't need to do anything — just talk to your AI assistant normally.

### How it works:

The `activate.sh` script creates this file in your project:

```
your-project/.agent/rules/antigravity_pipeline.md
```

Its YAML frontmatter contains:
```yaml
---
description: Antigravity 11-layer pipeline
alwaysApply: true
---
```

The `alwaysApply: true` flag tells the IDE to apply this rule on **every instruction**, not just when you type a specific command. The rule instructs the AI to run the pre-pipeline before doing work, and the post-pipeline after.

### What you see:

When you send any instruction (e.g., "Build me a login page"), the AI will:

1. Run the pre-pipeline (you'll see the 9-layer output in the terminal)
2. Read the results and adjust its approach
3. Do the actual work
4. Run the post-pipeline (you'll see the evaluation score)
5. Report results to you

---

## Manual Mode (/generate_code)

If you prefer manual control, use the `/generate_code` workflow command in your IDE. This is the same pipeline but triggered explicitly.

---

## CLI Mode

Run the pipeline directly from the terminal:

```bash
# Activate the Python environment
source ~/.antigravity/venv/bin/activate

# Pre-execution intelligence (layers 1-9)
python3 ~/.antigravity/run_pipeline.py --mode pre \
    --input "Build a REST API with JWT auth"

# Post-execution evaluation (layers 10-11)
python3 ~/.antigravity/run_pipeline.py --mode post \
    --input "Build a REST API with JWT auth" \
    --code-file /path/to/app.py

# Full pipeline (all 11 layers)
python3 ~/.antigravity/run_pipeline.py --mode full \
    --input "Build a REST API with JWT auth" \
    --code-file /path/to/app.py

# JSON output (for scripts and automation)
python3 ~/.antigravity/run_pipeline.py --mode full \
    --input "test" --json
```

### CLI Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--mode` | ✅ | `pre`, `post`, or `full` |
| `--input` / `-i` | ✅ | The user instruction text |
| `--code-file` | ❌ (required for `post`/`full`) | Path to the main output file |
| `--json` | ❌ | Output results as JSON instead of formatted table |

---

## Reading Pipeline Output

### Pre-Pipeline (Layers 1-9)

Key fields to pay attention to:

| Layer | What to look for |
|-------|-----------------|
| **L1** | `Intent` — what category was detected? `confidence` — how sure? |
| **L3** | `memories found` — were similar past tasks retrieved? |
| **L4** | `Complexity` — 0-100. `Strategy` — linear/parallel/conditional |
| **L6** | `Nodes skipped` — which workflow steps were skipped and why |
| **L7** | `Skill` + `confidence` — which skill was matched |
| **L9** | `Healthy` — how many MCP servers are actually running |

### Post-Pipeline (Layers 10-11)

| Layer | What to look for |
|-------|-----------------|
| **L10** | `Score` — overall quality (0-100%). `Safety` — passed/failed |
| **L11** | `State version` — backup count. `Trend` — improving/declining |

---

## Pipeline Guidance JSON

After every pre-pipeline run, the structured results are written to:

```
~/.antigravity/state/pipeline_guidance.json
```

This file contains the full output of all layers as a JSON object. You can use this for:
- Programmatic integration with other tools
- Custom dashboards
- Automated CI/CD quality gates
