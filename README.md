# Agent Reliability Lab

Agent Reliability Lab is a reproducible benchmark suite for tool-using AI agents. It measures whether an agent completes a task correctly, uses tools and permissions safely, recovers from controlled failures, and does so within explicit cost and latency budgets.

The project is intentionally **benchmark-first**. DeepEval, promptfoo, Langfuse, and OpenTelemetry are integrations; the durable product is the versioned scenario corpus, controlled execution environment, normalized run record, calibrated metrics, and CI quality gates.

## Status

**Step 0 — Project inception**

The repository currently defines the product boundary, benchmark methodology, autonomy maturity model, architecture decisions, and initial data contracts. The executable runner begins in Step 1.

## North-star question

> Given the same task, permissions, tools, failures, and budget, which agent completes the work more reliably—and how confident are we in that conclusion?

## Design principles

1. Repeat runs; never infer reliability from a single success.
2. Prefer deterministic oracles over model judges.
3. Treat security and authorization failures as vetoes, not weighted penalties.
4. Preserve every score's provenance: code, prompt, model, tools, scenario, and evaluator versions.
5. Keep the agent adapter vendor- and framework-neutral.
6. Make local, offline result storage a first-class mode.
7. Make every aggregate result traceable to an individual run and tool call.

## Planned capabilities

- Task success and partial-completion scoring
- Tool-selection, argument, ordering, and duplicate-call analysis
- Multi-turn completion and state-retention tests
- Deterministic fault injection and recovery evaluation
- Prompt-injection and authorization-boundary suites
- Cost, latency, token, and model comparison
- Repeatability statistics and baseline/candidate comparisons
- OpenTelemetry traces and optional Langfuse experiment export
- Risk-based CI quality gates and audit evidence bundles

## Repository map

```text
docs/                    Product, methodology, and architecture decisions
schemas/                 Versioned scenario and result contracts
suites/                  Human-reviewable benchmark scenarios
.github/                 Contribution and governance templates
```

The runnable package, adapters, sandbox, evaluators, telemetry layer, and dashboard will be added incrementally after the contracts are validated.

## Step 0 review checklist

- [ ] Confirm the v0.1 target users and non-goals
- [ ] Review the initial scenario schema
- [ ] Review the initial result schema
- [ ] Confirm the autonomy maturity definitions
- [ ] Confirm the default CI gate philosophy
- [ ] Choose the first reference agent for Step 1

See [the Step 0 charter](docs/step-0-project-charter.md) for the decisions and exit criteria.

## License

Apache-2.0. See [LICENSE](LICENSE).
