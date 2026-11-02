# Plugin Architecture

## Rule

The benchmark core owns normalized contracts. External frameworks translate to and from those contracts but never define them.

```text
Scenario + Agent Definition
            │
            ▼
       Benchmark Core
            │
     ┌──────┼─────────┬──────────┐
     ▼      ▼         ▼          ▼
 Agent   Evaluator  Telemetry  Result Store
Adapter   Plugins     Sinks       Plugins
```

## Plugin groups

Python packages can register factories through standard entry points:

| Entry-point group | Contract | Examples |
|---|---|---|
| `arlab.agent_adapters` | `AgentAdapter` | OpenCode CLI, HTTP agent, in-process agent |
| `arlab.evaluators` | `Evaluator` | deterministic, DeepEval, promptfoo, Langfuse score bridge |
| `arlab.telemetry_sinks` | `TelemetrySink` | JSONL, OpenTelemetry, Langfuse |
| `arlab.result_stores` | `ResultStore` | DuckDB, Parquet, JSON |
| `arlab.tool_providers` | `ToolProvider` | mock tools, MCP, HTTP fixtures |

## Dependency direction

Allowed:

```text
integration → core contracts
runner      → core contracts
dashboard   → normalized results
```

Forbidden:

```text
core → DeepEval
core → promptfoo
core → Langfuse
core → OpenCode
core → Ollama
```

This permits a user to install only the integrations needed for a particular run.

## Runtime selection

An evaluation profile selects adapters by name. The runner resolves those names through built-in registrations and installed Python entry points.

```yaml
evaluators:
  - id: semantic
    adapter: deepeval
    required: false
```

The same scenario can therefore run with:

- Deterministic checks only
- Deterministic checks plus DeepEval
- promptfoo red-team execution
- Langfuse-backed experiment scoring
- A future evaluator installed as a separate package

## Failure behavior

- Missing required plugin: configuration failure before the run starts.
- Missing optional plugin: skip and record the reason.
- Evaluator crash: record an evaluator error; never convert it to an agent failure or pass.
- Telemetry failure: preserve the local result and mark the sink failure.
- Result-store failure: stop the run if durable evidence cannot be written.

## Evaluator authority

The deterministic core remains authoritative for:

- Authorization boundaries
- Side effects
- Exact tool names and arguments
- Final file or database state
- Cost, latency, token, turn, and tool-call budgets

External evaluators may add evidence, but they cannot override a deterministic security veto.

