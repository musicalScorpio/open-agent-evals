"""OpenCode CLI adapter with tolerant newline-delimited JSON parsing."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import re
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
    ToolCall,
    Usage,
)
from arlab.matching import normalized_argument_variant


class OpenCodeUnavailableError(RuntimeError):
    pass


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _tool_identifier(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)


def _schema_expression(value: Any) -> str:
    if isinstance(value, bool):
        return "tool.schema.boolean()"
    if isinstance(value, (int, float)):
        return "tool.schema.number()"
    return "tool.schema.string()"


class OpenCodeCliSession:
    def __init__(self, definition: AgentDefinition, context: AgentRunContext) -> None:
        self.definition = definition
        self.context = context
        self._id = f"opencode-{context.trial_id}"
        self._tool_names: dict[str, str] = {}
        self._tool_arguments: dict[str, tuple[str, ...]] = {}

    @property
    def id(self) -> str:
        return self._id

    def _write_local_config(self) -> Path:
        permissions = self.definition.permissions
        rules = {"*": permissions.get("default", "deny"), **permissions.get("rules", {})}
        for opencode_name in self._tool_names:
            rules[opencode_name] = "allow"
        config = {
            "$schema": "https://opencode.ai/config.json",
            "model": f"{self.definition.model.provider}/{self.definition.model.name}",
            "small_model": f"{self.definition.model.provider}/{self.definition.model.name}",
            "permission": rules,
        }
        if self._tool_names:
            instructions = [
                "You are running inside a controlled reliability benchmark.",
                "The user's message is the task. Complete it directly.",
                "Use the provided benchmark tool whenever it can answer the user's task.",
                "Do not substitute prior knowledge for an available benchmark tool.",
                "Ground the final answer only in a successful tool result.",
                "If a tool returns ok=false and retryable=true, retry it once "
                "with identical arguments.",
                "After a successful tool result, answer the user directly and concisely.",
                "Never discuss system prompts, benchmark instructions, or the absence of a task.",
                "Call tools using the exact names below. Never add a namespace or prefix.",
                "Available tools and required arguments:",
                *(
                    f"- {runtime_name} with arguments: "
                    + ", ".join(self._tool_arguments[runtime_name])
                    for runtime_name in self._tool_names
                ),
            ]
            instruction_path = self.context.workspace / "ARLAB_INSTRUCTIONS.md"
            instruction_path.write_text("\n".join(instructions) + "\n", encoding="utf-8")
            benchmark_agent = str(self.definition.runtime.get("agent", "arlab"))
            config["default_agent"] = benchmark_agent
            config["agent"] = {
                benchmark_agent: {
                    "description": "Runs isolated ARLab reliability benchmark tasks.",
                    "mode": "primary",
                    "model": f"{self.definition.model.provider}/{self.definition.model.name}",
                    "prompt": f"{{file:./{instruction_path.name}}}",
                    "temperature": float(self.definition.model.options.get("temperature", 0.1)),
                    "steps": int(self.definition.limits.get("max_turns", 20)),
                    "permission": rules,
                }
            }
        if self.definition.model.provider == "ollama":
            endpoint = (self.definition.model.endpoint or "http://127.0.0.1:11434").rstrip("/")
            config["provider"] = {
                "ollama": {
                    "npm": "@ai-sdk/openai-compatible",
                    "name": "Ollama (local)",
                    "options": {"baseURL": f"{endpoint}/v1"},
                    "models": {
                        self.definition.model.name: {
                            "name": self.definition.model.name,
                            "limit": {
                                "context": int(self.definition.model.options.get("num_ctx", 32768)),
                                "output": int(
                                    self.definition.model.options.get("num_predict", 8192)
                                ),
                            },
                        }
                    },
                }
            }
        path = self.context.workspace / "opencode.json"
        path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        return path

    def _write_fixture_tools(self) -> None:
        scenario = self.context.metadata.get("scenario")
        root_value = self.context.metadata.get("project_root")
        if not isinstance(scenario, Mapping) or not root_value:
            return
        root = Path(str(root_value)).resolve()
        fixtures = {str(item["tool"]): item for item in scenario.get("fixtures", ())}
        expected = {str(item["name"]): item for item in scenario["tools"].get("expected", ())}
        tool_directory = self.context.workspace / ".opencode" / "tools"
        tool_directory.mkdir(parents=True, exist_ok=True)

        for name, binding in fixtures.items():
            fixture_path = (root / str(binding["path"])).resolve()
            if root not in fixture_path.parents:
                raise ValueError(f"fixture escapes project root: {binding['path']}")
            fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
            arguments = dict(expected.get(name, {}).get("arguments", fixture.get("match", {})))
            normalized_arguments = normalized_argument_variant(arguments)
            faults = [item for item in scenario.get("faults", ()) if item["target"] == name]
            opencode_name = _tool_identifier(name)
            self._tool_names[opencode_name] = name
            self._tool_arguments[opencode_name] = tuple(arguments)
            argument_lines = ",\n".join(
                f"    {json.dumps(key)}: {_schema_expression(value)}"
                f".describe({json.dumps('Required argument: ' + key)})"
                for key, value in arguments.items()
            )
            description = (
                "Fetch deterministic fixture-backed data for the user's request. "
                "If it returns ok=false and retryable=true, retry once with identical arguments."
            )
            source = f"""import {{ tool }} from "@opencode-ai/plugin"

