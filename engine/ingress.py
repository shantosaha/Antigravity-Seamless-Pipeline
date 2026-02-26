"""
Antigravity Engine — Ingress Layers (1–3)
Layer 1: Intent Parser       [v3: Weighted scoring + confidence + multi-intent]
Layer 2: Context Manager     [v3: Intent-ranked files + file-hash cache]
Layer 3: Knowledge + Memory  [v4: TF-IDF semantic vectors + 3-strategy retrieval]
"""

import os
import re
import hashlib
import yaml
import numpy as np
from datetime import datetime, timezone
from typing import Any

# ── Semantic vectorizer [P2] ──────────────────────────────────────────────────
try:
    from sklearn.feature_extraction.text import HashingVectorizer
    from sklearn.metrics.pairwise import cosine_similarity as sk_cosine
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False

# ── Service imports with fallbacks ────────────────────────────────────────────
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_OK = True
except ImportError:
    QDRANT_OK = False

try:
    import redis as redis_lib
    REDIS_OK = True
except ImportError:
    REDIS_OK = False


VECTOR_DIM = 128

# [P2] Singleton TF-IDF hasher — character n-grams for semantic similarity
_HASHER = None
def _get_hasher():
    global _HASHER
    if _HASHER is None and SKLEARN_OK:
        _HASHER = HashingVectorizer(
            n_features=VECTOR_DIM,
            analyzer='char_wb',       # Character n-grams with word boundaries
            ngram_range=(2, 5),       # 2-to-5 char grams capture morphology
            alternate_sign=True,      # Reduce hash collisions
            norm='l2',                # L2 normalize for cosine similarity
        )
    return _HASHER


def _text_to_vector(text: str) -> list[float]:
    """[P2] Convert text to a semantic TF-IDF vector via character n-gram hashing.
    Falls back to SHA-512 hash vector if sklearn is unavailable."""
    hasher = _get_hasher()
    if hasher is not None:
        try:
            vec = hasher.transform([text.lower()]).toarray()[0]
            return vec.tolist()
        except Exception:
            pass
    # Fallback: deterministic hash vector
    digest = hashlib.sha512(text.encode()).hexdigest()
    vec = []
    for i in range(0, VECTOR_DIM * 2, 2):
        byte_val = int(digest[i % len(digest):i % len(digest) + 2], 16)
        vec.append((byte_val / 255.0) * 2 - 1)
    return vec[:VECTOR_DIM]


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """[P2] Compute cosine similarity between two vectors."""
    try:
        a_np = np.array(a)
        b_np = np.array(b)
        dot = np.dot(a_np, b_np)
        norm = np.linalg.norm(a_np) * np.linalg.norm(b_np)
        return float(dot / norm) if norm > 0 else 0.0
    except Exception:
        return 0.0


