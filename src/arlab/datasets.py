"""Framework-neutral dataset manifests and evaluator-specific exports."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arlab.config import load_jsonl_documents, load_scenario, validate_document


def dataset_records(manifest: Mapping[str, Any], root: Path) -> list[Mapping[str, Any]]:
    definition = manifest.get("records")
    if not isinstance(definition, Mapping):
        return []
    return load_jsonl_documents(root / str(definition["path"]), root / str(definition["schema"]))


def _record_scenario(manifest: Mapping[str, Any], record: Mapping[str, Any]) -> Mapping[str, Any]:
    metadata = dict(record["metadata"])
    return {
        "schema_version": "1.0",
        "id": record["id"],
        "title": f"Golden-answer case: {metadata.get('country', record['id'])}",
        "description": "Answer a synthetic factual prompt against a curated hidden golden.",
        "suite": manifest["id"],
        "tags": ["golden-answer", "synthetic-prompt", "geography"],
        "risk_tier": 1,
        "autonomy_level": 0,
        "task": {
            "user_prompt": record["input"],
            "success_conditions": ["answer_contains_all_expected_answers"],
        },
        "tools": {"available": [], "expected": []},
        "fixtures": [],
        "authorization": {
            "principal": "standard_user",
            "allowed_tools": [],
            "forbidden_tools": ["*"],
            "maximum_side_effects": 0,
        },
        "expectations": {
            "must": ["answer_from_model_knowledge"],
            "must_not": ["call_any_tool", "fabricate_additional_capitals"],
        },
        "budgets": {
            "max_turns": 3,
            "max_tool_calls": 0,
            "max_latency_ms": 30000,
            "max_cost_usd": 0.05,
            "max_output_tokens": 512,
        },
        "execution": {
            "repetitions": 1,
            "timeout_seconds": 45,
            "seed": int(manifest["generator"]["seed"]),
        },
        "metadata": {
            **metadata,
            "dataset_id": manifest["id"],
            "expected_output": record["expected_output"],
            "accepted_answers": record["accepted_answers"],
        },
    }


def scenario_cases(manifest: Mapping[str, Any], root: Path) -> list[tuple[Mapping[str, Any], str]]:
    if "cases" in manifest:
        return [
            (load_scenario(root / str(case["scenario"])), str(case["split"]))
            for case in manifest["cases"]
        ]

    cases = []
    definition = manifest["records"]
    record_path = root / str(definition["path"])
    for record in dataset_records(manifest, root):
        scenario = _record_scenario(manifest, record)
        validate_document(scenario, root / "schemas/scenario.schema.json", record_path)
        cases.append((scenario, str(record["split"])))
    return cases


def dataset_case_count(manifest: Mapping[str, Any], root: Path) -> int:
    return len(manifest.get("cases", ())) or len(dataset_records(manifest, root))


def dataset_split_counts(manifest: Mapping[str, Any], root: Path) -> dict[str, int]:
    splits: dict[str, int] = {}
    for _, split in scenario_cases(manifest, root):
        splits[split] = splits.get(split, 0) + 1
    return splits


def _scenario_golden(
    manifest: Mapping[str, Any], scenario: Mapping[str, Any], split: str, root: Path
) -> dict[str, Any]:
    metadata = scenario.get("metadata", {})
    if "expected_output" in metadata:
        expected_output = str(metadata["expected_output"])
        context = [json.dumps(metadata.get("capital_roles", []), sort_keys=True)]
    else:
        fixture_binding = scenario["fixtures"][0]
        fixture = json.loads((root / str(fixture_binding["path"])).read_text(encoding="utf-8"))
        result = fixture["result"]
        expected_output = (
            f"{result['recommendation']}. The forecast for {result['city']} shows "
            f"{result['conditions']} with a {result['precipitation_probability']}% "
            "chance of precipitation."
        )
        context = [json.dumps(result, sort_keys=True)]
    return {
        "input": scenario["task"]["user_prompt"],
        "expected_output": expected_output,
        "context": context,
        "additional_metadata": {
            "dataset_id": manifest["id"],
            "dataset_version": manifest["version"],
            "scenario_id": scenario["id"],
            "split": split,
            "source": manifest["source"],
            "expected_tools": scenario["tools"].get("expected", []),
            "faults": scenario.get("faults", []),
            "risk_tier": scenario["risk_tier"],
            "autonomy_level": scenario["autonomy_level"],
            **dict(metadata),
        },
    }


def export_deepeval_jsonl(manifest: Mapping[str, Any], root: Path, output_path: Path) -> Path:
    """Export local goldens without importing or requiring DeepEval."""
    records = [
        _scenario_golden(manifest, scenario, split, root)
        for scenario, split in scenario_cases(manifest, root)
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    return output_path
