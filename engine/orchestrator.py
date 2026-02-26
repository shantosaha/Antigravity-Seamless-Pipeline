"""
Antigravity Engine — Pipeline Orchestrator
[v3: Singleton services + parallel L2/L3 + circuit breaker + full guidance cache]
"""

import time
import hashlib
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from engine.ingress import IntentParser, ContextManager, KnowledgeMemory
from engine.processing import TaskPlanner, PolicyEngine, WorkflowRunner, SkillRouter, ToolCache
from engine.egress import MCPInterface, OutputEvaluator, StateManager

# ── Service imports with fallbacks ────────────────────────────────────────────
try:
    from qdrant_client import QdrantClient
    QDRANT_OK = True
except ImportError:
    QDRANT_OK = False

try:
    import redis as redis_lib
    REDIS_OK = True
except ImportError:
    REDIS_OK = False


class CircuitBreaker:
    """[P0] Skip services that keep failing — avoids timeout waste."""

    def __init__(self, max_failures: int = 3, cooldown_s: float = 300):
        self.max_failures = max_failures
        self.cooldown_s = cooldown_s
        self._failures: dict[str, int] = {}
        self._tripped_at: dict[str, float] = {}

    def is_open(self, service: str) -> bool:
        """Returns True if we should SKIP this service (too many failures)."""
        if service not in self._tripped_at:
            return False
        elapsed = time.time() - self._tripped_at[service]
        if elapsed > self.cooldown_s:
            # Reset after cooldown
            self._failures.pop(service, None)
            self._tripped_at.pop(service, None)
            return False
        return True

    def record_failure(self, service: str):
        self._failures[service] = self._failures.get(service, 0) + 1
        if self._failures[service] >= self.max_failures:
            self._tripped_at[service] = time.time()

    def record_success(self, service: str):
        self._failures.pop(service, None)
        self._tripped_at.pop(service, None)


class ServicePool:
    """[P0] Singleton service pool — create connections once, share across layers."""

    def __init__(self, circuit: CircuitBreaker):
        self.circuit = circuit
        self.qdrant = None
        self.redis = None
        self.qdrant_ok = False
        self.redis_ok = False
        self._init_services()

    def _init_services(self):
        # Qdrant
        if QDRANT_OK and not self.circuit.is_open('qdrant'):
            try:
                self.qdrant = QdrantClient(host="localhost", port=6333, timeout=3)
                self.qdrant.get_collections()
                self.qdrant_ok = True
                self.circuit.record_success('qdrant')
            except Exception:
                self.qdrant_ok = False
                self.circuit.record_failure('qdrant')

        # Redis
        if REDIS_OK and not self.circuit.is_open('redis'):
            try:
                self.redis = redis_lib.Redis(
                    host='localhost', port=6379, db=0,
                    decode_responses=True, socket_timeout=2,
                )
                self.redis.ping()
                self.redis_ok = True
                self.circuit.record_success('redis')
            except Exception:
                self.redis_ok = False
                self.circuit.record_failure('redis')


class LayerResult:
    """Container for a single layer execution result."""

    def __init__(self, layer_num: int, name: str) -> None:
        self.layer_num = layer_num
        self.name = name
        self.data: dict[str, Any] = {}
        self.duration_ms: float = 0
        self.success: bool = False
        self.error: str = ""


