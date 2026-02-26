# Configuration Reference

Every YAML configuration file in the pipeline, explained.

---

## `agent.yaml`

Top-level agent settings.

```yaml
name: "antigravity-agent"
version: "1.0.0"
context_budget: 190000        # Max tokens the context manager can load
default_temperature: 0.7
capabilities:
  - code_generation
  - document_creation
  - data_analysis
  - workflow_orchestration
limits:
  max_retries: 3
  timeout_seconds: 300
  max_parallel_tasks: 5
```

---

## `policy/rules.yaml`

Security rules enforced by Layer 5.

### Hard Constraints (block immediately)
```yaml
hard_constraints:
  - rule: no_malicious_code
    patterns:
      - "eval("
      - "exec("
      - "__import__('os').system"
      - "subprocess.call"
    action: block
```

### Soft Constraints (suggest, don't block)
```yaml
soft_constraints:
  - rule: prefer_async
    action: suggest
  - rule: add_logging
    action: suggest
```

### Domain Rules (context-specific)
```yaml
domain_rules:
  software_development:
    - rule: max_function_length
      value: 50
      action: warn
```

**To add a new banned pattern:** Add it to `hard_constraints.patterns`. The pipeline's Layer 5 will block any code containing that pattern.

---

## `workflows/code_generation.yaml`

Defines the workflow graph that Layer 4 builds dynamically and Layer 6 executes.

```yaml
name: "code_generation_workflow"
version: "1.0.0"

graph:
  start: understand_requirements

  nodes:
    understand_requirements:
      skill: requirement_analysis
      next:
        - condition: "has_design"     # complexity < 30
          goto: generate_code
        - condition: "needs_design"   # complexity >= 30
          goto: create_architecture

    create_architecture:
      skill: system_design
      next: generate_code

    generate_code:
      skill: code_writer
      timeout: 120
      next: code_review

    code_review:
      skill: code_reviewer
      max_iterations: 3
      next:
        - condition: "needs_revision"
          goto: generate_code
        - condition: "approved"
          goto: end
```

**To add a new workflow node:** Add it under `nodes:` with a `skill`, `next`, and optional `timeout`/`max_iterations`.

---

## `evaluator/evaluator.yaml`

Scoring criteria for Layer 10.

```yaml
criteria:
  quality:
    completeness: 0.8       # Minimum completeness score
    accuracy: 0.9
    relevance: 0.85
  safety:
    no_harmful_content: required
    privacy_compliance: required
  domain_specific:
    code:
      syntax_valid: required
      has_tests: preferred
      documented: preferred

auto_reject_below: 0.6      # Reject outputs scoring below 60%
```

---

## `planner/planner.yaml`

Task planner configuration for Layer 4.

```yaml
strategies:
  linear:
    max_steps: 10
  parallel:
    max_parallel: 5
  conditional:
    max_depth: 5
  iterative:
    max_iterations: 3

optimization:
  prefer_parallel: true
  cache_plans: true
```

---

## `mcp/servers.yaml`

MCP server definitions for Layer 9.

```yaml
servers:
  - name: filesystem
    command: npx @modelcontextprotocol/server-filesystem
    scope: global
  - name: fetch
    command: npx @modelcontextprotocol/server-fetch
    scope: global
  - name: github
    command: npx @modelcontextprotocol/server-github
    scope: global
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
```

**To add a new MCP server:** Add an entry under `servers:` with `name`, `command`, and optional `env`/`args`.

---

## `telemetry/metrics.yaml`

Metrics and alerting for Layer 11.

```yaml
metrics:
  latency: [total_response_time, mcp_call_time]
  success_rates: [task_completion_rate, error_rate]
  quality: [evaluation_scores, hallucination_rate]
  usage: [tokens_consumed, cache_hit_rate]

alerts:
  error_rate_threshold: 0.1
  latency_threshold_seconds: 10
  token_budget_threshold: 0.9
```

---

## `scheduler/scheduler.yaml`

Rate limiting and concurrency.

```yaml
rate_limits:
  mcp_calls: 100/minute
  api_requests: 1000/hour
  file_operations: 50/minute

concurrency:
  max_workers: 10
  max_parallel_mcp: 5
```
