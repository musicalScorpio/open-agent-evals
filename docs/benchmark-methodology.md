# Benchmark Methodology

## Unit of evaluation

A **scenario** defines the task, environment, tools, permissions, injected faults, budgets, and expected behavior. A **trial** is one execution of one scenario against one agent variant. A **benchmark run** is a versioned collection of trials.

The framework reports trial-level evidence first and aggregates second.

## Evaluation order

Each trial is evaluated in this order:

1. Validate the run record and required telemetry.
2. Verify authorization and side effects.
3. Verify deterministic final-state and tool-call expectations.
4. Compute resource measurements.
5. Apply semantic evaluators only to unresolved qualitative conditions.
6. Assign normalized failure categories.
7. Apply scenario and suite gates.

This order prevents a semantic score from masking an exact policy violation.

## Core metric families

### Outcome

- Task success rate
- Partial condition coverage
- False-success rate
- Safe-refusal correctness

### Tool use

- Tool-selection precision, recall, and F1
- Required-call coverage
- Unnecessary-call rate
- Call-order accuracy
- Duplicate-call rate
- Field-level argument correctness

### Multi-turn behavior

- Conversation completion rate
- Turns to completion
- State-retention accuracy
- Loop and repeated-question rates
- Premature-completion rate

### Recovery

- Recovery success rate
- Attempts and time to recovery
- Unsafe-retry rate
- Duplicate-side-effect rate
- Graceful-degradation rate

### Security and authorization

- Authorization violations
- Cross-tenant access attempts
- Secret exfiltration events
- Injection compromise rate
- Approval-bypass rate
- Forbidden side effects

### Efficiency

- Model and evaluator cost
- Cost per successful task
- Input, output, cached, and reasoning tokens when available
- Model and tool call counts
- Median, p90, and p95 latency
- Reliability gained per additional dollar and second

## Failure taxonomy

Failures receive one primary category and may receive multiple contributing tags.

Primary categories:

- `task.incomplete`
- `task.false_success`
- `tool.wrong_selection`
- `tool.missing_call`
- `tool.invalid_arguments`
- `tool.invalid_order`
- `tool.duplicate_side_effect`
- `recovery.retry_exhausted`
- `recovery.unsafe_retry`
- `recovery.no_fallback`
- `security.prompt_injection`
- `security.secret_exfiltration`
- `authorization.forbidden_tool`
- `authorization.cross_tenant`
- `authorization.approval_bypass`
- `budget.turns_exceeded`
- `budget.tool_calls_exceeded`
- `budget.latency_exceeded`
- `budget.cost_exceeded`
- `infrastructure.harness_error`
- `infrastructure.provider_error`

Harness and provider failures are reported separately from agent failures and must not silently become passes.

## Repetition tiers

| Tier | Default repetitions | Intended use |
|---|---:|---|
| Local smoke | 1 | Fast author feedback |
| Pull request | 3 | Obvious regression detection |
| Nightly | 20 | Run-to-run reliability estimation |
| Release | 50 for critical scenarios | Governance evidence |

Suites may override these defaults based on cost, risk, or deterministic behavior.

## Statistical reporting

Reports must include:

- Success numerator and denominator
- Confidence interval for rates
- Median and tail latency
- Cost distributions and cost per success
- Failure-category distribution
- Paired baseline/candidate deltas when the same scenarios are used
- Missing-data and infrastructure-error counts

The initial implementation should use Wilson score intervals for binary rates and bootstrap intervals for non-normal continuous metrics. Exact implementation choices will be recorded before they become release gates.

## Evaluator calibration

Semantic evaluators require a versioned calibration set with human-reviewed examples. A gating evaluator must record:

- Evaluator identifier and version
- Judge model and configuration
- Rubric or prompt hash
- Judge-to-human agreement
- False-pass and false-fail rates
- Last calibration date

Changing a judge model, rubric, or threshold creates a new evaluator version.

## Comparison rules

A baseline and candidate are comparable only when they share:

- Scenario schema and scenario content versions
- Tool fixtures and fault schedules
- Evaluator definitions
- Relevant environment settings
- Repetition policy, or an explicitly documented statistical adjustment

Reports disclose model/provider nondeterminism and do not describe hosted model runs as perfectly reproducible.

## Gate philosophy

Gates have three forms:

1. **Veto:** zero tolerance, used for severe security and authorization failures.
2. **Absolute threshold:** minimum reliability or maximum resource usage.
3. **Regression threshold:** permitted change relative to an approved baseline.

A composite score may be displayed for exploration, but it cannot override vetoes and is not the canonical release decision.
