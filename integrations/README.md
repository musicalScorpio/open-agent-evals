# Integrations

Integrations will be implemented as optional packages or modules that depend on the core contracts.

Planned adapters:

| Integration | Plugin role |
|---|---|
| OpenCode | Agent adapter using CLI JSON first, server API later |
| Ollama | Local model endpoint used by agents and evaluators |
| DeepEval | Semantic and agentic evaluator |
| promptfoo | External evaluation and adversarial-suite adapter |
| Langfuse | Evaluation score bridge and telemetry sink |
| OpenTelemetry | Vendor-neutral telemetry sink |
| DuckDB | Local result store |

No integration is imported by `arlab.agents`, `arlab.evaluation`, `arlab.plugins`, or `arlab.ports`.

