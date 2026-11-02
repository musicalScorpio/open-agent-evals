# Contributing

Agent Reliability Lab values benchmark clarity over scenario volume.

## Scenario contributions

A scenario contribution should:

1. Describe one primary reliability or security claim.
2. Declare tools, permissions, budgets, and expected behavior explicitly.
3. Prefer deterministic checks where exact behavior is knowable.
4. Include a known-pass and known-fail rationale.
5. Avoid real secrets, personal data, or production credentials.
6. Explain whether failures are attributed to the agent, harness, or provider.
7. State the applicable autonomy level and risk tier.

Changes to a scenario after publication require a new version or an explicit migration note when they can change benchmark results.

## Evaluator contributions

Semantic evaluators must include calibration evidence before they can become release gates. Authorization, side effects, and exact budgets must use deterministic evaluators.

## Pull requests

Pull requests should identify:

- The reliability claim being added or changed
- The affected scenario and schema versions
- Expected benchmark impact
- Validation performed
- Any new data, privacy, or cost risk
