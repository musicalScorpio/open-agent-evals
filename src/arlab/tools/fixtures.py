"""Deterministic tool responses and occurrence-based fault injection."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class ToolInvocationError(RuntimeError):
    def __init__(self, error_type: str, *, retryable: bool = False, details: Any = None) -> None:
        super().__init__(error_type)
        self.error_type = error_type
        self.retryable = retryable
        self.details = details


class FixtureToolProvider:
    """Resolve tools from committed fixtures and inject declared failures."""

    id = "fixtures"

    def __init__(self, scenario: Mapping[str, Any], root: Path) -> None:
        self._root = root.resolve()
        self._scenario = scenario
        self._calls: dict[str, int] = defaultdict(int)
        self._fixtures = self._load_fixtures(scenario.get("fixtures", ()))

    def _load_fixtures(self, bindings: Any) -> list[Mapping[str, Any]]:
        fixtures = []
        for binding in bindings:
            relative = Path(str(binding["path"]))
            path = (self._root / relative).resolve()
            if self._root not in path.parents:
                raise ValueError(f"fixture escapes project root: {relative}")
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("tool") != binding["tool"]:
                raise ValueError(f"fixture tool mismatch in {relative}")
            fixtures.append(value)
        return fixtures

    async def invoke(self, name: str, arguments: Mapping[str, Any]) -> Any:
        self._calls[name] += 1
        occurrence = self._calls[name]
        for fault in self._scenario.get("faults", ()):
            if fault["target"] == name and int(fault["occurrence"]) == occurrence:
                response = fault["response"]
                raise ToolInvocationError(
                    str(response["error"]),
                    retryable=bool(response.get("retryable", False)),
                    details=response.get("details"),
                )

        for fixture in self._fixtures:
            if fixture["tool"] == name and dict(fixture.get("match", {})) == dict(arguments):
                return fixture["result"]
        raise ToolInvocationError("fixture_not_found", retryable=False)
