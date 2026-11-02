"""Runtime discovery for optional agent and evaluation integrations."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from importlib.metadata import EntryPoint, entry_points
from typing import Generic, TypeVar


T = TypeVar("T")
Factory = Callable[[], T]

PLUGIN_GROUPS = {
    "agent_adapter": "arlab.agent_adapters",
    "evaluator": "arlab.evaluators",
    "telemetry_sink": "arlab.telemetry_sinks",
    "result_store": "arlab.result_stores",
    "tool_provider": "arlab.tool_providers",
}


class PluginRegistry(Generic[T]):
    """Small registry that supports built-ins and installed entry-point plugins."""

    def __init__(self, group: str) -> None:
        if group not in PLUGIN_GROUPS.values():
            raise ValueError(f"unknown plugin group: {group}")
        self.group = group
        self._factories: dict[str, Factory[T]] = {}

    def register(self, name: str, factory: Factory[T], *, replace: bool = False) -> None:
        if not name:
            raise ValueError("plugin name is required")
        if name in self._factories and not replace:
            raise ValueError(f"plugin already registered: {name}")
        self._factories[name] = factory

    def discover(self, discovered: Iterable[EntryPoint] | None = None) -> None:
        candidates = discovered if discovered is not None else entry_points(group=self.group)
        for entry_point in candidates:
            self.register(entry_point.name, entry_point.load())

    def create(self, name: str) -> T:
        try:
            factory = self._factories[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._factories)) or "none"
            raise KeyError(f"plugin not found: {name}; available: {available}") from exc
        return factory()

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))

