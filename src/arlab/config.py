"""Load and validate versioned YAML definitions."""

from __future__ import annotations

import hashlib
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
    _validate_voice_assets(value, root, path)
    return value


def _validate_voice_assets(value: Mapping[str, Any], root: Path, source: Path) -> None:
    voice = value.get("voice")
    if not isinstance(voice, Mapping):
        return
    for index, message in enumerate(voice.get("conversation", ()), start=1):
        audio = message.get("audio") if isinstance(message, Mapping) else None
        if not isinstance(audio, Mapping):
            continue
        asset = _project_path(root, str(audio["path"]), f"voice audio turn {index}")
        if not asset.is_file():
            raise ConfigurationError(f"{source} references missing audio fixture: {asset}")
        expected = audio.get("sha256")
        actual = hashlib.sha256(asset.read_bytes()).hexdigest()
        if expected and expected != actual:
            raise ConfigurationError(
                f"{source} voice audio turn {index} sha256 mismatch: {audio['path']}"
            )


def load_dataset(path: Path) -> Mapping[str, Any]:
    root = project_root(path)
    value = load_yaml(path)
    validate_document(value, root / "schemas/dataset.schema.json", path)
    for case in value.get("cases", ()):
        scenario_path = _project_path(root, str(case["scenario"]), "dataset scenario")
        load_scenario(scenario_path)
    if "records" in value:
        records = value["records"]
        record_path = _project_path(root, str(records["path"]), "dataset records")
        schema_path = _project_path(root, str(records["schema"]), "dataset record schema")
        load_jsonl_documents(record_path, schema_path)
    return value


def _project_path(root: Path, relative: str, label: str) -> Path:
    path = (root / relative).resolve()
    if root not in path.parents:
        raise ConfigurationError(f"{label} escapes project root: {relative}")
    return path


def load_jsonl_documents(path: Path, schema_path: Path) -> list[Mapping[str, Any]]:
    documents = []
    identifiers = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ConfigurationError(f"could not load JSONL {path}: {exc}") from exc
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        source = Path(f"{path}:{number}")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ConfigurationError(f"invalid JSON in {source}: {exc}") from exc
        if not isinstance(value, dict):
            raise ConfigurationError(f"expected an object in {source}")
        validate_document(value, schema_path, source)
        identifier = str(value.get("id", ""))
        if identifier in identifiers:
            raise ConfigurationError(f"duplicate record id in {path}: {identifier}")
        identifiers.add(identifier)
        documents.append(value)
    if not documents:
        raise ConfigurationError(f"dataset records are empty: {path}")
    return documents
