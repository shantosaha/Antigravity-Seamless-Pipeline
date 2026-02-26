---
description: Use the Antigravity local workflow for code generation
---

**This is the MANDATORY workflow for ALL user instructions.** Every task MUST pass through the full 11-layer Antigravity pipeline (v4: P0–P3 optimized).

# Pre-Execution Pipeline (Layers 1–9)

Before doing ANY work, run the pipeline in `pre` mode to gather intelligence.

// turbo
1. **Run Pre-Pipeline**
   ```bash
   source ~/.antigravity/venv/bin/activate && python3 ~/.antigravity/run_pipeline.py --mode pre --input "${USER_INSTRUCTION}"
   ```
   Replace `<USER_INSTRUCTION>` with the user's actual instruction text (escaped for shell).

2. **Read Pipeline Output** — Check the pre-pipeline results:
   - **Layer 1 (Intent):** Type + confidence score + secondary intent + detected language
   - **Layer 2 (Context):** Intent-ranked critical files loaded within token budget
   - **Layer 3 (Knowledge):** Semantic TF-IDF memory retrieval from Qdrant (3-strategy: vector + cosine + n-gram)
   - **Layer 4 (Planner):** Complexity score (0-100), strategy, sub-task decomposition. Graph built dynamically from workflow YAML
   - **Layer 5 (Policy):** Approval status, hard/soft violations, context-aware dynamic rules
   - **Layer 6 (Workflow):** YAML condition evaluation — nodes skipped if conditions aren't met
   - **Layer 7 (Skill):** Primary + secondary skill via TF-IDF semantic matching with confidence
   - **Layer 8 (Cache):** Full guidance cache check — if hit, skip layers 1-7 next time
   - **Layer 9 (MCP):** Server availability + live health probes

3. **Read the Guidance JSON** — The pipeline writes `~/.antigravity/state/pipeline_guidance.json` with structured data for all layers. Use this to inform your approach:
   - Follow the **strategy** from Layer 4 (linear/parallel/conditional)
   - Respect all **rules** from Layer 5 — hard violations MUST be addressed
   - Use the matched **skill's instructions** from Layer 7
   - Reference **past memories** from Layer 3 for similar tasks

---

# Execution Phase (The Actual Work)

Follow the workflow graph from `~/.antigravity/workflows/code_generation.yaml`:

4. **Understand Requirements** (Node: `understand_requirements`)
   - Analyze the user request using the intent + confidence from Layer 1.
   - If confidence < 30%, ask clarifying questions.
   - Check sub-tasks from Layer 4 — complex tasks are split automatically.

5. **System Design** (Node: `create_architecture`)
   - **SKIPPED** if complexity < 30 (condition: `has_design` is true for simple tasks)
   - If `needs_design` (complexity ≥ 30), propose a high-level architecture.
   - List key components, data flow, and technologies.

6. **Generate Code** (Node: `generate_code`)
   - Execute in parallel where strategy allows:
     - Write the core logic (following matched skill's instructions).
     - Write unit tests.
     - Write documentation.
   - **ENFORCE** rules from `rules.yaml` + Layer 5's dynamic rules:
     - ❌ No `eval()`, `exec()`, `subprocess.call`, `os.system()`, `pickle.loads()`, `yaml.load()`
     - ❌ No `dangerouslySetInnerHTML`, `innerHTML =`, `child_process`, `execSync()`
     - ⚠️ Max 50 lines per function
     - ✅ Add logging and error handling
     - ✅ Prefer async patterns
     - ✅ Never log/expose environment variables if `.env` files are present

7. **Code Review** (Node: `code_review`)
   - Analyze code for bugs, performance, style violations.
   - Max 3 revision cycles (enforced by YAML `max_iterations: 3`).
   - Once `approved`, proceed to post-pipeline.

---

# Post-Execution Pipeline (Layers 10–11)

After completing the work, run the pipeline in `post` mode to evaluate and persist.

// turbo
8. **Run Post-Pipeline**
   ```bash
   source ~/.antigravity/venv/bin/activate && python3 ~/.antigravity/run_pipeline.py --mode post --input "${USER_INSTRUCTION}" --code-file "${PATH_TO_MAIN_OUTPUT_FILE}"
   ```
   Replace `<PATH_TO_MAIN_OUTPUT_FILE>` with the absolute path to the primary file you created/edited.

9. **Report Results** — Include in your final response:
   - The evaluation score from Layer 10 (AST analysis + TF-IDF alignment + complexity metrics)
   - Whether the output passed safety checks (graduated scoring)
   - State version and backup status from Layer 11

---

# Summary

```
PRE  → python run_pipeline.py --mode pre  --input "..."
WORK → Follow workflow nodes (understand → [design] → generate → review)
POST → python run_pipeline.py --mode post --input "..." --code-file "..."
```

Every instruction the user sends MUST follow this PRE → WORK → POST cycle.