class Pipeline:
    """
    Full 11-layer Antigravity pipeline orchestrator.
    [v3: Singleton services, parallel L2/L3, circuit breaker, guidance caching]
    """

    LAYER_NAMES = [
        "User Intent",
        "Context Manager",
        "Knowledge + Memory Retrieval",
        "Planner (LangGraph)",
        "Policy Engine + Rules",
        "Workflow Graph",
        "Skill Router",
        "Tool Cache (Redis)",
        "MCP Servers",
        "Evaluator",
        "State Store + Memory Update",
    ]

    PRE_LAYERS = {1, 2, 3, 4, 5, 6, 7, 8, 9}
    POST_LAYERS = {10, 11}

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        self.results: list[LayerResult] = []

        # [P0] Singleton services + circuit breaker
        self.circuit = CircuitBreaker(max_failures=3, cooldown_s=300)
        self.pool = ServicePool(self.circuit)

    def execute(self, raw_input: str, code_output: str = "",
                mode: str = "full") -> dict[str, Any]:
        """Execute pipeline layers based on mode."""
        self.results = []
        start_time = time.time()

        if mode == "full":
            active = self.PRE_LAYERS | self.POST_LAYERS
        elif mode == "pre":
            active = self.PRE_LAYERS
        elif mode == "post":
            active = self.POST_LAYERS
        else:
            active = self.PRE_LAYERS | self.POST_LAYERS

        # Shared state
        intent = {}
        context = {}
        knowledge = {}
        plan = {}
        policy = {}
        workflow = {}
        skill = {}
        cache = {}
        mcp = {}
        evaluation = {}

        # ── Layer 1: User Intent ──────────────────────────────────────────
        if 1 in active:
            intent = self._run_layer(1, lambda: IntentParser(
                self.base_dir).process(raw_input))

        # ── Layers 2+3: PARALLEL execution [P0] ──────────────────────────
        if 2 in active and 3 in active:
            context, knowledge = self._run_parallel_2_3(intent)
        elif 2 in active:
            context = self._run_layer(2, lambda: ContextManager(
                self.base_dir, redis_client=self.pool.redis).process(intent))
        elif 3 in active:
            knowledge = self._run_layer(3, lambda: KnowledgeMemory(
                self.base_dir, qdrant_client=self.pool.qdrant).process(intent))

        # ── Layer 4: Planner ──────────────────────────────────────────────
        if 4 in active:
            plan = self._run_layer(4, lambda: TaskPlanner(
                self.base_dir).process(intent, context, knowledge))

        # ── Layer 5: Policy [v3: receives context for dynamic rules] ─────
        if 5 in active:
            policy = self._run_layer(5, lambda: PolicyEngine(
                self.base_dir).process(intent, plan, code_output, context=context))

        # ── Layer 6: Workflow [v3: receives strategy from planner] ────────
        if 6 in active:
            workflow = self._run_layer(6, lambda: WorkflowRunner(
                self.base_dir).process(intent, plan))

        # ── Layer 7: Skill [v3: shared Redis for caching] ────────────────
        if 7 in active:
            skill = self._run_layer(7, lambda: SkillRouter(
                self.base_dir, redis_client=self.pool.redis).process(intent))

        # ── Layer 8: Cache [v3: shared Redis client] ─────────────────────
        if 8 in active:
            cache = self._run_layer(8, lambda: ToolCache(
                self.base_dir, redis_client=self.pool.redis).process(intent, skill))

        # ── Layer 9: MCP ─────────────────────────────────────────────────
        if 9 in active:
            mcp = self._run_layer(9, lambda: MCPInterface(
                self.base_dir).process(skill))

        # ── Layer 10: Evaluator ──────────────────────────────────────────
        if 10 in active:
            if not intent:
                intent = {"type": "code_request", "raw_input": raw_input,
                          "timestamp": "", "word_count": len(raw_input.split())}
            evaluation = self._run_layer(10, lambda: OutputEvaluator(
                self.base_dir).process(code_output, intent, workflow))

        # ── Layer 11: State [v3: shared Qdrant + Redis] ──────────────────
        if 11 in active:
            if not intent:
                intent = {"type": "code_request", "raw_input": raw_input,
                          "timestamp": "", "word_count": len(raw_input.split())}
            full_result = {"layers_completed": sum(1 for r in self.results if r.success)}
            _state = self._run_layer(11, lambda: StateManager(
                self.base_dir, qdrant_client=self.pool.qdrant, redis_client=self.pool.redis
            ).process(intent, evaluation, full_result))

        total_ms = round((time.time() - start_time) * 1000, 2)
        return self._build_report(total_ms, mode)

    def _run_parallel_2_3(self, intent: dict) -> tuple[dict, dict]:
        """[P0] Run Context Manager + Knowledge Memory concurrently."""
        context_data = {}
        knowledge_data = {}

        def run_context():
            return ContextManager(self.base_dir, redis_client=self.pool.redis).process(intent)

        def run_knowledge():
            return KnowledgeMemory(self.base_dir, qdrant_client=self.pool.qdrant).process(intent)

        with ThreadPoolExecutor(max_workers=2) as executor:
            ctx_future = executor.submit(run_context)
            know_future = executor.submit(run_knowledge)

            # Wrap Layer 2
            t0 = time.time()
            result2 = LayerResult(2, self.LAYER_NAMES[1])
            try:
                context_data = ctx_future.result(timeout=10)
                result2.data = context_data
                result2.success = True
            except Exception as e:
                result2.error = str(e)
            result2.duration_ms = round((time.time() - t0) * 1000, 2)
            self.results.append(result2)

            # Wrap Layer 3
            t1 = time.time()
            result3 = LayerResult(3, self.LAYER_NAMES[2])
            try:
                knowledge_data = know_future.result(timeout=10)
                result3.data = knowledge_data
                result3.success = True
            except Exception as e:
                result3.error = str(e)
            result3.duration_ms = round((time.time() - t1) * 1000, 2)
            self.results.append(result3)

        return context_data, knowledge_data

    def _run_layer(self, num: int, fn) -> dict:
        result = LayerResult(num, self.LAYER_NAMES[num - 1])
        t0 = time.time()
        try:
            result.data = fn()
            result.success = True
        except Exception as e:
            result.error = str(e)
            result.success = False
            result.data = {}
        result.duration_ms = round((time.time() - t0) * 1000, 2)
        self.results.append(result)
        return result.data

    def _build_report(self, total_ms: float, mode: str = "full") -> dict[str, Any]:
        layers_report = []
        for r in self.results:
            layers_report.append({
                "layer": r.layer_num,
                "name": r.name,
                "status": "✅ PASS" if r.success else "❌ FAIL",
                "duration_ms": r.duration_ms,
                "error": r.error if r.error else None,
                "data": r.data,
            })

        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        return {
            "summary": {
                "mode": mode,
                "total_layers": total,
                "layers_passed": passed,
                "layers_failed": total - passed,
                "all_passed": passed == total,
                "total_duration_ms": total_ms,
                "services": {   # [P0]
                    "qdrant": self.pool.qdrant_ok,
                    "redis": self.pool.redis_ok,
                },
            },
            "layers": layers_report,
        }
