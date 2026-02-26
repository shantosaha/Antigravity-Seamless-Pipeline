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
