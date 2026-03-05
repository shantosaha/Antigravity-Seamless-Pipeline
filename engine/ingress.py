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
            # ── Original Skills — Boosted to beat generic agent keywords ────────
            # Weight 6-7 ensures these specialist skills win over agent weight-5
            'design-skill': [('design', 6), ('ui design', 7), ('ux design', 7), ('glassmorphism', 7),
                             ('visual design', 7), ('color palette', 6), ('design system', 5),
                             ('typography', 6), ('visual hierarchy', 7), ('ui aesthetic', 7),
                             ('make it look', 6), ('beautiful ui', 7), ('premium design', 7),
                             ('high fidelity', 7), ('wireframe', 6), ('mockup', 6), ('layout design', 6)],
            'clean-code': [('clean code', 7), ('solid principles', 7), ('naming convention', 6),
                           ('code readability', 6), ('dry principle', 6), ('kiss principle', 6),
                           ('code organization', 6), ('best practices', 5), ('clean architecture', 6)],
            'data-storytelling': [('dashboard design', 7), ('data visualization', 7), ('charts', 6),
                                  ('reporting dashboard', 7), ('analytics dashboard', 7),
                                  ('d3.js', 6), ('chart.js', 6), ('graph visualization', 7),
                                  ('data narrative', 6), ('insights dashboard', 7), ('kpi dashboard', 7)],
            'implement-design': [('figma to code', 7), ('design to code', 7), ('pixel perfect', 7),
                                 ('implement this design', 7), ('mockup to code', 7),
                                 ('figma', 6), ('zeplin', 6), ('sketch to code', 7)],
            'responsive-design': [('responsive design', 7), ('mobile first design', 7),
                                  ('media queries', 6), ('responsive layout', 7),
                                  ('adaptive design', 7), ('breakpoints', 5)],
            'framer-motion-animator': [('framer motion', 7), ('page transitions', 6),
                                       ('scroll animations', 6), ('micro animations', 7),
                                       ('motion design', 6), ('animated ui', 6), ('smooth animations', 6)],
            'tailwind-design-system': [('tailwind', 9), ('tailwind css', 9), ('tailwind config', 9), ('tailwind setup', 9),
                                       ('utility first css', 8), ('tailwind components', 8),
                                       ('tailwind theme', 8)],
            'theme-factory': [('theme', 6), ('dark mode theme', 7), ('light dark toggle', 7),
                              ('generate theme', 7), ('css variables', 6), ('color scheme', 6),
                              ('theming', 6), ('brand colors', 6)],
            'canvas-design': [('canvas drawing', 7), ('html5 canvas', 7), ('2d game', 6),
                              ('pixel art', 6), ('canvas animation', 7), ('interactive canvas', 7)],
            'stripe-integration': [('stripe checkout', 7), ('payment integration', 7),
                                   ('subscription billing', 7), ('stripe webhook', 7),
                                   ('billing portal', 6), ('stripe api', 7)],
            'supabase-postgres-best-practices': [('supabase setup', 7), ('rls policy', 7),
                                                  ('supabase auth', 7), ('supabase migration', 7),
                                                  ('postgres rls', 6), ('supabase edge function', 6)],
            'react-native-design': [('react native ui', 7), ('expo ui', 7), ('mobile design system', 7),
                                    ('native styling', 6), ('mobile component design', 7)],
            'react-native-architecture': [('react native architecture', 7), ('expo navigation', 7),
                                           ('react native state', 7), ('native module', 6)],
            'nextjs-app-router-patterns': [('next.js', 7), ('nextjs app router', 7),
                                            ('server components', 7), ('nextjs api route', 7),
                                            ('next.js page', 6), ('nextjs middleware', 6)],
            'fastapi-templates': [('fastapi endpoint', 7), ('pydantic model', 7),
                                  ('fastapi router', 7), ('python api endpoint', 6)],
            'auth-implementation-patterns': [('login system', 7), ('signup flow', 7),
                                             ('jwt authentication', 7), ('oauth2 flow', 7),
                                             ('session management', 6), ('password reset', 6),
                                             ('magic link', 6), ('two factor auth', 6)],
            'rag-implementation': [('rag system', 7), ('vector search', 7), ('embedding pipeline', 7),
                                   ('retrieval augmented generation', 7), ('knowledge base', 6),
                                   ('semantic search', 6), ('qdrant setup', 6)],
            'mcp-builder': [('mcp', 8), ('build mcp server', 8), ('mcp server', 8),
                            ('mcp tool', 8), ('model context protocol', 8),
                            ('mcp resource', 7), ('mcp prompt', 7)],
            'langchain-architecture': [('langchain agent', 7), ('langchain chain', 7),
                                       ('langgraph', 7), ('langsmith', 6), ('langchain tool', 6)],
            'e2e-testing-patterns': [('playwright test', 7), ('cypress test', 7),
                                     ('end to end test', 7), ('browser test', 6)],
            'javascript-testing-patterns': [('jest test', 7), ('vitest test', 7),
                                            ('unit test javascript', 7), ('mocha test', 6)],
            'github-actions-templates': [('github actions workflow', 7), ('ci cd github', 7),
                                         ('github workflow yaml', 7), ('deploy github', 6)],
            'k8s-manifest-generator': [('kubernetes deployment', 7), ('k8s manifest', 7),
                                       ('helm chart', 7), ('kubectl', 6), ('k8s service', 6)],
            'postgresql-table-design': [('postgres table', 7), ('postgresql index', 7),
                                        ('postgres query', 6), ('sql schema', 6),
                                        ('database table design', 7)],
            'database-migration': [('alembic migration', 7), ('knex migration', 7),
                                   ('schema migration', 7), ('migration script', 6)],
            'microservices-patterns': [('service mesh', 7), ('api gateway', 6),
                                       ('event sourcing', 7), ('cqrs', 7), ('saga pattern', 7)],
            'gdpr-data-handling': [('gdpr compliance', 7), ('data privacy', 7),
                                   ('pii handling', 7), ('data retention', 6),
                                   ('right to erasure', 7), ('privacy policy', 6)],
            'prompt-engineering-patterns': [('system prompt', 7), ('prompt template', 7),
                                            ('few shot prompt', 7), ('chain of thought', 6),
                                            ('prompt design', 7)],
            'startup-metrics-framework': [('startup kpi', 7), ('saas metrics', 7),
                                          ('cohort analysis', 6), ('unit economics', 7),
                                          ('customer acquisition cost', 7)],
            'threejs-fundamentals': [('three.js', 7), ('3d web', 7), ('webgl scene', 7),
                                     ('3d model viewer', 7), ('three.js scene', 7)],
            'web-artifacts-builder': [('interactive widget', 7), ('html tool', 6),
                                      ('web calculator', 6), ('mini app', 6),
                                      ('interactive prototype', 7), ('web artifact', 7)],
            'accessibility-compliance': [('wcag audit', 7), ('a11y compliance', 7),
                                         ('aria labels', 7), ('accessibility check', 7),
                                         ('screen reader support', 7), ('focus management', 6)],
            'competitive-landscape': [('competitor analysis', 7), ('market research', 7),
                                      ('competitive audit', 7), ('swot analysis', 6)],
            'algorithmic-art': [('generative art', 7), ('p5.js sketch', 7),
                                ('creative coding', 7), ('algorithmic pattern', 6)],
            'sendgrid-automation': [('sendgrid email', 7), ('email template', 6),
                                    ('transactional email', 7), ('email api', 6)],
            'google-cloud-agent-sdk-master': [('vertex ai agent', 7), ('google cloud agent', 7),
                                              ('gcp agent', 7), ('adk', 6)],
            'sast-configuration': [('sast setup', 7), ('code scanning config', 7),
                                   ('security scanner', 6), ('static analysis', 7)],
            # ── 32-Agent Ecosystem — Layer 0 (Pre-Execution) ────────────────────
            'requirement-clarifier': [
                ('requirements', 4), ('clarify', 5), ('what exactly', 5), ('spec', 3),
                ('acceptance criteria', 5), ('user story', 5), ('define scope', 4),
                ('gather requirements', 5), ('what do you want', 3), ('ambiguous', 4),
            ],
            'project-planner': [
                ('project plan', 5), ('milestone', 5), ('roadmap', 5), ('sprint', 4),
                ('phases', 4), ('project timeline', 5), ('deliverables', 4), ('plan this project', 5),
            ],
            'prerequisite-scanner': [
                ('prerequisites', 5), ('environment setup', 5), ('check tools', 4),
                ('installed', 3), ('missing dependencies', 5), ('verify setup', 5),
                ('system check', 4), ('check environment', 5),
            ],
            'dependency-solver': [
                ('package conflict', 5), ('npm install', 4), ('dependency', 4),
                ('resolve packages', 5), ('version conflict', 5), ('pip install', 4),
                ('yarn add', 4), ('library versions', 4), ('compatible packages', 5),
            ],
            'skeleton-generator': [
                ('project skeleton', 5), ('scaffold', 5), ('boilerplate', 5),
                ('file structure', 4), ('starter template', 5), ('project structure', 4),
                ('create project layout', 5), ('generate structure', 4),
            ],
            'context-memory-manager': [
                ('context', 3), ('remember', 4), ('what we built', 4), ('session recap', 5),
                ('project history', 5), ('pick up where', 5), ('continue from', 4),
                ('save context', 5), ('restore session', 5),
            ],
            'risk-detector': [
                ('risk', 4), ('potential issues', 5), ('what could go wrong', 5),
                ('risks', 4), ('technical debt', 3), ('failure points', 5),
                ('identify risks', 5), ('risk assessment', 5), ('red flags', 4),
            ],
            'task-decomposer': [
                ('break down', 5), ('decompose', 5), ('subtasks', 5), ('task list', 4),
                ('split into tasks', 5), ('create backlog', 5), ('create tickets', 4),
                ('work breakdown', 5), ('divide work', 4), ('atomic tasks', 5),
            ],
            # ── 32-Agent Ecosystem — Layer 1 (Foundation) ────────────────────────
            'architect': [
                ('design architecture', 5), ('system architecture', 5), ('adr', 5),
                ('architecture decision', 5), ('technical design', 5), ('erd', 4),
                ('data model', 4), ('api contract', 4), ('system design', 4),
                ('architecture diagram', 5), ('design the system', 5),
            ],
            'implementor-dispatcher': [
                ('dispatch', 4), ('assign tasks', 4), ('who should build', 4),
                ('which agent', 4), ('delegate', 4), ('route task', 4),
            ],
            'critic': [
                ('review code', 5), ('code review', 5), ('critique', 5),
                ('code quality', 4), ('review this', 4), ('check my code', 5),
                ('is this correct', 4), ('feedback on code', 5), ('code audit', 4),
            ],
            'debugger': [
                ('debug', 5), ('bug', 4), ('broken', 4), ('not working', 4),
                ('stack trace', 5), ('error message', 4), ('why is this failing', 5),
                ('runtime error', 5), ('crash', 4), ('exception', 4), ('trace', 3),
            ],
            'synthesizer': [
                ('what did i learn', 5), ('weekly recap', 5), ('learning summary', 5),
                ('synthesize', 5), ('what patterns', 4), ('what concepts', 4),
                ('knowledge review', 5), ('teach me', 3), ('explain patterns', 4),
            ],
            'operator': [
                ('deploy', 5), ('ship', 5), ('release', 5), ('production', 4),
                ('staging', 4), ('push to prod', 5), ('go live', 5), ('cicd', 4),
                ('publish', 4), ('rollout', 5), ('deploy to vercel', 5),
            ],
            # ── 32-Agent Ecosystem — Layer 2 (Implementation Fleet) ──────────────
            'frontend-ui-engineer': [
                ('frontend', 4), ('component', 3), ('react component', 5), ('ui', 3),
                ('page', 2), ('button', 3), ('form', 3), ('modal', 4), ('table', 3),
                ('tailwind', 3), ('css', 3), ('user interface', 4), ('web ui', 4),
                ('build the ui', 5), ('design this page', 4), ('next.js component', 5),
            ],
            'backend-api-engineer': [
                ('api endpoint', 5), ('rest api', 4), ('post request', 4), ('get request', 4),
                ('controller', 4), ('route handler', 5), ('api route', 5),
                ('backend logic', 5), ('server side', 4), ('node backend', 4),
                ('express route', 5), ('api layer', 5), ('build the api', 5),
            ],
            'database-implementor': [
                ('database schema', 5), ('create table', 5), ('sql migration', 5),
                ('prisma schema', 5), ('database design', 4), ('add column', 4),
                ('index', 3), ('foreign key', 4), ('database table', 5),
                ('write migration', 5), ('db schema', 5),
            ],
            'mobile-engineer': [
                ('mobile', 4), ('react native', 5), ('expo', 5), ('ios', 4), ('android', 4),
                ('mobile screen', 5), ('mobile app', 4), ('native app', 4),
                ('offline mode', 4), ('push notification', 4), ('mobile component', 5),
            ],
            'devops-infra-coder': [
                ('dockerfile', 5), ('docker compose', 5), ('github actions', 5),
                ('ci/cd pipeline', 5), ('containerize', 5), ('infrastructure', 4),
                ('kubernetes manifest', 5), ('deployment pipeline', 5), ('terraform', 5),
                ('set up cicd', 5), ('write dockerfile', 5), ('devops', 4),
            ],
            'algorithm-engineer': [
                ('algorithm', 5), ('too slow', 4), ('optimize this', 4), ('complexity', 4),
                ('data structure', 5), ('sorting', 4), ('search algorithm', 5),
                ('big o', 5), ('performance algorithm', 5), ('efficient solution', 4),
            ],
            'ai-feature-builder': [
                ('openai', 5), ('chatgpt', 5), ('llm', 5), ('anthropic', 5),
                ('add ai', 5), ('chatbot', 5), ('semantic search', 5), ('embeddings', 4),
                ('ai feature', 5), ('gpt', 4), ('claude', 4), ('gemini', 4),
                ('ai powered', 5), ('intelligent', 3), ('language model', 5),
            ],
            'cli-scripting-engineer': [
                ('bash script', 5), ('shell script', 5), ('python script', 4),
                ('automate this', 4), ('write a script', 5), ('cli tool', 5),
                ('cron job', 5), ('migration script', 5), ('automation script', 5),
                ('build a cli', 5), ('data pipeline script', 4),
            ],
            'realtime-systems-engineer': [
                ('websocket', 5), ('real-time', 5), ('live update', 5), ('realtime', 5),
                ('server-sent events', 5), ('sse', 5), ('presence', 4), ('who is online', 4),
                ('live dashboard', 5), ('push update', 4), ('streaming', 4),
                ('make this real-time', 5), ('socket.io', 5),
            ],
            'integration-glue-engineer': [
                ('integrate with', 5), ('stripe', 4), ('webhook', 5), ('oauth', 4),
                ('third party', 4), ('slack integration', 5), ('sendgrid', 4),
                ('resend', 4), ('connect to', 3), ('twilio', 5), ('zapier', 5),
                ('external api', 4), ('add payments', 5), ('payment gateway', 5),
            ],
            # ── 32-Agent Ecosystem — Layer 3 (Quality & Depth) ──────────────────
            'tester': [
                ('write tests', 5), ('unit test', 5), ('integration test', 5),
                ('test coverage', 5), ('jest test', 5), ('pytest', 5),
                ('add test', 4), ('test this', 4), ('test suite', 5),
                ('regression test', 5), ('test the function', 5),
            ],
            'documenter': [
                ('document this', 5), ('write documentation', 5), ('jsdoc', 5),
                ('readme', 4), ('api documentation', 5), ('add comments', 4),
                ('explain this code', 4), ('documentation', 3), ('write the readme', 5),
            ],
            'refactorer': [
                ('refactor', 5), ('clean up', 4), ('simplify', 4), ('restructure', 5),
                ('too complex', 4), ('hard to read', 4), ('messy code', 5),
                ('extract function', 5), ('tech debt', 4), ('code smell', 5),
            ],
            'security-auditor': [
                ('security audit', 5), ('vulnerability', 5), ('owasp', 5),
                ('sql injection', 5), ('xss', 5), ('is this secure', 5),
                ('security check', 5), ('penetration', 4), ('security review', 5),
                ('secure this', 4), ('audit security', 5), ('check for vulnerabilities', 5),
            ],
            # ── 32-Agent Ecosystem — Layer 4 (Specialization) ────────────────────
            'data-database-architect': [
                ('database architecture', 5), ('scale the database', 5), ('partitioning', 5),
                ('database performance', 5), ('multi database', 5), ('read replica', 5),
                ('sharding', 5), ('10 million rows', 5), ('database bottleneck', 5),
                ('reporting schema', 5), ('data warehouse', 5), ('olap', 5),
            ],
            'api-integration-specialist': [
                ('openapi spec', 5), ('swagger', 5), ('api versioning', 5),
                ('public api', 4), ('api key', 4), ('api rate limit', 5),
                ('design the api', 5), ('api contract', 4), ('breaking change', 5),
                ('sdk', 4), ('api documentation', 4), ('rest contract', 5),
            ],
            'performance-engineer': [
                ('lighthouse score', 5), ('core web vitals', 5), ('page load', 4),
                ('profile performance', 5), ('bottleneck', 4), ('too slow', 3),
                ('n+1 query', 5), ('lcp', 5), ('fid', 5), ('cls', 5),
                ('optimize performance', 5), ('slow query', 5), ('benchmark', 4),
            ],
            'ai-ml-integration-specialist': [
                ('fine-tune', 5), ('ml pipeline', 5), ('prompt engineering', 4),
                ('evaluation dataset', 5), ('model drift', 5), ('ai quality', 5),
                ('model monitoring', 5), ('rag pipeline', 5), ('train model', 5),
                ('ai system', 4), ('machine learning', 4), ('model evaluation', 5),
            ],
            # ── 32-Agent Ecosystem — Layer 5 (Orchestration) ─────────────────────
            'orchestrator': [
                ('orchestrate', 5), ('which agent', 5), ('agent sequence', 5),
                ('run all agents', 5), ('full pipeline', 4), ('coordinate agents', 5),
                ('what runs next', 5), ('agent flow', 5), ('system status', 4),
            ],
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
