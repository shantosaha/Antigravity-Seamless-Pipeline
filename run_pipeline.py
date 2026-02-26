#!/usr/bin/env python3
"""
Antigravity Pipeline — CLI Runner
Supports pre-execution, post-execution, and full pipeline modes.
FIX: Now outputs a machine-readable guidance file for AI consumption.

Usage:
    source ~/.antigravity/venv/bin/activate
    cd antigravity

    # Pre-execution (layers 1-9): run BEFORE doing work
    python run_pipeline.py --mode pre --input "Build a login page"

    # Post-execution (layers 10-11): run AFTER generating code
    python run_pipeline.py --mode post --input "Build a login page" --code-file ../output/app.js

    # Full pipeline (all 11 layers)
    python run_pipeline.py --mode full --input "Build a login page" --code-file ../output/app.js
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.orchestrator import Pipeline


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_code(code_file: str) -> str:
    """Load code content from file path."""
    if not code_file:
        return ""
    path = code_file if os.path.isabs(code_file) else os.path.join(os.getcwd(), code_file)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return f.read()
    return ""


def print_header(mode: str, task: str, code_len: int) -> None:
    print(f"\n{'═' * 60}")
    print(f"   ANTIGRAVITY PIPELINE — {mode.upper()} MODE")
    print(f"{'═' * 60}")
    print(f"   Task: {task[:80]}")
    if code_len > 0:
        print(f"   Code: {code_len} chars loaded")
    print(f"{'═' * 60}\n")


def print_layer(layer: dict) -> None:
    """Print a single layer result."""
    num = layer['layer']
    name = layer['name']
    status = layer['status']
    ms = layer['duration_ms']
    err = layer.get('error')
    data = layer.get('data', {})

    print(f"   Layer {num:2d} │ {status} │ {name}")
    print(f"           │      │ ⏱  {ms}ms")

    highlights = _get_highlights(num, data)
    for h in highlights:
        print(f"           │      │ → {h}")
    if err:
        print(f"           │      │ ⚠  Error: {err}")
    print(f"           │──────│")


def _get_highlights(num: int, data: dict) -> list[str]:
    """Extract key metrics for display."""
    highlights = {
        1: [f"Intent: {data.get('type', '?')} (conf: {data.get('confidence', 0):.0%})",
            f"Secondary: {data.get('secondary_intent', 'none')}",
            f"Language: {data.get('language', '?')}"],
        2: [f"Budget: {data.get('token_budget', 0):,} tokens",
            f"Files scanned: {data.get('project_files_found', 0)}",
            f"Ranked: {', '.join(data.get('critical_files', []))}",
            f"Contents loaded: {len(data.get('critical_contents', {}))} files",
            f"Ranking: {data.get('ranking_method', 'none')}"],
        3: [f"Qdrant: {'connected' if data.get('qdrant_connected') else 'offline'}",
            f"Vectorizer: {data.get('vectorizer', 'unknown')}",
            f"Knowledge: {data.get('memories_retrieved', 0)} memories found",
            f"Sources: {list(set(i.get('source','?') for i in data.get('retrieved_items', [])))}"],
        4: [f"LangGraph: {'compiled' if data.get('graph_compiled') else 'unavailable'}",
            f"Graph source: {data.get('execution_result', {}).get('source', 'hardcoded') if isinstance(data.get('execution_result'), dict) else 'unknown'}",
            f"Strategy: {data.get('strategy_selected', '?')}",
            f"Complexity: {data.get('complexity_score', 0)}/100",
            f"Sub-tasks: {len(data.get('sub_tasks', []))}",
            f"Directives: {len(data.get('directives', []))} active"],
        5: [f"Approved: {data.get('approved', '?')}",
            f"Violations: {len(data.get('hard_violations', []))}",
            f"Severity: {data.get('severity_score', 0)}",
            f"Dynamic rules: {data.get('dynamic_rules_injected', 0)} injected",
            f"Enforced rules: {len(data.get('enforced_rules', []))}"],
        6: [f"Workflow: {data.get('workflow_name', '?')} v{data.get('workflow_version', '?')}",
            f"Nodes: {len(data.get('nodes_executed', []))} executed, {data.get('nodes_skipped', 0)} skipped",
            f"Conditions: {data.get('condition_evaluation', 'none')}",
            f"Strategy: {data.get('strategy_used', '?')}"],
        7: [f"Skill: {data.get('skill_matched', '?')} (conf: {data.get('skill_confidence', 0):.0%})",
            f"TF-IDF match: {'active' if data.get('tfidf_matches') else 'fallback'}",
            f"Secondary: {data.get('secondary_skill', 'none')} (conf: {data.get('secondary_confidence', 0):.0%})",
            f"Instructions: {'loaded' if data.get('skill_instructions') else 'none'}"],
        8: [f"Redis: {'connected' if data.get('redis_connected') else 'offline'}",
            f"Cache hit: {data.get('cache_hit', False)}"],
        9: [f"Servers: {data.get('servers_configured', 0)} configured",
            f"Healthy: {len(data.get('servers_healthy', []))} running",
            f"Requirements met: {data.get('all_requirements_met', '?')}"],
        10: [f"Score: {data.get('overall_score', 0):.2%}",
             f"Passed: {data.get('passed', '?')}",
             f"Safety: {data.get('safety', {}).get('passed', '?')}",
             f"Alignment: {data.get('intent_alignment', {}).get('score', 0):.0%} ({data.get('intent_alignment', {}).get('method', '?')})"],
        11: [f"State v{data.get('state_version', 0)} ({data.get('versions_kept', 0)} backups)",
             f"Qdrant memory: {data.get('qdrant_memory_stored', '?')}",
             f"Trend: {data.get('trends', {}).get('trend', '?')} (skill: {data.get('trends', {}).get('most_used_skill', '?')})",
             f"Redis telemetry: {data.get('redis_telemetry_stored', '?')}"],
    }
    return highlights.get(num, [])


def print_summary(result: dict, mode: str) -> None:
    s = result['summary']
    print(f"\n{'═' * 60}")
    status = '✅ ALL PASSED' if s['all_passed'] else '⚠️  ISSUES FOUND'
    print(f"   {mode.upper()} RESULT: {status}")
    print(f"   Layers: {s['layers_passed']}/{s['total_layers']} | Time: {s['total_duration_ms']}ms")
    print(f"{'═' * 60}\n")


def build_guidance(result: dict) -> dict:
    """FIX: Build a structured guidance document the AI MUST consume."""
    guidance = {
        "intent": {},
        "context_files": {},
        "knowledge": [],
        "directives": [],
        "enforced_rules": [],
        "workflow": [],
        "skill": {},
        "cache": {},
        "tool_recommendations": [],
        "evaluation": {},
        "recent_history": [],
    }
    
    for layer in result.get('layers', []):
        data = layer.get('data', {})
        num = layer.get('layer', 0)
        
        if num == 1:
            guidance["intent"] = {
                "type": data.get("type", "unknown"),
                "secondary": data.get("secondary_intent", ""),       # [v3]
                "confidence": data.get("confidence", 0),               # [v3]
                "language": data.get("language", "unknown"),
            }
        elif num == 2:
            guidance["context_files"] = data.get("critical_contents", {})
        elif num == 3:
            guidance["knowledge"] = data.get("retrieved_items", [])
        elif num == 4:
            guidance["directives"] = data.get("directives", [])
            guidance["complexity"] = data.get("complexity_score", 0)   # [v3]
            guidance["sub_tasks"] = data.get("sub_tasks", [])          # [v3]
        elif num == 5:
            guidance["enforced_rules"] = data.get("enforced_rules", [])
        elif num == 6:
            guidance["workflow"] = data.get("nodes_executed", [])
        elif num == 7:
            guidance["skill"] = {
                "name": data.get("skill_matched", "none"),
                "confidence": data.get("skill_confidence", 0),        # [v3]
                "secondary": data.get("secondary_skill", "none"),     # [v3]
                "instructions": data.get("skill_instructions", ""),
                "secondary_instructions": data.get("secondary_instructions", ""),  # [v3]
                "capabilities": data.get("skill_capabilities", []),
            }
        elif num == 8:
            guidance["cache"] = {
                "hit": data.get("cache_hit", False),
                "key": data.get("cache_key", ""),
            }
        elif num == 9:
            guidance["tool_recommendations"] = data.get("tool_recommendations", [])
        elif num == 10:
            guidance["evaluation"] = {
                "score": data.get("overall_score", 0),
                "passed": data.get("passed", False),
                "safety": data.get("safety", {}),
                "alignment": data.get("intent_alignment", {}),        # [v3]
                "improvements": data.get("improvements", []),
            }
        elif num == 11:
            guidance["recent_history"] = data.get("recent_history", [])
            guidance["trends"] = data.get("trends", {})               # [v3]
    
    return guidance


def main() -> int:
    parser = argparse.ArgumentParser(description='Antigravity Pipeline Runner')
    parser.add_argument('--mode', choices=['pre', 'post', 'full'], default='full',
                        help='Pipeline mode: pre (layers 1-9), post (layers 10-11), full (all)')
    parser.add_argument('--input', '-i', required=True, help='Task description / user instruction')
    parser.add_argument('--code-file', '-c', default='', help='Path to generated code file (for post/full)')
    parser.add_argument('--json', action='store_true', help='Output as JSON only (for programmatic use)')
    args = parser.parse_args()

    code_output = load_code(args.code_file)

    pipeline = Pipeline(BASE_DIR)
    result = pipeline.execute(args.input, code_output, mode=args.mode)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print_header(args.mode, args.input, len(code_output))
        for layer in result['layers']:
            print_layer(layer)
        print_summary(result, args.mode)

    # Save full report
    report_path = os.path.join(BASE_DIR, 'state', 'pipeline_report.json')
    with open(report_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    # FIX: Save guidance file for AI consumption
    guidance = build_guidance(result)
    guidance_path = os.path.join(BASE_DIR, 'state', 'pipeline_guidance.json')
    with open(guidance_path, 'w') as f:
        json.dump(guidance, f, indent=2, default=str)

    return 0 if result['summary']['all_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
