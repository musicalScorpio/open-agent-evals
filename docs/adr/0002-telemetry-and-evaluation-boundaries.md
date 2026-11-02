# ADR 0002: Telemetry and Evaluation Boundaries

Status: Accepted for Step 0

Date: 2026-11-02

## Context

The project needs trace portability, experiment comparison, exact policy checks, semantic scoring, and adversarial test generation. No single external tool is authoritative for all of these concerns.

## Decision

1. OpenTelemetry is the canonical emission boundary for spans, events, and resource measurements.
2. The normalized result record is the canonical benchmark artifact.
3. Deterministic project-owned evaluators are authoritative for permissions, side effects, exact tool expectations, and budgets.
4. DeepEval supplies selected semantic, tool, argument, trajectory, and conversational metrics.
5. promptfoo supplies adversarial case generation, red-team execution, and selected model-matrix assertions.
6. Langfuse is an optional trace, dataset, experiment, and comparison backend.

## Consequences

- The repository maintains an explicit mapping between its versioned fields and OpenTelemetry GenAI conventions.
- Experimental upstream semantic conventions are pinned rather than assumed stable.
- Raw tool arguments and model content are redacted or disabled by default when they may contain secrets or personal data.
- A Langfuse outage cannot invalidate locally stored benchmark evidence.
- Evaluator provenance is stored with every semantic score.
