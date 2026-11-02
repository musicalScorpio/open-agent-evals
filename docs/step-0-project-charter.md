# Step 0: Project Charter

Status: Proposed

Date: 2026-11-02

## Problem

Agent demonstrations frequently report that an agent completed a task once. That does not establish reliability, safe autonomy, regression resistance, or acceptable operating cost.

Teams need a repeatable way to expose different agents to the same tasks, tools, permissions, injected failures, and budgets; measure the resulting behavior; compare variants; and enforce release policies.

## Product statement

Agent Reliability Lab is a framework-neutral benchmark laboratory for evaluating tool-using agents under controlled conditions. It produces reproducible evidence about task success, trajectory quality, recovery, authorization, security, cost, latency, and run-to-run variability.

## Primary users

1. Agent engineers comparing prompts, models, memory, and orchestration loops.
2. AI platform and reliability engineers defining shared test infrastructure.
3. Security engineers validating prompt-injection and authorization boundaries.
4. Governance teams requiring versioned release evidence and audit trails.
5. Engineering leaders making reliability-versus-cost decisions.

## v0.1 outcomes

The first public benchmark must let a third party:

1. Implement a small adapter for an agent.
2. Run a versioned suite locally.
3. Reproduce controlled tool failures.
4. Repeat scenarios across multiple trials.
5. Compare a baseline and candidate.
6. Inspect failures down to individual tool calls.
7. Enforce deterministic CI gates.
8. Export traces through OpenTelemetry.

## v0.1 scope

- Python runner and Python/HTTP adapter contracts
- YAML scenario authoring with JSON Schema validation
- Deterministic mock tools and a side-effect ledger
- Task, tool, argument, recovery, security, cost, and latency measurements
- Repetition tiers for local, pull-request, nightly, and release runs
- Local JSON/Parquet-compatible result records
- DeepEval integration for selected semantic and conversational metrics
- promptfoo integration for adversarial generation and red-team execution
- OpenTelemetry instrumentation
- Optional Langfuse export and comparison workflow
- A compact dashboard or static report for comparisons

## Explicit non-goals for v0.1

- Building a new general-purpose agent framework
- Replacing DeepEval, promptfoo, Langfuse, or OpenTelemetry
- Hosting arbitrary untrusted third-party code as a public service
- Claiming a universal definition of intelligence or autonomy
- Reducing all reliability and safety evidence to one leaderboard score
- Supporting every agent framework before the adapter contract is stable
- Treating an LLM judge as authoritative for exact authorization or side effects

## Success measures

Step 1 and later work should optimize toward these acceptance measures:

- A known-good reference agent passes the smoke suite.
- An intentionally defective agent fails the expected scenarios.
- Re-running a deterministic scenario produces identical structural results.
- Every run records scenario, agent, environment, and evaluator versions.
- Every forbidden side effect is detectable without an LLM judge.
- Baseline/candidate results include denominators and confidence intervals.
- A clean checkout can reproduce the published v0.1 example.

## Product principles

### Benchmark-first

The scenario corpus, schemas, failure model, and governance rules are the product. Vendor integrations remain replaceable.

### Evidence before averages

Reports retain raw trial outcomes and failure categories. Aggregate scores never erase the evidence underneath them.

### Deterministic where possible

Exact expected tools, arguments, permissions, side effects, budgets, and final state use code-based oracles. Semantic judging is used only when the desired outcome cannot be captured deterministically.

### Safety vetoes

Unauthorized actions, secret exfiltration, cross-tenant access, and irreversible duplicate side effects cannot be offset by high scores elsewhere.

### Reproducibility with honest limits

The system records all controllable inputs and versions. It does not claim that hosted model outputs are deterministic when the provider cannot guarantee that property.

## Step 0 decisions

| Area | Decision |
|---|---|
| Project name | `agent-reliability-lab` |
| Core language | Python 3.12+ |
| Scenario format | YAML validated by versioned JSON Schema |
| Result contract | JSON-compatible normalized run record |
| Agent boundary | Framework-neutral adapter; Python and HTTP first |
| Evaluation order | Deterministic oracle, then semantic evaluator when required |
| Security policy | Hard veto for boundary violations |
| Telemetry | OpenTelemetry as the canonical emission boundary |
| Experiment backend | Local-first; Langfuse optional |
| License | Apache-2.0 |

## Step 0 exit criteria

- [x] Project identity and product boundary documented
- [x] Primary users and non-goals documented
- [x] Architecture direction recorded as ADRs
- [x] Benchmark methodology drafted
- [x] Autonomy maturity model drafted
- [x] Scenario schema drafted
- [x] Result schema drafted
- [x] One illustrative smoke scenario added
- [x] Contribution and security expectations added
- [ ] Human review of the contracts completed
- [ ] Step 1 reference agent selected

Step 0 is complete when the final two review items are resolved. No runner implementation should force incompatible changes before that review.
