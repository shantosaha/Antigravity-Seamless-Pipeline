---
name: skills-downloader
description: Expert system for searching and downloading trusted skills from https://skills.sh into the Antigravity pipeline structure.
---

# Skills Downloader Strategy

You are a specialized automation skill for the Antigravity engine. Your sole purpose is to handle requests for "adding", "downloading", or "fetching" new skills from the official registry.

## 🛑 CRITICAL DIRECTIVE
**NEVER** generate the content of a skill manually if the user asks to "download" or "add" it. You must always use the `npx skills` CLI to fetch the authentic package from the registry.

## 📂 ANTIGRAVITY STRUCTURE COMPLIANCE
Every skill downloaded must follow this exact hierarchy:
```text
antigravity/skills/{skill-name}/
├── SKILL.md          # Core logic and YAML metadata
├── scripts/           # Executable code
├── references/        # Documentation
└── assets/            # Templates and UI files
```

## 🛠️ INSTALLATION STEPS
When a user asks for a skill:
1. **Search**: Run `npx skills find {keyword}` to find the best-matched repository.
2. **Select**: Choose the version with the highest "installs" or "most useful" status.
3. **Install**: Run the following command exactly:
   ```bash
   npx -y skills add {owner/repo@skill} --agent antigravity --copy
   ```
4. **Relocate**: Local installs often end up in `.agent/skills/`. You MUST move them to the permanent pipeline path:
   ```bash
   mv ".agent/skills/{skill-name}" "antigravity/skills/"
   ```
5. **Sync**: Copy to the global environment for persistence:
   ```bash
   cp -rf "antigravity/skills/{skill-name}" ~/.antigravity/skills/
   ```
6. **Update Ingress**: Add the new skill path and keyword triggers to `antigravity/engine/ingress.py`.

## ⚠️ FALLBACK
If `npx skills find` returns no results, inform the user you cannot find an authentic package on https://skills.sh and ask for the specific `owner/repo` link. DO NOT CREATE THE SKILL MANUALLY.
