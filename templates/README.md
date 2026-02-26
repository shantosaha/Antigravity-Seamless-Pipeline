# Templates

These are the files that `activate.sh` installs into your project when you run:

```bash
bash ~/.antigravity/activate.sh
```

## Files

| Template | Installed To | Trigger |
|----------|-------------|---------|
| `antigravity_pipeline.md` | `.agent/rules/antigravity_pipeline.md` | **Automatic** — runs on every task (`alwaysApply: true`) |
| `generate_code.md` | `.agents/workflows/generate_code.md` | **Manual** — only when you type `/generate_code` |

## How They Work

### `antigravity_pipeline.md` (Auto-Run Rule)

This is the core mechanism. The `alwaysApply: true` YAML frontmatter tells the IDE to read and follow this rule on **every single interaction**. It instructs the AI to:

1. Run `run_pipeline.py --mode pre` before doing any work
2. Apply the pipeline's guidance (strategy, rules, skill, memories)
3. Run `run_pipeline.py --mode post` after finishing
4. Report evaluation scores

### `generate_code.md` (Manual Workflow)

This is the detailed step-by-step workflow for the `/generate_code` slash command. It includes the same pipeline calls plus additional structure for the "WORK" phase (understand → design → generate → review loop).

## Manual Installation

If you don't want to use `activate.sh`, copy these files manually:

```bash
# Create directories
mkdir -p your-project/.agent/rules
mkdir -p your-project/.agents/workflows

# Copy templates
cp templates/antigravity_pipeline.md your-project/.agent/rules/
cp generate_code.md your-project/.agents/workflows/
```
