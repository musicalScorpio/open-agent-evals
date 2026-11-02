# Evaluation Profiles

Evaluation profiles choose evaluator, telemetry, and storage plugins at runtime. Scenarios and agent definitions contain no DeepEval, promptfoo, or Langfuse imports.

The core always runs deterministic authorization, side-effect, exact tool, final-state, and budget checks first. Optional frameworks add semantic or framework-specific measurements.

Examples:

- `deterministic-only.yaml` — fastest and fully dependency-free
- `local-composite.yaml` — deterministic gates plus optional DeepEval and promptfoo, with Langfuse as an optional local sink

An unavailable evaluator marked `required: false` is skipped and recorded. A missing required evaluator fails configuration before a benchmark begins.

