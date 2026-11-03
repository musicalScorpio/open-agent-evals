"""Normalized inputs and outputs for any evaluation framework."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


def _frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


@dataclass(frozen=True, slots=True)
class EvaluatorDefinition:
    id: str
    adapter: str
    metrics: tuple[str, ...] = ()
    config: Mapping[str, Any] = field(default_factory=dict)
    required: bool = True

    def __post_init__(self) -> None:
        if not self.id or not self.adapter:
            raise ValueError("evaluator id and adapter are required")
        object.__setattr__(self, "metrics", tuple(self.metrics))
        object.__setattr__(self, "config", _frozen_mapping(self.config))


@dataclass(frozen=True, slots=True)
class EvaluationProfile:
    id: str
    version: str
    evaluators: tuple[EvaluatorDefinition, ...]
    telemetry_sinks: tuple[str, ...] = ()
    result_store: str = "local"
    result_store_config: Mapping[str, Any] = field(default_factory=dict)
    fail_fast: bool = False

    def __post_init__(self) -> None:
        if not self.id or not self.version:
            raise ValueError("profile id and version are required")
        if not self.evaluators:
            raise ValueError("an evaluation profile needs at least one evaluator")
        evaluator_ids = [evaluator.id for evaluator in self.evaluators]
        if len(evaluator_ids) != len(set(evaluator_ids)):
            raise ValueError("evaluator ids must be unique within a profile")
        object.__setattr__(self, "evaluators", tuple(self.evaluators))
        object.__setattr__(self, "telemetry_sinks", tuple(self.telemetry_sinks))
        object.__setattr__(self, "result_store_config", _frozen_mapping(self.result_store_config))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> EvaluationProfile:
        store = value["result_store"]
        return cls(
            id=str(value["id"]),
            version=str(value["version"]),
            evaluators=tuple(
                EvaluatorDefinition(
                    id=str(item["id"]),
                    adapter=str(item["adapter"]),
                    metrics=tuple(item.get("metrics", ())),
                    config=item.get("config", {}),
                    required=bool(item.get("required", True)),
                )
                for item in value["evaluators"]
            ),
            telemetry_sinks=tuple(value.get("telemetry", {}).get("sinks", ())),
            result_store=str(store["adapter"]),
            result_store_config=store.get("config", {}),
            fail_fast=bool(value.get("fail_fast", False)),
        )


@dataclass(frozen=True, slots=True)
class EvaluationRequest:
    run_id: str
    trial_id: str
    scenario: Mapping[str, Any]
    agent: Mapping[str, Any]
    trial: Mapping[str, Any]
    expected: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for attribute in ("scenario", "agent", "trial", "expected"):
            object.__setattr__(self, attribute, _frozen_mapping(getattr(self, attribute)))


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    metric: str
    score: float
    passed: bool
    evaluator_id: str
    evaluator_version: str
    threshold: float | None = None
    reason: str | None = None
    evidence: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))
