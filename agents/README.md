# Agent Definitions

Agent definitions describe **what to run** without importing the runtime into the benchmark core. The `runtime.adapter` value selects an installed `arlab.agent_adapters` plugin at execution time.

The initial definitions use OpenCode with a local Ollama endpoint. They do not download models, start services, or contain credentials.

Profiles:

- `opencode-gpt-oss-20b.yaml` — default local agent with practical memory headroom
- `opencode-qwen3-coder-30b.yaml` — high-memory coding challenger
- `opencode-qwen3.5-9b.yaml` — fast smoke-test agent

All permissions are deny-by-default. Scenario-specific setup may narrow or explicitly enable individual tools, but it may not silently broaden the definition.

