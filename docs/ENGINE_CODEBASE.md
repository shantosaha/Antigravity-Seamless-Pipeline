# Engine Codebase Walkthrough

A developer guide to the Python modules that power the 11-layer pipeline.

---

## File Overview

| File | Lines | Layers | Classes |
|------|-------|--------|---------|
| `ingress.py` | 644 | L1, L2, L3 | `IntentParser`, `ContextManager`, `KnowledgeRetrieval` |
| `processing.py` | 837 | L4, L5, L6, L7, L8 | `TaskPlanner`, `PolicyEngine`, `WorkflowRunner`, `SkillRouter`, `ToolCache` |
| `egress.py` | 762 | L9, L10, L11 | `MCPInterface`, `OutputEvaluator`, `StateManager` |
| `orchestrator.py` | 317 | — | `PipelineOrchestrator`, `ServiceSingleton`, `CircuitBreaker` |
| `__init__.py` | 12 | — | Layer registry |
| **Total** | **2,815** | **11** | **12** |

---

## Entry Point: `run_pipeline.py`

The CLI runner (243 lines) that invokes the orchestrator:

```python
# Simplified flow:
args = parse_args()          # --mode, --input, --code-file, --json
orchestrator = PipelineOrchestrator()
results = orchestrator.run(mode=args.mode, user_input=args.input, code_path=args.code_file)
display(results)             # Formatted table or JSON
```

---

## `orchestrator.py` — The Brain

### `ServiceSingleton`

Manages shared connections (Qdrant, Redis) as singletons to avoid reconnecting per layer:

```python
class ServiceSingleton:
    _qdrant = None
    _redis = None

    @classmethod
    def get_qdrant(cls):
        if cls._qdrant is None:
            cls._qdrant = QdrantClient(host="localhost", port=6333)
        return cls._qdrant
```

### `CircuitBreaker`

Wraps external service calls. If a service fails 3 times in a row, the circuit "opens" and subsequent calls skip the service for 60 seconds:

```python
class CircuitBreaker:
    def call(self, fn, *args):
        if self.state == "open" and time.time() - self.last_failure < 60:
            return None  # Skip — circuit is open
        try:
            result = fn(*args)
            self.failures = 0
            return result
        except Exception:
            self.failures += 1
            if self.failures >= 3:
                self.state = "open"
```

### `PipelineOrchestrator.run()`

Orchestrates the full pipeline, running layers in sequence (with L2/L3 in parallel for speed):

```python
def run(self, mode, user_input, code_path=None):
    context = {"user_input": user_input, "code_path": code_path}

    if mode in ("pre", "full"):
        # L2 and L3 run in parallel (both read-only)
        with ThreadPoolExecutor() as pool:
            context.update(pool.submit(L2.process, context))
            context.update(pool.submit(L3.process, context))
        for layer in [L4, L5, L6, L7, L8, L9]:
            context.update(layer.process(context))

    if mode in ("post", "full"):
        for layer in [L10, L11]:
            context.update(layer.process(context))

    return context
```

---

## `ingress.py` — Input Processing

### `IntentParser` (Layer 1)

Key method: `process(context) → dict`

```python
def process(self, context):
    text = context["user_input"].lower()
    scores = {}
    for intent, keywords in self._INTENT_KEYWORDS.items():
        score = sum(w * text.count(k) for k, w in keywords.items())
        scores[intent] = score
    best = max(scores, key=scores.get)
    return {"intent_type": best, "confidence": scores[best] / sum(scores.values())}
```

### `ContextManager` (Layer 2)

Scans the project directory, ranks files by intent relevance, and loads them within a token budget. Uses Redis to cache file content hashes.

### `KnowledgeRetrieval` (Layer 3)

3-strategy memory retrieval from Qdrant:

```python
def _retrieve_memories(self, text):
    vector = self._vectorize(text)       # TF-IDF char n-grams
    results = []
    results += self._vector_search(vector)        # Strategy 1: vector similarity
    results += self._tfidf_cosine_search(text)     # Strategy 2: TF-IDF cosine
    results += self._ngram_jaccard_search(text)    # Strategy 3: n-gram overlap
    return deduplicate(results)
```

---

## `processing.py` — Planning & Routing

### `TaskPlanner` (Layer 4)

- Scores complexity (0-100) using weighted keyword analysis
- Selects strategy: linear (<30), parallel (30-60), conditional (60+)
- Builds LangGraph dynamically from `workflows/code_generation.yaml`

### `PolicyEngine` (Layer 5)

- Loads `policy/rules.yaml`
- Scans code context for banned patterns (12+)
- Injects dynamic rules based on intent (e.g., auth → bcrypt)

### `WorkflowRunner` (Layer 6)

- Iterates through YAML workflow nodes
- Evaluates conditions against pipeline context
- Tracks status per node: `completed`, `skipped`, with reasons

### `SkillRouter` (Layer 7)

- **[NEW] Local Experience API**: Intercepts routing to query `experiences.json` for 32-Agent confident historical patterns.
- Reads all `SKILL.md` files for static fallback matching
- Builds TF-IDF vectors from descriptions
- Returns top match + secondary match with confidence scores

### `ToolCache` (Layer 8)

- Normalizes task key → Redis lookup
- On hit: returns cached guidance (skips layers 1-7 on next call)
- On miss: stores current guidance with 24h TTL

---

## `egress.py` — Output & Persistence

### `MCPInterface` (Layer 9)

- Reads `mcp/servers.yaml`
- 3-strategy health probes: `pgrep`, `socket.connect_ex`, `shutil.which`
- Returns server health map: `{name: "running" | "installed" | "down"}`

### `OutputEvaluator` (Layer 10)

- **Safety** (40%): Pattern matching against banned functions
- **Alignment** (30%): TF-IDF cosine between instruction and output
- **Structure** (30%): AST analysis — function/class count, cyclomatic complexity

### `StateManager` (Layer 11)

- **[NEW] Experience API Trainer**: Injects successful execution logs, tools utilized, and scores back into the 32-agent storage `exp_api.record()` layer.
- **Versioned writes**: `state_v{N}.json` backup → write → prune old versions
- **File locking**: `fcntl.flock(f, LOCK_EX)` during writes
- **Rollback**: If write fails, restore from latest `state_v{N}.json`
- **Qdrant storage**: Store task embedding + metadata for future retrieval
- **Redis telemetry**: Log timing, scores, and skill usage

---

## Adding a Layer 12

To add your own layer:

### 1. Create a class with a `process()` method:

```python
class MyCustomLayer:
    def __init__(self):
        self.name = "My Custom Layer"
        self.layer_num = 12

    def process(self, context):
        # Your logic here
        result = do_something(context["user_input"])
        return {"my_custom_output": result}
```

### 2. Register it in `__init__.py`:

```python
from .egress import MCPInterface, OutputEvaluator, StateManager
from .my_module import MyCustomLayer

LAYERS = {
    # ... existing layers ...
    12: MyCustomLayer,
}
```

### 3. Add it to the orchestrator's layer sequence in `orchestrator.py`.

### 4. Add a display entry in `run_pipeline.py`'s `_get_highlights()` function.
