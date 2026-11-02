"""Dependency-free value objects shared by all agent adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


def _frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


class AgentEventType(StrEnum):
    """Normalized lifecycle events emitted by an agent adapter."""

    TEXT = "text"
    REASONING = "reasoning"
    TOOL_CALL_REQUESTED = "tool_call.requested"
    TOOL_CALL_COMPLETED = "tool_call.completed"
    PERMISSION_REQUESTED = "permission.requested"
    RETRY_SCHEDULED = "retry.scheduled"
    USAGE = "usage"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class ModelDefinition:
    provider: str
    name: str
    endpoint: str | None = None
    license: str | None = None
    options: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.provider or not self.name:
            raise ValueError("model provider and name are required")
        object.__setattr__(self, "options", _frozen_mapping(self.options))


@dataclass(frozen=True, slots=True)
class AgentCapabilities:
    tool_use: bool = False
    multi_turn: bool = False
    streaming: bool = False
    resumable: bool = False
    permission_handling: bool = False
    structured_output: bool = False


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    """Portable description of an agent variant, independent of its runtime."""

    id: str
    version: str
    adapter: str
    model: ModelDefinition
    description: str = ""
    capabilities: AgentCapabilities = field(default_factory=AgentCapabilities)
    runtime: Mapping[str, Any] = field(default_factory=dict)
    permissions: Mapping[str, Any] = field(default_factory=dict)
    limits: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id or not self.version or not self.adapter:
            raise ValueError("agent id, version, and adapter are required")
        for attribute in ("runtime", "permissions", "limits", "metadata"):
            object.__setattr__(self, attribute, _frozen_mapping(getattr(self, attribute)))
        object.__setattr__(self, "tags", tuple(self.tags))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> AgentDefinition:
        model = value["model"]
        capabilities = value.get("capabilities", {})
        runtime = value["runtime"]
        return cls(
            id=str(value["id"]),
            version=str(value["version"]),
            adapter=str(runtime["adapter"]),
            description=str(value.get("description", "")),
            model=ModelDefinition(
                provider=str(model["provider"]),
                name=str(model["name"]),
                endpoint=model.get("endpoint"),
                license=model.get("license"),
                options=model.get("options", {}),
            ),
            capabilities=AgentCapabilities(**capabilities),
            runtime=runtime,
            permissions=value.get("permissions", {}),
            limits=value.get("limits", {}),
            metadata=value.get("metadata", {}),
            tags=tuple(value.get("tags", ())),
        )


@dataclass(frozen=True, slots=True)
class AgentRunContext:
    run_id: str
    trial_id: str
    scenario_id: str
    workspace: Path
    environment: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id or not self.trial_id or not self.scenario_id:
            raise ValueError("run, trial, and scenario identifiers are required")
        object.__setattr__(self, "environment", _frozen_mapping(self.environment))
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str | None = None
    authorized: bool | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "arguments", _frozen_mapping(self.arguments))


@dataclass(frozen=True, slots=True)
class Usage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    cached_input_tokens: int | None = None
    cost_usd: float | None = None


@dataclass(frozen=True, slots=True)
class AgentEvent:
    type: AgentEventType
    timestamp: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", _frozen_mapping(self.payload))


@dataclass(frozen=True, slots=True)
class AgentTurn:
    content: str
    events: tuple[AgentEvent, ...] = ()
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage | None = None
    finished: bool = False
    raw: Any = None

