"""Built-in plugins; optional frameworks are discovered through entry points."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from arlab.evaluation.deterministic import DeterministicEvaluator
from arlab.integrations.opencode import OpenCodeCliAdapter
from arlab.integrations.reference_agent import ReferenceWeatherAdapter
from arlab.plugins import PLUGIN_GROUPS, PluginRegistry
from arlab.storage import JsonlTelemetrySink, JsonResultStore


def registries(root: Path) -> dict[str, PluginRegistry[Any]]:
    result = {kind: PluginRegistry(group) for kind, group in PLUGIN_GROUPS.items()}
    result["agent_adapter"].register("scripted-weather", ReferenceWeatherAdapter)
    result["agent_adapter"].register("opencode", OpenCodeCliAdapter)
    result["evaluator"].register("deterministic", lambda config: DeterministicEvaluator())
    result["result_store"].register("json", lambda config: JsonResultStore(config, root=root))
    result["telemetry_sink"].register(
        "local-jsonl", lambda config: JsonlTelemetrySink(config, root=root)
    )
    for registry in result.values():
        registry.discover()
    return result
