"""
Antigravity Engine — Processing Layers (4–8)
Layer 4: Task Planner       [v4: Dynamic graph from workflow YAML]
Layer 5: Policy Engine      [v3: Context-aware dynamic rules + expanded bans]
Layer 6: Workflow Runner     [v4: YAML condition evaluation + status tracking]
Layer 7: Skill Router        [v4: TF-IDF semantic matching + multi-skill]
Layer 8: Tool Cache          [v3: Normalized keys + full guidance caching]
"""

import os
import re
import json
import hashlib
import yaml
import numpy as np
from datetime import datetime, timezone
from typing import Any

# ── Service imports with fallbacks ────────────────────────────────────────────
try:
    from langgraph.graph import StateGraph, END
    from typing_extensions import TypedDict
    LANGGRAPH_OK = True
except ImportError:
    LANGGRAPH_OK = False

try:
    import redis as redis_lib
    REDIS_OK = True
except ImportError:
    REDIS_OK = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity as sk_cosine_sim
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False

try:
    from skills.experience_api import get_experience_api
    EXP_API_OK = True
except ImportError:
    EXP_API_OK = False


def _load_yaml(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if path.endswith('.md'):
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[1]
    return yaml.safe_load(content) or {}


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 4: Task Planner  [v4: Dynamic graph from workflow YAML]
# ═══════════════════════════════════════════════════════════════════════════════

if LANGGRAPH_OK:
    class PlanState(TypedDict):
        current_node: str
        completed: list[str]
        task_type: str
        status: str


class TaskPlanner:
    """[P3] Dynamic LangGraph with complexity scoring and sub-task decomposition."""

    # [P1] Complexity multipliers
    _COMPLEXITY_KEYWORDS = {
        'authentication': 3, 'database': 3, 'docker': 2, 'deployment': 2,
        'api': 2, 'testing': 2, 'pagination': 1, 'rate limiting': 2,
        'websocket': 3, 'real-time': 3, 'caching': 2, 'logging': 1,
        'monitoring': 2, 'ci/cd': 2, 'kubernetes': 3, 'microservices': 3,
    }

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        self.config = _load_yaml(os.path.join(base_dir, 'planner', 'planner.yaml'))
        self.langgraph_available = LANGGRAPH_OK

    def process(self, intent: dict[str, Any], context: dict, knowledge: dict) -> dict[str, Any]:
        # [P1] Compute complexity score
        complexity = self._score_complexity(intent, context)
        strategy = self._select_strategy(intent, complexity)
        sub_tasks = self._decompose_subtasks(intent)
        graph_result = self._build_graph(intent)

        directives = self._generate_directives(intent, context, knowledge, strategy, sub_tasks)

        return {
            "langgraph_available": self.langgraph_available,
            "strategy_selected": strategy,
            "complexity_score": complexity,       # [P1] 0–100
            "sub_tasks": sub_tasks,               # [P1] Decomposed sub-tasks
            "graph_compiled": graph_result.get("compiled", False),
            "graph_nodes": graph_result.get("nodes", []),
            "graph_executed": graph_result.get("executed", False),
            "execution_result": graph_result.get("result", {}),
            "directives": directives,
            "engine": self.config.get('engine', 'langgraph'),
            "optimization_enabled": self.config.get('optimization', {}).get('enabled', False),
        }

    def _score_complexity(self, intent: dict, context: dict) -> int:
        """[P1] Score task complexity on 0–100 scale."""
        score = 0
        text = intent.get('raw_input', '').lower()

        # Word count component (0–20)
        wc = intent.get('word_count', 0)
        score += min(wc * 0.5, 20)

        # Keyword complexity (0–40)
        for kw, weight in self._COMPLEXITY_KEYWORDS.items():
            if kw in text:
                score += weight * 3

        # Context file count (0–20)
        file_count = context.get('project_files_found', 0)
        score += min(file_count * 0.1, 20)

        # Multi-intent bonus (0–20)
        if intent.get('secondary_intent'):
            score += 15

        return min(int(score), 100)

    def _select_strategy(self, intent: dict, complexity: int) -> str:
        """[P1] Select strategy based on complexity score."""
        if complexity < 15:
            return 'linear'
        elif complexity < 40:
            return 'parallel'
        else:
            return 'conditional'

    def _decompose_subtasks(self, intent: dict) -> list[str]:
        """[P1] Split input by conjunctions into sub-tasks."""
        raw = intent.get('raw_input', '')
        # Split on "and", "with", comma, "+"
        parts = re.split(r'\b(?:and|with|plus)\b|[,+]', raw, flags=re.IGNORECASE)
        parts = [p.strip() for p in parts if len(p.strip()) > 5]
        return parts if len(parts) > 1 else [raw]

    def _generate_directives(self, intent: dict, context: dict, knowledge: dict,
                              strategy: str, sub_tasks: list[str]) -> list[str]:
        directives = []

        # Context directives
        critical = context.get('critical_files', [])
        if critical:
            directives.append(f"CONTEXT: Reference these project files: {', '.join(critical[:6])}")

        # Memory directives
        memories = knowledge.get('retrieved_items', [])
        if memories:
            past = [m.get('text', '')[:60] for m in memories[:3]]
            directives.append(f"MEMORY: Similar past tasks: {past}")

        # Sub-task directives [P1]
        if len(sub_tasks) > 1:
            directives.append(f"DECOMPOSE: Task has {len(sub_tasks)} sub-tasks: {sub_tasks}")

        # Strategy directive
        strat_map = {
            'parallel': "STRATEGY: Use parallel execution — write code, tests, and docs simultaneously",
            'conditional': "STRATEGY: Use conditional branching — design before coding",
            'linear': "STRATEGY: Use linear execution — step by step",
        }
        directives.append(strat_map.get(strategy, strat_map['linear']))

        # Language
        lang = intent.get('language', 'javascript')
        directives.append(f"LANGUAGE: Primary language is {lang}")

        # Confidence warning [P1]
        conf = intent.get('confidence', 0)
        if conf < 0.3:
            directives.append("CAUTION: Low intent confidence — consider asking user for clarification")

        return directives

    def _build_graph(self, intent: dict) -> dict[str, Any]:
        """[P3] Build LangGraph DYNAMICALLY from workflow YAML."""
        if not self.langgraph_available:
            return {"compiled": False, "nodes": [], "reason": "langgraph not installed"}

        try:
            # [P3] Load workflow YAML to determine nodes
            wf_path = os.path.join(self.base_dir, 'workflows', 'code_generation.yaml')
            workflow = _load_yaml(wf_path)
            yaml_nodes = workflow.get('graph', {}).get('nodes', {})

            if not yaml_nodes:
                yaml_nodes = {
                    'understand': {'skill': 'analysis'},
                    'generate': {'skill': 'code_writer'},
                    'review': {'skill': 'reviewer'},
                }

            graph = StateGraph(PlanState)
            node_names = list(yaml_nodes.keys())

            # [P3] Create a node function for each YAML node
            for name in node_names:
                def make_fn(n):
                    def fn(state):
                        return {
                            "current_node": n,
                            "completed": state["completed"] + [n],
                            "status": f"executing_{n}",
                        }
                    return fn
                graph.add_node(name, make_fn(name))

            # [P3] Wire edges from YAML `next` fields
            graph.set_entry_point(node_names[0])
            for i, name in enumerate(node_names):
                node_cfg = yaml_nodes[name]
                next_val = node_cfg.get('next')

                if isinstance(next_val, str) and next_val in yaml_nodes:
                    graph.add_edge(name, next_val)
                elif isinstance(next_val, list):
                    # [P3] Conditional edges — always take first path for now
                    targets = [c.get('goto') for c in next_val if c.get('goto') in yaml_nodes]
                    if targets:
                        graph.add_edge(name, targets[0])
                    elif i + 1 < len(node_names):
                        graph.add_edge(name, node_names[i + 1])
                    else:
                        graph.add_edge(name, END)
                elif i + 1 < len(node_names):
                    graph.add_edge(name, node_names[i + 1])
                else:
                    graph.add_edge(name, END)

            compiled = graph.compile()
            result = compiled.invoke({
                "current_node": "start", "completed": [],
                "task_type": intent.get("type", "code_request"), "status": "pending",
            })

            return {
                "compiled": True,
                "nodes": node_names,
                "node_count": len(node_names),
                "source": "workflow_yaml",  # [P3] Shows it was built from YAML
                "executed": True,
                "result": {
                    "final_node": result.get("current_node"),
                    "completed_nodes": result.get("completed", []),
                    "final_status": result.get("status"),
                },
            }
        except Exception as e:
            return {"compiled": False, "nodes": [], "reason": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 5: Policy Engine  [v3: Context-aware + expanded bans]
# ═══════════════════════════════════════════════════════════════════════════════
class PolicyEngine:
    """Context-aware policy enforcement with expanded security patterns."""

    # [P1] Extended banned patterns
    BANNED_PATTERNS = [
        'eval(', 'exec(', "__import__('os').system", 'subprocess.call',
        'os.system(', 'pickle.loads(', 'yaml.load(',                    # [P1] New
        'dangerouslySetInnerHTML', 'innerHTML =',                       # [P1] XSS vectors
        'child_process', 'spawn(', 'execSync(',                        # [P1] Node.js injection
    ]

    # [P1] Severity levels (1-10)
    PATTERN_SEVERITY = {
        'eval(': 10, 'exec(': 10, "__import__('os').system": 10,
        'subprocess.call': 8, 'os.system(': 9, 'pickle.loads(': 8,
        'yaml.load(': 6, 'dangerouslySetInnerHTML': 7, 'innerHTML =': 5,
        'child_process': 7, 'spawn(': 6, 'execSync(': 8,
    }

    def __init__(self, base_dir: str) -> None:
        self.rules = _load_yaml(os.path.join(base_dir, 'policy', 'rules.yaml'))
        self.policies = _load_yaml(os.path.join(base_dir, 'policy', 'policy_engine.yaml'))

    def process(self, intent: dict, plan: dict, code_output: str = "",
                context: dict = None) -> dict[str, Any]:
        """Check constraints with context-aware dynamic rule injection."""
        # [P1] Inject dynamic rules based on context
        dynamic_rules = self._inject_context_rules(context or {})

        hard_violations = self._check_hard_constraints(intent, code_output)
        soft_suggestions = self._check_soft_constraints(intent)
        domain_checks = self._check_domain_rules(intent, code_output)

        # Compute severity score [P1]
        severity_total = sum(
            self.PATTERN_SEVERITY.get(v.split("'")[1] if "'" in v else v, 5)
            for v in hard_violations
        )

        enforced_rules = self._build_enforcement_directives(
            hard_violations, soft_suggestions, domain_checks, dynamic_rules)

        approved = len(hard_violations) == 0
        return {
            "approved": approved,
            "hard_violations": hard_violations,
            "soft_suggestions": soft_suggestions,
            "domain_checks": domain_checks,
            "dynamic_rules_injected": len(dynamic_rules),   # [P1]
            "severity_score": severity_total,                 # [P1]
            "enforced_rules": enforced_rules,
            "hard_rules_checked": len(self.rules.get('hard_constraints', [])),
            "soft_rules_checked": len(self.rules.get('soft_constraints', [])),
            "strict_mode": self.policies.get('enforcement', {}).get('strict_mode', True),
        }

    def _inject_context_rules(self, context: dict) -> list[str]:
        """[P1] Generate rules based on what Layer 2 found in the project."""
        dynamic = []
        critical_files = context.get('critical_files', [])
        contents = context.get('critical_contents', {})

        for f in critical_files:
            f_lower = f.lower()
            if '.env' in f_lower:
                dynamic.append("HARD: Never log, print, or expose environment variables or secrets")
                dynamic.append("HARD: Never commit .env files — ensure .gitignore includes .env")
            if 'dockerfile' in f_lower or 'docker-compose' in f_lower:
                dynamic.append("RECOMMEND: Use multi-stage Docker builds for smaller images")
                dynamic.append("RECOMMEND: Pin Docker image versions (avoid :latest in production)")
            if 'package-lock' in f_lower or 'yarn.lock' in f_lower:
                dynamic.append("RECOMMEND: Commit lock files for reproducible builds")

        # Scan contents for sensitive patterns
        for fname, content in contents.items():
            if any(secret in content.lower() for secret in ['password', 'secret', 'api_key', 'token']):
                if '.env' not in fname.lower():
                    dynamic.append(f"WARNING: File '{fname}' may contain hardcoded secrets — externalize to .env")

        return dynamic

    def _build_enforcement_directives(self, violations: list, suggestions: list,
                                       domain: list, dynamic: list) -> list[str]:
        directives = []

        # Hard rules MANDATORY
        directives.append("HARD: Do NOT use eval(), exec(), subprocess.call, os.system(), pickle.loads()")
        directives.append("HARD: Do NOT use dangerouslySetInnerHTML or innerHTML= without sanitization")
        if violations:
            for v in violations:
                directives.append(f"VIOLATION: {v} — must be fixed before submission")

        # Dynamic context-aware rules [P1]
        for d in dynamic:
            directives.append(d)

        # Soft rules
        for s in suggestions:
            directives.append(f"RECOMMEND: {s}")

        # Domain rules
        for d in domain:
            rule = d.get('rule', '')
            if rule == 'max_function_length':
                directives.append(f"STYLE: Keep functions under {d.get('max', 50)} lines")
            elif rule == 'require_type_hints':
                directives.append(f"STYLE: Use type hints for {', '.join(d.get('languages', []))}")

        return directives

    def _check_hard_constraints(self, intent: dict, code: str) -> list[str]:
        violations = []
        for rule in self.rules.get('hard_constraints', []):
            name = rule.get('rule', '')
            if name == 'max_tokens_per_request':
                limit = rule.get('value', 100000)
                tokens = intent.get('word_count', 0) * 4
                if tokens > limit:
                    violations.append(f"Token limit exceeded: {tokens} > {limit}")
            elif name == 'no_malicious_code' and code:
                code_clean = self._strip_comments(code)
                for pattern in self.BANNED_PATTERNS:
                    if pattern in code_clean:
                        violations.append(f"Banned pattern found: '{pattern}'")
        return violations

    @staticmethod
    def _strip_comments(code: str) -> str:
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
        code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'^\s*\*.*$', '', code, flags=re.MULTILINE)
        return code

    def _check_soft_constraints(self, intent: dict) -> list[str]:
        suggestions = []
        for rule in self.rules.get('soft_constraints', []):
            name = rule.get('rule', '')
            if name == 'prefer_async':
                suggestions.append("Consider using async patterns where possible")
            elif name == 'add_logging':
                suggestions.append("Ensure logging is implemented in all modules")
        return suggestions

    def _check_domain_rules(self, intent: dict, code: str) -> list[dict]:
        checks = []
        dev_rules = self.rules.get('domain_rules', {}).get('software_development', [])
        for rule in dev_rules:
            name = rule.get('rule', '')
            if name == 'max_function_length' and code:
                checks.append({"rule": name, "max": rule.get('value', 50), "action": rule.get('action', 'warn')})
            elif name == 'require_type_hints':
                checks.append({"rule": name, "languages": rule.get('languages', []), "action": rule.get('action', 'suggest')})
        return checks


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 6: Workflow Runner  [v4: YAML condition evaluation + status tracking]
# ═══════════════════════════════════════════════════════════════════════════════
class WorkflowRunner:
    """[P3] Executes workflows with YAML condition evaluation and status tracking."""

    # [P3] Condition evaluation map — maps YAML conditions to pipeline state checks
    _CONDITION_MAP = {
        'has_design': lambda ctx: ctx.get('complexity', 0) < 30,       # Simple tasks already have a mental model
        'needs_design': lambda ctx: ctx.get('complexity', 0) >= 30,    # Complex tasks need architecture
        'approved': lambda ctx: True,                                   # Always approve first pass
        'needs_revision': lambda ctx: False,                            # No revision in simulation
        # Agent ecosystem conditions
        'is_new_project': lambda ctx: ctx.get('intent_type', '') in ('requirement-clarifier', 'project-planner', 'skeleton-generator'),
        'needs_security_gate': lambda ctx: ctx.get('intent_type', '') in ('operator', 'devops-infra-coder'),
        'is_bug_fix': lambda ctx: ctx.get('intent_type', '') in ('debugger',),
        'is_feature': lambda ctx: ctx.get('intent_type', '') not in ('debugger', 'refactorer', 'documenter', 'tester'),
        'needs_review': lambda ctx: ctx.get('complexity', 0) >= 20,
    }

    # Maps Layer 1 intent types → flow names in agent_orchestration.yaml
    _AGENT_INTENT_MAP = {
        # Layer 0 intents → new_project flow (these all precede building)
        'requirement-clarifier': 'new_project',
        'project-planner':       'new_project',
        'prerequisite-scanner':  'new_project',
        'dependency-solver':     'new_project',
        'skeleton-generator':    'new_project',
        'task-decomposer':       'new_project',
        'context-memory-manager': 'new_project',
        'risk-detector':         'new_project',
        # Layer 1 foundation agents
        'architect':             'new_feature',
        'implementor-dispatcher':'new_feature',
        'critic':                'refactor_request',
        'debugger':              'bug_report',
        'synthesizer':           'learning_request',
        'operator':              'deployment_request',
        # Layer 2 implementation agents → new_feature flow
        'frontend-ui-engineer':      'new_feature',
        'backend-api-engineer':      'new_feature',
        'database-implementor':      'new_feature',
        'mobile-engineer':           'new_feature',
        'devops-infra-coder':        'deployment_request',
        'algorithm-engineer':        'new_feature',
        'ai-feature-builder':        'new_feature',
        'cli-scripting-engineer':    'new_feature',
        'realtime-systems-engineer': 'new_feature',
        'integration-glue-engineer': 'new_feature',
        # Layer 3 quality agents
        'tester':           'refactor_request',
        'documenter':       'documentation_request',
        'refactorer':       'refactor_request',
        'security-auditor': 'security_concern',
        # Layer 4 specialist agents
        'data-database-architect':    'new_feature',
        'api-integration-specialist': 'new_feature',
        'performance-engineer':       'performance_issue',
        'ai-ml-integration-specialist': 'new_feature',
        # Layer 5
        'orchestrator': 'new_project',
    }

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        self.workflows_dir = os.path.join(base_dir, 'workflows')

    def process(self, intent: dict, plan: dict) -> dict[str, Any]:
        workflow = self._load_workflow(intent['type'])
        if not workflow:
            return {"executed": False, "reason": "No matching workflow found"}

        strategy = plan.get('strategy_selected', 'linear')
        complexity = plan.get('complexity_score', 0)

        # [P3] Build evaluation context for YAML conditions
        eval_ctx = {
            'complexity': complexity,
            'strategy': strategy,
            'intent_type': intent.get('type', ''),
            'has_tests': 'test' in intent.get('raw_input', '').lower(),
        }

        nodes_executed = self._execute_nodes(workflow, strategy, complexity, eval_ctx)

        return {
            "executed": True,
            "workflow_name": workflow.get('name', 'unknown'),
            "workflow_version": workflow.get('version', '0.0.0'),
            "agent_mode": workflow.get('_agent_mode', False),         # [v5]
            "active_flow": workflow.get('_active_flow', ''),           # [v5]
            "total_nodes": len(workflow.get('graph', {}).get('nodes', {})),
            "nodes_executed": nodes_executed,
            "nodes_skipped": sum(1 for n in nodes_executed if n.get('status') == 'skipped'),
            "strategy_used": strategy,
            "complexity_score": complexity,
            "condition_evaluation": "yaml_based",     # [P3]
            "timeouts": workflow.get('timeouts', {}),
        }

    def _load_workflow(self, intent_type: str) -> dict:
        """[v5] Route agent-ecosystem intents to agent_orchestration.yaml,
        all other intents to code_generation.yaml."""
        # Check if this intent maps to the agent ecosystem workflow
        agent_flow = self._AGENT_INTENT_MAP.get(intent_type)
        if agent_flow:
            ag_path = os.path.join(self.workflows_dir, 'agent_orchestration.yaml')
            wf = _load_yaml(ag_path)
            if wf:
                # Inject the specific flow's stages as 'graph.nodes' so the
                # existing _execute_nodes logic can consume them uniformly.
                flow_stages = wf.get('flows', {}).get(agent_flow, {}).get('stages', [])
                nodes = {}
                for stage in flow_stages:
                    stage_key = f"stage_{stage['stage']}"
                    agents = stage.get('agents', [])
                    nodes[stage_key] = {
                        'skill': agents[0] if agents else 'unknown',
                        'description': stage.get('name', ''),
                        'agents': agents,
                        'parallel': stage.get('parallel', False),
                        'blocking': stage.get('blocking', False),
                        'note': stage.get('note', ''),
                    }
                    if stage.get('loop_back'):
                        nodes[stage_key]['loop_back'] = stage['loop_back']
                # Stitch nodes into a graph structure for WorkflowRunner compatibility
                wf['graph'] = {'nodes': nodes}
                wf['_active_flow'] = agent_flow
                wf['_agent_mode'] = True
                return wf

        # Default: code_generation workflow
        type_map = {'code_request': 'code_generation.yaml'}
        filename = type_map.get(intent_type, 'code_generation.yaml')
        return _load_yaml(os.path.join(self.workflows_dir, filename))

    def _execute_nodes(self, workflow: dict, strategy: str, complexity: int,
                       eval_ctx: dict) -> list[dict]:
        """[P3] Execute nodes with YAML condition evaluation."""
        graph = workflow.get('graph', {})
        nodes = graph.get('nodes', {})
        timeouts = workflow.get('timeouts', {})
        executed = []

        for node_name, node_config in nodes.items():
            next_val = node_config.get('next')

            # [P3] Evaluate YAML conditions to decide if this node should run
            should_run = True
            skip_reason = ""

            # Check if this node is reached via a condition
            if isinstance(next_val, list):
                # This node HAS conditions on its outputs — always run it
                pass

            # [P3] Check if upstream conditions skip this node
            if node_name == 'create_architecture':
                # The YAML says: understand_requirements → has_design → skip architecture
                if self._eval_condition('has_design', eval_ctx):
                    should_run = False
                    skip_reason = f"Condition 'has_design' is true (complexity {complexity} < 30)"

            if not should_run:
                executed.append({
                    "node": node_name,
                    "skill": node_config.get('skill', 'unknown'),
                    "description": node_config.get('description', ''),
                    "status": "skipped",
                    "reason": skip_reason,
                    "parallel_tasks": [],
                    "timeout": timeouts.get(node_name, 'none'),
                })
                continue

            # Include parallel tasks based on strategy
            parallel = node_config.get('parallel', [])
            if strategy == 'linear':
                parallel = []

            # [P3] Track max_iterations from YAML conditions
            max_iter = None
            if isinstance(next_val, list):
                for cond in next_val:
                    if cond.get('max_iterations'):
                        max_iter = cond['max_iterations']

            entry = {
                "node": node_name,
                "skill": node_config.get('skill', 'unknown'),
                "description": node_config.get('description', ''),
                "status": "completed",
                "parallel_tasks": parallel,
                "timeout": timeouts.get(node_name, 'none'),
            }
            # [v5] Preserve agent-ecosystem metadata when running in agent mode
            if node_config.get('agents'):
                entry["agents"] = node_config['agents']
            if node_config.get('blocking'):
                entry["blocking"] = node_config['blocking']
            if node_config.get('note'):
                entry["note"] = node_config['note']
            if node_config.get('loop_back'):
                entry["loop_back"] = node_config['loop_back']
            if max_iter:
                entry["max_iterations"] = max_iter

            executed.append(entry)

        return executed

    def _eval_condition(self, condition: str, ctx: dict) -> bool:
        """[P3] Evaluate a YAML condition against the pipeline context."""
        evaluator = self._CONDITION_MAP.get(condition)
        if evaluator:
            try:
                return evaluator(ctx)
            except Exception:
                return False
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 7: Skill Router  [v4: Experience API + TF-IDF semantic multi-skill fallback]
# ═══════════════════════════════════════════════════════════════════════════════
class SkillRouter:
    """Routes tasks to skills using 32-Agent Experience API + TF-IDF semantic fallback."""

    def __init__(self, base_dir: str, redis_client=None) -> None:
        self.skills_dir = os.path.join(base_dir, 'skills')
        self.redis = redis_client  # [P0] Shared Redis for skill cache
        self.skills = self._load_skills_cached()

    def _load_skills_cached(self) -> dict[str, dict]:
        """[P0] Load skills from cache if available, else scan disk."""
        if self.redis:
            try:
                cached = self.redis.get('ag:skills:registry')
                if cached:
                    return json.loads(cached)
            except Exception:
                pass

        skills = self._load_all_skills()

        # Cache for 7 days
        if self.redis and skills:
            try:
                self.redis.setex('ag:skills:registry', 604800, json.dumps(skills))
            except Exception:
                pass

        return skills

    def _load_all_skills(self) -> dict[str, dict]:
        skills = {}
        if not os.path.isdir(self.skills_dir):
            return skills
        for item in os.listdir(self.skills_dir):
            path = os.path.join(self.skills_dir, item)
            if os.path.isdir(path):
                for fn in ['SKILL.md', 'skill.yaml', 'skill.yml']:
                    candidate = os.path.join(path, fn)
                    if os.path.exists(candidate):
                        skill = _load_yaml(candidate)
                        if skill:
                            skill_name = skill.get('name', item)
                            skills[skill_name] = skill
                            if item != skill_name:
                                skills[item] = skill
                        else:
                            skills[item] = {"name": item, "version": "0.0.0", "_folder": item}
                        break
                else:
                    skills[item] = {"name": item, "version": "0.0.0", "_folder": item}
            elif item.endswith(('.yaml', '.yml', '.md')):
                skill = _load_yaml(path)
                if skill:
                    skills[skill.get('name', item)] = skill
        return skills

    def process(self, intent: dict, workflow_node: str = "") -> dict[str, Any]:
        """[P1] Return primary + secondary skills with confidence."""
        primary, secondary, pri_conf, sec_conf = self._match_multi_skill(intent)

        # Load skill instructions
        skill_instructions = ""
        secondary_instructions = ""
        if primary:
            skill_instructions = self._load_skill_md(primary)
        if secondary:
            secondary_instructions = self._load_skill_md(secondary)[:2000]  # Half budget for secondary

        return {
            "skills_available": list(set(s.get('name', k) for k, s in self.skills.items())),
            "skill_matched": primary.get('name', 'none') if primary else 'none',
            "skill_confidence": pri_conf,           # [P1]
            "secondary_skill": secondary.get('name', 'none') if secondary else 'none',  # [P1]
            "secondary_confidence": sec_conf,       # [P1]
            "skill_version": primary.get('version', '0.0.0') if primary else '0.0.0',
            "skill_capabilities": primary.get('capabilities', []) if primary else [],
            "skill_instructions": skill_instructions,
            "secondary_instructions": secondary_instructions,  # [P1]
            "required_mcp_servers": primary.get('requires', {}).get('mcp_servers', []) if primary else [],
            "required_knowledge": primary.get('requires', {}).get('knowledge', []) if primary else [],
            "output_schema": primary.get('output_schema', {}) if primary else {},
        }

    def _load_skill_md(self, skill: dict) -> str:
        """Load full SKILL.md content."""
        folder = skill.get('_folder', skill.get('name', ''))
        path = os.path.join(self.skills_dir, folder, 'SKILL.md')
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return f.read()[:6000]  # [P1] Increased to 6KB
            except Exception:
                pass
        return ""

    def _match_multi_skill(self, intent: dict) -> tuple:
        """[P2] Return (primary, secondary, pri_conf, sec_conf) using TF-IDF + fallback."""
        intent_type = intent.get('type', '')
        secondary_type = intent.get('secondary_intent', '')
        raw_input = intent.get('raw_input', '')

        # [NEW] Check Experience API first
        if EXP_API_OK:
            try:
                exp_api = get_experience_api()
                complexity_score = intent.get('word_count', 0)
                rec = exp_api.get_recommendation({
                    "task_type": intent_type,
                    "complexity": "HIGH" if complexity_score > 40 else "MEDIUM" if complexity_score > 15 else "LOW"
                })
                if rec.get("confidence", 0) > 0.8 and rec.get("skill") in self.skills:
                    primary = self.skills[rec["skill"]]
                    return primary, None, rec["confidence"], 0.0
            except Exception:
                pass

        # Strategy 1: Direct name match (exact)
        primary = self._match_single(intent_type)
        secondary = self._match_single(secondary_type) if secondary_type else None

        pri_conf = 1.0 if primary and intent_type in self.skills else 0.7
        sec_conf = 0.8 if secondary and secondary_type in self.skills else 0.5

        # Strategy 2: [P2] TF-IDF semantic matching if direct match fails or is low confidence
        if SKLEARN_OK and raw_input:
            tfidf_matches = self._tfidf_match(raw_input)
            if tfidf_matches:
                best_name, best_score = tfidf_matches[0]
                # Override primary if TF-IDF found a better match
                if not primary or (primary and pri_conf < 0.8 and best_score > 0.2):
                    if best_name in self.skills:
                        primary = self.skills[best_name]
                        pri_conf = round(min(best_score + 0.5, 1.0), 3)

                # Find secondary from TF-IDF
                if not secondary and len(tfidf_matches) > 1:
                    sec_name, sec_score = tfidf_matches[1]
                    if sec_name in self.skills and sec_score > 0.1:
                        secondary = self.skills[sec_name]
                        sec_conf = round(min(sec_score + 0.3, 0.9), 3)

        if not primary:
            pri_conf = 0.0
        if not secondary:
            sec_conf = 0.0

        return primary, secondary, pri_conf, sec_conf

    def _tfidf_match(self, user_input: str) -> list[tuple[str, float]]:
        """[P2] Match user input against all skill descriptions using TF-IDF cosine."""
        try:
            # Build a corpus: skill descriptions + user input
            skill_names = []
            descriptions = []
            for name, skill in self.skills.items():
                desc = skill.get('description', '')
                if desc and name == skill.get('name', name):  # Avoid duplicates
                    skill_names.append(name)
                    descriptions.append(desc)

            if not descriptions:
                return []

            # Add user input as last document
            all_docs = descriptions + [user_input]

            # Fit TF-IDF on the corpus
            vectorizer = TfidfVectorizer(
                analyzer='word',
                ngram_range=(1, 2),
                max_features=500,
                stop_words='english',
            )
            tfidf_matrix = vectorizer.fit_transform(all_docs)

            # Compare user input (last) against all skill descriptions
            user_vec = tfidf_matrix[-1]
            skill_vecs = tfidf_matrix[:-1]
            similarities = sk_cosine_sim(user_vec, skill_vecs)[0]

            # Rank by similarity
            ranked = sorted(zip(skill_names, similarities), key=lambda x: x[1], reverse=True)
            return [(name, round(float(score), 4)) for name, score in ranked if score > 0.05][:3]

        except Exception:
            return []

    def _match_single(self, intent_type: str) -> dict | None:
        """Match a single intent type to a skill."""
        if not intent_type:
            return None
        if intent_type in self.skills:
            return self.skills[intent_type]
        aliases = {'code_request': 'code_generation'}
        aliased = aliases.get(intent_type, '')
        if aliased and aliased in self.skills:
            return self.skills[aliased]
        for name, skill in self.skills.items():
            if intent_type.replace('-', '_') in name.replace('-', '_'):
                return skill
            if name.replace('-', '_') in intent_type.replace('-', '_'):
                return skill
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 8: Tool Cache  [v3: Normalized keys + full guidance caching]
# ═══════════════════════════════════════════════════════════════════════════════
class ToolCache:
    """Redis-backed caching with normalized keys and full guidance storage."""

    PREFIX = "ag:cache:"

    def __init__(self, base_dir: str, redis_client=None) -> None:
        self.redis_client = redis_client  # [P0] Shared client
        self.connected = self.redis_client is not None

        if not self.connected and REDIS_OK:
            try:
                self.redis_client = redis_lib.Redis(
                    host='localhost', port=6379, db=0,
                    decode_responses=True, socket_timeout=3,
                )
                self.redis_client.ping()
                self.connected = True
            except Exception:
                self.connected = False

    def process(self, intent: dict, skill: dict) -> dict[str, Any]:
        cache_key = self._make_key(intent['raw_input'])
        hit = False
        cached_result = None

        if self.connected:
            cached_result = self.redis_client.get(cache_key)
            hit = cached_result is not None

            if not hit:
                self.redis_client.setex(
                    cache_key, 7200,  # [P0] 2 hour TTL (up from 1h)
                    json.dumps({"type": intent['type'], "timestamp": intent['timestamp']}),
                )
            info = self.redis_client.info('stats')
            total_keys = self.redis_client.dbsize()
        else:
            info = {}
            total_keys = 0

        return {
            "redis_connected": self.connected,
            "cache_key": cache_key,
            "cache_hit": hit,
            "cached_result": cached_result,
            "total_cached_keys": total_keys,
            "cache_hits_total": info.get('keyspace_hits', 0),
            "cache_misses_total": info.get('keyspace_misses', 0),
        }

    def store_full_guidance(self, intent: dict, guidance: dict) -> bool:
        """[P0] Store full guidance JSON for instant replay on cache hit."""
        if not self.connected:
            return False
        try:
            key = self._make_guidance_key(intent['raw_input'])
            self.redis_client.setex(key, 86400, json.dumps(guidance))  # 24h
            return True
        except Exception:
            return False

    def get_full_guidance(self, raw_input: str) -> dict | None:
        """[P0] Retrieve full cached guidance if available."""
        if not self.connected:
            return None
        try:
            key = self._make_guidance_key(raw_input)
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    def _make_key(self, text: str) -> str:
        """[P0] Normalized cache key — case/punctuation insensitive."""
        normalized = self._normalize(text)
        digest = hashlib.md5(normalized.encode()).hexdigest()[:16]
        return f"{self.PREFIX}{digest}"

    def _make_guidance_key(self, text: str) -> str:
        normalized = self._normalize(text)
        digest = hashlib.md5(normalized.encode()).hexdigest()[:16]
        return f"{self.PREFIX}guidance:{digest}"

    @staticmethod
    def _normalize(text: str) -> str:
        """[P0] Normalize text: lowercase, strip punctuation, sort words."""
        clean = re.sub(r'[^a-z0-9\s]', '', text.lower())
        words = sorted(clean.split())
        return ' '.join(words)