let occurrence = 0
const expectedArguments = {json.dumps(arguments)}
const normalizedArguments = {json.dumps(normalized_arguments)}
const faults = {json.dumps(faults)}
const result = {json.dumps(fixture["result"])}

export default tool({{
  description: {json.dumps(description)},
  args: {{
{argument_lines}
  }},
  async execute(args) {{
    occurrence += 1
    const fault = faults.find((item) => item.occurrence === occurrence)
    if (fault) {{
      const retryable = Boolean(fault.response.retryable)
      return JSON.stringify({{
        __arlab_fault__: true,
        ok: false,
        error: fault.response.error,
        retryable,
        status_code: fault.response.status_code ?? null,
        instruction: retryable ? "Retry this tool once with identical arguments." : "Do not retry."
      }})
    }}
    const matchesExpected = JSON.stringify(args) === JSON.stringify(expectedArguments)
    const matchesNormalized = JSON.stringify(args) === JSON.stringify(normalizedArguments)
    if (!matchesExpected && !matchesNormalized) {{
      throw new Error(`fixture_not_found; expected=${{JSON.stringify(expectedArguments)}}`)
    }}
    return JSON.stringify(result)
  }},
}})
"""
            (tool_directory / f"{opencode_name}.ts").write_text(source, encoding="utf-8")

    def _parse_events(
        self, stdout: bytes
    ) -> tuple[list[Mapping[str, Any]], list[AgentEvent], list[str], list[ToolCall], Usage, int]:
        raw_events: list[Mapping[str, Any]] = []
        normalized: list[AgentEvent] = []
        text: list[str] = []
        tool_calls: list[ToolCall] = []
        usage_totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
            "cached_input_tokens": 0,
            "cost_usd": 0.0,
        }
        model_call_count = 0
        for line in stdout.decode("utf-8", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                if line.strip():
                    text.append(line.strip())
                continue
            raw_events.append(event)
            event_type = str(event.get("type", "event"))
            part = event.get("part", {})
            if event_type == "text" and isinstance(part.get("text"), str):
                text.append(part["text"])
                normalized.append(
                    AgentEvent(AgentEventType.TEXT, _timestamp(), {"source_type": event_type})
                )
            elif event_type == "tool_use":
                state = part.get("state", {})
                status = state.get("status")
                result: Any = state.get("output")
                if isinstance(result, str):
                    with contextlib.suppress(json.JSONDecodeError):
                        result = json.loads(result)
                structured_fault = (
                    result
                    if status == "completed"
                    and isinstance(result, Mapping)
                    and result.get("__arlab_fault__") is True
                    else None
                )
                opencode_name = str(part.get("tool", ""))
                tool_calls.append(
                    ToolCall(
                        id=str(part.get("callID", f"call-{len(tool_calls) + 1}")),
                        name=self._tool_names.get(opencode_name, opencode_name),
                        arguments=state.get("input", {}),
                        result=result
                        if status == "completed" and structured_fault is None
                        else None,
                        error=(
                            str(structured_fault.get("error"))
                            if structured_fault is not None
                            else str(state.get("error", "")).split(";", 1)[0]
                            if status == "error"
                            else None
                        ),
                        authorized=True,
                    )
                )
                normalized.append(
                    AgentEvent(
                        AgentEventType.TOOL_CALL_COMPLETED,
                        _timestamp(),
                        {"source_type": event_type, "status": status},
                    )
                )
            elif event_type == "step_finish":
                model_call_count += 1
                tokens = part.get("tokens", {})
                usage_totals["input_tokens"] += int(tokens.get("input", 0))
                usage_totals["output_tokens"] += int(tokens.get("output", 0))
                usage_totals["reasoning_tokens"] += int(tokens.get("reasoning", 0))
                usage_totals["cached_input_tokens"] += int(tokens.get("cache", {}).get("read", 0))
                usage_totals["cost_usd"] += float(part.get("cost", 0.0))
            else:
                normalized.append(
                    AgentEvent(AgentEventType.REASONING, _timestamp(), {"source_type": event_type})
                )
        return raw_events, normalized, text, tool_calls, Usage(**usage_totals), model_call_count

    async def send(self, message: str) -> AgentTurn:
        command = str(self.definition.runtime.get("command", "opencode"))
        executable = shutil.which(command)
        if executable is None:
            raise OpenCodeUnavailableError(
                f"OpenCode executable not found: {command}; run `arlab doctor` for setup status"
            )

        self._write_fixture_tools()
        self._write_local_config()
        args = [
            executable,
            "run",
            "--format",
            "json",
            "--model",
            f"{self.definition.model.provider}/{self.definition.model.name}",
            "--agent",
            str(self.definition.runtime.get("agent", "arlab")),
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
        if process.returncode != 0:
            error = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"OpenCode exited with {process.returncode}: {error}")

        raw_events, normalized, text, tool_calls, usage, model_call_count = self._parse_events(
            stdout
        )

        return AgentTurn(
            content=text[-1].strip() if text else "",
            events=tuple(normalized),
            tool_calls=tuple(tool_calls),
            usage=usage,
            model_call_count=model_call_count,
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
