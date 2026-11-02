# Autonomy Maturity Model

This model is specific to Agent Reliability Lab. It is a governance lens, not a claim of universal industry standardization.

## Levels

### L0 — Respond

The system generates content but cannot invoke external tools or create side effects.

Evidence required:

- Output correctness and groundedness
- Content and data-handling safety
- Cost and latency budgets

### L1 — Assist

The system can retrieve data and recommend actions but cannot perform consequential writes.

Evidence required:

- Correct retrieval and tool selection
- Source and tenant boundaries
- Resistance to untrusted retrieved instructions
- Honest communication of uncertainty

### L2 — Act with approval

The system can perform actions, but consequential or irreversible operations require explicit approval.

Evidence required:

- Argument and target correctness
- Approval enforcement
- Idempotency and duplicate-call protection
- Clear preview of intended side effects
- Safe handling of denied or expired approval

### L3 — Bounded autonomy

The system can complete multi-step tasks within explicit permissions, budgets, and escalation rules.

Evidence required:

- Multi-turn and trajectory reliability
- Recovery from transient failures
- Bounded retries and resource use
- Cross-tool state consistency
- Escalation when policy or confidence requires it
- Zero critical authorization violations

### L4 — Supervised operations

The system can manage longer-running or cross-system workflows with monitoring, rollback, and human intervention points.

Evidence required:

- Durable state and resumability
- Continuous policy enforcement
- Rollback or compensating actions
- Incident containment and shutdown controls
- Traceable human interventions
- Continuous evaluation on production-derived cases

### L5 — Adaptive autonomy

The system adapts plans under changing conditions while remaining inside dynamic policy and risk boundaries.

Evidence required:

- Reliability under distribution shift
- Policy-preserving replanning
- Strong long-horizon repeatability evidence
- Continuous drift detection
- Tested containment and recovery procedures
- Independent governance review

## Qualification rule

An agent qualifies for a level only when it passes all mandatory gates for that level and every preceding level. Average scores do not compensate for failed authorization or containment requirements.

The initial public release should target credible evaluation through L3. L4 and L5 remain documented extension points until the repository includes durable workflow and continuous-monitoring benchmarks.
