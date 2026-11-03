# Agent Reliability Lab

Agent Reliability Lab is a reproducible benchmark suite for tool-using AI agents. It measures whether an agent completes a task correctly, uses tools and permissions safely, recovers from controlled failures, and does so within explicit cost and latency budgets.

The project is intentionally **benchmark-first**. DeepEval, promptfoo, Langfuse, and OpenTelemetry are integrations; the durable product is the versioned scenario corpus, controlled execution environment, normalized run record, calibrated metrics, and CI quality gates.

## Run it locally

The first executable benchmark is intentionally self-contained. It does not need a cloud key,
Ollama, or OpenCode: it runs a known-good reference agent against a committed weather fixture,
forces the first tool call to time out, verifies the retry, scores six deterministic metrics, and
repeats the trial three times.

```bash
cd /Users/musicalscorpio/Documents/CODING/agent-reliability-lab
uv sync --extra dev
uv run arlab doctor
uv run arlab validate
uv run arlab run
```

The last command prints a run summary. Full evidence is written to
`results/<run-id>/trial-*.json`, with an aggregate `summary.json`. The `results/` directory is
ignored by Git so local runs do not dirty the repository.

Useful variations:

```bash
# One quick trial instead of the scenario's default three
uv run arlab run --runs 1

# See every agent, evaluator, telemetry, and storage plugin available at runtime
uv run arlab plugins

# Select definitions explicitly
uv run arlab run \
  --scenario suites/smoke/recovery-weather-timeout.yaml \
  --agent agents/reference-weather-recovery.yaml \
  --profile evaluation-profiles/deterministic-only.yaml
```

`arlab doctor` reports Ollama and OpenCode separately. They are optional for this harness
self-test. The OpenCode adapter and Ollama agent definitions are present; connecting benchmark
tools to a real OpenCode session uses generated, trial-isolated custom tools.

After installing OpenCode, starting Ollama, and pulling `gpt-oss:20b`, run the same scenario
against the real local agent:

```bash
uv run arlab run --agent agents/opencode-gpt-oss-20b.yaml --runs 1
```

A nonzero exit code means the candidate failed one or more quality gates; it does not necessarily
mean the harness crashed. Inspect the printed result directory to see task, tool, authorization,
and budget evidence.

## Synthetic comparison dataset

The first human-reviewed synthetic dataset contains three fixture-grounded weather cases across
validation and test splits. Validate it, export DeepEval-compatible goldens, or compare agents:

```bash
uv run arlab dataset validate
uv run arlab dataset export-deepeval

# Establish the known-good baseline
uv run arlab dataset run \
  --agent agents/reference-weather-recovery.yaml

# Compare the baseline with the local OpenCode candidate
uv run arlab dataset run \
  --agent agents/reference-weather-recovery.yaml \
  --agent agents/opencode-gpt-oss-20b.yaml
```

The source manifest is `datasets/synthetic/weather-reliability-v1.yaml`. The export command writes
one JSON object per line with DeepEval's `input`, `expected_output`, and `context` golden fields,
plus ARLab provenance and tool expectations in `additional_metadata`, under `results/exports/` by
default. DeepEval can load the file directly with
`EvaluationDataset.add_goldens_from_jsonl_file()`; DeepEval remains optional.
The comparison JSON reports pass rate, average latency, model/tool calls, cost, and token totals for
each agent. Increase `--runs` to measure repeatability instead of relying on a single attempt.

### World capitals dataset

The curated capitals dataset contains 195 records: the 193 UN member states plus Palestine and
Vatican City/Holy See. Its prompts are generated deterministically from a pinned open-data source;
special cases such as South Africa, Bolivia, Sri Lanka, Eswatini, Malaysia, Palestine, Switzerland,
and Nauru preserve multiple, claimed, administrative, or de facto capital roles.

```bash
# Validate all 195 records and export them as DeepEval goldens
uv run arlab dataset validate --dataset datasets/curated/world-capitals-v1.yaml
uv run arlab dataset export-deepeval \
  --dataset datasets/curated/world-capitals-v1.yaml

# Fast local-model smoke run, then the complete benchmark
uv run arlab dataset run \
  --dataset datasets/curated/world-capitals-v1.yaml \
  --limit 5
uv run arlab dataset run \
  --dataset datasets/curated/world-capitals-v1.yaml
```

Use `--split validation` or `--split test` to select a split. A complete local run makes 195 model
requests per agent and can take a while, so start with `--limit`. Dataset-specific ODbL attribution
and generation provenance are committed beside the JSONL file.

To run a special case directly, use its stable ID, for example
`--case geography.capital.za` for South Africa. Repeat `--case` to select several countries.

## Status

**Step 1B — First runnable vertical slice**

The repository now has validated definitions, pluggable runtime registries, deterministic fixture
tools and fault injection, normalized results, local JSON/JSONL evidence, and an executable smoke
benchmark. DeepEval, promptfoo, Langfuse, and OpenTelemetry remain optional runtime integrations;
none are required by the core.

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
agents/                  Portable agent definitions selected at runtime
evaluation-profiles/     Runtime-selectable evaluator and telemetry stacks
fixtures/                Deterministic tool and environment data
src/arlab/               Core contracts, runner, built-ins, and plugin discovery
integrations/            Future separately packaged framework integrations
docs/                    Product, methodology, and architecture decisions
schemas/                 Versioned agent, scenario, result, and profile contracts
suites/                  Human-reviewable benchmark scenarios
tests/                   Contract and plugin-boundary tests
.github/                 Contribution and governance templates
```

The core does not import OpenCode, Ollama, DeepEval, promptfoo, or Langfuse. Runtime profiles resolve optional integrations through standard plugin entry points.

See [the plugin architecture](docs/plugin-architecture.md) and [agent definitions](agents/README.md).

See [the Step 0 charter](docs/step-0-project-charter.md) for the product decisions and
[the plugin architecture](docs/plugin-architecture.md) for extension contracts.

## License

Apache-2.0. See [LICENSE](LICENSE).
