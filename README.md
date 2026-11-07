# Agent Reliability Lab

Agent Reliability Lab is a reproducible benchmark suite for tool-using AI agents. It measures whether an agent completes a task correctly, uses tools and permissions safely, recovers from controlled failures, and does so within explicit cost and latency budgets.

The project is intentionally **benchmark-first**. DeepEval, promptfoo, Langfuse, and OpenTelemetry are integrations; the durable product is the versioned scenario corpus, controlled execution environment, normalized run record, calibrated metrics, and CI quality gates.

## Quickstart

ARLab has two useful starting modes:

1. **Harness self-test:** requires only Git and `uv`; no model, account, API key, OpenCode, or
   Ollama is needed.
2. **Real local-agent benchmark:** adds OpenCode 1.x, Ollama, and the local `gpt-oss:20b` model.

### 1. Clone and install

Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/) if it is not already
available. On macOS, either command works:

```bash
brew install uv
# or: curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then clone and install the locked project dependencies:

```bash
git clone https://github.com/musicalScorpio/open-agent-evals.git
cd open-agent-evals
uv sync --extra dev
```

`uv` creates the project virtual environment and installs dependencies from `pyproject.toml` and
`uv.lock`. You do not need to activate the environment; use `uv run` for every command below.

### 2. Run the self-contained harness test

```bash
uv run arlab doctor
uv run arlab validate
uv run pytest -q
uv run arlab run --runs 1
```

This uses the built-in reference agent and committed weather fixtures. It injects a retryable tool
failure, verifies recovery, evaluates six deterministic quality gates, and writes evidence locally.
It works even when `doctor` reports OpenCode or Ollama as missing.

The final command prints a `result_directory`. Inspect its evidence with:

```bash
# Replace <run-id> with the value printed by the command
cat results/<run-id>/summary.json
cat results/<run-id>/trial-001.json
```

### 3. Install the real local-agent stack

ARLab's OpenCode adapter is currently tested with **OpenCode 1.19.5**. OpenCode 1 and 2 use the
same executable name but different configuration formats, so use the official OpenCode 1 installer:

```bash
curl -fsSL https://opencode.ai/install | bash
opencode --version
```

Install [Ollama](https://ollama.com/download), start it, and pull the configured model:

```bash
curl -fsSL https://ollama.com/install.sh | sh

# Run this in a separate terminal if the Ollama app/service is not already running
ollama serve

# Back in the project terminal
ollama pull gpt-oss:20b
ollama list
uv run arlab doctor
```

`gpt-oss:20b` is a large local download and needs substantially more memory than a small model.
No cloud key is required: OpenCode calls Ollama at `http://127.0.0.1:11434`.

### 4. Run a real OpenCode + Ollama benchmark

```bash
uv run arlab run \
  --scenario suites/smoke/recovery-weather-timeout.yaml \
  --agent agents/opencode-gpt-oss-20b.yaml \
  --profile evaluation-profiles/deterministic-only.yaml \
  --runs 1
```

The exit code is meaningful:

- `0`: every required quality gate passed.
- `1`: the harness ran, but the candidate failed at least one quality gate or configuration check.

A failed benchmark is not automatically a harness crash. Open the printed `trial-001.json` and
inspect `outcome`, `tool_calls`, `measurements`, and `evaluations` to see the exact reason.

### Useful commands

```bash
# List installed runtime adapters, evaluators, telemetry sinks, and result stores
uv run arlab plugins

# Run the default reference scenario three times, as declared by the scenario
uv run arlab run

# Show command-specific flags
uv run arlab --help
uv run arlab dataset run --help
```

All generated evidence stays under `results/`, which is ignored by Git. ARLab does not write API
keys, environment files, prompts from unrelated sessions, or runtime traces into committed source
directories.

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

## Customer voice-agent evaluation

The repository now includes a fully synthetic, local customer-support call with one audio clip per
turn, a reference and observed transcript, and an explicit decision-policy oracle. Run the harness
baseline first, then the real OpenCode + Ollama candidate:

```bash
uv run arlab run \
  --scenario suites/voice/customer-support/refund-without-verification.yaml \
  --agent agents/reference-voice-decision.yaml \
  --profile evaluation-profiles/voice-local.yaml \
  --runs 1

uv run arlab run \
  --scenario suites/voice/customer-support/refund-without-verification.yaml \
  --agent agents/opencode-gpt-oss-20b.yaml \
  --profile evaluation-profiles/voice-local.yaml \
  --runs 3
```

The required gates cover audio traceability, ASR word error rate, exact next-action correctness,
policy/authorization compliance, customer-message requirements, and operational budgets. Export a
local, non-uploading trace in Confident AI's documented per-message audio shape with:

```bash
uv run arlab voice export-trace
```

See [customer voice-agent evaluation](docs/voice-evaluation.md) for the scoring model, result paths,
DeepEval's optional semantic role, privacy guidance, and instructions for adding real calls safely.

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
