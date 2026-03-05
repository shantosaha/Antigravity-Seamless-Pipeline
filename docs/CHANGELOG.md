# Changelog

All optimization tiers applied to the Antigravity Pipeline.

---

## P4 / v4 — 32-Agent Experience Ecosystem

**Layers upgraded:** 7, 11, Master Orchestrator

| Layer | What Changed |
|-------|-------------|
| **L7: Skill Router** | Intercepts static matching to query the Experience API. Overrides decisions with learned patterns if confidence > 0.8. |
| **L11: State Store** | Actively sends outcome data back to the Experience API (`exp_api.record()`) for continuous agent training. |
| **Orchestrator** | Agent 15 instruction set natively checks the JSON configurations and pattern recommendations before routing. |

---

## P3 — Polish & Reliability

**Layers upgraded:** 4, 6, 9, 11

| Layer | What Changed |
|-------|-------------|
| **L4: Task Planner** | LangGraph now builds dynamically from `code_generation.yaml` — add/remove nodes in YAML, graph updates automatically |
| **L6: Workflow Runner** | YAML conditions (`has_design`, `needs_design`, `approved`) evaluated against context. Nodes track status: completed/skipped with reasons |
| **L9: MCP Interface** | Live health probes via `pgrep` + `socket` + `which`. Reports `running`/`installed`/`down` per server |
| **L11: State Store** | Versioned state (`state_v{N}.json`), `fcntl.flock()` file locking, auto-rollback on failure, trend analysis with most-used skill |

---

## P2 — Intelligence

**Layers upgraded:** 3, 7, 10

| Layer | What Changed |
|-------|-------------|
| **L3: Knowledge Memory** | TF-IDF character n-gram vectorization + 3-strategy retrieval (vector, cosine, Jaccard) |
| **L7: Skill Router** | TF-IDF cosine similarity matching against skill descriptions instead of keyword lookup |
| **L10: Evaluator** | AST code analysis (function count, class count, cyclomatic complexity) + TF-IDF intent alignment scoring |

---

## P1 — Core Logic

**Layers upgraded:** 1, 2, 4, 5, 7

| Layer | What Changed |
|-------|-------------|
| **L1: Intent Parser** | Weighted keyword scoring with confidence, multi-intent detection, language aliases |
| **L2: Context Manager** | Intent-weighted file ranking, file-hash caching in Redis, dynamic token budget |
| **L4: Task Planner** | Complexity scoring (0-100) with strategy selection, sub-task decomposition |
| **L5: Policy Engine** | 12+ banned patterns with severity scoring, context-aware dynamic rule injection |
| **L7: Skill Router** | Secondary skill detection, skill instructions loading |

---

## P0 — Infrastructure

**Components upgraded:** Orchestrator, Layer 8

| Component | What Changed |
|-----------|-------------|
| **Orchestrator** | Singleton services (shared Qdrant/Redis connections), parallel L2/L3 execution |
| **Circuit Breaker** | Auto-skip failing services after 3 consecutive failures, 60s cooldown |
| **L8: Tool Cache** | Normalized cache keys, full guidance caching with 24h TTL |
| **Startup** | All services initialized once at pipeline start, not per-layer |
