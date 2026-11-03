"""OpenCode CLI adapter with tolerant newline-delimited JSON parsing."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arlab.agents import (
    AgentDefinition,
    AgentEvent,
    AgentEventType,
    AgentRunContext,
    AgentTurn,
)


class OpenCodeUnavailableError(RuntimeError):
    pass


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _text_fragments(value: Any) -> list[str]:
    fragments: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"text", "content"} and isinstance(item, str):
                fragments.append(item)
            elif isinstance(item, (dict, list)):
                fragments.extend(_text_fragments(item))
    elif isinstance(value, list):
        for item in value:
            fragments.extend(_text_fragments(item))
    return fragments


class OpenCodeCliSession:
    def __init__(self, definition: AgentDefinition, context: AgentRunContext) -> None:
        self.definition = definition
        self.context = context
        self._id = f"opencode-{context.trial_id}"

    @property
    def id(self) -> str:
        return self._id

    def _write_local_config(self) -> Path:
        permissions = self.definition.permissions
        rules = {"*": permissions.get("default", "deny"), **permissions.get("rules", {})}
        config = {
            "$schema": "https://opencode.ai/config.json",
            "model": f"{self.definition.model.provider}/{self.definition.model.name}",
            "permission": rules,
        }
        path = self.context.workspace / "opencode.json"
        path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        return path

    async def send(self, message: str) -> AgentTurn:
        command = str(self.definition.runtime.get("command", "opencode"))
        executable = shutil.which(command)
        if executable is None:
            raise OpenCodeUnavailableError(
                f"OpenCode executable not found: {command}; run `arlab doctor` for setup status"
            )

        self._write_local_config()
        args = [
            executable,
            "run",
            "--standalone",
            "--format",
            "json",
            "--model",
            f"{self.definition.model.provider}/{self.definition.model.name}",
            "--agent",
            str(self.definition.runtime.get("agent", "build")),
            "--dir",
            str(self.context.workspace),
        ]
        if bool(self.definition.runtime.get("auto_approve", True)):
            args.append("--auto")
        args.append(message)

        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **self.context.environment},
        )
        stdout, stderr = await process.communicate()
        raw_events: list[Mapping[str, Any]] = []
        normalized: list[AgentEvent] = []
        text: list[str] = []
        for line in stdout.decode("utf-8", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                if line.strip():
                    text.append(line.strip())
                continue
            raw_events.append(event)
            event_type = str(event.get("type", "event"))
            fragments = _text_fragments(event)
            if fragments:
                text.extend(fragments)
            normalized.append(
                AgentEvent(
                    AgentEventType.TEXT if fragments else AgentEventType.REASONING,
                    _timestamp(),
                    {"source_type": event_type},
                )
            )

        if process.returncode != 0:
            error = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"OpenCode exited with {process.returncode}: {error}")

        return AgentTurn(
            content="\n".join(fragment for fragment in text if fragment).strip(),
            events=tuple(normalized),
            finished=True,
            raw=raw_events,
        )

    async def close(self) -> None:
        return None


class OpenCodeCliAdapter:
    id = "opencode"

    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        self.config = dict(config or {})

    async def open_session(
        self,
        definition: AgentDefinition,
        context: AgentRunContext,
    ) -> OpenCodeCliSession:
        return OpenCodeCliSession(definition, context)