def _load_yaml(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as f:
        return yaml.safe_load(f) or {}


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 1: Intent Parser  [v3: Weighted scoring + confidence + multi-intent]
# ═══════════════════════════════════════════════════════════════════════════════
class IntentParser:
    """Parses raw user input with weighted keyword scoring and confidence."""

    # ── Language alias map [P1 upgrade] ────────────────────────────────────────
    LANG_ALIASES = {
        'python': 'python', 'py': 'python', 'django': 'python', 'flask': 'python',
        'fastapi': 'python', 'pytorch': 'python',
        'javascript': 'javascript', 'js': 'javascript', 'node': 'javascript',
        'node.js': 'javascript', 'nodejs': 'javascript', 'express': 'javascript',
        'react': 'javascript', 'vue': 'javascript', 'angular': 'javascript',
        'next.js': 'javascript', 'nextjs': 'javascript', 'deno': 'javascript',
        'html': 'javascript', 'web': 'javascript', 'css': 'javascript',
        'typescript': 'typescript', 'ts': 'typescript',
        'rust': 'rust', 'rs': 'rust', 'cargo': 'rust', 'tokio': 'rust',
        'go': 'go', 'golang': 'go',
        'swift': 'swift', 'swiftui': 'swift',
        'kotlin': 'kotlin', 'kt': 'kotlin',
        'java': 'java', 'spring': 'java',
        'c#': 'csharp', 'csharp': 'csharp', '.net': 'csharp',
        'ruby': 'ruby', 'rails': 'ruby',
        'php': 'php', 'laravel': 'php',
        'sql': 'sql', 'postgresql': 'sql', 'postgres': 'sql', 'mysql': 'sql',
    }

    def __init__(self, base_dir: str) -> None:
        self.schema = _load_yaml(os.path.join(base_dir, 'input', 'input_schema.yaml'))
        self.schemas = self.schema.get('schemas', {})
        self._kw_rules = self._build_weighted_rules()

    def process(self, raw_input: str) -> dict[str, Any]:
        """Classify intent with confidence and optional secondary intent."""
        primary, secondary, confidence = self._classify_intent(raw_input)
        language = self._detect_language(raw_input)
        return {
            "type": primary,
            "secondary_intent": secondary,        # [P1] Multi-intent
            "confidence": confidence,              # [P1] 0.0–1.0
            "raw_input": raw_input,
            "language": language,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "schema_matched": primary in self.schemas,
            "word_count": len(raw_input.split()),
        }

    # ── Weighted keyword rules [P1] ────────────────────────────────────────────
    def _build_weighted_rules(self) -> dict[str, list[tuple[str, int]]]:
        """Build keyword rules with weights: (keyword, weight).
        Higher weight = stronger signal for that intent."""
        return {
            'mcp-builder': [('mcp server', 5), ('mcp tool', 5), ('model context protocol', 5), ('mcp schema', 4)],
            'web-artifacts-builder': [('artifact', 4), ('web component', 4), ('interactive prototype', 4),
                                      ('html component', 3), ('calculator', 3), ('todo app', 3), ('utility tool', 2)],
            'docx': [('docx', 5), ('word document', 5), ('document generation', 4), ('office file', 3)],
            'pdf': [('pdf', 5), ('portable document', 4), ('generate pdf', 5), ('pdf export', 4)],
            'pptx': [('pptx', 5), ('slide deck', 4), ('powerpoint', 5), ('presentation', 3)],
            'xlsx': [('xlsx', 5), ('excel', 5), ('spreadsheet', 4), ('csv export', 3), ('table data', 2)],
            'theme-factory': [('generate theme', 5), ('mui theme', 5), ('tailwind config', 4),
                              ('css variables', 4), ('dark mode', 3), ('light mode', 3), ('theme toggle', 3)],
            'algorithmic-art': [('algorithmic art', 5), ('generative art', 5), ('p5.js', 4),
                                ('processing', 2), ('python turtle', 4), ('canvas art', 3)],
            'canvas-design': [('canvas', 3), ('webgl', 5), ('physics simulation', 4),
                              ('html5 game', 4), ('2d drawing', 3)],
            'skill-creator': [('create skill from scratch', 5), ('build a skill', 4),
                              ('write a skill file', 4), ('author new skill', 4)],
            'skills-downloader': [('download skill', 5), ('add skill', 4), ('fetch skill', 4),
                                  ('install skill', 4), ('npx skills', 3), ('grab skill', 3), ('new skill', 2), ('get skill', 3)],
            'accessibility-compliance': [('accessibility', 4), ('wcag', 5), ('aria', 4),
                                         ('a11y', 5), ('screen reader', 4), ('contrast ratio', 4)],
            'architecture-patterns': [('architecture', 3), ('system design', 4), ('infrastructure', 3),
                                      ('high level design', 4), ('monolith', 3), ('microservices', 3)],
            'auth-implementation-patterns': [('jwt', 5), ('oauth', 5), ('login', 3), ('authentication', 5),
                                             ('refresh token', 5), ('signup', 3), ('auth', 4), ('sessions', 3)],
            'competitive-landscape': [('competitors', 5), ('market analysis', 5), ('differentiation', 4),
                                      ('competitive strategy', 5), ('market research', 4)],
            'data-storytelling': [('reporting', 3), ('visualization', 3), ('dashboard', 3),
                                  ('charts', 3), ('data narrative', 5), ('insights', 2)],
            'database-migration': [('migration', 4), ('database schema', 4), ('alembic', 5),
                                   ('knex', 5), ('liquidbase', 5), ('database update', 3)],
            'e2e-testing-patterns': [('e2e', 5), ('playwright', 5), ('cypress', 5),
                                     ('end to end testing', 5), ('automated browser test', 4)],
            'fastapi-templates': [('fastapi', 5), ('pydantic', 4), ('uvicorn', 4),
                                  ('async api', 3), ('python api', 3)],
            'framer-motion-animator': [('framer motion', 5), ('transitions', 2), ('animations', 2),
                                       ('smooth ui', 2), ('framer', 4), ('motion design', 4)],
            'gdpr-data-handling': [('gdpr', 5), ('privacy', 3), ('pii', 5), ('compliance', 2),
                                   ('data protection', 4), ('right to be forgotten', 5)],
            'github-actions-templates': [('github actions', 5), ('ci/cd', 4), ('automation workflow', 3),
                                         ('github workflows', 5), ('deployment pipeline', 3)],
            'go-concurrency-patterns': [('goroutines', 5), ('channels', 4), ('go concurrency', 5),
                                        ('go parallelism', 4), ('golang', 3)],
            'google-cloud-agent-sdk-master': [('google cloud', 4), ('gcp', 5), ('vertex ai', 5),
                                              ('cloud integrations', 3)],
            'implement-design': [('figma', 5), ('design to code', 5), ('ui implementation', 4),
                                 ('pixel perfect', 4), ('mockup to code', 5)],
            'javascript-testing-patterns': [('jest', 5), ('vitest', 5), ('unit testing js', 4),
                                            ('mocha', 4), ('chai', 4), ('test runner', 3)],
            'k8s-manifest-generator': [('kubernetes', 5), ('k8s', 5), ('helm', 5),
                                       ('manifests', 4), ('cluster deployment', 4)],
            'langchain-architecture': [('langchain', 5), ('rag', 4), ('llm chains', 5),
                                       ('agents orchestration', 4), ('langsmith', 5)],
            'mcp-integration-expert': [('mcp integration', 5), ('external tool', 3),
                                       ('mcp client', 5), ('mcp host', 5)],
            'microservices-patterns': [('microservices', 5), ('distributed systems', 4),
                                       ('event driven', 3), ('service mesh', 5), ('docker compose', 3)],
            'modern-javascript-patterns': [('es6', 4), ('promises', 3), ('async javascript', 4),
                                            ('functional js', 4), ('math', 2), ('scientific', 2)],
            'nextjs-app-router-patterns': [('nextjs', 5), ('app router', 5), ('server components', 5),
                                            ('rsc', 5), ('nextjs page', 4)],
            'nodejs-backend-patterns': [('express', 3), ('nestjs', 5), ('backend development', 3),
                                        ('node server', 3), ('rest api', 3)],
            'postgresql-table-design': [('postgres', 4), ('sql design', 4), ('database indexing', 4),
                                        ('relational schema', 4), ('tuning', 2)],
            'prompt-engineering-patterns': [('prompt engineering', 5), ('system prompt', 5),
                                            ('instruction tuning', 4), ('chain of thought', 5)],
            'python-performance-optimization': [('python speed', 5), ('multiprocessing', 4),
                                                 ('python optimization', 5), ('cpython', 4), ('numba', 5)],
            'rag-implementation': [('retrieval augmented', 5), ('vector db', 5), ('embeddings search', 5),
                                   ('qdrant', 4), ('chroma', 5)],
            'react-native-architecture': [('react native', 5), ('expo mobile', 4),
                                           ('mobile architecture', 4), ('native mobile', 3)],
            'react-native-design': [('mobile ui', 3), ('mobile design', 3),
                                    ('native components', 3), ('mobile aesthetic', 3)],
            'react-performance-optimization': [('react performance', 5), ('react memo', 5),
                                                ('re-renders', 4), ('virtualization', 3)],
            'responsive-design': [('responsive', 4), ('mobile first', 4), ('media queries', 4),
                                  ('flexbox', 3), ('grid layout', 3)],
            'rust-async-patterns': [('tokio', 5), ('asynchronous rust', 5), ('memory safety', 3),
                                    ('borrow checker', 4)],
            'sast-configuration': [('sast', 5), ('security scanning', 5), ('vulnerability audit', 5),
                                   ('code scanning', 4)],
            'sendgrid-automation': [('sendgrid', 5), ('email automation', 5), ('transactional email', 4),
                                    ('email campaign', 4)],
            'startup-metrics-framework': [('startup metrics', 5), ('saas kpi', 5), ('cac', 4),
                                           ('ltv', 4), ('churn', 4), ('unit economics', 5)],
            'stripe-integration': [('stripe', 5), ('payments', 4), ('subscription billing', 5),
                                   ('checkout', 3), ('billing portal', 4)],
            'supabase-postgres-best-practices': [('supabase', 5), ('rls policies', 5),
                                                  ('supabase auth', 5), ('postgres rls', 5), ('postgrest', 4)],
            'tailwind-design-system': [('tailwind', 4), ('utility classes', 3),
                                       ('tailwind setup', 4), ('jit mode', 4)],
            'task-coordination-strategies': [('sub-agent', 5), ('task coordination', 5),
                                             ('complex planning', 4), ('agent swarm', 5)],
            'threejs-fundamentals': [('threejs', 5), ('3d rendering', 5), ('webgl scene', 5),
                                     ('shaders', 4), ('3d modeling', 3)],
            'vue3': [('vue 3', 5), ('composition api', 5), ('pinia', 5), ('vuex', 4), ('vite vue', 4)],
            'workflow-orchestration-patterns': [('temporal', 5), ('state machine', 4),
                                                ('orchestration', 3), ('workflow engine', 4)],
            # Generic fallback — low weights so specific intents always win
            'code_request': [('code', 1), ('build', 1), ('create', 1), ('app', 1), ('script', 1),
                             ('program', 1), ('update', 1), ('modify', 1), ('fix', 1)],
        }

    def _classify_intent(self, text: str) -> tuple[str, str, float]:
        """[P1] Weighted keyword scoring with confidence and secondary intent."""
        text_lower = text.lower()

        scores: dict[str, float] = {}
        for intent, rules in self._kw_rules.items():
            total = sum(weight for kw, weight in rules if kw in text_lower)
            if total > 0:
                scores[intent] = total

        if not scores:
            return 'code_request', '', 0.0

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = ranked[0][0]
        primary_score = ranked[0][1]

        # Secondary intent (if distinctly different and above threshold)
        secondary = ''
        if len(ranked) > 1 and ranked[1][1] >= 3:
            # Only if it's not a substring of primary
            if ranked[1][0] not in primary and primary not in ranked[1][0]:
                secondary = ranked[1][0]

        # Confidence: primary_score / max_possible for that intent
        max_possible = sum(w for _, w in self._kw_rules.get(primary, []))
        confidence = round(min(primary_score / max(max_possible, 1), 1.0), 3)

        return primary, secondary, confidence

    def _detect_language(self, text: str) -> str:
        """[P1] Detect language using expanded alias map."""
        text_lower = text.lower()
        # Check multi-word aliases first (longer matches = more specific)
        for alias in sorted(self.LANG_ALIASES.keys(), key=len, reverse=True):
            if alias in text_lower:
                return self.LANG_ALIASES[alias]
        return 'javascript'  # default


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 2: Context Manager  [v3: Intent-ranked files + file-hash cache]
# ═══════════════════════════════════════════════════════════════════════════════
class ContextManager:
    """Manages token budget, loads project context with intent-aware ranking."""

    # File relevance scoring by extension+name per intent keyword
    _RELEVANCE = {
        'docker':    {'.dockerfile': 10, 'dockerfile': 10, 'docker-compose': 10, '.dockerignore': 5},
        'database':  {'.sql': 10, 'schema': 8, 'migration': 8, 'migrate': 8, '.prisma': 8},
        'auth':      {'.env': 8, 'auth': 8, 'jwt': 8, 'passport': 8, 'session': 6},
        'api':       {'routes': 8, 'controller': 8, 'endpoint': 8, 'middleware': 7, 'handler': 7},
        'test':      {'.test.': 8, '.spec.': 8, 'test': 6, '__tests__': 8, 'jest': 7, 'pytest': 7},
        'config':    {'package.json': 9, 'requirements.txt': 9, 'makefile': 7, '.env': 8,
                      'tsconfig': 7, '.eslintrc': 5, 'vite.config': 6, 'webpack': 6},
        'deploy':    {'kubernetes': 8, 'k8s': 8, 'helm': 8, 'terraform': 8, 'ansible': 8, 'ci': 7},
    }

    def __init__(self, base_dir: str, redis_client=None) -> None:
        self.base_dir = base_dir
        self.config = _load_yaml(os.path.join(base_dir, 'context', 'context_manager.yaml'))
        self.token_budget = self.config.get('token_budget', 190000)
        self.priorities = self.config.get('priorities', {})
        self.redis = redis_client  # [P0] Shared Redis for file-hash cache

    def process(self, intent: dict[str, Any]) -> dict[str, Any]:
        """Load and prioritize context with intent-aware ranking."""
        project_files = self._scan_project_files()
        estimated_tokens = self._estimate_tokens(intent['raw_input'])

        # [P1] Rank files by relevance to intent BEFORE deciding which to read
        ranked_files = self._rank_files_by_intent(project_files, intent)
        critical_files = [f for f, _score in ranked_files[:8]]

        # [P1] Read contents of top-ranked files (dynamic budget: 10% of token budget)
        read_budget = int(self.token_budget * 0.1)  # ~19,000 chars
        per_file_budget = max(read_budget // max(len(critical_files), 1), 1000)
        critical_contents = {}
        total_read = 0
        for f in critical_files:
            if total_read >= read_budget:
                break
            full_path = os.path.join(self.base_dir, f)
            content = self._read_with_cache(full_path, per_file_budget)
            if content:
                critical_contents[f] = content
                total_read += len(content)

        return {
            "token_budget": self.token_budget,
            "tokens_used": estimated_tokens,
            "tokens_remaining": self.token_budget - estimated_tokens,
            "utilization": round(estimated_tokens / self.token_budget, 4),
            "project_files_found": len(project_files),
            "project_files": project_files[:30],
            "critical_files": critical_files,
            "critical_contents": critical_contents,
            "context_items_loaded": len(critical_contents),
            "ranking_method": "intent_weighted",  # [P1]
            "read_budget_chars": read_budget,
            "priorities": self.priorities,
            "pruning_strategy": self.config.get('pruning_strategy', 'relevance_score'),
        }

    def _rank_files_by_intent(self, files: list[str], intent: dict) -> list[tuple[str, int]]:
        """[P1] Score each file by relevance to the current intent."""
        intent_type = intent.get('type', '').lower()
        raw_input = intent.get('raw_input', '').lower()

        scored = []
        for f in files:
            f_lower = f.lower()
            score = 0

            # Always-critical files get base score
            for name in ['package.json', 'requirements.txt', 'docker-compose', '.env', 'makefile']:
                if name in f_lower:
                    score += 5

            # Intent-specific boosting
            for category, patterns in self._RELEVANCE.items():
                # Does this category match the intent?
                cat_relevant = (category in intent_type or category in raw_input)
                for pattern, weight in patterns.items():
                    if pattern in f_lower:
                        score += weight if cat_relevant else weight // 3

            if score > 0:
                scored.append((f, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _read_with_cache(self, path: str, budget: int) -> str:
        """[P0] Read file with Redis hash cache — skip if unchanged."""
        try:
            with open(path, 'r', errors='ignore') as fh:
                content = fh.read()[:budget]

            # If Redis available, check if content hash changed
            if self.redis:
                file_hash = hashlib.md5(content.encode()).hexdigest()[:12]
                cache_key = f"ag:filecache:{hashlib.md5(path.encode()).hexdigest()[:12]}"
                cached_hash = self.redis.get(cache_key)
                if cached_hash == file_hash:
                    pass  # Content unchanged — still return it, but we could skip in future
                else:
                    self.redis.setex(cache_key, 86400, file_hash)  # 24h TTL

            return content
        except Exception:
            return ""

    def _scan_project_files(self) -> list[str]:
        """Scan project directory for relevant files."""
        relevant_ext = {'.py', '.js', '.ts', '.yaml', '.yml', '.json', '.md', '.sh',
                        '.env', '.lock', '.dockerfile', '.css', '.html', '.sql', '.prisma',
                        '.tf', '.toml', '.cfg', '.ini', '.graphql'}
        relevant_names = {'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
                          'package.json', 'requirements.txt', 'Makefile', 'Procfile',
                          '.gitignore', '.eslintrc', 'tsconfig.json', 'jest.config.js'}
        files = []
        for root, _, filenames in os.walk(self.base_dir):
            if any(skip in root for skip in ['node_modules', '__pycache__', '.git', 'venv', 'dist', 'build']):
                continue
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext in relevant_ext or fn in relevant_names:
                    files.append(os.path.relpath(os.path.join(root, fn), self.base_dir))
        return sorted(files)[:500]  # [P1] Increased scan limit

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 3: Knowledge + Memory  [v4: TF-IDF semantic vectors + 3-strategy retrieval]
# ═══════════════════════════════════════════════════════════════════════════════
class KnowledgeMemory:
    """Stores/retrieves knowledge from Qdrant with semantic TF-IDF vectors."""

    COLLECTION = "antigravity_knowledge"

    def __init__(self, base_dir: str, qdrant_client=None) -> None:
        self.base_dir = base_dir
        self.config = _load_yaml(os.path.join(base_dir, 'knowledge', 'memory', 'config.yaml'))
        self.qdrant = qdrant_client  # [P0] Shared client
        self.connected = self.qdrant is not None

        if not self.connected and QDRANT_OK:
            try:
                self.qdrant = QdrantClient(host="localhost", port=6333, timeout=3)
                self.qdrant.get_collections()
                self.connected = True
                self._ensure_collection()
            except Exception:
                self.connected = False

    def _ensure_collection(self) -> None:
        collections = [c.name for c in self.qdrant.get_collections().collections]
        if self.COLLECTION not in collections:
            self.qdrant.create_collection(
                collection_name=self.COLLECTION,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            )

    def process(self, intent: dict[str, Any]) -> dict[str, Any]:
        stored = False
        domain_files = self._scan_domain_knowledge()

        if self.connected and self.qdrant:
            stored = self._store_knowledge(intent)

        retrieved = self._retrieve_knowledge(intent['raw_input'])

        # [P2] Re-rank by recency + score composite
        retrieved = self._rerank(retrieved)

        domain_contents = {}
        domain_dir = os.path.join(self.base_dir, 'knowledge', 'domain')
        # [P1] Intent-aware domain loading
        for f in domain_files[:3]:
            f_lower = f.lower()
            intent_lower = intent.get('type', '').lower()
            if any(kw in f_lower for kw in intent_lower.split('-')) or len(domain_files) <= 3:
                try:
                    with open(os.path.join(domain_dir, f), 'r') as fh:
                        domain_contents[f] = fh.read()[:2000]
                except Exception:
                    pass

        return {
            "qdrant_connected": self.connected,
            "knowledge_stored": stored,
            "memories_retrieved": len(retrieved),
            "retrieved_items": retrieved,
            "domain_files_available": len(domain_files),
            "domain_contents": domain_contents,
            "vectorizer": "tfidf_char_ngram" if SKLEARN_OK else "sha512_hash",  # [P2]
            "memory_engine": self.config.get('engine', 'qdrant'),
            "memory_types": list(self.config.get('memory_types', {}).keys()),
        }

    def _store_knowledge(self, intent: dict) -> bool:
        try:
            point_id = abs(hash(intent['raw_input'])) % (2**63)
            self.qdrant.upsert(
                collection_name=self.COLLECTION,
                points=[PointStruct(
                    id=point_id,
                    vector=_text_to_vector(intent['raw_input']),
                    payload={"text": intent['raw_input'], "type": intent['type'],
                             "timestamp": intent['timestamp']},
                )],
            )
            return True
        except Exception:
            return False

    def _retrieve_knowledge(self, query: str, limit: int = 5) -> list[dict]:
        """[P2] 3-strategy retrieval: vector search + TF-IDF cosine + n-gram Jaccard."""
        retrieved = []

        if self.connected and self.qdrant:
            # Strategy 1: Vector search (now uses TF-IDF vectors)
            try:
                results = self.qdrant.search(
                    collection_name=self.COLLECTION,
                    query_vector=_text_to_vector(query),
                    limit=limit,
                )
                for r in results:
                    if r.score > 0.3:  # [P2] Lower threshold — TF-IDF vectors are more spread
                        retrieved.append({
                            "text": r.payload.get("text", ""),
                            "score": round(r.score, 4),
                            "source": "tfidf_vector" if SKLEARN_OK else "hash_vector",
                            "timestamp": r.payload.get("timestamp", ""),
                        })
            except Exception:
                pass

            # Strategy 2: [P2] TF-IDF cosine similarity (recomputed client-side)
            # This catches semantic matches the vector search might miss
            if SKLEARN_OK:
                try:
                    offset = None
                    all_points = []
                    for _ in range(3):  # Max 150 points
                        page, next_offset = self.qdrant.scroll(
                            collection_name=self.COLLECTION,
                            limit=50,
                            offset=offset,
                            with_payload=True,
                            with_vectors=True,  # [P2] Need vectors for cosine
                        )
                        all_points.extend(page)
                        if next_offset is None:
                            break
                        offset = next_offset

                    query_vec = _text_to_vector(query)
                    for point in all_points:
                        stored_text = point.payload.get("text", "")
                        if stored_text == query:
                            continue
                        stored_vec = point.vector if hasattr(point, 'vector') and point.vector else None
                        if stored_vec:
                            sim = _cosine_sim(query_vec, stored_vec)
                            if sim > 0.25 and not any(r['text'] == stored_text for r in retrieved):
                                retrieved.append({
                                    "text": stored_text,
                                    "score": round(sim, 4),
                                    "source": "tfidf_cosine",
                                    "timestamp": point.payload.get("timestamp", ""),
                                })
                except Exception:
                    pass

            # Strategy 3: N-gram Jaccard (catches lexical matches)
            try:
                if not all_points:  # Only fetch if not already done
                    offset = None
                    all_points = []
                    for _ in range(3):
                        page, next_offset = self.qdrant.scroll(
                            collection_name=self.COLLECTION,
                            limit=50,
                            offset=offset,
                            with_payload=True,
                            with_vectors=False,
                        )
                        all_points.extend(page)
                        if next_offset is None:
                            break
                        offset = next_offset

                query_ngrams = self._get_ngrams(query.lower(), 3)
                if query_ngrams:
                    for point in all_points:
                        stored_text = point.payload.get("text", "")
                        stored_ngrams = self._get_ngrams(stored_text.lower(), 3)
                        if stored_ngrams:
                            overlap = len(query_ngrams & stored_ngrams)
                            union = len(query_ngrams | stored_ngrams)
                            jaccard = overlap / union if union else 0
                            if jaccard > 0.12 and stored_text != query:
                                if not any(r['text'] == stored_text for r in retrieved):
                                    retrieved.append({
                                        "text": stored_text,
                                        "score": round(jaccard, 4),
                                        "source": "ngram_jaccard",
                                        "timestamp": point.payload.get("timestamp", ""),
                                    })
            except Exception:
                pass

        retrieved.sort(key=lambda x: x['score'], reverse=True)
        return retrieved[:limit]

    def _rerank(self, items: list[dict]) -> list[dict]:
        """[P2-lite] Re-rank by composite: 0.7 * similarity + 0.3 * recency."""
        now = datetime.now(timezone.utc)
        for item in items:
            ts = item.get('timestamp', '')
            recency = 0.5  # default
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    age_hours = (now - dt).total_seconds() / 3600
                    recency = max(0, 1.0 - (age_hours / 720))  # Decays over 30 days
                except Exception:
                    pass
            item['composite_score'] = round(0.7 * item['score'] + 0.3 * recency, 4)
        items.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
        return items

    @staticmethod
    def _get_ngrams(text: str, n: int = 3) -> set:
        clean = re.sub(r'[^a-z0-9 ]', '', text)
        words = clean.split()
        ngrams = set()
        for word in words:
            for i in range(len(word) - n + 1):
                ngrams.add(word[i:i+n])
        for i in range(len(words) - 1):
            ngrams.add(f"{words[i]}_{words[i+1]}")
        return ngrams

    def _scan_domain_knowledge(self) -> list[str]:
        domain_dir = os.path.join(self.base_dir, 'knowledge', 'domain')
        if not os.path.isdir(domain_dir):
            return []
        return [f for f in os.listdir(domain_dir) if not f.startswith('.')]
