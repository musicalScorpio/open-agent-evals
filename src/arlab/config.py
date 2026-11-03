"""Load and validate versioned YAML definitions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from arlab.agents import AgentDefinition
from arlab.evaluation import EvaluationProfile


class ConfigurationError(ValueError):
    pass


def project_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise ConfigurationError(f"could not find project root from {start}")


def load_yaml(path: Path) -> Mapping[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"could not load YAML {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f"expected an object in {path}")
    return value


def validate_document(value: Mapping[str, Any], schema_path: Path, source: Path) -> None:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"could not load schema {schema_path}: {exc}") from exc

    errors = sorted(
        Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.path)
    )
    if not errors:
        return
    details = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        details.append(f"{location}: {error.message}")
    raise ConfigurationError(f"{source} failed validation:\n  " + "\n  ".join(details))


def load_agent(path: Path) -> AgentDefinition:
    root = project_root(path)
    value = load_yaml(path)
    validate_document(value, root / "schemas/agent.schema.json", path)
    return AgentDefinition.from_mapping(value)


def load_profile(path: Path) -> EvaluationProfile:
    root = project_root(path)
    value = load_yaml(path)
    validate_document(value, root / "schemas/evaluation-profile.schema.json", path)
    return EvaluationProfile.from_mapping(value)


def load_scenario(path: Path) -> Mapping[str, Any]:
    root = project_root(path)
    value = load_yaml(path)
    validate_document(value, root / "schemas/scenario.schema.json", path)
    return value


def load_dataset(path: Path) -> Mapping[str, Any]:
    root = project_root(path)
    value = load_yaml(path)
    validate_document(value, root / "schemas/dataset.schema.json", path)
    for case in value["cases"]:
        scenario_path = (root / str(case["scenario"])).resolve()
        if root not in scenario_path.parents:
            raise ConfigurationError(f"dataset scenario escapes project root: {case['scenario']}")
        load_scenario(scenario_path)
    return value
