"""
Antigravity Engine — Egress Layers (9–11)
Layer 9:  MCP Server Interface  [v4: Live health probes + intent tools]
Layer 10: Output Evaluator      [v4: AST analysis + TF-IDF alignment + complexity]
Layer 11: State Store            [v4: Versioned state + file locking + searchable history]
"""

import os
import json
import re
import ast
import yaml
import fcntl
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any

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

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity as sk_cosine_sim
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False


def _load_yaml(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 9: MCP Server Interface  [v4: Live health probes + intent tools]
# ═══════════════════════════════════════════════════════════════════════════════
class MCPInterface:
    """[P3] MCP interface with live health probes and intent-aware recommendations."""

    # [P1] Intent-to-tool mapping for smarter recommendations
    _INTENT_TOOLS = {
        'auth': ["Use GitHub server for OAuth app config and secret management"],
        'database': ["Use SQLite server for local DB queries", "Consider Postgres MCP for production"],
        'api': ["Use Fetch server for external API testing"],
        'deploy': ["Use filesystem server for config file generation"],
        'k8s': ["Use filesystem server for manifest YAML generation"],
    }

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        self.config = _load_yaml(os.path.join(base_dir, 'mcp', 'servers.yaml'))
        self.servers = self.config.get('servers', [])

    def process(self, skill: dict[str, Any]) -> dict[str, Any]:
        required = skill.get('required_mcp_servers', [])
        available = self._get_available_servers()

        # [P3] Live health probes
        health_status = self._probe_health()
        healthy_servers = [name for name, status in health_status.items() if status == 'running']

        matched = [s for s in required if s in available]
        missing = [s for s in required if s not in available]

        tool_recommendations = self._recommend_tools(available, skill)

        return {
            "servers_configured": len(self.servers),
            "servers_available": available,
            "servers_healthy": healthy_servers,       # [P3]
            "health_status": health_status,            # [P3]
            "servers_required": required,
            "servers_matched": matched,
            "servers_missing": missing,
            "tool_recommendations": tool_recommendations,
            "all_requirements_met": len(missing) == 0,
        }

    def _get_available_servers(self) -> list[str]:
        return [s.get('name', '') for s in self.servers if s.get('name')]

    def _probe_health(self) -> dict[str, str]:
        """[P3] Check if each MCP server is actually running."""
        health = {}
        for server in self.servers:
            name = server.get('name', '')
            if not name:
                continue

            command = server.get('command', '')
            port = server.get('port')

            # Strategy 1: Check if the process is running by command name
            if command:
                try:
                    result = subprocess.run(
                        ['pgrep', '-f', command],
                        capture_output=True, timeout=2,
                    )
                    if result.returncode == 0:
                        health[name] = 'running'
                        continue
                except Exception:
                    pass

            # Strategy 2: Check if the port is open (for HTTP-based servers)
            if port:
                try:
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex(('localhost', int(port)))
                    sock.close()
                    if result == 0:
                        health[name] = 'running'
                        continue
                except Exception:
                    pass

            # Strategy 3: Check for well-known MCP binaries
            if command:
                binary = command.split()[0] if command else ''
                if shutil.which(binary):
                    health[name] = 'installed'
                    continue

            health[name] = 'down'
        return health

    def _recommend_tools(self, available: list[str], skill: dict) -> list[str]:
        recommendations = []

        # Base recommendations
        if 'filesystem' in available:
            recommendations.append("MCP: Use filesystem server for file read/write operations")
        if 'github' in available:
            recommendations.append("MCP: GitHub server available for repository operations")
        if 'fetch' in available:
            recommendations.append("MCP: Fetch server available for HTTP requests")
        if 'sqlite' in available:
            recommendations.append("MCP: SQLite server available for database queries")

        # [P1] Intent-specific recommendations
        skill_name = skill.get('skill_matched', '').lower()
        for intent_kw, tools in self._INTENT_TOOLS.items():
            if intent_kw in skill_name:
                for tool in tools:
                    recommendations.append(f"MCP-INTENT: {tool}")

        # Missing server warnings
        for m in skill.get('required_mcp_servers', []):
            if m not in available:
                recommendations.append(f"WARNING: Skill requires '{m}' MCP server but it's not configured")

        return recommendations


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 10: Output Evaluator  [v4: AST analysis + TF-IDF alignment + complexity]
# ═══════════════════════════════════════════════════════════════════════════════
class OutputEvaluator:
    """Evaluates output with AST analysis, TF-IDF alignment, and complexity metrics."""

    BANNED_PATTERNS = [
        'eval(', 'exec(', "__import__('os').system", 'subprocess.call',
        'os.system(', 'pickle.loads(', 'yaml.load(',
        'dangerouslySetInnerHTML', 'innerHTML =',
    ]

    # [P1] Graduated severity
    PATTERN_SEVERITY = {
        'eval(': 1.0, 'exec(': 1.0, "__import__('os').system": 1.0,
        'subprocess.call': 0.8, 'os.system(': 0.9, 'pickle.loads(': 0.7,
        'yaml.load(': 0.4, 'dangerouslySetInnerHTML': 0.6, 'innerHTML =': 0.3,
    }

    def __init__(self, base_dir: str) -> None:
        self.config = _load_yaml(os.path.join(base_dir, 'evaluator', 'evaluator.yaml'))
        self.criteria = self.config.get('criteria', {})
        self.auto_reject_below = self.config.get('auto_reject_below', 0.6)

    def process(self, code_output: str, intent: dict, workflow: dict) -> dict[str, Any]:
        quality_result = self._score_quality(code_output, intent, workflow)
        safety_check = self._check_safety(code_output)
        performance_check = self._check_performance(code_output)
        alignment = self._check_intent_alignment(code_output, intent)  # [P1]

        overall = round((quality_result['score'] + safety_check['score'] +
                         performance_check['score'] + alignment['score']) / 4, 4)
        passed = overall >= self.auto_reject_below and safety_check['passed']

        improvements = self._suggest_improvements(quality_result, safety_check,
                                                   performance_check, alignment, code_output)
        return {
            "overall_score": overall,
            "passed": passed,
            "quality_score": quality_result['score'],
            "quality_breakdown": quality_result['breakdown'],
            "safety": safety_check,
            "performance": performance_check,
            "intent_alignment": alignment,           # [P1]
            "improvements": improvements,
            "auto_reject_threshold": self.auto_reject_below,
            "evaluation_method": self.config.get('evaluation_method', 'custom'),
        }

    def _check_intent_alignment(self, code: str, intent: dict) -> dict:
        """[P2] Check alignment using TF-IDF cosine similarity + keyword coverage."""
        raw = intent.get('raw_input', '').lower()
        code_lower = code.lower()

        # Method 1: Keyword coverage (fast baseline)
        keywords = set(re.findall(r'\b[a-z]{4,}\b', raw))
        stops = {'with', 'that', 'this', 'from', 'have', 'will', 'your', 'using',
                 'build', 'create', 'make', 'implement', 'full', 'stack', 'include',
                 'should', 'also', 'each', 'every', 'more', 'some', 'very', 'need',
                 'want', 'like', 'please', 'just', 'only', 'well', 'good'}
        keywords -= stops
        matched = [kw for kw in keywords if kw in code_lower]
        total = len(keywords) if keywords else 1
        keyword_ratio = len(matched) / total

        # Method 2: [P2] TF-IDF cosine similarity (semantic alignment)
        tfidf_score = 0.0
        if SKLEARN_OK and code and raw:
            try:
                vectorizer = TfidfVectorizer(
                    analyzer='word', ngram_range=(1, 2),
                    max_features=300, stop_words='english'
                )
                matrix = vectorizer.fit_transform([raw, code[:5000]])
                tfidf_score = float(sk_cosine_sim(matrix[0], matrix[1])[0][0])
            except Exception:
                pass

        # Composite: 40% keyword + 60% TF-IDF (semantic is more important)
        if tfidf_score > 0:
            composite = 0.4 * keyword_ratio + 0.6 * tfidf_score
        else:
            composite = keyword_ratio

        return {
            "score": round(min(composite + 0.3, 1.0), 4),  # Generous baseline
            "keyword_coverage": round(keyword_ratio, 4),
            "tfidf_similarity": round(tfidf_score, 4),
            "keywords_checked": len(keywords),
            "keywords_found": len(matched),
            "missing_keywords": list(keywords - set(matched))[:5],
            "method": "tfidf+keywords" if tfidf_score > 0 else "keywords_only",
        }

    def _score_quality(self, code: str, intent: dict, workflow: dict) -> dict:
        """[P2] Score quality with multi-language structure detection."""
        breakdown = {}
        score = 0.0

        has_content = len(code) > 100
        breakdown['has_content'] = has_content
        if has_content:
            score += 0.2

        # [P2] AST-based structure detection for Python
        ast_result = self._analyze_ast(code)
        # Multi-language regex-based structure detection
        regex_structure = self._detect_structure_regex(code)
        has_structure = ast_result['has_structure'] or regex_structure['has_structure']
        breakdown['has_structure'] = has_structure
        breakdown['structure_detail'] = {
            "functions": ast_result.get('functions', 0) + regex_structure.get('functions', 0),
            "classes": ast_result.get('classes', 0) + regex_structure.get('classes', 0),
            "exports": regex_structure.get('exports', 0),
            "method": "ast+regex" if ast_result['has_structure'] else "regex_only",
        }
        if has_structure:
            score += 0.2

        has_docs = any(marker in code for marker in [
            '/**', '"""', '@param', '@returns', '@description',
            'Args:', 'Returns:', 'Raises:', '# ---'])
        breakdown['has_documentation'] = has_docs
        if has_docs:
            score += 0.2

        has_tests = bool(re.search(
            r'\b(?:test_|_test|Test|assert|expect\(|it\(|describe\(|should|pytest|jest|mocha)\b',
            code, re.IGNORECASE))
        breakdown['has_tests'] = has_tests
        if has_tests:
            score += 0.15

        has_logging = bool(re.search(
            r'\b(?:console\.|Logger|logging\.|log\.|try\s*[{:]|catch\s*[{(]|except\s|raise\s)\b', code))
        breakdown['has_error_handling'] = has_logging
        if has_logging:
            score += 0.15

        has_async = bool(re.search(r'\b(?:async|await|Promise|\.then\(|asyncio)\b', code))
        breakdown['uses_async'] = has_async
        if has_async:
            score += 0.05

        # [P2] Bonus for type annotations
        has_types = bool(re.search(
            r'(?::\s*(?:str|int|float|bool|list|dict|Any|Optional|Union)|interface\s+\w+|type\s+\w+\s*=)',
            code))
        breakdown['has_type_annotations'] = has_types
        if has_types:
            score += 0.05

        return {"score": min(score, 1.0), "breakdown": breakdown}

    def _analyze_ast(self, code: str) -> dict:
        """[P2] Use Python AST to accurately count functions, classes, and nesting."""
        result = {'has_structure': False, 'functions': 0, 'classes': 0,
                  'decorators': 0, 'max_depth': 0, 'long_functions': []}
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    result['functions'] += 1
                    result['decorators'] += len(node.decorator_list)
                    # Check function length
                    if hasattr(node, 'end_lineno') and node.end_lineno:
                        func_len = node.end_lineno - node.lineno
                        if func_len > 50:
                            result['long_functions'].append({
                                "name": node.name,
                                "lines": func_len,
                            })
                elif isinstance(node, ast.ClassDef):
                    result['classes'] += 1
            result['has_structure'] = (result['functions'] + result['classes']) > 0
        except (SyntaxError, ValueError):
            pass  # Not Python code
        return result

    def _detect_structure_regex(self, code: str) -> dict:
        """[P2] Regex-based structure detection for JS/TS and other languages."""
        result = {'has_structure': False, 'functions': 0, 'classes': 0, 'exports': 0}

        # JS/TS function declarations
        result['functions'] += len(re.findall(
            r'\b(?:function|async\s+function)\s+\w+', code))
        # Arrow functions assigned to variables
        result['functions'] += len(re.findall(
            r'\b(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?\(', code))
        # Class methods
        result['functions'] += len(re.findall(
            r'^\s+(?:async\s+)?\w+\s*\([^)]*\)\s*\{', code, re.MULTILINE))

        # Classes
        result['classes'] += len(re.findall(r'\bclass\s+\w+', code))

        # Exports
        result['exports'] = len(re.findall(
            r'\b(?:export\s+(?:default\s+)?(?:function|class|const|let)|module\.exports)', code))

        result['has_structure'] = (result['functions'] + result['classes']) > 0
        return result

    def _check_safety(self, code: str) -> dict:
        """[P1] Graduated safety scoring."""
        code_clean = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code_clean = re.sub(r'//.*$', '', code_clean, flags=re.MULTILINE)
        code_clean = re.sub(r'#.*$', '', code_clean, flags=re.MULTILINE)
        code_clean = re.sub(r'^\s*\*.*$', '', code_clean, flags=re.MULTILINE)

        violations = []
        total_penalty = 0.0
        for p in self.BANNED_PATTERNS:
            if p in code_clean:
                severity = self.PATTERN_SEVERITY.get(p, 0.5)
                violations.append({"pattern": p, "severity": severity})
                total_penalty += severity

        score = max(0, 1.0 - total_penalty)
        critical = any(v['severity'] >= 0.8 for v in violations)
        return {
            "score": round(score, 4),
            "passed": not critical,  # [P1] Only fail on critical violations
            "violations": violations,
            "total_penalty": round(total_penalty, 4),
        }

    def _check_performance(self, code: str) -> dict:
        """[P2] Performance analysis with cyclomatic complexity approximation."""
        score = 0.8
        issues = []
        metrics = {}

        # File size
        code_len = len(code)
        metrics['code_size_bytes'] = code_len
        if code_len > 50000:
            score -= 0.3
            issues.append("File exceeds 50KB — consider splitting")

        # Function count
        functions = re.findall(r'(?:function|def|class|=>)\s*\w*', code)
        metrics['functions_found'] = len(functions)
        score += min(len(functions) * 0.02, 0.2)

        # [P2] Cyclomatic complexity approximation
        # Count decision points: if, elif, else, for, while, case, catch, &&, ||
        decision_points = len(re.findall(
            r'\b(?:if|elif|else|for|while|case|catch|switch)\b|&&|\|\|', code))
        metrics['decision_points'] = decision_points
        avg_complexity = decision_points / max(len(functions), 1)
        metrics['avg_cyclomatic_complexity'] = round(avg_complexity, 2)
        if avg_complexity > 10:
            issues.append(f"High avg cyclomatic complexity ({avg_complexity:.1f}) — simplify logic")
            score -= 0.1

        # [P2] Per-function length analysis
        func_starts = [(m.start(), m.group()) for m in re.finditer(
            r'(?:function|def)\s+(\w+)', code)]
        long_funcs = []
        for i, (start, name) in enumerate(func_starts):
            end = func_starts[i + 1][0] if i + 1 < len(func_starts) else len(code)
            func_lines = code[start:end].count('\n')
            if func_lines > 50:
                long_funcs.append(f"{name} ({func_lines} lines)")
        if long_funcs:
            issues.append(f"Long functions: {', '.join(long_funcs[:3])}")
            score -= 0.05 * min(len(long_funcs), 3)
        metrics['long_functions'] = len(long_funcs)

        # Nesting depth
        max_indent = 0
        for line in code.split('\n'):
            stripped = line.lstrip()
            if stripped:  # Skip blank lines
                indent = len(line) - len(stripped)
                max_indent = max(max_indent, indent)
        metrics['max_nesting_depth'] = max_indent // 4
        if max_indent > 32:
            issues.append(f"Deep nesting ({max_indent // 4} levels) — refactor")
            score -= 0.1

        # [P2] Code-to-comment ratio
        total_lines = code.count('\n') + 1
        comment_lines = len(re.findall(r'^\s*(?://|#|\*|/\*)', code, re.MULTILINE))
        metrics['comment_ratio'] = round(comment_lines / max(total_lines, 1), 3)

        return {
            "score": round(min(max(score, 0), 1.0), 4),
            "functions_found": len(functions),
            "metrics": metrics,
            "issues": issues,
        }

    def _suggest_improvements(self, quality, safety, performance, alignment, code):
        improvements = []

        bd = quality.get('breakdown', {})
        if not bd.get('has_structure'):
            improvements.append("ADD: Use proper function/class structure")
        if not bd.get('has_documentation'):
            improvements.append("ADD: Include JSDoc/docstrings for public functions")
        if not bd.get('has_tests'):
            improvements.append("ADD: Include unit tests")
        if not bd.get('has_error_handling'):
            improvements.append("ADD: Add try/catch and error logging")

        for v in safety.get('violations', []):
            sev = v.get('severity', 0)
            pat = v.get('pattern', '')
            label = "CRITICAL" if sev >= 0.8 else "WARNING"
            improvements.append(f"{label} SECURITY: Remove '{pat}' (severity {sev})")

        for issue in performance.get('issues', []):
            improvements.append(f"PERF: {issue}")

        # [P1] Intent alignment suggestions
        missing = alignment.get('missing_keywords', [])
        if missing:
            improvements.append(f"ALIGNMENT: Code may be missing: {', '.join(missing)}")

        if not improvements:
            improvements.append("QUALITY: Code passes all checks — no improvements needed")
        return improvements


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 11: State Store  [v4: Versioned state + file locking + searchable history]
# ═══════════════════════════════════════════════════════════════════════════════
class StateManager:
    """[P3] Versioned state with file locking, trend analysis, and searchable history."""

    MAX_VERSIONS = 3  # [P3] Keep last 3 state versions

    def __init__(self, base_dir: str, qdrant_client=None, redis_client=None) -> None:
        self.base_dir = base_dir
        self.state_dir = os.path.join(base_dir, 'state')
        self.state_path = os.path.join(self.state_dir, 'state_store.json')
        self.telemetry_config = _load_yaml(os.path.join(base_dir, 'telemetry', 'metrics.yaml'))

        # [P0] Use shared clients from orchestrator
        self.qdrant = qdrant_client
        self.qdrant_connected = self.qdrant is not None

        self.redis_client = redis_client
        self.redis_connected = self.redis_client is not None

        # Fallback to own connections if no shared clients
        if not self.qdrant_connected and QDRANT_OK:
            try:
                self.qdrant = QdrantClient(host="localhost", port=6333, timeout=3)
                self.qdrant.get_collections()
                self.qdrant_connected = True
            except Exception:
                pass

        if not self.redis_connected and REDIS_OK:
            try:
                self.redis_client = redis_lib.Redis(
                    host='localhost', port=6379, db=1,
                    decode_responses=True, socket_timeout=2,
                )
                self.redis_client.ping()
                self.redis_connected = True
            except Exception:
                pass

    def process(self, intent: dict, evaluation: dict, pipeline_result: dict) -> dict[str, Any]:
        state_updated = self._update_state_store(intent, evaluation)
        memory_stored = self._store_task_memory(intent, evaluation, pipeline_result)
        telemetry_logged = self._log_telemetry(intent, evaluation)

        recent_history = self._load_recent_history()
        trends = self._compute_trends(recent_history)

        # [P3] Get version info
        version_info = self._get_version_info()

        return {
            "state_file_updated": state_updated,
            "state_file_path": self.state_path,
            "state_version": version_info.get('current_version', 0),  # [P3]
            "versions_kept": version_info.get('versions_kept', 0),    # [P3]
            "qdrant_memory_stored": memory_stored,
            "qdrant_connected": self.qdrant_connected,
            "redis_telemetry_stored": telemetry_logged,
            "redis_connected": self.redis_connected,
            "recent_history": recent_history,
            "trends": trends,
            "telemetry_provider": self.telemetry_config.get('provider', 'local'),
        }

    def _compute_trends(self, history: list[dict]) -> dict:
        """Compute trends from recent task history."""
        if len(history) < 2:
            return {"status": "insufficient_data", "tasks_analyzed": len(history)}

        scores = [h.get('score', 0) for h in history]
        avg = round(sum(scores) / len(scores), 4)
        latest = scores[-1] if scores else 0
        trend = "improving" if latest > avg else ("stable" if latest == avg else "declining")

        # Success rate
        passed = sum(1 for s in scores if s >= 0.6)
        success_rate = round(passed / len(scores), 2)

        # [P3] Most used skill
        skills_used = [h.get('skill', 'unknown') for h in history if h.get('skill')]
        most_used = max(set(skills_used), key=skills_used.count) if skills_used else 'unknown'

        return {
            "avg_score": avg,
            "latest_score": latest,
            "trend": trend,
            "success_rate": success_rate,
            "most_used_skill": most_used,             # [P3]
            "tasks_analyzed": len(history),
        }

    def _load_recent_history(self) -> list[dict]:
        try:
            with open(self.state_path, 'r') as f:
                state = json.load(f)
            return state.get('completed_steps', [])[-5:]
        except Exception:
            return []

    def _update_state_store(self, intent: dict, evaluation: dict) -> bool:
        """[P3] Update state with file locking and versioned backup."""
        try:
            # [P3] Create versioned backup BEFORE writing
            self._create_version_backup()

            # [P3] File locking for crash-safe writes
            with open(self.state_path, 'r+') as f:
                fcntl.flock(f, fcntl.LOCK_EX)  # Exclusive lock
                try:
                    state = json.load(f)

                    state['statistics']['total_tasks'] = state['statistics'].get('total_tasks', 0) + 1
                    if evaluation.get('passed', False):
                        state['statistics']['successful_tasks'] = state['statistics'].get('successful_tasks', 0) + 1
                    else:
                        state['statistics']['failed_tasks'] = state['statistics'].get('failed_tasks', 0) + 1

                    state['current_task'] = {
                        "type": intent.get('type', 'unknown'),
                        "input": intent.get('raw_input', '')[:200],
                        "score": evaluation.get('overall_score', 0),
                        "passed": evaluation.get('passed', False),
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }

                    # [P3] Richer history entries for searchable history
                    state['completed_steps'].append({
                        "task": intent.get('raw_input', '')[:100],
                        "type": intent.get('type', 'unknown'),
                        "skill": intent.get('type', 'unknown'),  # [P3] Track skill used
                        "score": evaluation.get('overall_score', 0),
                        "passed": evaluation.get('passed', False),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    state['completed_steps'] = state['completed_steps'][-20:]

                    # [P3] Track version number
                    state['state_version'] = state.get('state_version', 0) + 1

                    f.seek(0)
                    f.truncate()
                    json.dump(state, f, indent=2)
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)  # Release lock
            return True
        except Exception:
            # [P3] Attempt rollback on failure
            self._rollback_state()
            return False

    def _create_version_backup(self) -> None:
        """[P3] Create a versioned backup of the current state."""
        if not os.path.exists(self.state_path):
            return
        try:
            with open(self.state_path, 'r') as f:
                state = json.load(f)
            version = state.get('state_version', 0)
            backup_path = os.path.join(self.state_dir, f'state_v{version}.json')
            shutil.copy2(self.state_path, backup_path)

            # [P3] Clean old versions — keep only MAX_VERSIONS
            self._cleanup_old_versions()
        except Exception:
            pass

    def _cleanup_old_versions(self) -> None:
        """[P3] Remove old state versions, keeping only the last MAX_VERSIONS."""
        try:
            versions = []
            for f in os.listdir(self.state_dir):
                if f.startswith('state_v') and f.endswith('.json'):
                    try:
                        v = int(f.replace('state_v', '').replace('.json', ''))
                        versions.append((v, f))
                    except ValueError:
                        pass
            versions.sort(reverse=True)
            for _, fname in versions[self.MAX_VERSIONS:]:
                os.remove(os.path.join(self.state_dir, fname))
        except Exception:
            pass

    def _rollback_state(self) -> None:
        """[P3] Rollback to the most recent versioned state."""
        try:
            versions = []
            for f in os.listdir(self.state_dir):
                if f.startswith('state_v') and f.endswith('.json'):
                    try:
                        v = int(f.replace('state_v', '').replace('.json', ''))
                        versions.append((v, f))
                    except ValueError:
                        pass
            if versions:
                versions.sort(reverse=True)
                latest = versions[0][1]
                shutil.copy2(os.path.join(self.state_dir, latest), self.state_path)
        except Exception:
            pass

    def _get_version_info(self) -> dict:
        """[P3] Get current version number and count of kept versions."""
        try:
            with open(self.state_path, 'r') as f:
                state = json.load(f)
            current = state.get('state_version', 0)
            versions = [f for f in os.listdir(self.state_dir)
                        if f.startswith('state_v') and f.endswith('.json')]
            return {'current_version': current, 'versions_kept': len(versions)}
        except Exception:
            return {'current_version': 0, 'versions_kept': 0}

    def _store_task_memory(self, intent: dict, evaluation: dict, result: dict) -> bool:
        """[P3] Store task memory with richer payload for searchable history."""
        if not self.qdrant_connected:
            return False
        try:
            from engine.ingress import _text_to_vector, VECTOR_DIM
            collection = "antigravity_task_memory"
            collections = [c.name for c in self.qdrant.get_collections().collections]
            if collection not in collections:
                from qdrant_client.models import VectorParams, Distance
                self.qdrant.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
                )
            from qdrant_client.models import PointStruct
            point_id = abs(hash(intent['raw_input'] + intent.get('timestamp', ''))) % (2**63)
            self.qdrant.upsert(
                collection_name=collection,
                points=[PointStruct(
                    id=point_id,
                    vector=_text_to_vector(intent['raw_input']),
                    payload={
                        "task": intent['raw_input'][:200],
                        "type": intent['type'],
                        "skill": intent.get('type', 'unknown'),       # [P3] Searchable
                        "language": intent.get('language', ''),        # [P3] Searchable
                        "timestamp": intent.get('timestamp', ''),
                        "score": evaluation.get('overall_score', 0),
                        "passed": evaluation.get('passed', False),
                        "layers_executed": result.get('layers_completed', 0),
                    },
                )],
            )
            return True
        except Exception:
            return False

    def _log_telemetry(self, intent: dict, evaluation: dict) -> bool:
        if not self.redis_connected:
            return False
        try:
            key = f"ag:telemetry:{datetime.now(timezone.utc).strftime('%Y%m%d:%H%M%S')}"
            self.redis_client.setex(key, 86400, json.dumps({
                "task_type": intent.get('type', 'unknown'),
                "score": evaluation.get('overall_score', 0),
                "passed": evaluation.get('passed', False),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }))
            return True
        except Exception:
            return False
