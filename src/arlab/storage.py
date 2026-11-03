"""Simple, inspectable local result storage."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class JsonResultStore:
    id = "json"

    def __init__(self, config: Mapping[str, Any], *, root: Path) -> None:
        configured = Path(str(config.get("directory", "results")))
        self.directory = configured if configured.is_absolute() else root / configured
        self.last_path: Path | None = None

    async def write_trial(self, trial: Mapping[str, Any]) -> None:
        directory = self.directory / str(trial["run_id"])
        directory.mkdir(parents=True, exist_ok=True)
        self.last_path = directory / f"{trial['trial_id']}.json"
        self.last_path.write_text(
            json.dumps(trial, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    async def read_run(self, run_id: str) -> list[Mapping[str, Any]]:
        directory = self.directory / run_id
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(directory.glob("trial-*.json"))
        ]


class JsonlTelemetrySink:
    id = "local-jsonl"

    def __init__(self, config: Mapping[str, Any], *, root: Path) -> None:
        configured = Path(str(config.get("path", "results/telemetry.jsonl")))
        self.path = configured if configured.is_absolute() else root / configured

    async def emit(self, event: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")

    async def flush(self) -> None:
        return None
