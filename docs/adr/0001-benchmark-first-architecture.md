# ADR 0001: Benchmark-First Architecture

Status: Accepted for Step 0

Date: 2026-11-02

## Context

Existing projects already provide agent frameworks, LLM evaluators, red-team generators, trace stores, and dashboards. A new generic wrapper would add little durable value and would couple the project to external APIs.

## Decision

The repository's canonical assets are:

- Versioned scenarios
- Agent and tool contracts
- Controlled fault and permission models
- Normalized trial records
- Calibrated evaluation policies
- Statistical comparison rules
- CI governance gates

DeepEval, promptfoo, Langfuse, and OpenTelemetry are replaceable integrations behind those contracts.

## Consequences

- Scenarios and schemas are reviewed before runner implementation.
- Vendor-specific fields cannot be required in the canonical contracts.
- Local execution and result storage remain supported.
- Integration convenience must not weaken deterministic security assertions.
- Schema evolution requires explicit versions and migration notes.
